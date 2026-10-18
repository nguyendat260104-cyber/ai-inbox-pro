(function() {
  const SCRIPT_URL = document.currentScript ? document.currentScript.src : "http://127.0.0.1:8080/widget/chat_widget.js";
  const BASE_ORIGIN = new URL(SCRIPT_URL).origin;

  // 1. Inject Stylesheet
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = `${BASE_ORIGIN}/widget/chat_widget.css`;
  document.head.appendChild(link);

  // 2. State & Storage
  const STORAGE_KEY = "ai_inbox_conv_id";
  let conversationId = localStorage.getItem(STORAGE_KEY) || null;
  let isHandoffActive = false;

  // 3. Inject DOM Structure
  const root = document.createElement("div");
  root.id = "ai-chat-root";
  root.innerHTML = `
    <button class="ai-launcher-btn" id="ai-toggle-btn" title="Trợ lý bán hàng">
      <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0-2-.9-2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
    </button>

    <div class="ai-chat-dialog" id="ai-dialog">
      <div class="ai-header">
        <div class="ai-header-info">
          <div class="ai-avatar">🤖</div>
          <div>
            <div class="ai-title">Trợ Lý Tư Vấn Bán Hàng</div>
            <div class="ai-status"><span class="ai-status-dot"></span> Sẵn sàng phản hồi (0.5s)</div>
          </div>
        </div>
        <button class="ai-close-btn" id="ai-close-btn">&times;</button>
      </div>

      <div class="ai-handoff-banner" id="ai-handoff-banner">
        <span>⚡</span> <span>Đã kết nối nhân viên tư vấn trực tiếp</span>
      </div>

      <div class="ai-feed" id="ai-feed">
        <div class="ai-msg bot">
          <div class="ai-msg-sender">Trợ lý AI</div>
          Xin chào! Em là trợ lý tư vấn sản phẩm. Bạn đang tìm mẫu nào, cần kiểm tra size, màu hay phí ship cứ nhắn em nhé!
        </div>
      </div>

      <div class="ai-typing" id="ai-typing">
        <div class="ai-dot"></div><div class="ai-dot"></div><div class="ai-dot"></div>
      </div>

      <form class="ai-input-wrap" id="ai-form">
        <input type="text" class="ai-input" id="ai-input" placeholder="Nhập câu hỏi (size, màu, giá, ship)..." autocomplete="off" />
        <button type="submit" class="ai-send-btn" id="ai-send-btn">
          <svg style="width:16px;height:16px;fill:currentColor" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </form>
    </div>
  `;
  document.body.appendChild(root);

  const dialog = document.getElementById("ai-dialog");
  const toggleBtn = document.getElementById("ai-toggle-btn");
  const closeBtn = document.getElementById("ai-close-btn");
  const form = document.getElementById("ai-form");
  const input = document.getElementById("ai-input");
  const feed = document.getElementById("ai-feed");
  const typing = document.getElementById("ai-typing");
  const handoffBanner = document.getElementById("ai-handoff-banner");

  // Toggle Dialog
  toggleBtn.addEventListener("click", () => {
    dialog.classList.toggle("open");
    if (dialog.classList.contains("open")) {
      input.focus();
      if (conversationId) fetchHistory();
    }
  });

  closeBtn.addEventListener("click", () => dialog.classList.remove("open"));

  // Append Message Helper
  function appendMessage(text, type, senderName) {
    const msg = document.createElement("div");
    msg.className = `ai-msg ${type}`;
    if (senderName && type !== "user") {
      const s = document.createElement("div");
      s.className = "ai-msg-sender";
      s.textContent = senderName;
      msg.appendChild(s);
    }
    const content = document.createElement("div");
    content.textContent = text;
    msg.appendChild(content);
    feed.appendChild(msg);
    feed.scrollTop = feed.scrollHeight;
  }

  // Load message history from server
  async function fetchHistory() {
    if (!conversationId) return;
    try {
      const res = await fetch(`${BASE_ORIGIN}/api/widget/history?conversation_id=${conversationId}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === "assigned_human") {
        isHandoffActive = true;
        handoffBanner.classList.add("active");
      }
      if (data.messages && data.messages.length > 0) {
        feed.innerHTML = "";
        data.messages.forEach(m => {
          const type = m.sender_type === "customer" ? "user" : (m.sender_type === "staff" ? "staff" : "bot");
          appendMessage(m.content, type, m.sender_name);
        });
      }
    } catch (e) {
      console.warn("AI Widget history fetch error:", e);
    }
  }

  // Form Submit Handler
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    appendMessage(text, "user");
    input.value = "";
    typing.classList.add("active");
    feed.scrollTop = feed.scrollHeight;

    try {
      const res = await fetch(`${BASE_ORIGIN}/api/widget/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: "ws-01",
          conversation_id: conversationId,
          customer_text: text
        })
      });

      const data = await res.json();
      typing.classList.remove("active");

      if (data.conversation_id) {
        conversationId = data.conversation_id;
        localStorage.setItem(STORAGE_KEY, conversationId);
      }

      if (data.human_handoff_triggered) {
        isHandoffActive = true;
        handoffBanner.classList.add("active");
      }

      if (data.bot_replied && data.response) {
        appendMessage(data.response, "bot", "Trợ lý AI");
      }
    } catch (err) {
      typing.classList.remove("active");
      appendMessage("Có lỗi kết nối tạm thời. Vui lòng thử lại sau giây lát ạ!", "bot", "Hệ thống");
      console.error("AI Widget send error:", err);
    }
  });

  // Polling for live staff messages every 4 seconds when chat is open
  setInterval(() => {
    if (dialog.classList.contains("open") && conversationId) {
      fetchHistory();
    }
  }, 4000);

})();
