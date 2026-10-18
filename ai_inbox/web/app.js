/**
 * AI Inbox & Sales Management - Admin Dashboard Application Logic
 * Omnichannel Unified Inbox, Kanban Pipeline, Product Catalog & Staff Metrics
 */

let activeConvId = null;
let currentActiveLeadId = null;
let currentConversations = [];
let activeChannelFilter = "all";
let searchQuery = "";

const CHANNEL_LABELS = {
  "web_widget": "Web",
  "facebook_page": "Messenger",
  "zalo_oa": "Zalo OA",
  "tiktok_shop": "TikTok",
  "shopee": "Shopee",
  "lazada": "Lazada"
};

function getChannelLabel(channel) {
  return CHANNEL_LABELS[channel] || (channel ? channel.toUpperCase() : "WEB");
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

  const targetBtn = Array.from(document.querySelectorAll(".tab-btn")).find(b => b.getAttribute("onclick") && b.getAttribute("onclick").includes(tabId));
  if (targetBtn) targetBtn.classList.add("active");

  const targetContent = document.getElementById(`tab-${tabId}`);
  if (targetContent) targetContent.classList.add("active");

  if (tabId === "kanban") loadKanban();
  if (tabId === "products") loadProducts();
  if (tabId === "staff") loadStaffMetrics();
}

async function loadMetrics() {
  try {
    const res = await fetch("/api/dashboard/metrics");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("metric-convs").textContent = data.total_conversations || 0;
    document.getElementById("metric-hot").textContent = data.hot_leads || 0;
    document.getElementById("metric-won").textContent = data.won_deals || 0;
    document.getElementById("metric-won-rev").textContent = `${(data.won_revenue_vnd || 0).toLocaleString()}đ doanh thu`;
    document.getElementById("metric-cvr").textContent = `${data.conversion_rate_pct || 0}%`;
  } catch (e) {
    console.error("Failed to load metrics:", e);
  }
}

async function loadInbox() {
  try {
    const res = await fetch("/api/dashboard/inbox");
    if (!res.ok) return;
    const data = await res.json();
    currentConversations = data.conversations || [];
    filterAndRenderConversations();
  } catch (e) {
    console.error("Failed to load inbox:", e);
  }
}

function filterByChannel(channel) {
  activeChannelFilter = channel;
  document.querySelectorAll(".channel-pill").forEach(pill => {
    const fnAttr = pill.getAttribute("onclick") || "";
    if (fnAttr.includes(`'${channel}'`)) {
      pill.classList.add("active");
    } else {
      pill.classList.remove("active");
    }
  });
  filterAndRenderConversations();
}

function handleSearch(query) {
  searchQuery = (query || "").toLowerCase().trim();
  filterAndRenderConversations();
}

function filterAndRenderConversations() {
  let list = currentConversations;
  if (activeChannelFilter !== "all") {
    list = list.filter(c => c.channel === activeChannelFilter);
  }
  if (searchQuery) {
    list = list.filter(c => {
      const name = (c.customer_name || "").toLowerCase();
      const phone = (c.customer_phone || "").toLowerCase();
      const prod = (c.product_name || "").toLowerCase();
      return name.includes(searchQuery) || phone.includes(searchQuery) || prod.includes(searchQuery);
    });
  }
  renderInboxList(list);
}

function renderInboxList(convs) {
  const container = document.getElementById("inbox-list");
  if (!container) return;
  if (!convs || convs.length === 0) {
    container.innerHTML = '<div style="padding:28px 16px; color:var(--text-muted); text-align:center; font-size:13px;">Không tìm thấy cuộc trò chuyện phù hợp</div>';
    return;
  }

  container.innerHTML = "";
  convs.forEach(c => {
    const item = document.createElement("div");
    item.className = `inbox-item ${c.id === activeConvId ? 'active' : ''}`;
    item.onclick = () => selectConversation(c.id);

    const isHot = c.intent_label === "HOT";
    const isWarm = c.intent_label === "WARM";
    const badgeHtml = isHot ? '<span class="badge-hot">🔥 HOT</span>' : (isWarm ? '<span class="badge-warm">⚡ WARM</span>' : '');

    const channelTag = `<span class="badge-channel channel-${c.channel || 'web_widget'}">${getChannelLabel(c.channel)}</span>`;
    const isStaff = c.status === "assigned_human";

    item.innerHTML = `
      <div class="inbox-item-header">
        <span class="inbox-cust-name">${escapeHtml(c.customer_name || 'Khách Hàng')} ${channelTag}</span>
        ${badgeHtml}
      </div>
      <div class="inbox-last-msg">${escapeHtml(c.product_name ? 'Quan tâm: ' + c.product_name : 'Đang trao đổi...')}${c.customer_phone ? ' • ' + escapeHtml(c.customer_phone) : ''}</div>
      <div style="font-size:13px; color:var(--text-muted); margin-top:6px; display:flex; justify-content:space-between; align-items:center;">
        <span>${isStaff ? '<span style="color:var(--primary); font-weight:700;">👨‍💼 Nhân viên tiếp quản</span>' : '🤖 AI Trợ lý tự động'}</span>
        <span style="font-size:12.5px; opacity:0.9; font-weight:500;">${formatTimestamp(c.last_message_at)}</span>
      </div>
    `;
    container.appendChild(item);
  });
}

function formatTimestamp(ts) {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return `${d.getDate()}/${d.getMonth() + 1}`;
  } catch (e) {
    return "";
  }
}

async function selectConversation(convId) {
  activeConvId = convId;
  filterAndRenderConversations(); // Update active highlight

  try {
    const res = await fetch(`/api/dashboard/conversations/${convId}/messages`);
    if (!res.ok) return;
    const data = await res.json();
    const conv = data.conversation;
    const messages = data.messages || [];

    currentActiveLeadId = conv ? conv.lead_id : null;

    // 1. Update Header
    const channelName = getChannelLabel(conv ? conv.channel : "web_widget");
    document.getElementById("thread-cust-name").textContent = conv ? (conv.customer_name || "Khách Hàng") : "Khách Hàng";
    const metaEl = document.getElementById("thread-cust-meta-text") || document.getElementById("thread-cust-meta");
    if (metaEl) {
      metaEl.textContent = `Kênh: ${channelName} • Trạng thái: ${conv ? (conv.status === 'assigned_human' ? 'Nhân viên tiếp quản' : 'Bot AI đang xử lý') : ''}`;
    }

    const takeoverBtn = document.getElementById("btn-takeover");
    if (takeoverBtn) {
      if (conv && conv.status === "assigned_human") {
        takeoverBtn.className = "btn-takeover active-staff";
        takeoverBtn.textContent = "✅ Đang Tiếp Quản";
      } else {
        takeoverBtn.className = "btn-takeover";
        takeoverBtn.textContent = "⚡ Can Thiệp / Chốt Đơn";
      }
    }

    // Copilot Smart Intent Badge
    const copilotBadge = document.getElementById("copilot-intent-badge");
    if (copilotBadge) {
      if (conv && conv.intent_label === "HOT") {
        copilotBadge.textContent = "🔥 Khách Cực Nóng (Có SĐT / Sẵn Sàng Chốt Đơn)";
        copilotBadge.style.color = "var(--hot-red)";
      } else if (conv && conv.intent_label === "WARM") {
        copilotBadge.textContent = "⚡ Khách Cân Nhắc (Cần Tư Vấn Size & Màu)";
        copilotBadge.style.color = "var(--warm-amber)";
      } else {
        copilotBadge.textContent = "💬 Khách Hỏi Thông Tin Ban Đầu";
        copilotBadge.style.color = "var(--text-muted)";
      }
    }

    // 2. Update Customer 360 Sidebar & Order Draft Card
    const channelBadge = document.getElementById("detail-channel-badge");
    if (channelBadge && conv) {
      channelBadge.textContent = channelName;
      channelBadge.className = `badge-channel channel-${conv.channel || 'web_widget'}`;
    }

    document.getElementById("detail-name").textContent = conv ? (conv.customer_name || '-') : '-';
    document.getElementById("detail-phone").textContent = conv ? (conv.customer_phone || 'Chưa cung cấp') : '-';
    document.getElementById("detail-product").textContent = conv ? (conv.product_name ? `${conv.product_name} (${(conv.product_price || 0).toLocaleString()}đ)` : 'Chưa xác định') : '-';
    
    // Order Draft Summary calculation
    const prodPrice = conv ? (conv.product_price || 0) : 0;
    const shipFee = prodPrice > 0 ? 25000 : 0;
    const totalAmount = prodPrice + shipFee;
    const draftNameEl = document.getElementById("draft-prod-name");
    const draftPriceEl = document.getElementById("draft-prod-price");
    const draftShipEl = document.getElementById("draft-ship-fee");
    const draftTotalEl = document.getElementById("draft-total-amount");
    if (draftNameEl) draftNameEl.textContent = conv && conv.product_name ? conv.product_name : "Chưa chọn mẫu";
    if (draftPriceEl) draftPriceEl.textContent = `${prodPrice.toLocaleString()}đ`;
    if (draftShipEl) draftShipEl.textContent = `${shipFee.toLocaleString()}đ`;
    if (draftTotalEl) draftTotalEl.textContent = `${totalAmount.toLocaleString()}đ`;

    const scoreVal = conv ? (conv.lead_score || 0) : 0;
    const intentLabel = conv ? (conv.intent_label || 'COLD') : 'COLD';
    document.getElementById("detail-score").textContent = `${scoreVal} / 100 (${intentLabel})`;

    // Score Gauge Fill
    const gaugeFill = document.getElementById("score-gauge");
    if (gaugeFill) {
      gaugeFill.style.width = `${Math.min(scoreVal, 100)}%`;
      if (scoreVal >= 70) {
        gaugeFill.style.background = "var(--hot-red)";
      } else if (scoreVal >= 40) {
        gaugeFill.style.background = "var(--warm-amber)";
      } else {
        gaugeFill.style.background = "var(--cold-blue)";
      }
    }

    // Stage Select
    const stageSelect = document.getElementById("detail-stage-select");
    if (stageSelect && conv) {
      stageSelect.value = conv.lead_status || "new";
    }

    // Dynamic Context-Aware Copilot Action Chips
    const copilotChipsWrap = document.querySelector(".copilot-chips-wrap");
    if (copilotChipsWrap) {
      const lastCust = [...messages].reverse().find(m => m.sender_type === "customer");
      const lastText = (lastCust ? lastCust.content : "").toLowerCase();
      let chipsHtml = "";

      if (lastText.includes("size") || lastText.includes("nặng") || lastText.includes("cao") || lastText.includes("kg") || lastText.includes("vừa")) {
        chipsHtml += `
          <button class="quick-chip" onclick="insertQuickReply('Dạ với chiều cao và cân nặng của bạn, bên em tư vấn bạn mặc size L là vừa vặn, chuẩn form và tôn dáng nhất ạ!')">
            📏 Gợi ý size L chuẩn form
          </button>
          <button class="quick-chip" onclick="insertQuickReply('Dạ mẫu này form chuẩn ôm vừa, bạn cho mình xin thêm số đo chiều cao và cân nặng để em chọn size chính xác nhé!')">
            📏 Hỏi chiều cao / cân nặng
          </button>
        `;
      }

      if (lastText.includes("ship") || lastText.includes("địa chỉ") || lastText.includes("sđt") || lastText.includes("đà nẵng") || lastText.includes("hà nội") || lastText.includes("hcm") || lastText.includes("giao")) {
        chipsHtml += `
          <button class="quick-chip" onclick="insertQuickReply('Dạ em đã ghi nhận địa chỉ nhận hàng. Đơn hàng trị giá ${(totalAmount || 275000).toLocaleString()}đ (gồm 25k ship) sẽ được chuyển phát nhanh và giao trong 2-3 ngày ạ!')">
            📦 Xác nhận lên đơn & giao hàng
          </button>
          <button class="quick-chip" onclick="insertQuickReply('Dạ bên em áp dụng chính sách FREESHIP toàn quốc cho mọi đơn hàng từ 2 sản phẩm trở lên. Bạn có muốn chọn thêm 1 mẫu để được miễn phí ship không ạ?')">
            🚚 Báo ưu đãi Freeship 2 chiếc
          </button>
        `;
      }

      // High-conversion standard chips
      chipsHtml += `
        <button class="quick-chip" onclick="insertQuickReply('Dạ mẫu này bên em đang có sẵn đủ size M, L, XL ạ. Bạn cho mình xin chiều cao và cân nặng để em chọn size chuẩn form và tôn dáng nhất nhé!')">
          📏 Tư vấn chọn size
        </button>
        <button class="quick-chip" onclick="insertQuickReply('Dạ mình cho em xin Số Điện Thoại và Địa Chỉ nhận hàng để em lên đơn giữ hàng và gửi mã vận đơn cho mình ngay nhé!')">
          📦 Xin SĐT & Địa chỉ ship
        </button>
        <button class="quick-chip" onclick="insertQuickReply('Dạ em đã kiểm tra kho và giữ đúng mẫu này cho mình rồi ạ. Anh/chị yên tâm nhé!')">
          ✅ Xác nhận giữ hàng tại kho
        </button>
        <button class="quick-chip" onclick="insertQuickReply('Dạ bên em áp dụng chính sách đồng giá ship 25k toàn quốc và MIỄN PHÍ VẬN CHUYỂN cho mọi đơn hàng từ 2 sản phẩm trở lên ạ!')">
          🚚 Báo phí ship & Freeship
        </button>
      `;
      copilotChipsWrap.innerHTML = chipsHtml;
    }

    // 3. Render Messages in Thread Body
    const body = document.getElementById("thread-body");
    body.innerHTML = "";
    if (messages.length === 0) {
      body.innerHTML = '<div style="text-align:center; color:var(--text-muted); margin-top:40px;">Chưa có tin nhắn trong hội thoại này</div>';
    } else {
      messages.forEach(m => {
        const msgEl = document.createElement("div");
        msgEl.className = `msg-row ${m.sender_type}`;

        const senderTitle = m.sender_name || (
          m.sender_type === 'bot' ? '🤖 Trợ lý AI' :
          (m.sender_type === 'staff' ? '👨‍💼 Nhân viên Sale' : '👤 Khách hàng')
        );

        msgEl.innerHTML = `
          <div class="msg-bubble">
            <div style="font-size:13px; font-weight:700; margin-bottom:4px; opacity:0.9;">${escapeHtml(senderTitle)}</div>
            <div>${escapeHtml(m.content)}</div>
          </div>
          <div class="msg-meta">
            <span style="font-size:12.5px;">${formatTimestamp(m.timestamp)}</span>
            ${m.intent ? `<span style="font-size:12px; background:#e2e8f0; padding:2px 6px; border-radius:4px; font-weight:600;">${escapeHtml(m.intent)}</span>` : ''}
          </div>
        `;
        body.appendChild(msgEl);
      });
      body.scrollTop = body.scrollHeight;
    }
  } catch (e) {
    console.error("Failed to load conversation details:", e);
  }
}

async function takeoverChat() {
  if (!activeConvId) return alert("Vui lòng chọn một cuộc trò chuyện trước.");
  try {
    const res = await fetch(`/api/dashboard/conversations/${activeConvId}/takeover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ staff_id: "staff-01" })
    });
    if (res.ok) {
      selectConversation(activeConvId);
      loadInbox();
    }
  } catch (e) {
    console.error("Takeover error:", e);
  }
}

async function sendStaffReply(e) {
  e.preventDefault();
  if (!activeConvId) return alert("Vui lòng chọn một cuộc trò chuyện trước.");
  const input = document.getElementById("reply-input");
  const text = input.value.trim();
  if (!text) return;

  try {
    const res = await fetch(`/api/dashboard/conversations/${activeConvId}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ staff_name: "Tuấn Sale", message: text })
    });
    if (res.ok) {
      input.value = "";
      selectConversation(activeConvId);
    }
  } catch (e) {
    console.error("Send reply error:", e);
  }
}

function insertQuickReply(text) {
  const input = document.getElementById("reply-input");
  if (input) {
    input.value = text;
    input.focus();
  }
}

function copyPhone() {
  const phoneEl = document.getElementById("detail-phone");
  const phone = phoneEl ? phoneEl.textContent.trim() : "";
  if (!phone || phone === "-" || phone === "Chưa cung cấp") {
    alert("Khách hàng này chưa để lại số điện thoại.");
    return;
  }
  navigator.clipboard.writeText(phone).then(() => {
    alert(`Đã sao chép SĐT: ${phone}`);
  }).catch(() => {
    prompt("Sao chép số điện thoại:", phone);
  });
}

async function updateLeadStageFromSidebar(newStage) {
  if (!currentActiveLeadId) {
    alert("Cuộc trò chuyện này chưa gắn với Lead nào.");
    return;
  }
  try {
    const res = await fetch(`/api/dashboard/leads/${currentActiveLeadId}/stage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage: newStage })
    });
    if (res.ok) {
      loadMetrics();
      loadInbox();
    }
  } catch (e) {
    console.error("Update lead stage error:", e);
  }
}

async function markLeadWonFast() {
  if (!currentActiveLeadId) {
    alert("Chưa có hồ sơ lead để chốt đơn.");
    return;
  }
  try {
    const res = await fetch(`/api/dashboard/leads/${currentActiveLeadId}/stage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage: "won" })
    });
    if (res.ok) {
      const stageSelect = document.getElementById("detail-stage-select");
      if (stageSelect) stageSelect.value = "won";
      alert("🎉 Chúc mừng! Đã chốt đơn thành công (Won) và ghi nhận doanh thu!");
      loadMetrics();
      loadInbox();
      if (activeConvId) selectConversation(activeConvId);
    }
  } catch (e) {
    console.error("Mark won error:", e);
  }
}

async function loadKanban() {
  const container = document.getElementById("kanban-board");
  try {
    const res = await fetch("/api/dashboard/leads/kanban");
    if (!res.ok) return;
    const data = await res.json();
    const stages = data.stages || {};

    const stageTitles = {
      "new": "1. Mới Nhận (New)",
      "ai_qualified": "2. AI Đã Lọc (Qualified)",
      "assigned": "3. Đã Bàn Giao Sale",
      "contacted": "4. Đang Liên Hệ",
      "negotiating": "5. Đang Thương Lượng",
      "won": "6. Thành Công (Won)",
      "lost": "7. Thất Bại (Lost)"
    };

    container.innerHTML = "";
    Object.keys(stageTitles).forEach(st => {
      const col = document.createElement("div");
      col.className = "kanban-col";
      const cards = stages[st] || [];

      col.innerHTML = `
        <div class="kanban-col-header">
          <span>${stageTitles[st]}</span>
          <span style="background:#e2e8f0; padding:2px 8px; border-radius:10px; font-size:12.5px; font-weight:700;">${cards.length}</span>
        </div>
        <div class="kanban-cards" id="col-${st}"></div>
      `;
      container.appendChild(col);

      const cardsContainer = col.querySelector(`#col-${st}`);
      cards.forEach(c => {
        const cardEl = document.createElement("div");
        cardEl.className = "lead-card";
        cardEl.draggable = true;
        cardEl.dataset.leadId = c.id;
        cardEl.addEventListener("dragstart", event => {
          event.dataTransfer.setData("text/plain", c.id);
          event.dataTransfer.effectAllowed = "move";
        });
        const isHot = c.intent_label === "HOT";
        const channelTag = `<span class="badge-channel channel-${c.channel || 'web_widget'}">${getChannelLabel(c.channel)}</span>`;

        cardEl.innerHTML = `
          <div class="lead-card-header">
            <span class="lead-name">${escapeHtml(c.customer_name || 'Khách')} ${channelTag}</span>
            ${isHot ? '<span class="badge-hot">🔥 HOT</span>' : ''}
          </div>
          <div class="lead-prod">${escapeHtml(c.product_name || 'Quan tâm sản phẩm')}</div>
          <div class="lead-meta">
            <span>SĐT: ${escapeHtml(c.customer_phone || '-')}</span>
            <strong>${(c.estimated_value_vnd || 0).toLocaleString()}đ</strong>
          </div>
          <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
            <select style="font-size:13px; font-weight:600; padding:4px 8px; border-radius:6px; border:1px solid var(--border-light); background:#f8fafc; cursor:pointer;" onchange="moveLeadStage('${c.id}', this.value)">
              <option value="new" ${c.status === 'new' ? 'selected' : ''}>1. Mới Nhận</option>
              <option value="ai_qualified" ${c.status === 'ai_qualified' ? 'selected' : ''}>2. AI Qualified</option>
              <option value="assigned" ${c.status === 'assigned' ? 'selected' : ''}>3. Giao Sale</option>
              <option value="contacted" ${c.status === 'contacted' ? 'selected' : ''}>4. Đang gọi</option>
              <option value="negotiating" ${c.status === 'negotiating' ? 'selected' : ''}>5. Thương lượng</option>
              <option value="won" ${c.status === 'won' ? 'selected' : ''}>6. Chốt Won 🏆</option>
              <option value="lost" ${c.status === 'lost' ? 'selected' : ''}>7. Thất bại</option>
            </select>
          </div>
        `;
        cardsContainer.appendChild(cardEl);
      });

      cardsContainer.addEventListener("dragover", event => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        cardsContainer.classList.add("drag-over");
      });
      cardsContainer.addEventListener("dragleave", () => cardsContainer.classList.remove("drag-over"));
      cardsContainer.addEventListener("drop", event => {
        event.preventDefault();
        cardsContainer.classList.remove("drag-over");
        const leadId = event.dataTransfer.getData("text/plain");
        if (leadId) moveLeadStage(leadId, st);
      });
    });
  } catch (e) {
    console.error("Failed to load Kanban:", e);
  }
}

async function moveLeadStage(leadId, newStage) {
  try {
    const res = await fetch(`/api/dashboard/leads/${leadId}/stage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage: newStage })
    });
    if (res.ok) {
      loadKanban();
      loadMetrics();
    }
  } catch (e) {
    console.error("Move lead stage error:", e);
  }
}

async function loadProducts() {
  const container = document.getElementById("product-list-container");
  try {
    const res = await fetch("/api/dashboard/products");
    if (!res.ok) return;
    const data = await res.json();
    const products = data.products || [];

    if (products.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);">Chưa có sản phẩm nào trong kho dữ liệu.</p>';
      return;
    }

    let html = `
      <table style="width:100%; border-collapse:collapse; font-size:14px;">
        <thead>
          <tr style="text-align:left; border-bottom:2px solid var(--border-light); background:#f8fafc;">
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Mã SKU</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Tên Sản Phẩm</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Giá Bán</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Tồn Kho</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Size Có Sẵn</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Màu Sắc</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Chính Sách Giao Hàng</th>
            <th style="padding:14px 16px; font-size:13px; font-weight:700; color:var(--text-muted); text-transform:uppercase; text-align:center;">Thao Tác</th>
          </tr>
        </thead>
        <tbody>
    `;

    products.forEach(p => {
      html += `
        <tr style="border-bottom:1px solid var(--border-light); transition:background 0.15s;">
          <td style="padding:14px 16px; font-weight:700; font-family:var(--font-mono); font-size:13.5px; color:#0f172a;">${escapeHtml(p.sku)}</td>
          <td style="padding:14px 16px; color:var(--primary); font-weight:700; font-size:14.5px;">${escapeHtml(p.name)}</td>
          <td style="padding:14px 16px; font-weight:700; font-size:14px; color:#0f172a;">${(p.price_vnd || 0).toLocaleString()}đ</td>
          <td style="padding:14px 16px; font-weight:700; font-size:14px; color:${p.stock_quantity > 0 ? '#059669' : '#dc2626'};">${p.stock_quantity} cái</td>
          <td style="padding:14px 16px; font-size:13.5px;">${escapeHtml((p.sizes || []).join(', '))}</td>
          <td style="padding:14px 16px; font-size:13.5px;">${escapeHtml((p.colors || []).join(', '))}</td>
          <td style="padding:14px 16px; font-size:13px; color:var(--text-muted);">${escapeHtml(p.shipping_policy || '-')}</td>
          <td style="padding:14px 16px; text-align:center;">
            <button onclick="deleteProduct('${p.id}')" style="background:#fee2e2; color:#ef4444; border:none; padding:6px 14px; border-radius:6px; font-size:12.5px; font-weight:700; cursor:pointer;">Xóa</button>
          </td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (e) {
    console.error("Failed to load products:", e);
  }
}

function openProductModal() {
  document.getElementById("product-modal").style.display = "flex";
}

function closeProductModal() {
  document.getElementById("product-modal").style.display = "none";
}

async function submitAddProduct(e) {
  e.preventDefault();
  const sku = document.getElementById("prod-sku").value.trim();
  const name = document.getElementById("prod-name").value.trim();
  const price = parseInt(document.getElementById("prod-price").value) || 0;
  const stock = parseInt(document.getElementById("prod-stock").value) || 0;
  const sizes = document.getElementById("prod-sizes").value.split(",").map(s => s.trim()).filter(Boolean);
  const colors = document.getElementById("prod-colors").value.split(",").map(c => c.trim()).filter(Boolean);
  const shipping = document.getElementById("prod-shipping").value.trim();

  try {
    const res = await fetch("/api/dashboard/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: "ws-01",
        sku,
        name,
        price_vnd: price,
        stock_quantity: stock,
        sizes,
        colors,
        shipping_policy: shipping
      })
    });
    if (res.ok) {
      closeProductModal();
      loadProducts();
    } else {
      const err = await res.json();
      alert("Lỗi thêm sản phẩm: " + (err.error || "Không thể lưu"));
    }
  } catch (err) {
    console.error("Add product error:", err);
  }
}

async function deleteProduct(productId) {
  if (!confirm("Bạn có chắc chắn muốn xóa sản phẩm này khỏi danh mục không?")) return;
  try {
    const res = await fetch(`/api/dashboard/products/${productId}/delete`, {
      method: "POST"
    });
    if (res.ok) {
      loadProducts();
    }
  } catch (err) {
    console.error("Delete product error:", err);
  }
}

async function loadStaffMetrics() {
  const tbody = document.getElementById("staff-leaderboard-body");
  if (!tbody) return;
  try {
    const res = await fetch("/api/dashboard/staff/metrics");
    if (!res.ok) return;
    const data = await res.json();
    const leaderboard = data.leaderboard || [];
    if (leaderboard.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#94a3b8;">Chưa có nhân viên nào trong workspace.</td></tr>';
      return;
    }
    tbody.innerHTML = leaderboard.map((s, idx) => `
      <tr style="border-bottom:1px solid var(--border-light); transition:background 0.15s;">
        <td style="padding:16px 18px;">
          <div style="font-weight:700; font-size:15px; color:#0f172a;">${idx === 0 ? "🥇 " : (idx === 1 ? "🥈 " : (idx === 2 ? "🥉 " : ""))}${escapeHtml(s.name)}</div>
          <div style="font-size:13px; color:var(--text-muted); margin-top:2px;">${escapeHtml(s.email)}</div>
        </td>
        <td style="padding:16px 18px;"><span class="badge" style="background:#e0f2fe; color:#0369a1; font-weight:700; padding:4px 10px; border-radius:6px; font-size:12.5px;">${escapeHtml(s.role)}</span></td>
        <td style="padding:16px 18px; text-align:center; font-weight:700; font-size:14.5px;">${s.assigned_leads}</td>
        <td style="padding:16px 18px; text-align:center; color:#16a34a; font-weight:800; font-size:15px;">${s.won_deals}</td>
        <td style="padding:16px 18px; text-align:center; font-weight:700; font-size:14.5px;">${s.closing_rate_pct}%</td>
        <td style="padding:16px 18px; text-align:right; font-weight:800; font-size:15px; color:#0f172a;">${(s.won_revenue_vnd || 0).toLocaleString()}đ</td>
        <td style="padding:16px 18px; text-align:right; font-weight:800; font-size:15px; color:var(--primary);">${(s.estimated_commission_vnd || 0).toLocaleString()}đ</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Load staff metrics error:", err);
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#ef4444;">Lỗi khi tải bảng xếp hạng nhân viên.</td></tr>';
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  });
}

// Initial Boot
loadMetrics();
loadInbox();

// Auto-refresh inbox & metrics every 4s
setInterval(() => {
  loadMetrics();
  loadInbox();
  if (activeConvId) {
    selectConversation(activeConvId);
  }
}, 4000);
