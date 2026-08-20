import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Menu,
  Plus,
  Send,
  Sparkles,
  MessageSquare,
  Search,
  Settings,
  User,
  X,
} from "lucide-react";

export const Route = createFileRoute("/")({
  component: ChatPage,
  head: () => ({
    meta: [
      { title: "Trợ lý AI — Trò chuyện thông minh" },
      {
        name: "description",
        content:
          "Giao diện trò chuyện AI tối giản, hỗ trợ Markdown và phản hồi theo thời gian thực.",
      },
    ],
  }),
});

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
};

const MOCK_HISTORY = [
  "Cách học tiếng Anh hiệu quả",
  "Gợi ý món ăn tối cho gia đình",
  "Viết email xin nghỉ phép",
  "Tóm tắt tin tức công nghệ",
  "Kế hoạch du lịch Đà Nẵng 3 ngày",
  "Giải thích khái niệm blockchain",
  "Công thức làm bánh mì Việt Nam",
  "Bài tập thể dục tại nhà",
  "Học lập trình React từ đầu",
  "Ý tưởng khởi nghiệp năm 2026",
  "Phân tích thơ Nguyễn Du",
  "Cách viết CV chuyên nghiệp",
];

const SAMPLE_REPLY = `Chắc chắn rồi! Đây là **một số gợi ý** giúp bạn bắt đầu:

## Các bước cơ bản

1. **Xác định mục tiêu** rõ ràng của bạn
2. Lập kế hoạch chi tiết theo tuần
3. Thực hành đều đặn mỗi ngày

### Ví dụ mã nguồn

\`\`\`javascript
function chao(ten) {
  return \`Xin chào, \${ten}!\`;
}

console.log(chao("bạn"));
\`\`\`

> Hãy nhớ rằng *sự kiên trì* là chìa khóa của thành công.

Bạn có muốn tôi giải thích chi tiết hơn về phần nào không?`;

function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const streamTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      if (streamTimerRef.current) clearInterval(streamTimerRef.current);
    };
  }, []);

  // const startStreaming = (fullText: string) => {
  //   const aiId = crypto.randomUUID();
  //   setMessages((prev) => [...prev, { id: aiId, role: "assistant", content: "", streaming: true }]);
  //   setIsStreaming(true);

  //   let i = 0;
  //   streamTimerRef.current = setInterval(() => {
  //     i += Math.floor(Math.random() * 4) + 2;
  //     if (i >= fullText.length) {
  //       i = fullText.length;
  //       if (streamTimerRef.current) clearInterval(streamTimerRef.current);
  //       setMessages((prev) =>
  //         prev.map((m) =>
  //           m.id === aiId ? { ...m, content: fullText, streaming: false } : m,
  //         ),
  //       );
  //       setIsStreaming(false);
  //       return;
  //     }
  //     setMessages((prev) =>
  //       prev.map((m) => (m.id === aiId ? { ...m, content: fullText.slice(0, i) } : m)),
  //     );
  //   }, 25);
  // };

  // const handleSend = () => {
  //   const text = input.trim();
  //   if (!text || isStreaming) return;
  //   setMessages((prev) => [
  //     ...prev,
  //     { id: crypto.randomUUID(), role: "user", content: text },
  //   ]);
  //   setInput("");
  //   setTimeout(() => startStreaming(SAMPLE_REPLY), 300);
  // };

  // 1. CẬP NHẬT LẠI HÀM START STREAMING
  const startStreaming = (fullText: string, aiId: string) => {
    let i = 0;
    streamTimerRef.current = setInterval(() => {
      i += Math.floor(Math.random() * 4) + 2;
      if (i >= fullText.length) {
        i = fullText.length;
        if (streamTimerRef.current) clearInterval(streamTimerRef.current);
        // Khi gõ xong chữ, tắt trạng thái streaming (tắt con trỏ nhấp nháy)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiId ? { ...m, content: fullText, streaming: false } : m,
          ),
        );
        setIsStreaming(false);
        return;
      }
      // Đang gõ chữ dần dần
      setMessages((prev) =>
        prev.map((m) => (m.id === aiId ? { ...m, content: fullText.slice(0, i) } : m)),
      );
    }, 25);
  };

  // 2. CẬP NHẬT LẠI HÀM XỬ LÝ GỬI TIN NHẮN
  const handleSend = async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    // Tạo ID cố định cho tin nhắn của AI lần này
    const aiId = crypto.randomUUID();

    // Hiển thị ngay tin nhắn của User và tạo sẵn bong bóng chat rỗng cho AI
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: text },
      { id: aiId, role: "assistant", content: "", streaming: true }
    ]);
    
    setInput("");
    setIsStreaming(true); // Khóa khung nhập liệu

    try {
      // Gọi API thực tế tới FastAPI
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: text })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Nhận được dữ liệu thật, truyền vào hàm chạy hiệu ứng gõ chữ
      startStreaming(data.reply, aiId);

    } catch (error) {
      console.error("Lỗi khi gọi API:", error);
      // Báo lỗi trực tiếp trên giao diện Chat
      startStreaming("Xin lỗi, hiện tại không thể kết nối đến máy chủ. Vui lòng kiểm tra lại backend.", aiId);
    }
  };

  const handleNewChat = () => {
    if (streamTimerRef.current) clearInterval(streamTimerRef.current);
    setIsStreaming(false);
    setMessages([]);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = input.trim().length > 0 && !isStreaming;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "w-72" : "w-0"
        } shrink-0 overflow-hidden border-r border-sidebar-border bg-sidebar transition-all duration-300 ease-in-out`}
      >
        <div className="flex h-full w-72 flex-col">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Sparkles className="h-4 w-4" />
              </div>
              <span className="text-sm font-semibold">Trợ lý AI</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded-md p-1.5 text-sidebar-foreground/70 hover:bg-sidebar-accent lg:hidden"
              aria-label="Đóng thanh bên"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="px-3">
            <button
              onClick={handleNewChat}
              className="flex w-full items-center gap-2 rounded-lg border border-sidebar-border bg-background px-3 py-2.5 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
            >
              <Plus className="h-4 w-4" />
              Đoạn chat mới
            </button>
          </div>

          <div className="px-3 pt-3">
            <div className="flex items-center gap-2 rounded-lg bg-sidebar-accent/60 px-3 py-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Tìm kiếm..."
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
            </div>
          </div>

          <div className="mt-4 px-3">
            <p className="px-2 pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Gần đây
            </p>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 pb-3">
            <ul className="space-y-0.5">
              {MOCK_HISTORY.map((title, idx) => (
                <li key={idx}>
                  <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-sidebar-foreground/90 transition-colors hover:bg-sidebar-accent">
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <div className="border-t border-sidebar-border p-3">
            <div className="flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-sidebar-accent">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent">
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">Người dùng</p>
                <p className="truncate text-xs text-muted-foreground">Tài khoản miễn phí</p>
              </div>
              <Settings className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="rounded-md p-2 text-foreground/70 transition-colors hover:bg-accent"
              aria-label="Bật/tắt thanh bên"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-sm font-medium">Trợ lý AI</h1>
          </div>
          <button className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-foreground/70 hover:bg-accent">
            <Sparkles className="h-3.5 w-3.5" />
            Nâng cấp
          </button>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-4 text-center">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/60 text-primary-foreground">
                <Sparkles className="h-7 w-7" />
              </div>
              <h2 className="text-3xl font-semibold tracking-tight">Xin chào, tôi có thể giúp gì?</h2>
              <p className="mt-2 text-muted-foreground">
                Sẵn sàng giải đáp các câu hỏi tổng quát về Y khoa
              </p>
              <div className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
                {[
                  "Triệu chứng của cảm cúm là gì?",
                  "Phân tích tương tác thuốc và rủi ro khi sử dụng kháng sinh",
                  "Phân tích rủi ro và tối ưu hóa liều lượng kháng sinh",
                  "Đánh giá hiệu quả của kháng sinh trong dự phòng nhiễm khuẩn",
                ].map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground/80 transition-colors hover:bg-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl px-4 py-6">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="sticky bottom-0 border-t border-border bg-background px-4 py-3">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm focus-within:border-foreground/30 focus-within:shadow-md">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Nhập tin nhắn..."
                rows={1}
                className="max-h-[200px] min-h-[40px] flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground"
              />
              <button
                onClick={handleSend}
                disabled={!canSend}
                aria-label="Gửi"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-all disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Trợ lý AI có thể mắc lỗi. Vui lòng kiểm tra thông tin quan trọng.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="mb-6 flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-secondary px-4 py-2.5 text-sm text-secondary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6 flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/60 text-primary-foreground">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1 pt-1">
        <div className="prose prose-sm prose-neutral max-w-none dark:prose-invert prose-pre:bg-muted prose-pre:text-foreground prose-code:before:content-none prose-code:after:content-none prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-[0.85em]">
          {message.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          ) : null}
          {message.streaming && <span className="blink-cursor" />}
        </div>
      </div>
    </div>
  );
}
