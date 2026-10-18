/**
 * AI Inbox & Sales Management - Admin Dashboard Application Logic
 */

let activeConvId = null;
let currentConversations = [];

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

  const targetBtn = Array.from(document.querySelectorAll(".tab-btn")).find(b => b.getAttribute("onclick") && b.getAttribute("onclick").includes(tabId));
  if (targetBtn) targetBtn.classList.add("active");

  const targetContent = document.getElementById(`tab-${tabId}`);
  if (targetContent) targetContent.classList.add("active");

  if (tabId === "kanban") loadKanban();
  if (tabId === "products") loadProducts();
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
    renderInboxList(currentConversations);
  } catch (e) {
    console.error("Failed to load inbox:", e);
  }
}

function renderInboxList(convs) {
  const container = document.getElementById("inbox-list");
  if (!convs || convs.length === 0) {
    container.innerHTML = '<div style="padding:20px; color:var(--text-muted); text-align:center;">Chưa có cuộc trò chuyện nào</div>';
    return;
  }

  container.innerHTML = "";
  convs.forEach(c => {
    const item = document.createElement("div");
    item.className = `inbox-item ${c.id === activeConvId ? 'active' : ''}`;
    item.onclick = () => selectConversation(c.id);

    const isHot = c.intent_label === "HOT";
    const badgeHtml = isHot ? '<span class="badge-hot">🔥 HOT</span>' : (c.intent_label === "WARM" ? '<span class="badge-warm">⚡ WARM</span>' : '');

    item.innerHTML = `
      <div class="inbox-item-header">
        <span class="inbox-cust-name">${escapeHtml(c.customer_name || 'Khách Hàng')}</span>
        ${badgeHtml}
      </div>
      <div class="inbox-last-msg">${escapeHtml(c.product_name || 'Đang trao đổi...')}</div>
      <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">
        Trạng thái: <strong>${c.status === 'assigned_human' ? 'Nhân viên chốt' : 'Bot hỗ trợ'}</strong>
      </div>
    `;
    container.appendChild(item);
  });
}

async function selectConversation(convId) {
  activeConvId = convId;
  renderInboxList(currentConversations); // Update active state

  try {
    const res = await fetch(`/api/dashboard/conversations/${convId}/messages`);
    if (!res.ok) return;
    const data = await res.json();
    const conv = data.conversation;
    const messages = data.messages || [];

    // 1. Update Header & Sidebar
    document.getElementById("thread-cust-name").textContent = conv ? conv.customer_name : "Khách Hàng";
    document.getElementById("thread-cust-meta").textContent = `Kênh: ${conv ? conv.channel : 'Web'} • Trạng thái: ${conv ? (conv.status === 'assigned_human' ? 'Nhân viên tiếp quản' : 'Bot đang xử lý') : ''}`;

    document.getElementById("detail-name").textContent = conv ? (conv.customer_name || '-') : '-';
    document.getElementById("detail-phone").textContent = conv ? (conv.customer_phone || 'Chưa cung cấp') : '-';
    document.getElementById("detail-product").textContent = conv ? (conv.product_name ? `${conv.product_name} (${(conv.product_price || 0).toLocaleString()}đ)` : 'Chưa xác định') : '-';
    document.getElementById("detail-score").textContent = conv ? `${conv.lead_score || 0} / 100 (${conv.intent_label || 'COLD'})` : '-';
    document.getElementById("detail-stage").textContent = conv ? (conv.lead_status || 'new').toUpperCase() : '-';
    document.getElementById("detail-conv-status").textContent = conv ? (conv.status === 'assigned_human' ? '👨‍💼 Nhân viên đang chat' : '🤖 Bot đang tự trả lời') : '-';

    // 2. Render Messages
    const body = document.getElementById("thread-body");
    body.innerHTML = "";
    messages.forEach(m => {
      const msgEl = document.createElement("div");
      msgEl.className = `thread-msg ${m.sender_type}`;
      msgEl.innerHTML = `
        <div style="font-size:11px; font-weight:600; margin-bottom:2px; color:var(--text-muted);">
          ${escapeHtml(m.sender_name || (m.sender_type === 'bot' ? 'Trợ lý AI' : (m.sender_type === 'staff' ? 'Nhân viên Sale' : 'Khách')))}
        </div>
        <div>${escapeHtml(m.content)}</div>
      `;
      body.appendChild(msgEl);
    });
    body.scrollTop = body.scrollHeight;
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
      alert("⚡ Bạn đã tiếp quản cuộc trò chuyện! Bot đã tạm dừng để bạn trực tiếp chốt đơn.");
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
          <span style="background:#e2e8f0; padding:2px 6px; border-radius:10px; font-size:11px;">${cards.length}</span>
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
        cardEl.innerHTML = `
          <div class="lead-card-header">
            <span class="lead-name">${escapeHtml(c.customer_name || 'Khách')}</span>
            ${isHot ? '<span class="badge-hot">🔥 HOT</span>' : ''}
          </div>
          <div class="lead-prod">${escapeHtml(c.product_name || 'Quan tâm sản phẩm')}</div>
          <div class="lead-meta">
            <span>SĐT: ${escapeHtml(c.customer_phone || '-')}</span>
            <strong>${(c.estimated_value_vnd || 0).toLocaleString()}đ</strong>
          </div>
          <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
            <select style="font-size:11px; padding:2px 4px; border-radius:4px;" onchange="moveLeadStage('${c.id}', this.value)">
              <option value="new" ${c.status === 'new' ? 'selected' : ''}>Mới</option>
              <option value="ai_qualified" ${c.status === 'ai_qualified' ? 'selected' : ''}>AI Qualified</option>
              <option value="assigned" ${c.status === 'assigned' ? 'selected' : ''}>Giao Sale</option>
              <option value="contacted" ${c.status === 'contacted' ? 'selected' : ''}>Đang gọi</option>
              <option value="negotiating" ${c.status === 'negotiating' ? 'selected' : ''}>Thương lượng</option>
              <option value="won" ${c.status === 'won' ? 'selected' : ''}>Chốt Won 🏆</option>
              <option value="lost" ${c.status === 'lost' ? 'selected' : ''}>Thất bại</option>
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
      <table style="width:100%; border-collapse:collapse; font-size:13.5px;">
        <thead>
          <tr style="text-align:left; border-bottom:2px solid var(--border);">
            <th style="padding:8px;">SKU</th>
            <th style="padding:8px;">Tên Sản Phẩm</th>
            <th style="padding:8px;">Giá Bán</th>
            <th style="padding:8px;">Tồn Kho</th>
            <th style="padding:8px;">Size Có Sẵn</th>
            <th style="padding:8px;">Màu Sắc</th>
            <th style="padding:8px;">Chính Sách Giao Hàng</th>
            <th style="padding:8px; text-align:center;">Thao Tác</th>
          </tr>
        </thead>
        <tbody>
    `;

    products.forEach(p => {
      html += `
        <tr style="border-bottom:1px solid var(--border);">
          <td style="padding:8px; font-weight:600;">${escapeHtml(p.sku)}</td>
          <td style="padding:8px; color:var(--primary-dark); font-weight:600;">${escapeHtml(p.name)}</td>
          <td style="padding:8px;">${(p.price_vnd || 0).toLocaleString()}đ</td>
          <td style="padding:8px; font-weight:600;">${p.stock_quantity} cái</td>
          <td style="padding:8px;">${escapeHtml((p.sizes || []).join(', '))}</td>
          <td style="padding:8px;">${escapeHtml((p.colors || []).join(', '))}</td>
          <td style="padding:8px; font-size:12px; color:var(--text-muted);">${escapeHtml(p.shipping_policy || '-')}</td>
          <td style="padding:8px; text-align:center;">
            <button onclick="deleteProduct('${p.id}')" style="background:#fee2e2; color:#ef4444; border:none; padding:4px 8px; border-radius:4px; font-size:11px; cursor:pointer;">Xóa</button>
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

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
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
