import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AlertModal from '@components/common/AlertModal';
import { ActivePageId } from '@app-types/navigation';
import { pageIdToPath } from '@lib/routes';
import {
  uploadDocumentAsync,
  getUploadProgress,
  askQuestion,
  askQuestionStream,
  getDocuments,
  getCategories,
  getDocumentFile,
  deleteDocuments,
  deleteDocument,
  previewDocument,
  reclassifyDocument,
  getAISettings,
} from '../../api';
import { t as translate, useTranslation, type SupportedLanguage } from '@i18n/translate';
import { usePermissions } from '@lib/permissions';
import '@styles/ai-chat.css';

interface AiAssistantPageProps {
  onNavigate?: (page: ActivePageId) => void;
}

interface CitationSource {
  index?: number;
  file_name?: string;
  page?: number | string | null;
  section?: string | number;
  chunk_id?: string | number;
  source_type?: string | null;
  source_id?: number | string | null;
  preview?: string;
  score?: number;
  label?: string;
  code?: string;
  targetPage?: ActivePageId;
  type?: 'incoming' | 'outgoing' | 'confidential' | 'approval';
}

interface TargetDocInfo {
  filename: string;
  label?: string;
  category?: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  time: string;
  citations?: CitationSource[];
  quickPrompts?: string[];
  targetDoc?: TargetDocInfo;
  targetDocs?: TargetDocInfo[];
  isError?: boolean;
  retryText?: string;
}

interface ChatSession {
  id: string;
  title: string;
  timeLabel: 'Hôm nay' | 'Hôm qua' | '7 ngày trước';
  snippet: string;
  messages: ChatMessage[];
}

interface DocItem {
  filename: string;
  category?: string;
  uploaded_at?: string;
  size?: number | null;
  file_type?: string;
  source_type?: string;
  source_id?: number;
  is_managed?: boolean;
}

interface CategoryItem {
  name: string;
  count: number;
}

export interface SubFolderGroup {
  name: string;
  docs: DocItem[];
}

export interface RootFolderGroup {
  name: string;
  subFolders: Record<string, SubFolderGroup>;
  directDocs: DocItem[];
  totalCount: number;
}

const EMPTY_MESSAGES: ChatMessage[] = [];
const MAX_QUESTION_LENGTH = 4000;
const MAX_PINNED_DOCUMENTS = 5;

const SOFT_FALLBACK_NOTE_REGEX =
  /(?:^|\n)\s*(?:\*{1,2}|_{1,2})?\s*(\((?:Không có tài liệu cụ thể được ghim\. Phản hồi dựa trên nghiệp vụ hành chính tổng hợp|No specific document is pinned\. Response is based on general administrative best practices)\))\s*(?:\*{1,2}|_{1,2})?\s*(?=\n|$)/gi;

function splitSoftFallbackNote(text: string): { body: string; note: string | null } {
  let extractedNote: string | null = null;
  const cleaned = text
    .replace(SOFT_FALLBACK_NOTE_REGEX, (_match, noteText: string) => {
      extractedNote = noteText;
      return '\n';
    })
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  return { body: cleaned, note: extractedNote };
}

function createMessageTimestamp(): number {
  return Date.now();
}

interface AIConfig {
  provider?: string;
  llm_model?: string;
  api_key?: string;
  [key: string]: unknown;
}

interface UploadProgress {
  status?: string;
  message?: string;
  [key: string]: unknown;
}

interface ApiError {
  data?: { code?: string; detail?: unknown };
  response?: { data?: { detail?: unknown } };
}

interface SpeechRecognitionResultEvent extends Event {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionInstance;
}

function getSafeApiErrorDetail(error: unknown, fallback: string): string {
  if (typeof error !== 'object' || error === null) return fallback;
  const apiError = error as ApiError;
  const detail = apiError.data?.detail ?? apiError.response?.data?.detail;
  return typeof detail === 'string' && detail.trim() ? detail : fallback;
}

function createDefaultSession(id: string = 'session-default', lang: SupportedLanguage = 'vi'): ChatSession {
  const tr = (key: string) => translate(key, undefined, lang);
  return {
    id,
    title: tr('aiAssistant.defaultSession.title'),
    timeLabel: 'Hôm nay',
    snippet: tr('aiAssistant.defaultSession.snippet'),
    messages: [
      {
        id: `msg-welcome-${Date.now()}`,
        sender: 'ai',
        text: tr('aiAssistant.defaultSession.welcome'),
        time: new Date().toLocaleTimeString(lang === 'en' ? 'en-US' : 'vi-VN', { hour: '2-digit', minute: '2-digit' }),
        quickPrompts: [1, 2, 3, 4].map((i) => tr(`aiAssistant.defaultSession.quickPrompt${i}`)),
      },
    ],
  };
}

function isDefaultSessionTitle(title: string): boolean {
  const defaultTitles = [
    translate('aiAssistant.defaultSession.title', undefined, 'vi'),
    translate('aiAssistant.defaultSession.title', undefined, 'en'),
    'Tra cứu quy trình & văn bản',
    'Cuộc trò chuyện mới',
    'New Conversation',
    'New Chat',
  ];
  return defaultTitles.includes(title) || title.startsWith('Hội thoại mới');
}

function isDefaultSessionSnippet(snippet: string): boolean {
  return [
    translate('aiAssistant.defaultSession.snippet', undefined, 'vi'),
    translate('aiAssistant.defaultSession.snippet', undefined, 'en'),
  ].includes(snippet);
}

// 4 Thẻ gợi ý chuẩn nhận diện thương hiệu TLBM; nội dung dịch nằm ở aiAssistant.templates.<key>
const PROMPT_TEMPLATES = [
  {
    key: 'incoming',
    icon: 'fa-inbox',
    iconClass: 'text-primary bg-primary-subtle border-primary/30',
  },
  {
    key: 'confidential',
    icon: 'fa-shield-halved',
    iconClass: 'text-danger bg-danger-subtle border-danger/30',
  },
  {
    key: 'signing',
    icon: 'fa-file-signature',
    iconClass: 'text-warning-text bg-warning-subtle border-warning/30',
  },
  {
    key: 'organization',
    icon: 'fa-sitemap',
    iconClass: 'text-success bg-success-subtle border-success/30',
  },
];

function getSessionUser() {
  try {
    const raw = localStorage.getItem('tlbm_session');
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        username: typeof parsed.username === 'string' ? parsed.username : '',
        fullName: parsed.fullName || parsed.full_name || '',
        role: parsed.roleTitle || translate('aiAssistant.msg.defaultRole'),
      };
    }
  } catch {
    // fallback
  }
  return {
    username: '',
    fullName: '',
    role: translate('aiAssistant.msg.defaultRole'),
  };
}

const CHAT_HISTORY_STORAGE_VERSION = '3';
const CHAT_HISTORY_STORAGE_VERSION_KEY = 'tlbm_chat_sessions_storage_version';

function getChatStorageKey(username: string): string | null {
  if (localStorage.getItem(CHAT_HISTORY_STORAGE_VERSION_KEY) !== CHAT_HISTORY_STORAGE_VERSION) {
    // The legacy v2 key was shared across accounts and cannot be safely assigned.
    // Keep account-scoped keys so a version marker update never erases their history.
    localStorage.removeItem('tlbm_chat_sessions_v2');
    localStorage.setItem(CHAT_HISTORY_STORAGE_VERSION_KEY, CHAT_HISTORY_STORAGE_VERSION);
  }
  return username ? `tlbm_chat_sessions_${encodeURIComponent(username)}` : null;
}

// Render a safe Markdown subset with React nodes; raw HTML is always escaped.
function formatInline(
  str: string = '',
  onInternalLink?: (href: string) => void
): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\$(?!\s)[^$\n]+?(?<!\s)\$(?!\d)|\[[^\]]+\]\((?:https?:\/\/|\/)[^)]+\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      parts.push(str.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(<code key={match.index} className="rounded bg-surface-hover px-1">{token.slice(1, -1)}</code>);
    } else if (token.startsWith('$') && token.endsWith('$') && token.length > 2) {
      parts.push(<code key={match.index} className="ai-math-inline">{token.slice(1, -1)}</code>);
    } else if (token.startsWith('[')) {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const href = link?.[2];
      const safeHref = href && ((href.startsWith('/') && !href.startsWith('//')) || /^https?:\/\//i.test(href));
      parts.push(safeHref ? (
        <a
          key={match.index}
          href={href}
          target={href?.startsWith('/') ? undefined : '_blank'}
          rel="noreferrer"
          className="text-primary underline"
          onClick={
            href?.startsWith('/') && onInternalLink
              ? (event) => {
                  event.preventDefault();
                  onInternalLink(href);
                }
              : undefined
          }
        >
          {link?.[1]}
        </a>
      ) : token);
    } else {
      parts.push(<em key={match.index}>{token.slice(1, -1)}</em>);
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < str.length) {
    parts.push(str.substring(lastIndex));
  }
  return parts.length > 0 ? parts : [str];
}

// Formatter Markdown đa dòng
function FormattedMessage({
  text = '',
  onInternalLink,
}: {
  text: string;
  onInternalLink?: (href: string) => void;
}) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  const isTableSeparator = (line: string) => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
  const parseTableRow = (line: string) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());

  let lineIdx = 0;
  while (lineIdx < lines.length) {
    const line = lines[lineIdx];
    const trimmed = line.trim();
    if (trimmed.startsWith('```')) {
      const codeLines: string[] = [];
      lineIdx += 1;
      while (lineIdx < lines.length && !lines[lineIdx].trim().startsWith('```')) {
        codeLines.push(lines[lineIdx]);
        lineIdx += 1;
      }
      elements.push(
        <pre key={`code-${lineIdx}`} className="my-2 max-w-full overflow-x-auto rounded-lg bg-surface-hover p-3 text-sm">
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
      lineIdx += 1;
      continue;
    }
    if (trimmed.startsWith('$$')) {
      const singleLineMatch = /^\$\$(.+)\$\$$/.exec(trimmed);
      if (singleLineMatch) {
        elements.push(
          <pre key={`math-${lineIdx}`} className="ai-math-block">
            <code>{singleLineMatch[1].trim()}</code>
          </pre>
        );
        lineIdx += 1;
        continue;
      }
      const mathLines: string[] = [];
      lineIdx += 1;
      while (lineIdx < lines.length && !lines[lineIdx].trim().startsWith('$$')) {
        mathLines.push(lines[lineIdx]);
        lineIdx += 1;
      }
      elements.push(
        <pre key={`math-${lineIdx}`} className="ai-math-block">
          <code>{mathLines.join('\n')}</code>
        </pre>
      );
      lineIdx += 1;
      continue;
    }
    if (!trimmed) {
      elements.push(<div key={`br-${lineIdx}`} className="h-2 my-1" />);
      lineIdx += 1;
      continue;
    }
    if (trimmed.includes('|') && lineIdx + 1 < lines.length && isTableSeparator(lines[lineIdx + 1])) {
      const headers = parseTableRow(trimmed);
      lineIdx += 2;
      const rows: string[][] = [];
      while (lineIdx < lines.length && lines[lineIdx].includes('|') && lines[lineIdx].trim()) {
        rows.push(parseTableRow(lines[lineIdx]));
        lineIdx += 1;
      }
      elements.push(
        <div key={`table-${lineIdx}`} className="my-2 max-w-full overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead><tr>{headers.map((cell, index) => <th key={index} className="border border-border-subtle bg-surface-hover px-2 py-1">{formatInline(cell, onInternalLink)}</th>)}</tr></thead>
            <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex} className="border border-border-subtle px-2 py-1">{formatInline(row[cellIndex] || '', onInternalLink)}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
      continue;
    }
    if (/^#{1,3}\s/.test(trimmed)) {
      elements.push(<h4 key={`heading-${lineIdx}`} className="bubble-h4 text-base font-bold my-2 text-primary">{formatInline(trimmed.replace(/^#{1,3}\s+/, ''), onInternalLink)}</h4>);
      lineIdx += 1;
      continue;
    }
    if (trimmed.startsWith('> ')) {
      elements.push(<blockquote key={`quote-${lineIdx}`} className="my-1 border-l-2 border-primary ps-3 text-secondary">{formatInline(trimmed.slice(2), onInternalLink)}</blockquote>);
      lineIdx += 1;
      continue;
    }
    if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      const ordered = /^\d+\.\s+/.test(trimmed);
      const items: string[] = [];
      while (lineIdx < lines.length && (ordered ? /^\s*\d+\.\s+/.test(lines[lineIdx]) : /^\s*[-*]\s+/.test(lines[lineIdx]))) {
        items.push(lines[lineIdx].trim().replace(ordered ? /^\d+\.\s+/ : /^[-*]\s+/, ''));
        lineIdx += 1;
      }
      const List = ordered ? 'ol' : 'ul';
      elements.push(<List key={`list-${lineIdx}`} className={`ps-5 mb-2 space-y-1 text-sm ${ordered ? 'list-decimal' : 'list-disc'}`}>
        {items.map((item, index) => <li key={index} className="mb-0.5">{formatInline(item, onInternalLink)}</li>)}
      </List>);
      continue;
    }
    elements.push(<p key={`p-${lineIdx}`} className="bubble-p text-sm leading-relaxed mb-1.5">{formatInline(line, onInternalLink)}</p>);
    lineIdx += 1;
  }

  return <div className="message-content">{elements}</div>;
}

// Modal Xem Trước Tài Liệu
interface PreviewModalProps {
  filename: string;
  onClose: () => void;
}

interface PreviewData {
  full_text?: string;
  render_mode?: 'pdf' | 'text' | 'image';
  file_url?: string;
  file_type?: string;
  total_pages?: number;
  pages?: Array<{ page?: number; text: string }>;
}

const IMAGE_PREVIEW_RE = /\.(png|jpe?g|webp|bmp|tiff?|gif)$/i;

function DocumentPreviewModal({ filename, onClose }: PreviewModalProps) {
  const { t, currentLang } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<PreviewData | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'full' | 'pages'>('full');

  const displayTitle = filename;

  const isDocx = filename.toLowerCase().endsWith('.docx') || filename.toLowerCase().endsWith('.doc');
  const isPdf = data?.render_mode === 'pdf' || filename.toLowerCase().endsWith('.pdf');
  const isImage = data?.render_mode === 'image' || IMAGE_PREVIEW_RE.test(filename);
  const needsBinaryBlob = isPdf || isImage;
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    previewDocument(filename)
      .then((res: PreviewData) => {
        if (!cancelled) {
          setData(res);
          setError('');
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(translate('aiAssistant.inline.unableToLoadDocumentContent', undefined, currentLang));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [filename, currentLang]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleCopyAll = async () => {
    if (!data?.full_text) return;
    try {
      await navigator.clipboard.writeText(data.full_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const handleDownload = async () => {
    try {
      const blob = await getDocumentFile(filename);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = displayTitle;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert(t('aiAssistant.inline.unableToDownloadFile'));
    }
  };

  useEffect(() => {
    if (!needsBinaryBlob) return;

    let cancelled = false;
    let objectUrl: string | null = null;
    getDocumentFile(filename)
      .then((file) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(file);
        setBlobUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) {
          setError(
            isImage
              ? translate('aiAssistant.previewModal.unableToLoadImage', undefined, currentLang)
              : translate('aiAssistant.inline.unableToLoadPdfFile', undefined, currentLang)
          );
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [filename, needsBinaryBlob, isImage, currentLang]);

  const fileUrl = needsBinaryBlob ? blobUrl : null;
  const iconClass = isPdf ? 'icon-pdf' : isDocx ? 'icon-docx' : 'icon-txt';
  const iconFa = isPdf ? 'fa-file-pdf' : isImage ? 'fa-image' : isDocx ? 'fa-file-word' : 'fa-file-lines';

  return (
    <div className="preview-backdrop" onClick={onClose}>
      <div
        className={`preview-panel ${isPdf ? 'preview-panel-pdf' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Thanh Công Cụ */}
        <div className="preview-header">
          <div className="preview-title-area">
            <div className={`preview-title-icon ${iconClass}`}>
              <i className={`fa-solid ${iconFa}`} />
            </div>
            <div className="preview-title-text-group">
              <div className="preview-filename" title={filename}>
                {displayTitle}
              </div>
              {data && (
                <div className="preview-meta">
                  <span className="preview-badge badge-type">{data.file_type || (isPdf ? 'PDF' : isImage ? 'IMG' : 'DOCX')}</span>
                  {!needsBinaryBlob && data.total_pages ? (
                    <span className="preview-badge badge-pages">
                      <i className="fa-solid fa-layer-group me-1" />
                      {t('aiAssistant.previewModal.byParts', { count: data.total_pages })}
                    </span>
                  ) : null}
                  <span className="preview-badge badge-size" title={t('aiAssistant.previewModal.fileArchive')}>
                    <i className="fa-solid fa-file-code me-1" />
                    {filename}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="preview-header-actions">
            {data && !needsBinaryBlob && (
              <button
                type="button"
                className="preview-action-btn copy-btn"
                onClick={handleCopyAll}
                title={t('aiAssistant.previewModal.copyAll')}
              >
                <i className={`fa-solid ${copied ? 'fa-check text-success' : 'fa-copy'}`} />
                <span>{copied ? t('aiAssistant.previewModal.copied') : t('aiAssistant.previewModal.copyAll')}</span>
              </button>
            )}

            <button
              type="button"
              className="preview-action-btn download-btn"
              onClick={handleDownload}
              title={t('aiAssistant.previewModal.download')}
            >
              <i className="fa-solid fa-download" />
              <span>{t('aiAssistant.previewModal.download')}</span>
            </button>

            {needsBinaryBlob && fileUrl && (
              <a
                href={fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="preview-action-btn open-tab-btn"
                title={t('aiAssistant.previewModal.openNewTab')}
              >
                <i className="fa-solid fa-arrow-up-right-from-square" />
                <span>{t('aiAssistant.previewModal.openNewTab')}</span>
              </a>
            )}

            <button
              type="button"
              className="preview-close-btn"
              onClick={onClose}
              title={t('aiAssistant.previewModal.close')}
            >
              <i className="fa-solid fa-xmark" />
            </button>
          </div>
        </div>

        {/* Tab chuyển đổi toàn văn vs phân đoạn */}
        {data && !needsBinaryBlob && (data.total_pages || 0) > 1 && (
          <div className="preview-tabs">
            <button
              type="button"
              className={`preview-tab ${activeTab === 'full' ? 'active' : ''}`}
              onClick={() => setActiveTab('full')}
            >
              <i className="fa-solid fa-align-left me-1" />
              {t('aiAssistant.previewModal.fullText')}
            </button>
            <button
              type="button"
              className={`preview-tab ${activeTab === 'pages' ? 'active' : ''}`}
              onClick={() => setActiveTab('pages')}
            >
              <i className="fa-solid fa-layer-group me-1" />
              {t('aiAssistant.previewModal.byParts', { count: data.total_pages })}
            </button>
          </div>
        )}

        {/* Khung nội dung tài liệu */}
        <div className="preview-body">
          {loading && (
            <div className="d-flex align-items-center justify-content-center p-5 text-secondary flex-1">
              <span className="spinner-border spinner-border-sm me-2 text-primary" />
              {t('aiAssistant.previewModal.loading')}
            </div>
          )}

          {error && (
            <div className="alert alert-danger d-flex align-items-center gap-2 m-3">
              <i className="fa-solid fa-triangle-exclamation" />
              <span>{error}</span>
            </div>
          )}

          {data && !loading && isPdf && fileUrl && (
            <div className="preview-pdf-container">
              <iframe src={fileUrl} className="preview-pdf-iframe" title={displayTitle} />
            </div>
          )}

          {data && !loading && isImage && fileUrl && (
            <div className="preview-image-container">
              <img src={fileUrl} alt={displayTitle} className="preview-image-viewer" />
            </div>
          )}

          {data && !loading && !needsBinaryBlob && activeTab === 'full' && (
            <div className="preview-paper">
              <div className="preview-paper-content">
                {data.full_text || t('aiAssistant.previewModal.noContent')}
              </div>
            </div>
          )}

          {data && !loading && !needsBinaryBlob && activeTab === 'pages' && data.pages && (
            <div className="preview-pages-container">
              {data.pages.map((page, idx) => (
                <div key={idx} className="preview-page-card">
                  <div className="preview-page-header">
                    <i className="fa-solid fa-bookmark me-1" />
                    {t('aiAssistant.previewModal.part', { num: page.page || idx + 1 })}
                  </div>
                  <div className="preview-paper-content">
                    {page.text}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const BUSINESS_SPEC_PAGE_MAP: Record<string, ActivePageId> = {
  'branch-01-dashboard': 'dashboard',
  'branch-02-documents': 'documents_incoming',
  'branch-03-records': 'records',
  'branch-04-templates': 'resources',
  'branch-05-signing': 'approvals',
  'branch-06-tasks': 'tasks',
  'branch-07-system': 'organizations',
};

function deduplicateCitations(sources: CitationSource[]): CitationSource[] {
  const seen = new Set<string>();
  return sources.filter((src) => {
    const isEntity =
      src.source_type === 'vanbanden' ||
      src.source_type === 'vanbandi' ||
      src.source_type === 'tailieu' ||
      src.source_type === 'business_spec';
    const key =
      isEntity && src.source_id != null
        ? `${src.source_type}:${src.source_id}`
        : `${src.source_type || 'doc'}:${src.file_name || src.label || ''}:${src.page ?? src.section ?? ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// Component Chính AiAssistantPage
function CitationsBox({
  sources,
  onPreview,
  onNavigate,
}: {
  sources?: CitationSource[];
  onPreview?: (filename: string) => void;
  onNavigate?: (page: ActivePageId, urlOverride?: string) => void;
}) {
  const { t } = useTranslation();
  const [isCollapsed, setIsCollapsed] = useState(true);
  if (!sources || sources.length === 0) return null;

  const uniqueSources = deduplicateCitations(sources);
  const toggleLabel = isCollapsed
    ? t('aiAssistant.toggleCitationsExpand')
    : t('aiAssistant.toggleCitationsCollapse');

  return (
    <div className={`ai-citations-box ${isCollapsed ? 'is-collapsed' : ''}`}>
      <button
        type="button"
        className="citations-toggle-btn"
        onClick={() => setIsCollapsed((prev) => !prev)}
        aria-expanded={!isCollapsed}
        aria-label={toggleLabel}
        title={toggleLabel}
      >
        <span className="citations-title">
          <i className="fa-solid fa-link" />
          <span>{t('aiAssistant.citations')}</span>
          <span className="citations-count-badge">
            {t('aiAssistant.citationsCount', { count: uniqueSources.length })}
          </span>
        </span>
        <i
          className={`fa-solid ${isCollapsed ? 'fa-chevron-down' : 'fa-chevron-up'} citations-chevron`}
          aria-hidden="true"
        />
      </button>

      {!isCollapsed && (
        <div className="citations-list">
        {uniqueSources.map((src, idx) => {
          const defaultDocLabel = t('aiAssistant.inline.documentValue', { value: idx + 1 });
          const fileName = src.file_name || src.label || defaultDocLabel;
          const code = src.code || (src.page ? `${t('aiAssistant.inline.page')}${src.page}` : src.section ? `${t('aiAssistant.inline.section')}${src.section}` : `${t('aiAssistant.inline.part')}#${idx + 1}`);

          const isConfidential = src.type === 'confidential';
          const isBusinessSpec = src.source_type === 'business_spec';

          const handleClick = () => {
            const sqlRouteMap: Partial<Record<string, { page: ActivePageId; path: string }>> = {
              vanbanden: { page: 'documents_incoming', path: '/documents/incoming' },
              vanbandi: { page: 'documents_outgoing', path: '/documents/outgoing' },
              tailieu: { page: 'resources', path: '/resources' },
            };
            const sqlTarget = sqlRouteMap[src.source_type || ''];
            if (sqlTarget && onNavigate) {
              const detailUrl = src.source_id != null
                ? `${sqlTarget.path}?detail=${encodeURIComponent(String(src.source_id))}`
                : undefined;
              onNavigate(sqlTarget.page, detailUrl);
            } else if (isBusinessSpec && onNavigate) {
              const mappedPage = src.targetPage || BUSINESS_SPEC_PAGE_MAP[String(src.source_id || '')] || 'dashboard';
              onNavigate(mappedPage);
            } else if (src.targetPage && onNavigate) {
              onNavigate(src.targetPage);
            } else if (src.file_name && onPreview) {
              onPreview(src.file_name);
            }
          };

          return (
            <button
              key={`${src.source_type || 'doc'}-${src.source_id ?? src.file_name ?? idx}-${idx}`}
              type="button"
              className={`citation-pill ${isConfidential ? 'confidential' : ''} ${isBusinessSpec ? 'business-spec' : ''} ${src.type || ''}`}
              onClick={handleClick}
              title={`${t('aiAssistant.viewDocument')}: ${fileName}`}
            >
              <i
                className={`fa-solid ${
                  isConfidential
                    ? 'fa-shield-halved'
                    : isBusinessSpec
                    ? 'fa-diagram-project'
                    : fileName.toLowerCase().endsWith('.pdf')
                    ? 'fa-file-pdf'
                    : 'fa-file-lines'
                }`}
              />
              <span className="citation-name">{fileName}</span>
              {isBusinessSpec && <span className="citation-code">{t('aiAssistant.businessSpec')}</span>}
              <span className="citation-code">{code}</span>
              <i className="fa-solid fa-arrow-up-right-from-square citation-ext-icon" />
            </button>
          );
        })}
        </div>
      )}
    </div>
  );
}

// Component Chính AiAssistantPage
export default function AiAssistantPage({ onNavigate }: AiAssistantPageProps) {
  const { t, currentLang } = useTranslation();
  const sessionUser = getSessionUser();
  const location = useLocation();
  const routerNavigate = useNavigate();
  const navigateToCitation = (page: ActivePageId, urlOverride?: string) => {
    if (urlOverride) {
      routerNavigate(urlOverride);
      return;
    }
    if (onNavigate) onNavigate(page);
    else routerNavigate(pageIdToPath(page));
  };
  const handleInternalLink = useCallback((href: string) => {
    routerNavigate(href);
  }, [routerNavigate]);
  const { loaded: aiPermissionLoaded, can, isSystemAdmin } = usePermissions();
  // Quản trị hệ thống (superuser hoặc nhóm ADMIN) lấy từ quyền thật, khớp cổng _require_ai_admin của API.
  const currentUser = { ...sessionUser, isAdmin: isSystemAdmin };
  const canUseAI = aiPermissionLoaded && can('use_aiassistant');
  // Chat input states
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth <= 860;
    }
    return false;
  });

  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth > 860;
    }
    return true;
  });
  const sidebarRef = useRef<HTMLElement>(null);

  // Tự động đóng mở sidebar và cập nhật isMobile khi chuyển đổi giữa Desktop và Mobile
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mql = window.matchMedia('(max-width: 860px)');
    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      setIsSidebarOpen(!e.matches);
    };
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);
  useEffect(() => {
    if (!isMobile || !isSidebarOpen || !sidebarRef.current) return;
    const sidebar = sidebarRef.current;
    const selector = 'a[href], button:not([disabled]), input:not([disabled]):not([type="file"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const getFocusable = () => Array.from(sidebar.querySelectorAll<HTMLElement>(selector));
    getFocusable()[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setIsSidebarOpen(false);
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = getFocusable();
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !sidebar.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !sidebar.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMobile, isSidebarOpen]);
  const [sidebarTab, setSidebarTab] = useState<'sessions' | 'docs'>('sessions');
  const [sessionSearch, setSessionSearch] = useState('');
  const [docSearch, setDocSearch] = useState('');
  const [collapsedRoots, setCollapsedRoots] = useState<Record<string, boolean>>({});
  const [collapsedSubs, setCollapsedSubs] = useState<Record<string, boolean>>({});

  const toggleRoot = (rootName: string) => {
    setCollapsedRoots((prev) => ({
      ...prev,
      [rootName]: !prev[rootName],
    }));
  };

  const toggleSub = (subKey: string) => {
    setCollapsedSubs((prev) => ({
      ...prev,
      [subKey]: !prev[subKey],
    }));
  };

  // Khóa lưu trữ cục bộ riêng biệt theo tài khoản để cách ly dữ liệu
  const storageKey = getChatStorageKey(currentUser.username);

  // Sessions state (Đọc từ localStorage với fallback thông minh)
  const [chatHistoryState, setChatHistoryState] = useState(() => {
    let initialSessions = [createDefaultSession('session-default', currentLang)];
    if (storageKey) {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed) && parsed.length > 0) {
            initialSessions = parsed;
          }
        }
      } catch {
        // fallback to default
      }
    }
    return {
      storageKey,
      sessions: initialSessions,
      activeSessionId: initialSessions[0].id,
    };
  });
  const activeChatHistoryState = chatHistoryState.storageKey === storageKey
    ? chatHistoryState
    : (() => {
        let nextSessions = [createDefaultSession('session-default', currentLang)];
        if (storageKey) {
          try {
            const saved = localStorage.getItem(storageKey);
            if (saved) {
              const parsed = JSON.parse(saved);
              if (Array.isArray(parsed) && parsed.length > 0) {
                nextSessions = parsed;
              }
            }
          } catch {
            // fallback
          }
        }
        return { storageKey, sessions: nextSessions, activeSessionId: nextSessions[0].id };
      })();
  const isChatHistoryReady = chatHistoryState.storageKey === storageKey;
  const sessions = activeChatHistoryState.sessions;
  const activeSessionId = activeChatHistoryState.activeSessionId;

  const updateChatHistory = (update: (current: ChatSession[]) => ChatSession[]) => {
    setChatHistoryState((current) => {
      if (current.storageKey !== storageKey) return current;
      return { ...current, sessions: update(current.sessions) };
    });
  };

  const setActiveSessionId = (id: string) => {
    setTargetDocuments([]);
    setChatHistoryState((current) => {
      if (current.storageKey !== storageKey) return current;
      return { ...current, activeSessionId: id };
    });
  };

  // Tự động đồng bộ và lưu sessions vào localStorage khi có thay đổi
  useEffect(() => {
    if (storageKey && isChatHistoryReady && activeChatHistoryState.sessions.length > 0) {
      localStorage.setItem(storageKey, JSON.stringify(activeChatHistoryState.sessions));
    }
  }, [activeChatHistoryState, storageKey, isChatHistoryReady]);

  // Luôn đảm bảo activeSession trỏ đúng tới phiên đang chọn (hoặc phiên đầu tiên)
  const activeSession = isChatHistoryReady
    ? sessions.find((s) => s.id === activeSessionId) || sessions[0] || null
    : null;
  const messages = activeSession?.messages || EMPTY_MESSAGES;

  // Knowledge base state
  const [documents, setDocuments] = useState<DocItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const urlPreviewFilename = useMemo(
    () => new URLSearchParams(location.search).get('preview'),
    [location.search]
  );
  const [manualPreviewFilename, setManualPreviewFilename] = useState<string | null>(null);
  const [dismissedUrlPreview, setDismissedUrlPreview] = useState<string | null>(null);
  const previewFilename =
    manualPreviewFilename ??
    (urlPreviewFilename && dismissedUrlPreview !== urlPreviewFilename ? urlPreviewFilename : null);
  const setPreviewFilename = (filename: string | null) => {
    setManualPreviewFilename(filename);
    if (filename === null && urlPreviewFilename) {
      setDismissedUrlPreview(urlPreviewFilename);
    }
  };
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null);
  const [isCategoryDropdownOpen, setIsCategoryDropdownOpen] = useState(false);
  const categoryDropdownRef = useRef<HTMLDivElement>(null);
  const [docSourceFilter, setDocSourceFilter] = useState<'all' | 'managed' | 'uploaded'>('all');
  const [isDocSourceDropdownOpen, setIsDocSourceDropdownOpen] = useState(false);
  const docSourceDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isCategoryDropdownOpen) return;
    const handlePointerDown = (e: MouseEvent) => {
      if (categoryDropdownRef.current && !categoryDropdownRef.current.contains(e.target as Node)) {
        setIsCategoryDropdownOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsCategoryDropdownOpen(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isCategoryDropdownOpen]);

  useEffect(() => {
    if (!isDocSourceDropdownOpen) return;
    const handlePointerDown = (e: MouseEvent) => {
      if (docSourceDropdownRef.current && !docSourceDropdownRef.current.contains(e.target as Node)) {
        setIsDocSourceDropdownOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsDocSourceDropdownOpen(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isDocSourceDropdownOpen]);

  // Chat input states
  const [inputVal, setInputVal] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const isGeneratingRef = useRef(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [reclassifyingDoc, setReclassifyingDoc] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [aiAlertOpen, setAiAlertOpen] = useState(false);
  const [aiAlertMsg, setAiAlertMsg] = useState('');
  const [targetDocuments, setTargetDocuments] = useState<TargetDocInfo[]>([]);
  const [isChatDragOver, setIsChatDragOver] = useState(false);

  const isAiConnected = aiConfig
    ? aiConfig.configured !== false && aiConfig.api_key_configured !== false
    : false;

  const isDocumentPinned = (filename: string) =>
    targetDocuments.some((doc) => doc.filename === filename);

  const pinTargetDocument = (doc: TargetDocInfo) => {
    setTargetDocuments((prev) => {
      if (prev.some((item) => item.filename === doc.filename)) return prev;
      if (prev.length >= MAX_PINNED_DOCUMENTS) {
        setAiAlertMsg(t('aiAssistant.inline.maxPinnedDocuments', { max: MAX_PINNED_DOCUMENTS }));
        setAiAlertOpen(true);
        return prev;
      }
      return [...prev, doc];
    });
  };

  const toggleTargetDocument = (doc: TargetDocInfo) => {
    setTargetDocuments((prev) => {
      if (prev.some((item) => item.filename === doc.filename)) {
        return prev.filter((item) => item.filename !== doc.filename);
      }
      if (prev.length >= MAX_PINNED_DOCUMENTS) {
        setAiAlertMsg(t('aiAssistant.inline.maxPinnedDocuments', { max: MAX_PINNED_DOCUMENTS }));
        setAiAlertOpen(true);
        return prev;
      }
      return [...prev, doc];
    });
  };

  const removeTargetDocument = (filename: string) => {
    setTargetDocuments((prev) => prev.filter((item) => item.filename !== filename));
  };

  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const restoreInputFocusRef = useRef(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  // Giải phóng pollTimerRef, recognitionRef và speechSynthesis khi unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current !== null) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
        recognitionRef.current = null;
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Tự động co giãn chiều cao textarea theo nội dung, loại bỏ thanh cuộn
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      if (scrollHeight > 0) {
        textareaRef.current.style.height = `${Math.min(scrollHeight, 120)}px`;
      }
    }
  }, [inputVal]);

  useEffect(() => {
    if (!isGenerating && restoreInputFocusRef.current) {
      restoreInputFocusRef.current = false;
      textareaRef.current?.focus();
    }
  }, [isGenerating]);

  // Load tài liệu & cấu hình ban đầu
  const loadDocuments = useCallback(async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Lỗi tải danh sách tài liệu:', err);
    }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const data = await getCategories();
      setCategories(data.categories || []);
    } catch (err) {
      console.error(err);
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    await loadDocuments();
    await loadCategories();
  }, [loadDocuments, loadCategories]);

  useEffect(() => {
    if (!canUseAI) return;
    let cancelled = false;
    getCategories()
      .then((data) => {
        if (!cancelled) setCategories(data.categories || []);
      })
      .catch(console.error);

    getAISettings()
      .then((data) => {
        if (!cancelled) setAiConfig(data);
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setAiConfig({ configured: false });
      });

    getDocuments()
      .then((data) => {
        if (!cancelled) setDocuments(data.documents || []);
      })
      .catch(console.error);

    return () => {
      cancelled = true;
    };
  }, [canUseAI]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  // Tạo phiên chat mới
  const handleNewChat = () => {
    if (!isChatHistoryReady) return;
    const newId = `session-${createMessageTimestamp()}`;
    const newSession = createDefaultSession(newId, currentLang);
    setChatHistoryState((current) => {
      if (current.storageKey !== storageKey) return current;
      return {
        ...current,
        sessions: [newSession, ...current.sessions],
        activeSessionId: newId,
      };
    });
    setSidebarTab('sessions');
    setInputVal('');
    setSelectedCategory('');
    setTargetDocuments([]);
    if (typeof window !== 'undefined' && window.innerWidth <= 860) {
      setIsSidebarOpen(false);
    }
  };

  const handleDeleteSession = (e: React.MouseEvent, id: string) => {
    if (!isChatHistoryReady) return;
    e.stopPropagation();
    if (confirm(t('aiAssistant.deleteSessionConfirm'))) {
      setChatHistoryState((current) => {
        if (current.storageKey !== storageKey) return current;
        const updated = current.sessions.filter((s) => s.id !== id);
        if (updated.length === 0) {
          const freshId = `session-${createMessageTimestamp()}`;
          const freshSession = createDefaultSession(freshId, currentLang);
          return {
            ...current,
            sessions: [freshSession],
            activeSessionId: freshId,
          };
        }
        let nextActiveId = current.activeSessionId;
        if (current.activeSessionId === id) {
          nextActiveId = updated[0].id;
        }
        return {
          ...current,
          sessions: updated,
          activeSessionId: nextActiveId,
        };
      });
    }
  };

  // Xuất file Markdown
  const handleFileUpload = async (file: File) => {
    if (!file) return;

    const existingDocument = documents.find((document) => document.filename === file.name);
    const replaceExisting = existingDocument
      ? window.confirm(t('aiAssistant.replaceExistingConfirm', { filename: file.name }))
      : false;
    if (existingDocument && !replaceExisting) return;

    // Hủy bỏ polling timer cũ nếu đang chạy
    if (pollTimerRef.current !== null) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    try {
      setUploadProgress({
        status: 'uploading',
        message: t('aiAssistant.inline.uploadingFileName', { name: file.name }),
      });
      const res = await uploadDocumentAsync(file, replaceExisting);

      if (res.job_id) {
        const jobId = res.job_id;
        pollTimerRef.current = setInterval(async () => {
          try {
            const prog = await getUploadProgress(jobId);
            const isSuccess = prog.status === 'done' || prog.status === 'completed';
            const isFailed = prog.status === 'error' || prog.status === 'failed';
            setUploadProgress(isFailed
              ? {
                  ...prog,
                  message: typeof prog.message === 'string' && prog.message.trim()
                    ? prog.message
                    : t('aiAssistant.inline.failedToUploadDocument'),
                }
              : prog);

            if (isSuccess || isFailed) {
              if (pollTimerRef.current !== null) {
                clearInterval(pollTimerRef.current);
                pollTimerRef.current = null;
              }

              if (isSuccess) {
                // Tự động tải lại danh sách tài liệu NGAY LẬP TỨC
                await refreshDocuments();
                // Giữ badge báo thành công trong 2.5s rồi tự đóng
                setTimeout(() => {
                  setUploadProgress(null);
                }, 2500);
              } else {
                // Báo lỗi và tự đóng sau 4s
                setTimeout(() => {
                  setUploadProgress(null);
                }, 4000);
              }
            }
          } catch {
            if (pollTimerRef.current !== null) {
              clearInterval(pollTimerRef.current);
              pollTimerRef.current = null;
            }
            setUploadProgress(null);
          }
        }, 1200);
      } else {
        await refreshDocuments();
        setUploadProgress({
          status: 'done',
          message: t('aiAssistant.inline.uploadAndIndexingSuccessful'),
        });
        setTimeout(() => {
          setUploadProgress(null);
        }, 2500);
      }
    } catch (err: unknown) {
      const error = typeof err === 'object' && err !== null ? (err as ApiError) : {};
      const isDuplicate = error.data?.code === 'duplicate_filename';
      setUploadProgress({
        status: 'error',
        message: isDuplicate
          ? t('aiAssistant.duplicateUploadError')
          : getSafeApiErrorDetail(err, t('aiAssistant.inline.failedToUploadDocument')),
      });
      window.setTimeout(() => setUploadProgress(null), 5000);
    }
  };

  const handleDropFiles = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (currentUser.isAdmin && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDeleteDoc = async (filename: string) => {
    if (confirm(t('aiAssistant.deleteDocConfirm', { filename }))) {
      try {
        await deleteDocument(filename);
        removeTargetDocument(filename);
        await refreshDocuments();
      } catch {
        alert(t('aiAssistant.inline.failedToDeleteDocument'));
      }
    }
  };

  const handleReclassifyDoc = async (filename: string) => {
    if (reclassifyingDoc) return;
    setReclassifyingDoc(filename);
    try {
      const res = await reclassifyDocument(filename);
      await refreshDocuments();
      setAiAlertMsg(
        t('aiAssistant.inline.reclassifySuccess', {
          filename,
          category: res?.category || t('aiAssistant.uncategorized'),
        })
      );
      setAiAlertOpen(true);
    } catch (err: unknown) {
      setAiAlertMsg(getSafeApiErrorDetail(err, t('aiAssistant.inline.reclassifyFailed')));
      setAiAlertOpen(true);
    } finally {
      setReclassifyingDoc(null);
    }
  };

  const handleClearAllDocs = async () => {
    if (confirm(t('aiAssistant.clearAllDocsConfirm')) &&
        prompt(t('aiAssistant.clearAllDocsTypeConfirm')) === 'DELETE') {
      try {
        await deleteDocuments('DELETE');
        setTargetDocuments([]);
        await refreshDocuments();
      } catch {
        alert(t('aiAssistant.inline.failedToClearDocuments'));
      }
    }
  };

  // Gửi câu hỏi đến AI
  const handleSend = async (overrideText?: string, removeErrorMsgId?: string) => {
    if (isGeneratingRef.current || !canUseAI || !isChatHistoryReady) return;
    const text = (overrideText ?? inputVal).trim();
    if (!text) return;
    if (text.length > MAX_QUESTION_LENGTH) {
      setAiAlertMsg(t('aiAssistant.msg.questionTooLong'));
      setAiAlertOpen(true);
      return;
    }

    restoreInputFocusRef.current = document.activeElement === textareaRef.current ||
      (document.activeElement instanceof HTMLElement && document.activeElement.closest('.input-box-container') !== null);
    isGeneratingRef.current = true;
    setIsGenerating(true);
    const sessionId = activeSessionId;
    const sessionAtSend = sessions.find((session) => session.id === sessionId);
    const baseMessages = (sessionAtSend?.messages || []).filter(
      (message) => !removeErrorMsgId || message.id !== removeErrorMsgId
    );
    const history = baseMessages
      .filter((message) => !message.id.startsWith('msg-welcome') && !message.isError)
      .slice(-8)
      .map((message) => ({ role: message.sender === 'user' ? 'user' : 'assistant', content: message.text }));

    const pinnedFilenames = targetDocuments.map((doc) => doc.filename);
    const singleFilename = pinnedFilenames.length === 1 ? pinnedFilenames[0] : null;
    const multipleFilenames = pinnedFilenames.length > 0 ? pinnedFilenames : null;

    const messageTimestamp = createMessageTimestamp();
    const shouldAppendUserMsg = !removeErrorMsgId;
    const userMsg: ChatMessage = {
      id: `user-${sessionId}-${messageTimestamp}`,
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString(currentLang === 'en' ? 'en-US' : 'vi-VN', { hour: '2-digit', minute: '2-digit' }),
      targetDocs: targetDocuments.length > 0 ? targetDocuments : undefined,
    };
    const newMessages = shouldAppendUserMsg ? [...baseMessages, userMsg] : baseMessages;
    const isFirstQuestion = !baseMessages.some((message) => message.sender === 'user');
    const title = isFirstQuestion
      ? (text.length > 60 ? `${text.slice(0, 60).trimEnd()}...` : text)
      : (sessionAtSend?.title || text);
    const initialSnippet = text.length > 55 ? `${text.slice(0, 55)}...` : text;

    updateChatHistory((prev) => prev.map((session) => session.id === sessionId
      ? { ...session, title, snippet: initialSnippet, messages: newMessages }
      : session));
    if (shouldAppendUserMsg) {
      setInputVal('');
    }

    try {
      const aiMsgId = `ai-${sessionId}-${messageTimestamp}`;
      let accumulatedText = '';
      let streamedSources: CitationSource[] = [];
      let messageStreamed = false;

      const updateOrAddAiMessage = (answerText: string, sources: CitationSource[]) => {
        const aiMsg: ChatMessage = {
          id: aiMsgId,
          sender: 'ai',
          text: answerText,
          time: new Date().toLocaleTimeString(currentLang === 'en' ? 'en-US' : 'vi-VN', { hour: '2-digit', minute: '2-digit' }),
          citations: sources,
          quickPrompts: [
            t('aiAssistant.msg.followUpSummary'),
            t('aiAssistant.msg.followUpFigures'),
            t('aiAssistant.msg.followUpBasis'),
          ],
        };
        const cleanAiText = answerText.replace(/[*#`_\n]/g, ' ').replace(/\s+/g, ' ').trim();
        const updatedSnippet = cleanAiText.length > 65 ? `${cleanAiText.slice(0, 65)}...` : cleanAiText;

        updateChatHistory((prev) => prev.map((session) => {
          if (session.id !== sessionId) return session;
          const exists = session.messages.some((m) => m.id === aiMsgId);
          const messages = exists
            ? session.messages.map((m) => (m.id === aiMsgId ? aiMsg : m))
            : [...session.messages, aiMsg];
          return {
            ...session,
            snippet: updatedSnippet || initialSnippet,
            messages,
          };
        }));
      };

      try {
        await askQuestionStream(text, {
          history,
          category: selectedCategory || null,
          filename: singleFilename,
          filenames: multipleFilenames,
          language: currentLang,
          onSources: (sources) => {
            streamedSources = (sources || []) as CitationSource[];
            if (messageStreamed) {
              updateOrAddAiMessage(accumulatedText, streamedSources);
            }
          },
          onDelta: (_delta, full) => {
            accumulatedText = full;
            if (!messageStreamed) {
              messageStreamed = true;
              setIsGenerating(false);
            }
            updateOrAddAiMessage(accumulatedText, streamedSources);
          },
          onDone: (data) => {
            if (data?.answer) accumulatedText = data.answer;
            if (Array.isArray(data?.sources)) streamedSources = data.sources as CitationSource[];
            updateOrAddAiMessage(accumulatedText, streamedSources);
          },
        });
      } catch (streamError: unknown) {
        if (!messageStreamed) {
          console.warn('Stream failed, falling back to askQuestion:', streamError);
          const response = await askQuestion(text, history, selectedCategory || null, singleFilename, currentLang, multipleFilenames);
          const aiText = response.answer || response.text;
          if (typeof aiText !== 'string' || !aiText.trim()) throw new Error('Empty AI response', { cause: streamError });
          updateOrAddAiMessage(aiText, response.sources || response.citations || []);
        } else {
          throw streamError;
        }
      }
    } catch (error: unknown) {
      console.warn('AI chat request failed:', error);
      const errDetail = getSafeApiErrorDetail(error, t('aiAssistant.msg.aiUnavailable'));
      const errMsg: ChatMessage = {
        id: `ai-err-${sessionId}-${messageTimestamp}`,
        sender: 'ai',
        text: errDetail,
        time: new Date().toLocaleTimeString(currentLang === 'en' ? 'en-US' : 'vi-VN', { hour: '2-digit', minute: '2-digit' }),
        isError: true,
        retryText: text,
      };
      updateChatHistory((prev) => prev.map((session) => session.id === sessionId
        ? { ...session, messages: [...newMessages, errMsg] }
        : session));
    } finally {
      isGeneratingRef.current = false;
      setIsGenerating(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Đọc to / Dừng đọc câu trả lời
  const handleSpeakText = (msgId: string, text: string) => {
    if ('speechSynthesis' in window) {
      if (speakingId === msgId) {
        window.speechSynthesis.cancel();
        setSpeakingId(null);
        return;
      }
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*#`_]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = currentLang === 'en' ? 'en-US' : 'vi-VN';
      utterance.rate = 1.0;
      utterance.onend = () => setSpeakingId(null);
      utterance.onerror = () => setSpeakingId(null);
      setSpeakingId(msgId);
      window.speechSynthesis.speak(utterance);
    } else {
      alert(t('aiAssistant.msg.ttsUnsupported'));
    }
  };

  // Nhận diện giọng nói tiếng Việt (Web Speech API)
  const handleToggleVoice = () => {
    const speechWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
    const SpeechRecognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert(t('aiAssistant.msg.speechUnsupported'));
      return;
    }

    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore if already stopped
        }
        recognitionRef.current = null;
      }
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = currentLang === 'en' ? 'en-US' : 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };
    recognition.onerror = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognition.onresult = (event: SpeechRecognitionResultEvent) => {
      const transcript = event.results[0][0].transcript;
      setInputVal((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };

    recognition.start();
  };

  // Formatter Markdown Inline
  const handleExportChat = () => {
    if (!isChatHistoryReady) return;
    const transcript = sessions.map((session) => {
      const sessionTranscript = session.messages.map((message) => {
        const messageText = message.id.startsWith('msg-welcome-')
          ? t('aiAssistant.defaultSession.welcome')
          : message.text;
        const sender = message.sender === 'user'
          ? t('aiAssistant.exportUser')
          : t('aiAssistant.exportAssistant');
        const citationLines = (message.citations || []).map((source, index) => {
          const label = source.file_name || source.label || t('aiAssistant.inline.documentValue', { value: index + 1 });
          const location = source.code || [
            source.page ? `${t('aiAssistant.inline.page')}${source.page}` : '',
            source.section ? `${t('aiAssistant.inline.section')}${source.section}` : '',
          ].filter(Boolean).join(', ');
          return `- ${label}${location ? ` (${location})` : ''}`;
        });
        const citations = citationLines.length
          ? `\n\n${t('aiAssistant.exportSources')}:\n${citationLines.join('\n')}`
          : '';
        return `**${sender} - ${message.time}**\n\n${messageText}${citations}`;
      }).join('\n\n');
      const sessionTitle = isDefaultSessionTitle(session.title)
        ? t('aiAssistant.defaultSession.title')
        : session.title;
      return `# ${sessionTitle}\n\n${sessionTranscript}`;
    }).join('\n\n---\n\n');
    const blob = new Blob([transcript], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const titleForFilename = activeSession
      ? isDefaultSessionTitle(activeSession.title)
        ? t('aiAssistant.defaultSession.title')
        : activeSession.title
      : t('aiAssistant.exportChat');
    // eslint-disable-next-line no-control-regex -- remove control characters from a downloaded filename
    const safeTitle = titleForFilename.replace(/[<>:"/\\|?*\u0000-\u001F]/g, '_').slice(0, 80);
    a.download = `TLBM_AI_Chat_${safeTitle}_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Lọc danh sách phiên hội thoại theo từ khóa (Tiêu đề, Câu hỏi user, Nội dung tin nhắn)
  const filteredSessions = (isChatHistoryReady ? sessions : []).filter((s) => {
    if (!sessionSearch.trim()) return true;
    const query = sessionSearch.trim().toLowerCase();

    // 1. Tìm theo tiêu đề cuộc trò chuyện
    if (s.title && s.title.toLowerCase().includes(query)) return true;

    // 2. Tìm theo đoạn trích xem trước (snippet)
    if (s.snippet && s.snippet.toLowerCase().includes(query)) return true;

    // 3. Tìm theo nội dung các tin nhắn (câu hỏi và câu trả lời) trong phiên
    if (s.messages && Array.isArray(s.messages)) {
      return s.messages.some((m) => m.text && m.text.toLowerCase().includes(query));
    }

    return false;
  });

  // Lọc và gom nhóm tài liệu theo thư mục
  const filteredDocs = documents.filter((d) => {
    if (!docSearch.trim()) return true;
    const q = docSearch.toLowerCase();
    return (
      (d.filename && d.filename.toLowerCase().includes(q)) ||
      (d.category && d.category.toLowerCase().includes(q))
    );
  });

  const buildHierarchicalDocs = (
    docsList: DocItem[],
    uncategorizedLabel: string
  ): Record<string, RootFolderGroup> => {
    const groups: Record<string, RootFolderGroup> = {};

    for (const doc of docsList) {
      const rawCategory = doc.category?.trim();
      const normalizedCategory = rawCategory
        ?.normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd')
        .toLowerCase();
      const effectiveCategory = rawCategory && normalizedCategory !== 'chua phan loai'
        ? rawCategory
        : uncategorizedLabel;

      const slashIdx = effectiveCategory.indexOf(' / ');
      const rootName = slashIdx > 0 ? effectiveCategory.slice(0, slashIdx).trim() : effectiveCategory;
      const subName = slashIdx > 0 ? effectiveCategory.slice(slashIdx + 3).trim() : '';

      if (!groups[rootName]) {
        groups[rootName] = {
          name: rootName,
          subFolders: {},
          directDocs: [],
          totalCount: 0,
        };
      }

      groups[rootName].totalCount += 1;
      if (subName) {
        if (!groups[rootName].subFolders[subName]) {
          groups[rootName].subFolders[subName] = { name: subName, docs: [] };
        }
        groups[rootName].subFolders[subName].docs.push(doc);
      } else {
        groups[rootName].directDocs.push(doc);
      }
    }

    return groups;
  };

  const uploadedDocs = useMemo(
    () => filteredDocs.filter((d) => !d.is_managed),
    [filteredDocs]
  );

  const managedDocs = useMemo(
    () => filteredDocs.filter((d) => Boolean(d.is_managed)),
    [filteredDocs]
  );

  const uploadedTree: Record<string, RootFolderGroup> = useMemo(
    () => buildHierarchicalDocs(uploadedDocs, t('aiAssistant.uncategorized')),
    [uploadedDocs, t]
  );

  const managedTree: Record<string, RootFolderGroup> = useMemo(
    () => buildHierarchicalDocs(managedDocs, t('aiAssistant.uncategorized')),
    [managedDocs, t]
  );

  const renderFolderTree = (tree: Record<string, RootFolderGroup>, sectionPrefix: string) =>
    Object.values(tree).map((root: RootFolderGroup) => {
      const rootKey = `${sectionPrefix}:${root.name}`;
      const isRootCollapsed = !!collapsedRoots[rootKey];
      return (
        <div key={rootKey} className={`sidebar-doc-category ${isRootCollapsed ? 'is-collapsed' : ''}`}>
          {/* Thư mục gốc duy nhất (Level 1) */}
          <button
            type="button"
            className="sidebar-category-header"
            onClick={() => toggleRoot(rootKey)}
            aria-expanded={!isRootCollapsed}
            title={
              isRootCollapsed
                ? t('aiAssistant.inline.expandFolderName', { name: root.name })
                : t('aiAssistant.inline.collapseFolderName', { name: root.name })
            }
          >
            <span className="sidebar-category-title">
              <i
                className={`sidebar-chevron-icon fa-solid ${
                  isRootCollapsed ? 'fa-chevron-right' : 'fa-chevron-down'
                }`}
              />
              <i className="fa-solid fa-folder text-warning" />
              <span className="sidebar-category-name" title={root.name}>
                {root.name}
              </span>
            </span>
            <span className="sidebar-category-count font-bold">
              {root.totalCount}
            </span>
          </button>

          {/* Danh sách Item bên trong Folder nhỏ */}
          {!isRootCollapsed && (
            <div className="sidebar-root-content">
              {Object.values(root.subFolders).map((sub: SubFolderGroup) => {
                const subKey = `${rootKey}_${sub.name}`;
                const isSubCollapsed = !!collapsedSubs[subKey];
                return (
                  <div
                    key={sub.name}
                    className={`sidebar-subfolder-card ${isSubCollapsed ? 'is-collapsed' : ''}`}
                  >
                    {/* Top Header */}
                    <button
                      type="button"
                      className="sidebar-subfolder-header"
                      onClick={() => toggleSub(subKey)}
                      aria-expanded={!isSubCollapsed}
                      title={
                        isSubCollapsed
                          ? t('aiAssistant.inline.expandName', { name: sub.name })
                          : t('aiAssistant.inline.collapseName', { name: sub.name })
                      }
                    >
                      <span className="sidebar-subfolder-title">
                        <i
                          className={`text-[10px] text-muted transition-transform fa-solid ${
                            isSubCollapsed ? 'fa-chevron-right' : 'fa-chevron-down'
                          }`}
                        />
                        <i
                          className={`fa-solid ${
                            isSubCollapsed ? 'fa-folder text-warning' : 'fa-folder-open text-warning'
                          } text-xs`}
                        />
                        <span className="sidebar-subfolder-name" title={sub.name}>
                          {sub.name}
                        </span>
                      </span>
                      <span className="sidebar-subfolder-count">
                        {sub.docs.length}
                      </span>
                    </button>

                    {/* Danh sách Item bên trong Folder nhỏ */}
                    {!isSubCollapsed && (
                      <div className="sidebar-doc-list">
                        {sub.docs.map((d) => {
                          const itemLabel = d.filename;
                          const isPinned = isDocumentPinned(d.filename);

                          return (
                            <div
                              key={d.filename}
                              className={`sidebar-doc-row ${isPinned ? 'is-targeted' : ''}`}
                              draggable={true}
                              onDragStart={(e) => {
                                e.dataTransfer.setData(
                                  'application/x-tlbm-doc',
                                  JSON.stringify({ filename: d.filename, label: itemLabel, category: d.category })
                                );
                                e.dataTransfer.effectAllowed = 'copy';
                              }}
                              title={
                                t('aiAssistant.inline.dragItemlabelToChatOr', { itemLabel })
                              }
                            >
                              <div className="sidebar-doc-info" title={d.filename}>
                                <i
                                  className={`sidebar-doc-icon fa-solid ${
                                    d.filename.toLowerCase().endsWith('.pdf')
                                      ? 'fa-file-pdf text-danger'
                                      : 'fa-file-lines text-primary'
                                  }`}
                                />
                                <span className="sidebar-doc-name">
                                  {itemLabel}
                                </span>
                              </div>
                              <div className="sidebar-doc-actions">
                                {/* Nút chỉ định nhanh */}
                                <button
                                  type="button"
                                  className={`sidebar-doc-btn pin-btn ${isPinned ? 'is-active text-primary' : ''}`}
                                  onClick={() => toggleTargetDocument({ filename: d.filename, label: itemLabel, category: d.category })}
                                  title={
                                    isPinned
                                      ? (t('aiAssistant.inline.unpinTargetDocument'))
                                      : (t('aiAssistant.inline.targetThisDocumentForQ'))
                                  }
                                >
                                  <i className="fa-solid fa-crosshairs" />
                                </button>
                                {!d.is_managed && (
                                  <>
                                    <button
                                      type="button"
                                      className="sidebar-doc-btn"
                                      onClick={() => setPreviewFilename(d.filename)}
                                      title={t('aiAssistant.preview')}
                                    >
                                      <i className="fa-solid fa-eye" />
                                    </button>
                                    {currentUser.isAdmin && (
                                      <>
                                        <button
                                          type="button"
                                          className="sidebar-doc-btn"
                                          onClick={() => handleReclassifyDoc(d.filename)}
                                          disabled={reclassifyingDoc === d.filename}
                                          title={reclassifyingDoc === d.filename ? t('aiAssistant.inline.reclassifying') : t('aiAssistant.inline.reclassifyDoc')}
                                          aria-label={`${t('aiAssistant.inline.reclassifyDoc')}: ${d.filename}`}
                                        >
                                          <i className={`fa-solid ${reclassifyingDoc === d.filename ? 'fa-spinner fa-spin' : 'fa-tags'}`} />
                                        </button>
                                        <button
                                          type="button"
                                          className="sidebar-doc-btn delete-btn"
                                          onClick={() => handleDeleteDoc(d.filename)}
                                          title={t('aiAssistant.deleteDoc')}
                                          aria-label={`${t('aiAssistant.deleteDoc')}: ${d.filename}`}
                                        >
                                          <i className="fa-solid fa-trash" />
                                        </button>
                                      </>
                                    )}
                                  </>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Tài liệu cấp trực tiếp (nếu có) */}
              {root.directDocs.length > 0 && (
                <div className="sidebar-doc-list">
                  {root.directDocs.map((d) => {
                    const isPinned = isDocumentPinned(d.filename);
                    return (
                    <div
                      key={d.filename}
                      className={`sidebar-doc-row ${isPinned ? 'is-targeted' : ''}`}
                      draggable={true}
                      onDragStart={(e) => {
                        e.dataTransfer.setData(
                          'application/x-tlbm-doc',
                          JSON.stringify({ filename: d.filename, label: d.filename, category: d.category })
                        );
                        e.dataTransfer.effectAllowed = 'copy';
                      }}
                      title={
                        t('aiAssistant.inline.dragFilenameToChatOr', { filename: d.filename })
                      }
                    >
                      <div className="sidebar-doc-info" title={d.filename}>
                        <i
                          className={`sidebar-doc-icon fa-solid ${
                            d.filename.toLowerCase().endsWith('.pdf')
                              ? 'fa-file-pdf text-danger'
                              : 'fa-file-lines text-primary'
                          }`}
                        />
                        <span className="sidebar-doc-name">{d.filename}</span>
                      </div>
                      <div className="sidebar-doc-actions">
                        <button
                          type="button"
                          className={`sidebar-doc-btn pin-btn ${isPinned ? 'is-active text-primary' : ''}`}
                          onClick={() => toggleTargetDocument({ filename: d.filename, label: d.filename, category: d.category })}
                          title={
                            isPinned
                              ? (t('aiAssistant.inline.unpinTargetDocument'))
                              : (t('aiAssistant.inline.targetThisDocumentForQ'))
                          }
                        >
                          <i className="fa-solid fa-crosshairs" />
                        </button>
                        {!d.is_managed && (
                          <>
                            <button
                              type="button"
                              className="sidebar-doc-btn"
                              onClick={() => setPreviewFilename(d.filename)}
                              title={t('aiAssistant.preview')}
                            >
                              <i className="fa-solid fa-eye" />
                            </button>
                            {currentUser.isAdmin && (
                              <>
                                <button
                                  type="button"
                                  className="sidebar-doc-btn"
                                  onClick={() => handleReclassifyDoc(d.filename)}
                                  disabled={reclassifyingDoc === d.filename}
                                  title={reclassifyingDoc === d.filename ? t('aiAssistant.inline.reclassifying') : t('aiAssistant.inline.reclassifyDoc')}
                                  aria-label={`${t('aiAssistant.inline.reclassifyDoc')}: ${d.filename}`}
                                >
                                  <i className={`fa-solid ${reclassifyingDoc === d.filename ? 'fa-spinner fa-spin' : 'fa-tags'}`} />
                                </button>
                                <button
                                  type="button"
                                  className="sidebar-doc-btn delete-btn"
                                  onClick={() => handleDeleteDoc(d.filename)}
                                  title={t('aiAssistant.deleteDoc')}
                                  aria-label={`${t('aiAssistant.deleteDoc')}: ${d.filename}`}
                                >
                                  <i className="fa-solid fa-trash" />
                                </button>
                              </>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      );
    });

  if (!aiPermissionLoaded) {
    return <div className="flex h-full items-center justify-center text-text-secondary">{t('aiAssistant.accessChecking')}</div>;
  }
  if (!canUseAI) {
    return <div className="flex h-full items-center justify-center p-6 text-center text-text-secondary">{t('aiAssistant.accessDenied')}</div>;
  }

  return (
    <div className="ai-chat-page-root">
      {/* Sidebar Footer */}
      {isSidebarOpen && (
        <button
          className="ai-sidebar-mobile-backdrop"
          onClick={() => setIsSidebarOpen(false)}
          aria-label={t('aiAssistant.msg.closeSidebar')}
          type="button"
        />
      )}

      {/* ====================================================================
         1. SIDEBAR (LỊCH SỬ CHAT & KHO TÀI LIỆU)
         ==================================================================== */}
      <aside
        ref={sidebarRef}
        className={`ai-chat-sidebar ${isSidebarOpen ? 'is-open' : 'is-collapsed'}`}
        role={isMobile && isSidebarOpen ? 'dialog' : undefined}
        aria-modal={isMobile && isSidebarOpen ? true : undefined}
        aria-label={t('aiAssistant.inline.chatHistory')}
      >
        {/* Nút Tạo Đoạn chat mới & Thu gọn */}
        <div className="ai-sidebar-top">
          <button type="button" className="new-chat-btn" onClick={handleNewChat}>
            <i className="fa-solid fa-plus" />
            <span>{t('aiAssistant.newChat')}</span>
          </button>

          <button
            type="button"
            className="sidebar-toggle-btn"
            aria-label={isSidebarOpen ? t('aiAssistant.collapseSidebar') : t('aiAssistant.expandSidebar')}
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            title={isSidebarOpen ? t('aiAssistant.collapseSidebar') : t('aiAssistant.expandSidebar')}
          >
            <i className={`fa-solid ${isSidebarOpen ? 'fa-angles-left' : 'fa-angles-right'}`} />
          </button>
        </div>

        {/* Tab Switcher: Hội thoại vs Kho tài liệu (tích hợp dropdown phân loại kho) */}
        {isSidebarOpen && (
          <div className="sidebar-tab-switcher-wrap" ref={docSourceDropdownRef}>
            <div className="sidebar-tab-switcher">
              <button
                type="button"
                className={`sidebar-tab-pill ${sidebarTab === 'sessions' ? 'active' : ''}`}
                onClick={() => {
                  setSidebarTab('sessions');
                  setIsDocSourceDropdownOpen(false);
                }}
              >
                <i className="fa-regular fa-message" />
                <span>{t('aiAssistant.tabSessions')}</span>
              </button>
              <button
                type="button"
                className={`sidebar-tab-pill ${sidebarTab === 'docs' ? 'active' : ''}`}
                onClick={() => {
                  if (sidebarTab !== 'docs') {
                    setSidebarTab('docs');
                  } else {
                    setIsDocSourceDropdownOpen((prev) => !prev);
                  }
                }}
                aria-haspopup="listbox"
                aria-expanded={sidebarTab === 'docs' && isDocSourceDropdownOpen}
                title={t('aiAssistant.inline.filterDocSource')}
              >
                <i className="fa-solid fa-folder-open" />
                <span>{t('aiAssistant.tabDocs')}</span>
                {documents.length > 0 && (
                  <span className="sidebar-tab-badge">
                    {docSourceFilter === 'managed'
                      ? managedDocs.length
                      : docSourceFilter === 'uploaded'
                      ? uploadedDocs.length
                      : documents.length}
                  </span>
                )}
                {sidebarTab === 'docs' && (
                  <i className={`fa-solid fa-chevron-down sidebar-tab-chevron ${isDocSourceDropdownOpen ? 'is-open' : ''}`} />
                )}
              </button>
            </div>

            {sidebarTab === 'docs' && isDocSourceDropdownOpen && (
              <div className="sidebar-tab-dropdown-menu" role="listbox" aria-label={t('aiAssistant.inline.filterDocSource')}>
                <button
                  type="button"
                  role="option"
                  aria-selected={docSourceFilter === 'all'}
                  className={`category-dropdown-option ${docSourceFilter === 'all' ? 'is-selected' : ''}`}
                  onClick={() => {
                    setDocSourceFilter('all');
                    setIsDocSourceDropdownOpen(false);
                  }}
                >
                  <span className="category-dropdown-option-text">{t('aiAssistant.inline.allDocSources')}</span>
                  <span className="category-dropdown-option-count">{uploadedDocs.length + managedDocs.length}</span>
                </button>
                <button
                  type="button"
                  role="option"
                  aria-selected={docSourceFilter === 'managed'}
                  className={`category-dropdown-option ${docSourceFilter === 'managed' ? 'is-selected' : ''}`}
                  onClick={() => {
                    setDocSourceFilter('managed');
                    setIsDocSourceDropdownOpen(false);
                  }}
                >
                  <span className="category-dropdown-option-text">{t('aiAssistant.inline.serverDocSource')}</span>
                  <span className="category-dropdown-option-count">{managedDocs.length}</span>
                </button>
                <button
                  type="button"
                  role="option"
                  aria-selected={docSourceFilter === 'uploaded'}
                  className={`category-dropdown-option ${docSourceFilter === 'uploaded' ? 'is-selected' : ''}`}
                  onClick={() => {
                    setDocSourceFilter('uploaded');
                    setIsDocSourceDropdownOpen(false);
                  }}
                >
                  <span className="category-dropdown-option-text">{t('aiAssistant.inline.aiUploadedDocSource')}</span>
                  <span className="category-dropdown-option-count">{uploadedDocs.length}</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 1: Danh sách các phiên trò chuyện */}
        {isSidebarOpen && sidebarTab === 'sessions' && (
          <>
            <div className="ai-sidebar-search">
              <i className="fa-solid fa-magnifying-glass" />
              <input
                type="text"
                placeholder={t('aiAssistant.searchSessionsPlaceholder')}
                aria-label={t('aiAssistant.searchSessionsPlaceholder')}
                value={sessionSearch}
                onChange={(e) => setSessionSearch(e.target.value)}
              />
              {sessionSearch && (
                <button
                  type="button"
                  className="sidebar-search-clear-btn"
                  onClick={() => setSessionSearch('')}
                  title={t('aiAssistant.clearSearch')}
                >
                  <i className="fa-solid fa-xmark" />
                </button>
              )}
            </div>

            <div className="ai-sidebar-sessions-list">
              <div className="session-group">
                <div className="session-group-title">
                  <span>{t('aiAssistant.inline.chatHistory')}</span>
                  {sessions.length > 0 && (
                    <span className="session-count-badge">{sessions.length}</span>
                  )}
                </div>

                {filteredSessions.length === 0 ? (
                  <div className="sidebar-search-empty">
                    <i className="fa-regular fa-comments sidebar-search-empty-icon" />
                    <p className="sidebar-search-empty-text">
                      {sessionSearch.trim()
                        ? t('aiAssistant.emptySessionsSearch')
                        : t('aiAssistant.emptySessions')}
                    </p>
                  </div>
                ) : (
                  <div className="session-items">
                    {filteredSessions.map((s) => {
                      const sessionTitle = isDefaultSessionTitle(s.title)
                        ? t('aiAssistant.defaultSession.title')
                        : s.title;
                      const sessionSnippet = isDefaultSessionSnippet(s.snippet)
                        ? t('aiAssistant.defaultSession.snippet')
                        : s.snippet;
                      return (
                      <div key={s.id} className="session-item-row">
                        <button
                          type="button"
                          className={`session-item-btn ${s.id === activeSessionId ? 'active' : ''}`}
                          onClick={() => {
                            setActiveSessionId(s.id);
                            if (typeof window !== 'undefined' && window.innerWidth <= 860) {
                              setIsSidebarOpen(false);
                            }
                          }}
                          title={sessionTitle}
                          aria-pressed={s.id === activeSessionId}
                        >
                          <i className="fa-regular fa-message session-item-icon" />
                          <span className="session-item-text">
                            <span className="session-item-title" title={sessionTitle}>{sessionTitle}</span>
                            <span className="session-item-snippet" title={sessionSnippet}>{sessionSnippet}</span>
                          </span>
                        </button>
                        <button
                          type="button"
                          className="session-item-delete"
                          onClick={(event) => handleDeleteSession(event, s.id)}
                          title={t('aiAssistant.deleteSession')}
                          aria-label={`${t('aiAssistant.deleteSession')}: ${sessionTitle}`}
                        >
                          <i className="fa-solid fa-trash-can" />
                        </button>
                      </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Tab 2: Quản lý kho tài liệu */}
        {isSidebarOpen && sidebarTab === 'docs' && (
          <>
            <div className="ai-sidebar-search">
              <i className="fa-solid fa-magnifying-glass" />
                <input
                type="text"
                placeholder={t('aiAssistant.searchDocsPlaceholder')}
                  aria-label={t('aiAssistant.searchDocsPlaceholder')}
                value={docSearch}
                onChange={(e) => setDocSearch(e.target.value)}
              />
              {docSearch && (
                <button
                  type="button"
                  className="sidebar-search-clear-btn"
                  onClick={() => setDocSearch('')}
                  title={t('aiAssistant.clearSearch')}
                >
                  <i className="fa-solid fa-xmark" />
                </button>
              )}
            </div>

            <div className="ai-sidebar-docs-list">
              {/* Drag & Drop Upload Zone - Chỉ hiển thị cho Quản trị viên khi xem Tất cả hoặc Kho tải lên từ AI */}
              {currentUser.isAdmin && docSourceFilter !== 'managed' && (
                <button
                  ref={dropZoneRef}
                  type="button"
                  className={`sidebar-dropzone ${isDragging ? 'is-dragging' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDropFiles}
                  onClick={() => fileInputRef.current?.click()}
                  aria-label={`${t('aiAssistant.dropzoneText')}. ${t('aiAssistant.dropzoneSub')}`}
                >
                  <span className="sidebar-dropzone-icon" aria-hidden="true">
                    <i className="fa-solid fa-plus" />
                  </span>
                  <span className="sidebar-dropzone-content">
                    <span className="sidebar-dropzone-text">{t('aiAssistant.dropzoneText')}</span>
                    <span className="sidebar-dropzone-subtext">{t('aiAssistant.dropzoneSub')}</span>
                  </span>
                </button>
              )}

              {/* Progress indicator */}
              {uploadProgress && (
                <div
                  className={`sidebar-upload-progress ${
                    uploadProgress.status === 'done' || uploadProgress.status === 'completed'
                      ? 'is-success'
                      : uploadProgress.status === 'error' || uploadProgress.status === 'failed'
                      ? 'is-error'
                      : ''
                  }`}
                  role={uploadProgress.status === 'error' || uploadProgress.status === 'failed' ? 'alert' : 'status'}
                  aria-live={uploadProgress.status === 'error' || uploadProgress.status === 'failed' ? 'assertive' : 'polite'}
                >
                  {uploadProgress.status === 'done' || uploadProgress.status === 'completed' ? (
                    <i className="fa-solid fa-circle-check text-success" />
                  ) : uploadProgress.status === 'error' || uploadProgress.status === 'failed' ? (
                    <i className="fa-solid fa-circle-exclamation text-danger" />
                  ) : (
                    <i className="fa-solid fa-circle-notch fa-spin text-primary" />
                  )}
                  <span>{uploadProgress.message}</span>
                </div>
              )}

              {/* Danh mục tài liệu chia 2 nhóm: Kho tài liệu tải lên từ AI & Kho tài liệu máy chủ */}
              {(docSourceFilter === 'all' && uploadedDocs.length === 0 && managedDocs.length === 0) ||
              (docSourceFilter === 'managed' && managedDocs.length === 0) ||
              (docSourceFilter === 'uploaded' && uploadedDocs.length === 0) ? (
                <div className="sidebar-empty-state">
                  <i className="fa-regular fa-folder-open sidebar-empty-icon" />
                  <div>{documents.length === 0 ? t('aiAssistant.emptyDocs') : t('aiAssistant.emptyDocsSearch')}</div>
                </div>
              ) : (
                <>
                  {docSourceFilter !== 'managed' && uploadedDocs.length > 0 && (
                    <div className="sidebar-doc-section">
                      {docSourceFilter === 'all' && (
                        <div className="sidebar-doc-section-header">
                          <span className="sidebar-doc-section-title">
                            <i className="fa-solid fa-cloud-arrow-up text-primary" />
                            <span>{t('aiAssistant.inline.uploadedDocsSection')}</span>
                          </span>
                          <span className="sidebar-doc-section-count">{uploadedDocs.length}</span>
                        </div>
                      )}
                      {renderFolderTree(uploadedTree, 'uploaded')}
                    </div>
                  )}

                  {docSourceFilter !== 'uploaded' && managedDocs.length > 0 && (
                    <div className="sidebar-doc-section">
                      {docSourceFilter === 'all' && (
                        <div className="sidebar-doc-section-header">
                          <span className="sidebar-doc-section-title">
                            <i className="fa-solid fa-database text-primary" />
                            <span>{t('aiAssistant.inline.systemDocsSection')}</span>
                          </span>
                          <span className="sidebar-doc-section-count">{managedDocs.length}</span>
                        </div>
                      )}
                      {renderFolderTree(managedTree, 'managed')}
                    </div>
                  )}
                </>
              )}

              {currentUser.isAdmin && docSourceFilter !== 'managed' && documents.some((d) => !d.is_managed) && (
                <button
                  type="button"
                  className="sidebar-clear-all-btn"
                  disabled={!isChatHistoryReady || isGenerating}
                  onClick={handleClearAllDocs}
                >
                  <i className="fa-solid fa-trash-can" />
                  <span>{t('aiAssistant.clearAllDocs')}</span>
                </button>
              )}
            </div>
          </>
        )}

        {/* Sidebar Footer */}
        {isSidebarOpen && (
          <div className="ai-sidebar-footer">
            <div className="ai-stats-badge">
              <span className="live-pulse-dot" />
              <span>{t('aiAssistant.syncedDocs', { count: documents.length })}</span>
            </div>
            <div className="ai-partner-tag">{t('aiAssistant.smartDocSub')}</div>
          </div>
        )}
      </aside>

      {/* ====================================================================
         2. MAIN CHAT STAGE (KHUNG TRÒ CHUYỆN CHÍNH)
         ==================================================================== */}
      <main className="ai-chat-main-stage">
        {/* Top Header */}
        <header className="ai-chat-top-header">
          <div className="top-header-left">
            <div className="ai-brand-badge">
              <div className="ai-brand-icon">
                <i className="fa-solid fa-robot" />
              </div>
              <div>
                <div className="ai-brand-title">
                  <span>{t('aiAssistant.pageTitle')}</span>
                </div>
                <div className="ai-brand-sub">
                  {t('aiAssistant.pageSubtitle')}
                </div>
              </div>
            </div>
          </div>

          <div className="top-header-actions">
            {/* Bộ lọc chủ đề */}
            {categories.length > 0 && (
              <div className="category-filter-dropdown" ref={categoryDropdownRef}>
                <button
                  type="button"
                  className={`model-selector-wrapper category-filter-wrapper category-dropdown-trigger ${isCategoryDropdownOpen ? 'is-open' : ''}`}
                  onClick={() => setIsCategoryDropdownOpen((prev) => !prev)}
                  aria-haspopup="listbox"
                  aria-expanded={isCategoryDropdownOpen}
                  aria-label={t('aiAssistant.allCategories')}
                >
                  <i className="fa-solid fa-filter text-primary" />
                  <span className="category-dropdown-label">
                    {selectedCategory
                      ? `${selectedCategory} (${categories.find((c) => c.name === selectedCategory)?.count ?? 0})`
                      : `${t('aiAssistant.allCategories')} (${documents.length})`}
                  </span>
                  <i className={`fa-solid fa-chevron-down category-dropdown-chevron ${isCategoryDropdownOpen ? 'is-open' : ''}`} />
                </button>

                {isCategoryDropdownOpen && (
                  <div className="category-dropdown-menu" role="listbox" aria-label={t('aiAssistant.allCategories')}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selectedCategory === ''}
                      className={`category-dropdown-option ${selectedCategory === '' ? 'is-selected' : ''}`}
                      onClick={() => {
                        setSelectedCategory('');
                        setIsCategoryDropdownOpen(false);
                      }}
                    >
                      <span className="category-dropdown-option-text">{t('aiAssistant.allCategories')}</span>
                      <span className="category-dropdown-option-count">{documents.length}</span>
                    </button>
                    {categories.map((c) => (
                      <button
                        key={c.name}
                        type="button"
                        role="option"
                        aria-selected={selectedCategory === c.name}
                        className={`category-dropdown-option ${selectedCategory === c.name ? 'is-selected' : ''}`}
                        onClick={() => {
                          setSelectedCategory(c.name);
                          setIsCategoryDropdownOpen(false);
                        }}
                      >
                        <span className="category-dropdown-option-text">{c.name}</span>
                        <span className="category-dropdown-option-count">{c.count}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* AI Connection Status Badge */}
            {aiConfig && (
              <div
                className="model-selector-wrapper ai-model-badge"
                style={{ display: 'flex' }}
                aria-live="polite"
                aria-label={isAiConnected ? t('aiAssistant.statusActive') : t('aiAssistant.statusDisconnected')}
                title={isAiConnected ? t('aiAssistant.statusActive') : t('aiAssistant.statusDisconnected')}
              >
                <span className={`live-pulse-dot ${isAiConnected ? '' : 'is-disconnected'}`} />
                <span className="ai-status-badge-text">
                  {isAiConnected ? t('aiAssistant.statusActive') : t('aiAssistant.statusDisconnected')}
                </span>
              </div>
            )}

            {/* Nút Xuất file */}
            <button
              type="button"
              className="chat-action-btn"
              disabled={!isChatHistoryReady}
              onClick={handleExportChat}
              title={t('aiAssistant.exportChat')}
            >
              <i className="fa-solid fa-download" />
              <span className="hidden xl:inline">{t('aiAssistant.inline.export')}</span>
            </button>

            {/* Nút Làm mới */}
            <button
              type="button"
              className="chat-action-btn"
              disabled={isGenerating || !isChatHistoryReady}
              onClick={() => {
                if (confirm(t('aiAssistant.inline.resetThisConversation'))) {
                  updateChatHistory((prev) =>
                    prev.map((s) =>
                      s.id === activeSessionId ? createDefaultSession(s.id, currentLang) : s
                    )
                  );
                  setTargetDocuments([]);
                  setInputVal('');
                }
              }}
              title={t('aiAssistant.inline.resetConversation')}
            >
              <i className="fa-solid fa-rotate-left" />
            </button>
          </div>
        </header>

        {/* Vùng hiển thị tin nhắn (Scrollable) */}
        <div
          className={`ai-chat-viewport ${isChatDragOver ? 'is-chat-dragover-viewport' : ''}`}
          onDragOver={(e) => {
            if (e.dataTransfer.types.includes('application/x-tlbm-doc')) {
              e.preventDefault();
              e.dataTransfer.dropEffect = 'copy';
              if (!isChatDragOver) setIsChatDragOver(true);
            }
          }}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node)) {
              setIsChatDragOver(false);
            }
          }}
          onDrop={(e) => {
            const raw = e.dataTransfer.getData('application/x-tlbm-doc');
            if (raw) {
              e.preventDefault();
              e.stopPropagation();
              setIsChatDragOver(false);
              try {
                const doc = JSON.parse(raw);
                pinTargetDocument(doc);
                textareaRef.current?.focus();
              } catch (err) {
                console.error(err);
              }
            }
          }}
        >
          {/* Lưới thẻ Prompt gợi ý ban đầu */}
          {messages.length <= 1 && (
            <div className="ai-prompt-grid-container">
              <div className="prompt-grid-header">
                <h3>{t('aiAssistant.inline.quickQASuggestionsFor')}</h3>
                <p>{t('aiAssistant.inline.clickAnyCardToAutomatically')}</p>
              </div>

              <div className="ai-prompt-cards-grid">
                {PROMPT_TEMPLATES.map((tmpl, idx) => (
                  <button
                    type="button"
                    key={idx}
                    className="ai-prompt-card"
                            disabled={isGenerating || !isChatHistoryReady}
                    onClick={() => handleSend(t(`aiAssistant.templates.${tmpl.key}.query`))}
                    aria-label={`${t(`aiAssistant.templates.${tmpl.key}.title`)}. ${t(`aiAssistant.templates.${tmpl.key}.desc`)}`}
                  >
                    <span className={`prompt-card-icon border ${tmpl.iconClass}`}>
                      <i className={`fa-solid ${tmpl.icon}`} />
                    </span>
                    <span className="prompt-card-body">
                      <span className="prompt-card-title">{t(`aiAssistant.templates.${tmpl.key}.title`)}</span>
                      <span className="prompt-card-desc">{t(`aiAssistant.templates.${tmpl.key}.desc`)}</span>
                    </span>
                    <i className="fa-solid fa-arrow-right prompt-card-arrow" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Danh sách các tin nhắn */}
          <div className="ai-messages-list" role="log" aria-live="polite" aria-relevant="additions text" aria-label={t('aiAssistant.inline.chatHistory')}>
            {messages.map((msg) => {
              const isWelcomeMessage = msg.id.startsWith('msg-welcome-');
              const displayedText = isWelcomeMessage ? t('aiAssistant.defaultSession.welcome') : msg.text;
              const { body: messageBodyText, note: softFallbackNote } = msg.sender === 'ai'
                ? splitSoftFallbackNote(displayedText)
                : { body: displayedText, note: null };
              const displayedQuickPrompts = isWelcomeMessage
                ? [1, 2, 3, 4].map((index) => t(`aiAssistant.defaultSession.quickPrompt${index}`))
                : msg.quickPrompts;
              return (
              <div
                key={msg.id}
                className={`ai-chat-message-row ${msg.sender === 'user' ? 'is-user' : 'is-ai'}`}
              >
                {/* Avatar */}
                <div className="message-avatar">
                  {msg.sender === 'user' ? (
                    <span className="user-avatar-text">{currentUser.fullName.charAt(0) || 'U'}</span>
                  ) : (
                    <i className="fa-solid fa-brain" />
                  )}
                </div>

                {/* Bong bóng tin nhắn */}
                <div className="message-content-wrapper">
                  <div className="message-header-meta">
                    <span className="sender-name">
                      {msg.sender === 'user'
                        ? currentUser.fullName
                        : t('aiAssistant.assistantSenderName')}
                    </span>
                    <span className="message-time">{msg.time}</span>
                  </div>

                  <div className="message-bubble-body">
                    {msg.sender === 'user' && (msg.targetDocs?.length || msg.targetDoc) && (
                      <div className="message-target-doc-list">
                        {(msg.targetDocs && msg.targetDocs.length > 0 ? msg.targetDocs : msg.targetDoc ? [msg.targetDoc] : []).map((doc) => (
                          <div key={doc.filename} className="message-target-doc-tag">
                            <i className={`fa-solid ${doc.filename.toLowerCase().endsWith('.pdf') ? 'fa-file-pdf' : 'fa-file-lines'}`} />
                            <span>{doc.label || doc.filename}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <FormattedMessage text={messageBodyText} onInternalLink={handleInternalLink} />

                    {msg.isError && msg.retryText && (
                      <div className="ai-error-retry-row" role="alert">
                        <button
                          type="button"
                          className="ai-error-retry-btn"
                          disabled={isGenerating || !isChatHistoryReady}
                          onClick={() => handleSend(msg.retryText, msg.id)}
                        >
                          <i className="fa-solid fa-rotate-right" />
                          <span>{t('aiAssistant.inline.retrySend')}</span>
                        </button>
                      </div>
                    )}

                    {/* Dẫn link web & văn bản trích dẫn */}
                    {msg.citations && msg.citations.length > 0 && (
                      <CitationsBox
                        sources={msg.citations}
                        onPreview={(fn) => setPreviewFilename(fn)}
                        onNavigate={navigateToCitation}
                      />
                    )}

                    {softFallbackNote && (
                      <div className="ai-soft-fallback-note">
                        {softFallbackNote}
                      </div>
                    )}

                    {/* Câu hỏi gợi ý tiếp theo (Follow-up prompts) */}
                    {displayedQuickPrompts && displayedQuickPrompts.length > 0 && (
                      <div className="ai-followup-prompts">
                        {displayedQuickPrompts.map((qPrompt, pIdx) => (
                          <button
                            key={pIdx}
                            type="button"
                            className="followup-btn"
                                    disabled={isGenerating || !isChatHistoryReady}
                            onClick={() => handleSend(qPrompt)}
                          >
                            <i className="fa-solid fa-bolt-lightning" />
                            <span>{qPrompt}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Thanh công cụ hành động dưới phản hồi AI */}
                  {msg.sender === 'ai' && (
                    <div className="message-toolbar">
                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => handleCopy(msg.id, messageBodyText)}
                        title={t('aiAssistant.copy')}
                      >
                        <i className={`fa-solid ${copiedId === msg.id ? 'fa-check' : 'fa-copy'}`} />
                        <span>{copiedId === msg.id ? t('aiAssistant.copied') : t('aiAssistant.copy')}</span>
                      </button>

                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => handleSpeakText(msg.id, messageBodyText)}
                        title={speakingId === msg.id ? t('aiAssistant.inline.stopReading') : t('aiAssistant.readAloud')}
                      >
                        <i className={`fa-solid ${speakingId === msg.id ? 'fa-stop' : 'fa-volume-high'}`} />
                        <span>{speakingId === msg.id ? t('aiAssistant.inline.stopReading') : t('aiAssistant.inline.read')}</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
              );
            })}

            {/* Trạng thái AI đang suy nghĩ / tra cứu */}
            {isGenerating && (
              <div className="ai-chat-message-row is-ai">
                <div className="message-avatar">
                  <i className="fa-solid fa-brain" />
                </div>
                <div className="message-content-wrapper">
                  <div className="ai-thinking-card">
                    <span className="thinking-spinner" />
                    <span role="status" aria-live="polite">
                      {t('aiAssistant.inline.aiAssistantIsSearchingThe')}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* 3. THANH NHẬP LIỆU Ở ĐÁY */}
        <footer
          className={`ai-chat-bottom-input ${isChatDragOver ? 'is-chat-dragover' : ''}`}
          onDragOver={(e) => {
            if (e.dataTransfer.types.includes('application/x-tlbm-doc')) {
              e.preventDefault();
              e.dataTransfer.dropEffect = 'copy';
              if (!isChatDragOver) setIsChatDragOver(true);
            }
          }}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node)) {
              setIsChatDragOver(false);
            }
          }}
          onDrop={(e) => {
            const raw = e.dataTransfer.getData('application/x-tlbm-doc');
            if (raw) {
              e.preventDefault();
              e.stopPropagation();
              setIsChatDragOver(false);
              try {
                const doc = JSON.parse(raw);
                pinTargetDocument(doc);
                textareaRef.current?.focus();
              } catch (err) {
                console.error(err);
              }
            }
          }}
        >
          {/* Huy hiệu chỉ định tài liệu tra cứu riêng (Target Documents, tối đa 5) */}
          {targetDocuments.length > 0 && (
            <div className="target-doc-pinned-list">
              <div className="target-doc-pinned-header">
                <span className="target-doc-tag">
                  {t('aiAssistant.inline.targetedCount', { count: targetDocuments.length, max: MAX_PINNED_DOCUMENTS })}
                </span>
                {targetDocuments.length > 1 && (
                  <button
                    type="button"
                    className="target-doc-clear-all-btn"
                    onClick={() => setTargetDocuments([])}
                    title={t('aiAssistant.inline.clearAllTargetedDocuments')}
                  >
                    {t('aiAssistant.inline.clearAllTargetedDocuments')}
                  </button>
                )}
              </div>
              <div className="target-doc-pinned-items">
                {targetDocuments.map((doc) => (
                  <div key={doc.filename} className="target-doc-pinned-badge">
                    <div className="target-doc-badge-left">
                      <i
                        className={`fa-solid ${
                          doc.filename.toLowerCase().endsWith('.pdf')
                            ? 'fa-file-pdf text-danger'
                            : 'fa-file-lines text-primary'
                        }`}
                      />
                      <span className="target-doc-label" title={doc.filename}>
                        {doc.label || doc.filename}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="target-doc-remove-btn"
                      onClick={() => removeTargetDocument(doc.filename)}
                      title={t('aiAssistant.inline.clearTargetedDocument')}
                    >
                      <i className="fa-solid fa-xmark" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gợi ý khi đang kéo tệp qua thanh chat */}
          {isChatDragOver && (
            <div className="chat-drag-cue">
              <i className="fa-solid fa-crosshairs text-primary fa-bounce" />
              <span>
                {t('aiAssistant.inline.dropToTargetThisDocument')}
              </span>
            </div>
          )}

          {/* Thông báo tiến độ khi upload tệp trực tiếp */}
          {uploadProgress && (
            <div
              className={`chat-upload-indicator ${
                uploadProgress.status === 'done' || uploadProgress.status === 'completed'
                  ? 'is-success'
                  : uploadProgress.status === 'error' || uploadProgress.status === 'failed'
                  ? 'is-error'
                  : ''
              }`}
              role={uploadProgress.status === 'error' || uploadProgress.status === 'failed' ? 'alert' : 'status'}
              aria-live={uploadProgress.status === 'error' || uploadProgress.status === 'failed' ? 'assertive' : 'polite'}
            >
              {uploadProgress.status === 'done' || uploadProgress.status === 'completed' ? (
                <i className="fa-solid fa-circle-check text-success" />
              ) : uploadProgress.status === 'error' || uploadProgress.status === 'failed' ? (
                <i className="fa-solid fa-circle-exclamation text-danger" />
              ) : (
                <i className="fa-solid fa-circle-notch fa-spin text-primary" />
              )}
              <span>
                {uploadProgress.message ||
                  (t('aiAssistant.inline.processingDocument'))}
              </span>
            </div>
          )}

          <div
            className="input-box-container"
            onClick={(e) => {
              // Chạm vào bất kỳ khoảng trống nào trong thanh chat sẽ tự động focus vào textarea để bật bàn phím ảo
              if (!(e.target as HTMLElement).closest('button')) {
                textareaRef.current?.focus();
              }
            }}
          >
            {/* Input file ẩn: Tải lên ngay lập tức khi vừa chọn tệp */}
            {currentUser.isAdmin && (
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                    e.target.value = '';
                  }
                }}
                accept=".pdf,.doc,.docx,.txt,.csv,.pptx,.md,.markdown,.html,.htm,.json,.xml,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif,.gif"
              />
            )}

            {/* Nút Đính kèm file (icon kẹp giấy) - Giữ nguyên theo yêu cầu */}
            {currentUser.isAdmin && (
              <button
                type="button"
                className="input-tool-btn"
                onClick={() => fileInputRef.current?.click()}
                title={t('aiAssistant.attachFile')}
              >
                <i className="fa-solid fa-paperclip" />
              </button>
            )}

            {/* Khung gõ câu hỏi */}
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder={
                targetDocuments.length === 1
                  ? (t('aiAssistant.inline.askAboutValue', { value: targetDocuments[0].label || targetDocuments[0].filename }))
                  : targetDocuments.length > 1
                  ? (t('aiAssistant.inline.askAboutMultipleValue', { count: targetDocuments.length }))
                  : isMobile
                  ? t('aiAssistant.inputPlaceholderMobile')
                  : t('aiAssistant.inputPlaceholder')
              }
              aria-label={targetDocuments.length === 1
                ? t('aiAssistant.inline.askAboutValue', { value: targetDocuments[0].label || targetDocuments[0].filename })
                : targetDocuments.length > 1
                ? t('aiAssistant.inline.askAboutMultipleValue', { count: targetDocuments.length })
                : t('aiAssistant.inputPlaceholder')}
              rows={1}
              maxLength={MAX_QUESTION_LENGTH}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onFocus={() => {
                // Trên điện thoại, tự động cuộn nhẹ để giữ thanh chat nằm ngay trên bàn phím ảo
                if (isMobile) {
                  setTimeout(() => {
                    textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
                  }, 250);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  if (e.nativeEvent.isComposing) return;
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isGenerating}
              enterKeyHint="send"
              autoCapitalize="sentences"
              autoComplete="on"
            />

            {/* Nút Nhập giọng nói */}
            <button
              type="button"
              className={`input-tool-btn voice-btn ${isListening ? 'listening' : ''}`}
              onClick={handleToggleVoice}
              title={isListening ? t('aiAssistant.voiceActive') : t('aiAssistant.voiceMode')}
              aria-label={isListening ? t('aiAssistant.voiceActive') : t('aiAssistant.voiceMode')}
              aria-pressed={isListening}
            >
              <i className="fa-solid fa-microphone" />
            </button>

            {/* Nút Gửi */}
            <button
              type="button"
              className="send-message-btn"
              disabled={!inputVal.trim() || isGenerating || !isChatHistoryReady}
              onClick={() => handleSend()}
              title={t('aiAssistant.send')}
              aria-label={t('aiAssistant.send')}
            >
              <i className="fa-solid fa-paper-plane" />
            </button>
          </div>
        </footer>
      </main>

      {/* Modal Xem Trước Tài Liệu */}
      {previewFilename && (
        <DocumentPreviewModal
          key={previewFilename}
          filename={previewFilename}
          onClose={() => setPreviewFilename(null)}
        />
      )}

      <AlertModal open={aiAlertOpen} onClose={()=>setAiAlertOpen(false)} message={aiAlertMsg} />
    </div>
  );
}
