import React, { useState, useRef, useEffect, useCallback } from 'react';
import AlertModal from '@components/common/AlertModal';
import { ActivePageId } from '@app-types/navigation';
import {
  uploadDocumentAsync,
  getUploadProgress,
  askQuestion,
  getDocuments,
  getCategories,
  getDocumentFile,
  deleteDocuments,
  deleteDocument,
  reclassifyDocument,
  previewDocument,
  getAISettings,
} from '../../api';
import AISettingsModal from '../../components/AISettingsModal';
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

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  time: string;
  citations?: CitationSource[];
  quickPrompts?: string[];
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
  size?: number;
  file_type?: string;
}

interface CategoryItem {
  name: string;
  count: number;
}

const EMPTY_MESSAGES: ChatMessage[] = [];

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
  message?: unknown;
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

function getErrorMessage(error: unknown, fallback: string): string {
  if (typeof error !== 'object' || error === null) return fallback;

  const apiError = error as ApiError;
  const detail = apiError.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return typeof apiError.message === 'string' ? apiError.message : fallback;
}

function parseChatSessions(raw: string | null): ChatSession[] | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ChatSession[];
  } catch {
    return null;
  }
}

// 4 Thẻ gợi ý chuẩn nhận diện thương hiệu TLBM
const PROMPT_TEMPLATES = [
  {
    icon: 'fa-inbox',
    iconClass: 'text-primary bg-primary-subtle border-primary/30',
    title: 'Tiếp nhận Văn bản Đến',
    desc: 'Hỏi các bước vào sổ, scan số hóa và trình Ban Giám Hiệu bút phê.',
    query: 'Hướng dẫn quy trình tiếp nhận và xử lý văn bản đến trong ngày?',
  },
  {
    icon: 'fa-shield-halved',
    iconClass: 'text-danger bg-danger-subtle border-danger/30',
    title: 'Xử lý Văn bản Mật',
    desc: 'Quy chuẩn mã hóa, xác thực 2FA và quyền xem tài liệu Tuyệt Mật.',
    query: 'Quy định bảo mật và quy trình chuyển giao văn bản tuyệt mật?',
  },
  {
    icon: 'fa-file-signature',
    iconClass: 'text-warning-text bg-warning-subtle border-warning/30',
    title: 'Quy trình Trình Ký Số',
    desc: 'Sơ đồ luồng ký số Token PKI/Cloud HSM và phát hành văn bản đi.',
    query: 'Làm thế nào để tạo luồng trình ký số điện tử trên hệ thống?',
  },
  {
    icon: 'fa-sitemap',
    iconClass: 'text-success bg-success-subtle border-success/30',
    title: 'Cơ cấu & Phân quyền',
    desc: 'Tra cứu danh mục phòng ban Cấp 1, Cấp 2 và ma trận quyền CBNV.',
    query: 'Hệ thống phân quyền cán bộ nhân viên hoạt động như thế nào?',
  },
];

function getSessionUser() {
  try {
    const raw = localStorage.getItem('tlbm_session');
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        fullName: parsed.fullName || 'Huỳnh Vương Thanh Nhã',
        role: parsed.roleTitle || 'Cán bộ chuyên môn (Nhóm 8)',
        isAdmin: parsed.role === 'admin',
      };
    }
  } catch {
    // fallback
  }
  return {
    fullName: 'Huỳnh Vương Thanh Nhã',
    role: 'Cán bộ chuyên môn (Nhóm 8)',
    isAdmin: false,
  };
}

// Formatter Markdown Inline
function formatInline(str: string = '') {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      parts.push(str.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(<code key={match.index}>{token.slice(1, -1)}</code>);
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < str.length) {
    parts.push(str.substring(lastIndex));
  }
  return parts.length > 0 ? parts : str;
}

// Formatter Markdown đa dòng
function FormattedMessage({ text = '' }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="ps-3 mb-2 space-y-1 list-disc list-inside text-sm">
          {listItems.map((item, idx) => (
            <li key={idx} className="mb-0.5">{item}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`h4-${lineIdx}`} className="bubble-h4 text-base font-bold my-2 text-primary">
          {trimmed.replace('### ', '')}
        </h4>
      );
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
      const textContent = trimmed.replace(/^[-*]\s+|\d+\.\s+/, '');
      listItems.push(formatInline(textContent));
    } else {
      flushList();
      if (trimmed === '') {
        elements.push(<div key={`br-${lineIdx}`} className="h-2 my-1" />);
      } else {
        elements.push(
          <p key={`p-${lineIdx}`} className="bubble-p text-sm leading-relaxed mb-1.5">
            {formatInline(line)}
          </p>
        );
      }
    }
  });
  flushList();

  return <div className="message-content">{elements}</div>;
}

// Modal Xem Trước Tài Liệu
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<PreviewData | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'full' | 'pages'>('full');
  const contentRef = useRef<HTMLPreElement>(null);

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
      .catch((err: unknown) => {
        if (!cancelled) {
          const resErr = err as { response?: { data?: { detail?: string } }; message?: string };
          const msg = resErr.response?.data?.detail || resErr.message || 'Không thể tải nội dung tài liệu.';
          setError(msg);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [filename]);

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

  const isPdf = data?.render_mode === 'pdf';
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!isPdf || !data?.file_url) {
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    getDocumentFile(filename)
      .then((file) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(file);
        setPdfUrl(objectUrl);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const resErr = err as { message?: string };
          setError(resErr.message || 'Không thể tải tệp PDF.');
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [data?.file_url, filename, isPdf]);

  const fileUrl = isPdf && data?.file_url ? pdfUrl : null;

  return (
    <div className="preview-backdrop" onClick={onClose}>
      <div
        className={`preview-panel ${isPdf ? 'preview-panel-pdf' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="preview-header">
          <div className="preview-title-area">
            <div className="preview-title-icon">
              <i className={`fa-solid ${isPdf ? 'fa-file-pdf' : 'fa-file-lines'}`} />
            </div>
            <div>
              <div className="preview-filename" title={filename}>{filename}</div>
              {data && (
                <div className="preview-meta">
                  <span className="badge bg-light text-dark border me-1">{data.file_type}</span>
                  {!isPdf && data.total_pages && <span>• {data.total_pages} phần</span>}
                </div>
              )}
            </div>
          </div>

          <div className="preview-header-actions">
            {data && !isPdf && (
              <button
                type="button"
                className="preview-copy-btn"
                onClick={handleCopyAll}
                title="Sao chép toàn bộ nội dung"
              >
                <i className={`fa-solid ${copied ? 'fa-check' : 'fa-copy'}`} />
                <span>{copied ? 'Đã sao chép' : 'Sao chép'}</span>
              </button>
            )}

            {isPdf && fileUrl && (
              <a
                href={fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="preview-copy-btn"
                title="Mở tài liệu trong tab mới"
              >
                <i className="fa-solid fa-arrow-up-right-from-square" />
                <span>Mở tab mới</span>
              </a>
            )}

            <button type="button" className="preview-close-btn" onClick={onClose} title="Đóng (Esc)">
              <i className="fa-solid fa-xmark" />
            </button>
          </div>
        </div>

        {data && !isPdf && (data.total_pages || 0) > 1 && (
          <div className="preview-tabs">
            <button
              type="button"
              className={`preview-tab ${activeTab === 'full' ? 'active' : ''}`}
              onClick={() => setActiveTab('full')}
            >
              <i className="fa-solid fa-align-left me-1" />
              Toàn bộ văn bản
            </button>
            <button
              type="button"
              className={`preview-tab ${activeTab === 'pages' ? 'active' : ''}`}
              onClick={() => setActiveTab('pages')}
            >
              <i className="fa-solid fa-layer-group me-1" />
              Theo từng phần ({data.total_pages})
            </button>
          </div>
        )}

        <div className="preview-body">
          {loading && (
            <div className="d-flex align-items-center justify-content-center p-5 text-secondary">
              <span className="spinner-border spinner-border-sm me-2 text-primary" />
              Đang tải nội dung tài liệu...
            </div>
          )}

          {error && (
            <div className="alert alert-danger d-flex align-items-center gap-2 m-3">
              <i className="fa-solid fa-triangle-exclamation" />
              <span>{error}</span>
            </div>
          )}

          {data && !loading && isPdf && fileUrl && (
            <iframe src={fileUrl} className="preview-pdf-iframe w-full h-[600px] border-0" title={filename} />
          )}

          {data && !loading && !isPdf && activeTab === 'full' && (
            <pre ref={contentRef} className="preview-text">
              {data.full_text || '(Không có nội dung)'}
            </pre>
          )}

          {data && !loading && !isPdf && activeTab === 'pages' && data.pages && (
            <div>
              {data.pages.map((page, idx) => (
                <div key={idx} className="preview-page-block">
                  <div className="preview-page-label">
                    <i className="fa-solid fa-bookmark me-1" />
                    {page.page ? `Phần ${page.page}` : `Phần ${idx + 1}`}
                  </div>
                  <pre className="preview-text border-0 rounded-0 m-0">{page.text}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Component Hộp Trích Dẫn Văn Bản
function CitationsBox({
  sources,
  onPreview,
  onNavigate,
}: {
  sources?: CitationSource[];
  onPreview?: (filename: string) => void;
  onNavigate?: (page: ActivePageId) => void;
}) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="ai-citations-box">
      <div className="citations-title">
        <i className="fa-solid fa-link" />
        <span>Văn bản & liên kết liên quan trong hệ thống (Nhấp để mở):</span>
      </div>

      <div className="citations-list">
        {sources.map((src, idx) => {
          const fileName = src.file_name || src.label || `Tài liệu #${idx + 1}`;
          const code = src.code || (src.page ? `Trang ${src.page}` : src.section ? `Đoạn ${src.section}` : `Phần #${idx + 1}`);

          const isConfidential =
            src.type === 'confidential' ||
            fileName.toLowerCase().includes('mat') ||
            fileName.toLowerCase().includes('tuyet_mat');
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
              title={`Nhấp để mở tài liệu ${fileName}`}
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
              {isBusinessSpec && <span className="citation-code">Spec</span>}
              <span className="citation-code">{code}</span>
              <i className="fa-solid fa-arrow-up-right-from-square citation-ext-icon" />
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Component Chính AiAssistantPage
export default function AiAssistantPage({ onNavigate }: AiAssistantPageProps) {
  const currentUser = getSessionUser();
  // Sidebar states
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<'sessions' | 'docs'>('sessions');
  const [sessionSearch, setSessionSearch] = useState('');
  const [docSearch, setDocSearch] = useState('');

  // Sessions state
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    const savedSessions = parseChatSessions(localStorage.getItem('tlbm_chat_sessions_v2'));
    if (savedSessions) return savedSessions;
    return [
      {
        id: 'session-default',
        title: 'Tra cứu quy trình & văn bản',
        timeLabel: 'Hôm nay',
        snippet: 'Bắt đầu cuộc trò chuyện mới...',
        messages: [
          {
            id: 'msg-welcome',
            sender: 'ai',
            text: `**Xin chào Quý Cán bộ!**\n\nTôi là **Trợ Lý AI TLBM** — hệ thống hỏi đáp quy trình số hóa, văn bản nội bộ và hồ sơ tra cứu thông minh.\n\nTôi ưu tiên tìm kiếm trong kho tài liệu đã nạp (PDF, DOCX, TXT), phân tích văn bản đến/đi và liên kết chính xác đến các phân hệ nghiệp vụ. Bạn có thể chọn thẻ mẫu bên dưới hoặc gõ câu hỏi bất kỳ!`,
            time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
            quickPrompts: [
              'Quy trình tiếp nhận văn bản đến?',
              'Quy định bảo mật tài liệu Tuyệt Mật?',
              'Hướng dẫn ký số điện tử token PKI?',
              'Xem cơ cấu và phân quyền cán bộ nhân viên?',
            ],
          },
        ],
      },
    ];
  });

  const [activeSessionId, setActiveSessionId] = useState<string>('session-default');

  // Lưu sessions vào localStorage
  useEffect(() => {
    localStorage.setItem('tlbm_chat_sessions_v2', JSON.stringify(sessions));
  }, [sessions]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];
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
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [aiAlertOpen, setAiAlertOpen] = useState(false);
  const [aiAlertMsg, setAiAlertMsg] = useState('');

  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
    let cancelled = false;
    getCategories()
      .then((data) => {
        if (!cancelled) setCategories(data.categories || []);
      })
      .catch(console.error);

    if (currentUser.isAdmin) {
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
    }

    return () => {
      cancelled = true;
    };
  }, [currentUser.isAdmin]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  // Tạo phiên chat mới
  const handleNewChat = () => {
    const newId = `session-${Date.now()}`;
    const newSession: ChatSession = {
      id: newId,
      title: `Hội thoại mới #${sessions.length + 1}`,
      timeLabel: 'Hôm nay',
      snippet: 'Bắt đầu cuộc trò chuyện mới...',
      messages: [
        {
          id: `msg-${Date.now()}`,
          sender: 'ai',
          text: `**Phiên Trò Chuyện Mới Đã Sẵn Sàng!**\nBạn muốn tra cứu thông tin văn bản hoặc quy trình nào hôm nay? Hãy nhập câu hỏi hoặc chọn một gợi ý mẫu.`,
          time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
          quickPrompts: [
            'Tiếp nhận văn bản đến',
            'Xử lý văn bản mật',
            'Quy trình trình ký số',
            'Ma trận phân quyền nhân viên',
          ],
        },
      ],
    };
    setSessions([newSession, ...sessions]);
    setActiveSessionId(newId);
  };

  const handleDeleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (sessions.length <= 1) {
      alert('Không thể xóa phiên trò chuyện duy nhất.');
      return;
    }
    if (confirm('Bạn có chắc muốn xóa phiên trò chuyện này?')) {
      const updated = sessions.filter((s) => s.id !== id);
      setSessions(updated);
      if (activeSessionId === id) {
        setActiveSessionId(updated[0].id);
      }
    }
  };

  // Upload file và theo dõi tiến độ
  const handleFileUpload = async (file: File) => {
    if (!file) return;
    try {
      setUploadProgress({ status: 'uploading', message: `Đang tải tệp ${file.name}...` });
      const res = await uploadDocumentAsync(file);

      if (res.job_id) {
        const jobId = res.job_id;
        pollTimerRef.current = setInterval(async () => {
          try {
            const prog = await getUploadProgress(jobId);
            setUploadProgress(prog);
            if (prog.status === 'completed' || prog.status === 'failed') {
              if (pollTimerRef.current !== null) {
                clearInterval(pollTimerRef.current);
                pollTimerRef.current = null;
              }
              setTimeout(() => {
                setUploadProgress(null);
                refreshDocuments();
              }, 2000);
            }
          } catch {
            if (pollTimerRef.current !== null) {
              clearInterval(pollTimerRef.current);
              pollTimerRef.current = null;
            }
            setUploadProgress(null);
          }
        }, 1500);
      } else {
        setUploadProgress(null);
        refreshDocuments();
      }
    } catch (err: unknown) {
      alert(getErrorMessage(err, 'Lỗi tải lên tài liệu.'));
      setUploadProgress(null);
    }
  };

  const handleDropFiles = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDeleteDoc = async (filename: string) => {
    if (confirm(`Bạn có chắc muốn xóa tài liệu "${filename}" khỏi kho tri thức?`)) {
      try {
        await deleteDocument(filename);
        await refreshDocuments();
      } catch (err: unknown) {
        alert(getErrorMessage(err, 'Lỗi khi xóa tài liệu.'));
      }
    }
  };

  const handleReclassifyDoc = async (filename: string) => {
    try {
      await reclassifyDocument(filename);
      await refreshDocuments();
    } catch (err: unknown) {
      alert(getErrorMessage(err, 'Lỗi phân loại tài liệu.'));
    }
  };

  const handleClearAllDocs = async () => {
    if (confirm('CẢNH BÁO: Thao tác này sẽ xóa toàn bộ tài liệu trong cơ sở dữ liệu vector. Bạn có chắc không?')) {
      try {
        await deleteDocuments();
        await refreshDocuments();
      } catch (err: unknown) {
        alert(getErrorMessage(err, 'Lỗi khi dọn sạch kho tài liệu.'));
      }
    }
  };

  // Gửi câu hỏi đến AI
  const handleSend = async (overrideText?: string) => {
    const text = (overrideText || inputVal).trim();
    if (!text && !attachedFile) return;

    // Nếu có file đính kèm, upload trước
    if (attachedFile) {
      await handleFileUpload(attachedFile);
      setAttachedFile(null);
    }

    const userMsg: ChatMessage = {
      id: `user-${activeSessionId}-${messages.length}`,
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    };

    const newMessages = [...messages, userMsg];
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? {
              ...s,
              snippet: text.slice(0, 45) + '...',
              messages: newMessages,
            }
          : s
      )
    );

    setInputVal('');
    setIsGenerating(true);

    try {
      // Chuẩn bị lịch sử chat cho Backend
      const history = newMessages
        .slice(-6)
        .map((m) => ({ role: m.sender === 'user' ? 'user' : 'assistant', content: m.text }));

      const res = await askQuestion(text, history, selectedCategory || null);

      const aiMsg: ChatMessage = {
        id: `ai-${activeSessionId}-${newMessages.length}`,
        sender: 'ai',
        text: res.answer || res.text || 'Không có phản hồi từ mô hình AI.',
        time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        citations: res.sources || res.citations || [],
        quickPrompts: [
          'Tóm tắt các điểm quan trọng',
          'Trích xuất số liệu liên quan',
          'Văn bản quy định căn cứ',
        ],
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, messages: [...newMessages, aiMsg] }
            : s
        )
      );
    } catch (err: unknown) {
      console.warn('Backend call failed:', err);
      const aiMsg: ChatMessage = {
        id: `ai-${activeSessionId}-${newMessages.length}`,
        sender: 'ai',
        text: getErrorMessage(err, 'Không thể truy cập AI lúc này. Vui lòng thử lại sau.'),
        time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, messages: [...newMessages, aiMsg] }
            : s
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Đọc to câu trả lời bằng giọng nói tiếng Việt
  const handleSpeakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*#`_]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = 'vi-VN';
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    } else {
      alert('Trình duyệt không hỗ trợ nhận diện giọng nói TTS.');
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
      alert('Trình duyệt không hỗ trợ Web Speech API. Vui lòng sử dụng Google Chrome hoặc Microsoft Edge.');
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN';
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

  // Xuất file Markdown
  const handleExportChat = () => {
    const transcript = messages
      .map((m) => `[${m.time}] ${m.sender.toUpperCase()}:\n${m.text}\n`)
      .join('\n---\n\n');
    const blob = new Blob([transcript], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TLBM_AI_Chat_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Lọc danh sách phiên hội thoại
  const filteredSessions = sessions.filter(
    (s) =>
      s.title.toLowerCase().includes(sessionSearch.toLowerCase()) ||
      s.snippet.toLowerCase().includes(sessionSearch.toLowerCase())
  );

  // Lọc và gom nhóm tài liệu theo thư mục
  const filteredDocs = documents.filter((d) => {
    if (!docSearch.trim()) return true;
    const q = docSearch.toLowerCase();
    return (
      (d.filename && d.filename.toLowerCase().includes(q)) ||
      (d.category && d.category.toLowerCase().includes(q))
    );
  });

  const groupedDocs: Record<string, DocItem[]> = {};
  for (const doc of filteredDocs) {
    const cat = doc.category || 'Chưa phân loại';
    if (!groupedDocs[cat]) groupedDocs[cat] = [];
    groupedDocs[cat].push(doc);
  }

  return (
    <div className="ai-chat-page-root">
      {/* ====================================================================
         1. SIDEBAR (LỊCH SỬ CHAT & KHO TÀI LIỆU)
         ==================================================================== */}
      <aside className={`ai-chat-sidebar ${isSidebarOpen ? 'is-open' : 'is-collapsed'}`}>
        {/* Nút Tạo đoạn chat mới & Thu gọn */}
        <div className="ai-sidebar-top">
          <button type="button" className="new-chat-btn" onClick={handleNewChat}>
            <i className="fa-solid fa-plus" />
            <span>Đoạn chat mới</span>
          </button>

          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            title={isSidebarOpen ? 'Thu gọn sidebar' : 'Mở rộng sidebar'}
          >
            <i className={`fa-solid ${isSidebarOpen ? 'fa-angles-left' : 'fa-angles-right'}`} />
          </button>
        </div>

        {/* Tab Switcher: Hội thoại vs Kho tài liệu */}
        {isSidebarOpen && (
          <div className="sidebar-tab-switcher">
            <button
              type="button"
              className={`sidebar-tab-pill ${sidebarTab === 'sessions' ? 'active' : ''}`}
              onClick={() => setSidebarTab('sessions')}
            >
              <i className="fa-regular fa-message" />
              <span>Hội thoại</span>
            </button>
            {currentUser.isAdmin && <button
              type="button"
              className={`sidebar-tab-pill ${sidebarTab === 'docs' ? 'active' : ''}`}
              onClick={() => setSidebarTab('docs')}
            >
              <i className="fa-solid fa-folder-open" />
              <span>Kho tài liệu ({documents.length})</span>
            </button>}
          </div>
        )}

        {/* Tab 1: Danh sách các phiên trò chuyện */}
        {isSidebarOpen && sidebarTab === 'sessions' && (
          <>
            <div className="ai-sidebar-search">
              <i className="fa-solid fa-magnifying-glass" />
              <input
                type="text"
                placeholder="Tìm kiếm phiên chat..."
                value={sessionSearch}
                onChange={(e) => setSessionSearch(e.target.value)}
              />
            </div>

            <div className="ai-sidebar-sessions-list">
              <div className="session-group">
                <div className="session-group-title">Lịch sử trò chuyện</div>
                <div className="session-items">
                  {filteredSessions.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`session-item-btn ${s.id === activeSessionId ? 'active' : ''}`}
                      onClick={() => setActiveSessionId(s.id)}
                    >
                      <i className="fa-regular fa-message session-item-icon" />
                      <div className="session-item-text">
                        <div className="session-item-title">{s.title}</div>
                        <div className="session-item-snippet">{s.snippet}</div>
                      </div>
                      <span
                        className="session-item-delete hover:text-danger p-1"
                        onClick={(e) => handleDeleteSession(e, s.id)}
                        title="Xóa phiên chat"
                      >
                        <i className="fa-solid fa-trash-can text-xs" />
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Tab 2: Quản lý kho tài liệu */}
        {currentUser.isAdmin && isSidebarOpen && sidebarTab === 'docs' && (
          <div className="ai-sidebar-sessions-list p-2">
            <div className="ai-sidebar-search p-0 mb-2">
              <i className="fa-solid fa-magnifying-glass" />
              <input
                type="text"
                placeholder="Tìm file tài liệu..."
                value={docSearch}
                onChange={(e) => setDocSearch(e.target.value)}
              />
            </div>

            {/* Drag & Drop Upload Zone */}
            <div
              ref={dropZoneRef}
              className={`sidebar-dropzone mb-3 ${isDragging ? 'is-dragging' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDropFiles}
              onClick={() => fileInputRef.current?.click()}
            >
              <i className="fa-solid fa-cloud-arrow-up sidebar-dropzone-icon d-block" />
              <div className="sidebar-dropzone-text">Kéo thả hoặc Nhấp để nạp file</div>
              <div className="sidebar-dropzone-subtext">Hỗ trợ PDF, DOCX, TXT</div>
            </div>

            {/* Progress indicator */}
            {uploadProgress && (
              <div className="p-2 mb-2 bg-primary/10 border border-primary/20 rounded-lg text-xs">
                <div className="flex items-center gap-2 mb-1">
                  <span className="spinner-border spinner-border-sm text-primary" />
                  <span className="font-semibold text-primary">{uploadProgress.message}</span>
                </div>
              </div>
            )}

            {/* Danh mục tài liệu theo chủ đề */}
            {Object.keys(groupedDocs).length === 0 ? (
              <div className="text-center text-muted text-xs py-4">
                {documents.length === 0 ? 'Chưa có tài liệu nào trong kho.' : 'Không có kết quả tìm kiếm.'}
              </div>
            ) : (
              Object.entries(groupedDocs).map(([cat, docs]) => (
                <div key={cat} className="sidebar-doc-category mb-3">
                  <div className="sidebar-category-header flex items-center justify-between py-1 px-1 text-xs font-bold text-secondary">
                    <div className="flex items-center gap-1.5 truncate">
                      <i className="fa-solid fa-folder text-warning" />
                      <span className="truncate">{cat}</span>
                    </div>
                    <span className="sidebar-category-count px-1.5 py-0.5 rounded-full bg-surface-elevated border text-[10px]">
                      {docs.length}
                    </span>
                  </div>

                  <div className="space-y-1 mt-1">
                    {docs.map((d) => (
                      <div key={d.filename} className="sidebar-doc-row flex items-center justify-between p-1.5 rounded-md hover:bg-surface-hover text-xs">
                        <div className="flex items-center gap-1.5 truncate flex-1 min-w-0">
                          <i
                            className={`fa-solid ${
                              d.filename.toLowerCase().endsWith('.pdf')
                                ? 'fa-file-pdf text-danger'
                                : 'fa-file-lines text-primary'
                            }`}
                          />
                          <span className="sidebar-doc-name truncate" title={d.filename}>
                            {d.filename}
                          </span>
                        </div>
                        <div className="sidebar-doc-actions flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            className="sidebar-doc-btn hover:text-primary"
                            onClick={() => setPreviewFilename(d.filename)}
                            title="Xem trước"
                          >
                            <i className="fa-solid fa-eye" />
                          </button>
                          {d.category === 'Chưa phân loại' && (
                            <button
                              type="button"
                              className="sidebar-doc-btn hover:text-warning"
                              onClick={() => handleReclassifyDoc(d.filename)}
                              title="Phân loại lại AI"
                            >
                              <i className="fa-solid fa-wand-magic-sparkles" />
                            </button>
                          )}
                          <button
                            type="button"
                            className="sidebar-doc-btn delete-btn hover:text-danger"
                            onClick={() => handleDeleteDoc(d.filename)}
                            title="Xóa tài liệu"
                          >
                            <i className="fa-solid fa-trash" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}

            {documents.length > 0 && (
              <button
                type="button"
                className="w-full mt-2 py-1.5 px-3 rounded-lg border border-danger/30 text-danger hover:bg-danger/10 text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
                onClick={handleClearAllDocs}
              >
                <i className="fa-solid fa-trash-can" />
                <span>Xóa toàn bộ kho tài liệu</span>
              </button>
            )}
          </div>
        )}

        {/* Sidebar Footer */}
        {isSidebarOpen && (
          <div className="ai-sidebar-footer">
            <div className="ai-stats-badge">
              <span className="live-pulse-dot" />
              <span>Đã đồng bộ {documents.length} tài liệu TLBM</span>
            </div>
            <div className="ai-partner-tag">Hệ thống Trợ lý số · SmartDoc RAG AI</div>
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
            {!isSidebarOpen && (
              <button
                type="button"
                className="open-sidebar-btn"
                onClick={() => setIsSidebarOpen(true)}
                title="Mở lịch sử chat"
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
                  <span>Trợ Lý AI Tra Cứu Quy Trình & Văn Bản</span>
                  <span className="team-badge">LlamaIndex · ChromaDB</span>
                </div>
                <div className="ai-brand-sub">
                  Mô hình AI chuyên biệt cho hệ thống QLVB & RAG Tri Thức
                </div>
              </div>
            </div>
          </div>

          <div className="top-header-actions">
            {/* Bộ lọc chủ đề */}
            {categories.length > 0 && (
              <div className="model-selector-wrapper">
                <i className="fa-solid fa-filter text-primary" />
                <select
                  className="model-select"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="">Tất cả chủ đề ({documents.length})</option>
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
              <div className="model-selector-wrapper hidden md:flex">
                <span className="live-pulse-dot" />
                <span className="text-uppercase font-bold">{aiConfig.provider || 'GEMINI'}</span>
                <span className="opacity-50">|</span>
                <span>{aiConfig.llm_model || 'gemini-3.8-flash'}</span>
              </div>
            )}

            {/* Nút Cài đặt AI */}
            {currentUser.isAdmin && <button
              type="button"
              className="chat-action-btn"
              onClick={() => setShowSettingsModal(true)}
              title="Cài đặt mô hình & API Key"
            >
              <i className="fa-solid fa-gear" />
              <span className="hidden xl:inline">Cài đặt AI</span>
            </button>}

            {/* Nút Xuất file */}
            <button
              type="button"
              className="chat-action-btn"
              onClick={handleExportChat}
              title="Xuất nội dung chat ra tệp Markdown"
            >
              <i className="fa-solid fa-download" />
              <span className="hidden xl:inline">Xuất</span>
            </button>

            {/* Nút Làm mới */}
            <button
              type="button"
              className="chat-action-btn"
              onClick={() => {
                if (confirm('Làm mới đoạn trò chuyện này?')) {
                  setSessions((prev) =>
                    prev.map((s) =>
                      s.id === activeSessionId ? { ...s, messages: [s.messages[0]] } : s
                    )
                  );
                }
              }}
              title="Làm mới cuộc trò chuyện"
            >
              <i className="fa-solid fa-rotate-left" />
            </button>
          </div>
        </header>

        {/* Vùng hiển thị tin nhắn (Scrollable) */}
        <div className="ai-chat-viewport">
          {/* Lưới thẻ Prompt gợi ý ban đầu */}
          {messages.length <= 1 && (
            <div className="ai-prompt-grid-container">
              <div className="prompt-grid-header">
                <h3>Gợi Ý Tra Cứu Nhanh Dành Cho Bạn</h3>
                <p>Nhấp vào thẻ bất kỳ để gửi yêu cầu tra cứu tự động đến Trợ lý AI</p>
              </div>

              <div className="ai-prompt-cards-grid">
                {PROMPT_TEMPLATES.map((tmpl, idx) => (
                  <div
                    key={idx}
                    className="ai-prompt-card"
                    onClick={() => handleSend(tmpl.query)}
                  >
                    <div className={`prompt-card-icon border ${tmpl.iconClass}`}>
                      <i className={`fa-solid ${tmpl.icon}`} />
                    </div>
                    <div className="prompt-card-body">
                      <div className="prompt-card-title">{tmpl.title}</div>
                      <div className="prompt-card-desc">{tmpl.desc}</div>
                    </div>
                    <i className="fa-solid fa-arrow-right prompt-card-arrow" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Danh sách các tin nhắn */}
          <div className="ai-messages-list">
            {messages.map((msg) => (
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
                      {msg.sender === 'user' ? currentUser.fullName : `Trợ Lý AI TLBM (${aiConfig?.provider ? aiConfig.provider.toUpperCase() : 'GPT-4o'})`}
                    </span>
                    <span className="message-time">{msg.time}</span>
                  </div>

                  <div className="message-bubble-body">
                    <FormattedMessage text={msg.text} />

                    {/* Dẫn link web & văn bản trích dẫn */}
                    {msg.citations && msg.citations.length > 0 && (
                      <CitationsBox
                        sources={msg.citations}
                        onPreview={(fn) => setPreviewFilename(fn)}
                        onNavigate={onNavigate}
                      />
                    )}

                    {/* Câu hỏi gợi ý tiếp theo (Follow-up prompts) */}
                    {msg.quickPrompts && msg.quickPrompts.length > 0 && (
                      <div className="ai-followup-prompts">
                        {msg.quickPrompts.map((qPrompt, pIdx) => (
                          <button
                            key={pIdx}
                            type="button"
                            className="followup-btn"
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
                        onClick={() => handleCopy(msg.id, msg.text)}
                        title="Sao chép nội dung"
                      >
                        <i className={`fa-solid ${copiedId === msg.id ? 'fa-check' : 'fa-copy'}`} />
                        <span>{copiedId === msg.id ? 'Đã sao chép' : 'Sao chép'}</span>
                      </button>

                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => { setAiAlertMsg('Cảm ơn bạn đã đánh giá câu trả lời hữu ích!'); setAiAlertOpen(true); }}
                        title="Hữu ích"
                      >
                        <i className="fa-regular fa-thumbs-up" />
                      </button>

                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => { setAiAlertMsg('Hệ thống đã ghi nhận phản hồi để hoàn thiện mô hình AI!'); setAiAlertOpen(true); }}
                        title="Cần cải thiện"
                      >
                        <i className="fa-regular fa-thumbs-down" />
                      </button>

                      <button
                        type="button"
                        className="msg-tool-btn"
                        onClick={() => handleSpeakText(msg.text)}
                        title="Đọc to bằng giọng nói tiếng Việt"
                      >
                        <i className="fa-solid fa-volume-high" />
                        <span>Đọc</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Trạng thái AI đang suy nghĩ / tra cứu */}
            {isGenerating && (
              <div className="ai-chat-message-row is-ai">
                <div className="message-avatar">
                  <i className="fa-solid fa-brain" />
                </div>
                <div className="message-content-wrapper">
                  <div className="ai-thinking-card">
                    <span className="thinking-spinner" />
                    <span>Trợ lý AI đang tra cứu cơ sở dữ liệu văn bản TLBM và tổng hợp câu trả lời...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* 3. THANH NHẬP LIỆU Ở ĐÁY */}
        <footer className="ai-chat-bottom-input">
          {/* Tệp đính kèm xem trước */}
          {attachedFile && (
            <div className="attached-file-preview">
              <i className="fa-solid fa-paperclip" />
              <span className="attached-name">{attachedFile.name}</span>
              <button
                type="button"
                className="remove-file-btn"
                onClick={() => setAttachedFile(null)}
                title="Gỡ tệp"
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          )}

          <div className="input-box-container">
            {/* Input file ẩn */}
            {currentUser.isAdmin && <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setAttachedFile(e.target.files[0]);
                }
              }}
              accept=".pdf,.doc,.docx,.txt"
            />}

            {/* Nút Đính kèm file */}
            {currentUser.isAdmin && <button
              type="button"
              className="input-tool-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Đính kèm tài liệu (PDF, Word, TXT) để AI đọc & phân tích"
            >
              <i className="fa-solid fa-paperclip" />
            </button>}

            {/* Khung gõ câu hỏi */}
            <textarea
              className="chat-textarea"
              placeholder="Nhập câu hỏi tra cứu văn bản, quy trình nghiệp vụ... (Enter để gửi)"
              rows={1}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isGenerating}
            />

            {/* Nút Nhập giọng nói */}
            <button
              type="button"
              className={`input-tool-btn voice-btn ${isListening ? 'listening' : ''}`}
              onClick={handleToggleVoice}
              title={isListening ? 'Đang lắng nghe... (Nhấp để dừng)' : 'Nhập bằng giọng nói tiếng Việt'}
            >
              <i className="fa-solid fa-microphone" />
            </button>

            {/* Nút Gửi */}
            <button
              type="button"
              className="send-message-btn"
              disabled={(!inputVal.trim() && !attachedFile) || isGenerating}
              onClick={() => handleSend()}
              title="Gửi câu hỏi (Enter)"
            >
              <i className="fa-solid fa-paper-plane" />
            </button>
          </div>

          <div className="chat-disclaimer">
            <span>
              Trợ lý AI TLBM có thể hỗ trợ tra cứu văn bản và quy trình nghiệp vụ. Vui lòng đối chiếu với văn bản gốc đối với các tài liệu mật hoặc pháp lý quan trọng.
            </span>
          </div>
        </footer>
      </main>

      {/* Modal Xem Trước Tài Liệu */}
      {previewFilename && (
        <DocumentPreviewModal
          filename={previewFilename}
          onClose={() => setPreviewFilename(null)}
        />
      )}

      {/* Modal Cài Đặt AI */}
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
