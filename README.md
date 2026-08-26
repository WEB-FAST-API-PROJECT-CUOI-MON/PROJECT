# Construction Management API

API quản lý công trình xây dựng, xây dựng bằng FastAPI + SQLAlchemy + MySQL.

## Tính năng chính

- **Auth**: đăng ký, đăng nhập (JWT access + refresh token), rate limit chống brute-force cho `/auth/login`.
- **Users**: xem thông tin bản thân (`/users/me`), danh sách user (chỉ role `ADMIN`, hỗ trợ search/filter).
- **Công trình (Construction Sites)**: CRUD, soft delete, quản lý thành viên và role (`OWNER`/`MEMBER`) trong từng công trình.
- **Đội thi công (Teams)**: CRUD đội và thành viên đội trong một công trình — chỉ `OWNER` công trình được quản lý. Hạng mục thi công được assign cho đội, không assign trực tiếp cho user.
- **Hạng mục thi công (Work Items)**: CRUD, filter/search/sort/pagination; phân quyền chi tiết theo role — `OWNER` toàn quyền, `MEMBER` được xem/tạo, thành viên đội đang được assign chỉ được cập nhật `status`/`description`.
- **Comment**: nhật ký thi công theo từng hạng mục.
- **Attachment**: upload file đính kèm (ảnh jpg/png/webp hoặc PDF) cho hạng mục, giới hạn loại và kích thước file.
- **Activity log**: ghi lại lịch sử các thao tác quan trọng (tạo/sửa/xóa công trình, đội, hạng mục, thành viên...).
- **Response format chuẩn**: mọi API trả về đúng 6 trường thống nhất (xem [Format response chuẩn](#format-response-chuẩn)).

## Cấu trúc thư mục

```
construction_management/
├── app/
│   ├── core/                    # Cấu hình và bảo mật
│   │   ├── config.py            # Đọc biến môi trường
│   │   ├── security.py          # Băm mật khẩu, JWT token
│   │   ├── rate_limit.py        # Rate limit chống brute-force cho /auth/login (in-memory)
│   │   ├── response_envelope.py # Middleware bọc response thành công theo format chuẩn
│   │   └── exceptions.py        # Exception handler, format lỗi JSON thống nhất
│   ├── db/
│   │   ├── database.py       # Khởi tạo kết nối database (engine, session)
│   │   └── seed.py           # Script seed dữ liệu mẫu (user/công trình/đội thi công/hạng mục)
│   ├── dependencies/
│   │   └── auth.py           # get_current_user, kiểm tra quyền theo role
│   ├── models/                # Bảng trong Database (SQLAlchemy)
│   │   ├── activity_log.py    # Lịch sử thao tác
│   │   ├── site.py            # Công trình / Thành viên
│   │   ├── team.py            # Đội thi công (Tổ đội) / Thành viên đội
│   │   ├── user.py            # Người dùng
│   │   └── work_item.py       # Hạng mục thi công / Comment / Attachment
│   ├── routers/                # Endpoints
│   │   ├── auth.py             # Đăng ký, Đăng nhập
│   │   ├── site.py             # API Công trình
│   │   ├── team.py             # API Đội thi công
│   │   ├── users.py            # API User
│   │   └── work_item.py        # API Hạng mục thi công, comment, attachment
│   ├── schemas/                # Pydantic models (request/response)
│   ├── services/                # Logic nghiệp vụ: query DB, phân quyền, validate, ghi activity log
│   │   ├── auth_service.py      # Đăng ký, đăng nhập, refresh token
│   │   ├── user_service.py      # Danh sách user
│   │   ├── site_service.py      # CRUD công trình + thành viên công trình
│   │   ├── team_service.py      # CRUD đội thi công + thành viên đội
│   │   └── work_item_service.py # CRUD hạng mục thi công, comment, attachment
│   ├── utils/                   # Hàm tiện ích dùng chung (authz.py: kiểm tra quyền theo site)
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

Tạo user/công trình/đội thi công/hạng mục thi công mẫu để test và demo (idempotent, chạy lại không tạo trùng):

```bash
python -m app.db.seed
```

Tài khoản mẫu sau khi seed. Đăng nhập qua `POST /auth/login` bằng **email** (chuẩn OAuth2 password
grant đặt tên field là `username`, nhưng giá trị truyền vào phải là email):

| email                  | password    | role hệ thống (`User.role`) | vai trò trong site mẫu     |
|-------------------------|-------------|------------------------------|-----------------------------|
| admin@example.com       | admin123    | ADMIN                        | không thuộc site nào        |
| manager1@example.com    | manager123  | USER                         | OWNER cả 2 site mẫu         |
| worker1@example.com     | worker123   | USER                         | MEMBER cả 2 site, thuộc cả 2 đội mẫu |
| worker2@example.com     | worker123   | USER                         | MEMBER site 1, thuộc đội mẫu ở site 1 |
| inactive@example.com    | inactive123 | USER (đã khóa, `is_active=false`) | không thuộc site nào   |

`role` hệ thống (`ADMIN`/`USER`) khác với vai trò trong từng công trình (`OWNER`/`MEMBER`, xem
`SiteMemberRole`) — chỉ `ADMIN` mới gọi được `GET /users`, còn `OWNER`/`MEMBER` quyết định quyền
thao tác trên từng công trình, đội thi công và hạng mục thi công.

## Format response chuẩn

Mọi API (thành công lẫn lỗi) đều trả về đúng 6 trường:

```json
{
  "statusCode": 200,
  "message": "Lấy dữ liệu thành công",
  "data": { ... },
  "error": null,
  "path": "/construction-sites/1",
  "timestamp": "2026-08-25T13:21:25.882424+00:00"
}
```

- `statusCode`: HTTP status code thực tế của response.
- `message`: mô tả ngắn, tự sinh theo method (GET/POST/PUT/PATCH/DELETE) khi thành công, hoặc thông báo lỗi khi thất bại.
- `data`: payload thực sự của endpoint khi thành công, `null` khi lỗi.
- `error`: `null` khi thành công; khi lỗi là message hoặc mảng chi tiết lỗi validate (422).
- `path`, `timestamp`: đường dẫn request và thời điểm trả response (ISO-8601, UTC).

Response thành công được `StandardResponseMiddleware` (`app/core/response_envelope.py`) tự
động bọc lại — router không cần tự dựng envelope. Response lỗi được dựng đúng format ngay
tại `app/core/exceptions.py`. Do 204 No Content không được phép có body, mọi endpoint
DELETE trả về `200 OK` với `data: null` thay vì `204` để vẫn giữ đủ 6 trường chuẩn.

## File đính kèm (attachment)

`POST /work-items/{item_id}/attachments` nhận file upload (chỉ ảnh `jpg/png/webp` hoặc `PDF`) và
lưu vào thư mục cấu hình bởi `WORK_ITEM_UPLOAD_DIR` (mặc định `uploads/work_items`, đã thêm vào
`.gitignore`). Kích thước tối đa mỗi file cấu hình qua `WORK_ITEM_ATTACHMENT_MAX_SIZE_MB` (mặc
định 5MB). Cả hai biến đều có giá trị mặc định trong `app/core/config.py`, không bắt buộc khai
báo trong `.env`.

## Chạy test

```bash
pytest
```
