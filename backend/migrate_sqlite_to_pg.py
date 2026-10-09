"""
Script dong bo toan dien du lieu tu SQLite sang PostgreSQL theo kien truc 3 Model va SQL_Fix3:
- auth_user & accounts_staffprofile
- VanBanDen  -> documents_vanbanden
- VanBanDi   -> documents_vanbandi
- VanBanMat  -> documents_vanbanmat
- Attachments & View Logs
"""

import os
import sqlite3
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from documents.models import (
    HieuLuc,
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
    DocumentViewLog,
)

sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cur = sqlite_conn.cursor()

# 1. Dong bo auth_user
print("[1] Dong bo nguoi dung (auth_user)...")
sqlite_cur.execute("""
    SELECT id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined
    FROM auth_user
""")
users = sqlite_cur.fetchall()
for u in users:
    u_casted = (
        u[0],
        u[1],
        u[2],
        bool(u[3]),
        u[4],
        u[5],
        u[6],
        u[7],
        bool(u[8]),
        bool(u[9]),
        u[10],
    )
    with connection.cursor() as cur:
        cur.execute("""
            INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                password = EXCLUDED.password,
                is_superuser = EXCLUDED.is_superuser,
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                is_staff = EXCLUDED.is_staff,
                is_active = EXCLUDED.is_active;
        """, u_casted)
with connection.cursor() as cur:
    cur.execute("SELECT setval('auth_user_id_seq', COALESCE((SELECT MAX(id) FROM auth_user), 1));")
print(f"  -> Da dong bo {len(users)} nguoi dung auth_user.")

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

# 2. Dong bo accounts_staffprofile neu bang ton tai
with connection.cursor() as cur:
    cur.execute("SELECT to_regclass('public.accounts_staffprofile');")
    has_staff = cur.fetchone()[0]

if has_staff:
    print("[2] Dong bo accounts_staffprofile...")
    sqlite_cur.execute("""
        SELECT id, full_name, department, position, role, phone, avatar_url, birthday, created_at, updated_at, user_id
        FROM accounts_staffprofile
    """)
    staff_rows = sqlite_cur.fetchall()
    with connection.cursor() as cur:
        for s in staff_rows:
            cur.execute("""
                INSERT INTO accounts_staffprofile (id, full_name, department, position, role, phone, avatar_url, birthday, created_at, updated_at, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    role = EXCLUDED.role;
            """, s)
        try:
            cur.execute("SELECT setval('accounts_staffprofile_id_seq', COALESCE((SELECT MAX(id) FROM accounts_staffprofile), 1));")
        except Exception:
            pass
    print(f"  -> Da dong bo {len(staff_rows)} ho so can bo.")

# 3. Dong bo cac van ban tu documents_document
print("[3] Dong bo van ban (DEN, DI, MAT)...")
sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_document';")
has_old_table = sqlite_cur.fetchone()

if has_old_table:
    sqlite_cur.execute("""
        SELECT id, loai, nam, so_hieu, so_thu_tu, ngay_den, ngay_ban_hanh, ngay_van_ban,
               trich_yeu, noi_ban_hanh, nguoi_ky, chuc_vu, hieu_luc, ngay_het_hieu_luc,
               link_thay_the, ghi_chu, hien_thi, gui_mail_toan_he_thong, created_at, updated_at
        FROM documents_document
    """)
    rows = sqlite_cur.fetchall()

    for r in rows:
        loai = r[1]
        common_data = {
            'nam': r[2] or 2026,
            'so_hieu': r[3],
            'ngay_van_ban': r[7],
            'trich_yeu': r[8],
            'nguoi_ky': r[10] or '',
            'chuc_vu': r[11] or '',
            'hieu_luc': r[12] if r[12] in ('CON_HIEU_LUC', 'HET_HIEU_LUC', 'HET_VA_THAY_THE') else 'CON_HIEU_LUC',
            'ngay_het_hieu_luc': r[13],
            'link_thay_the': r[14] or '',
            'ghi_chu': r[15] or '',
            'hien_thi': bool(r[16]),
            'gui_mail_toan_he_thong': bool(r[17]),
            'nguoi_tao': admin_user,
        }

        if loai == 'DEN':
            doc, created = VanBanDen.objects.update_or_create(
                id=r[0],
                defaults={
                    **common_data,
                    'so_thu_tu': r[4] or 1,
                    'ngay_den': r[5] or timezone.now(),
                    'noi_ban_hanh': r[9] or '',
                }
            )
            print(f"  [VB Den] ID {doc.id} ({doc.so_hieu}): {'Tao moi' if created else 'Cap nhat'}")
        elif loai == 'DI':
            doc, created = VanBanDi.objects.update_or_create(
                id=r[0],
                defaults={
                    **common_data,
                    'so_thu_tu': r[4] or 1,
                    'ngay_ban_hanh': r[6] or timezone.now(),
                    'noi_ban_hanh': r[9] or '',
                }
            )
            print(f"  [VB Di] ID {doc.id} ({doc.so_hieu}): {'Tao moi' if created else 'Cap nhat'}")
        elif loai == 'MAT':
            doc, created = VanBanDen.objects.update_or_create(
                id=r[0],
                defaults={
                    **common_data,
                    'pham_vi': PhamVi.HAN_CHE,
                    'ngay_den': r[6] or timezone.now(),
                    'noi_ban_hanh': r[9] or '',
                }
            )
            print(f"  [VB Han che] ID {doc.id} ({doc.so_hieu}): {'Tao moi' if created else 'Cap nhat'}")

# Seed mau cho VB Di neu chua co
if VanBanDi.objects.count() == 0:
    print("[*] Khoi tao du lieu mau cho Van ban Di (documents_vanbandi)...")
    VanBanDi.objects.create(
        nam=2026,
        so_hieu="42/TB-ITC",
        so_thu_tu=1,
        ngay_ban_hanh=timezone.now(),
        ngay_van_ban=timezone.now(),
        trich_yeu="Thong bao lich thi ket thuc hoc phan Hoc ky 1 nam hoc 2026-2027.",
        noi_ban_hanh="Truong Cao dang Cong nghe Thong tin TP.HCM (ITC)",
        nguoi_ky="ThS. Nguyen Van A",
        chuc_vu="Pho Hieu truong",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        hien_thi=True,
        nguoi_tao=admin_user,
    )
    VanBanDi.objects.create(
        nam=2026,
        so_hieu="43/QD-ITC",
        so_thu_tu=2,
        ngay_ban_hanh=timezone.now(),
        ngay_van_ban=timezone.now(),
        trich_yeu="Quyet dinh ban hanh Quy che bao ve bi mat nha nuoc va an toan thong tin noi bo.",
        noi_ban_hanh="Truong Cao dang Cong nghe Thong tin TP.HCM (ITC)",
        nguoi_ky="TS. Le Van B",
        chuc_vu="Hieu truong",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        hien_thi=True,
        nguoi_tao=admin_user,
    )

# 4. Dong bo tep dinh kem (Attachments)
print("[4] Dong bo tep dinh kem...")
sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_documentattachment';")
has_att_table = sqlite_cur.fetchone()

if has_att_table:
    sqlite_cur.execute("SELECT id, file_name, file_size, uploaded_at, document_id, file FROM documents_documentattachment")
    att_rows = sqlite_cur.fetchall()
    for att in att_rows:
        att_id, file_name, file_size, uploaded_at, document_id, file_path = att
        # Kiem tra van ban den tuong ung
        if VanBanDen.objects.filter(id=document_id).exists():
            VanBanDenAttachment.objects.update_or_create(
                id=att_id,
                defaults={
                    'document_id': document_id,
                    'name': file_name,
                    'path': file_path,
                    'is_deleted': False,
                    'created_time': uploaded_at,
                    'created_user': admin_user,
                }
            )
            print(f"  [Attachment Den] ID {att_id}: {file_name} -> Doc ID {document_id}")
    print(f"  -> Da dong bo {VanBanDenAttachment.objects.count()} tep dinh kem.")

# 5. Dong bo Lich su xem (View logs)
print("[5] Dong bo lich su xem van ban...")
with connection.cursor() as cur:
    cur.execute("""
        INSERT INTO accounts_employee (id, ho_ten, ngay_sinh, chuc_vu_id, email, don_vi_id, username, password, is_active, is_staff, is_superuser, is_public, trang_thai)
        VALUES
        (2, 'Cán bộ Văn thư 1', '1995-01-01', 1, 'canbo@itc.edu.vn', 6, 'canbo', 'pbkdf2_sha256$system_seed_placeholder', true, false, false, true, 'LAM_VIEC'),
        (3, 'Cán bộ Văn thư 2', '1996-01-01', 1, 'canbo2@itc.edu.vn', 6, 'canbo2', 'pbkdf2_sha256$system_seed_placeholder', true, false, false, true, 'LAM_VIEC')
        ON CONFLICT (id) DO NOTHING;
    """)
    cur.execute("SELECT setval('accounts_employee_id_seq', COALESCE((SELECT MAX(id) FROM accounts_employee), 1));")

sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_documentviewlog';")
has_vl_table = sqlite_cur.fetchone()

if has_vl_table:
    sqlite_cur.execute("SELECT id, viewed_at, document_id, user_id FROM documents_documentviewlog")
    vl_rows = sqlite_cur.fetchall()
    for vl in vl_rows:
        vl_id, viewed_at, document_id, user_id = vl
        user_obj = User.objects.filter(id=user_id).first() or admin_user
        if VanBanDen.objects.filter(id=document_id).exists() and user_obj:
            DocumentViewLog.objects.update_or_create(
                id=vl_id,
                defaults={
                    'document_type': 'vanbanden',
                    'document_id': document_id,
                    'user': user_obj,
                    'viewed_at': viewed_at,
                }
            )
    print(f"  -> Da dong bo {DocumentViewLog.objects.count()} nhat ky xem van ban.")

# 6. Dong bo cot nguoi_nhan M2M (employee_id <-> user_id)
print("[6] Dong bo cot user_id cho cac bang M2M nguoi nhan...")
with connection.cursor() as cur:
    for tbl in ['documents_vanbanden_nguoinhan', 'documents_vanbandi_nguoinhan']:
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS user_id BIGINT;")
        cur.execute(f"UPDATE {tbl} SET user_id = employee_id WHERE user_id IS NULL AND employee_id IS NOT NULL;")
        cur.execute(f"UPDATE {tbl} SET employee_id = user_id WHERE employee_id IS NULL AND user_id IS NOT NULL;")

    cur.execute("""
        CREATE OR REPLACE FUNCTION sync_m2m_nguoinhan_cols()
        RETURNS TRIGGER AS $func$
        BEGIN
            IF NEW.user_id IS NOT NULL AND NEW.employee_id IS NULL THEN
                NEW.employee_id := NEW.user_id;
            END IF;
            IF NEW.employee_id IS NOT NULL AND NEW.user_id IS NULL THEN
                NEW.user_id := NEW.employee_id;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;
    """)

    for tbl, trg in [
        ('documents_vanbanden_nguoinhan', 'trg_sync_vbden_nguoinhan'),
        ('documents_vanbandi_nguoinhan', 'trg_sync_vbdi_nguoinhan'),
    ]:
        cur.execute(f"DROP TRIGGER IF EXISTS {trg} ON {tbl};")
        cur.execute(f"""
            CREATE TRIGGER {trg}
            BEFORE INSERT OR UPDATE ON {tbl}
            FOR EACH ROW EXECUTE FUNCTION sync_m2m_nguoinhan_cols();
        """)

# 7. Reset toan bo PostgreSQL sequences
print("[7] Reset sequences PostgreSQL...")
with connection.cursor() as cur:
    for tbl, seq in [
        ('auth_user', 'auth_user_id_seq'),
        ('documents_vanbanden', 'documents_vanbanden_id_seq'),
        ('documents_vanbandi', 'documents_vanbandi_id_seq'),
        ('documents_vanbanden_attachment', 'documents_vanbanden_attachment_id_seq'),
        ('documents_vanbandi_attachment', 'documents_vanbandi_attachment_id_seq'),
        ('documents_view_log', 'documents_view_log_id_seq'),
    ]:
        try:
            cur.execute(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {tbl}), 1));")
        except Exception as e:
            print(f"  Luu y sequence {seq}: {e}")

print("\n" + "="*50)
print("DONG BO HOAN TAT VOI POSTGRESQL CHAU KIET (SQL_Fix3)!")
print(f"  - Nguoi dung auth_user              : {User.objects.count()} tai khoan")
print(f"  - Van ban Den (documents_vanbanden) : {VanBanDen.objects.count()} ban ghi")
print(f"  - Van ban Di  (documents_vanbandi)  : {VanBanDi.objects.count()} ban ghi")
print(f"  - Tep dinh kem Van ban Den          : {VanBanDenAttachment.objects.count()} tep")
print(f"  - Nhat ky xem van ban (view log)    : {DocumentViewLog.objects.count()} luot")
print("="*50)
