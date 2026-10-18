(function() {
  const SCRIPT_URL = document.currentScript ? document.currentScript.src : "http://127.0.0.1:8080/widget/chat_widget.js";
  const BASE_ORIGIN = new URL(SCRIPT_URL).origin;

  // 1. Inject Stylesheet (Guarded against duplicates)
  if (!document.getElementById("ai-widget-stylesheet")) {
    const link = document.createElement("link");
    link.id = "ai-widget-stylesheet";
    link.rel = "stylesheet";
    link.href = `${BASE_ORIGIN}/widget/chat_widget.css`;
    document.head.appendChild(link);
  }

  // 2. Storage & State Keys
  const STORAGE_KEY = "ai_inbox_conv_id";
  let conversationId = localStorage.getItem(STORAGE_KEY) || null;
  let isHandoffActive = false;
  let lastActiveElement = null;

  // 3. Inject Widget DOM Tree
  const root = document.createElement("div");
  root.id = "ai-chat-root";
  root.innerHTML = `
    <button class="ai-launcher-btn" id="ai-toggle-btn" aria-label="Mở khung chat trợ lý bán hàng" title="Trợ lý bán hàng AI">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0-2-.9-2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
    </button>

    <div class="ai-chat-dialog" id="ai-dialog" role="dialog" aria-modal="true" aria-label="Cửa sổ tư vấn bán hàng AI">
      <div class="ai-header">
        <div class="ai-header-info">
          <div class="ai-avatar" aria-hidden="true">🤖</div>
          <div>
            <div class="ai-title">Trợ Lý Tư Vấn Bán Hàng</div>
            <div class="ai-status"><span class="ai-status-dot"></span> Sẵn sàng phản hồi (0.5s)</div>
          </div>
        </div>
        <button class="ai-close-btn" id="ai-close-btn" aria-label="Đóng cửa sổ chat">&times;</button>
      </div>

      <div class="ai-handoff-banner" id="ai-handoff-banner" role="status">
        <span aria-hidden="true">👨‍💼</span> <span>Nhân viên tư vấn đang trực tiếp hỗ trợ bạn</span>
      </div>

      <div class="ai-feed" id="ai-feed" aria-live="polite">
        <div class="ai-msg bot">
          <div class="ai-msg-sender">🤖 Trợ lý AI</div>
          <div>Xin chào! Em là trợ lý tư vấn sản phẩm. Bạn đang tìm mẫu nào, cần kiểm tra size, màu hay phí ship cứ nhắn em nhé!</div>
          <div class="ai-msg-time">Vừa xong</div>
        </div>
      </div>

      <div class="ai-typing" id="ai-typing" aria-label="AI đang phản hồi...">
        <div class="ai-dot"></div><div class="ai-dot"></div><div class="ai-dot"></div>
      </div>

      <!-- Quick Action Suggestions Row -->
      <div class="ai-quick-actions" id="ai-quick-actions">
        <button type="button" class="ai-quick-chip" onclick="window.prepareAiPrompt('Dạ shop báo giá chi tiết sản phẩm này giúp mình nhé!')">💰 Báo giá chi tiết</button>
        <button type="button" class="ai-quick-chip" onclick="window.prepareAiPrompt('Mình cần tư vấn chọn size chuẩn ạ!')">📏 Tư vấn chọn size</button>
        <button type="button" class="ai-quick-chip" onclick="window.prepareAiPrompt('Phí ship và thời gian giao hàng thế nào ạ?')">🚚 Phí ship</button>
        <button type="button" class="ai-quick-chip" onclick="window.prepareAiPrompt('Mình muốn gặp trực tiếp nhân viên tư vấn ạ!')">👨‍💼 Gặp nhân viên</button>
      </div>

      <form class="ai-input-wrap" id="ai-form">
        <input type="text" class="ai-input" id="ai-input" placeholder="Nhập câu hỏi (size, màu, giá, ship)..." autocomplete="off" aria-label="Tin nhắn gửi shop" />
        <button type="submit" class="ai-send-btn" id="ai-send-btn" aria-label="Gửi tin nhắn">
          <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24" aria-hidden="true"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
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

  function openDialog() {
    lastActiveElement = document.activeElement;
    dialog.classList.add("open");
    input.focus();
    if (conversationId) fetchHistory();
  }

  function closeDialog() {
    dialog.classList.remove("open");
    if (lastActiveElement && typeof lastActiveElement.focus === "function") {
      lastActiveElement.focus();
    }
  }

  // Toggle Dialog
  toggleBtn.addEventListener("click", () => {
    if (dialog.classList.contains("open")) {
      closeDialog();
    } else {
      openDialog();
    }
  });

  closeBtn.addEventListener("click", closeDialog);

  // Escape key closes dialog
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && dialog.classList.contains("open")) {
      closeDialog();
    }
  });

  // Public API to prepare prompt without sending
  window.prepareAiPrompt = function(text) {
    if (!dialog.classList.contains("open")) {
      openDialog();
    }
    input.value = text;
    input.focus();
  };

  // Public API to open chat with optional pre-filled grounded question
  window.openAiChat = function(initialText) {
    openDialog();
    if (initialText) {
      input.value = initialText;
    }
    input.focus();
  };

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

    const timeEl = document.createElement("div");
    timeEl.className = "ai-msg-time";
    timeEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    msg.appendChild(timeEl);

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
          const senderLabel = m.sender_type === "customer" ? "Khách" : (m.sender_type === "staff" ? "👨‍💼 " + (m.sender_name || "Nhân viên Sale") : "🤖 Trợ lý AI");
          appendMessage(m.content, type, senderLabel);
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

      if (data.human_handoff_triggered || data.status === "assigned_human") {
        isHandoffActive = true;
        handoffBanner.classList.add("active");
      }

      if (data.bot_replied && data.response) {
        appendMessage(data.response, "bot", "🤖 Trợ lý AI");
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
