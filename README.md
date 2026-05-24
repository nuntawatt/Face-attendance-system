# ระบบบันทึกเวลาทำงานด้วยใบหน้า (Face Attendance System) 🎭

ระบบหลังบ้าน (Backend API) สำหรับบันทึกเวลาเข้า-ออกงานด้วยใบหน้าแบบ Realtime พัฒนาด้วย **FastAPI** ควบคู่กับโมเดล AI **InsightFace** สำหรับตรวจจับและจำแนกใบหน้า พร้อมระบบจัดเก็บไฟล์รูปภาพใบหน้าใน **MinIO Object Storage** และรองรับการทำ **Soft Delete** เพื่อความปลอดภัยของข้อมูล

---

## 🌟 ฟีเจอร์เด่นของระบบ

1. **สแกนใบหน้าด้วย AI แม่นยำสูง**: ใช้โมเดล InsightFace (`buffalo_l` / `buffalo_s`) เพื่อสแกน ค้นหา และจดจำใบหน้าได้รวดเร็ว
2. **เก็บรูปภาพใบหน้าอัตโนมัติ (MinIO)**: เมื่อสแกนผ่าน ระบบจะตัดเฉพาะภาพใบหน้า (Face Crop) บันทึกขึ้น MinIO ด้วยชื่อไฟล์แบบ UUID ป้องกันการซ้ำซ้อน และบันทึก URL ลงในฐานข้อมูลทันที
3. **จัดการเขตเวลาถูกต้องแม่นยำ (Timezone Asia/Bangkok)**: ล็อกเขตเวลาของเซิร์ฟเวอร์เป็นเวลาประเทศไทย ป้องกันการเช็คอินผิดวันเมื่อนำไป Deploy บนคลาวด์ต่างประเทศ (เช่น AWS/Render ที่ปกติเป็นเวลา UTC)
4. **ลบข้อมูลแบบปลอดภัย (Soft Delete)**: ตารางข้อมูลหลักมีคอลัมน์ `deleted_at` ป้องกันการลบข้อมูลแบบถาวรโดยไม่ได้ตั้งใจ เพื่อให้สามารถตรวจสอบย้อนหลัง (Audit Trail) ได้ตลอดเวลา
5. **ดึงข้อมูลความเร็วสูง**: มีระบบแคชใบหน้าใน memory (In-Memory Embedding Cache) ทำให้สแกนและเปรียบเทียบใบหน้าได้แบบ Realtime ไม่ต้องโหลดข้อมูลจากฐานข้อมูลใหม่ทุกครั้ง

---

## 🛠️ เทคโนโลยีที่เลือกใช้ (Tech Stack)

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **Database**: PostgreSQL (สตรีมผ่าน [SQLAlchemy 2.0](https://www.sqlalchemy.org/) และ AsyncPG)
- **Object Storage**: [MinIO](https://min.io/) (เก็บไฟล์รูปภาพ)
- **Caching & Broker**: Redis (ใช้ควบคุมคิวการรับส่งข้อมูล)
- **AI & Computer Vision**: [InsightFace](https://github.com/deepinsight/insightface), ONNXRuntime, OpenCV, Pillow (รองรับรูปภาพ .png, .jpg, .jpeg, .webp, .bmp)

---

## 📚 โครงสร้างฐานข้อมูล (Data Dictionary)

ฐานข้อมูลหลักแบ่งออกเป็น 3 ตารางหลัก ดังนี้:

### 1. ตาราง: `employees` (ข้อมูลพนักงาน)
> เก็บประวัติส่วนตัวและสถานะการทำงานทั่วไปของพนักงาน

| ชื่อคอลัมน์ (Column) | ประเภทข้อมูล (Data Type) | ข้อจำกัด (Constraints) | ค่าเริ่มต้น (Default) | คำอธิบาย (Description) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK**, ห้ามว่าง | `uuid4()` | รหัสอ้างอิงพนักงานระดับฐานข้อมูล |
| `employee_code` | `VARCHAR(50)` | **Unique**, Indexed, ห้ามว่าง | - | รหัสพนักงาน (เช่น EMP-001) ใช้เชื่อมโยงระบบอื่น |
| `full_name` | `VARCHAR(200)` | ห้ามว่าง | - | ชื่อ - นามสกุล ของพนักงาน |
| `department` | `VARCHAR(100)` | Indexed, ห้ามว่าง | - | แผนกหรือฝ่ายที่สังกัด |
| `position` | `VARCHAR(100)` | ห้ามว่าง | - | ตำแหน่งงานของพนักงาน |
| `email` | `VARCHAR(255)` | **Unique**, ว่างได้ | `NULL` | อีเมลสำหรับติดต่อ |
| `phone` | `VARCHAR(20)` | ว่างได้ | `NULL` | เบอร์โทรศัพท์พนักงาน |
| `notes` | `TEXT` | ว่างได้ | `NULL` | หมายเหตุหรือรายละเอียดเพิ่มเติม |
| `is_active` | `BOOLEAN` | ห้ามว่าง | `TRUE` | สถานะการทำงาน (`TRUE`=ยังอยู่, `FALSE`=พ้นสภาพ) |
| `face_registered` | `BOOLEAN` | ห้ามว่าง | `FALSE` | สถานะการลงทะเบียนใบหน้า (`TRUE`=ลงทะเบียนแล้ว) |
| `created_at` | `TIMESTAMPTZ` | ห้ามว่าง | `now()` | วัน-เวลาที่บันทึกข้อมูลเข้าระบบ |
| `updated_at` | `TIMESTAMPTZ` | ห้ามว่าง | `now()` | วัน-เวลาที่มีการแก้ไขข้อมูลล่าสุด |
| `deleted_at` | `TIMESTAMPTZ` | ว่างได้ | `NULL` | วัน-เวลาที่ลบพนักงานออกจากระบบ (**Soft Delete**) |

---

### 2. ตาราง: `face_embeddings` (ชุดเวกเตอร์ใบหน้าของพนักงาน)
> เก็บ Biometric Vector ของใบหน้าพนักงาน ใช้สำหรับเปรียบเทียบตอนสแกนเข้างาน

| ชื่อคอลัมน์ (Column) | ประเภทข้อมูล (Data Type) | ข้อจำกัด (Constraints) | ค่าเริ่มต้น (Default) | คำอธิบาย (Description) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK**, ห้ามว่าง | `uuid4()` | รหัสอ้างอิงระดับฐานข้อมูล |
| `employee_id` | `UUID` | **FK** (`employees.id`), **Unique**, ห้ามว่าง | - | เชื่อมกับพนักงาน (1 พนักงาน มีได้ 1 ใบหน้าเท่านั้น) |
| `embedding_vector` | `BYTEA` | ห้ามว่าง | - | เวกเตอร์ลักษณะใบหน้า 512 มิติ ที่ AI คำนวณได้ |
| `model_version` | `VARCHAR(50)` | ห้ามว่าง | - | เวอร์ชันโมเดล AI ที่ใช้ (เช่น `buffalo_l_v1`) |
| `image_quality_score`| `FLOAT` | ว่างได้ | `NULL` | คะแนนความคมชัดของภาพถ่ายตอนลงทะเบียน (0.0 - 1.0) |
| `image_url` | `VARCHAR(512)` | ว่างได้ | `NULL` | ลิงก์รูปภาพใบหน้าพนักงานที่บันทึกไว้ในระบบ MinIO |
| `created_at` | `TIMESTAMPTZ` | ห้ามว่าง | `now()` | วัน-เวลาที่ลงทะเบียนใบหน้า |
| `updated_at` | `TIMESTAMPTZ` | ห้ามว่าง | `now()` | วัน-เวลาที่แก้ไขชุดใบหน้าล่าสุด |
| `deleted_at` | `TIMESTAMPTZ` | ว่างได้ | `NULL` | วัน-เวลาที่ลบชุดข้อมูลใบหน้า (**Soft Delete**) |

> ⚠️ **หมายเหตุ:** `employee_id` เป็นแบบ **Cascade Delete** หากลบข้อมูลพนักงานในตารางหลัก ใบหน้าในตารางนี้จะถูกลบตามทันที

---

### 3. ตาราง: `attendance_records` (ประวัติการสแกนเข้า-ออกงานประจำวัน)
> เก็บประวัติเวลาการทำงานประจำวันของพนักงานทุกคน

| ชื่อคอลัมน์ (Column) | ประเภทข้อมูล (Data Type) | ข้อจำกัด (Constraints) | ค่าเริ่มต้น (Default) | คำอธิบาย (Description) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK**, ห้ามว่าง | `uuid4()` | รหัสอ้างอิงระดับฐานข้อมูล |
| `employee_id` | `UUID` | **FK** (`employees.id`), Indexed, ห้ามว่าง | - | พนักงานที่สแกนใบหน้าเข้างาน |
| `work_date` | `DATE` | Indexed, ห้ามว่าง | - | วันที่ทำงาน (อิงตามเวลาไทย `Asia/Bangkok` เสมอ) |
| `check_in_time` | `TIMESTAMPTZ` | ห้ามว่าง | - | เวลาที่สแกนใบหน้าเข้างานสำเร็จครั้งแรกของวัน |
| `check_out_time` | `TIMESTAMPTZ` | ว่างได้ | `NULL` | เวลาสแกนออกงานล่าสุด (ระบบจะสลับเช็คเอาท์หลังผ่านไป 10 นาที) |
| `camera_id` | `VARCHAR(100)` | ห้ามว่าง | - | ไอดีกล้องหรืออุปกรณ์ Kiosk ที่ใช้สแกน |
| `confidence_score` | `FLOAT` | ห้ามว่าง | - | คะแนนความแม่นยำของใบหน้า (%) |
| `status` | `VARCHAR(20)` | ห้ามว่าง | `'present'` | สถานะ: `present` (มาทำงานปกติ), `late` (สาย), `early_leave` (กลับก่อนเวลา) |
| `image_url` | `VARCHAR(512)` | ว่างได้ | `NULL` | ลิงก์รูปภาพถ่ายสดใบหน้าตอนที่สแกนผ่านจริงใน MinIO |
| `created_at` | `TIMESTAMPTZ` | ห้ามว่าง | `now()` | วัน-เวลาที่สร้างบันทึกนี้เข้าระบบ |
| `updated_at` | `TIMESTAMPTZ` | ห้ามว่าง | `now()` | วัน-เวลาที่อัปเดตข้อมูลล่าสุด |
| `deleted_at` | `TIMESTAMPTZ` | ว่างได้ | `NULL` | วัน-เวลาที่ลบบันทึกประวัตินี้ออก (**Soft Delete**) |

> ⚠️ **หมายเหตุ:** มีคีย์ประกอบแบบพิเศษ `UniqueConstraint("employee_id", "work_date")` ควบคุมอยู่เพื่อห้ามสร้างแถวบันทึกเวลาซ้ำซ้อนในวันเดียวกัน

---

## ⚡ วิธีการติดตั้งและรันระบบ (Quick Start)

### 1. เปิดใช้งานบริการผ่าน Docker (MinIO, Postgres, Redis)
ระบบต้องการฐานข้อมูล PostgreSQL, แคช Redis และพื้นที่เก็บรูป MinIO ในการทำงาน:

- **ลิงก์หน้าจัดการ MinIO Web Console**: [http://localhost:9001](http://localhost:9001)
- **ข้อมูลเข้าระบบ MinIO**: User: `moragon` / Password: `moragon1234`
- **ชื่อโฟลเดอร์เก็บภาพ (Bucket)**: `images` (ระบบสร้างให้อัตโนมัติเมื่อเริ่มโปรแกรมครั้งแรก)

```bash
# สั่งเปิดฐานข้อมูลและ Object Storage ในโหมดพื้นหลัง
docker compose up -d minio postgres redis

# ตรวจเช็คสถานะการทำงานของตู้คอนเทนเนอร์
docker compose ps
```

### 2. ตั้งค่าการรันระบบหลังบ้าน (FastAPI Server)

1. **สร้างและเรียกใช้งาน Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **ติดตั้งปลั๊กอินและ Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **อัปเดตสคีมาฐานข้อมูล (Run Database Migrations)**:
   ```bash
   alembic upgrade head
   ```

4. **สั่งรันเซิร์ฟเวอร์หลังบ้าน**:
   ```bash
   uvicorn app.main:app --reload
   ```
   *หมายเหตุ: สามารถเข้าเช็ค Interactive API Documents (Swagger) ได้ที่ [http://localhost:8000/docs](http://localhost:8000/docs)*

---

## 🧪 วิธีการทดสอบระบบ (Testing)

เราเขียนชุดทดสอบ (Unit & Integration Tests) เพื่อตรวจสอบความถูกต้องของ Timezone, สิทธิ์การเขียนตารางฐานข้อมูล, Soft Delete และการอัปโหลดไฟล์ขึ้น MinIO อย่างครบถ้วน:

```bash
# รันการทดสอบระบบทั้งหมดในทีเดียว
PYTHONPATH=. ./.venv/bin/pytest -v
```

---

## 📂 โครงสร้างโฟลเดอร์ของโครงการ (Directory Structure)

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
├── tests/             # ไฟล์ทดสอบสคริปต์ (Pytest)
├── Dockerfile         # คำสั่งสร้างอิมเมจ API ของระบบ
├── docker-compose.yml # จัดระเบียบการเชื่อมโยงระบบฐานข้อมูล, คีย์เวิร์ด และ MinIO
├── requirements.txt   # รายชื่อแพ็กเกจระบบควบคุมการรันภาษา Python
└── run_kiosk.py       # แอปพลิเคชันจำลองหน้าตู้นำทางด้วยกล้องสแกน OpenCV
```