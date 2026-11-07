import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { FolderItem, FolderFileItem, FolderBreadcrumb as BreadcrumbType } from '@app-types/resource';
import { folderService } from '@lib/folderService';
import { Button } from '@components/common/Button';
import { FolderTreeView } from './FolderTreeView';
import { FolderBreadcrumb } from './FolderBreadcrumb';
import {
  CreateOrEditFolderModal,
  MoveFolderModal,
  DeleteFolderModal,
} from './FolderActionModals';
import { useTranslation } from '@i18n/translate';

function findNodeInTree(nodes: FolderItem[], id: number): FolderItem | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNodeInTree(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

interface FolderManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectFolderForResource?: (folder: FolderItem) => void;
}

export const FolderManagerModal: React.FC<FolderManagerModalProps> = ({
  isOpen,
  onClose,
  onSelectFolderForResource,
}) => {
  const { t } = useTranslation();
  const [tree, setTree] = useState<FolderItem[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<FolderItem | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbType[]>([]);
  const [files, setFiles] = useState<FolderFileItem[]>([]);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createModalParent, setCreateModalParent] = useState<FolderItem | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingFolder, setEditingFolder] = useState<FolderItem | null>(null);
  const [isMoveModalOpen, setIsMoveModalOpen] = useState(false);
  const [movingFolder, setMovingFolder] = useState<FolderItem | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deletingFolder, setDeletingFolder] = useState<FolderItem | null>(null);

  // Add File State
  const [isAddFileModalOpen, setIsAddFileModalOpen] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileSize, setNewFileSize] = useState('');
  const [newFileType, setNewFileType] = useState('pdf');
  const [newFileDescription, setNewFileDescription] = useState('');
  const [isAddingFile, setIsAddingFile] = useState(false);

  // Scan Local State
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [scanFolderPath, setScanFolderPath] = useState('');
  const [scanUnderCurrentFolder, setScanUnderCurrentFolder] = useState(false);
  const [isScanningLocal, setIsScanningLocal] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);

  const handleScanLocal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsScanningLocal(true);
      setScanResult(null);
      const res = await folderService.scanLocal({
        folder_path: scanFolderPath.trim() || undefined,
        parent_id: scanUnderCurrentFolder && selectedFolder ? selectedFolder.id : null,
      });
      setScanResult(res.message);
      await loadTree();
      if (res.root_folder_id) {
        await loadFolderDetails(res.root_folder_id);
      }
      setTimeout(() => {
        setIsScanModalOpen(false);
        setScanResult(null);
        setScanFolderPath('');
      }, 1500);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Local folder scan failed.');
    } finally {
      setIsScanningLocal(false);
    }
  };

  // Tải lại toàn bộ cây thư mục
  const loadTree = useCallback(async () => {
    try {
      const data = await folderService.getTree();
      setTree(data);
      // Nếu folder đang chọn còn tồn tại, cập nhật lại dữ liệu của nó
      if (selectedFolder) {
        const found = findNodeInTree(data, selectedFolder.id);
        if (found) setSelectedFolder(found);
      }
    } catch (e) {
      console.error('Lỗi khi tải cây thư mục:', e);
    }
  }, [selectedFolder]);

  // Tìm node trong tree
  // Thu gom danh sách phẳng tất cả thư mục
  const flatFolders = useMemo(() => {
    const list: FolderItem[] = [];
    const traverse = (items: FolderItem[]) => {
      items.forEach((item) => {
        list.push(item);
        if (item.children) traverse(item.children);
      });
    };
    traverse(tree);
    return list;
  }, [tree]);

  // Tải chi tiết thư mục khi chọn
  const loadFolderDetails = useCallback(async (folderId: number | null) => {
    if (folderId === null) {
      setSelectedFolder(null);
      setBreadcrumbs([]);
      setFiles([]);
      return;
    }

    try {
      setIsLoadingDetails(true);
      const [folderData, bcData, filesData] = await Promise.all([
        folderService.getById(folderId).catch(() => null),
        folderService.getBreadcrumb(folderId).catch(() => []),
        folderService.getFiles(folderId).catch(() => []),
      ]);

      if (folderData) setSelectedFolder(folderData);
      setBreadcrumbs(bcData);
      setFiles(filesData);
    } catch (e) {
      console.error('Lỗi khi tải chi tiết thư mục:', e);
    } finally {
      setIsLoadingDetails(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadTree();
    }
  }, [isOpen, loadTree]);

  if (!isOpen) return null;

  // Thao tác Tạo thư mục (gốc hoặc con)
  const handleCreateSubmit = async (data: { name: string; description: string; order: number }) => {
    if (createModalParent) {
      await folderService.createChild(createModalParent.id, data);
    } else {
      await folderService.create({ ...data, parent_id: null });
    }
    await loadTree();
    if (createModalParent) {
      loadFolderDetails(createModalParent.id);
    }
  };

  // Thao tác Sửa thư mục
  const handleEditSubmit = async (data: { name: string; description: string; order: number }) => {
    if (!editingFolder) return;
    await folderService.update(editingFolder.id, data);
    await loadTree();
    loadFolderDetails(editingFolder.id);
  };

  // Thao tác Di chuyển
  const handleConfirmMove = async (folderId: number, targetParentId: number | null) => {
    await folderService.move(folderId, targetParentId);
    await loadTree();
    loadFolderDetails(folderId);
  };

  // Thao tác Xóa
  const handleConfirmDelete = async (folderId: number) => {
    await folderService.delete(folderId);
    if (selectedFolder && selectedFolder.id === folderId) {
      setSelectedFolder(null);
      setBreadcrumbs([]);
      setFiles([]);
    }
    await loadTree();
  };

  // Thao tác thêm File vào thư mục
  const handleAddFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFolder || !newFileName.trim()) return;

    try {
      setIsAddingFile(true);
      await folderService.addFile(selectedFolder.id, {
        file_name: newFileName.trim(),
        file_size: parseInt(newFileSize, 10) || 1024,
        file_type: newFileType,
        description: newFileDescription.trim(),
      });
      setIsAddFileModalOpen(false);
      setNewFileName('');
      setNewFileSize('');
      setNewFileDescription('');
      loadFolderDetails(selectedFolder.id);
      loadTree();
    } catch (err) {
      console.error('Lỗi thêm tệp:', err);
    } finally {
      setIsAddingFile(false);
    }
  };

  // Xóa file
  const handleDeleteFile = async (fileId: number) => {
    if (!window.confirm(t('folders.modal.confirmDeleteFile'))) return;
    try {
      await folderService.deleteFile(fileId);
      if (selectedFolder) loadFolderDetails(selectedFolder.id);
      loadTree();
    } catch (err) {
      console.error('Lỗi xóa file:', err);
    }
  };

  // Định dạng kích thước file
  const formatSize = (bytes: number): string => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/65 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-surface rounded-2xl border border-border-subtle shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header Modal */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle shrink-0 bg-surface">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <i className="fa-solid fa-folder-tree text-lg" />
            </div>
            <div>
              <h2 className="text-lg font-black text-main tracking-tight flex items-center gap-2">
                {t('folders.modal.title')}
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                  Hierarchical Folders
                </span>
              </h2>
              <p className="text-xs text-secondary">
                {t('folders.modal.subtitle')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon="fa-laptop"
              onClick={() => {
                setScanUnderCurrentFolder(Boolean(selectedFolder));
                setIsScanModalOpen(true);
              }}
              title={t('folders.modal.syncLocalHint')}
            >
              {t('folders.modal.syncLocal')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon="fa-folder-plus"
              onClick={() => {
                setCreateModalParent(null);
                setIsCreateModalOpen(true);
              }}
            >
              {t('folders.modal.createRoot')}
            </Button>
            <button
              type="button"
              onClick={onClose}
              className="w-9 h-9 rounded-xl text-secondary hover:text-main hover:bg-surface-elevated flex items-center justify-center transition-colors"
            >
              <i className="fa-solid fa-xmark text-base" />
            </button>
          </div>
        </div>

        {/* Thân Modal — Bố cục 2 cột (Trái: TreeView | Phải: Nội dung chi tiết thư mục) */}
        <div className="flex-1 flex overflow-hidden">
          {/* Cột trái: Cây thư mục */}
          <div className="w-80 sm:w-96 border-r border-border-subtle p-3 bg-surface/50 shrink-0 flex flex-col overflow-hidden">
            <FolderTreeView
              tree={tree}
              selectedFolderId={selectedFolder?.id || null}
              onSelectFolder={(folder) => loadFolderDetails(folder.id)}
              onCreateChild={(folder) => {
                setCreateModalParent(folder);
                setIsCreateModalOpen(true);
              }}
              onEditFolder={(folder) => {
                setEditingFolder(folder);
                setIsEditModalOpen(true);
              }}
              onMoveFolder={(folder) => {
                setMovingFolder(folder);
                setIsMoveModalOpen(true);
              }}
              onDeleteFolder={(folder) => {
                setDeletingFolder(folder);
                setIsDeleteModalOpen(true);
              }}
            />
          </div>

          {/* Cột phải: Chi tiết thư mục & Files */}
          <div className="flex-1 flex flex-col overflow-hidden bg-surface-elevated/20 p-5">
            {isLoadingDetails ? (
              <div className="flex-1 flex items-center justify-center text-secondary text-sm">
                <i className="fa-solid fa-spinner fa-spin mr-2 text-primary text-base" />
                {t('folders.modal.loading')}
              </div>
            ) : selectedFolder ? (
              <div className="flex-1 flex flex-col overflow-hidden space-y-4">
                {/* Breadcrumb Navigation */}
                <FolderBreadcrumb
                  breadcrumbs={breadcrumbs}
                  onSelect={(folderId) => loadFolderDetails(folderId)}
                />

                {/* Header Thư mục hiện tại */}
                <div className="p-4 rounded-2xl bg-surface border border-border-subtle shadow-xs shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center">
                        <i className="fa-solid fa-folder-open text-base" />
                      </span>
                      <h3 className="text-base font-bold text-main">{selectedFolder.name}</h3>
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                        {t('folders.modal.depthLevel', { level: selectedFolder.depth || 0 })}
                      </span>
                      {selectedFolder.is_local && (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-600 font-bold border border-sky-500/20 flex items-center gap-1">
                          <i className="fa-solid fa-laptop text-[10px]" />
                          {t('folders.modal.localFolder')}
                        </span>
                      )}
                    </div>
                    {selectedFolder.description && (
                      <p className="text-xs text-secondary pl-10">{selectedFolder.description}</p>
                    )}
                    {selectedFolder.local_path && (
                      <p className="text-[11px] text-sky-600 pl-10 font-mono truncate" title={selectedFolder.local_path}>
                        {t('folders.modal.localDisk', { path: selectedFolder.local_path || '' })}
                      </p>
                    )}
                    <p className="text-[11px] text-muted pl-10 font-mono">
                      {t('folders.modal.idPath', { path: selectedFolder.path || '' })}
                    </p>
                  </div>

                  {/* Nhóm nút hành động */}
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Button
                      variant="secondary"
                      size="sm"
                      icon="fa-folder-plus"
                      onClick={() => {
                        setCreateModalParent(selectedFolder);
                        setIsCreateModalOpen(true);
                      }}
                      title={t('folders.modal.addSubfolderHint')}
                    >
                      {t('folders.modal.addSubfolder')}
                    </Button>
                    {!selectedFolder.is_local ? (
                      <Button
                        variant="primary"
                        size="sm"
                        icon="fa-file-circle-plus"
                        onClick={() => setIsAddFileModalOpen(true)}
                        title={t('folders.modal.addFileHint')}
                      >
                        {t('folders.modal.addFile')}
                      </Button>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400 text-xs font-semibold select-none border border-sky-200 dark:border-sky-800/50"
                        title={t('folders.modal.localReadOnlyHint')}
                      >
                        <i className="fa-solid fa-eye text-[11px]" />
                        <span>{t('folders.modal.localReadOnly')}</span>
                      </span>
                    )}
                    {onSelectFolderForResource && (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon="fa-check"
                        onClick={() => {
                          onSelectFolderForResource(selectedFolder);
                          onClose();
                        }}
                      >
                        {t('folders.modal.selectThisFolder')}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Thư mục con (nếu có) */}
                {selectedFolder.children && selectedFolder.children.length > 0 && (
                  <div className="shrink-0 space-y-2">
                    <h4 className="text-xs font-bold text-secondary uppercase tracking-wider">
                      {t('folders.modal.subfolders', { count: selectedFolder.children.length })}
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                      {selectedFolder.children.map((child) => (
                        <div
                          key={child.id}
                          onClick={() => loadFolderDetails(child.id)}
                          className="flex items-center gap-2.5 p-2.5 rounded-xl bg-surface border border-border-subtle hover:border-primary/40 hover:bg-primary/5 transition-all cursor-pointer group"
                        >
                          <i className="fa-solid fa-folder text-amber-500 text-sm group-hover:scale-110 transition-transform" />
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-main truncate">{child.name}</p>
                            <span className="text-[10px] text-muted">
                              {t('folders.modal.filesCount', { count: child.files_count || 0 })}
                            </span>
                          </div>
                          <i className="fa-solid fa-chevron-right text-[10px] text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Bảng Tệp trong thư mục */}
                <div className="flex-1 flex flex-col overflow-hidden bg-surface rounded-2xl border border-border-subtle shadow-xs">
                  <div className="p-3.5 border-b border-border-subtle flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-file-lines text-primary text-xs" />
                      <h4 className="text-xs font-bold text-main">
                        {t('folders.modal.fileList', { count: files.length })}
                      </h4>
                    </div>
                    {!selectedFolder.is_local && (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon="fa-plus"
                        onClick={() => setIsAddFileModalOpen(true)}
                      >
                        {t('folders.modal.addFile')}
                      </Button>
                    )}
                  </div>

                  <div className="flex-1 overflow-y-auto custom-scrollbar">
                    {files.length === 0 ? (
                      <div className="py-12 text-center text-xs text-muted space-y-2">
                        <i className="fa-solid fa-file-circle-question text-3xl text-muted/40 block" />
                        <p>{t('folders.modal.noFiles')}</p>
                        {!selectedFolder.is_local && (
                          <Button
                            variant="secondary"
                            size="sm"
                            icon="fa-upload"
                            onClick={() => setIsAddFileModalOpen(true)}
                          >
                            {t('folders.modal.addFirstFile')}
                          </Button>
                        )}
                      </div>
                    ) : (
                      <table className="w-full text-left text-xs border-collapse">
                        <thead className="sticky top-0 bg-surface-elevated text-secondary font-semibold border-b border-border-subtle">
                          <tr>
                            <th className="py-2.5 px-3">{t('folders.modal.colFileName')}</th>
                            <th className="py-2.5 px-3">{t('folders.modal.colType')}</th>
                            <th className="py-2.5 px-3">{t('folders.modal.colSize')}</th>
                            <th className="py-2.5 px-3">{t('folders.modal.colDescription')}</th>
                            <th className="py-2.5 px-3 text-right">{t('folders.modal.colActions')}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle">
                          {files.map((file) => (
                            <tr key={file.id} className="hover:bg-surface-elevated/40 transition-colors">
                              <td className="py-2.5 px-3 font-semibold text-main">
                                <div className="flex items-center gap-2">
                                  <i
                                    className={`fa-solid ${
                                      file.file_type === 'pdf'
                                        ? 'fa-file-pdf text-danger'
                                        : file.file_type?.includes('doc')
                                        ? 'fa-file-word text-sky-500'
                                        : 'fa-file text-secondary'
                                    } text-sm`}
                                  />
                                  <span className="truncate">{file.file_name}</span>
                                  {file.is_local && (
                                    <span
                                      className="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-600 font-semibold border border-sky-500/20 shrink-0 flex items-center gap-0.5"
                                      title={file.file_path || t('folders.modal.localFile')}
                                    >
                                      <i className="fa-solid fa-laptop text-[8px]" />
                                      Local
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-secondary uppercase font-mono text-[11px]">
                                {file.file_type || '—'}
                              </td>
                              <td className="py-2.5 px-3 text-secondary">
                                {formatSize(file.file_size)}
                              </td>
                              <td className="py-2.5 px-3 text-muted max-w-[200px] truncate" title={file.description || file.file_path}>
                                {file.description || file.file_path || '—'}
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <div className="flex items-center justify-end gap-1">
                                  <a
                                    href={folderService.getDownloadUrl(file.id, true)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-7 h-7 rounded-lg hover:bg-primary/10 text-primary inline-flex items-center justify-center transition-colors"
                                    title={t('folders.modal.viewFile')}
                                  >
                                    <i className="fa-solid fa-eye text-xs" />
                                  </a>
                                  <a
                                    href={folderService.getDownloadUrl(file.id, false)}
                                    download={file.file_name}
                                    className="w-7 h-7 rounded-lg hover:bg-sky-500/10 text-sky-600 inline-flex items-center justify-center transition-colors"
                                    title={t('folders.modal.downloadFile')}
                                  >
                                    <i className="fa-solid fa-download text-xs" />
                                  </a>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteFile(file.id)}
                                    className="w-7 h-7 rounded-lg hover:bg-danger/10 text-danger inline-flex items-center justify-center transition-colors"
                                    title={t('folders.modal.deleteFile')}
                                  >
                                    <i className="fa-solid fa-trash text-xs" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-secondary space-y-3">
                <div className="w-16 h-16 rounded-3xl bg-primary/10 text-primary flex items-center justify-center">
                  <i className="fa-solid fa-sitemap text-2xl" />
                </div>
                <div>
                  <h3 className="font-bold text-main text-base">{t('folders.modal.pickFolder')}</h3>
                  <p className="text-xs text-secondary mt-1 max-w-sm">
                    {t('folders.modal.pickFolderHint')}
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  icon="fa-folder-plus"
                  onClick={() => {
                    setCreateModalParent(null);
                    setIsCreateModalOpen(true);
                  }}
                >
                  {t('folders.modal.createNewRoot')}
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal tạo / sửa thư mục */}
      <CreateOrEditFolderModal
        key={`${isCreateModalOpen || isEditModalOpen}-${editingFolder?.id ?? 'new'}-${createModalParent?.id ?? 'root'}`}
        isOpen={isCreateModalOpen || isEditModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setIsEditModalOpen(false);
          setEditingFolder(null);
          setCreateModalParent(null);
        }}
        onSubmit={isEditModalOpen ? handleEditSubmit : handleCreateSubmit}
        initialData={editingFolder}
        parentFolder={createModalParent}
      />

      {/* Modal di chuyển thư mục */}
      <MoveFolderModal
        key={`${isMoveModalOpen}-${movingFolder?.id ?? 'none'}`}
        isOpen={isMoveModalOpen}
        onClose={() => {
          setIsMoveModalOpen(false);
          setMovingFolder(null);
        }}
        folder={movingFolder}
        allFolders={flatFolders}
        onConfirmMove={handleConfirmMove}
      />

      {/* Modal xác nhận xóa */}
      <DeleteFolderModal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setDeletingFolder(null);
        }}
        folder={deletingFolder}
        onConfirmDelete={handleConfirmDelete}
      />

      {/* Modal thêm File vào thư mục */}
      {isAddFileModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="bg-surface rounded-2xl border border-border-subtle shadow-xl w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <h3 className="font-bold text-main text-sm flex items-center gap-2">
                <i className="fa-solid fa-file-circle-plus text-primary" />
                {t('folders.modal.addFileTo', { name: selectedFolder?.name ?? '' })}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddFileModalOpen(false)}
                className="text-secondary hover:text-main"
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            <form onSubmit={handleAddFile} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-main mb-1">
                  {t('folders.modal.fileName')} <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder={t('folders.modal.fileNamePlaceholder')}
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary text-main"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-main mb-1">{t('folders.modal.format')}</label>
                  <select
                    value={newFileType}
                    onChange={(e) => setNewFileType(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary text-main"
                  >
                    <option value="pdf">PDF (.pdf)</option>
                    <option value="docx">Word (.docx)</option>
                    <option value="xlsx">Excel (.xlsx)</option>
                    <option value="txt">Text (.txt)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-main mb-1">{t('folders.modal.sizeBytes')}</label>
                  <input
                    type="number"
                    min={0}
                    placeholder="1048576 (1MB)"
                    value={newFileSize}
                    onChange={(e) => setNewFileSize(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary text-main"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-main mb-1">{t('folders.modal.colDescription')}</label>
                <textarea
                  rows={2}
                  value={newFileDescription}
                  onChange={(e) => setNewFileDescription(e.target.value)}
                  placeholder={t('folders.modal.descriptionPlaceholder')}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary text-main resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
                <Button
                  variant="secondary"
                  size="sm"
                  type="button"
                  onClick={() => setIsAddFileModalOpen(false)}
                >
                  {t('folders.modal.cancel')}
                </Button>
                <Button variant="primary" size="sm" type="submit" disabled={isAddingFile}>
                  {isAddingFile ? t('folders.modal.adding') : t('folders.modal.saveFile')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Đồng bộ thư mục máy tính (Local Directory Sync) */}
      {isScanModalOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-surface rounded-2xl border border-border-subtle shadow-xl w-full max-w-lg p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
              <div className="flex items-center gap-2.5">
                <span className="w-8 h-8 rounded-xl bg-sky-500/10 text-sky-600 flex items-center justify-center">
                  <i className="fa-solid fa-laptop text-sm" />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-main">{t('folders.modal.syncTitle')}</h3>
                  <p className="text-[11px] text-secondary">
                    {t('folders.modal.syncSubtitle')}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsScanModalOpen(false)}
                className="text-secondary hover:text-main"
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            <form onSubmit={handleScanLocal} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-main mb-1">
                  {t('folders.modal.localPath')}
                </label>
                <input
                  type="text"
                  placeholder={t('folders.modal.localPathPlaceholder')}
                  value={scanFolderPath}
                  onChange={(e) => setScanFolderPath(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary text-main font-mono"
                  autoFocus
                />
                <p className="text-[11px] text-muted mt-1">
                  {t('folders.modal.defaultScanPrefix')} <span className="font-mono text-primary">./Folder</span> {t('folders.modal.defaultScanSuffix')}
                </p>
              </div>

              {selectedFolder && (
                <div className="p-3 rounded-xl bg-surface-elevated/40 border border-border-subtle flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="scanUnderCurrent"
                    checked={scanUnderCurrentFolder}
                    onChange={(e) => setScanUnderCurrentFolder(e.target.checked)}
                    className="rounded border-border-subtle text-primary focus:ring-0"
                  />
                  <label htmlFor="scanUnderCurrent" className="text-xs text-secondary cursor-pointer">
                    {t('folders.modal.syncIntoSelected')} <strong className="text-main">{selectedFolder.name}</strong>
                  </label>
                </div>
              )}

              {scanResult && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 text-xs flex items-center gap-2">
                  <i className="fa-solid fa-circle-check text-sm" />
                  <span>{scanResult}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
                <Button
                  variant="secondary"
                  size="sm"
                  type="button"
                  onClick={() => setIsScanModalOpen(false)}
                  disabled={isScanningLocal}
                >
                  {t('folders.modal.close')}
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  type="submit"
                  icon={isScanningLocal ? 'fa-spinner fa-spin' : 'fa-arrows-rotate'}
                  disabled={isScanningLocal}
                >
                  {isScanningLocal ? t('folders.modal.scanning') : t('folders.modal.startSync')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>,
    document.body
  );
};

export default FolderManagerModal;
