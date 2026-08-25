# Construction Management API

API quản lý công trình xây dựng, xây dựng bằng FastAPI + SQLAlchemy + MySQL.

## Cấu trúc thư mục

```
construction_management/
├── app/
│   ├── core/                 # Cấu hình và bảo mật
│   │   ├── config.py         # Đọc biến môi trường
│   │   ├── security.py       # Băm mật khẩu, JWT token
│   │   └── exceptions.py     # Exception handler, format lỗi JSON thống nhất
│   ├── db/
│   │   ├── database.py       # Khởi tạo kết nối database (engine, session)
│   │   └── seed.py           # Script seed dữ liệu mẫu (user/công trình/hạng mục)
│   ├── dependencies/
│   │   └── auth.py           # get_current_user, kiểm tra quyền theo role
│   ├── models/                # Bảng trong Database (SQLAlchemy)
│   │   ├── activity_log.py    # Lịch sử thao tác
│   │   ├── site.py            # Công trình / Thành viên
│   │   ├── user.py            # Người dùng
│   │   └── work_item.py       # Hạng mục thi công
│   ├── routers/                # Endpoints
│   │   ├── auth.py             # Đăng ký, Đăng nhập
│   │   ├── site.py             # API Công trình
│   │   ├── users.py            # API User
│   │   └── work_item.py        # API Hạng mục thi công
│   ├── schemas/                # Pydantic models (request/response)
│   ├── services/                # Logic nghiệp vụ, tính toán
│   ├── utils/                   # Hàm tiện ích dùng chung
│   └── main.py                  # Điểm khởi chạy FastAPI
├── tests/                       # Unit test / integration test
├── .env.example
├── README.md
└── requirements.txt
```

## Cài đặt

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Sao chép `.env.example` thành `.env` và điền cấu hình thật (KHÔNG commit `.env`):

```bash
copy .env.example .env
```

## Chạy ứng dụng

```bash
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000/docs để xem Swagger UI.

Kiểm tra API còn sống (health-check, dùng cho monitoring/uptime check):

```bash
curl http://127.0.0.1:8000/health
```

## Seed dữ liệu mẫu

Tạo user/công trình/hạng mục thi công mẫu để test và demo (idempotent, chạy lại không tạo trùng):

```bash
python -m app.db.seed
```

Tài khoản mẫu sau khi seed (đăng nhập qua `POST /auth/login`):

| username | password    | role    |
|----------|-------------|---------|
| admin    | admin123    | admin   |
| manager1 | manager123  | manager |
| worker1  | worker123   | worker  |
| worker2  | worker123   | worker  |

## Format lỗi

Mọi lỗi (400/401/403/404/422/500) trả về theo cùng một cấu trúc JSON:

```json
{"error": {"status_code": 404, "message": "Không tìm thấy công trình"}}
```

Riêng lỗi validate dữ liệu (422) có thêm mảng `details` liệt kê từng field lỗi.

## Chạy test

```bash
pytest
```
