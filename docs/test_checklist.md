# Checklist test API — luồng chính

Test cả case đúng (thành công) và case lỗi (400/401/403/404/422/429) cho từng luồng nghiệp
vụ chính. Toàn bộ checklist dưới đây đã được tự động hoá bằng pytest (`tests/`) — chạy bằng
`pytest -q`; kết quả hiện tại: **66/66 pass**, không còn lỗi 500 ở các case nghiệp vụ thông
thường.

| Luồng | Case | Kết quả mong đợi | Test |
|---|---|---|---|
| **Auth** | Đăng ký thành công | 201 | `test_register_success` |
| | Đăng ký email trùng | 400 | `test_register_duplicate_email` |
| | Đăng ký password quá ngắn | 422 | `test_register_password_too_short` |
| | Đăng nhập đúng | 200, có access + refresh token | `test_login_success_returns_access_and_refresh_token` |
| | Đăng nhập sai mật khẩu | 401 | `test_login_wrong_password` |
| | Đăng nhập tài khoản bị khóa | 403 | `test_login_inactive_account` |
| | Đăng nhập sai quá số lần cho phép | 429 | `test_login_rate_limit_blocks_after_max_attempts` |
| | Lấy user hiện tại có/không token, token hết hạn/không hợp lệ | 200 / 401 | `test_get_current_user*` |
| | Refresh token hợp lệ / dùng nhầm access token | 200 / 401 | `test_refresh_token_issues_new_access_token`, `test_refresh_rejects_access_token` |
| **Users** | Danh sách user — chỉ Admin | 403 (không phải admin) / 200 (admin, search + filter) | `test_list_users_requires_admin`, `test_list_users_as_admin_with_search_and_status_filter` |
| **Construction Sites** | Tạo công trình → tự thành OWNER | 201 | `test_create_site_success_and_becomes_owner` |
| | Tạo công trình chưa đăng nhập / tên rỗng / tên quá dài | 401 / 422 / 422 | `test_create_site_requires_auth`, `test_create_site_name_*` |
| | Danh sách công trình chỉ thấy owner/member, search theo tên | 200 | `test_list_sites_*` |
| | Chi tiết công trình — không phải member / không tồn tại | 403 / 404 | `test_get_site_requires_membership`, `test_get_site_not_found` |
| | Cập nhật công trình qua PATCH và PUT — chỉ OWNER | 200 / 403 | `test_update_site_owner_only`, `test_update_site_via_put_same_as_patch` |
| | Xóa công trình (soft delete) — chỉ OWNER, ẩn khỏi danh sách | 200 / 403 | `test_delete_site_soft_delete_hides_it`, `test_delete_site_non_owner_forbidden` |
| | Thêm/xóa thành viên công trình — trùng, không tồn tại, không phải owner, xóa owner cuối | 201 / 400 / 404 / 403 / 400 | `test_add_member_*`, `test_remove_member_*`, `test_cannot_remove_last_owner` |
| **Teams (Đội thi công)** | Tạo đội — chỉ OWNER | 201 / 403 | `test_create_team_owner_only` |
| | Danh sách đội — cần là member | 403 | `test_team_list_requires_site_membership` |
| | Chi tiết đội — cần là member / không tồn tại | 403 / 200 / 404 | `test_get_team_detail_requires_membership`, `test_get_team_not_found` |
| | Cập nhật đội — chỉ OWNER | 403 / 200 | `test_update_team_owner_only` |
| | Xóa đội — chỉ OWNER; hạng mục đang gán về `assignee_team_id=null`, không 500 | 403 / 200 | `test_delete_team_owner_only_and_unassigns_work_items` |
| | Thêm thành viên đội — user chưa thuộc site, đã trùng | 400 / 400 | `test_add_team_member_requires_site_membership`, `test_add_team_member_duplicate_rejected` |
| | Danh sách thành viên đội | 200 | `test_list_team_members` |
| | Xóa thành viên đội — chỉ OWNER, không tồn tại | 403 / 200 / 404 | `test_remove_team_member_owner_only_and_not_found` |
| **Work Items** | Tạo hạng mục — mọi member được tạo, không phải member bị chặn | 201 / 403 | `test_create_work_item_by_any_member`, `test_create_work_item_requires_membership` |
| | Tạo với `assignee_team_id` thuộc site khác / hợp lệ | 400 / 201 | `test_create_work_item_assignee_team_must_belong_to_site`, `test_create_work_item_with_valid_assignee_team` |
| | Danh sách — chỉ thấy đúng site, cần membership | 200 / 403 | `test_list_work_items_scoped_to_site`, `test_list_work_items_requires_membership` |
| | Filter theo priority/status, search theo title, pagination | 200 | `test_list_work_items_filter_and_search`, `test_list_work_items_pagination` |
| | Chi tiết — cần membership / không tồn tại | 403 / 200 / 404 | `test_get_work_item_detail_requires_membership`, `test_get_work_item_not_found` |
| | Cập nhật — OWNER sửa mọi field, PATCH không ghi đè field chưa gửi | 200 | `test_update_work_item_owner_can_edit_any_field`, `test_update_work_item_does_not_overwrite_unset_fields` |
| | Cập nhật — thành viên đội đang assign chỉ sửa được status/description | 200 (đúng field) / 403 (field khác) | `test_update_work_item_assignee_team_member_can_only_update_status_description` |
| | Cập nhật — member không liên quan / không phải site member | 403 | `test_update_work_item_unrelated_member_forbidden`, `test_update_work_item_non_member_forbidden` |
| | Xóa — chỉ OWNER | 403 / 200, sau đó GET trả 404 | `test_delete_work_item_owner_only` |
| **Comment** | Tạo/xem comment — cần là site member, người ngoài bị chặn | 201 / 403 / 200 / 403 | `test_comment_create_and_list_requires_membership` |
| **Attachment** | Upload sai loại file (không phải ảnh/PDF) | 400 | `test_upload_attachment_rejects_invalid_type` |
| | Upload thành công + xuất hiện trong danh sách | 201 / 200 | `test_upload_attachment_success_and_list` |
| | Upload — cần là site member | 403 | `test_upload_attachment_requires_membership` |
| **Response format / Health** | Mọi response (thành công + lỗi) đúng 6 trường chuẩn | — | `test_root`, `test_health`, `test_unified_error_format_404` |

## Case đã kiểm tra thủ công thêm (không đưa vào bộ test tự động vì trùng logic)

- Query filter kết hợp nhiều điều kiện cùng lúc (status + priority + assignee_team_id + search).
- Biên `page=0` và `size=101` → 422 (đúng theo `ge=1`/`le=100`).
- Enum sai trong query (`status=NOT_A_STATUS`) và trong body (`priority=URGENT`) → 422.
- PATCH rỗng (`{}`) bởi thành viên đội đang assign → 200, không lỗi.
- Đặt `assignee_team_id: null` tường minh bởi OWNER → 200, gỡ gán đúng.
- Sắp xếp theo `due_date` với `sort_order=asc/desc`.

## Kết luận

Không phát hiện lỗi 500 ở bất kỳ case nghiệp vụ thông thường nào trong quá trình test —
mọi lỗi nghiệp vụ đều được xử lý và trả về đúng status code (400/401/403/404/422/429) theo
format chuẩn 6 trường. 8 test case mới đã được bổ sung vào `tests/test_work_item.py` và
`tests/test_site.py` để lấp các lỗ hổng coverage phát hiện được (CRUD đội thi công đầy đủ,
PUT công trình).
