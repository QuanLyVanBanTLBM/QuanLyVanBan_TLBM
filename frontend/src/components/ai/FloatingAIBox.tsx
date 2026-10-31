import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActivePageId } from '@app-types/navigation';
import { askQuestion, getAISettings } from '../../api';
import { t as translate, useTranslation, type SupportedLanguage } from '@i18n/translate';

interface FloatingAIBoxProps {
  onNavigate?: (pageId: ActivePageId) => void;
}

interface Source {
  file_name?: string;
  page?: number | null;
  source_type?: string | null;
}

interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  createdAt: number;
  quickReplies?: string[];
  sources?: Source[];
}

interface AIConfig {
  provider?: string;
  llm_model?: string;
}

const MAX_WIDGET_QUESTION_LENGTH = 4000;

let floatingMsgSeq = 0;
function createBoxMessage(sender: Message['sender'], text: string, extras: Partial<Message> = {}): Message {
  return {
    id: `${sender}-${Date.now().toString(36)}-${++floatingMsgSeq}`,
    sender,
    text,
    createdAt: Date.now(),
    ...extras,
  };
}

function createInitialMessages(language: SupportedLanguage): Message[] {
  const t = (key: string) => translate(key, undefined, language);
  return [
    {
      id: 'msg-init',
      sender: 'ai',
      text: t('floatingAI.welcome'),
      createdAt: Date.now(),
      quickReplies: [
        t('floatingAI.suggestionIncoming'),
        t('floatingAI.suggestionLookup'),
        t('floatingAI.suggestionSigning'),
        t('floatingAI.suggestionPermissions'),
      ],
    },
  ];
}

function safeLinkTarget(href: string): string | null {
  if (href.startsWith('/') && !href.startsWith('//')) return href;
  try {
    const parsed = new URL(href, window.location.origin);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? href : null;
  } catch {
    return null;
  }
}

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\((?:https?:\/\/|\/)[^)]+\))/g;
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index));
    const token = match[0];
    if (token.startsWith('**')) {
      nodes.push(<strong key={`${keyPrefix}-${match.index}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('`')) {
      nodes.push(<code key={`${keyPrefix}-${match.index}`} className="rounded bg-surface-hover px-1">{token.slice(1, -1)}</code>);
    } else if (token.startsWith('[')) {
      const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const href = linkMatch ? safeLinkTarget(linkMatch[2]) : null;
      nodes.push(href ? (
        <a key={`${keyPrefix}-${match.index}`} href={href} target={href.startsWith('/') ? undefined : '_blank'} rel="noreferrer" className="text-primary underline">
          {linkMatch?.[1]}
        </a>
      ) : token);
    } else {
      nodes.push(<em key={`${keyPrefix}-${match.index}`}>{token.slice(1, -1)}</em>);
    }
    cursor = pattern.lastIndex;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

function FormattedMessage({ text }: { text: string }) {
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (line.trim().startsWith('```')) {
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        code.push(lines[index]);
        index += 1;
      }
      blocks.push(<pre key={`code-${index}`} className="my-2 overflow-x-auto rounded-lg bg-surface-hover p-2"><code>{code.join('\n')}</code></pre>);
      index += 1;
      continue;
    }

    const trimmed = line.trim();
    if (!trimmed) {
      blocks.push(<div key={`space-${index}`} className="h-1" />);
      index += 1;
      continue;
    }
    const isTableSeparator = (candidate: string) => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(candidate);
    if (trimmed.includes('|') && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
      const parseRow = (row: string) => row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
      const headers = parseRow(trimmed);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        rows.push(parseRow(lines[index]));
        index += 1;
      }
      blocks.push(<div key={`table-${index}`} className="my-2 max-w-full overflow-x-auto">
        <table className="w-full border-collapse text-left text-[11px]">
          <thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex} className="border border-subtle bg-surface-hover px-2 py-1">{renderInline(cell, `table-head-${index}-${cellIndex}`)}</th>)}</tr></thead>
          <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex} className="border border-subtle px-2 py-1">{renderInline(row[cellIndex] || '', `table-cell-${index}-${rowIndex}-${cellIndex}`)}</td>)}</tr>)}</tbody>
        </table>
      </div>);
      continue;
    }
    if (/^#{1,3}\s/.test(trimmed)) {
      blocks.push(<h4 key={`heading-${index}`} className="my-1 font-bold">{renderInline(trimmed.replace(/^#{1,3}\s+/, ''), `heading-${index}`)}</h4>);
      index += 1;
      continue;
    }
    if (trimmed.startsWith('> ')) {
      blocks.push(<blockquote key={`quote-${index}`} className="my-1 border-l-2 border-primary ps-2 text-text-secondary">{renderInline(trimmed.slice(2), `quote-${index}`)}</blockquote>);
      index += 1;
      continue;
    }
    if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      const ordered = /^\d+\.\s+/.test(trimmed);
      const items: string[] = [];
      while (index < lines.length && (ordered ? /^\s*\d+\.\s+/.test(lines[index]) : /^\s*[-*]\s+/.test(lines[index]))) {
        items.push(lines[index].trim().replace(ordered ? /^\d+\.\s+/ : /^[-*]\s+/, ''));
        index += 1;
      }
      const List = ordered ? 'ol' : 'ul';
      blocks.push(<List key={`list-${index}`} className={`my-1 space-y-0.5 ps-5 ${ordered ? 'list-decimal' : 'list-disc'}`}>
        {items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item, `list-${index}-${itemIndex}`)}</li>)}
      </List>);
      continue;
    }
    blocks.push(<p key={`paragraph-${index}`} className="my-1">{renderInline(line, `paragraph-${index}`)}</p>);
    index += 1;
  }
  return <div className="break-words">{blocks}</div>;
}

export default function FloatingAIBox({ onNavigate }: FloatingAIBoxProps) {
  const { t, currentLang } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState('');
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null);
  const [messages, setMessages] = useState<Message[]>(() => createInitialMessages(currentLang));
  const visibleMessages = useMemo(() => {
    const localizedWelcome = createInitialMessages(currentLang)[0];
    return messages.map((message) => message.id === 'msg-init'
      ? { ...message, text: localizedWelcome.text, quickReplies: localizedWelcome.quickReplies }
      : message);
  }, [messages, currentLang]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  const sendingRef = useRef(false);

  useEffect(() => {
    try {
      localStorage.removeItem('tlbm_ai_box_pos');
    } catch {
      // Storage may be unavailable in private browsing contexts.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    getAISettings()
      .then((settings: AIConfig) => {
        if (!cancelled) setAiConfig(settings);
      })
      .catch(() => {
        // The widget still uses the server's configured provider when it sends a request.
      });
    const handleConfigUpdate = (event: Event) => {
      const updated = (event as CustomEvent<AIConfig>).detail;
      if (updated && !cancelled) setAiConfig((current) => ({ ...current, ...updated }));
    };
    window.addEventListener('tlbm_ai_config_updated', handleConfigUpdate);
    return () => {
      cancelled = true;
      window.removeEventListener('tlbm_ai_config_updated', handleConfigUpdate);
    };
  }, []);

  useEffect(() => {
    if (isOpen && !isMinimized) chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [visibleMessages, isOpen, isMinimized, isTyping]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend ?? inputMessage).trim();
    if (!text || sendingRef.current) return;
    if (text.length > MAX_WIDGET_QUESTION_LENGTH) {
      setError('aiAssistant.msg.questionTooLong');
      return;
    }

    sendingRef.current = true;
    setError('');
    const previousMessages = messages.filter((message) => message.id !== 'msg-init');
    const history = previousMessages.slice(-8).map((message) => ({
      role: message.sender === 'ai' ? 'assistant' : 'user',
      content: message.text,
    }));
    setMessages((previous) => [...previous, createBoxMessage('user', text)]);
    setInputMessage('');
    setIsTyping(true);

    try {
      const response = await askQuestion(text, history);
      const answer = typeof response?.answer === 'string' && response.answer.trim()
        ? response.answer
        : t('floatingAI.emptyResponse');
      const sources = Array.isArray(response?.sources) ? response.sources as Source[] : [];
      setMessages((previous) => [...previous, createBoxMessage('ai', answer, { sources })]);
    } catch {
      setError('floatingAI.requestFailed');
    } finally {
      sendingRef.current = false;
      setIsTyping(false);
    }
  };

  const handleClearHistory = () => {
    if (isTyping) return;
    if (window.confirm(t('floatingAI.clearConfirm'))) {
      setMessages(createInitialMessages(currentLang));
      setError('');
    }
  };

  const handleQuickNavigate = (pageId: ActivePageId) => {
    onNavigate?.(pageId);
  };

  const openFullAssistant = () => {
    setIsOpen(false);
    handleQuickNavigate('ai_assistant');
  };

  const modelLabel = aiConfig?.llm_model;
  const sourceTypeLabels: Record<string, string> = {
    vanbanden: t('floatingAI.sourceTypes.incoming'),
    vanbandi: t('floatingAI.sourceTypes.outgoing'),
    tailieu: t('floatingAI.sourceTypes.document'),
    business_spec: t('floatingAI.sourceTypes.businessSpec'),
  };

  return (
    <>
      {!isOpen && (
        <div className="fixed bottom-[72px] right-6 sm:right-8 z-[9998]">
          <button
            type="button"
            className="relative w-16 h-16 rounded-full bg-gradient-to-tr from-purple-600 via-primary to-cyan-400 p-[2.5px] shadow-xl hover:shadow-2xl shadow-primary/25 cursor-pointer flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95 group"
            onClick={() => { setIsOpen(true); setIsMinimized(false); }}
            title={t('floatingAI.openTitle')}
            aria-label={t('floatingAI.openTitle')}
          >
            <div className="absolute inset-0 rounded-full bg-primary/30 animate-ping -z-10" />
            <div className="w-full h-full rounded-full bg-surface-elevated flex items-center justify-center text-primary text-2xl shadow-inner group-hover:bg-primary group-hover:text-white transition-colors duration-fast">
              <i className="fa-solid fa-robot" />
            </div>
            <span className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-emerald-500 border-2 border-surface" />
          </button>
        </div>
      )}

      {isOpen && (
        <div
          ref={windowRef}
          className={`fixed bottom-[68px] right-6 z-[9999] w-[390px] max-w-[calc(100vw-32px)] rounded-2xl bg-surface-elevated/95 backdrop-blur-xl border border-subtle shadow-2xl flex flex-col overflow-hidden transition-all duration-fast animate-in fade-in slide-in-from-bottom-4 ${
            isMinimized ? 'h-14' : 'h-fit max-h-[calc(100vh-120px)]'
          }`}
        >
          <div className="p-3 bg-surface border-b border-subtle flex items-center justify-between select-none">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-500 to-primary text-white flex items-center justify-center text-sm relative shadow-xs shrink-0">
                <i className="fa-solid fa-robot" />
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-surface" />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-xs font-bold text-text-main truncate">{t('floatingAI.title')}</span>
                  {modelLabel && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-subtle text-purple font-mono font-semibold truncate max-w-32" title={modelLabel}>
                      {modelLabel}
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-text-muted">{t('floatingAI.subtitle')}</div>
              </div>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              <button type="button" className="w-7 h-7 rounded-lg text-text-muted hover:text-text-main hover:bg-surface-hover flex items-center justify-center transition-colors text-xs cursor-pointer disabled:opacity-40" onClick={handleClearHistory} title={t('floatingAI.reset')} disabled={isTyping}>
                <i className="fa-solid fa-rotate-left" />
              </button>
              <button type="button" className="w-7 h-7 rounded-lg text-text-muted hover:text-primary hover:bg-primary-subtle flex items-center justify-center transition-colors text-xs cursor-pointer" onClick={openFullAssistant} title={t('floatingAI.fullAssistant')} aria-label={t('floatingAI.fullAssistant')}>
                <i className="fa-solid fa-expand" />
              </button>
              <button type="button" className="w-7 h-7 rounded-lg text-text-muted hover:text-text-main hover:bg-surface-hover flex items-center justify-center transition-colors text-xs cursor-pointer" onClick={() => setIsMinimized(!isMinimized)} title={isMinimized ? t('floatingAI.expand') : t('floatingAI.minimize')} aria-label={isMinimized ? t('floatingAI.expand') : t('floatingAI.minimize')}>
                <i className={`fa-solid ${isMinimized ? 'fa-window-maximize' : 'fa-window-minimize'}`} />
              </button>
              <button type="button" className="w-7 h-7 rounded-lg text-text-muted hover:text-danger hover:bg-danger-subtle flex items-center justify-center transition-colors text-xs cursor-pointer" onClick={() => setIsOpen(false)} title={t('floatingAI.close')} aria-label={t('floatingAI.close')}>
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          </div>

          {!isMinimized && (
            <>
              <div className="flex-none overflow-y-auto p-3.5 space-y-3 max-h-[min(55vh,24rem)]">
                {visibleMessages.map((message) => (
                  <div key={message.id} className={`flex gap-2.5 ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {message.sender === 'ai' && <div className="w-7 h-7 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-xs shrink-0 mt-0.5"><i className="fa-solid fa-brain" /></div>}
                    <div className="flex flex-col gap-1 max-w-[85%] min-w-0">
                      <div className={`p-3 text-xs leading-relaxed ${message.sender === 'user' ? 'bg-primary text-white rounded-2xl rounded-tr-sm shadow-xs' : 'bg-surface border border-subtle text-text-main rounded-2xl rounded-tl-sm shadow-xs'}`}>
                        <FormattedMessage text={message.text} />
                      </div>
                      {message.sources && message.sources.length > 0 && (
                        <div className="text-[10px] text-text-muted px-1">
                          <span className="font-semibold">{t('floatingAI.sources')}: </span>
                          {message.sources.map((source, index) => (
                            <span key={`${source.file_name || source.source_type || 'source'}-${index}`}>
                              {index > 0 ? ', ' : ''}{source.file_name || sourceTypeLabels[source.source_type || ''] || t('floatingAI.documentSource')}{source.page ? `, ${t('floatingAI.page', { page: source.page })}` : ''}
                            </span>
                          ))}
                        </div>
                      )}
                      {message.quickReplies && message.quickReplies.length > 0 && (
                        <div className="flex flex-col gap-1 mt-1">
                          {message.quickReplies.map((reply, replyIndex) => (
                            <button key={replyIndex} type="button" className="w-full text-left text-[11px] py-1.5 px-2.5 rounded-lg bg-surface-hover hover:bg-primary-subtle text-text-secondary hover:text-primary border border-subtle hover:border-primary/40 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => void handleSendMessage(reply)} disabled={isTyping}>
                              <i className="fa-solid fa-bolt-lightning text-[10px] text-warning" /><span>{reply}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      <time className="text-[10px] text-text-muted mt-0.5" dateTime={new Date(message.createdAt).toISOString()}>
                        {new Intl.DateTimeFormat(currentLang, { hour: '2-digit', minute: '2-digit' }).format(message.createdAt)}
                      </time>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex gap-2.5 justify-start items-center">
                    <div className="w-7 h-7 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-xs shrink-0"><i className="fa-solid fa-brain" /></div>
                    <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface border border-subtle text-text-muted text-xs" role="status" aria-label={t('floatingAI.thinking')}>
                      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" /><span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.2s]" /><span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <form className="p-2.5 bg-surface border-t border-subtle flex items-center gap-2" onSubmit={(event) => { event.preventDefault(); void handleSendMessage(); }}>
                <input type="text" maxLength={MAX_WIDGET_QUESTION_LENGTH} className="flex-1 min-w-0 bg-surface-elevated border border-subtle rounded-xl px-3 py-2 text-xs text-text-main placeholder:text-text-muted focus:border-primary transition-colors disabled:opacity-50" placeholder={t('floatingAI.placeholder')} value={inputMessage} onChange={(event) => setInputMessage(event.target.value)} disabled={isTyping} aria-label={t('floatingAI.placeholder')} />
                <button type="button" className="w-8 h-8 rounded-lg text-text-muted hover:text-primary hover:bg-primary-subtle flex items-center justify-center text-xs transition-colors cursor-pointer group" title={t('floatingAI.fullAssistant')} aria-label={t('floatingAI.fullAssistant')} onClick={openFullAssistant}>
                  <i className="fa-solid fa-expand text-sm" />
                </button>
                <button type="submit" className="w-8 h-8 rounded-lg bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center text-xs transition-colors shadow-xs cursor-pointer" disabled={!inputMessage.trim() || isTyping} title={t('floatingAI.send')} aria-label={t('floatingAI.send')}>
                  <i className="fa-solid fa-paper-plane" />
                </button>
              </form>
              {error && <div className="px-3 pb-2 text-xs text-danger bg-surface" role="alert">{t(error)}</div>}
            </>
          )}
        </div>
      )}
    </>
  );
}
