"""Script seed dữ liệu mẫu: user, công trình, thành viên, hạng mục thi công.

Chạy:
    python -m app.db.seed

Script idempotent: nếu đã thấy user "admin@example.com" trong DB thì bỏ qua, không tạo trùng.
"""

import sys
from datetime import datetime

from app.core.security import hash_password
from app.db.database import Base, SessionLocal, engine
from app.models.site import Site, SiteMember, SiteMemberRole
from app.models.user import User, UserRole
from app.models.work_item import WorkItem, WorkItemPriority, WorkItemStatus


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
        inactive_user = User(
            email="inactive@example.com",
            full_name="Tài Khoản Đã Khóa",
            password_hash=hash_password("inactive123"),
            role=UserRole.USER,
            is_active=False,
        )
        db.add_all([admin, manager, worker1, worker2, inactive_user])
        db.commit()
        for u in (admin, manager, worker1, worker2, inactive_user):
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
        db.add_all([site1, site2])
        db.commit()
        for s in (site1, site2):
            db.refresh(s)

        # --- Site members ---
        db.add_all(
            [
                SiteMember(site_id=site1.id, user_id=manager.id, role=SiteMemberRole.OWNER),
                SiteMember(site_id=site1.id, user_id=worker1.id, role=SiteMemberRole.MEMBER),
                SiteMember(site_id=site1.id, user_id=worker2.id, role=SiteMemberRole.MEMBER),
                SiteMember(site_id=site2.id, user_id=manager.id, role=SiteMemberRole.OWNER),
                SiteMember(site_id=site2.id, user_id=worker1.id, role=SiteMemberRole.MEMBER),
            ]
        )

        # --- Work items ---
        db.add_all(
            [
                WorkItem(
                    site_id=site1.id,
                    title="Đổ móng",
                    description="Thi công phần móng toàn bộ khối nhà",
                    status=WorkItemStatus.DONE,
                    priority=WorkItemPriority.HIGH,
                    assignee_id=worker1.id,
                    due_date=datetime(2026, 3, 1),
                ),
                WorkItem(
                    site_id=site1.id,
                    title="Xây tường tầng 1-5",
                    description="Xây tường gạch, hoàn thiện thô",
                    status=WorkItemStatus.IN_PROGRESS,
                    priority=WorkItemPriority.MEDIUM,
                    assignee_id=worker2.id,
                    due_date=None,
                ),
                WorkItem(
                    site_id=site1.id,
                    title="Lắp đặt hệ thống điện",
                    description="Đi dây điện âm tường toàn bộ tòa nhà",
                    status=WorkItemStatus.TODO,
                    priority=WorkItemPriority.LOW,
                    assignee_id=None,
                    due_date=None,
                ),
                WorkItem(
                    site_id=site2.id,
                    title="San lấp mặt bằng",
                    description="San lấp, chuẩn bị mặt bằng thi công",
                    status=WorkItemStatus.TODO,
                    priority=WorkItemPriority.HIGH,
                    assignee_id=worker1.id,
                    due_date=datetime(2026, 9, 1),
                ),
            ]
        )

        db.commit()
        print("Seed dữ liệu mẫu thành công:")
        print(
            "  - Users: admin@example.com/admin123, manager1@example.com/manager123, "
            "worker1@example.com/worker123, worker2@example.com/worker123, "
            "inactive@example.com/inactive123 (đã khóa)"
        )
        print(f"  - Sites: {site1.name!r}, {site2.name!r}")
        print("  - Đã tạo site_members và work_items mẫu.")
    finally:
        db.close()


if __name__ == "__main__":
    # Console Windows mặc định dùng codepage cp1252/850, không encode được tiếng Việt
    # có dấu -> ép stdout/stderr sang UTF-8 để tránh UnicodeEncodeError khi print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    seed()
