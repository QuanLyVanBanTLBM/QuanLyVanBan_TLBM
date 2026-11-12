from django.db import models

# SQL_Fix4 mở rộng auth_permission (module_ten NOT NULL, content_type_id NULL) và auth_group (ma_nhom_quyen).
# django.contrib.auth.models.Permission/Group không biết các cột này nên hai model dưới đây chỉ ánh xạ lại
# cùng bảng (managed=False) để đọc/ghi phần mở rộng; nhóm/quyền vẫn gán cho người dùng qua auth.Group/Permission.


class PermissionInfo(models.Model):
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100, unique=True)
    module_ten = models.CharField(max_length=150)
    content_type_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "auth_permission"
        ordering = ["id"]


class GroupInfo(models.Model):
    name = models.CharField(max_length=150, unique=True)
    ma_nhom_quyen = models.CharField(max_length=50, unique=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "auth_group"
