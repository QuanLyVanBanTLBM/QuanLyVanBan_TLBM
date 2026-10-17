import React, { useState, useEffect, useRef } from 'react';
import { ActivePageId } from '@app-types/navigation';

interface FloatingAIBoxProps {
  onNavigate?: (pageId: ActivePageId) => void;
}

interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  time: string;
  quickReplies?: string[];
}

let floatingMsgSeq = 0;
function createBoxMessage(sender: 'ai' | 'user', text: string): Message {
  return {
    id: `${sender}-${Date.now().toString(36)}-${++floatingMsgSeq}`,
    sender,
    text,
    time: 'Vừa xong',
  };
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 'msg-init',
    sender: 'ai',
    text: `**Xin chào Quý Cán bộ!**\nTôi là **Trợ Lý AI TLBM (GPT-4o)** — trợ lý tra cứu quy trình và hỗ trợ nghiệp vụ văn bản.\n\nHãy chọn gợi ý bên dưới hoặc gõ câu hỏi để tôi hỗ trợ bạn ngay!`,
    time: 'Vừa xong',
    quickReplies: [
      'Quy trình tiếp nhận văn bản đến?',
      'Quy chế xử lý văn bản Tuyệt Mật?',
      'Sơ đồ trình ký số điện tử?',
      'Phân quyền vai trò cán bộ nhân viên?',
    ],
  },
];

export default function FloatingAIBox({ onNavigate }: FloatingAIBoxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const windowRef = useRef<HTMLDivElement>(null);

  // Dọn dẹp vị trí cũ trong localStorage để cố định hẳn góc dưới bên phải
  useEffect(() => {
    try {
      localStorage.removeItem('tlbm_ai_box_pos');
    } catch {
      // ignore
    }
  }, []);

  // Cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    if (isOpen && !isMinimized) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isMinimized, isTyping]);

  // Trả lời AI thông minh
  const generateAIResponse = (query: string): string => {
    const q = query.toLowerCase();

    if (q.includes('văn bản đến') || q.includes('tiếp nhận') || q.includes('đến')) {
      return `**Quy Trình Tiếp Nhận Văn Bản Đến:**\n1. **Tiếp nhận & Vào sổ:** Văn thư tiếp nhận văn bản giấy hoặc điện tử, kiểm tra dấu và tính hợp lệ.\n2. **Số hóa & Phân loại:** Quét scan tài liệu PDF đính kèm, gắn số đến, phân loại độ khẩn (Thường/Khẩn/Hỏa tốc).\n3. **Trình Bút phê:** Chuyển Ban Giám Hiệu duyệt phân công đơn vị chủ trì xử lý qua hệ thống.`;
    }

    if (q.includes('mật') || q.includes('tuyệt mật') || q.includes('bảo mật')) {
      return `**Quy Chế Xử Lý Văn Bản Mật & Tuyệt Mật (TLBM):**\n- Phân định rõ 3 mức độ bảo mật: **Mật, Tối mật, Tuyệt mật**.\n- Văn bản Tuyệt mật được mã hóa đầu cuối, phân phối đích danh CBNV có thẩm quyền.\n- Hệ thống ghi vết nhật ký truy cập (Audit Log) theo tiêu chuẩn an toàn an ninh dữ liệu số.`;
    }

    if (q.includes('ký số') || q.includes('trình ký') || q.includes('phê duyệt')) {
      return `**Quy Trình Trình Ký Số Điện Tử:**\n- Cán bộ khởi tạo tờ trình/văn bản > Chọn luồng ký duyệt đa cấp.\n- Lãnh đạo xác thực ký số điện tử (USB Token / Cloud HSM).\n- Sau khi ký đủ thẩm quyền, hệ thống tự động ban hành và chuyển sang luồng Văn Bản Đi.`;
    }

    if (q.includes('phân quyền') || q.includes('nhân viên') || q.includes('cbnv')) {
      return `**Hệ Thống Phân Quyền & Hồ Sơ Cán Bộ Nhân Viên:**\n- Cấu trúc 2 cấp: Cấp 1 (Khối/Khu vực) và Cấp 2 (Đơn vị phòng ban).\n- Ma trận quyền RBAC chi tiết: Admin hệ thống, Lãnh đạo duyệt ký, Văn thư lưu trữ, Cán bộ chuyên môn.\n- Tự động che giấu năm sinh và mã hóa thông tin nhạy cảm của nhân sự.`;
    }

    return `**Trợ Lý AI TLBM (GPT-4o):**\nTôi đã ghi nhận yêu cầu của bạn về: *"${query}"*.\n\nTrong hệ thống TLBM, bạn có thể xem nhanh dữ liệu tại:\n- **Trang chủ Dashboard:** Thống kê văn bản đến/đi trong năm.\n- **Quản lý văn bản:** Danh mục phân loại và xử lý luồng công việc.\n- **Cài đặt:** Tùy chỉnh chế độ hiển thị Sáng/Tối theo sở thích.`;
  };

  const handleSendMessage = (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text) return;

    const userMsg = createBoxMessage('user', text);

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsTyping(true);

    // Giả lập độ trễ xử lý AI thông minh
    setTimeout(() => {
      const replyText = generateAIResponse(text);
      const aiMsg = createBoxMessage('ai', replyText);
      setMessages((prev) => [...prev, aiMsg]);
      setIsTyping(false);
    }, 650);
  };

  const handleClearHistory = () => {
    if (confirm('Bạn có muốn làm mới cuộc trò chuyện với Trợ lý AI không?')) {
      setMessages(INITIAL_MESSAGES);
    }
  };

  const handleQuickNavigate = (pageId: ActivePageId) => {
    if (onNavigate) {
      onNavigate(pageId);
    }
  };

  return (
    <>
      {/* 1. NÚT AI ROBOT NỔI CỐ ĐỊNH XUỐNG GÓC DƯỚI BÊN PHẢI (Nhích lên để không che thanh footer) */}
      {!isOpen && (
        <div className="fixed bottom-[72px] right-6 sm:right-8 z-[9998]">
          <button
            type="button"
            className="relative w-16 h-16 rounded-full bg-gradient-to-tr from-purple-600 via-primary to-cyan-400 p-[2.5px] shadow-xl hover:shadow-2xl shadow-primary/25 cursor-pointer flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95 group"
            onClick={() => {
              setIsOpen(true);
              setIsMinimized(false);
            }}
            title="Trợ Lý AI Tra Cứu TLBM (Cố định góc dưới bên phải - Bấm để mở)"
            aria-label="Mở Trợ Lý AI TLBM"
          >
            {/* Vòng hào quang sáng xung quanh */}
            <div className="absolute inset-0 rounded-full bg-primary/30 animate-ping -z-10" />
            <div className="w-full h-full rounded-full bg-surface-elevated flex items-center justify-center text-primary text-2xl shadow-inner group-hover:bg-primary group-hover:text-white transition-colors duration-fast">
              <i className="fa-solid fa-robot" />
            </div>
            {/* Chấm trạng thái trực tuyến */}
            <span className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-emerald-500 border-2 border-surface shadow-xs" />
          </button>
        </div>
      )}

      {/* 2. CỬA SỔ HỘI THOẠI AI CHATBOX (Cố định góc dưới bên phải, nằm trên thanh footer) */}
      {isOpen && (
        <div
          ref={windowRef}
          className={`fixed bottom-[68px] right-6 z-[9999] w-[390px] max-w-[calc(100vw-32px)] rounded-2xl bg-surface-elevated/95 backdrop-blur-xl border border-subtle shadow-2xl flex flex-col overflow-hidden transition-all duration-fast animate-in fade-in slide-in-from-bottom-4 ${
            isMinimized ? 'h-14' : 'h-[540px] max-h-[calc(100vh-120px)]'
          }`}
        >
          {/* Thanh tiêu đề (Header) */}
          <div className="p-3 bg-surface border-b border-subtle flex items-center justify-between select-none">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-500 to-primary text-white flex items-center justify-center text-sm relative shadow-xs">
                <i className="fa-solid fa-robot" />
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-surface" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-text-main">Trợ Lý AI TLBM</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-purple-subtle text-purple font-mono font-semibold">
                    GPT-4o
                  </span>
                </div>
                <div className="text-[10px] text-text-muted">Trợ lý hỗ trợ quy trình & nghiệp vụ</div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                className="w-7 h-7 rounded-lg text-text-muted hover:text-text-main hover:bg-surface-hover flex items-center justify-center transition-colors text-xs cursor-pointer"
                onClick={handleClearHistory}
                title="Làm mới đoạn chat"
              >
                <i className="fa-solid fa-rotate-left" />
              </button>

              {/* Nút phóng to full màn hình giống YouTube: chuyển sang trang Trợ lý AI */}
              <button
                type="button"
                className="w-7 h-7 rounded-lg text-text-muted hover:text-primary hover:bg-primary-subtle flex items-center justify-center transition-colors text-xs cursor-pointer group"
                onClick={() => {
                  setIsOpen(false);
                  handleQuickNavigate('ai_assistant');
                }}
                title="Phóng to toàn màn hình (Chuyển sang trang Trợ lý AI)"
                aria-label="Phóng to toàn màn hình"
              >
                <i className="fa-solid fa-expand transition-transform duration-fast group-hover:scale-110" />
              </button>

              <button
                type="button"
                className="w-7 h-7 rounded-lg text-text-muted hover:text-text-main hover:bg-surface-hover flex items-center justify-center transition-colors text-xs cursor-pointer"
                onClick={() => setIsMinimized(!isMinimized)}
                title={isMinimized ? 'Mở rộng hộp thoại' : 'Thu nhỏ'}
              >
                <i className={`fa-solid ${isMinimized ? 'fa-window-maximize' : 'fa-window-minimize'}`} />
              </button>

              <button
                type="button"
                className="w-7 h-7 rounded-lg text-text-muted hover:text-danger hover:bg-danger-subtle flex items-center justify-center transition-colors text-xs cursor-pointer"
                onClick={() => setIsOpen(false)}
                title="Đóng về nút AI nổi góc dưới"
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          </div>

          {/* Thân cửa sổ chat (khi không bị thu nhỏ) */}
          {!isMinimized && (
            <>
              <div className="flex-1 overflow-y-auto p-3.5 space-y-3 max-h-[380px]">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-2.5 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.sender === 'ai' && (
                      <div className="w-7 h-7 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-xs shrink-0 mt-0.5">
                        <i className="fa-solid fa-brain" />
                      </div>
                    )}

                    <div className="flex flex-col gap-1 max-w-[85%]">
                      <div
                        className={`p-3 text-xs leading-relaxed ${
                          msg.sender === 'user'
                            ? 'bg-primary text-white rounded-2xl rounded-tr-sm shadow-xs'
                            : 'bg-surface border border-subtle text-text-main rounded-2xl rounded-tl-sm shadow-xs'
                        }`}
                      >
                        {msg.text.split('\n').map((line, idx) => (
                          <p key={idx} className="my-0.5">
                            {line}
                          </p>
                        ))}
                      </div>

                      {/* Các nút bấm gợi ý câu hỏi nhanh (Quick Replies) */}
                      {msg.quickReplies && msg.quickReplies.length > 0 && (
                        <div className="flex flex-col gap-1 mt-1">
                          {msg.quickReplies.map((reply, rIdx) => (
                            <button
                              key={rIdx}
                              type="button"
                              className="w-full text-left text-[11px] py-1.5 px-2.5 rounded-lg bg-surface-hover hover:bg-primary-subtle text-text-secondary hover:text-primary border border-subtle hover:border-primary/40 transition-colors flex items-center gap-1.5 cursor-pointer"
                              onClick={() => handleSendMessage(reply)}
                            >
                              <i className="fa-solid fa-bolt-lightning text-[10px] text-warning" />
                              <span>{reply}</span>
                            </button>
                          ))}
                        </div>
                      )}

                      <span className="text-[10px] text-text-muted mt-0.5">
                        {msg.time}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Trạng thái AI đang phản hồi */}
                {isTyping && (
                  <div className="flex gap-2.5 justify-start items-center">
                    <div className="w-7 h-7 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-xs shrink-0">
                      <i className="fa-solid fa-brain" />
                    </div>
                    <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface border border-subtle text-text-muted text-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.2s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>

              {/* Thanh nhập tin nhắn ở đáy */}
              <form
                className="p-2.5 bg-surface border-t border-subtle flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
              >
                <input
                  type="text"
                  className="flex-1 bg-surface-elevated border border-subtle rounded-xl px-3 py-2 text-xs text-text-main placeholder:text-text-muted focus:border-primary transition-colors"
                  placeholder="Hỏi trợ lý AI về văn bản, quy trình..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                />

                {/* Nút phóng to toàn màn hình giống YouTube */}
                <button
                  type="button"
                  className="w-8 h-8 rounded-lg text-text-muted hover:text-primary hover:bg-primary-subtle flex items-center justify-center text-xs transition-colors cursor-pointer group"
                  title="Phóng to toàn màn hình (Chuyển sang trang Trợ lý AI)"
                  aria-label="Phóng to toàn màn hình"
                  onClick={() => {
                    setIsOpen(false);
                    handleQuickNavigate('ai_assistant');
                  }}
                >
                  <i className="fa-solid fa-expand text-sm transition-transform duration-fast group-hover:scale-110" />
                </button>

                <button
                  type="submit"
                  className="w-8 h-8 rounded-lg bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center text-xs transition-colors shadow-xs cursor-pointer"
                  disabled={!inputMessage.trim()}
                  title="Gửi câu hỏi"
                >
                  <i className="fa-solid fa-paper-plane" />
                </button>
              </form>
            </>
          )}
        </div>
      )}
    </>
  );
}


