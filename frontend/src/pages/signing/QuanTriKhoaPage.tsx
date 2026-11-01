/**
 * Tab quản lý khóa ký và quyền ký của tài khoản khác (quản trị viên, phân vùng 3 của #447): xem trạng thái khóa ký,
 * PIN, quyền ký; khóa tạm thời hoặc bật lại quyền ký; thu hồi khẩn cấp khóa ký. Mọi thao tác bắt buộc nhập lý do;
 * server kiểm quyền quản trị và ghi nhật ký.
 */
import { useEffect, useState } from 'react';
import { Badge, Button, Card } from '@components/common';
import { DangTai, HopThoai, LoiTai, Rong, ThongBao, TruongNhap } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { dinhDangNgay, GIOI_HAN, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { QuanTriNguoiDung, ThoiHanKhoaQuyenKy } from '@lib/signing/types';
import { useTranslation } from '@i18n/translate';

type HanhDong = 'khoa' | 'bat_lai' | 'thu_hoi';

const THOI_HAN: { gia_tri: ThoiHanKhoaQuyenKy; khoa: string }[] = [
  { gia_tri: '1_gio', khoa: 'thoiHan1Gio' },
  { gia_tri: '8_gio', khoa: 'thoiHan8Gio' },
  { gia_tri: '24_gio', khoa: 'thoiHan24Gio' },
  { gia_tri: 'den_khi_bat_lai', khoa: 'thoiHanDenKhiBatLai' },
];

export default function QuanTriKhoaPage() {
  const { t, loi } = useSigningT();
  const { currentLang } = useTranslation();
  const { toi } = useToi();
  const [tuKhoa, setTuKhoa] = useState('');
  const [tuKhoaTim, setTuKhoaTim] = useState('');
  const ds = useTai(() => signingApi.quanTriNguoiDung(tuKhoaTim), [tuKhoaTim]);
  const [dong, setDong] = useState<{ nguoi: QuanTriNguoiDung; hanhDong: HanhDong } | null>(null);
  const [thoiHan, setThoiHan] = useState<ThoiHanKhoaQuyenKy>('8_gio');
  const [lyDo, setLyDo] = useState('');
  const [loiLyDo, setLoiLyDo] = useState('');
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: 'loi' | 'thanh_cong'; noi_dung: string } | null>(null);

  // Gõ tìm kiếm: chờ ngắn rồi mới gọi server để không gửi yêu cầu theo từng phím
  useEffect(() => {
    const hen = setTimeout(() => setTuKhoaTim(tuKhoa.trim()), 300);
    return () => clearTimeout(hen);
  }, [tuKhoa]);

  const ngayGio = (iso: string | null) => dinhDangNgay(iso, currentLang);
  const dongHopThoai = () => {
    if (dangLam) return;
    setDong(null);
    setLyDo('');
    setLoiLyDo('');
    setThoiHan('8_gio');
  };
  const moHopThoai = (nguoi: QuanTriNguoiDung, hanhDong: HanhDong) => {
    setThongBao(null);
    setDong({ nguoi, hanhDong });
  };

  const xacNhan = async () => {
    if (!dong) return;
    if (!lyDo.trim()) {
      setLoiLyDo(t('quanTri.lyDoBatBuoc'));
      return;
    }
    setDangLam(true);
    try {
      const { nguoi, hanhDong } = dong;
      if (hanhDong === 'khoa') await signingApi.quanTriKhoaQuyenKy(nguoi.id, thoiHan, lyDo.trim());
      else if (hanhDong === 'bat_lai') await signingApi.quanTriBatLaiQuyenKy(nguoi.id, lyDo.trim());
      else await signingApi.quanTriThuHoiKhoa(nguoi.id, lyDo.trim());
      const khoa = hanhDong === 'khoa' ? 'daKhoa' : hanhDong === 'bat_lai' ? 'daBatLai' : 'daThuHoi';
      setThongBao({ loai: 'thanh_cong', noi_dung: t(`quanTri.${khoa}`, { ten: nguoi.ten }) });
      setDangLam(false);
      setDong(null);
      setLyDo('');
      setLoiLyDo('');
      ds.tai();
    } catch (err) {
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
      setDangLam(false);
      setDong(null);
      ds.tai();
    }
  };

  if (!toi?.la_quan_tri) return <ThongBao loai="canh_bao">{t('quanTri.khongPhaiQuanTri')}</ThongBao>;

  const tieuDeHop = !dong ? '' : t(
    dong.hanhDong === 'khoa' ? 'quanTri.tieuDeKhoaQuyen' : dong.hanhDong === 'bat_lai' ? 'quanTri.tieuDeBatLai' : 'quanTri.tieuDeThuHoi',
    { ten: dong.nguoi.ten },
  );
  const moTaHop = !dong ? '' : t(
    dong.hanhDong === 'khoa' ? 'quanTri.moTaKhoaQuyen' : dong.hanhDong === 'bat_lai' ? 'quanTri.moTaBatLai' : 'quanTri.moTaThuHoi',
  );

  return (
    <div className="space-y-3.5">
      <Card className="min-w-0 p-4 space-y-3">
        <div>
          <h3 className="text-base font-bold text-main">{t('quanTri.tieuDe')}</h3>
          <p className="text-sm text-secondary">{t('quanTri.moTa')}</p>
        </div>
        <input
          className={LOP_O_NHAP}
          type="search"
          value={tuKhoa}
          onChange={(e) => setTuKhoa(e.target.value)}
          placeholder={t('quanTri.timKiem')}
          aria-label={t('quanTri.timKiem')}
        />
        {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.noi_dung}</ThongBao>}
        {ds.dangTai && !ds.duLieu && <DangTai />}
        {ds.loi != null && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
        {ds.duLieu && ds.duLieu.length === 0 && <Rong icon="fa-user-lock">{t('quanTri.khongCoKetQua')}</Rong>}
        {ds.duLieu && ds.duLieu.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle bg-surface-subtle text-xs font-bold uppercase tracking-wider text-muted">
                  <th className="px-3 py-2">{t('quanTri.cotTaiKhoan')}</th>
                  <th className="px-3 py-2">{t('quanTri.cotKhoaKy')}</th>
                  <th className="px-3 py-2">{t('quanTri.cotPin')}</th>
                  <th className="px-3 py-2">{t('quanTri.cotQuyenKy')}</th>
                  <th className="px-3 py-2">{t('quanTri.cotThaoTac')}</th>
                </tr>
              </thead>
              <tbody>
                {ds.duLieu.map((u) => (
                  <tr key={u.id} className="border-b border-border-subtle hover:bg-surface-hover align-top">
                    <td className="px-3 py-2.5">
                      <div className="font-semibold text-main">{u.ten}</div>
                      <div className="text-xs text-muted">
                        {[u.ten_dang_nhap, u.chuc_vu, u.don_vi].filter(Boolean).join(' · ')}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      {u.khoa_ky
                        ? <span className="font-mono text-xs text-main">{u.khoa_ky.ma_khoa}</span>
                        : <span className="text-muted">{t('quanTri.chuaCoKhoa')}</span>}
                    </td>
                    <td className="px-3 py-2.5">
                      {!u.pin ? <span className="text-muted">{t('quanTri.chuaDatPin')}</span>
                        : u.pin.khoa_cung ? <Badge variant="danger" size="sm" withDot>{t('quanTri.pinKhoaCung')}</Badge>
                          : u.pin.dang_khoa
                            ? <Badge variant="warning" size="sm" withDot>{t('quanTri.pinKhoaTam', { han: ngayGio(u.pin.khoa_den) })}</Badge>
                            : u.pin.so_lan_sai > 0
                              ? <Badge variant="secondary" size="sm">{t('quanTri.pinSaiLan', { so: u.pin.so_lan_sai })}</Badge>
                              : <span className="text-secondary">{t('quanTri.pinBinhThuong')}</span>}
                    </td>
                    <td className="px-3 py-2.5">
                      {u.khoa_quyen_ky
                        ? (
                          <div className="space-y-0.5">
                            <Badge variant="danger" size="sm" withDot>
                              {u.khoa_quyen_ky.khoa_den
                                ? t('quanTri.quyenBiKhoaDen', { han: ngayGio(u.khoa_quyen_ky.khoa_den) })
                                : t('quanTri.quyenBiKhoaVoHan')}
                            </Badge>
                            <div className="text-xs text-muted break-words">{u.khoa_quyen_ky.ly_do}</div>
                          </div>
                        )
                        : u.co_quyen_ky
                          ? <Badge variant="success" size="sm" withDot>{t('quanTri.quyenBinhThuong')}</Badge>
                          : <Badge variant="secondary" size="sm">{t('quanTri.quyenKhongCo')}</Badge>}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1.5">
                        {u.khoa_quyen_ky
                          ? <Button size="sm" variant="secondary" icon="fa-lock-open" onClick={() => moHopThoai(u, 'bat_lai')}>
                            {t('quanTri.batLaiQuyen')}
                          </Button>
                          : <Button size="sm" variant="secondary" icon="fa-user-lock" onClick={() => moHopThoai(u, 'khoa')}>
                            {t('quanTri.khoaQuyen')}
                          </Button>}
                        {u.khoa_ky && u.id !== toi.id && (
                          <Button size="sm" variant="danger" icon="fa-key" onClick={() => moHopThoai(u, 'thu_hoi')}>
                            {t('quanTri.thuHoiKhoa')}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <HopThoai
        moTieuDe={tieuDeHop}
        mo={dong !== null}
        onDong={dongHopThoai}
        dangXuLy={dangLam}
        chieuRong="32rem"
        chanDuoi={(
          <>
            <Button variant="secondary" onClick={dongHopThoai} disabled={dangLam}>{t('quanTri.huyBo')}</Button>
            <Button
              variant={dong?.hanhDong === 'bat_lai' ? 'primary' : 'danger'}
              onClick={xacNhan}
              disabled={dangLam}
            >
              {t('quanTri.xacNhan')}
            </Button>
          </>
        )}
      >
        <p className="text-sm text-secondary">{moTaHop}</p>
        {dong?.hanhDong === 'khoa' && (
          <TruongNhap nhan={t('quanTri.thoiHan')} batBuoc>
            <select className={LOP_O_NHAP} value={thoiHan} onChange={(e) => setThoiHan(e.target.value as ThoiHanKhoaQuyenKy)}>
              {THOI_HAN.map((m) => <option key={m.gia_tri} value={m.gia_tri}>{t(`quanTri.${m.khoa}`)}</option>)}
            </select>
          </TruongNhap>
        )}
        <TruongNhap nhan={t('quanTri.lyDo')} batBuoc loi={loiLyDo}>
          <textarea
            className={LOP_O_NHAP}
            rows={3}
            maxLength={GIOI_HAN.lyDo}
            value={lyDo}
            onChange={(e) => {
              setLyDo(e.target.value);
              if (loiLyDo) setLoiLyDo('');
            }}
          />
        </TruongNhap>
      </HopThoai>
    </div>
  );
}
