/** Tiện ích hiển thị dùng chung của phân hệ Trình ký. */

export const LOP_O_NHAP =
  'w-full rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main placeholder:text-muted ' +
  'focus:outline-none focus:border-focus focus:ring-2 focus:ring-primary-subtle';

export function dinhDangNgay(iso: string | null | undefined, lang: 'vi' | 'en'): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-GB', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

export function moTaVanBan(vb: { so_hieu?: string; trich_yeu?: string } | undefined, van_ban_id: number): string {
  const phan = [vb?.so_hieu, vb?.trich_yeu].filter(Boolean);
  return phan.length ? phan.join(' — ') : `#${van_ban_id}`;
}

export function taiXuong(blob: Blob, ten: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = ten;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
