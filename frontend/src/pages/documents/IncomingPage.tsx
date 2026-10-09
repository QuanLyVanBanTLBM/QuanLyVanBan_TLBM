import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from '@i18n/translate';
import { DocumentItem, PaginatedResponse } from '@app-types/document';
import DocumentFormModal from '@components/documents/DocumentFormModal';
import ImportExcelModal from '@components/documents/ImportExcelModal';
import apiClient from '@lib/apiClient';
import { Button } from '@components/common';
import AlertModal from '@components/common/AlertModal';
import ConfirmModal from '@components/common/ConfirmModal';

interface IncomingDocument extends DocumentItem {
  don_vi_nhan?: string;
  tac_gia?: string;
  author?: { username?: string };
  ghi_chu?: string;
}

export default function IncomingPage(){
  const { t } = useTranslation();
  const [openForm, setOpenForm] = useState(false);
  const [openImport, setOpenImport] = useState(false);
  const [list, setList] = useState<IncomingDocument[]>([]);
  const [initialDoc, setInitialDoc] = useState<IncomingDocument | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number|null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);

  useEffect(() => { void fetchList(); }, []);
  async function fetchList() {
    try {
      const data = await apiClient.get<PaginatedResponse<IncomingDocument> | IncomingDocument[]>('/api/documents/?loai=DEN');
      setList(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error(error);
    }
  }

  const filteredList = useMemo(() => {
    const fromTime = dateFrom ? new Date(`${dateFrom}T00:00:00`).getTime() : null;
    const toTime = dateTo ? new Date(`${dateTo}T23:59:59.999`).getTime() : null;
    return list.filter((document) => {
      const receivedTime = document.ngay_den ? new Date(document.ngay_den).getTime() : null;
      if (receivedTime === null || Number.isNaN(receivedTime)) return false;
      if (fromTime !== null && receivedTime < fromTime) return false;
      if (toTime !== null && receivedTime > toTime) return false;
      return true;
    });
  }, [list, dateFrom, dateTo]);

  function handleDelete(id?: number) {
    if (!id) return;
    // show confirm modal via state
    setPendingDelete(id);
  }

  async function doDelete(id: number) {
    try {
      await apiClient.delete(`/api/documents/${id}/`);
      setPendingDelete(null);
      fetchList();
    } catch (err: unknown) {
      console.error(err);
      setPendingDelete(null);
      // show inline alert modal instead of native alert
      setGlobalAlertMsg(err instanceof Error ? err.message : 'Không thể xóa văn bản');
      setGlobalAlertOpen(true);
    }
  }

  const [globalAlertOpen, setGlobalAlertOpen] = useState(false);
  const [globalAlertMsg, setGlobalAlertMsg] = useState('');

  async function handleExportExcel() {
    try {
      if (import.meta.env.DEV && !localStorage.getItem('tlbm_access_token')) {
        setGlobalAlertMsg('Tính năng xuất Excel cần kết nối máy chủ Backend để xử lý dữ liệu. Hiện tại hệ thống đang chạy ở chế độ offline.');
        setGlobalAlertOpen(true);
        return;
      }
      const res = await fetch('/api/documents/export/?loai=DEN');
      if (!res.ok) throw new Error('Quá trình xuất Excel thất bại. Vui lòng thử lại sau!');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'export.xlsx'; a.click(); URL.revokeObjectURL(url);
    } catch (error: unknown) {
      setGlobalAlertMsg(error instanceof Error ? error.message : String(error));
      setGlobalAlertOpen(true);
    }
  }

  return (
    <div className="p-4">
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">{t('documents_incoming_page.pageTitle')}</h2>
          <div className="flex items-center gap-2">
            <input placeholder={t('documents_incoming_page.searchTitle')} className="border rounded p-2 text-sm w-80" />
            <input value={dateFrom||''} onChange={e=>setDateFrom(e.target.value || null)} type="date" className="border rounded p-2 text-sm search-date search-date-compact" />
            <input value={dateTo||''} onChange={e=>setDateTo(e.target.value || null)} type="date" className="border rounded p-2 text-sm search-date search-date-compact" />
            <select className="border rounded p-2 text-sm">
              <option>{t('documents_incoming_page.year')}</option>
              <option>2026</option>
              <option>2025</option>
            </select>
            <Button variant="primary" onClick={() => void fetchList()}>{t('documents_incoming_page.searchBtn')}</Button>
          </div>
        </div>

        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center gap-3">
            <Button variant="primary" onClick={()=>{ setInitialDoc(null); setOpenForm(true); }}>{t('documents_incoming_page.addBtn')}</Button>
            <Button variant="secondary" onClick={()=>setOpenImport(true)}>{t('documents_incoming_page.importBtn')}</Button>
            <Button variant="secondary" onClick={handleExportExcel}>{t('documents_incoming_page.exportBtn')}</Button>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm">{t('documents_incoming_page.viewing')}</div>
            <select className="border rounded p-1 text-sm">
              <option>10</option>
              <option>25</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white rounded shadow overflow-auto">
        <table className="w-full table-fixed border-collapse text-sm border border-gray-200">
          <thead>
            <tr className="bg-gray-100 text-sm text-left">
              <th className="p-3 w-20 border border-gray-200">{t('documents_incoming_page.colAction')}</th>
              <th className="p-3 w-28 border border-gray-200">{t('documents_incoming_page.colIncomingDate')}</th>
              <th className="p-3 w-20 border border-gray-200">{t('documents_incoming_page.colIncomingNum')}</th>
              <th className="p-3 border border-gray-200">{t('documents_incoming_page.colOfficer')}</th>
              <th className="p-3 border border-gray-200">{t('documents_incoming_page.colRefNum')}</th>
              <th className="p-3 w-36 border border-gray-200">{t('documents_incoming_page.colDocDate')}</th>
              <th className="p-3 border border-gray-200">{t('documents_incoming_page.colTypeSummary')}</th>
              <th className="p-3 w-48 border border-gray-200">{t('documents_incoming_page.colRecipient')}</th>
              <th className="p-3 w-36 border border-gray-200">{t('documents_incoming_page.colIssueDate')}</th>
              <th className="p-3 w-36 border border-gray-200">{t('documents_incoming_page.colNotes')}</th>
            </tr>
          </thead>
          <tbody>
            {filteredList.map((d, idx)=> (
              <tr key={d.id || idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="p-3 border border-gray-200 align-top text-sm">
                  <div className="flex gap-2">
                    <button title="Sửa" onClick={()=>{ setInitialDoc(d); setOpenForm(true); }} className="text-blue-600">✏️</button>
                    <button title="Xóa" onClick={()=>handleDelete(d.id)} className="text-red-600">❌</button>
                    <button title="Tệp" className="text-gray-600">📎</button>
                    <button title="Hồ sơ" className="text-gray-600">🗂️</button>
                  </div>
                </td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.ngay_den ? new Date(d.ngay_den).toLocaleDateString() : '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.so_thu_tu ?? '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.tac_gia || (d.author && d.author.username) || '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.so_hieu || '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.ngay_van_ban ? new Date(d.ngay_van_ban).toLocaleDateString() : '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm text-blue-600 underline">{d.trich_yeu || '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.noi_ban_hanh || d.don_vi_nhan || '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{(d.ngay_ban_hanh || d.ngay_van_ban) ? new Date(d.ngay_ban_hanh || d.ngay_van_ban).toLocaleDateString('vi-VN') : '-'}</td>
                <td className="p-3 border border-gray-200 align-top text-sm">{d.ghi_chu || ''}</td>
              </tr>
            ))}
            {list.length===0 && (
              <tr><td colSpan={10} className="p-6 text-center text-sm text-gray-500">{t('documents_incoming_page.noData')}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <DocumentFormModal open={openForm} initial={initialDoc||undefined} onClose={()=>{ setOpenForm(false); setInitialDoc(null); }} onSaved={(savedData)=>{
        setOpenForm(false);
        setInitialDoc(null);
        if (import.meta.env.DEV && !localStorage.getItem('tlbm_access_token') && savedData) {
          // Mock cập nhật list ở frontend
          const savedDocument = savedData as IncomingDocument;
          setList(prev => {
            const exists = prev.find(item => item.id === savedDocument.id);
            if (exists) return prev.map(item => item.id === savedDocument.id ? savedDocument : item);
            return [savedDocument, ...prev];
          });
        } else {
          fetchList(); 
        }
      }} />
      <ImportExcelModal open={openImport} onClose={()=>setOpenImport(false)} onImported={()=>{ setOpenImport(false); fetchList(); }} />
      <AlertModal open={globalAlertOpen} onClose={()=>setGlobalAlertOpen(false)} message={globalAlertMsg} />
      <ConfirmModal open={!!pendingDelete} title="Xác nhận xóa văn bản này?" message="Bạn có chắc muốn xóa văn bản đã chọn? Hành động này không thể hoàn tác." confirmText="Xóa" cancelText="Hủy" onConfirm={()=>{ if (pendingDelete) doDelete(pendingDelete); }} onCancel={()=>setPendingDelete(null)} />
    </div>
  );
}
