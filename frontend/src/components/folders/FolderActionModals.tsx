import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { FolderItem } from '@app-types/resource';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';

// ═══════════════════════════════════════════════════════════════════
// 1. Create or Edit Folder Modal
// ═══════════════════════════════════════════════════════════════════
interface CreateOrEditFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; description: string; order: number }) => Promise<void>;
  initialData?: FolderItem | null;
  parentFolder?: FolderItem | null;
}

export const CreateOrEditFolderModal: React.FC<CreateOrEditFolderModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  parentFolder,
}) => {
  const { t } = useTranslation();
  const [name, setName] = useState(() => initialData?.name || '');
  const [description, setDescription] = useState(() => initialData?.description || '');
  const [order, setOrder] = useState<number>(() => initialData?.order || 0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = Boolean(initialData);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError(t('folders.actions.nameRequired'));
      return;
    }
    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit({ name: name.trim(), description: description.trim(), order });
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('folders.actions.saveError');
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-surface rounded-2xl border border-border-subtle shadow-xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between p-5 border-b border-border-subtle">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <i className={`fa-solid ${isEdit ? 'fa-pen-to-square' : 'fa-folder-plus'} text-base`} />
            </div>
            <div>
              <h3 className="font-bold text-main text-base">
                {isEdit ? t('folders.actions.editTitle') : t('folders.actions.createTitle')}
              </h3>
              <p className="text-xs text-secondary">
                {parentFolder
                  ? t('folders.actions.subfolderOf', { name: parentFolder.name, level: (parentFolder.depth || 0) + 1 })
                  : t('folders.actions.rootLevel')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-secondary hover:text-main hover:bg-surface-elevated transition-colors"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-danger text-xs flex items-start gap-2">
              <i className="fa-solid fa-triangle-exclamation mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-main mb-1.5">
              {t('folders.actions.folderName')} <span className="text-danger">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('folders.actions.namePlaceholder')}
              className="w-full px-3 py-2 text-sm rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-main"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-main mb-1.5">{t('folders.actions.order')}</label>
            <input
              type="number"
              min={0}
              value={order}
              onChange={(e) => setOrder(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 text-sm rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-main"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-main mb-1.5">{t('folders.actions.descriptionOptional')}</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('folders.actions.descriptionPlaceholder')}
              className="w-full px-3 py-2 text-sm rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-main resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-subtle">
            <Button variant="secondary" size="md" type="button" onClick={onClose}>
              {t('folders.actions.cancel')}
            </Button>
            <Button variant="primary" size="md" type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <i className="fa-solid fa-spinner fa-spin mr-1.5" />
                  {t('folders.actions.saving')}
                </>
              ) : isEdit ? (
                t('folders.actions.update')
              ) : (
                t('folders.actions.create')
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};

// ═══════════════════════════════════════════════════════════════════
// 2. Move Folder Modal (With Circular Reference Prevention)
// ═══════════════════════════════════════════════════════════════════
interface MoveFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  folder: FolderItem | null;
  allFolders: FolderItem[];
  onConfirmMove: (folderId: number, targetParentId: number | null) => Promise<void>;
}

export const MoveFolderModal: React.FC<MoveFolderModalProps> = ({
  isOpen,
  onClose,
  folder,
  allFolders,
  onConfirmMove,
}) => {
  const { t } = useTranslation();
  const [selectedParentId, setSelectedParentId] = useState<string>(() =>
    folder?.parent_id ? String(folder.parent_id) : 'root'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !folder) return null;

  // Lọc ra các folder không thể làm cha: chính nó và con cháu của nó (để tránh vòng lặp)
  const isDescendant = (item: FolderItem, target: FolderItem): boolean => {
    if (item.id === target.id) return true;
    if (item.path && target.path && item.path.startsWith(target.path)) return true;
    return false;
  };

  const validTargets = allFolders.filter((item) => !isDescendant(item, folder));

  const handleMove = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      const targetId = selectedParentId === 'root' ? null : parseInt(selectedParentId, 10);
      await onConfirmMove(folder.id, targetId);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('folders.actions.moveError');
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-surface rounded-2xl border border-border-subtle shadow-xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between p-5 border-b border-border-subtle">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center">
              <i className="fa-solid fa-arrows-up-down-left-right text-base" />
            </div>
            <div>
              <h3 className="font-bold text-main text-base">{t('folders.actions.moveTitle')}</h3>
              <p className="text-xs text-secondary">
                {t('folders.actions.moveTarget')} <span className="font-semibold text-main">"{folder.name}"</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-secondary hover:text-main hover:bg-surface-elevated transition-colors"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-danger text-xs flex items-start gap-2">
              <i className="fa-solid fa-triangle-exclamation mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-main mb-1.5">
              {t('folders.actions.newParent')}
            </label>
            <select
              value={selectedParentId}
              onChange={(e) => setSelectedParentId(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 text-main"
            >
              <option value="root">{t('folders.actions.moveToRoot')}</option>
              {validTargets.map((item) => (
                <option key={item.id} value={String(item.id)}>
                  {`${'— '.repeat(item.depth || 0)}${t('folders.actions.moveOption', { name: item.name, level: item.depth || 0 })}`}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-muted mt-1.5">
              <i className="fa-solid fa-shield-halved mr-1 text-primary" />
              {t('folders.actions.moveHint')}
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-subtle">
            <Button variant="secondary" size="md" type="button" onClick={onClose}>
              {t('folders.actions.cancel')}
            </Button>
            <Button variant="primary" size="md" onClick={handleMove} disabled={isSubmitting}>
              {isSubmitting ? t('folders.actions.moving') : t('folders.actions.confirmMove')}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

// ═══════════════════════════════════════════════════════════════════
// 3. Delete Confirmation Modal (Cascade Warning)
// ═══════════════════════════════════════════════════════════════════
interface DeleteFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  folder: FolderItem | null;
  onConfirmDelete: (folderId: number) => Promise<void>;
}

export const DeleteFolderModal: React.FC<DeleteFolderModalProps> = ({
  isOpen,
  onClose,
  folder,
  onConfirmDelete,
}) => {
  const { t } = useTranslation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !folder) return null;

  const handleDelete = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      await onConfirmDelete(folder.id);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('folders.actions.deleteError');
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const childrenCount = folder.children_count || 0;
  const filesCount = folder.files_count || 0;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-surface rounded-2xl border border-danger/30 shadow-xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-150">
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-danger/10 text-danger flex items-center justify-center shrink-0">
              <i className="fa-solid fa-triangle-exclamation text-lg" />
            </div>
            <div>
              <h3 className="font-bold text-main text-base">{t('folders.actions.deleteTitle')}</h3>
              <p className="text-xs text-secondary mt-0.5">
                {t('folders.actions.deleteConfirm')} <strong className="text-danger">"{folder.name}"</strong>?
              </p>
            </div>
          </div>

          {(childrenCount > 0 || filesCount > 0) && (
            <div className="p-3.5 rounded-xl bg-danger/5 border border-danger/20 text-xs text-danger space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <i className="fa-solid fa-circle-exclamation" />
                {t('folders.actions.cascadeWarning')}
              </p>
              <ul className="list-disc list-inside space-y-0.5 text-secondary pl-1">
                {childrenCount > 0 && (
                  <li>
                    {t('folders.actions.cascadeChildren', { count: childrenCount })}
                  </li>
                )}
                {filesCount > 0 && (
                  <li>
                    {t('folders.actions.cascadeFiles', { count: filesCount })}
                  </li>
                )}
              </ul>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-danger text-xs">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" size="md" type="button" onClick={onClose}>
              {t('folders.actions.cancel')}
            </Button>
            <Button
              variant="danger"
              size="md"
              onClick={handleDelete}
              disabled={isSubmitting}
            >
              {isSubmitting ? t('folders.actions.deleting') : t('folders.actions.deletePermanent')}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
