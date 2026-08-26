"""Tầng business logic: nhận input đã validate từ router, thao tác DB, áp dụng quy tắc
nghiệp vụ (phân quyền, validate chéo, ghi activity log) và raise HTTPException khi cần.

Router chỉ đóng vai trò khai báo route/response_model và gọi xuống service tương ứng —
không tự query DB hay raise lỗi nghiệp vụ.
"""
