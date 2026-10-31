import React, { useState, useEffect, useMemo, useRef, useCallback, ChangeEvent, FormEvent } from 'react';
import { createPortal } from 'react-dom';
import {
  ResourceItem,
  ResourceCategory,
  ResourceType,
  ResourceAttachment,
  HieuLucType,
  HienThiType,
} from '@app-types/resource';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';
import { authService } from '@lib/authService';
import { usePermissions } from '@lib/permissions';
import { formatDate } from '@lib/dateUtils';
import { ConfirmationModal } from './ConfirmationModal';
import { apiClientBlob, downloadBlob } from '@lib/apiClient';
import { FilePreviewModal } from './FilePreviewModal';

export interface ResourceFormData {
  dm_tai_lieu: number | '';
  loai_tai_lieu: number[];
  ky_hieu: string;
  tieu_de: string;
  ngay_dang: string;
  noi_ban_hanh: string;
  nguoi_tao_name?: string;
  hieu_luc: HieuLucType;
  ngay_het_hieu_luc: string;
  link_thay_the: string;
  ghi_chu: string;
  hien_thi: HienThiType;
  file?: File | null;
  files?: File[];
  deleted_attachment_ids?: number[];
}

export interface ResourceFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    formData: FormData;
    payload: ResourceFormData;
  }) => Promise<void> | void;
  initialData?: ResourceItem | null;
  categories?: ResourceCategory[];
  types?: ResourceType[];
  isLoading?: boolean;
  defaultCategoryId?: number;
}

const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = [
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.csv',
  '.jpg',
  '.jpeg',
  '.png',
  '.zip',
  '.rar',
];

const getFileDisplay = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return {
        icon: 'fa-solid fa-file-pdf',
        color: 'text-red-500',
        bg: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900/50',
      };
    case 'xls':
    case 'xlsx':
    case 'csv':
      return {
        icon: 'fa-solid fa-file-excel',
        color: 'text-emerald-600 dark:text-emerald-400',
        bg: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/50',
      };
    case 'doc':
    case 'docx':
      return {
        icon: 'fa-solid fa-file-word',
        color: 'text-blue-600 dark:text-blue-400',
        bg: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900/50',
      };
    case 'png':
    case 'jpg':
    case 'jpeg':
      return {
        icon: 'fa-solid fa-file-image',
        color: 'text-purple-600 dark:text-purple-400',
        bg: 'bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-900/50',
      };
    case 'zip':
    case 'rar':
      return {
        icon: 'fa-solid fa-file-zipper',
        color: 'text-amber-600 dark:text-amber-400',
        bg: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/50',
      };
    default:
      return {
        icon: 'fa-solid fa-file',
        color: 'text-gray-500',
        bg: 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700',
      };
  }
};

const formatSize = (bytes?: number) => {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const getTodayLocalDateString = (): string => {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const ResourceFormModal: React.FC<ResourceFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  categories = [],
  types = [],
  isLoading = false,
  defaultCategoryId,
}) => {
  const { t } = useTranslation();
  const isEditMode = Boolean(initialData);

  const currentSession = authService.getSession();
  const isSessionAdmin = currentSession?.role === 'admin' || currentSession?.username === 'admin';
  const { can, isSuperuser } = usePermissions();
  const canAdd = isSuperuser || isSessionAdmin || can('add_tailieu');
  const canEdit = isSuperuser || isSessionAdmin || can('change_tailieu') || Boolean(
    initialData && (
      (currentSession?.fullName && initialData.nguoi_tao_name === currentSession.fullName) ||
      (currentSession?.username && initialData.nguoi_tao_name === currentSession.username)
    )
  );
  const canSubmit = isEditMode ? canEdit : canAdd;

  const defaultAuthor =
    currentSession?.fullName ||
    currentSession?.username ||
    'Quản trị hệ thống';

  const prevIsOpenRef = useRef(false);
  const prevInitialDataIdRef = useRef<number | undefined>(undefined);

  // Custom Dropdown State cho Thư mục
  const [isCategoryDropdownOpen, setIsCategoryDropdownOpen] = useState(false);
  const [categorySearch, setCategorySearch] = useState('');
  const categoryDropdownRef = useRef<HTMLDivElement>(null);
  const categoryButtonRef = useRef<HTMLButtonElement>(null);
  const categoryMenuRef = useRef<HTMLDivElement>(null);
  const [categoryMenuPos, setCategoryMenuPos] = useState<{
    top?: number;
    bottom?: number;
    left: number;
    width: number;
    maxHeight: number;
  } | null>(null);

  // Cập nhật vị trí fixed cho Dropdown Thư mục trong ResourceFormModal
  const updateCategoryMenuPos = useCallback(() => {
    if (!categoryButtonRef.current) return;
    const rect = categoryButtonRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    const desiredHeight = 248; // Đủ cho ô tìm kiếm (~45px) + tối đa 5 mục thư mục (~180px) + padding (~15px)
    const minHeight = 120;

    let top: number | undefined;
    let bottom: number | undefined;
    let maxHeight: number;

    if (spaceBelow >= 230 || spaceBelow >= spaceAbove) {
      top = rect.bottom + 6;
      maxHeight = Math.min(desiredHeight, Math.max(minHeight, spaceBelow - 16));
    } else {
      bottom = window.innerHeight - rect.top + 6;
      maxHeight = Math.min(desiredHeight, Math.max(minHeight, spaceAbove - 16));
    }

    const buttonWidth = rect.width > 0 ? rect.width : (categoryButtonRef.current.offsetWidth || 320);
    const width = Math.min(buttonWidth, window.innerWidth - 16);
    const left = rect.left > 0 ? Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)) : 10;

    setCategoryMenuPos({
      top,
      bottom,
      left,
      width,
      maxHeight,
    });
  }, []);

  // Form State
  const [formData, setFormData] = useState<ResourceFormData>(() => {
    const initialCatId =
      defaultCategoryId && categories.some((c) => c.id === defaultCategoryId)
        ? defaultCategoryId
        : categories.length > 0
        ? categories[0].id
        : '';
    return {
      dm_tai_lieu: initialCatId,
      loai_tai_lieu: [],
      ky_hieu: '',
      tieu_de: '',
      ngay_dang: new Date().toISOString().split('T')[0],
      noi_ban_hanh: '',
      nguoi_tao_name: defaultAuthor,
      hieu_luc: 'CON_HIEU_LUC',
      ngay_het_hieu_luc: '',
      link_thay_the: '',
      ghi_chu: '',
      hien_thi: 'TAT_CA',
      file: null,
      files: [],
    };
  });

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [existingFiles, setExistingFiles] = useState<
    { id?: number; name: string; size?: number; path?: string }[]
  >([]);
  const [deletedAttachmentIds, setDeletedAttachmentIds] = useState<number[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isConfirmDiscardOpen, setIsConfirmDiscardOpen] = useState(false);
  const [previewAttachment, setPreviewAttachment] = useState<ResourceAttachment | null>(null);


  const fileInputRef = useRef<HTMLInputElement>(null);

  // Khởi tạo form khi mở modal - CHỈ chạy một lần khi modal vừa mở, KHÔNG ghi đè khi polling nạp lại categories
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    if (isOpen) {
      const justOpened = !prevIsOpenRef.current || prevInitialDataIdRef.current !== initialData?.id;
      prevIsOpenRef.current = true;
      prevInitialDataIdRef.current = initialData?.id;

      if (justOpened) {
        if (initialData) {
          setFormData({
            dm_tai_lieu: initialData.dm_tai_lieu,
            loai_tai_lieu: initialData.loai_tai_lieu || [],
            ky_hieu: initialData.ky_hieu || '',
            tieu_de: initialData.tieu_de || '',
            ngay_dang: initialData.ngay_dang || getTodayLocalDateString(),
            noi_ban_hanh: initialData.noi_ban_hanh || '',
            nguoi_tao_name: initialData.nguoi_tao_name || defaultAuthor,
            hieu_luc: initialData.hieu_luc || 'CON_HIEU_LUC',
            ngay_het_hieu_luc: initialData.ngay_het_hieu_luc || '',
            link_thay_the: initialData.link_thay_the || '',
            ghi_chu: initialData.ghi_chu || '',
            hien_thi: initialData.hien_thi || 'TAT_CA',
            file: null,
            files: [],
          });
          const activeAttachments = (initialData.attachments || []).filter((att) => !att.is_deleted);
          if (activeAttachments.length > 0) {
            setExistingFiles(
              activeAttachments.map((att) => ({
                id: att.id,
                name: att.name,
                size: att.file_size,
                path: att.path,
              }))
            );
          } else if (initialData.file_dinh_kem) {
            const fallbackName =
              initialData.file_dinh_kem.startsWith('blob:')
                ? `${initialData.tieu_de || 'Tệp đính kèm'}.pdf`
                : initialData.file_dinh_kem.split('?')[0].split('/').pop() || 'Tệp đính kèm';
            setExistingFiles([{ name: fallbackName, path: initialData.file_dinh_kem }]);
          } else {
            setExistingFiles([]);
          }
        } else {
          const initialCatId =
            defaultCategoryId && categories.some((c) => c.id === defaultCategoryId)
              ? defaultCategoryId
              : categories.length > 0
              ? categories[0].id
              : '';

          setFormData({
            dm_tai_lieu: initialCatId,
            loai_tai_lieu: [],
            ky_hieu: '',
            tieu_de: '',
            ngay_dang: getTodayLocalDateString(),
            noi_ban_hanh: '',
            nguoi_tao_name: defaultAuthor,
            hieu_luc: 'CON_HIEU_LUC',
            ngay_het_hieu_luc: '',
            link_thay_the: '',
            ghi_chu: '',
            hien_thi: 'TAT_CA',
            file: null,
            files: [],
          });
          setExistingFiles([]);
        }
        setSelectedFiles([]);
        setDeletedAttachmentIds([]);
        setErrors({});
        setFileError(null);
        setIsDirty(false);
        setIsConfirmDiscardOpen(false);
      } else {
        // Modal đã mở sẵn: nếu ban đầu chưa có danh mục nào (rỗng) mà nay categories mới nạp xong
        setFormData((prev) => {
          if (!prev.dm_tai_lieu && categories.length > 0) {
            const initialCatId =
              defaultCategoryId && categories.some((c) => c.id === defaultCategoryId)
                ? defaultCategoryId
                : categories[0].id;
            return { ...prev, dm_tai_lieu: initialCatId };
          }
          return prev;
        });
      }
    } else {
      prevIsOpenRef.current = false;
      prevInitialDataIdRef.current = undefined;
    }
  }, [isOpen, initialData, categories, defaultAuthor, defaultCategoryId]);


  // Đóng an toàn có xác nhận nếu đã chỉnh sửa dữ liệu
  const handleSafeClose = useCallback(() => {
    setIsCategoryDropdownOpen(false);
    setCategorySearch('');
    if (isDirty) {
      setIsConfirmDiscardOpen(true);
      return;
    }
    onClose();
  }, [isDirty, onClose]);

  // Đóng dropdown khi click ra ngoài, cuộn hoặc resize
  useEffect(() => {
    if (!isCategoryDropdownOpen) return;
    updateCategoryMenuPos();

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        categoryDropdownRef.current &&
        !categoryDropdownRef.current.contains(target) &&
        !categoryButtonRef.current?.contains(target) &&
        !categoryMenuRef.current?.contains(target)
      ) {
        setIsCategoryDropdownOpen(false);
        setCategoryMenuPos(null);
        setCategorySearch('');
      }
    };

    const handleScrollOrResize = (e?: Event) => {
      // Nếu sự kiện cuộn xảy ra bên trong chính menu dropdown thì bỏ qua, cho phép người dùng lăn chuột mượt mà
      if (e?.target && categoryMenuRef.current?.contains(e.target as Node)) {
        return;
      }
      if (!categoryButtonRef.current) {
        setIsCategoryDropdownOpen(false);
        setCategoryMenuPos(null);
        setCategorySearch('');
        return;
      }
      const rect = categoryButtonRef.current.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) {
        setIsCategoryDropdownOpen(false);
        setCategoryMenuPos(null);
        setCategorySearch('');
        return;
      }
      updateCategoryMenuPos();
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('resize', handleScrollOrResize);
    window.addEventListener('scroll', handleScrollOrResize, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('resize', handleScrollOrResize);
      window.removeEventListener('scroll', handleScrollOrResize, true);
    };
  }, [isCategoryDropdownOpen, updateCategoryMenuPos]);

  // Lắng nghe phím ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        if (isCategoryDropdownOpen) {
          setIsCategoryDropdownOpen(false);
          setCategoryMenuPos(null);
          setCategorySearch('');
          return;
        }
        if (isConfirmDiscardOpen) return;
        handleSafeClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isCategoryDropdownOpen, isConfirmDiscardOpen, handleSafeClose]);

  // Danh sách Thư mục lọc theo từ khóa tìm kiếm trong dropdown
  const filteredCategories = useMemo(() => {
    if (!categorySearch.trim()) return categories;
    const q = categorySearch.trim().toLowerCase();
    return categories.filter((c) =>
      c.ten_tai_lieu.toLowerCase().includes(q) ||
      (c.ky_hieu && c.ky_hieu.toLowerCase().includes(q))
    );
  }, [categories, categorySearch]);

  // Đối tượng Thư mục đang được chọn
  const selectedCategoryObj = useMemo(() => {
    if (!formData.dm_tai_lieu) return null;
    return categories.find((c) => c.id === Number(formData.dm_tai_lieu)) || null;
  }, [categories, formData.dm_tai_lieu]);

  // Danh sách Loại tài liệu theo Thư mục đã chọn (Cascading)
  const availableTypes = useMemo(() => {
    if (!formData.dm_tai_lieu) return [];
    return types.filter((t) => t.dm_tai_lieu === Number(formData.dm_tai_lieu));
  }, [types, formData.dm_tai_lieu]);

  if (!isOpen) return null;
  if (typeof document === 'undefined') return null;

  // Xử lý thay đổi Thư mục (reset Loại tài liệu)
  const handleCategoryChange = (catId: number | '') => {
    setIsDirty(true);
    setIsCategoryDropdownOpen(false);
    setCategorySearch('');
    setFormData((prev) => ({
      ...prev,
      dm_tai_lieu: catId,
      loai_tai_lieu: [],
    }));
    if (errors.dm_tai_lieu) {
      setErrors((prev) => ({ ...prev, dm_tai_lieu: '' }));
    }
  };

  // Xử lý toggle checkbox Loại tài liệu (Multi-select)
  const handleTypeToggle = (typeId: number) => {
    setIsDirty(true);
    setFormData((prev) => {
      const exists = prev.loai_tai_lieu.includes(typeId);
      const next = exists
        ? prev.loai_tai_lieu.filter((id) => id !== typeId)
        : [...prev.loai_tai_lieu, typeId];
      return { ...prev, loai_tai_lieu: next };
    });
    if (errors.loai_tai_lieu) {
      setErrors((prev) => ({ ...prev, loai_tai_lieu: '' }));
    }
  };

  // Xử lý kiểm tra và thêm nhiều file
  const validateAndAddFiles = (newFiles: FileList | File[]) => {
    setFileError(null);
    const fileArray = Array.from(newFiles);
    const validFiles: File[] = [];
    const errMessages: string[] = [];

    for (const file of fileArray) {
      const fileNameLower = file.name.toLowerCase();
      const isAllowedExt = ALLOWED_EXTENSIONS.some((ext) => fileNameLower.endsWith(ext));

      if (!isAllowedExt) {
        errMessages.push(t('resourceManagement.fileInvalidFormat', { name: file.name }));
        continue;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        errMessages.push(t('resourceManagement.fileExceedSize', { name: file.name, max: MAX_FILE_SIZE_MB }));
        continue;
      }

      validFiles.push(file);
    }

    if (errMessages.length > 0) {
      setFileError(errMessages.join(' '));
    }

    if (validFiles.length > 0) {
      setIsDirty(true);
      setSelectedFiles((prev) => {
        const filtered = validFiles.filter(
          (vf) => !prev.some((pf) => pf.name === vf.name && pf.size === vf.size)
        );
        const next = [...prev, ...filtered];
        setFormData((f) => ({ ...f, files: next, file: next[0] || null }));
        return next;
      });
      if (errors.file) {
        setErrors((prev) => ({ ...prev, file: '' }));
      }
    }
  };

  // Chọn file qua input
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Kéo thả file
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const handleRemoveSelectedFile = (index: number) => {
    setIsDirty(true);
    setSelectedFiles((prev) => {
      const next = prev.filter((_, i) => i !== index);
      setFormData((f) => ({ ...f, files: next, file: next[0] || null }));
      return next;
    });
  };

  const handleRemoveExistingFile = (index: number) => {
    setIsDirty(true);
    setExistingFiles((prev) => {
      const target = prev[index];
      if (target?.id) {
        setDeletedAttachmentIds((dIds) => [...dIds, target.id!]);
      }
      return prev.filter((_, i) => i !== index);
    });
  };

  // Xem trước tệp hiện có
  const isDirectPreviewable = (fileName?: string) => {
    if (!fileName) return false;
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp'].includes(ext);
  };

  // Xem trước tệp hiện có: PDF/Ảnh -> mở tab mới; ZIP/DOCX/EXCEL -> tải về máy
  const handlePreviewExistingFile = async (file: { id?: number; name: string; size?: number; path?: string }) => {
    const isPreviewable = isDirectPreviewable(file.name);
    const targetUrl = file.id
      ? `/api/resources/attachments/${file.id}/view/`
      : (file.path || '');

    if (!targetUrl) return;

    if (!isPreviewable) {
      const downloadUrl = file.id
        ? `/api/resources/attachments/${file.id}/download/`
        : targetUrl;
      try {
        await downloadBlob(downloadUrl, file.name);
      } catch (err) {
        console.warn('Lỗi downloadBlob:', err);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = file.name;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
      return;
    }

    try {
      const rawBlob = await apiClientBlob(targetUrl);
      const lower = file.name.toLowerCase();
      let mimeType = rawBlob.type;
      if (lower.endsWith('.pdf')) {
        mimeType = 'application/pdf';
      } else if (lower.endsWith('.png')) {
        mimeType = 'image/png';
      } else if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
        mimeType = 'image/jpeg';
      } else if (lower.endsWith('.webp')) {
        mimeType = 'image/webp';
      } else if (lower.endsWith('.gif')) {
        mimeType = 'image/gif';
      } else if (lower.endsWith('.svg')) {
        mimeType = 'image/svg+xml';
      } else if (lower.endsWith('.bmp')) {
        mimeType = 'image/bmp';
      }
      const viewBlob = mimeType ? new Blob([rawBlob], { type: mimeType }) : rawBlob;
      const blobUrl = window.URL.createObjectURL(viewBlob);
      window.open(blobUrl, '_blank');
    } catch (err) {
      console.error('Lỗi khi mở xem trước tệp:', err);
      window.open(targetUrl, '_blank');
    }
  };

  // Xem trước tệp mới tải lên: PDF/Ảnh -> mở tab mới; ZIP/DOCX/EXCEL -> tải về máy
  const handlePreviewSelectedFile = (file: File) => {
    const isPreviewable = isDirectPreviewable(file.name);
    const objectUrl = URL.createObjectURL(file);

    if (!isPreviewable) {
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      return;
    }

    window.open(objectUrl, '_blank');
  };



  // Validate form trước khi submit
  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.dm_tai_lieu) {
      newErrors.dm_tai_lieu = t('resourceManagement.valSelectCategory');
    }

    if (formData.loai_tai_lieu.length === 0) {
      newErrors.loai_tai_lieu = t('resourceManagement.valSelectType');
    }

    if (!formData.tieu_de.trim()) {
      newErrors.tieu_de = t('resourceManagement.valEnterTitle');
    }


    // Ràng buộc ngày hết hiệu lực không thể trước ngày đăng / ngày tạo
    if (formData.ngay_het_hieu_luc && formData.ngay_dang && formData.ngay_het_hieu_luc < formData.ngay_dang) {
      newErrors.ngay_het_hieu_luc = t('resourceManagement.valExpDateBeforePostDate', {
        date: formatDate(formData.ngay_dang),
      });
    }

    // Ràng buộc nghiêm ngặt khi Hết và thay thế
    if (formData.hieu_luc === 'HET_VA_THAY_THE') {
      if (!formData.ngay_het_hieu_luc) {
        newErrors.ngay_het_hieu_luc = t('resourceManagement.valEnterExpDate');
      }
      if (!formData.link_thay_the.trim()) {
        newErrors.link_thay_the = t('resourceManagement.valEnterReplLink');
      }
    }

    // Bắt buộc có tệp khi tạo mới
    const totalFilesCount = selectedFiles.length + existingFiles.length;
    if (!isEditMode && totalFilesCount === 0) {
      newErrors.file = t('resourceManagement.valAttachFile');
    }

    setErrors(newErrors);

    // Tự động focus và cuộn tới trường lỗi đầu tiên
    const firstErrorKey = Object.keys(newErrors)[0];
    if (firstErrorKey) {
      const errorEl = document.getElementById(`field-${firstErrorKey}`);
      if (errorEl) {
        errorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        errorEl.focus();
      }
    }

    return Object.keys(newErrors).length === 0;
  };

  // Xử lý gửi form
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    if (!validateForm()) return;

    const effectiveDate = formData.ngay_dang || getTodayLocalDateString();

    const data = new FormData();
    data.append('dm_tai_lieu', String(formData.dm_tai_lieu));
    formData.loai_tai_lieu.forEach((tId) => {
      data.append('loai_tai_lieu', String(tId));
    });
    data.append('ky_hieu', formData.ky_hieu.trim());
    data.append('tieu_de', formData.tieu_de.trim());
    data.append('ngay_dang', effectiveDate);
    data.append('noi_ban_hanh', formData.noi_ban_hanh.trim());
    data.append('hieu_luc', formData.hieu_luc);
    data.append('hien_thi', formData.hien_thi);
    data.append('ghi_chu', formData.ghi_chu.trim());

    const isReplaced = formData.hieu_luc === 'HET_VA_THAY_THE';
    const effectiveExpDate = formData.ngay_het_hieu_luc || '';
    const effectiveReplLink = isReplaced ? (formData.link_thay_the?.trim() || '') : '';

    data.append('ngay_het_hieu_luc', effectiveExpDate);
    data.append('link_thay_the', effectiveReplLink);

    // Gửi toàn bộ các tệp mới đính kèm
    selectedFiles.forEach((file) => {
      data.append('files', file);
    });
    if (selectedFiles.length > 0) {
      data.append('file_dinh_kem', selectedFiles[0]);
    }

    // Gửi danh sách ID tệp bị xóa (nếu có)
    deletedAttachmentIds.forEach((id) => {
      data.append('deleted_attachment_ids', String(id));
    });

    await onSubmit({
      formData: data,
      payload: {
        ...formData,
        ngay_dang: effectiveDate,
        ngay_het_hieu_luc: effectiveExpDate,
        link_thay_the: effectiveReplLink,
        files: selectedFiles,
        deleted_attachment_ids: deletedAttachmentIds,
      },
    });
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-6 bg-black/60 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-2xl max-h-[92vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slide-in-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Modal */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4 border-b border-border-subtle bg-surface-elevated shrink-0">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-main">
              {isEditMode ? t('resourceManagement.formTitleEdit') : t('resourceManagement.formTitleAdd')}
            </h2>
            <p className="text-xs text-secondary mt-0.5">
              {t('resourceManagement.formSubtitle')}
            </p>
          </div>

          <button
            type="button"
            onClick={handleSafeClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer"
            aria-label="Đóng form"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Nội dung Form cuộn dọc theo 4 khối đánh số */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-3.5 sm:p-6 space-y-4 sm:space-y-6 min-h-0">
          {/* KHỐI 1: Phân loại (Thư mục -> Loại tài liệu) */}
          <div className="space-y-4 p-3.5 sm:p-4 rounded-xl bg-surface-elevated/60 border border-border-subtle">
            <div className="flex items-center gap-2 border-b border-border-subtle/80 pb-2">
              <span className="w-5 h-5 rounded-full bg-primary text-white text-[11px] font-bold flex items-center justify-center shrink-0">
                1
              </span>
              <h3 className="text-xs font-bold text-main uppercase tracking-wider">
                {t('resourceManagement.block1Classification')}
              </h3>
            </div>

            {/* Thư mục (*) - Custom Responsive Dropdown chống tràn trên mobile */}
            <div className="relative" ref={categoryDropdownRef}>
              <label
                id="field-dm_tai_lieu-label"
                className="text-xs font-semibold text-main block mb-1"
              >
                {t('resourceManagement.fieldFolder')} <span className="text-danger">*</span>
              </label>

              {/* Nút bấm Custom Dropdown */}
              <button
                ref={categoryButtonRef}
                type="button"
                onClick={() => {
                  if (categories.length > 0) {
                    if (isCategoryDropdownOpen) {
                      setIsCategoryDropdownOpen(false);
                      setCategoryMenuPos(null);
                      setCategorySearch('');
                    } else {
                      updateCategoryMenuPos();
                      setIsCategoryDropdownOpen(true);
                    }
                  }
                }}
                disabled={categories.length === 0}
                aria-labelledby="field-dm_tai_lieu-label"
                aria-haspopup="listbox"
                aria-expanded={isCategoryDropdownOpen}
                className={`w-full px-3 py-2 bg-surface border rounded-xl text-xs sm:text-sm text-main flex items-center justify-between gap-2 shadow-2xs transition-colors cursor-pointer font-medium ${
                  categories.length === 0
                    ? 'opacity-60 cursor-not-allowed border-border-subtle'
                    : isCategoryDropdownOpen
                      ? 'border-primary ring-1 ring-primary/20'
                      : errors.dm_tai_lieu
                        ? 'border-danger'
                        : 'border-border-subtle hover:border-primary/50'
                }`}
              >
                <span className={`truncate text-left flex-1 ${!formData.dm_tai_lieu ? 'text-muted' : 'text-main'}`}>
                  {categories.length === 0
                    ? t('resourceManagement.noFoldersAvailable')
                    : selectedCategoryObj?.ten_tai_lieu || t('resourceManagement.selectFolderOption')}
                </span>
                <i
                  className={`fa-solid fa-chevron-down text-xs text-muted transition-transform duration-200 shrink-0 ${
                    isCategoryDropdownOpen ? 'rotate-180 text-primary' : ''
                  }`}
                />
              </button>

              {/* Native select ẩn để tương thích 100% submit form & kiểm thử */}
              <select
                id="field-dm_tai_lieu"
                value={formData.dm_tai_lieu}
                onChange={(e) =>
                  handleCategoryChange(e.target.value ? Number(e.target.value) : '')
                }
                disabled={categories.length === 0}
                className="sr-only"
                tabIndex={-1}
                aria-hidden="true"
              >
                <option value="">{categories.length === 0 ? t('resourceManagement.noFoldersAvailable') : t('resourceManagement.selectFolderOption')}</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.ten_tai_lieu}
                  </option>
                ))}
              </select>

              {categories.length === 0 && (
                <div className="mt-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs flex items-center gap-2">
                  <i className="fa-solid fa-triangle-exclamation text-amber-500 shrink-0" />
                  <span>{t('resourceManagement.systemHasNoFolders')}</span>
                </div>
              )}
              {errors.dm_tai_lieu && (
                <p className="text-danger text-xs mt-1 font-medium">{errors.dm_tai_lieu}</p>
              )}
            </div>

            {/* Loại tài liệu (*) (Multi-select) */}
            <div id="field-loai_tai_lieu">
              <label className="text-xs font-semibold text-main block mb-1">
                {t('resourceManagement.fieldType')} <span className="text-danger">*</span>
                <span className="text-muted font-normal text-xs ml-1">{t('resourceManagement.selectOneOrMoreTypes')}</span>
              </label>

              {!formData.dm_tai_lieu ? (
                <div className="p-3 rounded-lg bg-surface border border-dashed border-border-subtle text-xs text-muted italic">
                  {t('resourceManagement.selectFolderFirstPrompt')}
                </div>
              ) : availableTypes.length === 0 ? (
                <div className="p-3 rounded-lg bg-surface border border-dashed border-border-subtle text-xs text-muted italic">
                  {t('resourceManagement.folderHasNoTypes')}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-3 rounded-lg bg-surface border border-border-subtle max-h-36 overflow-y-auto">
                  {availableTypes.map((type) => {
                    const isChecked = formData.loai_tai_lieu.includes(type.id);
                    return (
                      <label
                        key={type.id}
                        className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs cursor-pointer select-none transition-colors ${
                          isChecked
                            ? 'bg-primary-subtle text-primary font-semibold'
                            : 'hover:bg-surface-elevated text-secondary'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleTypeToggle(type.id)}
                          className="rounded border-border-subtle text-primary focus:ring-0 cursor-pointer"
                        />
                        <span className="truncate">{type.ten_loai}</span>
                      </label>
                    );
                  })}
                </div>
              )}
              {errors.loai_tai_lieu && (
                <p className="text-danger text-xs mt-1 font-medium">{errors.loai_tai_lieu}</p>
              )}
            </div>
          </div>

          {/* KHỐI 2: Thông tin văn bản */}
          <div className="space-y-4 p-4 rounded-xl bg-surface-elevated/60 border border-border-subtle">
            <div className="flex items-center gap-2 border-b border-border-subtle/80 pb-2">
              <span className="w-5 h-5 rounded-full bg-primary text-white text-[11px] font-bold flex items-center justify-center shrink-0">
                2
              </span>
              <h3 className="text-xs font-bold text-main uppercase tracking-wider">
                {t('resourceManagement.block2Info')}
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {/* Ký hiệu */}
              <div>
                <label
                  htmlFor="field-ky_hieu"
                  className="text-xs font-semibold text-main block mb-1"
                >
                  {t('resourceManagement.fieldCode')}
                </label>
                <input
                  id="field-ky_hieu"
                  type="text"
                  placeholder={t('resourceManagement.placeholderCode')}
                  value={formData.ky_hieu}
                  onChange={(e) => {
                    setIsDirty(true);
                    setFormData((prev) => ({ ...prev, ky_hieu: e.target.value }));
                  }}
                  className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors"
                />
              </div>

              {/* Ngày đăng (Cố định theo ngày tạo) */}
              <div>
                <label
                  htmlFor="field-ngay_dang"
                  className="text-xs font-semibold text-main block mb-1"
                >
                  {t('resourceManagement.fieldPostedDateFixed')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                    <i className="fa-solid fa-lock text-xs" />
                  </div>
                  <input
                    id="field-ngay_dang"
                    type="date"
                    readOnly
                    disabled
                    value={formData.ngay_dang}
                    title={t('resourceManagement.postedDateFixedTooltip')}
                    className="w-full pl-8 pr-3 py-2 bg-surface-elevated/70 border border-border-subtle rounded-lg text-sm text-secondary cursor-not-allowed select-none font-medium opacity-90"
                  />
                </div>
              </div>
            </div>

            {/* Tiêu đề (*) */}
            <div>
              <label
                htmlFor="field-tieu_de"
                className="text-xs font-semibold text-main block mb-1"
              >
                {t('resourceManagement.fieldTitle')} <span className="text-danger">*</span>
              </label>
              <textarea
                id="field-tieu_de"
                rows={2}
                placeholder={t('resourceManagement.placeholderTitle')}
                value={formData.tieu_de}
                onChange={(e) => {
                  setIsDirty(true);
                  setFormData((prev) => ({ ...prev, tieu_de: e.target.value }));
                  if (errors.tieu_de) setErrors((prev) => ({ ...prev, tieu_de: '' }));
                }}
                className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors resize-none leading-relaxed"
              />
              {errors.tieu_de && (
                <p className="text-danger text-xs mt-1 font-medium">{errors.tieu_de}</p>
              )}
            </div>

            {/* Grid 2 cột: Nơi ban hành & Người tạo */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Nơi ban hành */}
              <div>
                <label
                  htmlFor="field-noi_ban_hanh"
                  className="text-xs font-semibold text-main block mb-1"
                >
                  {t('resourceManagement.fieldIssuingAuthority')}
                </label>
                <input
                  id="field-noi_ban_hanh"
                  type="text"
                  placeholder={t('resourceManagement.placeholderAuthority')}
                  value={formData.noi_ban_hanh}
                  onChange={(e) => {
                    setIsDirty(true);
                    setFormData((prev) => ({ ...prev, noi_ban_hanh: e.target.value }));
                  }}
                  className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors"
                />
              </div>

              {/* Người tạo tài liệu (Cố định theo tài khoản đăng nhập) */}
              <div>
                <label
                  htmlFor="field-nguoi_tao_name"
                  className="text-xs font-semibold text-main block mb-1"
                >
                  {t('resourceManagement.fieldAuthorFixed')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                    <i className="fa-solid fa-lock text-xs" />
                  </div>
                  <input
                    id="field-nguoi_tao_name"
                    type="text"
                    readOnly
                    disabled
                    value={formData.nguoi_tao_name || defaultAuthor}
                    title={t('resourceManagement.authorFixedTooltip')}
                    className="w-full pl-8 pr-3 py-2 bg-surface-elevated/70 border border-border-subtle rounded-lg text-sm text-secondary cursor-not-allowed select-none font-medium opacity-90"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* KHỐI 3: Hiệu lực & Phạm vi */}
          <div className="space-y-4 p-4 rounded-xl bg-surface-elevated/60 border border-border-subtle">
            <div className="flex items-center gap-2 border-b border-border-subtle/80 pb-2">
              <span className="w-5 h-5 rounded-full bg-primary text-white text-[11px] font-bold flex items-center justify-center shrink-0">
                3
              </span>
              <h3 className="text-xs font-bold text-main uppercase tracking-wider">
                {t('resourceManagement.block4Properties')}
              </h3>
            </div>

            {/* Thuộc tính hiệu lực: Phân tách rõ ràng giữa Thêm mới và Chỉnh sửa */}
            {!isEditMode ? (
              <div className="space-y-3">
                {/* Badge trạng thái mặc định Còn hiệu lực khi tạo mới */}
                <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                    <div>
                      <p className="text-xs font-bold text-emerald-800 dark:text-emerald-200">
                        {t('resourceManagement.statusActiveDefaultBadge')}
                      </p>
                      <p className="text-[11px] text-emerald-700/80 dark:text-emerald-300/80 mt-0.5 leading-relaxed">
                        {t('resourceManagement.statusActiveDefaultDesc')}
                      </p>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40 shrink-0">
                    {t('resourceManagement.statusActive')}
                  </span>
                </div>

                {/* Ô Ngày hết hiệu lực (Tùy chọn) khi tạo mới */}
                <div>
                  <label
                    htmlFor="field-ngay_het_hieu_luc"
                    className="text-xs font-semibold text-main block mb-1"
                  >
                    {t('resourceManagement.fieldScheduledExpiryDate')}
                  </label>
                  <input
                    id="field-ngay_het_hieu_luc"
                    type="date"
                    min={formData.ngay_dang || getTodayLocalDateString()}
                    value={formData.ngay_het_hieu_luc}
                    onChange={(e) => {
                      setIsDirty(true);
                      setFormData((prev) => ({
                        ...prev,
                        ngay_het_hieu_luc: e.target.value,
                      }));
                      if (errors.ngay_het_hieu_luc) {
                        setErrors((prev) => ({ ...prev, ngay_het_hieu_luc: '' }));
                      }
                    }}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors cursor-pointer"
                  />
                  {errors.ngay_het_hieu_luc && (
                    <p className="text-danger text-xs mt-1 font-medium">
                      {errors.ngay_het_hieu_luc}
                    </p>
                  )}
                  <p className="text-[11px] text-muted mt-1 leading-relaxed">
                    {t('resourceManagement.scheduledExpiryHint')}
                  </p>
                  {formData.ngay_het_hieu_luc && (
                    <div className="mt-2 p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-700 dark:text-blue-300 text-[11px] flex items-center gap-1.5">
                      <i className="fa-solid fa-calendar-check text-blue-500 shrink-0" />
                      <span>
                        {t('resourceManagement.futureExpDateHint', {
                          date: formatDate(formData.ngay_het_hieu_luc),
                        })}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* Khi Chỉnh sửa (isEditMode) */
              <div className="space-y-3">
                <label className="text-xs font-semibold text-main block mb-1">
                  {t('resourceManagement.fieldStatus')} <span className="text-danger">*</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { value: 'CON_HIEU_LUC', label: t('resourceManagement.statusActive'), color: 'text-emerald-600 bg-emerald-500/10 border-emerald-500/30' },
                    { value: 'CON_HIEU_LUC_1_PHAN', label: t('resourceManagement.statusPartial'), color: 'text-amber-600 bg-amber-500/10 border-amber-500/30' },
                    { value: 'HET_HIEU_LUC', label: t('resourceManagement.statusExpired'), color: 'text-rose-600 bg-rose-500/10 border-rose-500/30' },
                    { value: 'HET_VA_THAY_THE', label: t('resourceManagement.statusReplaced'), color: 'text-amber-600 bg-amber-500/10 border-amber-500/30' },
                  ].map((st) => {
                    const isSelected = formData.hieu_luc === st.value;
                    return (
                      <button
                        key={st.value}
                        type="button"
                        onClick={() => {
                          setIsDirty(true);
                          setFormData((prev) => ({
                            ...prev,
                            hieu_luc: st.value as HieuLucType,
                            link_thay_the: st.value === 'HET_VA_THAY_THE' ? prev.link_thay_the : '',
                          }));
                        }}
                        className={`px-2.5 py-2 text-xs font-semibold rounded-lg border text-center transition-all cursor-pointer ${
                          isSelected
                            ? `${st.color} ring-2 ring-primary/40 font-bold shadow-2xs`
                            : 'bg-surface border-border-subtle text-secondary hover:bg-surface-elevated'
                        }`}
                      >
                        {st.label}
                      </button>
                    );
                  })}
                </div>

                {/* Ngày hết hiệu lực khi chỉnh sửa */}
                <div className="pt-2 border-t border-border-subtle/80 space-y-3">
                  <div>
                    <label
                      htmlFor="field-ngay_het_hieu_luc"
                      className="text-xs font-semibold text-main block mb-1"
                    >
                      {formData.hieu_luc === 'HET_VA_THAY_THE'
                        ? t('resourceManagement.fieldExpirationDate')
                        : formData.hieu_luc === 'CON_HIEU_LUC'
                        ? t('resourceManagement.fieldScheduledExpiryDate')
                        : formData.hieu_luc === 'HET_HIEU_LUC'
                        ? t('resourceManagement.fieldTerminationDate')
                        : t('resourceManagement.fieldPartialExpiryDate')}{' '}
                      {formData.hieu_luc === 'HET_VA_THAY_THE' && (
                        <span className="text-danger">*</span>
                      )}
                    </label>
                    <input
                      id="field-ngay_het_hieu_luc"
                      type="date"
                      min={formData.ngay_dang || getTodayLocalDateString()}
                      value={formData.ngay_het_hieu_luc}
                      onChange={(e) => {
                        setIsDirty(true);
                        setFormData((prev) => ({
                          ...prev,
                          ngay_het_hieu_luc: e.target.value,
                        }));
                        if (errors.ngay_het_hieu_luc) {
                          setErrors((prev) => ({ ...prev, ngay_het_hieu_luc: '' }));
                        }
                      }}
                      className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors cursor-pointer"
                    />
                    {errors.ngay_het_hieu_luc && (
                      <p className="text-danger text-xs mt-1 font-medium">
                        {errors.ngay_het_hieu_luc}
                      </p>
                    )}
                    <p className="text-[11px] text-muted mt-1 leading-relaxed">
                      {formData.hieu_luc === 'CON_HIEU_LUC'
                        ? t('resourceManagement.scheduledExpiryHint')
                        : formData.hieu_luc === 'HET_HIEU_LUC'
                        ? t('resourceManagement.terminationDateHint')
                        : formData.hieu_luc === 'HET_VA_THAY_THE'
                        ? ''
                        : t('resourceManagement.autoExpireHint')}
                    </p>
                    {formData.ngay_het_hieu_luc && formData.ngay_het_hieu_luc > getTodayLocalDateString() && (
                      <div className="mt-2 p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-700 dark:text-blue-300 text-[11px] flex items-center gap-1.5">
                        <i className="fa-solid fa-calendar-check text-blue-500 shrink-0" />
                        <span>
                          {t('resourceManagement.futureExpDateHint', {
                            date: formatDate(formData.ngay_het_hieu_luc),
                          })}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Link thay thế (Chỉ bắt buộc khi Hết và thay thế) */}
                  {formData.hieu_luc === 'HET_VA_THAY_THE' && (
                    <div>
                      <label
                        htmlFor="field-link_thay_the"
                        className="text-xs font-semibold text-main block mb-1"
                      >
                        {t('resourceManagement.fieldReplacementLink')} <span className="text-danger">*</span>
                      </label>
                      <input
                        id="field-link_thay_the"
                        type="url"
                        placeholder={t('resourceManagement.placeholderReplacementLink')}
                        value={formData.link_thay_the}
                        onChange={(e) => {
                          setIsDirty(true);
                          setFormData((prev) => ({
                            ...prev,
                            link_thay_the: e.target.value,
                          }));
                          if (errors.link_thay_the) {
                            setErrors((prev) => ({ ...prev, link_thay_the: '' }));
                          }
                        }}
                        className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors"
                      />
                      {errors.link_thay_the && (
                        <p className="text-danger text-xs mt-1 font-medium">
                          {errors.link_thay_the}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Phạm vi áp dụng */}
            <div>
              <label className="text-xs font-semibold text-main block mb-1">
                {t('resourceManagement.fieldScope')}
              </label>
              <div className="flex items-center gap-4 text-xs">
                <label className="inline-flex items-center gap-2 cursor-pointer text-main">
                  <input
                    type="radio"
                    name="hien_thi"
                    value="TAT_CA"
                    checked={formData.hien_thi === 'TAT_CA'}
                    onChange={() => {
                      setIsDirty(true);
                      setFormData((prev) => ({ ...prev, hien_thi: 'TAT_CA' }));
                    }}
                    className="text-primary focus:ring-0 cursor-pointer"
                  />
                  <span>{t('resourceManagement.scopeAllDepts')}</span>
                </label>
                <label className="inline-flex items-center gap-2 cursor-pointer text-main">
                  <input
                    type="radio"
                    name="hien_thi"
                    value="NOI_BO_PHONG_BAN"
                    checked={formData.hien_thi === 'NOI_BO_PHONG_BAN'}
                    onChange={() => {
                      setIsDirty(true);
                      setFormData((prev) => ({ ...prev, hien_thi: 'NOI_BO_PHONG_BAN' }));
                    }}
                    className="text-primary focus:ring-0 cursor-pointer"
                  />
                  <span>{t('resourceManagement.scopeInternalDept')}</span>
                </label>
              </div>
            </div>
          </div>

          {/* KHỐI 4: Tệp đính kèm (*) */}
          <div
            id="field-file"
            className="space-y-3 p-4 rounded-xl bg-surface-elevated/60 border border-border-subtle"
          >
            <div className="flex items-center gap-2 border-b border-border-subtle/80 pb-2">
              <span className="w-5 h-5 rounded-full bg-primary text-white text-[11px] font-bold flex items-center justify-center shrink-0">
                4
              </span>
              <h3 className="text-xs font-bold text-main uppercase tracking-wider">
                {t('resourceManagement.block3Attachment')} {!isEditMode && <span className="text-danger">*</span>}
              </h3>
            </div>

            {/* Vùng kéo-thả tệp */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              className={`p-5 rounded-xl border-2 border-dashed text-center transition-all cursor-pointer ${
                isDragOver
                  ? 'border-primary bg-primary-subtle/30'
                  : 'border-border-subtle bg-surface hover:bg-surface-elevated'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                accept={ALLOWED_EXTENSIONS.join(',')}
                onChange={handleFileChange}
              />
              <div className="w-10 h-10 rounded-full bg-primary-subtle text-primary flex items-center justify-center mx-auto mb-2 text-base">
                <i className="fa-solid fa-cloud-arrow-up" />
              </div>
              <p className="text-xs sm:text-sm font-semibold text-main mb-1">
                {t('resourceManagement.dragDropFilesPrompt')}{' '}
                <span className="text-primary underline">{t('resourceManagement.browseFromDevice')}</span>
              </p>
              <p className="text-[11px] text-muted">
                {t('resourceManagement.attachmentSupportedHint')}
              </p>
            </div>

            {/* Danh sách tệp đã chọn hoặc tệp hiện có */}
            {(existingFiles.length > 0 || selectedFiles.length > 0) && (
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between px-1">
                  <span className="text-xs font-semibold text-main">
                    {t('resourceManagement.attachedFilesCount', { count: existingFiles.length + selectedFiles.length })}
                  </span>
                  {selectedFiles.length > 0 && (
                    <span className="text-[11px] text-primary font-medium">
                      {t('resourceManagement.newFilesAdded', { count: selectedFiles.length })}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                  {/* Danh sách tệp hiện có */}
                  {existingFiles.map((file, idx) => {
                    const display = getFileDisplay(file.name);
                    return (
                      <div
                        key={`existing-${file.id || idx}`}
                        className={`p-2.5 rounded-lg border ${display.bg} flex items-center justify-between gap-3 text-xs transition-colors hover:border-primary/40`}
                      >
                        <div
                          role="button"
                          tabIndex={0}
                          onClick={() => handlePreviewExistingFile(file)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handlePreviewExistingFile(file);
                            }
                          }}
                          className="flex items-center gap-2.5 min-w-0 flex-1 cursor-pointer group/file text-left focus:outline-hidden"
                          title={t('resourceManagement.previewAttachment')}
                        >
                          <i className={`${display.icon} ${display.color} text-sm shrink-0 group-hover/file:scale-110 transition-transform`} />
                          <span className="truncate font-medium text-main group-hover/file:text-primary group-hover/file:underline transition-colors" title={file.name}>
                            {file.name}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border-subtle text-muted shrink-0 font-medium">
                            {t('resourceManagement.existingFileBadge')}
                          </span>
                          {file.size && (
                            <span className="text-[11px] text-muted shrink-0">
                              ({formatSize(file.size)})
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => handlePreviewExistingFile(file)}
                            className="p-1 text-muted hover:text-primary rounded transition-colors cursor-pointer"
                            title={t('resourceManagement.previewAttachment')}
                            aria-label={t('resourceManagement.previewAttachment')}
                          >
                            <i className="fa-solid fa-eye text-xs" />
                          </button>
                          {file.id && (
                            <a
                              href={`/api/resources/attachments/${file.id}/download/`}
                              download={file.name}
                              className="p-1 text-muted hover:text-primary rounded transition-colors cursor-pointer inline-flex items-center justify-center"
                              title={t('resourceManagement.downloadAttachment')}
                              aria-label={t('resourceManagement.downloadAttachment')}
                            >
                              <i className="fa-solid fa-download text-xs" />
                            </a>
                          )}
                          <button
                            type="button"
                            onClick={() => handleRemoveExistingFile(idx)}
                            className="p-1 text-muted hover:text-danger rounded transition-colors cursor-pointer"
                            title={t('resourceManagement.deleteThisFile')}
                            aria-label={t('resourceManagement.deleteThisFile')}
                          >
                            <i className="fa-solid fa-trash-can text-xs" />
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {/* Danh sách tệp mới tải lên */}
                  {selectedFiles.map((file, idx) => {
                    const display = getFileDisplay(file.name);
                    return (
                      <div
                        key={`selected-${file.name}-${idx}`}
                        className={`p-2.5 rounded-lg border ${display.bg} flex items-center justify-between gap-3 text-xs transition-colors hover:border-primary/40`}
                      >
                        <div
                          role="button"
                          tabIndex={0}
                          onClick={() => handlePreviewSelectedFile(file)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handlePreviewSelectedFile(file);
                            }
                          }}
                          className="flex items-center gap-2.5 min-w-0 flex-1 cursor-pointer group/file text-left focus:outline-hidden"
                          title={t('resourceManagement.previewAttachment')}
                        >
                          <i className={`${display.icon} ${display.color} text-sm shrink-0 group-hover/file:scale-110 transition-transform`} />
                          <span className="truncate font-medium text-main group-hover/file:text-primary group-hover/file:underline transition-colors" title={file.name}>
                            {file.name}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-semibold border border-primary/20 shrink-0">
                            {t('resourceManagement.newlyAdded')}
                          </span>
                          <span className="text-[11px] text-muted shrink-0">
                            ({formatSize(file.size)})
                          </span>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => handlePreviewSelectedFile(file)}
                            className="p-1 text-muted hover:text-primary rounded transition-colors cursor-pointer"
                            title={t('resourceManagement.previewAttachment')}
                            aria-label={t('resourceManagement.previewAttachment')}
                          >
                            <i className="fa-solid fa-eye text-xs" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const url = URL.createObjectURL(file);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = file.name;
                              a.click();
                              URL.revokeObjectURL(url);
                            }}
                            className="p-1 text-muted hover:text-primary rounded transition-colors cursor-pointer"
                            title={t('resourceManagement.downloadAttachment')}
                            aria-label={t('resourceManagement.downloadAttachment')}
                          >
                            <i className="fa-solid fa-download text-xs" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRemoveSelectedFile(idx)}
                            className="p-1 text-muted hover:text-danger rounded transition-colors cursor-pointer"
                            title={t('resourceManagement.deleteThisFile')}
                            aria-label={t('resourceManagement.deleteThisFile')}
                          >
                            <i className="fa-solid fa-trash-can text-xs" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {fileError && <p className="text-danger text-xs font-medium">{fileError}</p>}
            {errors.file && <p className="text-danger text-xs font-medium">{errors.file}</p>}
          </div>

          {/* Ghi chú */}
          <div>
            <label
              htmlFor="field-ghi_chu"
              className="text-xs font-semibold text-main block mb-1"
            >
              {t('resourceManagement.fieldNotesExtra')}
            </label>
            <input
              id="field-ghi_chu"
              type="text"
              placeholder={t('resourceManagement.placeholderNotes')}
              value={formData.ghi_chu}
              onChange={(e) => {
                setIsDirty(true);
                setFormData((prev) => ({ ...prev, ghi_chu: e.target.value }));
              }}
              className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-sm text-main focus:outline-hidden focus:border-primary transition-colors"
            />
          </div>
        </form>

        {/* Footer cố định */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-border-subtle bg-surface-elevated flex items-center justify-end flex-wrap sm:flex-nowrap gap-2 sm:gap-3 shrink-0">
          <Button
            variant="outline"
            size="md"
            onClick={handleSafeClose}
            disabled={isLoading}
            className="text-xs"
          >
            {t('resourceManagement.cancel')}
          </Button>

          <Button
            variant="primary"
            size="md"
            icon={isLoading ? 'fa-spinner fa-spin' : 'fa-check'}
            onClick={handleSubmit}
            isLoading={isLoading}
            disabled={isLoading || categories.length === 0 || !canSubmit}
            title={!canSubmit ? t('roles.messages.permissionDenied') : undefined}
            className="text-xs shadow-sm"
          >
            {isEditMode ? t('resourceManagement.saveChanges') : t('resourceManagement.save')}
          </Button>
        </div>

        {/* Modal xác nhận hủy các thay đổi chưa lưu */}
        <ConfirmationModal
          isOpen={isConfirmDiscardOpen}
          onClose={() => setIsConfirmDiscardOpen(false)}
          onConfirm={() => {
            setIsConfirmDiscardOpen(false);
            setIsDirty(false);
            onClose();
          }}
          title={t('resourceManagement.confirmDiscardTitle')}
          message={t('resourceManagement.confirmDiscardMsg')}
          subMessage={t('resourceManagement.confirmDiscardSub')}
          confirmText={t('resourceManagement.confirmDiscardBtn')}
          cancelText={t('resourceManagement.continueEditingBtn')}
          variant="warning"
          headerIcon="fa-triangle-exclamation"
          confirmIcon="fa-arrow-rotate-left"
        />

        {/* Modal xem trước tệp đính kèm */}
        {previewAttachment && (
          <FilePreviewModal
            isOpen={Boolean(previewAttachment)}
            onClose={() => {
              if (previewAttachment.path?.startsWith('blob:')) {
                URL.revokeObjectURL(previewAttachment.path);
              }
              setPreviewAttachment(null);
            }}
            file={previewAttachment}
            documentTitle={formData.tieu_de}
          />
        )}
      </div>
      {/* Dropdown popup Thư mục rendered via Portal chống đè / cắt */}
      {isCategoryDropdownOpen && categoryMenuPos && createPortal(
        <div
          ref={categoryMenuRef}
          role="listbox"
          data-dropdown-container="true"
          onMouseDown={(e) => e.stopPropagation()}
          style={{
            position: 'fixed',
            top: categoryMenuPos.top !== undefined ? `${categoryMenuPos.top}px` : undefined,
            bottom: categoryMenuPos.bottom !== undefined ? `${categoryMenuPos.bottom}px` : undefined,
            left: `${categoryMenuPos.left}px`,
            width: `${categoryMenuPos.width}px`,
            maxHeight: `${categoryMenuPos.maxHeight}px`,
            zIndex: 10005,
          }}
          className="bg-surface-elevated rounded-xl border border-border-subtle shadow-2xl p-1.5 overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-100"
        >
          {/* Ô tìm kiếm nhanh thư mục */}
          <div className="p-1 pb-1.5 border-b border-border-subtle shrink-0">
            <div className="relative">
              <i className="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-muted text-[11px]" />
              <input
                type="text"
                value={categorySearch}
                onChange={(e) => setCategorySearch(e.target.value)}
                placeholder={t('resourceManagement.searchCategoryPlaceholder')}
                className="w-full pl-7 pr-7 py-1 text-xs bg-surface border border-border-subtle rounded-lg text-main placeholder:text-muted focus:outline-hidden focus:border-primary"
                onClick={(e) => e.stopPropagation()}
                autoFocus
              />
              {categorySearch && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCategorySearch('');
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-main text-[11px] p-0.5 cursor-pointer"
                >
                  <i className="fa-solid fa-xmark" />
                </button>
              )}
            </div>
          </div>

          {/* Danh sách các thư mục có scroll: hiển thị 5 mục, nếu nhiều hơn thì cuộn chuột lên xuống */}
          <div
            className="flex-1 overflow-y-auto max-h-[185px] pt-1 space-y-0.5 overscroll-contain pr-1 custom-scrollbar"
            role="listbox"
            onWheel={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => {
                handleCategoryChange('');
                setIsCategoryDropdownOpen(false);
                setCategoryMenuPos(null);
                setCategorySearch('');
              }}
              className={`w-full px-2.5 py-2 rounded-lg text-left text-xs font-medium flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                !formData.dm_tai_lieu
                  ? 'bg-primary/10 text-primary font-bold'
                  : 'text-muted hover:bg-surface'
              }`}
            >
              <span className="truncate">{t('resourceManagement.selectFolderOption')}</span>
              {!formData.dm_tai_lieu && (
                <i className="fa-solid fa-check text-primary text-xs shrink-0" />
              )}
            </button>

            <div className="my-1 border-t border-border-subtle" />

            {filteredCategories.length === 0 ? (
              <div className="p-3 text-center text-xs text-muted">
                {t('resourceManagement.noMatchingFolders')}
              </div>
            ) : (
              filteredCategories.map((cat) => {
                const isSelected = formData.dm_tai_lieu === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      handleCategoryChange(cat.id);
                      setIsCategoryDropdownOpen(false);
                      setCategoryMenuPos(null);
                      setCategorySearch('');
                    }}
                    className={`w-full px-2.5 py-2 rounded-lg text-left text-xs font-medium flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-primary/10 text-primary font-bold'
                        : 'text-main hover:bg-surface'
                    }`}
                  >
                    <span className="truncate flex items-center gap-2">
                      <i className="fa-solid fa-folder text-primary/70 text-xs shrink-0" />
                      <span className="truncate">{cat.ten_tai_lieu}</span>
                    </span>
                    {isSelected && (
                      <i className="fa-solid fa-check text-primary text-xs shrink-0" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>,
        document.body
      )}
    </div>,
    document.body
  );
};
