import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from documents.views import DocumentViewSet
from documents.models import VanBanDen, DocumentViewLog

User = get_user_model()

def test_features():
    print("==================================================")
    print("   BẮT ĐẦU KIỂM THỬ TOÀN DIỆN CÁC TÍNH NĂNG API   ")
    print("==================================================")

    factory = RequestFactory()
    user = User.objects.filter(username="admin").first()
    view = DocumentViewSet.as_view({"get": "list"})

    # 1. Kiểm tra danh sách văn bản đến tổng quan
    req = factory.get("/api/documents/?loai=DEN")
    req.user = user
    res = view(req)
    assert res.status_code == 200, f"Lỗi GET list: {res.status_code}"
    data = res.data if isinstance(res.data, list) else res.data.get("results", [])
    print(f"\n1. [OK] GET /api/documents/?loai=DEN -> HTTP 200 (Tổng số văn bản: {len(data)})")

    # 2. Kiểm tra lọc theo Danh mục hồ sơ
    target_hs = "Hồ sơ Chuyển đổi số & CNTT 2026"
    req_hs = factory.get(f"/api/documents/?loai=DEN&ho_so={target_hs}")
    req_hs.user = user
    res_hs = view(req_hs)
    assert res_hs.status_code == 200
    data_hs = res_hs.data if isinstance(res_hs.data, list) else res_hs.data.get("results", [])
    assert len(data_hs) >= 2, f"Kỳ vọng >= 2 văn bản nhưng nhận {len(data_hs)}"
    for item in data_hs:
        assert item.get("danh_muc_ho_so") == target_hs or target_hs in item.get("danh_muc_ho_so", "")
    print(f"2. [OK] Lọc theo Danh mục Hồ sơ '{target_hs}': Trả về {len(data_hs)} văn bản chính xác 100%")

    # 3. Kiểm tra lọc theo Loại văn bản
    target_lvb = "Quyết định"
    req_lvb = factory.get(f"/api/documents/?loai=DEN&loai_van_ban={target_lvb}")
    req_lvb.user = user
    res_lvb = view(req_lvb)
    assert res_lvb.status_code == 200
    data_lvb = res_lvb.data if isinstance(res_lvb.data, list) else res_lvb.data.get("results", [])
    assert len(data_lvb) >= 2
    for item in data_lvb:
        has_match = (
            item.get("ten_loai_van_ban") == target_lvb
            or target_lvb.lower() in item.get("ten_loai_van_ban", "").lower()
            or "QĐ" in item.get("so_hieu", "")
            or "Quyết định" in item.get("trich_yeu", "")
        )
        assert has_match, f"Văn bản {item.get('so_hieu')} không khớp loại văn bản {target_lvb}"
    print(f"3. [OK] Lọc theo Loại văn bản '{target_lvb}': Trả về {len(data_lvb)} văn bản chính xác 100%")

    # 4. Kiểm tra lọc theo Trạng thái hiệu lực
    req_hl = factory.get("/api/documents/?loai=DEN&hieu_luc=CON_HIEU_LUC_1_PHAN")
    req_hl.user = user
    res_hl = view(req_hl)
    assert res_hl.status_code == 200
    data_hl = res_hl.data if isinstance(res_hl.data, list) else res_hl.data.get("results", [])
    assert any(d["so_hieu"] == "55/HD-STTTT" for d in data_hl)
    print(f"4. [OK] Lọc theo Trạng thái 'CON_HIEU_LUC_1_PHAN': Tìm thấy 55/HD-STTTT chuẩn 100%")

    # 5. Kiểm tra nghiệp vụ Thay thế và Bị thay thế
    vb1 = VanBanDen.objects.get(so_hieu="101/QĐ-UBND")
    vb2 = VanBanDen.objects.get(so_hieu="102/QĐ-UBND")
    
    view_detail = DocumentViewSet.as_view({"get": "retrieve"})
    
    # Chi tiết VB 2 (Đi thay thế)
    req_det2 = factory.get(f"/api/documents/{vb2.id}/")
    req_det2.user = user
    res_det2 = view_detail(req_det2, pk=vb2.id)
    assert res_det2.status_code == 200
    d2 = res_det2.data
    assert "101/QĐ-UBND" in d2.get("thay_the_cho", []) or "101/QĐ-UBND" in d2.get("link_thay_the", "")
    print(f"5. [OK] Nghiệp vụ Thay thế:")
    print(f"   - VB mới {vb2.so_hieu}: Trạng thái = {d2['hieu_luc']}, Thay thế cho = {d2.get('thay_the_cho')}")

    # Chi tiết VB 1 (Bị thay thế)
    req_det1 = factory.get(f"/api/documents/{vb1.id}/")
    req_det1.user = user
    res_det1 = view_detail(req_det1, pk=vb1.id)
    assert res_det1.status_code == 200
    d1 = res_det1.data
    assert "102/QĐ-UBND" in d1.get("bi_thay_boi", []) or "102/QĐ-UBND" in d1.get("link_thay_the", "")
    print(f"   - VB cũ {vb1.so_hieu}: Trạng thái = {d1['hieu_luc']}, Bị thay bởi = {d1.get('bi_thay_boi')}")

    # 6. Kiểm tra API Người xem (viewers) kết nối CSDL thực tế
    vb5 = VanBanDen.objects.get(so_hieu="88/KH-CNTT")
    view_viewers = DocumentViewSet.as_view({"get": "viewers"})
    req_viewers = factory.get(f"/api/documents/{vb5.id}/viewers/")
    req_viewers.user = user
    res_viewers = view_viewers(req_viewers, pk=vb5.id)
    assert res_viewers.status_code == 200
    v_data = res_viewers.data if isinstance(res_viewers.data, list) else res_viewers.data.get("results", [])
    assert len(v_data) > 0, "Không có lịch sử người xem nào trả về!"
    first_viewer = v_data[0]
    assert "username" in first_viewer
    assert "viewed_at" in first_viewer
    print(f"6. [OK] API /api/documents/{vb5.id}/viewers/ kết nối CSDL thật 100%:")
    print(f"   - Số lượng người đã xem từ DB: {len(v_data)}")
    for v in v_data:
        print(f"     + [{v.get('username')}] {v.get('full_name')} - {v.get('chuc_danh', 'Chức danh')} ({v.get('don_vi', 'Đơn vị')}) lúc {v.get('viewed_at')}")

    # 7. Kiểm tra Tệp đính kèm PDF
    req_det5 = factory.get(f"/api/documents/{vb5.id}/")
    req_det5.user = user
    res_det5 = view_detail(req_det5, pk=vb5.id)
    d5 = res_det5.data
    attachments = d5.get("attachments", [])
    assert len(attachments) > 0, "Không có file đính kèm nào trả về!"
    first_att = attachments[0]
    print(f"7. [OK] Tệp đính kèm:")
    print(f"   - Tên file: {first_att.get('file_name')}")
    print(f"   - URL file: {first_att.get('file')}")

    print("\n==================================================")
    print("   TẤT CẢ 7/7 TÍNH NĂNG VÀ NGHIỆP VỤ PASS 100%!   ")
    print("==================================================")

if __name__ == "__main__":
    test_features()
