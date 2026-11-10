import React, { useState, useMemo } from 'react';
import { FolderItem } from '@app-types/resource';
import { useTranslation } from '@i18n/translate';

interface FolderTreeViewProps {
  tree: FolderItem[];
  selectedFolderId: number | null;
  onSelectFolder: (folder: FolderItem) => void;
  onCreateChild: (parentFolder: FolderItem) => void;
  onEditFolder: (folder: FolderItem) => void;
  onMoveFolder: (folder: FolderItem) => void;
  onDeleteFolder: (folder: FolderItem) => void;
  className?: string;
}

interface FolderTreeNodeProps {
  node: FolderItem;
  level: number;
  selectedFolderId: number | null;
  expandedIds: Set<number>;
  toggleExpand: (id: number) => void;
  onSelectFolder: (folder: FolderItem) => void;
  onCreateChild: (parentFolder: FolderItem) => void;
  onEditFolder: (folder: FolderItem) => void;
  onMoveFolder: (folder: FolderItem) => void;
  onDeleteFolder: (folder: FolderItem) => void;
  searchTerm?: string;
}

const FolderTreeNode: React.FC<FolderTreeNodeProps> = ({
  node,
  level,
  selectedFolderId,
  expandedIds,
  toggleExpand,
  onSelectFolder,
  onCreateChild,
  onEditFolder,
  onMoveFolder,
  onDeleteFolder,
  searchTerm = '',
}) => {
  const { t } = useTranslation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const hasChildren = Boolean(node.children && node.children.length > 0);
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedFolderId === node.id;

  const matchesSearch = searchTerm
    ? node.name.toLowerCase().includes(searchTerm.toLowerCase())
    : false;

  return (
    <div className="select-none">
      <div
        className={`group relative flex items-center justify-between py-1.5 px-2 rounded-xl text-xs transition-all cursor-pointer ${
          isSelected
            ? 'bg-primary/15 text-primary font-bold shadow-2xs'
            : matchesSearch
            ? 'bg-amber-500/10 text-amber-600 font-semibold'
            : 'text-secondary hover:text-main hover:bg-surface-elevated'
        }`}
        style={{ paddingLeft: `${Math.max(8, level * 18 + 8)}px` }}
        onClick={() => onSelectFolder(node)}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Nút thu gọn / mở rộng */}
          {hasChildren ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(node.id);
              }}
              className="w-4 h-4 flex items-center justify-center text-muted hover:text-main rounded transition-transform"
            >
              <i
                className={`fa-solid fa-chevron-right text-[10px] transition-transform duration-200 ${
                  isExpanded ? 'rotate-90 text-primary' : ''
                }`}
              />
            </button>
          ) : (
            <span className="w-4 h-4 flex items-center justify-center text-muted/30">
              <span className="w-1.5 h-1.5 rounded-full bg-border-subtle" />
            </span>
          )}

          {/* Icon thư mục */}
          <i
            className={`fa-solid ${
              isSelected
                ? 'fa-folder-open text-primary'
                : hasChildren && isExpanded
                ? 'fa-folder-open text-amber-500'
                : 'fa-folder text-amber-500/80'
            } text-sm shrink-0`}
          />

          {/* Tên thư mục */}
          <span className="truncate flex-1 font-medium text-xs" title={node.name}>
            {node.name}
          </span>

          {/* Depth badge */}
          <span className="text-[10px] px-1 py-0.2 rounded bg-surface border border-border-subtle text-muted shrink-0 hidden group-hover:inline-block">
            C{node.depth || 0}
          </span>

          {/* Local badge */}
          {node.is_local && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-600 font-semibold border border-sky-500/20 shrink-0 flex items-center gap-0.5"
              title={t('folders.tree.localFolderTitle', { path: node.local_path || '' })}
            >
              <i className="fa-solid fa-laptop text-[8px]" />
              Local
            </span>
          )}

          {/* Badges số file / con */}
          {(node.files_count || 0) > 0 && (
            <span
              className="text-[10px] px-1.5 py-0.2 rounded-full bg-primary/10 text-primary font-semibold shrink-0"
              title={t('folders.tree.filesTitle', { count: node.files_count })}
            >
              {node.files_count}
            </span>
          )}
        </div>

        {/* Nút thao tác nhanh (Hiện khi hover) */}
        <div
          className="relative opacity-0 group-hover:opacity-100 flex items-center gap-1 shrink-0 ml-1 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            title={t('folders.tree.addSubfolder')}
            onClick={() => onCreateChild(node)}
            className="w-6 h-6 rounded-md hover:bg-surface text-secondary hover:text-primary flex items-center justify-center transition-colors"
          >
            <i className="fa-solid fa-plus text-[10px]" />
          </button>

          <button
            type="button"
            title={t('folders.tree.moreOptions')}
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="w-6 h-6 rounded-md hover:bg-surface text-secondary hover:text-main flex items-center justify-center transition-colors"
          >
            <i className="fa-solid fa-ellipsis-vertical text-[10px]" />
          </button>

          {/* Context Dropdown Menu */}
          {isMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsMenuOpen(false)}
              />
              <div className="absolute right-0 top-7 z-50 w-44 bg-surface border border-border-subtle rounded-xl shadow-lg p-1 text-xs space-y-0.5 animate-in fade-in zoom-in-95">
                <button
                  type="button"
                  onClick={() => {
                    setIsMenuOpen(false);
                    onCreateChild(node);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-secondary hover:text-primary hover:bg-primary/10 text-left transition-colors font-medium"
                >
                  <i className="fa-solid fa-folder-plus text-primary w-4 text-center" />
                  {t('folders.tree.addSubfolder')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsMenuOpen(false);
                    onEditFolder(node);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-secondary hover:text-main hover:bg-surface-elevated text-left transition-colors"
                >
                  <i className="fa-solid fa-pen-to-square text-amber-500 w-4 text-center" />
                  {t('folders.tree.rename')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsMenuOpen(false);
                    onMoveFolder(node);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-secondary hover:text-main hover:bg-surface-elevated text-left transition-colors"
                >
                  <i className="fa-solid fa-arrows-up-down-left-right text-sky-500 w-4 text-center" />
                  {t('folders.tree.move')}
                </button>
                <div className="h-px bg-border-subtle my-0.5" />
                <button
                  type="button"
                  onClick={() => {
                    setIsMenuOpen(false);
                    onDeleteFolder(node);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-danger hover:bg-danger/10 text-left transition-colors font-medium"
                >
                  <i className="fa-solid fa-trash w-4 text-center" />
                  {t('folders.tree.delete')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Hiển thị con cháu đệ quy */}
      {hasChildren && isExpanded && (
        <div className="relative border-l border-border-subtle/50 ml-3.5 my-0.5 space-y-0.5">
          {node.children!.map((child) => (
            <FolderTreeNode
              key={child.id}
              node={child}
              level={level + 1}
              selectedFolderId={selectedFolderId}
              expandedIds={expandedIds}
              toggleExpand={toggleExpand}
              onSelectFolder={onSelectFolder}
              onCreateChild={onCreateChild}
              onEditFolder={onEditFolder}
              onMoveFolder={onMoveFolder}
              onDeleteFolder={onDeleteFolder}
              searchTerm={searchTerm}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FolderTreeView: React.FC<FolderTreeViewProps> = ({
  tree,
  selectedFolderId,
  onSelectFolder,
  onCreateChild,
  onEditFolder,
  onMoveFolder,
  onDeleteFolder,
  className = '',
}) => {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => {
    // Mặc định mở rộng cấp 0 và cấp 1
    const ids = new Set<number>();
    tree.forEach((root) => {
      ids.add(root.id);
      root.children?.forEach((c) => ids.add(c.id));
    });
    return ids;
  });

  // Thu gom toàn bộ ID trong cây
  const allIds = useMemo(() => {
    const ids: number[] = [];
    const traverse = (items: FolderItem[]) => {
      items.forEach((item) => {
        ids.push(item.id);
        if (item.children) traverse(item.children);
      });
    };
    traverse(tree);
    return ids;
  }, [tree]);

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExpandAll = () => {
    setExpandedIds(new Set(allIds));
  };

  const handleCollapseAll = () => {
    setExpandedIds(new Set());
  };

  return (
    <div className={`flex flex-col h-full bg-surface rounded-2xl border border-border-subtle overflow-hidden ${className}`}>
      {/* Header cây thư mục & Toolbar */}
      <div className="p-3 border-b border-border-subtle space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-sitemap text-primary text-xs" />
            <span className="font-bold text-main text-xs">{t('folders.tree.treeTitle')}</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-secondary">
            <button
              type="button"
              onClick={handleExpandAll}
              className="px-1.5 py-0.5 rounded hover:bg-surface-elevated hover:text-primary transition-colors"
              title={t('folders.tree.expandAllHint')}
            >
              <i className="fa-solid fa-angles-down text-[10px] mr-1" />
              {t('folders.tree.expandAll')}
            </button>
            <span className="text-muted">|</span>
            <button
              type="button"
              onClick={handleCollapseAll}
              className="px-1.5 py-0.5 rounded hover:bg-surface-elevated hover:text-primary transition-colors"
              title={t('folders.tree.collapseAllHint')}
            >
              <i className="fa-solid fa-angles-up text-[10px] mr-1" />
              {t('folders.tree.collapseAll')}
            </button>
          </div>
        </div>

        {/* Ô tìm kiếm trong cây */}
        <div className="relative">
          <i className="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-muted text-xs" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={t('folders.tree.filterPlaceholder')}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-border-subtle bg-surface focus:outline-none focus:border-primary text-main"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main"
            >
              <i className="fa-solid fa-xmark text-xs" />
            </button>
          )}
        </div>
      </div>

      {/* Danh sách cây cuộn được */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5 custom-scrollbar">
        {tree.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted">
            <i className="fa-solid fa-folder-open text-2xl mb-2 text-muted/40 block" />
            {t('folders.tree.empty')}
          </div>
        ) : (
          tree.map((node) => (
            <FolderTreeNode
              key={node.id}
              node={node}
              level={0}
              selectedFolderId={selectedFolderId}
              expandedIds={expandedIds}
              toggleExpand={toggleExpand}
              onSelectFolder={onSelectFolder}
              onCreateChild={onCreateChild}
              onEditFolder={onEditFolder}
              onMoveFolder={onMoveFolder}
              onDeleteFolder={onDeleteFolder}
              searchTerm={searchTerm}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default FolderTreeView;
