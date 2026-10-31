import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import AlertModal from '@components/common/AlertModal';
import { ActivePageId } from '@app-types/navigation';
import { pageIdToPath } from '@lib/routes';
import {
  uploadDocumentAsync,
  getUploadProgress,
  askQuestion,
  getDocuments,
  getCategories,
  getDocumentFile,
  deleteDocuments,
  deleteDocument,
  previewDocument,
  getAISettings,
} from '../../api';
import AISettingsModal from '../../components/AISettingsModal';
import { t as translate, useTranslation, type SupportedLanguage } from '@i18n/translate';
import { usePermissions } from '@lib/permissions';
import '@styles/ai-chat.css';

interface AiAssistantPageProps {
  onNavigate?: (page: ActivePageId) => void;
}

interface CitationSource {
  file_name?: string;
  page?: number | string;
  section?: string | number;
  chunk_id?: string | number;
  source_type?: string;
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
}

interface ChatSession {
  id: string;
  title: string;
  timeLabel: 'Hﾃｴm nay' | 'Hﾃｴm qua' | '7 ngﾃy trﾆｰ盻嫩';
  snippet: string;
  messages: ChatMessage[];
}

interface DocItem {
  filename: string;
  category?: string;
  uploaded_at?: string;
  size?: number;
  file_type?: string;
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
    timeLabel: 'Hﾃｴm nay',
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
    'Tra c盻ｩu quy trﾃｬnh & vﾄハ b蘯｣n',
    'Cu盻冂 trﾃｲ chuy盻㌻ m盻嬖',
    'New Conversation',
    'New Chat',
  ];
  return defaultTitles.includes(title) || title.startsWith('H盻冓 tho蘯｡i m盻嬖');
}

function isDefaultSessionSnippet(snippet: string): boolean {
  return [
    translate('aiAssistant.defaultSession.snippet', undefined, 'vi'),
    translate('aiAssistant.defaultSession.snippet', undefined, 'en'),
  ].includes(snippet);
}

// 4 Th蘯ｻ g盻｣i ﾃｽ chu蘯ｩn nh蘯ｭn di盻㌻ thﾆｰﾆ｡ng hi盻㎡ TLBM; n盻冓 dung d盻議h n蘯ｱm 盻・aiAssistant.templates.<key>
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
        isAdmin: parsed.role === 'admin',
      };
    }
  } catch {
    // fallback
  }
  return {
    username: '',
    fullName: '',
    role: translate('aiAssistant.msg.defaultRole'),
    isAdmin: false,
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
function formatInline(str: string = ''): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\((?:https?:\/\/|\/)[^)]+\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      parts.push(str.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('[')) {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const href = link?.[2];
      const safeHref = href && (href.startsWith('/') && !href.startsWith('//') || /^https?:\/\//i.test(href));
      parts.push(safeHref ? (
        <a key={match.index} href={href} target={href?.startsWith('/') ? undefined : '_blank'} rel="noreferrer" className="text-primary underline">
          {link?.[1]}
        </a>
      ) : token);
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(<code key={match.index} className="rounded bg-surface-hover px-1">{token.slice(1, -1)}</code>);
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

// Formatter Markdown ﾄ疎 dﾃｲng
function FormattedMessage({ text = '' }: { text: string }) {
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
            <thead><tr>{headers.map((cell, index) => <th key={index} className="border border-border-subtle bg-surface-hover px-2 py-1">{formatInline(cell)}</th>)}</tr></thead>
            <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex} className="border border-border-subtle px-2 py-1">{formatInline(row[cellIndex] || '')}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
      continue;
    }
    if (/^#{1,3}\s/.test(trimmed)) {
      elements.push(<h4 key={`heading-${lineIdx}`} className="bubble-h4 text-base font-bold my-2 text-primary">{formatInline(trimmed.replace(/^#{1,3}\s+/, ''))}</h4>);
      lineIdx += 1;
      continue;
    }
    if (trimmed.startsWith('> ')) {
      elements.push(<blockquote key={`quote-${lineIdx}`} className="my-1 border-l-2 border-primary ps-3 text-secondary">{formatInline(trimmed.slice(2))}</blockquote>);
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
        {items.map((item, index) => <li key={index} className="mb-0.5">{formatInline(item)}</li>)}
      </List>);
      continue;
    }
    elements.push(<p key={`p-${lineIdx}`} className="bubble-p text-sm leading-relaxed mb-1.5">{formatInline(line)}</p>);
    lineIdx += 1;
  }

  return <div className="message-content">{elements}</div>;
}

// Modal Xem Trﾆｰ盻嫩 Tﾃi Li盻㎡
interface PreviewModalProps {
  filename: string;
  onClose: () => void;
}

interface PreviewData {
  full_text?: string;
  render_mode?: 'pdf' | 'text';
  file_url?: string;
  file_type?: string;
  total_pages?: number;
  pages?: Array<{ page?: number; text: string }>;
}

function DocumentPreviewModal({ filename, onClose }: PreviewModalProps) {
  const { t, currentLang } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<PreviewData | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'full' | 'pages'>('full');

  const displayTitle = filename;

  const isDocx = filename.toLowerCase().endsWith('.docx');
  const isPdf = data?.render_mode === 'pdf' || filename.toLowerCase().endsWith('.pdf');
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

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
    if (!isPdf) return;

    let cancelled = false;
    let objectUrl: string | null = null;
    getDocumentFile(filename)
      .then((file) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(file);
        setPdfUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) {
          setError(translate('aiAssistant.inline.unableToLoadPdfFile', undefined, currentLang));
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [filename, isPdf, currentLang]);

  const fileUrl = isPdf ? pdfUrl : null;
  const iconClass = isPdf ? 'icon-pdf' : isDocx ? 'icon-docx' : 'icon-txt';
  const iconFa = isPdf ? 'fa-file-pdf' : isDocx ? 'fa-file-word' : 'fa-file-lines';

  return (
    <div className="preview-backdrop" onClick={onClose}>
      <div
        className={`preview-panel ${isPdf ? 'preview-panel-pdf' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Thanh Cﾃｴng C盻･ */}
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
                  <span className="preview-badge badge-type">{data.file_type || (isPdf ? 'PDF' : 'DOCX')}</span>
                  {!isPdf && data.total_pages ? (
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
            {data && !isPdf && (
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

            {isPdf && fileUrl && (
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

        {/* Tab chuy盻ハ ﾄ黛ｻ品 toﾃn vﾄハ vs phﾃ｢n ﾄ双蘯｡n */}
        {data && !isPdf && (data.total_pages || 0) > 1 && (
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

        {/* Khung n盻冓 dung tﾃi li盻㎡ */}
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

          {data && !loading && !isPdf && activeTab === 'full' && (
            <div className="preview-paper">
              <div className="preview-paper-content">
                {data.full_text || t('aiAssistant.previewModal.noContent')}
              </div>
            </div>
          )}

          {data && !loading && !isPdf && activeTab === 'pages' && data.pages && (
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

// Component H盻冪 Trﾃｭch D蘯ｫn Vﾄハ B蘯｣n
function CitationsBox({
  sources,
  onPreview,
  onNavigate,
}: {
  sources?: CitationSource[];
  onPreview?: (filename: string) => void;
  onNavigate?: (page: ActivePageId) => void;
}) {
  const { t } = useTranslation();
  if (!sources || sources.length === 0) return null;

  return (
    <div className="ai-citations-box">
      <div className="citations-title">
        <i className="fa-solid fa-link" />
        <span>{t('aiAssistant.citations')}</span>
      </div>

      <div className="citations-list">
        {sources.map((src, idx) => {
          const defaultDocLabel = t('aiAssistant.inline.documentValue', { value: idx + 1 });
          const fileName = src.file_name || src.label || defaultDocLabel;
          const code = src.code || (src.page ? `${t('aiAssistant.inline.page')}${src.page}` : src.section ? `${t('aiAssistant.inline.section')}${src.section}` : `${t('aiAssistant.inline.part')}#${idx + 1}`);

          const isConfidential = src.type === 'confidential';
          const isBusinessSpec = src.source_type === 'business_spec';

          const handleClick = () => {
            const sourcePage: Partial<Record<string, ActivePageId>> = {
              vanbanden: 'documents_incoming' as ActivePageId,
              vanbandi: 'documents_outgoing' as ActivePageId,
              tailieu: 'resources' as ActivePageId,
            };
            const targetPage = src.targetPage || sourcePage[src.source_type || ''];
            if (targetPage && onNavigate) {
              onNavigate(targetPage);
            } else if (!src.source_type && src.file_name && onPreview) {
              onPreview(src.file_name);
            }
          };

          return (
            <button
              key={idx}
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
    </div>
  );
}

// Component Chﾃｭnh AiAssistantPage
export default function AiAssistantPage({ onNavigate }: AiAssistantPageProps) {
  const { t, currentLang } = useTranslation();
  const currentUser = getSessionUser();
  const routerNavigate = useNavigate();
  const navigateToCitation = (page: ActivePageId) => {
    if (onNavigate) onNavigate(page);
    else routerNavigate(pageIdToPath(page));
  };
  const { loaded: aiPermissionLoaded, can } = usePermissions();
  const canUseAI = aiPermissionLoaded && can('use_aiassistant');
  // Sidebar & Responsive states (T盻ｱ ﾄ黛ｻ冢g thu g盻肱 trﾃｪn thi蘯ｿt b盻・di ﾄ黛ｻ冢g <= 860px)
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
  const sidebarOpenButtonRef = useRef<HTMLButtonElement>(null);

  // T盻ｱ ﾄ黛ｻ冢g ﾄ妥ｳng m盻・sidebar vﾃ c蘯ｭp nh蘯ｭt isMobile khi chuy盻ハ ﾄ黛ｻ品 gi盻ｯa Desktop vﾃ Mobile
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
    const opener = sidebarOpenButtonRef.current;
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
      opener?.focus();
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

  // Khﾃｳa lﾆｰu tr盻ｯ c盻･c b盻・riﾃｪng bi盻㏄ theo tﾃi kho蘯｣n ﾄ黛ｻ・cﾃ｡ch ly d盻ｯ li盻㎡
  const storageKey = getChatStorageKey(currentUser.username);

  // Sessions state (ﾄ雪ｻ皇 t盻ｫ localStorage v盻嬖 fallback thﾃｴng minh)
  const [chatHistoryState, setChatHistoryState] = useState(() => {
    const initialSessions = [createDefaultSession('session-default', currentLang)];
    return {
      storageKey,
      sessions: initialSessions,
      activeSessionId: initialSessions[0].id,
    };
  });
  const activeChatHistoryState = chatHistoryState.storageKey === storageKey
    ? chatHistoryState
    : (() => {
        const nextSessions = [createDefaultSession('session-default', currentLang)];
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
    setChatHistoryState({ ...activeChatHistoryState, activeSessionId: id });
  };

  // T盻ｱ ﾄ黛ｻ冢g ﾄ黛ｻ渡g b盻・vﾃ lﾆｰu sessions vﾃo localStorage khi cﾃｳ thay ﾄ黛ｻ品
  useEffect(() => {
    if (storageKey && isChatHistoryReady && activeChatHistoryState.sessions.length > 0) {
      localStorage.setItem(storageKey, JSON.stringify(activeChatHistoryState.sessions));
    }
  }, [activeChatHistoryState, storageKey, isChatHistoryReady]);

  // Luﾃｴn ﾄ黛ｺ｣m b蘯｣o activeSession tr盻・ﾄ妥ｺng t盻嬖 phiﾃｪn ﾄ疎ng ch盻肱 (ho蘯ｷc phiﾃｪn ﾄ黛ｺｧu tiﾃｪn)
  const activeSession = isChatHistoryReady
    ? sessions.find((s) => s.id === activeSessionId) || sessions[0] || null
    : null;
  const messages = activeSession?.messages || EMPTY_MESSAGES;

  // Knowledge base state
  const [documents, setDocuments] = useState<DocItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [previewFilename, setPreviewFilename] = useState<string | null>(null);
  const [showSettingsModal, setShowSettingsModal] = useState<boolean>(false);
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null);

  // Chat input states
  const [inputVal, setInputVal] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const isGeneratingRef = useRef(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [aiAlertOpen, setAiAlertOpen] = useState(false);
  const [aiAlertMsg, setAiAlertMsg] = useState('');
  const [targetDocument, setTargetDocument] = useState<TargetDocInfo | null>(null);
  const [isChatDragOver, setIsChatDragOver] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const restoreInputFocusRef = useRef(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Gi蘯｣i phﾃｳng pollTimerRef khi unmount trﾃ｡nh rﾃｲ r盻・b盻・nh盻・
  useEffect(() => {
    return () => {
      if (pollTimerRef.current !== null) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  // T盻ｱ ﾄ黛ｻ冢g co giﾃ｣n chi盻「 cao textarea theo n盻冓 dung, lo蘯｡i b盻・thanh cu盻冢
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

  // Load tﾃi li盻㎡ & c蘯･u hﾃｬnh ban ﾄ黛ｺｧu
  const loadDocuments = useCallback(async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('L盻擁 t蘯｣i danh sﾃ｡ch tﾃi li盻㎡:', err);
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
      .catch(console.error);

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

  // T蘯｡o phiﾃｪn chat m盻嬖
  const handleNewChat = () => {
    if (!isChatHistoryReady) return;
    const newId = `session-${Date.now()}`;
    const newSession = createDefaultSession(newId, currentLang);
    updateChatHistory((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    setInputVal('');
    if (typeof window !== 'undefined' && window.innerWidth <= 860) {
      setIsSidebarOpen(false);
    }
  };

  const handleDeleteSession = (e: React.MouseEvent, id: string) => {
    if (!isChatHistoryReady) return;
    e.stopPropagation();
    if (confirm(t('aiAssistant.deleteSessionConfirm'))) {
      updateChatHistory((prev) => {
        const updated = prev.filter((s) => s.id !== id);
        if (updated.length === 0) {
          const freshId = `session-${Date.now()}`;
          const freshSession = createDefaultSession(freshId, currentLang);
          setActiveSessionId(freshId);
          return [freshSession];
        }
        if (activeSessionId === id) {
          setActiveSessionId(updated[0].id);
        }
        return updated;
      });
    }
  };

  // Upload file vﾃ theo dﾃｵi ti蘯ｿn ﾄ黛ｻ・
  const handleFileUpload = async (file: File) => {
    if (!file) return;

    const existingDocument = documents.find((document) => document.filename === file.name);
    const replaceExisting = existingDocument
      ? window.confirm(t('aiAssistant.replaceExistingConfirm', { filename: file.name }))
      : false;
    if (existingDocument && !replaceExisting) return;

    // H盻ｧy b盻・polling timer cﾅｩ n蘯ｿu ﾄ疎ng ch蘯｡y
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
              ? { ...prog, message: t('aiAssistant.inline.failedToUploadDocument') }
              : prog);

            if (isSuccess || isFailed) {
              if (pollTimerRef.current !== null) {
                clearInterval(pollTimerRef.current);
                pollTimerRef.current = null;
              }

              if (isSuccess) {
                // T盻ｱ ﾄ黛ｻ冢g t蘯｣i l蘯｡i danh sﾃ｡ch tﾃi li盻㎡ NGAY L蘯ｬP T盻ｨC
                await refreshDocuments();
                // Gi盻ｯ badge bﾃ｡o thﾃnh cﾃｴng trong 2.5s r盻妬 t盻ｱ ﾄ妥ｳng
                setTimeout(() => {
                  setUploadProgress(null);
                }, 2500);
              } else {
                // Bﾃ｡o l盻擁 vﾃ t盻ｱ ﾄ妥ｳng sau 4s
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
        await refreshDocuments();
      } catch {
        alert(t('aiAssistant.inline.failedToDeleteDocument'));
      }
    }
  };

  const handleClearAllDocs = async () => {
    if (confirm(t('aiAssistant.clearAllDocsConfirm')) &&
        prompt(t('aiAssistant.clearAllDocsTypeConfirm')) === 'DELETE') {
      try {
        await deleteDocuments('DELETE');
        await refreshDocuments();
      } catch {
        alert(t('aiAssistant.inline.failedToClearDocuments'));
      }
    }
  };

  // G盻ｭi cﾃ｢u h盻淑 ﾄ黛ｺｿn AI
  const handleSend = async (overrideText?: string) => {
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
    const currentMessages = sessionAtSend?.messages || [];
    const messageTimestamp = createMessageTimestamp();
    const userMsg: ChatMessage = {
      id: `user-${sessionId}-${messageTimestamp}`,
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString(currentLang === 'en' ? 'en-US' : 'vi-VN', { hour: '2-digit', minute: '2-digit' }),
      targetDoc: targetDocument || undefined,
    };
    const newMessages = [...currentMessages, userMsg];
    const isFirstQuestion = !currentMessages.some((message) => message.sender === 'user');
    const title = isFirstQuestion
      ? (text.length > 60 ? `${text.slice(0, 60).trimEnd()}...` : text)
      : (sessionAtSend?.title || text);
    const initialSnippet = text.length > 55 ? `${text.slice(0, 55)}...` : text;

    updateChatHistory((prev) => prev.map((session) => session.id === sessionId
      ? { ...session, title, snippet: initialSnippet, messages: newMessages }
      : session));
    setInputVal('');

    try {
      const history = newMessages
        .filter((message) => !message.id.startsWith('msg-welcome'))
        .slice(-8)
        .map((message) => ({ role: message.sender === 'user' ? 'user' : 'assistant', content: message.text }));
      const response = await askQuestion(text, history, selectedCategory || null, targetDocument?.filename || null);
      const aiText = response.answer || response.text;
      if (typeof aiText !== 'string' || !aiText.trim()) throw new Error('Empty AI response');

      const aiMsg: ChatMessage = {
        id: `ai-${sessionId}-${messageTimestamp}`,
        sender: 'ai',
        text: aiText,
        time: new Date().toLocaleTimeString(currentLang === 'en' ? 'en-US' : 'vi-VN', { hour: '2-digit', minute: '2-digit' }),
        citations: response.sources || response.citations || [],
        quickPrompts: [
          t('aiAssistant.msg.followUpSummary'),
          t('aiAssistant.msg.followUpFigures'),
          t('aiAssistant.msg.followUpBasis'),
        ],
      };
      const cleanAiText = aiText.replace(/[*#`_\n]/g, ' ').replace(/\s+/g, ' ').trim();
      const updatedSnippet = cleanAiText.length > 65 ? `${cleanAiText.slice(0, 65)}...` : cleanAiText;

      updateChatHistory((prev) => prev.map((session) => session.id === sessionId
        ? { ...session, snippet: updatedSnippet || initialSnippet, messages: [...newMessages, aiMsg] }
        : session));
    } catch (error: unknown) {
      console.warn('AI chat request failed:', error);
      setAiAlertMsg(t('aiAssistant.msg.aiUnavailable'));
      setAiAlertOpen(true);
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

  // ﾄ雪ｻ皇 to cﾃ｢u tr蘯｣ l盻拱 b蘯ｱng gi盻肱g nﾃｳi ti蘯ｿng Vi盻㏄
  const handleSpeakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*#`_]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = currentLang === 'en' ? 'en-US' : 'vi-VN';
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    } else {
      alert(t('aiAssistant.msg.ttsUnsupported'));
    }
  };

  // Nh蘯ｭn di盻㌻ gi盻肱g nﾃｳi ti蘯ｿng Vi盻㏄ (Web Speech API)
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
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = currentLang === 'en' ? 'en-US' : 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognition.onresult = (event: SpeechRecognitionResultEvent) => {
      const transcript = event.results[0][0].transcript;
      setInputVal((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };

    recognition.start();
  };

  // Xu蘯･t file Markdown
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

  // L盻皇 danh sﾃ｡ch phiﾃｪn h盻冓 tho蘯｡i theo t盻ｫ khﾃｳa (Tiﾃｪu ﾄ黛ｻ・ Cﾃ｢u h盻淑 user, N盻冓 dung tin nh蘯ｯn)
  const filteredSessions = (isChatHistoryReady ? sessions : []).filter((s) => {
    if (!sessionSearch.trim()) return true;
    const query = sessionSearch.trim().toLowerCase();

    // 1. Tﾃｬm theo tiﾃｪu ﾄ黛ｻ・cu盻冂 trﾃｲ chuy盻㌻
    if (s.title && s.title.toLowerCase().includes(query)) return true;

    // 2. Tﾃｬm theo ﾄ双蘯｡n trﾃｭch xem trﾆｰ盻嫩 (snippet)
    if (s.snippet && s.snippet.toLowerCase().includes(query)) return true;

    // 3. Tﾃｬm theo n盻冓 dung cﾃ｡c tin nh蘯ｯn (cﾃ｢u h盻淑 vﾃ cﾃ｢u tr蘯｣ l盻拱) trong phiﾃｪn
    if (s.messages && Array.isArray(s.messages)) {
      return s.messages.some((m) => m.text && m.text.toLowerCase().includes(query));
    }

    return false;
  });

  // L盻皇 vﾃ gom nhﾃｳm tﾃi li盻㎡ theo thﾆｰ m盻･c
  const filteredDocs = documents.filter((d) => {
    if (!docSearch.trim()) return true;
    const q = docSearch.toLowerCase();
    return (
      (d.filename && d.filename.toLowerCase().includes(q)) ||
      (d.category && d.category.toLowerCase().includes(q))
    );
  });

  const hierarchicalDocs: Record<string, RootFolderGroup> = useMemo(() => {
    const groups: Record<string, RootFolderGroup> = {};

    for (const doc of filteredDocs) {
      const rawCategory = doc.category?.trim();
      const normalizedCategory = rawCategory
        ?.normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd')
        .toLowerCase();
      const rootName = rawCategory && normalizedCategory !== 'chua phan loai'
        ? rawCategory
        : t('aiAssistant.uncategorized');

      if (!groups[rootName]) {
        groups[rootName] = {
          name: rootName,
          subFolders: {},
          directDocs: [],
          totalCount: 0,
        };
      }

      groups[rootName].totalCount += 1;
      groups[rootName].directDocs.push(doc);
    }

    return groups;
  }, [filteredDocs, t]);

  if (!aiPermissionLoaded) {
    return <div className="flex h-full items-center justify-center text-text-secondary">{t('aiAssistant.accessChecking')}</div>;
  }
  if (!canUseAI) {
    return <div className="flex h-full items-center justify-center p-6 text-center text-text-secondary">{t('aiAssistant.accessDenied')}</div>;
  }

  return (
    <div className="ai-chat-page-root">
      {/* Backdrop overlay khi m盻・Sidebar trﾃｪn ﾄ訴盻㌻ tho蘯｡i */}
      {isSidebarOpen && (
        <button
          className="ai-sidebar-mobile-backdrop"
          onClick={() => setIsSidebarOpen(false)}
          aria-label={t('aiAssistant.msg.closeSidebar')}
          type="button"
        />
      )}

      {/* ====================================================================
         1. SIDEBAR (L盻海H S盻ｬ CHAT & KHO TﾃI LI盻・)
         ==================================================================== */}
      <aside
        ref={sidebarRef}
        className={`ai-chat-sidebar ${isSidebarOpen ? 'is-open' : 'is-collapsed'}`}
        role={isMobile && isSidebarOpen ? 'dialog' : undefined}
        aria-modal={isMobile && isSidebarOpen ? true : undefined}
        aria-label={t('aiAssistant.inline.chatHistory')}
      >
        {/* Nﾃｺt T蘯｡o ﾄ双蘯｡n chat m盻嬖 & Thu g盻肱 */}
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

        {/* Tab Switcher: H盻冓 tho蘯｡i vs Kho tﾃi li盻㎡ */}
        {isSidebarOpen && (
          <div className="sidebar-tab-switcher">
            <button
              type="button"
              className={`sidebar-tab-pill ${sidebarTab === 'sessions' ? 'active' : ''}`}
              onClick={() => setSidebarTab('sessions')}
            >
              <i className="fa-regular fa-message" />
              <span>{t('aiAssistant.tabSessions')}</span>
            </button>
            <button
              type="button"
              className={`sidebar-tab-pill ${sidebarTab === 'docs' ? 'active' : ''}`}
              onClick={() => setSidebarTab('docs')}
            >
              <i className="fa-solid fa-folder-open" />
              <span>{t('aiAssistant.tabDocs')}</span>
              {documents.length > 0 && <span className="sidebar-tab-badge">{documents.length}</span>}
            </button>
          </div>
        )}

        {/* Tab 1: Danh sﾃ｡ch cﾃ｡c phiﾃｪn trﾃｲ chuy盻㌻ */}
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

        {/* Tab 2: Qu蘯｣n lﾃｽ kho tﾃi li盻㎡ */}
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
              {/* Drag & Drop Upload Zone - Ch盻・hi盻ハ th盻・cho Qu蘯｣n tr盻・viﾃｪn */}
              {currentUser.isAdmin && (
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
                  <i className="fa-solid fa-cloud-arrow-up sidebar-dropzone-icon" />
                  <span className="sidebar-dropzone-text">{t('aiAssistant.dropzoneText')}</span>
                  <span className="sidebar-dropzone-subtext">{t('aiAssistant.dropzoneSub')}</span>
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

              {/* Danh m盻･c tﾃi li盻㎡ theo c蘯･u trﾃｺc Thﾆｰ m盻･c nhi盻「 c蘯･p */}
              {Object.keys(hierarchicalDocs).length === 0 ? (
                <div className="sidebar-empty-state">
                  <i className="fa-regular fa-folder-open sidebar-empty-icon" />
                  <div>{documents.length === 0 ? t('aiAssistant.emptyDocs') : t('aiAssistant.emptyDocsSearch')}</div>
                </div>
              ) : (
                Object.values(hierarchicalDocs).map((root: RootFolderGroup) => {
                  const isRootCollapsed = !!collapsedRoots[root.name];
                  return (
                    <div key={root.name} className={`sidebar-doc-category ${isRootCollapsed ? 'is-collapsed' : ''}`}>
                      {/* Thﾆｰ m盻･c g盻祖 duy nh蘯･t (Level 1) */}
                      <button
                        type="button"
                        className="sidebar-category-header"
                        onClick={() => toggleRoot(root.name)}
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

                      {/* Danh sﾃ｡ch cﾃ｡c Folder nh盻・bﾃｪn trong Thﾆｰ m盻･c g盻祖 */}
                      {!isRootCollapsed && (
                        <div className="sidebar-root-content">
                          {Object.values(root.subFolders).map((sub: SubFolderGroup) => {
                            const subKey = `${root.name}_${sub.name}`;
                            const isSubCollapsed = !!collapsedSubs[subKey];
                            return (
                              <div
                                key={sub.name}
                                className={`sidebar-subfolder-card ${isSubCollapsed ? 'is-collapsed' : ''}`}
                              >
                                {/* Header c盻ｧa Folder nh盻・*/}
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

                                {/* Danh sﾃ｡ch Item bﾃｪn trong Folder nh盻・*/}
                                {!isSubCollapsed && (
                                  <div className="sidebar-doc-list">
                                    {sub.docs.map((d) => {
                                      const itemLabel = d.filename;

                                      return (
                                        <div
                                          key={d.filename}
                                          className={`sidebar-doc-row ${targetDocument?.filename === d.filename ? 'is-targeted' : ''}`}
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
                                            {/* Nﾃｺt ch盻・ﾄ黛ｻ杵h nhanh */}
                                            <button
                                              type="button"
                                              className={`sidebar-doc-btn pin-btn ${targetDocument?.filename === d.filename ? 'is-active text-primary' : ''}`}
                                              onClick={() => setTargetDocument(
                                                targetDocument?.filename === d.filename ? null : { filename: d.filename, label: itemLabel, category: d.category }
                                              )}
                                              title={
                                                targetDocument?.filename === d.filename
                                                  ? (t('aiAssistant.inline.unpinTargetDocument'))
                                                  : (t('aiAssistant.inline.targetThisDocumentForQ'))
                                              }
                                            >
                                              <i className="fa-solid fa-crosshairs" />
                                            </button>
                                            <button
                                              type="button"
                                              className="sidebar-doc-btn"
                                              onClick={() => setPreviewFilename(d.filename)}
                                              title={t('aiAssistant.preview')}
                                            >
                                              <i className="fa-solid fa-eye" />
                                            </button>
                                            {currentUser.isAdmin && (
                                              <button
                                                type="button"
                                                className="sidebar-doc-btn delete-btn"
                                                onClick={() => handleDeleteDoc(d.filename)}
                                                title={t('aiAssistant.deleteDoc')}
                                              >
                                                <i className="fa-solid fa-trash" />
                                              </button>
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

                          {/* Tﾃi li盻㎡ c蘯･p tr盻ｱc ti蘯ｿp (n蘯ｿu cﾃｳ) */}
                          {root.directDocs.length > 0 && (
                            <div className="sidebar-doc-list">
                              {root.directDocs.map((d) => (
                                <div
                                  key={d.filename}
                                  className={`sidebar-doc-row ${targetDocument?.filename === d.filename ? 'is-targeted' : ''}`}
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
                                      className={`sidebar-doc-btn pin-btn ${targetDocument?.filename === d.filename ? 'is-active text-primary' : ''}`}
                                      onClick={() => setTargetDocument(
                                        targetDocument?.filename === d.filename ? null : { filename: d.filename, label: d.filename, category: d.category }
                                      )}
                                      title={
                                        targetDocument?.filename === d.filename
                                          ? (t('aiAssistant.inline.unpinTargetDocument'))
                                          : (t('aiAssistant.inline.targetThisDocumentForQ'))
                                      }
                                    >
                                      <i className="fa-solid fa-crosshairs" />
                                    </button>
                                    <button
                                      type="button"
                                      className="sidebar-doc-btn"
                                      onClick={() => setPreviewFilename(d.filename)}
                                      title={t('aiAssistant.preview')}
                                    >
                                      <i className="fa-solid fa-eye" />
                                    </button>
                                    <button
                                      type="button"
                                      className="sidebar-doc-btn delete-btn"
                                      onClick={() => handleDeleteDoc(d.filename)}
                                      title={t('aiAssistant.deleteDoc')}
                                    >
                                      <i className="fa-solid fa-trash" />
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}

              {currentUser.isAdmin && documents.length > 0 && (
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
         2. MAIN CHAT STAGE (KHUNG TRﾃ・CHUY盻・ CHﾃ康H)
         ==================================================================== */}
      <main className="ai-chat-main-stage">
        {/* Top Header */}
        <header className="ai-chat-top-header">
          <div className="top-header-left">
            {!isSidebarOpen && (
              <button
                type="button"
                className="open-sidebar-btn"
                ref={sidebarOpenButtonRef}
                onClick={() => setIsSidebarOpen(true)}
                title={t('aiAssistant.expandSidebar')}
                aria-label={t('aiAssistant.expandSidebar')}
              >
                <i className="fa-solid fa-bars" />
              </button>
            )}

            <div className="ai-brand-badge">
              <div className="ai-brand-icon">
                <i className="fa-solid fa-robot" />
              </div>
              <div>
                <div className="ai-brand-title">
                  <span>{t('aiAssistant.pageTitle')}</span>
                  <span className="team-badge">LlamaIndex ﾂｷ ChromaDB</span>
                </div>
                <div className="ai-brand-sub">
                  {t('aiAssistant.pageSubtitle')}
                </div>
              </div>
            </div>
          </div>

          <div className="top-header-actions">
            {/* B盻・l盻皇 ch盻ｧ ﾄ黛ｻ・*/}
            {categories.length > 0 && (
              <div className="model-selector-wrapper category-filter-wrapper">
                <i className="fa-solid fa-filter text-primary" />
                <select
                  className="model-select"
                  aria-label={t('aiAssistant.allCategories')}
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="">{t('aiAssistant.allCategories')} ({documents.length})</option>
                  {categories.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.count})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Model Badge */}
            {aiConfig && (
              <div
                className="model-selector-wrapper ai-model-badge"
                style={{ display: 'flex' }}
                aria-live="polite"
                aria-label={`${aiConfig.provider || 'GEMINI'} ${aiConfig.llm_model || t('aiAssistant.modelLoading')}`}
                title={`${aiConfig.provider || 'GEMINI'} ${aiConfig.llm_model || t('aiAssistant.modelLoading')}`}
              >
                <span className="live-pulse-dot" />
                <span className="text-uppercase font-bold">{aiConfig.provider || 'GEMINI'}</span>
                <span className="opacity-50">|</span>
                <span>{aiConfig.llm_model || t('aiAssistant.defaultModel')}</span>
              </div>
            )}

            {/* Nﾃｺt Cﾃi ﾄ黛ｺｷt AI */}
            {currentUser.isAdmin && (
              <button
                type="button"
                className="chat-action-btn"
                onClick={() => setShowSettingsModal(true)}
                title={t('aiAssistant.inline.aiModelApiKeySettings')}
              >
                <i className="fa-solid fa-gear" />
                <span className="hidden xl:inline">{t('aiAssistant.inline.aiSettings')}</span>
              </button>
            )}

            {/* Nﾃｺt Xu蘯･t file */}
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

            {/* Nﾃｺt Lﾃm m盻嬖 */}
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
                }
              }}
              title={t('aiAssistant.inline.resetConversation')}
            >
              <i className="fa-solid fa-rotate-left" />
            </button>
          </div>
        </header>

        {/* Vﾃｹng hi盻ハ th盻・tin nh蘯ｯn (Scrollable) */}
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
                setTargetDocument(doc);
                textareaRef.current?.focus();
              } catch (err) {
                console.error(err);
              }
            }
          }}
        >
          {/* Lﾆｰ盻嬖 th蘯ｻ Prompt g盻｣i ﾃｽ ban ﾄ黛ｺｧu */}
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

          {/* Danh sﾃ｡ch cﾃ｡c tin nh蘯ｯn */}
          <div className="ai-messages-list" role="log" aria-live="polite" aria-relevant="additions text" aria-label={t('aiAssistant.inline.chatHistory')}>
            {messages.map((msg) => {
              const isWelcomeMessage = msg.id.startsWith('msg-welcome-');
              const displayedText = isWelcomeMessage ? t('aiAssistant.defaultSession.welcome') : msg.text;
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

                {/* Bong bﾃｳng tin nh蘯ｯn */}
                <div className="message-content-wrapper">
                  <div className="message-header-meta">
                    <span className="sender-name">
                      {msg.sender === 'user'
                        ? currentUser.fullName
                        : t('aiAssistant.assistantSenderName', { provider: aiConfig?.provider ? aiConfig.provider.toUpperCase() : 'GEMINI' })}
                    </span>
                    <span className="message-time">{msg.time}</span>
                  </div>

                  <div className="message-bubble-body">
                    {msg.sender === 'user' && msg.targetDoc && (
                      <div className="message-target-doc-tag">
                        <i className={`fa-solid ${msg.targetDoc.filename.toLowerCase().endsWith('.pdf') ? 'fa-file-pdf' : 'fa-file-lines'}`} />
                        <span>{msg.targetDoc.label || msg.targetDoc.filename}</span>
                      </div>
                    )}
                    <FormattedMessage text={displayedText} />

                    {/* D蘯ｫn link web & vﾄハ b蘯｣n trﾃｭch d蘯ｫn */}
                    {msg.citations && msg.citations.length > 0 && (
                      <CitationsBox
                        sources={msg.citations}
                        onPreview={(fn) => setPreviewFilename(fn)}
                        onNavigate={navigateToCitation}
                      />
                    )}

                    {/* Cﾃ｢u h盻淑 g盻｣i ﾃｽ ti蘯ｿp theo (Follow-up prompts) */}
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

                  {/* Thanh cﾃｴng c盻･ hﾃnh ﾄ黛ｻ冢g dﾆｰ盻嬖 ph蘯｣n h盻妬 AI */}
                  {msg.sender === 'ai' && (
                    <div className="message-toolbar">
                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => handleCopy(msg.id, displayedText)}
                        title={t('aiAssistant.copy')}
                      >
                        <i className={`fa-solid ${copiedId === msg.id ? 'fa-check' : 'fa-copy'}`} />
                        <span>{copiedId === msg.id ? t('aiAssistant.copied') : t('aiAssistant.copy')}</span>
                      </button>

                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => handleSpeakText(displayedText)}
                        title={t('aiAssistant.readAloud')}
                      >
                        <i className="fa-solid fa-volume-high" />
                        <span>{t('aiAssistant.inline.read')}</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
              );
            })}

            {/* Tr蘯｡ng thﾃ｡i AI ﾄ疎ng suy nghﾄｩ / tra c盻ｩu */}
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

        {/* 3. THANH NH蘯ｬP LI盻・ 盻・ﾄ静〆 */}
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
                setTargetDocument(doc);
                textareaRef.current?.focus();
              } catch (err) {
                console.error(err);
              }
            }
          }}
        >
          {/* Huy hi盻㎡ ch盻・ﾄ黛ｻ杵h tﾃi li盻㎡ tra c盻ｩu riﾃｪng (Target Document) */}
          {targetDocument && (
            <div className="target-doc-pinned-badge">
              <div className="target-doc-badge-left">
                <i
                  className={`fa-solid ${
                    targetDocument.filename.toLowerCase().endsWith('.pdf')
                      ? 'fa-file-pdf text-danger'
                      : 'fa-file-lines text-primary'
                  }`}
                />
                <span className="target-doc-label" title={targetDocument.filename}>
                  {targetDocument.label || targetDocument.filename}
                </span>
                <span className="target-doc-tag">
                  {t('aiAssistant.inline.targeted')}
                </span>
              </div>
              <button
                type="button"
                className="target-doc-remove-btn"
                onClick={() => setTargetDocument(null)}
                title={t('aiAssistant.inline.clearTargetedDocument')}
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          )}

          {/* G盻｣i ﾃｽ khi ﾄ疎ng kﾃｩo t盻㎝ qua thanh chat */}
          {isChatDragOver && (
            <div className="chat-drag-cue">
              <i className="fa-solid fa-crosshairs text-primary fa-bounce" />
              <span>
                {t('aiAssistant.inline.dropToTargetThisDocument')}
              </span>
            </div>
          )}

          {/* Thﾃｴng bﾃ｡o ti蘯ｿn ﾄ黛ｻ・khi upload t盻㎝ tr盻ｱc ti蘯ｿp */}
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
              // Ch蘯｡m vﾃo b蘯･t k盻ｳ kho蘯｣ng tr盻創g nﾃo trong thanh chat s蘯ｽ t盻ｱ ﾄ黛ｻ冢g focus vﾃo textarea ﾄ黛ｻ・b蘯ｭt bﾃn phﾃｭm 蘯｣o
              if (!(e.target as HTMLElement).closest('button')) {
                textareaRef.current?.focus();
              }
            }}
          >
            {/* Input file 蘯ｩn: T蘯｣i lﾃｪn ngay l蘯ｭp t盻ｩc khi v盻ｫa ch盻肱 t盻㎝ */}
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
                accept=".pdf,.docx,.txt,.csv,.pptx,.md,.markdown,.html,.htm,.json,.xml,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif,.gif"
              />
            )}

            {/* Nﾃｺt ﾄ静ｭnh kﾃｨm file (icon k蘯ｹp gi蘯･y) - Gi盻ｯ nguyﾃｪn theo yﾃｪu c蘯ｧu */}
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

            {/* Khung gﾃｵ cﾃ｢u h盻淑 */}
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder={
                targetDocument
                  ? (t('aiAssistant.inline.askAboutValue', { value: targetDocument.label || targetDocument.filename }))
                  : isMobile
                  ? t('aiAssistant.inputPlaceholderMobile')
                  : t('aiAssistant.inputPlaceholder')
              }
              aria-label={targetDocument
                ? t('aiAssistant.inline.askAboutValue', { value: targetDocument.label || targetDocument.filename })
                : t('aiAssistant.inputPlaceholder')}
              rows={1}
              maxLength={MAX_QUESTION_LENGTH}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onFocus={() => {
                // Trﾃｪn ﾄ訴盻㌻ tho蘯｡i, t盻ｱ ﾄ黛ｻ冢g cu盻冢 nh蘯ｹ ﾄ黛ｻ・gi盻ｯ thanh chat n蘯ｱm ngay trﾃｪn bﾃn phﾃｭm 蘯｣o
                if (isMobile) {
                  setTimeout(() => {
                    textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
                  }, 250);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isGenerating}
              enterKeyHint="send"
              autoCapitalize="sentences"
              autoComplete="on"
            />

            {/* Nﾃｺt Nh蘯ｭp gi盻肱g nﾃｳi */}
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

            {/* Nﾃｺt G盻ｭi */}
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

      {/* Modal Xem Trﾆｰ盻嫩 Tﾃi Li盻㎡ */}
      {previewFilename && (
        <DocumentPreviewModal
          filename={previewFilename}
          onClose={() => setPreviewFilename(null)}
        />
      )}

      {/* Modal Cﾃi ﾄ雪ｺｷt AI */}
      {showSettingsModal && (
        <AISettingsModal
          onClose={() => setShowSettingsModal(false)}
          onSaved={(newConfig: AIConfig) => setAiConfig(newConfig)}
        />
      )}
      <AlertModal open={aiAlertOpen} onClose={()=>setAiAlertOpen(false)} message={aiAlertMsg} />
    </div>
  );
}
