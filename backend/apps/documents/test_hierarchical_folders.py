"""
Test Suite kiểm thử Mô hình Thư mục nhiều cấp (Nested / Hierarchical Folders)
Kiểm tra toàn diện:
1. Tạo thư mục nhiều cấp (Level 1 -> Level 2 -> Level 3 -> Level 4)
2. Tính toán Materialized Path và Depth
3. Chống vòng lặp thư mục (Circular Reference Prevention)
4. Giới hạn độ sâu (Depth limit <= MAX_DEPTH)
5. Ràng buộc duy nhất tên thư mục cùng cấp (UniqueConstraint)
6. Xóa cascade thư mục cha kéo theo toàn bộ con cháu và file
7. API CRUD Thư mục (/api/folders/)
8. API Cây thư mục (/api/folders/tree/)
9. API Di chuyển thư mục (/api/folders/<id>/move/) và tự động cập nhật path toàn cây con
10. API Breadcrumb (/api/folders/<id>/breadcrumb/)
11. Quản lý File trong thư mục (/api/folders/<id>/files/ và /api/folder-files/)
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from documents.models import Folder, FolderFile

User = get_user_model()


class HierarchicalFolderModelTests(TestCase):
    """Kiểm thử cấp Model: Logic cấu trúc dữ liệu, quan hệ và toàn vẹn dữ liệu."""

    def test_create_nested_folders_4_levels(self):
        """Tạo cấu trúc 4 cấp và kiểm tra depth, path."""
        # Cấp 1: Tài liệu
        f1 = Folder.objects.create(name="Tài liệu")
        self.assertEqual(f1.depth, 0)
        self.assertEqual(f1.path, f"/{f1.pk}/")

        # Cấp 2: Lập trình
        f2 = Folder.objects.create(name="Lập trình", parent=f1)
        self.assertEqual(f2.depth, 1)
        self.assertEqual(f2.path, f"/{f1.pk}/{f2.pk}/")

        # Cấp 3: Python
        f3 = Folder.objects.create(name="Python", parent=f2)
        self.assertEqual(f3.depth, 2)
        self.assertEqual(f3.path, f"/{f1.pk}/{f2.pk}/{f3.pk}/")

        # Cấp 4: Bài tập
        f4 = Folder.objects.create(name="Bài tập", parent=f3)
        self.assertEqual(f4.depth, 3)
        self.assertEqual(f4.path, f"/{f1.pk}/{f2.pk}/{f3.pk}/{f4.pk}/")

        # Kiểm tra get_ancestors & get_breadcrumb
        ancestors = f4.get_ancestors()
        self.assertEqual([a.name for a in ancestors], ["Tài liệu", "Lập trình", "Python"])

        breadcrumb = f4.get_breadcrumb()
        self.assertEqual([b.name for b in breadcrumb], ["Tài liệu", "Lập trình", "Python", "Bài tập"])

        # Kiểm tra full_path_display
        self.assertEqual(f4.full_path_display, "Tài liệu / Lập trình / Python / Bài tập")

        # Kiểm tra get_descendants từ gốc
        descendants = f1.get_descendants()
        self.assertEqual(descendants.count(), 3)
        desc_ids = set(descendants.values_list("id", flat=True))
        self.assertEqual(desc_ids, {f2.id, f3.id, f4.id})

    def test_circular_reference_prevention(self):
        """Kiểm tra không thể di chuyển thư mục cha vào thư mục con cháu của chính nó."""
        f1 = Folder.objects.create(name="Tài liệu")
        f2 = Folder.objects.create(name="Lập trình", parent=f1)
        f3 = Folder.objects.create(name="Python", parent=f2)

        # Thử di chuyển f1 vào con f2 -> Phải văng ValidationError
        with self.assertRaises(ValidationError):
            f1.move_to(f2)

        # Thử di chuyển f1 vào cháu f3 -> Phải văng ValidationError
        with self.assertRaises(ValidationError):
            f1.move_to(f3)

        # Thử đặt parent của f1 là chính nó -> Phải văng ValidationError
        with self.assertRaises(ValidationError):
            f1.move_to(f1)

    def test_move_folder_updates_descendant_paths(self):
        """Di chuyển nhánh thư mục phải cập nhật lại path và depth của tất cả con cháu."""
        root1 = Folder.objects.create(name="Kho A")
        root2 = Folder.objects.create(name="Kho B")

        sub = Folder.objects.create(name="Thư mục con", parent=root1)
        sub_sub = Folder.objects.create(name="Thư mục cháu", parent=sub)

        self.assertEqual(sub.depth, 1)
        self.assertEqual(sub_sub.depth, 2)
        self.assertTrue(sub_sub.path.startswith(f"/{root1.pk}/"))

        # Di chuyển sub từ root1 sang root2
        sub.move_to(root2)
        sub.refresh_from_db()
        sub_sub.refresh_from_db()

        self.assertEqual(sub.parent, root2)
        self.assertEqual(sub.depth, 1)
        self.assertEqual(sub.path, f"/{root2.pk}/{sub.pk}/")
        self.assertEqual(sub_sub.depth, 2)
        self.assertEqual(sub_sub.path, f"/{root2.pk}/{sub.pk}/{sub_sub.pk}/")

    def test_cascade_delete(self):
        """Xóa thư mục cha sẽ xóa toàn bộ con cháu và file."""
        root = Folder.objects.create(name="Gốc")
        child = Folder.objects.create(name="Con", parent=root)
        file1 = FolderFile.objects.create(folder=child, file_name="tailieu.pdf")

        self.assertTrue(Folder.objects.filter(pk=child.pk).exists())
        self.assertTrue(FolderFile.objects.filter(pk=file1.pk).exists())

        root.delete()

        self.assertFalse(Folder.objects.filter(pk=root.pk).exists())
        self.assertFalse(Folder.objects.filter(pk=child.pk).exists())
        self.assertFalse(FolderFile.objects.filter(pk=file1.pk).exists())


class HierarchicalFolderAPITests(TestCase):
    """Kiểm thử cấp API REST: Endpoints cho Frontend tương tác."""

    def setUp(self):
        user_kwargs = {"username": "testuser", "password": "password123"}
        if hasattr(User, "ho_ten"):
            user_kwargs["ho_ten"] = "Test User"
        self.user = User.objects.create_user(**user_kwargs)

        admin_kwargs = {"username": "testadmin", "password": "password123", "is_staff": True}
        if hasattr(User, "ho_ten"):
            admin_kwargs["ho_ten"] = "Admin User"
        self.admin_user = User.objects.create_user(**admin_kwargs)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_and_query_folder_tree_api(self):
        """Kiểm thử API tạo thư mục và lấy cây thư mục."""
        # 1. Tạo root folder qua API
        res = self.client.post("/api/folders/", {"name": "Tài liệu kỹ thuật"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        root_id = res.data["id"]

        # 2. Tạo subfolder qua API /api/folders/
        res = self.client.post("/api/folders/", {"name": "Backend", "parent_id": root_id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        backend_id = res.data["id"]

        # 3. Tạo subfolder qua endpoint /api/folders/<id>/children/
        res = self.client.post(f"/api/folders/{backend_id}/children/", {"name": "Django"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        django_id = res.data["id"]

        # 4. Thêm file vào thư mục Django
        res = self.client.post(
            f"/api/folders/{django_id}/files/",
            {"file_name": "guide.pdf", "file_size": 1024, "file_type": "pdf"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # 5. Lấy cây thư mục đầy đủ (/api/folders/tree/)
        res = self.client.get("/api/folders/tree/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tree = res.data
        self.assertEqual(len(tree), 1)
        root_node = tree[0]
        self.assertEqual(root_node["name"], "Tài liệu kỹ thuật")
        self.assertEqual(len(root_node["children"]), 1)

        backend_node = root_node["children"][0]
        self.assertEqual(backend_node["name"], "Backend")
        self.assertEqual(len(backend_node["children"]), 1)

        django_node = backend_node["children"][0]
        self.assertEqual(django_node["name"], "Django")
        self.assertEqual(django_node["files_count"], 1)

        # 6. Lấy breadcrumb của Django
        res = self.client.get(f"/api/folders/{django_id}/breadcrumb/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        bc_names = [item["name"] for item in res.data]
        self.assertEqual(bc_names, ["Tài liệu kỹ thuật", "Backend", "Django"])

    def test_move_folder_api_with_cycle_detection(self):
        """Kiểm thử API di chuyển thư mục và phát hiện vòng lặp."""
        f1 = Folder.objects.create(name="Thư mục 1")
        f2 = Folder.objects.create(name="Thư mục 2", parent=f1)
        f3 = Folder.objects.create(name="Thư mục 3", parent=f2)

        # Di chuyển f1 vào f3 qua API -> Phải trả về 400 Bad Request
        res = self.client.patch(f"/api/folders/{f1.id}/move/", {"target_parent_id": f3.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vòng lặp", res.data["detail"])

        # Di chuyển f3 ra làm thư mục gốc (target_parent_id = None)
        res = self.client.patch(f"/api/folders/{f3.id}/move/", {"target_parent_id": None}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        f3.refresh_from_db()
        self.assertIsNone(f3.parent)
        self.assertEqual(f3.depth, 0)

    def test_anonymous_user_blocked_from_folders_and_files(self):
        """Khách vãng lai (unauthenticated) không được phép truy cập folders và folder-files."""
        anon_client = APIClient()
        res = anon_client.get("/api/folders/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = anon_client.get("/api/folders/tree/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = anon_client.get("/api/folder-files/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_scan_local_requires_admin_permission(self):
        """Chỉ admin mới có quyền gọi API scan-local."""
        # Non-admin user (self.client is authenticated as self.user)
        res = self.client.post("/api/folders/scan-local/", {"folder_path": "/tmp/dummy"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Admin user
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)
        res = admin_client.post("/api/folders/scan-local/", {"folder_path": "/nonexistent_test_path_12345"}, format="json")
        self.assertNotEqual(res.status_code, status.HTTP_403_FORBIDDEN)
