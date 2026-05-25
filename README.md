# Face Attendance System 🎭

ระบบหลังบ้าน สำหรับบันทึกเวลาเข้า-ออกงานด้วยใบหน้า พัฒนาด้วย FastAPI ควบคู่กับโมเดล AI InsightFace สำหรับตรวจจับและจำแนกใบหน้า เพื่อแก้ปัญหาภายในองค์กร ช่วยลดต้นทุนของผู้บริหารในการลงทุนกับระบบที่มีอยู่แล้วในท้องตลาด

---

## 🌟 Features

1. **สแกนใบหน้าด้วย AI แม่นยำสูง**: ใช้โมเดล InsightFace (`buffalo_l`) เพื่อตรวจจับ, จัดตำแหน่ง และเข้ารหัสลายพิมพ์ใบหน้าได้อย่างแม่นยำสูง
2. **ตัวเร่งความเร็วฮาร์ดแวร์อัตโนมัติ**: ระบบตรวจจับตัวเร่งความเร็ว (CoreML บน Mac / CUDA บน Nvidia GPU) อัตโนมัติ ปรับปรุงความเร็วในการดึงรอยสแกนใบหน้าขึ้น 7 เท่า (~20ms ต่อเฟรม)
3. **จัดเก็บรูปภาพตัดเฉพาะ (MinIO Face Crop)**: ครอปเฉพาะส่วนใบหน้าพนักงานด้วยพิกัด AI สตรีมอัปโหลดขึ้นระบบ Object Storage (MinIO S3) แบบ Asynchronous ไร้รอยสะดุด
4. **แก้ไขเวลาคลาดเคลื่อน (Timezone Asia/Bangkok)**: ล็อกเวลาฐานข้อมูลเป็นเวลาประเทศไทย ป้องกันการเช็คอินผิดปฏิทินเมื่อนำไป Deploy บน Cloud ต่างประเทศ (เช่น AWS/Render ที่เป็น UTC)
5. **Deduplication Throttling**: ประยุกต์ใช้ Redis ป้องกันสแปมการเช็คอิน/เช็คเอาท์ซ้ำซ้อน ช่วยปกป้องการประมวลผลและการบันทึกฐานข้อมูล PostgreSQL
6. **อัปเดตผลลัพธ์แบบเรียลไทม์**: Broadcast ผลการเช็คอิน/เช็คเอาท์ส่งตรงไปยังหน้าแดชบอร์ดแบบเสี้ยววินาทีผ่าน WebSockets

---

## 🛠️ Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **Database**: PostgreSQL (สตรีมผ่าน [SQLAlchemy 2.0](https://www.sqlalchemy.org/) และ AsyncPG)
- **Object Storage**: [MinIO](https://min.io/) (เก็บไฟล์รูปภาพใบหน้าพนักงาน)
- **Caching & Throttling**: Redis (ควบคุมและกรองข้อมูลเข้างานซ้ำซ้อน)
- **AI & Computer Vision**: [InsightFace](https://github.com/deepinsight/insightface), ONNXRuntime, OpenCV, Pillow (รองรับภาพ .png, .jpg, .jpeg, .webp, .bmp)

---

## 📚 Data Dictionary

ฐานข้อมูลหลักแบ่งออกเป็น 3 ตารางหลัก ดังนี้:

### 1. Table : employees (ข้อมูลพนักงาน)
> เก็บประวัติส่วนตัวและสถานะการทำงานทั่วไปของพนักงาน

| Column | Data Type | Constraints | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| id | UUID | PK, ห้ามว่าง | uuid4() | รหัสอ้างอิงพนักงานระดับฐานข้อมูล |
| employee_code | VARCHAR(50) | Unique, Indexed, ห้ามว่าง | - | รหัสพนักงาน (เช่น EMP-001) ใช้เชื่อมโยงระบบอื่น |
| full_name | VARCHAR(200) | ห้ามว่าง | - | ชื่อ - นามสกุล ของพนักงาน |
| department | VARCHAR(100) | Indexed, ห้ามว่าง | - | แผนกหรือฝ่ายที่สังกัด |
| position | VARCHAR(100) | ห้ามว่าง | - | ตำแหน่งงานของพนักงาน |
| email | VARCHAR(255) | Unique, ว่างได้ | NULL | อีเมลสำหรับติดต่อ |
| phone | VARCHAR(20) | ว่างได้ | NULL | เบอร์โทรศัพท์พนักงาน |
| notes | TEXT | ว่างได้ | NULL | หมายเหตุหรือรายละเอียดเพิ่มเติม |
| is_active | BOOLEAN | ห้ามว่าง | TRUE | สถานะการทำงาน (TRUE=ยังอยู่, FALSE=พ้นสภาพ) |
| face_registered | BOOLEAN | ห้ามว่าง | FALSE | สถานะการลงทะเบียนใบหน้า (TRUE=ลงทะเบียนแล้ว) |
| created_at | TIMESTAMPTZ | ห้ามว่าง | now() | วัน-เวลาที่บันทึกข้อมูลเข้าระบบ |
| updated_at | TIMESTAMPTZ | ห้ามว่าง | now() | วัน-เวลาที่มีการแก้ไขข้อมูลล่าสุด |
| deleted_at | TIMESTAMPTZ | ว่างได้ | NULL | วัน-เวลาที่ลบพนักงานออกจากระบบ (Soft Delete) |

---

### 2. Table : face_embeddings (ชุดเวกเตอร์ใบหน้าของพนักงาน)
> เก็บ Biometric Vector ของใบหน้าพนักงาน ใช้สำหรับเปรียบเทียบตอนสแกนเข้างาน

| Column | Data Type | Constraints | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| id | UUID | PK, ห้ามว่าง | uuid4() | รหัสอ้างอิงระดับฐานข้อมูล |
| employee_id | UUID | FK (employees.id), Unique, ห้ามว่าง | - | เชื่อมกับพนักงาน (1 พนักงาน มีได้ 1 ใบหน้าเท่านั้น) |
| embedding_vector | BYTEA | ห้ามว่าง | - | เวกเตอร์ลักษณะใบหน้า 512 มิติ ที่ AI คำนวณได้ |
| model_version | VARCHAR(50) | ห้ามว่าง | - | เวอร์ชันโมเดล AI ที่ใช้ (เช่น buffalo_l_v1) |
| image_quality_score| FLOAT | ว่างได้ | NULL | คะแนนความคมชัดของภาพถ่ายตอนลงทะเบียน (0.0 - 1.0) |
| image_url | VARCHAR(512) | ว่างได้ | NULL | ลิงก์รูปภาพใบหน้าพนักงานที่บันทึกไว้ในระบบ MinIO |
| created_at | TIMESTAMPTZ | ห้ามว่าง | now() | วัน-เวลาที่ลงทะเบียนใบหน้า |
| updated_at | TIMESTAMPTZ | ห้ามว่าง | now() | วัน-เวลาที่แก้ไขชุดใบหน้าล่าสุด |
| deleted_at | TIMESTAMPTZ | ว่างได้ | NULL | วัน-เวลาที่ลบชุดข้อมูลใบหน้า (Soft Delete) |

> ⚠️ **หมายเหตุ:** `employee_id` เป็นแบบ **Cascade Delete** หากลบข้อมูลพนักงานในตารางหลัก ใบหน้าในตารางนี้จะถูกลบตามทันที

---

### 3. Table : attendance_records (ประวัติการสแกนเข้า-ออกงานประจำวัน)
> เก็บประวัติเวลาการทำงานประจำวันของพนักงานทุกคน

| Column | Data Type | Constraints | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| id | UUID | PK, ห้ามว่าง | uuid4() | รหัสอ้างอิงระดับฐานข้อมูล |
| employee_id | UUID | FK (employees.id), Indexed, ห้ามว่าง | - | พนักงานที่สแกนใบหน้าเข้างาน |
| work_date | DATE | Indexed, ห้ามว่าง | - | วันที่ทำงาน (อิงตามเวลาไทย Asia/Bangkok เสมอ) |
| check_in_time | TIMESTAMPTZ | ห้ามว่าง | - | เวลาที่สแกนใบหน้าเข้างานสำเร็จครั้งแรกของวัน |
| check_out_time | TIMESTAMPTZ | ว่างได้ | NULL | เวลาสแกนออกงานล่าสุด (ระบบจะสลับเช็คเอาท์หลังผ่านไป 10 นาที) |
| camera_id | VARCHAR(100) | ห้ามว่าง | - | ไอดีกล้องหรืออุปกรณ์ Kiosk ที่ใช้สแกน |
| confidence_score | FLOAT | ห้ามว่าง | - | คะแนนความแม่นยำของใบหน้า (%) |
| status | VARCHAR(20) | ห้ามว่าง | 'present' | สถานะ: present (มาทำงานปกติ) |
| image_url | VARCHAR(512) | ว่างได้ | NULL | ลิงก์รูปภาพถ่ายสดใบหน้าตอนที่สแกนผ่านจริงใน MinIO |
| created_at | TIMESTAMPTZ | ห้ามว่าง | now() | วัน-เวลาที่สร้างบันทึกนี้เข้าระบบ |
| updated_at | TIMESTAMPTZ | ห้ามว่าง | now() | วัน-เวลาที่อัปเดตข้อมูลล่าสุด |
| deleted_at | TIMESTAMPTZ | ว่างได้ | NULL | วัน-เวลาที่ลบบันทึกประวัตินี้ออก (Soft Delete) |

> ⚠️ **หมายเหตุ:** มีดัชนีคีย์ประกอบพิเศษ `UniqueConstraint("employee_id", "work_date")` ควบคุมอยู่เพื่อห้ามสร้างแถวบันทึกเวลาเข้างานซ้ำซ้อนในวันเดียวกัน

---

## ⚡ Quick Start

### 1. การใช้งานบนตู้คอนเทนเนอร์ (Docker Environment)

เนื่องจากระบบคอนฟิกทั้งหมดถูกจัดระเบียบและย้ายไปอยู่ที่โฟลเดอร์ `docker/` สคริปต์รันจึงย้ายและควบคุมได้จากที่เดียวกัน:

```bash
# 1. ย้ายเข้าโฟลเดอร์สำหรับจัดการ Docker
cd docker

# 2. สั่งเริ่มการทำงานระบบใน Background
docker compose up -d

# 3. สั่งรันและสร้างอิมเมจระบบใหม่ทั้งหมด
docker compose up -d --build

# 4. ตรวจสอบการบันทึกสถานะการรัน (Logs)
docker compose logs -f

# 5. สั่งหยุดการทำงานและล้างข้อมูลจำลอง
docker compose down -v
```

### 2. ตั้งค่าการรันสำหรับเครื่องพัฒนาหลังบ้าน (FastAPI Server)

1. **สร้างและเรียกใช้งาน Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **ติดตั้ง dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **อัปเดตสคีมาฐานข้อมูล (Run Database Migrations)**:
   ```bash
   alembic upgrade head
   ```

4. **สั่งรันเซิร์ฟเวอร์หลังบ้านเพื่อพัฒนา**:
   ```bash
   uvicorn app.main:app --reload
   ```

### 3. รันแอปพลิเคชันจำลองหน้าตู้นำทางด้วย OpenCV Kiosk

```bash
# สั่งรัน OpenCV Desktop Kiosk จำลองหน้าตู้ผ่านเว็บแคมเครื่อง
python gui/run_kiosk.py
```

---

## 🧪 Testing

```bash
# รันการทดสอบระบบและสถาปัตยกรรม Soft Delete ทั้งหมดในทีเดียว
PYTHONPATH=. ./.venv/bin/pytest -v
```

---

## 📂 Directory Structure

```
.
├── alembic/           # ไฟล์ควบคุมการอัปเดตและปรับโครงสร้างตารางฐานข้อมูล
├── app/
│   ├── ai/            # ตรรกะตรวจจับใบหน้าและวิเคราะห์ AI (InsightFace ONNX)
│   ├── api/           # ตัวจัดเส้นทางและ Endpoint API ต่างๆ (FastAPI Router v1)
│   ├── attendance/    # เครื่องมืออ่านเฟรมวิดีโอกล้อง RTSP และประมวลเวลาเข้างานประจำวัน
│   ├── core/          # ตัวตั้งค่าระบบ, ดักจับข้อผิดพลาด, ระบบเวลาประเทศไทย (Timezone)
│   ├── database/      # สคริปต์เชื่อมต่อฐานข้อมูล Mixins และคีย์ UUID
│   ├── models/        # ตาราง ORM Models (สัญญาข้อมูลกับตาราง PostgreSQL)
│   ├── repositories/  # เลเยอร์จัดการคำสั่งคิวรี SQL หลักแบบตัดการลบตรง
│   ├── schemas/       # สคีมารองรับและตรวจสอบความถูกต้องของข้อมูล (Pydantic)
│   └── services/      # บริการหลักของธุรกิจ, การประมวลผลระบบแคช, และการอัปโหลดภาพใบหน้าขึ้น MinIO
├── docker/            # โฟลเดอร์เก็บคอนฟิกสำหรับรัน Container
│   ├── Dockerfile     # สคริปต์สร้างอิมเมจสำหรับรัน API ระบบ
│   └── docker-compose.yml # เชื่อมโยงระบบหลังบ้าน ฐานข้อมูล Redis และ MinIO เข้าด้วยกัน
├── gui/               # โฟลเดอร์เก็บแอปพลิเคชันหน้าจอ Kiosk
│   └── run_kiosk.py   # แอปพลิเคชันหน้าตู้จำลองด้วยกล้องเว็บแคมผ่าน OpenCV
├── tests/             # ไฟล์ทดสอบสคริปต์แบบอัตโนมัติ (Pytest)
├── requirements.txt   # รายชื่อแพ็กเกจระบบควบคุมการรันภาษา Python
└── alembic.ini        # คอนฟิกกลางของระบบฐานข้อมูลไมเกรชัน
```
