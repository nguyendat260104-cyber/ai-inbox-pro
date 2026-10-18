/**
 * Affiliate Automation Command Center Dashboard Frontend
 */

let cachedData = null;

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

  const targetBtn = Array.from(document.querySelectorAll(".tab-btn")).find(b => b.getAttribute("onclick").includes(tabId));
  if (targetBtn) targetBtn.classList.add("active");

  const targetContent = document.getElementById(`tab-${tabId}`);
  if (targetContent) targetContent.classList.add("active");
}

async function fetchData() {
  const statusEl = document.getElementById("connection-status");
  const updatedEl = document.getElementById("last-updated");

  try {
    const res = await fetch("/api/data");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cachedData = data;

    statusEl.className = "status-indicator online";
    statusEl.textContent = "System Online";
    updatedEl.textContent = `Updated: ${new Date().toLocaleTimeString()}`;

    renderDashboard(data);
  } catch (err) {
    statusEl.className = "status-indicator offline";
    statusEl.textContent = "Offline / Connection Error";
    console.error("Failed to fetch dashboard data:", err);
  }
}

function renderDashboard(data) {
  // 1. Metric Counts
  document.getElementById("count-queued").textContent = data.counts.queued || 0;
  document.getElementById("count-running").textContent = data.counts.running || 0;
  document.getElementById("count-review").textContent = data.counts.review || 0;
  document.getElementById("count-done").textContent = data.counts.done || 0;
  document.getElementById("count-failed").textContent = data.counts.failed || 0;
  document.getElementById("count-offers").textContent = (data.top_products || []).length;

  document.getElementById("badge-queued").textContent = data.counts.queued || 0;
  document.getElementById("badge-running").textContent = data.counts.running || 0;
  document.getElementById("badge-review").textContent = data.counts.review || 0;
  document.getElementById("badge-done").textContent = data.counts.done || 0;
  document.getElementById("badge-failed").textContent = data.counts.failed || 0;

  // 2. Kanban Columns
  const statuses = ["queued", "running", "review", "done", "failed"];
  statuses.forEach(status => {
    const col = document.getElementById(`col-${status}-items`);
    col.innerHTML = "";
    const tasks = (data.tasks && data.tasks[status]) || [];

    if (tasks.length === 0) {
      col.innerHTML = `<div class="text-muted" style="text-align:center; padding:1.5rem 0.5rem; font-size:0.8rem;">No ${status} tasks</div>`;
      return;
    }

    tasks.forEach(task => {
      const card = document.createElement("div");
      card.className = "task-card";

      const prio = (task.priority || "medium").toLowerCase();
      const taskType = task.type || "task";
      const branch = task.suggested_branch || "";
      const created = task.created_at ? new Date(task.created_at).toLocaleTimeString() : "";

      card.innerHTML = `
        <div class="task-card-header">
          <span class="task-id">${escapeHtml(task.id || "ID")}</span>
          <span class="priority-tag ${prio}">${prio}</span>
        </div>
        <div class="task-goal">${escapeHtml(task.goal || "No goal specified")}</div>
        <div class="task-meta">
          <span>${escapeHtml(taskType)}</span>
          <span>${created}</span>
        </div>
      `;
      col.appendChild(card);
    });
  });

  // 3. Researched Offers Table
  const tbody = document.getElementById("offers-tbody");
  tbody.innerHTML = "";
  const products = data.top_products || [];

  if (products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted" style="padding: 2rem;">No evaluated products found in research/products/</td></tr>`;
  } else {
    products.forEach(p => {
      const tr = document.createElement("tr");

      const score = p.score !== undefined ? p.score : "N/A";
      const readiness = p.readiness_score !== undefined ? p.readiness_score : 0;
      const gate = p.readiness_gate || "BLOCKED_NEEDS_VERIFICATION";
      const rec = (p.recommendation || "REVIEW").toUpperCase();
      let badgeClass = "badge-retest";
      if (rec.includes("SCALE")) badgeClass = "badge scale";
      else if (rec.includes("HOLD") || rec.includes("RESEARCH")) badgeClass = "badge hold";
      else if (rec.includes("TEST")) badgeClass = "badge test";
      else if (rec.includes("KILL")) badgeClass = "badge kill";
      else if (rec.includes("RETEST")) badgeClass = "badge retest";
      else badgeClass = "badge test";

      const angles = Array.isArray(p.content_angles) ? p.content_angles.join("<br>&bull; ") : (p.content_angles || "N/A");
      const url = p.source_url ? `<a href="${escapeHtml(p.source_url)}" target="_blank" style="color:var(--accent); text-decoration:none;">View Link ↗</a>` : "needs_verification";

      tr.innerHTML = `
        <td><span class="score-badge" style="color: ${getScoreColor(score)}">${score}</span></td>
        <td><span class="score-badge" style="color: ${getReadinessColor(readiness)}">${readiness}</span></td>
        <td><span class="badge ${gate === "ELIGIBLE" ? "scale" : "hold"}">${escapeHtml(gate)}</span></td>
        <td><span class="${badgeClass}">${escapeHtml(rec)}</span></td>
        <td><strong>${escapeHtml(p.product || "Unknown")}</strong><br><small class="text-muted">${escapeHtml(p.brand || "")}</small></td>
        <td>${escapeHtml(p.category || "N/A")}</td>
        <td><strong>${escapeHtml(p.commission || "needs_verification")}</strong><br><small class="text-muted">Cookie: ${escapeHtml(p.cookie_window || "N/A")}</small></td>
        <td><small>${escapeHtml(p.target_audience || "N/A")}</small></td>
        <td><small>&bull; ${angles}</small></td>
        <td>${url}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 4. Content Pipeline
  const contentGrid = document.getElementById("content-grid");
  contentGrid.innerHTML = "";
  const assets = data.content_assets || [];

  if (assets.length === 0) {
    contentGrid.innerHTML = `<div class="text-muted" style="grid-column: 1/-1; padding: 2rem; text-align: center;">No content production files in content/ directory yet.</div>`;
  } else {
    assets.forEach(a => {
      const card = document.createElement("div");
      card.className = "content-asset-card";
      card.innerHTML = `
        <div class="asset-title">${escapeHtml(a.filename)}</div>
        <p class="text-muted" style="font-size:0.75rem; margin-bottom: 0.5rem;">Type: ${escapeHtml(a.type)} &bull; ${a.size_bytes} bytes</p>
        <span class="badge ${a.type === 'scripts' ? 'scale' : 'test'}">${escapeHtml(a.type)}</span>
      `;
      contentGrid.appendChild(card);
    });
  }

  // 5. Experiments
  const expContainer = document.getElementById("experiments-container");
  if (expContainer) {
    expContainer.innerHTML = "";
    const experiments = data.experiments || [];
    if (experiments.length === 0) {
      expContainer.innerHTML = `<div class="text-muted" style="padding: 2rem; text-align: center;">No active experiments defined in metrics/experiments/</div>`;
    } else {
      experiments.forEach(e => {
        const card = document.createElement("div");
        card.className = "review-card";
        const offerName = (e.offer && e.offer.name) || "Unknown Offer";
        card.innerHTML = `
          <div class="review-card-header">
            <div>
              <strong style="color:var(--accent); font-size:1.1rem;">${escapeHtml(e.experiment_id)}: ${escapeHtml(offerName)}</strong>
              <span class="badge test" style="margin-left: 0.8rem;">Status: ${escapeHtml(e.status || "planned")}</span>
            </div>
            <span class="text-muted" style="font-size:0.85rem;">Channel: ${escapeHtml(e.channel || "Multi-channel")}</span>
          </div>
          <p class="review-summary"><strong>Hypothesis:</strong> ${escapeHtml(e.hypothesis || "None")}</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.8rem;">
            <div>
              <strong style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">KPIs</strong>
              <ul class="review-list">
                <li><strong>Primary:</strong> ${escapeHtml(e.primary_kpi || "N/A")}</li>
                <li><strong>Secondary:</strong> ${escapeHtml(e.secondary_kpi || "N/A")}</li>
              </ul>
            </div>
            <div>
              <strong style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Creative Angle</strong>
              <ul class="review-list">
                <li><strong>Hook:</strong> "${escapeHtml(e.hook || "N/A")}"</li>
                <li><strong>CTA:</strong> "${escapeHtml(e.CTA || "N/A")}"</li>
              </ul>
            </div>
          </div>
        `;
        expContainer.appendChild(card);
      });
    }
  }

  // 6. Research Report
  const resReportEl = document.getElementById("research-report-body");
  const resFilenameEl = document.getElementById("research-filename");
  if (resReportEl) {
    if (data.latest_research) {
      if (resFilenameEl) resFilenameEl.textContent = `File: ${data.latest_research.filename}`;
      resReportEl.textContent = data.latest_research.content;
    } else {
      resReportEl.textContent = "No research report available yet in research/reports/.";
    }
  }

  // 7. Reviews Handoff
  const reviewsContainer = document.getElementById("reviews-container");
  reviewsContainer.innerHTML = "";
  const reviews = data.reviews || [];

  if (reviews.length === 0) {
    reviewsContainer.innerHTML = `<div class="text-muted" style="padding: 2rem; text-align: center;">No completed task reviews in results/ awaiting Lead action.</div>`;
  } else {
    reviews.forEach(r => {
      const card = document.createElement("div");
      card.className = "review-card";

      const dec = r.recommended_decision || "REVIEW";
      const conf = r.confidence !== undefined ? Math.round(r.confidence * 100) : 0;
      const findings = (r.key_findings || []).map(f => `<li>${escapeHtml(f)}</li>`).join("");
      const questions = (r.questions_for_lead || []).map(q => `<li>${escapeHtml(q)}</li>`).join("");
      const nextSteps = (r.next_task_suggestions || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");

      card.innerHTML = `
        <div class="review-card-header">
          <div>
            <strong style="color:var(--accent); font-size:1.1rem;">Task: ${escapeHtml(r.task_id || "Unknown")}</strong>
            <span class="badge ${getDecisionClass(dec)}" style="margin-left: 0.8rem;">Decision: ${escapeHtml(dec)}</span>
          </div>
          <span class="text-muted" style="font-size:0.85rem;">Confidence: ${conf}%</span>
        </div>
        <p class="review-summary"><strong>Executive Summary:</strong> ${escapeHtml(r.executive_summary || "None")}</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div>
            <strong style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Key Findings</strong>
            <ul class="review-list">${findings || "<li>None</li>"}</ul>
          </div>
          <div>
            <strong style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Questions for ChatGPT / Lead</strong>
            <ul class="review-list">${questions || "<li>None</li>"}</ul>
          </div>
        </div>
        <div>
          <strong style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Suggested Next Sprints</strong>
          <ul class="review-list">${nextSteps || "<li>None</li>"}</ul>
        </div>
      `;
      reviewsContainer.appendChild(card);
    });
  }

  // 8. Daily Report
  const reportBody = document.getElementById("daily-report-body");
  const reportFilename = document.getElementById("report-filename");
  if (data.latest_report) {
    reportFilename.textContent = `File: ${data.latest_report.filename}`;
    reportBody.textContent = data.latest_report.content;
  } else {
    reportFilename.textContent = "";
    reportBody.textContent = "No daily executive report found in metrics/daily/. Run `python scripts/daily_report.py` to generate one.";
  }
}

function getScoreColor(score) {
  if (typeof score !== "number") return "var(--text-muted)";
  if (score >= 80) return "var(--color-scale)";
  if (score >= 65) return "var(--color-test)";
  if (score >= 50) return "var(--color-retest)";
  return "var(--color-kill)";
}

function getReadinessColor(score) {
  return Number(score) >= 60 ? "var(--color-scale)" : "var(--color-kill)";
}

function getDecisionClass(decision) {
  const d = String(decision).toUpperCase();
  if (d.includes("SCALE")) return "scale";
  if (d.includes("TEST")) return "test";
  if (d.includes("RETEST")) return "retest";
  if (d.includes("KILL")) return "kill";
  return "test";
}

function escapeHtml(str) {
  if (typeof str !== "string") return String(str || "");
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Initial fetch and auto-refresh every 5 seconds
window.addEventListener("DOMContentLoaded", () => {
  fetchData();
  setInterval(fetchData, 5000);
});
