"""Script seed dữ liệu mẫu: user, công trình, thành viên, đội thi công, hạng mục thi công.

Chạy:
    python -m app.db.seed

Script idempotent: nếu đã thấy user "admin@example.com" trong DB thì bỏ qua, không tạo trùng.

Bộ dữ liệu được thiết kế để phủ nhiều tình huống test:
    - Nhiều vai trò: admin, quản lý sở hữu nhiều công trình, quản lý chỉ sở hữu 1 công trình,
      thợ thuộc nhiều công trình, thợ chỉ thuộc 1 công trình và không nằm trong đội nào,
      tài khoản đã bị khóa (is_active=False).
    - Công trình rỗng (chưa có hạng mục/thành viên ngoài chủ sở hữu) để test empty-state.
    - Công trình đã bị xóa mềm (is_deleted=True) để test việc ẩn khỏi danh sách.
    - Đội thi công rỗng (chưa có thành viên) để test empty-state.
    - Hạng mục thi công phủ đủ 3 trạng thái, đủ 3 mức ưu tiên, có/không có đội phụ trách,
      có/không có hạn hoàn thành, có hạn đã quá (overdue) để test cảnh báo trễ hạn.
    - Hạng mục có nhiều/1/0 comment và attachment để test phân trang & empty-state.
"""

import sys
from datetime import datetime

from app.core.security import hash_password
from app.db.database import Base, SessionLocal, engine
from app.models.site import Site, SiteMember, SiteMemberRole
from app.models.team import Team, TeamMember
from app.models.user import User, UserRole
from app.models.work_item import (
    WorkItem,
    WorkItemAttachment,
    WorkItemComment,
    WorkItemPriority,
    WorkItemStatus,
)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@example.com").first():
            print("Dữ liệu mẫu đã tồn tại, bỏ qua seed.")
            return

        # --- Users ---
        admin = User(
            email="admin@example.com",
            full_name="Quản trị viên",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN,
        )
        manager = User(
            email="manager1@example.com",
            full_name="Nguyễn Văn Quản Lý",
            password_hash=hash_password("manager123"),
            role=UserRole.USER,
        )
        manager2 = User(
            email="manager2@example.com",
            full_name="Phạm Thị Giám Sát",
            password_hash=hash_password("manager123"),
            role=UserRole.USER,
        )
        worker1 = User(
            email="worker1@example.com",
            full_name="Trần Văn Thợ",
            password_hash=hash_password("worker123"),
            role=UserRole.USER,
        )
        worker2 = User(
            email="worker2@example.com",
            full_name="Lê Thị Công",
            password_hash=hash_password("worker123"),
            role=UserRole.USER,
        )
        worker3 = User(
            email="worker3@example.com",
            full_name="Hoàng Văn Phụ",
            password_hash=hash_password("worker123"),
            role=UserRole.USER,
        )
        inactive_user = User(
            email="inactive@example.com",
            full_name="Tài Khoản Đã Khóa",
            password_hash=hash_password("inactive123"),
            role=UserRole.USER,
            is_active=False,
        )
        db.add_all([admin, manager, manager2, worker1, worker2, worker3, inactive_user])
        db.commit()
        for u in (admin, manager, manager2, worker1, worker2, worker3, inactive_user):
            db.refresh(u)

        # --- Construction sites ---
        site1 = Site(
            name="Chung cư Sunrise",
            description="Dự án chung cư cao tầng 20 tầng, 123 Đường Nguyễn Huệ, Quận 1, TP.HCM",
            owner_id=manager.id,
        )
        site2 = Site(
            name="Nhà xưởng Long Thành",
            description="Xây dựng nhà xưởng sản xuất, Khu công nghiệp Long Thành, Đồng Nai",
            owner_id=manager.id,
        )
        # Công trình rỗng: chỉ có chủ sở hữu, chưa có thành viên/đội/hạng mục nào khác
        # -> dùng để test các API list trả về danh sách rỗng.
        site3 = Site(
            name="Trường học ABC",
            description="Xây mới trường tiểu học ABC, Huyện Nhà Bè, TP.HCM",
            owner_id=manager2.id,
        )
        # Công trình đã xóa mềm -> dùng để test danh sách công trình phải ẩn bản ghi này.
        site4 = Site(
            name="Kho bãi cũ Bình Chánh",
            description="Công trình đã ngừng thi công, chờ thanh lý hồ sơ",
            owner_id=manager.id,
            is_deleted=True,
            deleted_at=datetime(2026, 6, 1),
        )
        db.add_all([site1, site2, site3, site4])
        db.commit()
        for s in (site1, site2, site3, site4):
            db.refresh(s)

        # --- Site members ---
        db.add_all(
            [
                SiteMember(site_id=site1.id, user_id=manager.id, role=SiteMemberRole.OWNER),
                SiteMember(site_id=site1.id, user_id=worker1.id, role=SiteMemberRole.MEMBER),
                SiteMember(site_id=site1.id, user_id=worker2.id, role=SiteMemberRole.MEMBER),
                # worker3 chỉ tham gia site1, không thuộc đội thi công nào (test thành viên
                # công trình nhưng chưa được xếp vào đội).
                SiteMember(site_id=site1.id, user_id=worker3.id, role=SiteMemberRole.MEMBER),
                SiteMember(site_id=site2.id, user_id=manager.id, role=SiteMemberRole.OWNER),
                SiteMember(site_id=site2.id, user_id=worker1.id, role=SiteMemberRole.MEMBER),
                # site3 chỉ có chủ sở hữu -> test truy cập bị từ chối với các user khác
                # (manager, worker1... không phải thành viên site3).
                SiteMember(site_id=site3.id, user_id=manager2.id, role=SiteMemberRole.OWNER),
            ]
        )

        # --- Đội thi công ---
        team1 = Team(site_id=site1.id, name="Tổ Móng - Xây tô", description="Đội phụ trách phần thô")
        team2 = Team(site_id=site2.id, name="Tổ San lấp", description="Đội phụ trách mặt bằng")
        # Đội rỗng, chưa có thành viên nào -> test empty-state danh sách thành viên đội.
        team3 = Team(site_id=site3.id, name="Tổ Bảo trì", description="Đội bảo trì, chưa phân công nhân sự")
        db.add_all([team1, team2, team3])
        db.commit()
        for t in (team1, team2, team3):
            db.refresh(t)

        db.add_all(
            [
                TeamMember(team_id=team1.id, user_id=worker1.id),
                TeamMember(team_id=team1.id, user_id=worker2.id),
                TeamMember(team_id=team2.id, user_id=worker1.id),
            ]
        )

        # --- Work items ---
        item_mong = WorkItem(
            site_id=site1.id,
            title="Đổ móng",
            description="Thi công phần móng toàn bộ khối nhà",
            status=WorkItemStatus.DONE,
            priority=WorkItemPriority.HIGH,
            assignee_team_id=team1.id,
            due_date=datetime(2026, 3, 1),
        )
        item_tuong = WorkItem(
            site_id=site1.id,
            title="Xây tường tầng 1-5",
            description="Xây tường gạch, hoàn thiện thô",
            status=WorkItemStatus.IN_PROGRESS,
            priority=WorkItemPriority.MEDIUM,
            assignee_team_id=team1.id,
            due_date=None,
        )
        item_dien = WorkItem(
            site_id=site1.id,
            title="Lắp đặt hệ thống điện",
            description="Đi dây điện âm tường toàn bộ tòa nhà",
            status=WorkItemStatus.TODO,
            priority=WorkItemPriority.LOW,
            assignee_team_id=None,
            due_date=None,
        )
        # Đã quá hạn (due_date ở quá khứ so với ngày hiện tại) nhưng chưa hoàn thành
        # -> dùng để test tính năng cảnh báo/lọc hạng mục trễ hạn.
        item_betong = WorkItem(
            site_id=site1.id,
            title="Kiểm tra chất lượng bê tông móng",
            description="Lấy mẫu, kiểm định cường độ bê tông móng đã đổ",
            status=WorkItemStatus.IN_PROGRESS,
            priority=WorkItemPriority.HIGH,
            assignee_team_id=team1.id,
            due_date=datetime(2026, 7, 15),
        )
        item_sanlap = WorkItem(
            site_id=site2.id,
            title="San lấp mặt bằng",
            description="San lấp, chuẩn bị mặt bằng thi công",
            status=WorkItemStatus.TODO,
            priority=WorkItemPriority.HIGH,
            assignee_team_id=team2.id,
            due_date=datetime(2026, 9, 1),
        )
        item_mong2 = WorkItem(
            site_id=site2.id,
            title="Đổ móng nhà xưởng",
            description="Thi công móng nhà xưởng theo bản vẽ kết cấu",
            status=WorkItemStatus.DONE,
            priority=WorkItemPriority.HIGH,
            assignee_team_id=team2.id,
            due_date=datetime(2026, 5, 1),
        )
        item_mai = WorkItem(
            site_id=site2.id,
            title="Lắp mái tôn",
            description="Lắp khung kèo và mái tôn nhà xưởng",
            status=WorkItemStatus.IN_PROGRESS,
            priority=WorkItemPriority.MEDIUM,
            assignee_team_id=None,
            due_date=datetime(2026, 10, 1),
        )
        db.add_all(
            [item_mong, item_tuong, item_dien, item_betong, item_sanlap, item_mong2, item_mai]
        )
        db.commit()
        for wi in (item_mong, item_tuong, item_dien, item_betong, item_sanlap, item_mong2, item_mai):
            db.refresh(wi)
        # site3 chủ động không có hạng mục thi công nào -> test empty-state.

        # --- Nhật ký thi công (comment) ---
        db.add_all(
            [
                WorkItemComment(
                    work_item_id=item_mong.id,
                    user_id=worker1.id,
                    content="Đã đổ bê tông móng xong, chờ đủ ngày dưỡng hộ trước khi tháo cốp pha.",
                ),
                WorkItemComment(
                    work_item_id=item_mong.id,
                    user_id=manager.id,
                    content="Đã nghiệm thu phần móng, đạt yêu cầu kỹ thuật.",
                ),
                WorkItemComment(
                    work_item_id=item_tuong.id,
                    user_id=worker2.id,
                    content="Đã xây xong tường tầng 1-2, tiếp tục lên tầng 3.",
                ),
                WorkItemComment(
                    work_item_id=item_tuong.id,
                    user_id=manager.id,
                    content="Nhắc đội chú ý mạch vữa đều, tránh nứt chân chim sau này.",
                ),
                WorkItemComment(
                    work_item_id=item_dien.id,
                    user_id=worker3.id,
                    content="Đã nhận bản vẽ điện, chuẩn bị vật tư trước khi thi công.",
                ),
                WorkItemComment(
                    work_item_id=item_betong.id,
                    user_id=worker1.id,
                    content="Kết quả nén mẫu chưa đạt cường độ thiết kế, cần kiểm tra lại.",
                ),
                WorkItemComment(
                    work_item_id=item_betong.id,
                    user_id=manager.id,
                    content="Đã báo đơn vị kiểm định lấy mẫu lại, chờ kết quả.",
                ),
                WorkItemComment(
                    work_item_id=item_sanlap.id,
                    user_id=worker1.id,
                    content="Đã san lấp được 60% diện tích mặt bằng.",
                ),
                WorkItemComment(
                    work_item_id=item_mong2.id,
                    user_id=manager.id,
                    content="Nghiệm thu móng nhà xưởng đạt yêu cầu, cho phép thi công tiếp.",
                ),
                # item_mai chủ động không có comment nào -> test empty-state.
            ]
        )

        # --- File đính kèm (attachment) ---
        db.add_all(
            [
                WorkItemAttachment(
                    work_item_id=item_mong.id,
                    uploaded_by_id=manager.id,
                    file_name="bien_ban_nghiem_thu_mong.pdf",
                    file_path="uploads/work_items/1/bien_ban_nghiem_thu_mong.pdf",
                    content_type="application/pdf",
                    size_bytes=204800,
                ),
                WorkItemAttachment(
                    work_item_id=item_tuong.id,
                    uploaded_by_id=worker2.id,
                    file_name="hien_truong_xay_tuong.jpg",
                    file_path="uploads/work_items/2/hien_truong_xay_tuong.jpg",
                    content_type="image/jpeg",
                    size_bytes=1048576,
                ),
                WorkItemAttachment(
                    work_item_id=item_betong.id,
                    uploaded_by_id=worker1.id,
                    file_name="ket_qua_kiem_dinh_betong.pdf",
                    file_path="uploads/work_items/4/ket_qua_kiem_dinh_betong.pdf",
                    content_type="application/pdf",
                    size_bytes=153600,
                ),
                WorkItemAttachment(
                    work_item_id=item_sanlap.id,
                    uploaded_by_id=manager.id,
                    file_name="mat_bang_san_lap.jpg",
                    file_path="uploads/work_items/5/mat_bang_san_lap.jpg",
                    content_type="image/jpeg",
                    size_bytes=2097152,
                ),
                # item_mai chủ động không có attachment nào -> test empty-state.
            ]
        )

        db.commit()
        print("Seed dữ liệu mẫu thành công:")
        print(
            "  - Users: admin@example.com/admin123, manager1@example.com/manager123, "
            "manager2@example.com/manager123, worker1@example.com/worker123, "
            "worker2@example.com/worker123, worker3@example.com/worker123, "
            "inactive@example.com/inactive123 (đã khóa)"
        )
        print(
            f"  - Sites: {site1.name!r}, {site2.name!r}, {site3.name!r} (rỗng), "
            f"{site4.name!r} (đã xóa mềm)"
        )
        print(
            "  - Đã tạo site_members, teams (kèm 1 đội rỗng), team_members, "
            "7 work_items (đủ trạng thái/ưu tiên, có hạng mục quá hạn), "
            "work_item_comments và work_item_attachments mẫu."
        )
    finally:
        db.close()


if __name__ == "__main__":
    # Console Windows mặc định dùng codepage cp1252/850, không encode được tiếng Việt
    # có dấu -> ép stdout/stderr sang UTF-8 để tránh UnicodeEncodeError khi print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    seed()
