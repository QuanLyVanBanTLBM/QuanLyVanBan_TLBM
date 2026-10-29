/**
 * Cấu hình quy trình ký (#80 mục A, E): quy trình CONG_TY do quản trị, PHONG_BAN do lãnh đạo đơn vị áp dụng.
 * Người ký cấu hình theo tài khoản (danh bạ cán bộ của phân hệ CBNV) hoặc theo chức vụ (Danh mục chức vụ của CBNV,
 * #275 mục 2, 7). Đơn vị áp dụng chọn từ Đơn vị của Nhóm 7 (quản trị: mọi đơn vị, lãnh đạo đơn vị: đơn vị mình).
 * Sửa quy trình nháp (đã kích hoạt thì nhân bản thành phiên bản mới). Xóa được phiên bản chưa có hồ sơ trình ký nào
 * dùng (#275 mục 1); còn hồ sơ thì nút Xóa bị vô hiệu kèm lý do. Người ký theo chức vụ hiện tên cán bộ đang giữ chức vụ
 * trong phạm vi đã chọn, không có ai thì cảnh báo (#275 mục 8).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Badge, Button, Card } from '@components/common';
import CauHinhUyQuyen from '@components/signing/CauHinhUyQuyen';
import { DangTai, HopThoai, LoiTai, Rong, ThongBao, TrangThaiBadge, TruongNhap } from '@components/signing/ChungUI';
import { docLoi, signingApi } from '@lib/signing/api';
import { boDau, GIOI_HAN, LOP_O_NHAP, MA_QUY_TRINH_HOP_LE, tenNguoiKyCauHinh } from '@lib/signing/dinhDang';
import { coQuyen, useTai, useToi } from '@lib/signing/hooks';
import { type HamDich, useSigningT } from '@lib/signing/i18n';
import type { CanBo, ChucVu, PhamViQuyTrinh, QuyTrinh, VaiTroKy } from '@lib/signing/types';

/** Người ký trong form: theo tài khoản (`nguoi_ky`) hoặc theo chức vụ (giữ nguyên khi sửa quy trình nháp). */
interface NguoiKyNhap {
  khoa: string; ten: string; chuc_danh?: string; nguoi_ky: number | null; chuc_vu_id: number | null;
  pham_vi_chuc_vu: string | null; vai_tro_ky: VaiTroKy; chan_ky_chinh: boolean;
}
interface CapNhap { ten_cap_ky: string; so_gio_xu_ly: string; don_vi_id: number | null; nguoi_ky: NguoiKyNhap[] }

const CAP_TRONG: CapNhap = { ten_cap_ky: '', so_gio_xu_ly: '', don_vi_id: null, nguoi_ky: [] };
/** Phạm vi tìm người giữ chức vụ chọn được trên form (DON_VI_CO_DINH cần cấp có đơn vị, giữ nguyên khi sửa). */
const PHAM_VI_CHUC_VU = ['DON_VI_NGUOI_TAO', 'TOAN_CO_QUAN'] as const;
const TOI_DA_GOI_Y = 500;

function capTuQuyTrinh(q: QuyTrinh, t: HamDich): CapNhap[] {
  return q.cap_ky.map((c) => ({
    ten_cap_ky: c.ten_cap_ky, so_gio_xu_ly: c.so_gio_xu_ly ? String(c.so_gio_xu_ly) : '', don_vi_id: c.don_vi_id,
    nguoi_ky: c.nguoi_ky.map((n) => ({
      khoa: `c${n.id}`, ten: tenNguoiKyCauHinh(n, t), nguoi_ky: n.nguoi_ky, chuc_vu_id: n.chuc_vu_id,
      chuc_danh: n.pham_vi_chuc_vu ? t(`phamViChucVu.${n.pham_vi_chuc_vu}`) : undefined,
      pham_vi_chuc_vu: n.pham_vi_chuc_vu, vai_tro_ky: n.vai_tro_ky, chan_ky_chinh: n.chan_ky_chinh,
    })),
  }));
}

/** Chức danh đầy đủ của cán bộ: chức vụ · đơn vị (danh bạ CBNV). */
function chucDanh(u: CanBo, khongCo: string): string {
  return [u.chuc_vu_ten, u.don_vi_ten].filter(Boolean).join(' · ') || khongCo;
}

interface ChonNguoiDungProps {
  onChon: (u: CanBo) => void;
}

/** Chọn cán bộ từ danh bạ CBNV (hỗ trợ tìm kiếm theo họ tên, username, chức vụ, đơn vị không dấu; hiển thị đầy đủ 83+ cán bộ). */
function ChonNguoiDung({ onChon }: ChonNguoiDungProps) {
  const { t, loi } = useSigningT();
  const [q, setQ] = useState('');
  const [mo, setMo] = useState(false);
  const hopRef = useRef<HTMLDivElement>(null);
  const ds = useTai(() => signingApi.danhBaCanBo(), []);

  useEffect(() => {
    const onBamNgoai = (e: MouseEvent) => {
      if (hopRef.current && !hopRef.current.contains(e.target as Node)) {
        setMo(false);
      }
    };
    document.addEventListener('mousedown', onBamNgoai);
    return () => document.removeEventListener('mousedown', onBamNgoai);
  }, []);

  const danhSach = useMemo(() => {
    if (!ds.duLieu) return [];
    if (Array.isArray(ds.duLieu)) return ds.duLieu;
    if (Array.isArray((ds.duLieu as { results?: CanBo[] }).results)) {
      return (ds.duLieu as { results: CanBo[] }).results;
    }
    return [];
  }, [ds.duLieu]);

  const tuKhoa = boDau(q.trim());

  // Danh sách cán bộ gợi ý: luôn hiển thị đầy đủ toàn bộ cán bộ nhân viên trong hệ thống
  const goiYCanBo = useMemo(() => {
    if (!danhSach.length) return [];
    if (tuKhoa) {
      return danhSach
        .filter((u) => boDau([u.ho_ten, u.username, u.chuc_vu_ten, u.don_vi_ten].join(' ')).includes(tuKhoa))
        .slice(0, TOI_DA_GOI_Y);
    }
    return danhSach.slice(0, TOI_DA_GOI_Y);
  }, [danhSach, tuKhoa]);

  const placeholder = t('quyTrinh.timNguoiDung');

  return (
    <div ref={hopRef} className="relative space-y-1">
      <div className="relative flex items-center">
        <input
          className={`${LOP_O_NHAP} pr-8`}
          placeholder={placeholder}
          aria-label={t('quyTrinh.themNguoiKy')}
          value={q}
          onFocus={() => setMo(true)}
          onChange={(e) => {
            setQ(e.target.value);
            setMo(true);
          }}
        />
        <button
          type="button"
          className="absolute right-2.5 text-muted hover:text-main"
          aria-label={mo ? t('chung.dong') : t('quyTrinh.themNguoiKy')}
          tabIndex={-1}
          onClick={() => setMo((m) => !m)}
        >
          <i className={`fa-solid ${mo ? 'fa-chevron-up' : 'fa-chevron-down'} text-xs`} aria-hidden="true" />
        </button>
      </div>
      {ds.loi && <p className="text-xs text-danger">{loi(ds.loi)}</p>}
      {mo && ds.dangTai && !ds.duLieu && (
        <div className="rounded-lg border border-border-subtle bg-surface p-2.5 text-xs text-muted shadow-sm flex items-center gap-2">
          <i className="fa-solid fa-spinner fa-spin text-primary" aria-hidden="true" />
          <span>{t('chung.dangTai')}</span>
        </div>
      )}
      {mo && goiYCanBo.length > 0 && (
        <div className="max-h-72 overflow-y-auto rounded-lg border border-border-subtle bg-surface shadow-md z-50 relative">
          <ul className="divide-y divide-border-subtle" role="listbox">
            {goiYCanBo.map((u) => (
              <li key={`cb-${u.id}`}>
                <button
                  type="button"
                  className="w-full px-3 py-2 text-left hover:bg-surface-hover flex items-center justify-between group transition-colors"
                  onClick={() => {
                    onChon(u);
                    setQ('');
                    setMo(false);
                  }}
                >
                  <div className="min-w-0 pr-2">
                    <span className="block text-sm font-semibold text-main group-hover:text-primary truncate flex items-center gap-1.5">
                      <i className="fa-solid fa-user text-xs text-secondary shrink-0" aria-hidden="true" />
                      <span>{u.ho_ten}</span>
                    </span>
                    <span className="block text-xs text-secondary truncate">{chucDanh(u, t('quyTrinh.chuaCoChucVu'))}</span>
                    <span className="block text-2xs text-muted truncate">@{u.username}</span>
                  </div>
                  <span className="text-xs text-primary font-medium shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100">
                    <i className="fa-solid fa-plus text-2xs" aria-hidden="true" />
                    <span>{t('chung.chon')}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {mo && !ds.dangTai && !!ds.duLieu && goiYCanBo.length === 0 && (
        <p className="rounded-lg border border-border-subtle bg-surface p-2.5 text-xs text-muted shadow-sm">
          {t('quyTrinh.khongThayNguoiDung')}
        </p>
      )}
    </div>
  );
}

/**
 * Đơn vị dùng để tìm cán bộ khớp người ký theo chức vụ: đơn vị cố định của cấp; "đơn vị người trình" của quy trình
 * phòng ban là đơn vị áp dụng; còn lại (toàn cơ quan, hoặc quy trình công ty theo đơn vị người trình) là mọi đơn vị.
 */
function donViTimCanBo(pham_vi_chuc_vu: string | null, don_vi_cap: number | null, pham_vi: PhamViQuyTrinh,
  don_vi_ap_dung: number | null): number | null {
  if (pham_vi_chuc_vu === 'DON_VI_CO_DINH') return don_vi_cap;
  if (pham_vi_chuc_vu === 'DON_VI_NGUOI_TAO' && pham_vi === 'PHONG_BAN') return don_vi_ap_dung;
  return null;
}

/** Tên cán bộ đang giữ chức vụ (dữ liệu phân hệ CBNV); không có ai thì cảnh báo cấp ký sẽ không có người ký. */
function CanBoChucVu({ chucVuId, donViId, theoNguoiTrinh }: {
  chucVuId: number; donViId: number | null; theoNguoiTrinh: boolean;
}) {
  const { t, loi } = useSigningT();
  const ds = useTai(() => signingApi.canBoTheoChucVu(chucVuId, donViId), [chucVuId, donViId]);
  if (ds.dangTai && !ds.duLieu) return <p className="text-xs text-muted">{t('chung.dangTai')}</p>;
  if (ds.loi) return <p className="text-xs text-danger">{loi(ds.loi)}</p>;
  if (!ds.duLieu) return null;
  if (ds.duLieu.count === 0) {
    return <p className="text-xs font-semibold text-warning-text" role="alert">{t('quyTrinh.khongCoUngVien')}</p>;
  }
  const con = ds.duLieu.count - ds.duLieu.results.length;
  return (
    <div className="space-y-0.5 text-xs" aria-label={t('quyTrinh.ungVien')}>
      <span className="font-semibold text-secondary">{t('quyTrinh.ungVien')} ({ds.duLieu.count}):</span>
      <ul className="flex flex-wrap gap-x-3 gap-y-0.5 text-main">
        {ds.duLieu.results.map((u) => (
          <li key={u.id}>{u.ten}{u.don_vi && <span className="text-muted"> · {u.don_vi}</span>}</li>
        ))}
        {con > 0 && <li className="text-muted">{t('quyTrinh.conNguoiKhac', { so: con })}</li>}
      </ul>
      {theoNguoiTrinh && <p className="text-muted">{t('quyTrinh.theoDonViNguoiTrinh')}</p>}
    </div>
  );
}

/** Khối thêm người ký cho từng cấp: chọn chức vụ (để lọc cán bộ hoặc gán quy tắc động) và chọn đích danh từ CBNV. */
function ThemNguoiKyCap({
  onChonCanBo,
  onChonChucVu,
  donViTim,
  chucVuCapKy,
}: {
  onChonCanBo: (u: CanBo) => void;
  onChonChucVu: (cv: { id: number; ten: string }, pham_vi: string) => void;
  donViTim: (pham_vi_chuc_vu: string) => number | null;
  chucVuCapKy?: ChucVu | null;
}) {
  const { t, loi } = useSigningT();
  const ds = useTai(() => signingApi.chucVu(), []);
  const [phamVi, setPhamVi] = useState<string>(PHAM_VI_CHUC_VU[0]);
  const [chucVuGoc, setChucVuGoc] = useState<string | null>(null);
  const [prevChucVuCapKy, setPrevChucVuCapKy] = useState(chucVuCapKy);
  if (chucVuCapKy !== prevChucVuCapKy) {
    setPrevChucVuCapKy(chucVuCapKy);
    setChucVuGoc(null);
  }
  const chucVu = chucVuGoc !== null ? chucVuGoc : (chucVuCapKy ? String(chucVuCapKy.id) : '');
  const setChucVu = (val: string) => setChucVuGoc(val);

  const chon = ds.duLieu?.find((c) => String(c.id) === chucVu);

  return (
    <div className="space-y-2 pt-2 border-t border-border-subtle">
      {/* 1. Chọn chức vụ: dùng để lọc danh bạ cán bộ hoặc bấm "Thêm theo chức vụ" để gán quy tắc động */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs font-semibold text-secondary">
          <span>{t('quyTrinh.chonTheoChucVu')}</span>
          {chon && (
            <button
              type="button"
              className="text-xs text-primary hover:underline"
              onClick={() => setChucVu('')}
            >
              {t('quyTrinh.xoaLocChucVu')}
            </button>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className={`${LOP_O_NHAP} w-auto min-w-48 flex-1`}
            aria-label={t('quyTrinh.themTheoChucVu')}
            value={chucVu}
            onChange={(e) => setChucVu(e.target.value)}
          >
            <option value="">{t('quyTrinh.tatCaChucVu')}</option>
            {ds.duLieu?.map((c) => (
              <option key={c.id} value={String(c.id)}>{c.name}</option>
            ))}
          </select>
          <select
            className={`${LOP_O_NHAP} w-auto`}
            aria-label={t('quyTrinh.phamViChucVu')}
            value={phamVi}
            onChange={(e) => setPhamVi(e.target.value)}
          >
            {PHAM_VI_CHUC_VU.map((p) => (
              <option key={p} value={p}>{t(`phamViChucVu.${p}`)}</option>
            ))}
          </select>
          <Button
            size="sm"
            variant="secondary"
            icon="fa-user-tie"
            disabled={!chon}
            title={t('quyTrinh.themTheoChucVu')}
            onClick={() => {
              if (chon) {
                onChonChucVu({ id: chon.id, ten: chon.name }, phamVi);
                setChucVu('');
              }
            }}
          >
            {t('quyTrinh.themTheoChucVu')}
          </Button>
        </div>
        {ds.loi && <p className="basis-full text-xs text-danger">{loi(ds.loi)}</p>}
        {chon && (
          <div className="basis-full">
            <CanBoChucVu
              chucVuId={chon.id}
              donViId={donViTim(phamVi)}
              theoNguoiTrinh={phamVi === 'DON_VI_NGUOI_TAO' && donViTim(phamVi) == null}
            />
          </div>
        )}
      </div>

      {/* 2. Chọn cán bộ đích danh từ danh bạ CBNV (luôn hiển thị đầy đủ toàn bộ cán bộ nhân viên) */}
      <div className="space-y-1">
        <span className="text-xs font-semibold text-secondary">
          {t('quyTrinh.chonCanBoDichDanh')}
        </span>
        <ChonNguoiDung onChon={onChonCanBo} />
      </div>
    </div>
  );
}

function FormTao({ mo, onDong, onXong, banDau }: { mo: boolean; onDong: () => void; onXong: () => void; banDau?: QuyTrinh }) {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const [ma, setMa] = useState(banDau?.ma_quy_trinh ?? '');
  const [ten, setTen] = useState(banDau?.ten_quy_trinh ?? '');
  const [phamVi, setPhamVi] = useState<PhamViQuyTrinh>(banDau?.pham_vi ?? (toi?.la_quan_tri ? 'CONG_TY' : 'PHONG_BAN'));
  const donViBanDau = banDau ? banDau.don_vi_ap_dung_id : toi?.don_vi_id;
  const [donVi, setDonVi] = useState(donViBanDau ? String(donViBanDau) : '');
  const dsDonVi = useTai(() => signingApi.donVi(), []);
  const dsChucVu = useTai(() => signingApi.chucVu(), []);
  const [cap, setCap] = useState<CapNhap[]>(banDau ? capTuQuyTrinh(banDau, t) : [CAP_TRONG]);
  const [dangLuu, setDangLuu] = useState(false);
  const [thongBao, setThongBao] = useState('');

  const donViApDung = phamVi === 'PHONG_BAN' && donVi ? Number(donVi) : null;
  const sua = (i: number, gia_tri: Partial<CapNhap>) => setCap((c) => c.map((x, j) => (j === i ? { ...x, ...gia_tri } : x)));
  const loiMa = !banDau && ma.trim() && !MA_QUY_TRINH_HOP_LE.test(ma.trim()) ? t('quyTrinh.loiMa') : '';
  const soGioQuaLon = (c: CapNhap) => Number(c.so_gio_xu_ly) > GIOI_HAN.soGio;
  const coKyNhayCu = cap.some((c) => c.nguoi_ky.some((n) => n.vai_tro_ky === 'KY_NHAY'));
  const lyDoChuaLuu = [
    !banDau && !ma.trim() ? t('quyTrinh.thieuMa') : '',
    loiMa ? t('quyTrinh.maKhongHopLe') : '',
    !ten.trim() ? t('quyTrinh.thieuTen') : '',
    phamVi === 'PHONG_BAN' && !donVi ? t('quyTrinh.thieuDonVi') : '',
    cap.some((c) => !c.ten_cap_ky.trim()) ? t('quyTrinh.thieuTenCap') : '',
    cap.some((c) => !c.nguoi_ky.length) ? t('quyTrinh.thieuNguoiKy') : '',
    cap.some(soGioQuaLon) ? t('quyTrinh.soGioKhongHopLe') : '',
    coKyNhayCu ? t('quyTrinh.kyNhayCu') : '',
  ].filter(Boolean);
  const hopLe = lyDoChuaLuu.length === 0;

  const luu = async () => {
    setDangLuu(true);
    setThongBao('');
    try {
      const body = {
        ma_quy_trinh: ma.trim(), ten_quy_trinh: ten.trim(), pham_vi: phamVi, mo_ta: banDau?.mo_ta ?? '',
        don_vi_ap_dung_id: phamVi === 'PHONG_BAN' ? Number(donVi) : null,
        cap_ky: cap.map((c, i) => ({
          cap_ky: i + 1, thu_tu: i + 1, ten_cap_ky: c.ten_cap_ky.trim(), don_vi_id: c.don_vi_id,
          so_gio_xu_ly: c.so_gio_xu_ly ? Number(c.so_gio_xu_ly) : null,
          nguoi_ky: c.nguoi_ky.map((n, j) => ({
            ...(n.nguoi_ky ? { nguoi_ky: n.nguoi_ky } : { chuc_vu_id: n.chuc_vu_id, pham_vi_chuc_vu: n.pham_vi_chuc_vu }),
            thu_tu: j + 1, vai_tro_ky: n.vai_tro_ky, chan_ky_chinh: n.chan_ky_chinh,
          })),
        })),
      };
      await (banDau ? signingApi.suaQuyTrinh(banDau.id, body) : signingApi.taoQuyTrinh(body));
      onXong();
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangLuu(false);
    }
  };

  return (
    <HopThoai moTieuDe={banDau ? t('quyTrinh.sua') : t('quyTrinh.tao')} mo={mo} onDong={onDong} dangXuLy={dangLuu}
      chanDuoi={<>
        <Button variant="secondary" onClick={onDong}>{t('chung.huyBo')}</Button>
        <Button icon="fa-floppy-disk" isLoading={dangLuu} disabled={!hopLe} onClick={luu}>{t('chung.luu')}</Button>
      </>}>
      <p className="m-0 text-xs text-secondary">{t('quyTrinh.dauSaoBatBuoc')}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        {!banDau && (
          <TruongNhap nhan={t('quyTrinh.ma')} batBuoc loi={loiMa} ghiChu={t('quyTrinh.maGhiChu')}>
            <input className={LOP_O_NHAP} maxLength={GIOI_HAN.maQuyTrinh} value={ma}
              aria-invalid={loiMa ? true : undefined} onChange={(e) => setMa(e.target.value)} />
          </TruongNhap>
        )}
        <TruongNhap nhan={t('quyTrinh.ten')} batBuoc>
          <input className={LOP_O_NHAP} maxLength={GIOI_HAN.tenQuyTrinh} value={ten} onChange={(e) => setTen(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('quyTrinh.phamVi')} batBuoc className={phamVi === 'CONG_TY' ? 'sm:col-span-2' : ''}>
          <select className={LOP_O_NHAP} value={phamVi} onChange={(e) => setPhamVi(e.target.value as PhamViQuyTrinh)}>
            <option value="CONG_TY">{t('phamVi.CONG_TY')}</option>
            <option value="PHONG_BAN">{t('phamVi.PHONG_BAN')}</option>
          </select>
        </TruongNhap>
        {phamVi === 'PHONG_BAN' && (
          <TruongNhap nhan={t('quyTrinh.donVi')} batBuoc>
            <select className={LOP_O_NHAP} value={donVi} onChange={(e) => setDonVi(e.target.value)}>
              <option value="">{t('quyTrinh.chonDonVi')}</option>
              {dsDonVi.duLieu?.map((d) => <option key={d.id} value={String(d.id)}>{d.ten}</option>)}
            </select>
          </TruongNhap>
        )}
      </div>
      <div className="space-y-3 max-h-[52vh] overflow-y-auto pr-1">
        <div className="flex items-center gap-2 text-sm font-bold text-main">
          {t('quyTrinh.capKy')} <span className="text-danger" aria-label={t('chung.batBuoc')}>*</span>
        </div>
        {dsChucVu.loi && <p className="text-xs text-danger">{loi(dsChucVu.loi)}</p>}
        {dsChucVu.duLieu && dsChucVu.duLieu.length === 0 && (
          <p className="text-xs text-muted">{t('quyTrinh.khongCoChucVu')}</p>
        )}
        {cap.map((c, i) => (
          <div key={i} className="space-y-2 rounded-lg border border-border-subtle p-2">
            <div className="flex gap-2">
              <span className="pt-2 text-sm font-bold text-main shrink-0">{i + 1}.</span>
              <select
                className={LOP_O_NHAP}
                aria-label={`${t('quyTrinh.tenCap')} ${i + 1} (${t('chung.batBuoc')})`}
                value={c.ten_cap_ky}
                disabled={dsChucVu.dangTai && !dsChucVu.duLieu}
                onChange={(e) => sua(i, { ten_cap_ky: e.target.value })}
              >
                <option value="">
                  {dsChucVu.dangTai && !dsChucVu.duLieu ? t('chung.dangTai') : t('quyTrinh.chonChucVuCapKy')}
                </option>
                {c.ten_cap_ky && !dsChucVu.duLieu?.some((cv) => cv.name === c.ten_cap_ky) && (
                  <option value={c.ten_cap_ky}>
                    {c.ten_cap_ky} ({t('quyTrinh.tenNgoaiDanhMuc')})
                  </option>
                )}
                {dsChucVu.duLieu?.map((cv) => (
                  <option key={cv.id} value={cv.name}>{cv.name}</option>
                ))}
              </select>
              <input className={`${LOP_O_NHAP} w-32`} inputMode="numeric" placeholder={t('quyTrinh.soGio')} maxLength={4}
                aria-label={`${t('quyTrinh.soGio')} ${i + 1}`} value={c.so_gio_xu_ly}
                aria-invalid={soGioQuaLon(c) ? true : undefined}
                onChange={(e) => sua(i, { so_gio_xu_ly: e.target.value.replace(/\D/g, '') })} />
              {cap.length > 1 && (
                <button type="button" className="px-1 text-danger cursor-pointer" aria-label={`${t('quyTrinh.xoaCap')} ${i + 1}`}
                  title={t('quyTrinh.xoaCap')} onClick={() => setCap((x) => x.filter((_, j) => j !== i))}>
                  <i className="fa-solid fa-trash" aria-hidden="true" />
                </button>
              )}
            </div>
            {soGioQuaLon(c) && (
              <p role="alert" className="text-xs font-semibold text-danger">{t('quyTrinh.loiSoGio', { so: GIOI_HAN.soGio })}</p>
            )}
            {c.nguoi_ky.map((n, j) => (
              <div key={n.khoa} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-main">
                  <span className="font-semibold">{n.ten}</span>
                  {n.chuc_danh && <span className="ml-1 text-xs text-secondary">({n.chuc_danh})</span>}
                </span>
                {n.vai_tro_ky === 'KY_NHAY' && <span className="text-danger">{t('vaiTro.KY_NHAY')}</span>}
                <button type="button" className="text-danger" aria-label={t('quyTrinh.boNguoiKy')}
                  onClick={() => sua(i, { nguoi_ky: c.nguoi_ky.filter((_, k) => k !== j) })}>
                  <i className="fa-solid fa-trash" aria-hidden="true" />
                </button>
                {n.chuc_vu_id != null && (
                  <div className="basis-full pl-1">
                    <CanBoChucVu chucVuId={n.chuc_vu_id}
                      donViId={donViTimCanBo(n.pham_vi_chuc_vu, c.don_vi_id, phamVi, donViApDung)}
                      theoNguoiTrinh={n.pham_vi_chuc_vu === 'DON_VI_NGUOI_TAO' && phamVi !== 'PHONG_BAN'} />
                  </div>
                )}
              </div>
            ))}
            <ThemNguoiKyCap
              chucVuCapKy={dsChucVu.duLieu?.find((cv) => cv.name === c.ten_cap_ky) ?? null}
              donViTim={(pham_vi) => donViTimCanBo(pham_vi, c.don_vi_id, phamVi, donViApDung)}
              onChonCanBo={(u: CanBo) => !c.nguoi_ky.some((n) => n.nguoi_ky === u.id)
                && sua(i, { nguoi_ky: [...c.nguoi_ky, {
                  khoa: `u${u.id}`, ten: u.ho_ten, chuc_danh: chucDanh(u, ''), nguoi_ky: u.id, chuc_vu_id: null, pham_vi_chuc_vu: null,
                  vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true,
                }] })}
              onChonChucVu={(cv, pham_vi) => !c.nguoi_ky.some((n) => n.chuc_vu_id === cv.id && n.pham_vi_chuc_vu === pham_vi)
                && sua(i, { nguoi_ky: [...c.nguoi_ky, {
                  khoa: `p${cv.id}-${pham_vi}`, ten: t('quyTrinh.theoChucVu', { ten: cv.ten }), chuc_danh: t(`phamViChucVu.${pham_vi}`),
                  nguoi_ky: null, chuc_vu_id: cv.id, pham_vi_chuc_vu: pham_vi, vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true,
                }] })}
            />
          </div>
        ))}
        <Button size="sm" variant="ghost" icon="fa-plus"
          onClick={() => setCap((c) => [...c, CAP_TRONG])}>{t('quyTrinh.themCap')}</Button>
      </div>
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
      {!hopLe && <ThongBao loai="canh_bao">
        <span>{t('quyTrinh.luuBiKhoa')}</span>
        <ul className="mt-1 list-disc pl-5">{lyDoChuaLuu.map((lyDo) => <li key={lyDo}>{lyDo}</li>)}</ul>
      </ThongBao>}
    </HopThoai>
  );
}

function ChiTietQuyTrinh({
  id,
  quanLy = false,
  onDong,
  onSua,
  onNhanBan,
}: {
  id: number;
  quanLy?: boolean;
  onDong: () => void;
  onSua?: (q: QuyTrinh) => void;
  onNhanBan?: (q: QuyTrinh) => void;
}) {
  const { t, loi } = useSigningT();
  const ct = useTai(() => signingApi.chiTietQuyTrinh(id), [id]);
  const q = ct.duLieu;
  return (
    <HopThoai moTieuDe={t('quyTrinh.chiTiet')} mo onDong={onDong}
      chanDuoi={
        <div className="flex w-full items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {quanLy && q?.trang_thai === 'NHAP' && onSua && (
              <Button size="sm" icon="fa-pen" onClick={() => onSua(q)}>{t('quyTrinh.sua')}</Button>
            )}
            {quanLy && q && (q.trang_thai === 'HOAT_DONG' || q.trang_thai === 'NGUNG') && onNhanBan && (
              <Button size="sm" variant="secondary" icon="fa-copy" onClick={() => onNhanBan(q)}>{t('quyTrinh.nhanBan')}</Button>
            )}
          </div>
          <Button variant="secondary" onClick={onDong}>{t('chung.dong')}</Button>
        </div>
      }>
      {ct.dangTai && <DangTai />}
      {ct.loi && <LoiTai thongBao={loi(ct.loi)} onThuLai={ct.tai} />}
      {q && (
        <div className="space-y-3 text-sm">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <dt className="text-secondary">{t('quyTrinh.ten')}</dt><dd className="text-main">{q.ten_quy_trinh}</dd>
            <dt className="text-secondary">{t('quyTrinh.phienBanNhan')}</dt><dd className="text-main">{q.phien_ban}</dd>
            <dt className="text-secondary">{t('danhSach.trangThai')}</dt><dd><TrangThaiBadge trangThai={q.trang_thai} /></dd>
            <dt className="text-secondary">{t('quyTrinh.phamVi')}</dt>
            <dd className="text-main">{t(`phamVi.${q.pham_vi}`)}{q.pham_vi === 'PHONG_BAN' ? ` · ${q.ten_don_vi_ap_dung || t('quyTrinh.donViChuaXacDinh')}` : ''}</dd>
            {q.mo_ta && <><dt className="text-secondary">{t('quyTrinh.moTa')}</dt><dd className="text-main">{q.mo_ta}</dd></>}
          </dl>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border-subtle bg-surface-subtle text-xs font-bold uppercase tracking-wider text-muted">
                <th className="px-3 py-2 text-center">{t('quyTrinh.thuTu')}</th>
                <th className="px-3 py-2 text-center">{t('quyTrinh.capKy')}</th>
                <th className="px-3 py-2 text-center">{t('quyTrinh.nguoiKy')}</th>
                <th className="px-3 py-2 text-center">{t('quyTrinh.soGioNhan')}</th>
              </tr>
            </thead>
            <tbody>
              {q.cap_ky.map((c) => (
                <tr key={c.id} className="border-b border-border-subtle hover:bg-surface-hover align-top">
                  <td className="px-3 py-2.5 font-bold text-main text-center">{c.thu_tu}</td>
                  <td className="px-3 py-2.5 text-main font-medium">{c.ten_cap_ky}</td>
                  <td className="px-3 py-2.5">
                    <ul className="space-y-0.5">
                      {c.nguoi_ky.map((n) => (
                        <li key={n.id} className="text-main">
                          {tenNguoiKyCauHinh(n, t)}
                          <span className="ml-1 text-secondary">({t(`vaiTro.${n.vai_tro_ky}`)}
                            {n.vai_tro_ky === 'KY_NHAY' && n.chan_ky_chinh ? ` · ${t('quyTrinh.chanKyChinh')}` : ''})</span>
                          {n.chuc_vu_id != null && (
                            <CanBoChucVu chucVuId={n.chuc_vu_id}
                              donViId={donViTimCanBo(n.pham_vi_chuc_vu, c.don_vi_id, q.pham_vi, q.don_vi_ap_dung_id)}
                              theoNguoiTrinh={n.pham_vi_chuc_vu === 'DON_VI_NGUOI_TAO' && q.pham_vi !== 'PHONG_BAN'} />
                          )}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="px-3 py-2.5 text-secondary text-center">{c.so_gio_xu_ly ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </HopThoai>
  );
}

export default function QuyTrinhPage() {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const ds = useTai(() => signingApi.quyTrinh());
  const [tim, setTim] = useState('');
  // Mặc định ẩn phiên bản đã ngừng để không xen giữa bản đang dùng cùng tên
  const [locTrangThai, setLocTrangThai] = useState('CON_DUNG');
  const [locPhamVi, setLocPhamVi] = useState('');
  const tuKhoa = boDau(tim.trim());
  const hienThi = (ds.duLieu ?? []).filter((q) => (!locTrangThai || q.trang_thai === locTrangThai
      || (locTrangThai === 'CON_DUNG' && q.trang_thai !== 'NGUNG'))
    && (!locPhamVi || q.pham_vi === locPhamVi)
    && (!tuKhoa || [q.ma_quy_trinh, q.ten_quy_trinh, q.ten_don_vi_ap_dung ?? ''].some((x) => boDau(x).includes(tuKhoa))));
  const [taoMo, setTaoMo] = useState(false);
  const [cauHinhUyQuyen, setCauHinhUyQuyen] = useState(false);
  const [dangSua, setDangSua] = useState<QuyTrinh | null>(null);
  const [xemId, setXemId] = useState<number | null>(null);
  const [canXoa, setCanXoa] = useState<QuyTrinh | null>(null);
  const [canNgung, setCanNgung] = useState<QuyTrinh | null>(null);
  const [dangThaoTac, setDangThaoTac] = useState(false);
  const [thongBao, setThongBao] = useState('');
  const quanLy = coQuyen(toi, 'manage_signing_process');

  // Mỗi lần bấm là một thao tác: nhấn đúp "Tạo phiên bản mới" không được sinh hai phiên bản
  const thaoTac = async (q: QuyTrinh, loai: 'kich-hoat' | 'ngung' | 'nhan-ban') => {
    if (dangThaoTac) return;
    setDangThaoTac(true);
    setThongBao('');
    try {
      const banMoi = await signingApi.thaoTacQuyTrinh(q.id, loai);
      if (loai === 'nhan-ban' && banMoi) {
        setDangSua(banMoi);
      }
      ds.tai();
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangThaoTac(false);
    }
  };

  const xoa = async (q: QuyTrinh) => {
    setCanXoa(null);
    if (dangThaoTac) return;
    setDangThaoTac(true);
    setThongBao('');
    try {
      await signingApi.xoaQuyTrinh(q.id);
      ds.tai();
    } catch (err) {
      const l = docLoi(err);
      const so = (l.fields?.so_ho_so as number[] | undefined)?.[0];
      setThongBao(l.code === 'quy_trinh_da_duoc_dung' && so ? t('quyTrinh.xoaKhongDuoc', { so }) : loi(err));
      ds.tai();
    } finally {
      setDangThaoTac(false);
    }
  };

  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex min-w-48 flex-1 flex-col gap-1.5 text-xs font-semibold text-secondary">
            <span><i className="fa-solid fa-magnifying-glass text-primary text-xs mr-1" aria-hidden="true" />{t('danhSach.timKiem')}</span>
            <input className={LOP_O_NHAP} type="search" value={tim} placeholder={t('quyTrinh.goiYTim')} onChange={(e) => setTim(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1.5 text-xs font-semibold text-secondary">
            <span><i className="fa-solid fa-filter text-primary text-xs mr-1" aria-hidden="true" />{t('danhSach.trangThai')}</span>
            <select className={`${LOP_O_NHAP} w-auto`} value={locTrangThai} onChange={(e) => setLocTrangThai(e.target.value)}>
              <option value="CON_DUNG">{t('quyTrinh.conDung')}</option>
              <option value="">{t('danhSach.tatCa')}</option>
              {['NHAP', 'HOAT_DONG', 'NGUNG'].map((s) => <option key={s} value={s}>{t(`trangThai.${s}`)}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-xs font-semibold text-secondary">
            <span><i className="fa-solid fa-diagram-project text-primary text-xs mr-1" aria-hidden="true" />{t('quyTrinh.phamVi')}</span>
            <select className={`${LOP_O_NHAP} w-auto`} value={locPhamVi} onChange={(e) => setLocPhamVi(e.target.value)}>
              <option value="">{t('danhSach.tatCa')}</option>
              <option value="CONG_TY">{t('phamVi.CONG_TY')}</option>
              <option value="PHONG_BAN">{t('phamVi.PHONG_BAN')}</option>
            </select>
          </label>
          {quanLy && toi?.la_quan_tri && <Button variant="secondary" onClick={() => setCauHinhUyQuyen(true)}>{t('uyQuyenCauHinh')}</Button>}
          {quanLy && <Button className="ml-auto" icon="fa-plus" onClick={() => setTaoMo(true)}>{t('quyTrinh.tao')}</Button>}
        </div>
      </Card>
      {!quanLy && <ThongBao loai="thong_tin">{t('quyTrinh.chiQuanLy')}</ThongBao>}
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
      {ds.dangTai && <DangTai />}
      {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
      {ds.duLieu && hienThi.length === 0 && (
        <Rong icon="fa-diagram-project">{t(ds.duLieu.length ? 'quyTrinh.khongKhopLoc' : 'quyTrinh.rong')}</Rong>
      )}
      <div className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(min(100%,22rem),1fr))]">
        {hienThi.map((q) => (
          <Card key={q.id} className="flex flex-col gap-3 p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="min-w-0 break-words text-lg font-bold text-main">{q.ten_quy_trinh}</span>
              <div className="flex items-center gap-1.5">
                <TrangThaiBadge trangThai={q.trang_thai} />
                <Badge variant="info" size="sm">{t(`phamVi.${q.pham_vi}`)}{q.pham_vi === 'PHONG_BAN' ? ` · ${q.ten_don_vi_ap_dung || t('quyTrinh.donViChuaXacDinh')}` : ''}</Badge>
              </div>
            </div>
            <div className="text-xs text-muted">{t('quyTrinh.phienBan', { so: q.phien_ban })}</div>
            <ol className="space-y-1 text-sm">
              {q.cap_ky.map((c) => (
                <li key={c.id} className="break-words text-main">
                  {c.cap_ky}. {c.ten_cap_ky}:{' '}
                  <span className="text-secondary">
                    {c.nguoi_ky.map((n) => `${tenNguoiKyCauHinh(n, t)} (${t(`vaiTro.${n.vai_tro_ky}`)})`).join(', ')}
                  </span>
                </li>
              ))}
            </ol>
            {/* mt-auto: hàng nút nằm cùng đáy giữa các thẻ cao khác nhau */}
            <div className="mt-auto flex flex-wrap gap-2 pt-1">
              <Button size="sm" variant="ghost" icon="fa-eye" onClick={() => setXemId(q.id)}>{t('quyTrinh.xemChiTiet')}</Button>
              {quanLy && q.trang_thai === 'NHAP' && (
                <>
                  <Button size="sm" icon="fa-play" disabled={dangThaoTac} onClick={() => thaoTac(q, 'kich-hoat')}>{t('quyTrinh.kichHoat')}</Button>
                  <Button size="sm" variant="secondary" icon="fa-pen" onClick={() => setDangSua(q)}>{t('quyTrinh.sua')}</Button>
                </>
              )}
              {quanLy && (
                <>
                {q.trang_thai === 'HOAT_DONG' && <Button size="sm" variant="secondary" icon="fa-stop" disabled={dangThaoTac} onClick={() => setCanNgung(q)}>{t('quyTrinh.ngung')}</Button>}
                <Button size="sm" variant="ghost" icon="fa-copy" disabled={dangThaoTac} onClick={() => thaoTac(q, 'nhan-ban')}>{t('quyTrinh.nhanBan')}</Button>
                <Button size="sm" variant="ghost" icon="fa-trash" disabled={q.so_ho_so > 0}
                  title={q.so_ho_so > 0 ? t('quyTrinh.xoaKhongDuoc', { so: q.so_ho_so }) : undefined}
                  onClick={() => setCanXoa(q)}>{t('quyTrinh.xoa')}</Button>
                </>
              )}
            </div>
            {quanLy && q.so_ho_so > 0 && (
              <p className="text-xs text-muted"><i className="fa-solid fa-lock mr-1" aria-hidden="true" />{t('quyTrinh.xoaKhongDuoc', { so: q.so_ho_so })}</p>
            )}
          </Card>
        ))}
      </div>
      {taoMo && <FormTao mo={taoMo} onDong={() => setTaoMo(false)} onXong={() => { setTaoMo(false); ds.tai(); }} />}
      {cauHinhUyQuyen && <CauHinhUyQuyen onDong={() => setCauHinhUyQuyen(false)} />}
      {dangSua && (
        <FormTao key={dangSua.id} mo banDau={dangSua} onDong={() => setDangSua(null)} onXong={() => { setDangSua(null); ds.tai(); }} />
      )}
      {xemId !== null && (
        <ChiTietQuyTrinh
          id={xemId}
          quanLy={quanLy}
          onDong={() => setXemId(null)}
          onSua={(q) => {
            setXemId(null);
            setDangSua(q);
          }}
          onNhanBan={(q) => {
            setXemId(null);
            thaoTac(q, 'nhan-ban');
          }}
        />
      )}
      {canNgung && (
        <HopThoai moTieuDe={t('quyTrinh.ngung')} mo onDong={() => setCanNgung(null)}
          chanDuoi={<>
            <Button variant="secondary" onClick={() => setCanNgung(null)}>{t('chung.huyBo')}</Button>
            <Button icon="fa-stop" onClick={() => { const q = canNgung; setCanNgung(null); thaoTac(q, 'ngung'); }}>{t('chung.xacNhan')}</Button>
          </>}>
          <p className="text-sm text-main">{t('quyTrinh.xacNhanNgung', { ten: canNgung.ten_quy_trinh, phienBan: canNgung.phien_ban })}</p>
        </HopThoai>
      )}
      {canXoa && (
        <HopThoai moTieuDe={t('quyTrinh.xoa')} mo onDong={() => setCanXoa(null)}
          chanDuoi={<>
            <Button variant="secondary" onClick={() => setCanXoa(null)}>{t('chung.huyBo')}</Button>
            <Button icon="fa-trash" onClick={() => xoa(canXoa)}>{t('chung.xacNhan')}</Button>
          </>}>
          <p className="text-sm text-main">{t('quyTrinh.xacNhanXoa', { ten: canXoa.ten_quy_trinh, phienBan: canXoa.phien_ban })}</p>
        </HopThoai>
      )}
    </div>
  );
}
