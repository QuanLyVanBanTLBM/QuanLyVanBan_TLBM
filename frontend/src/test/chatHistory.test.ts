import { describe, it, expect } from 'vitest';

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  time: string;
}

interface ChatSession {
  id: string;
  title: string;
  timeLabel: 'Hôm nay' | 'Hôm qua' | '7 ngày trước';
  snippet: string;
  messages: ChatMessage[];
}

// Logic chuẩn hóa và di chuyển tiêu đề
function parseChatSessions(raw: string | null): ChatSession[] | null {
  if (!raw) return null;
  try {
    const list = JSON.parse(raw);
    if (!Array.isArray(list) || list.length === 0) return null;

    return list.map((s: ChatSession) => {
      const isDefaultTitle =
        !s.title ||
        s.title === 'Tra cứu quy trình & văn bản' ||
        s.title.startsWith('Hội thoại mới') ||
        s.title === 'Cuộc trò chuyện mới';

      if (isDefaultTitle && Array.isArray(s.messages)) {
        const firstUserMsg = s.messages.find((m) => m.sender === 'user');
        if (firstUserMsg && firstUserMsg.text && firstUserMsg.text.trim()) {
          return {
            ...s,
            title: firstUserMsg.text.trim(),
          };
        }
      }
      return s;
    });
  } catch {
    return null;
  }
}

// Logic lọc tìm kiếm theo tiêu đề, câu hỏi và tin nhắn
function filterSessions(sessions: ChatSession[], search: string): ChatSession[] {
  if (!search.trim()) return sessions;
  const query = search.trim().toLowerCase();

  return sessions.filter((s) => {
    // 1. Tiêu đề
    if (s.title && s.title.toLowerCase().includes(query)) return true;

    // 2. Snippet
    if (s.snippet && s.snippet.toLowerCase().includes(query)) return true;

    // 3. Nội dung câu hỏi và câu trả lời trong tin nhắn
    if (s.messages && Array.isArray(s.messages)) {
      return s.messages.some((m) => m.text && m.text.toLowerCase().includes(query));
    }

    return false;
  });
}

// Logic cập nhật tiêu đề khi gửi tin nhắn mới
function updateSessionOnSend(
  session: ChatSession,
  questionText: string
): { updatedTitle: string; initialSnippet: string } {
  const isFirstQuestion = !session.messages.some((m) => m.sender === 'user');
  const updatedTitle = isFirstQuestion ? questionText : session.title;
  const initialSnippet = questionText.length > 55 ? questionText.slice(0, 55) + '...' : questionText;
  return { updatedTitle, initialSnippet };
}

describe('Lịch sử trò chuyện SmartDoc RAG AI (Unit Tests)', () => {
  it('Yêu cầu 1: Tạo tiêu đề từ câu hỏi đầu tiên của người dùng', () => {
    const session: ChatSession = {
      id: 'session-1',
      title: 'Cuộc trò chuyện mới',
      timeLabel: 'Hôm nay',
      snippet: 'Chưa có tin nhắn...',
      messages: [{ id: 'msg-welcome', sender: 'ai', text: 'Xin chào', time: '10:00' }],
    };

    const firstQuestion = 'Quy trình xin nghỉ phép được quy định như thế nào?';
    const { updatedTitle, initialSnippet } = updateSessionOnSend(session, firstQuestion);

    expect(updatedTitle).toBe('Quy trình xin nghỉ phép được quy định như thế nào?');
    expect(initialSnippet).toContain('Quy trình xin nghỉ phép');
  });

  it('Yêu cầu 2: Giữ nguyên tiêu đề ban đầu cho các câu hỏi tiếp theo trong cùng phiên', () => {
    const session: ChatSession = {
      id: 'session-1',
      title: 'Quy trình xin nghỉ phép được quy định như thế nào?',
      timeLabel: 'Hôm nay',
      snippet: 'Đang thảo luận...',
      messages: [
        { id: 'msg-welcome', sender: 'ai', text: 'Xin chào', time: '10:00' },
        { id: 'user-1', sender: 'user', text: 'Quy trình xin nghỉ phép được quy định như thế nào?', time: '10:01' },
        { id: 'ai-1', sender: 'ai', text: 'Căn cứ điều lệ công ty...', time: '10:01' },
      ],
    };

    const followUpQuestion = 'Thời hạn nộp đơn trước bao nhiêu ngày?';
    const { updatedTitle } = updateSessionOnSend(session, followUpQuestion);

    // Tiêu đề ban đầu phải được giữ nguyên
    expect(updatedTitle).toBe('Quy trình xin nghỉ phép được quy định như thế nào?');
  });

  it('Yêu cầu 2 & 6: Tự động khôi phục và chuẩn hóa tiêu đề từ lịch sử đã lưu', () => {
    const rawSaved = JSON.stringify([
      {
        id: 'session-legacy',
        title: 'Tra cứu quy trình & văn bản',
        timeLabel: 'Hôm nay',
        snippet: 'Đoạn chat cũ',
        messages: [
          { id: 'msg-welcome', sender: 'ai', text: 'Xin chào', time: '09:00' },
          { id: 'user-msg', sender: 'user', text: 'Quy chế công tác văn thư năm 2026', time: '09:05' },
        ],
      },
    ]);

    const restored = parseChatSessions(rawSaved);
    expect(restored).not.toBeNull();
    expect(restored![0].title).toBe('Quy chế công tác văn thư năm 2026');
  });

  it('Yêu cầu 3: Tìm kiếm theo tiêu đề cuộc trò chuyện', () => {
    const sessions: ChatSession[] = [
      {
        id: 's1',
        title: 'Quy trình xin nghỉ phép',
        timeLabel: 'Hôm nay',
        snippet: 'Đơn nghỉ phép...',
        messages: [],
      },
      {
        id: 's2',
        title: 'Ký số văn bản điện tử',
        timeLabel: 'Hôm nay',
        snippet: 'Token PKI...',
        messages: [],
      },
    ];

    const results = filterSessions(sessions, 'nghỉ phép');
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe('s1');
  });

  it('Yêu cầu 3: Tìm kiếm theo nội dung câu hỏi hoặc tin nhắn bên trong cuộc trò chuyện', () => {
    const sessions: ChatSession[] = [
      {
        id: 's1',
        title: 'Hồ sơ nhân sự',
        timeLabel: 'Hôm nay',
        snippet: 'Hồ sơ...',
        messages: [
          { id: 'm1', sender: 'user', text: 'Quy định bảo mật tài liệu Tuyệt Mật cấp 1?', time: '10:00' },
        ],
      },
      {
        id: 's2',
        title: 'Hội nghị sơ kết',
        timeLabel: 'Hôm nay',
        snippet: 'Phòng họp...',
        messages: [
          { id: 'm2', sender: 'user', text: 'Đặt phòng họp lầu 3', time: '10:00' },
        ],
      },
    ];

    // Tìm từ khóa nằm trong câu hỏi người dùng nhưng không có trong tiêu đề
    const results = filterSessions(sessions, 'Tuyệt Mật');
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe('s1');
  });

  it('Yêu cầu 3: Trả về rỗng khi không tìm thấy kết quả phù hợp', () => {
    const sessions: ChatSession[] = [
      {
        id: 's1',
        title: 'Quy trình nghỉ phép',
        timeLabel: 'Hôm nay',
        snippet: 'Đơn nghỉ phép...',
        messages: [],
      },
    ];

    const results = filterSessions(sessions, 'từ khóa không hề tồn tại');
    expect(results).toHaveLength(0);
  });
});
