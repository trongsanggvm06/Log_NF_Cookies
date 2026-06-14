// ===== TAB SWITCHING =====
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(target).classList.add("active");
  });
});

// ===== COPY HELPER =====
async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    btn.classList.add("copied");
    btn.textContent = "Đã copy!";
    setTimeout(() => {
      btn.classList.remove("copied");
      btn.textContent = "Copy";
    }, 1800);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    btn.classList.add("copied");
    btn.textContent = "Đã copy!";
    setTimeout(() => { btn.classList.remove("copied"); btn.textContent = "Copy"; }, 1800);
  }
}

// ===== COPY VỚI QUOTA (PC + Mobile dùng chung quota, max 4 lần / card) =====
const COPY_LIMIT = 4;

async function copyWithQuota(btn) {
  const card = btn.closest(".result-card");
  if (!card) return;

  const limit = parseInt(card.dataset.copyLimit || COPY_LIMIT, 10);
  let count = parseInt(card.dataset.copyCount || "0", 10);

  if (count >= limit) return;

  const text = btn.dataset.copyText || "";
  await copyText(text, btn);

  count += 1;
  card.dataset.copyCount = String(count);

  const countSpan = card.querySelector(".copy-count");
  if (countSpan) countSpan.textContent = String(count);

  const bar = card.querySelector(".copy-quota-bar");
  if (bar) {
    bar.classList.toggle("quota-warn", count >= limit - 1 && count < limit);
    bar.classList.toggle("quota-done", count >= limit);
  }

  if (count >= limit) {
    card.querySelectorAll(".btn-copy").forEach((b) => {
      b.disabled = true;
      b.classList.add("disabled");
      b.textContent = "Hết lượt";
    });
  }
}

// ===== BUILD RESULT CARD =====
function buildCard(data, index = null) {
  const card = document.createElement("div");

  if (data.ok) {
    card.className = "result-card success";
    card.dataset.copyCount = "0";
    card.dataset.copyLimit = String(COPY_LIMIT);
    const indexBadge = index !== null ? `<span class="badge badge-index">#${index}</span>` : "";
    // 2 link: PC = netflix.com trực tiếp; Mobile = qua landing page /go (né app cướp link → NSES-404)
    const pcUrl = data.pc || data.url || data.mobile;
    const mobileUrl = data.mobile || data.pc || data.url;
    card.innerHTML = `
      <div class="result-header">
        ${indexBadge}
        <span class="badge badge-ok">✓ Thành công</span>
        <span class="result-title">Build: ${data.build_id || "—"}</span>
      </div>

      <div class="link-row">
        <span class="link-label">💻 Link PC</span>
        <a class="link-url" href="${pcUrl}" target="_blank" title="${pcUrl}">${pcUrl}</a>
        <button class="btn btn-sm btn-copy" data-copy-text="${pcUrl}" onclick="copyWithQuota(this)">Copy</button>
      </div>

      <div class="link-row">
        <span class="link-label">📱 Link Điện thoại</span>
        <a class="link-url" href="${mobileUrl}" target="_blank" title="${mobileUrl}">${mobileUrl}</a>
        <button class="btn btn-sm btn-copy" data-copy-text="${mobileUrl}" onclick="copyWithQuota(this)">Copy</button>
        <span class="copy-quota-bar">
          📋 <span class="copy-count">0</span>/${COPY_LIMIT}
        </span>
      </div>

      <div class="usage-grid">
        <div class="usage-item">
          <div class="usage-icon">💻</div>
          <div class="usage-title">PC/Laptop: gửi <b>Link PC</b> → mở trực tiếp</div>
        </div>
        <div class="usage-item">
          <div class="usage-icon">📱</div>
          <div class="usage-title">iOS + Android: gửi <b>Link Điện thoại</b> → dán vào Chrome/Safari</div>
        </div>
      </div>

      <div class="expiry-row">⏰ Hết hạn: <span>${data.expiry}</span></div>
    `;
  } else {
    card.className = "result-card error-card";
    const indexBadge = index !== null ? `<span class="badge badge-index">#${index}</span>` : "";
    const debugJson = data.debug ? JSON.stringify(data.debug, null, 2) : "";
    const debugId = `dbg-${Math.random().toString(36).slice(2, 9)}`;
    card.innerHTML = `
      <div class="result-header">
        ${indexBadge}
        <span class="badge badge-fail">✗ Thất bại</span>
      </div>
      <div class="error-msg">❌ ${data.error}</div>
      ${debugJson ? `
        <details style="margin-top:10px;">
          <summary style="cursor:pointer;color:var(--text-muted);font-size:.8rem;user-select:none;">
            🔍 Debug log (${data.debug.length} endpoint) — click để mở
          </summary>
          <div style="margin-top:8px;display:flex;gap:8px;align-items:center;">
            <button class="btn btn-sm btn-copy" onclick="copyText(document.getElementById('${debugId}').textContent, this)">📋 Copy debug</button>
            <span style="color:var(--text-muted);font-size:.72rem;">Paste vào chat để tôi phân tích</span>
          </div>
          <pre id="${debugId}" style="margin-top:8px;background:var(--card2);border:1px solid var(--border);border-radius:var(--radius);padding:12px;font-size:.72rem;color:var(--text);overflow:auto;max-height:400px;white-space:pre-wrap;word-break:break-all;">${debugJson.replace(/</g, "&lt;")}</pre>
        </details>
      ` : ""}
    `;
  }

  return card;
}

// ===== DEBUG MODE =====
const debugForm = document.getElementById("debug-form");
const debugBtn = document.getElementById("debug-btn");
const debugSpinner = document.getElementById("debug-spinner");
const debugResult = document.getElementById("debug-result");

debugForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const raw = document.getElementById("debug-cookie").value.trim();
  const url = document.getElementById("debug-url").value.trim();
  const method = document.getElementById("debug-method").value;
  if (!raw || !url) return;

  debugBtn.disabled = true;
  debugSpinner.style.display = "inline-block";
  debugResult.innerHTML = "";

  try {
    const resp = await fetch("/api/debug", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: raw, url, method }),
    });
    const data = await resp.json();
    const pre = document.createElement("pre");
    pre.style.cssText = "background:var(--card2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;font-size:.75rem;color:var(--text);overflow:auto;max-height:400px;white-space:pre-wrap;word-break:break-all;";
    pre.textContent = JSON.stringify(data, null, 2);
    debugResult.appendChild(pre);

    // Gợi ý nếu tìm thấy token
    const str = JSON.stringify(data);
    if (str.includes("loginToken") || str.includes("nftoken") || str.includes('"token"')) {
      const hint = document.createElement("div");
      hint.style.cssText = "margin-top:10px;padding:10px;background:#1a3a1a;border:1px solid var(--success);border-radius:var(--radius);color:var(--success);font-size:.82rem;";
      hint.textContent = "✅ Response có vẻ chứa token! Hãy copy URL này vào CUSTOM_ENDPOINT trong config.py";
      debugResult.insertBefore(hint, pre);
    }
  } catch {
    debugResult.innerHTML = '<div class="result-card error-card"><div class="error-msg">❌ Lỗi kết nối</div></div>';
  } finally {
    debugBtn.disabled = false;
    debugSpinner.style.display = "none";
  }
});

// ===== SINGLE MODE =====
const singleForm = document.getElementById("single-form");
const singleInput = document.getElementById("single-input");
const singleBtn = document.getElementById("single-btn");
const singleSpinner = document.getElementById("single-spinner");
const singleResults = document.getElementById("single-results");

document.getElementById("clear-single").addEventListener("click", () => {
  singleInput.value = "";
  singleResults.innerHTML = '<div class="empty-state"><div class="icon">🎬</div>Kết quả sẽ hiện ở đây</div>';
});

function switchToBatchWith(rawCookies) {
  document.querySelector('[data-tab="tab-batch"]').click();
  batchInput.value = rawCookies;
  setTimeout(() => batchInput.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
}

singleForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const raw = singleInput.value.trim();
  if (!raw) return;

  singleBtn.disabled = true;
  singleSpinner.style.display = "inline-block";
  singleResults.innerHTML = "";

  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: raw }),
    });
    const data = await resp.json();
    const card = buildCard(data);

    // Nếu server đề xuất chuyển sang batch → thêm nút auto-switch
    if (!data.ok && data.suggest_tab === "tab-batch") {
      const switchBtn = document.createElement("button");
      switchBtn.className = "btn-retry";
      switchBtn.style.borderColor = "var(--primary)";
      switchBtn.style.color = "var(--primary)";
      switchBtn.textContent = `📦 Chuyển sang tab Batch (${data.count} cookie)`;
      switchBtn.onclick = () => switchToBatchWith(raw);
      card.appendChild(switchBtn);
    }

    singleResults.appendChild(card);
  } catch {
    singleResults.innerHTML = '<div class="result-card error-card"><div class="error-msg">❌ Lỗi kết nối đến server</div></div>';
  } finally {
    singleBtn.disabled = false;
    singleSpinner.style.display = "none";
  }
});

// ===== BATCH MODE (PROGRESSIVE) =====
const batchForm = document.getElementById("batch-form");
const batchInput = document.getElementById("batch-input");
const batchBtn = document.getElementById("batch-btn");
const batchSpinner = document.getElementById("batch-spinner");
const batchResults = document.getElementById("batch-results");
const batchStats = document.getElementById("batch-stats");
const stopBtn = document.getElementById("stop-batch");
const progressWrap = document.getElementById("batch-progress-wrap");
const progressText = document.getElementById("batch-progress-text");
const progressPercent = document.getElementById("batch-progress-percent");
const progressFill = document.getElementById("batch-progress-fill");

const THROTTLE_MS = 300;  // delay giữa các request → né rate limit Netflix
let cancelRequested = false;

document.getElementById("clear-batch").addEventListener("click", () => {
  batchInput.value = "";
  batchResults.innerHTML = '<div class="empty-state"><div class="icon">📦</div>Kết quả batch sẽ hiện ở đây</div>';
  batchStats.style.display = "none";
  progressWrap.style.display = "none";
});

stopBtn.addEventListener("click", () => {
  cancelRequested = true;
  stopBtn.disabled = true;
  stopBtn.textContent = "Đang dừng...";
});

function setProgress(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  progressFill.style.width = pct + "%";
  progressPercent.textContent = pct + "%";
  progressText.textContent = `Đang xử lý ${done}/${total}...`;
  if (done >= total) {
    progressText.textContent = `Hoàn tất ${done}/${total}`;
    progressFill.classList.add("done");
  }
}

function buildPendingCard(index) {
  const card = document.createElement("div");
  card.className = "result-card pending";
  card.id = `card-pending-${index}`;
  card.innerHTML = `
    <div class="result-header">
      <span class="badge badge-index">#${index}</span>
      <div class="pending-label">
        <div class="mini-spinner"></div>
        Đang xử lý...
      </div>
    </div>
  `;
  return card;
}

function buildRetryButton(rawBlock, index) {
  const btn = document.createElement("button");
  btn.className = "btn-retry";
  btn.textContent = "🔄 Thử lại";
  btn.onclick = async () => {
    btn.disabled = true;
    btn.textContent = "Đang thử lại...";
    const data = await callGenerate(rawBlock);
    data.index = index;
    const newCard = buildCard(data, index);
    if (!data.ok) {
      newCard.appendChild(buildRetryButton(rawBlock, index));
    }
    const oldCard = document.querySelector(`#batch-results > [data-index="${index}"]`);
    if (oldCard) oldCard.replaceWith(newCard);
    newCard.dataset.index = index;
  };
  return btn;
}

async function callGenerate(rawBlock) {
  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: rawBlock }),
    });

    const contentType = resp.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const text = await resp.text();
      return {
        ok: false,
        error: `Server trả về phản hồi không hợp lệ (HTTP ${resp.status})`,
        debug_preview: text.slice(0, 200),
      };
    }

    const data = await resp.json();
    if (!resp.ok) {
      return {
        ok: false,
        error: data?.error || `HTTP ${resp.status}`,
        debug: data?.debug,
      };
    }
    return data;
  } catch (err) {
    return { ok: false, error: err?.message || "Lỗi kết nối đến server" };
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

batchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const raw = batchInput.value.trim();
  if (!raw) return;

  cancelRequested = false;
  batchBtn.disabled = true;
  batchSpinner.style.display = "inline-block";
  stopBtn.style.display = "inline-block";
  stopBtn.disabled = false;
  stopBtn.textContent = "⏹ Dừng";
  batchResults.innerHTML = "";
  batchStats.style.display = "none";
  progressFill.classList.remove("done");

  let blocks = [];
  try {
    const splitResp = await fetch("/api/split", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: raw }),
    });
    const splitData = await splitResp.json();
    if (!splitData.ok || !splitData.blocks?.length) {
      batchResults.innerHTML = `<div class="result-card error-card"><div class="error-msg">❌ ${splitData.error || "Không tách được block cookie"}</div></div>`;
      throw new Error("split failed");
    }
    blocks = splitData.blocks;
  } catch (err) {
    if (err.message !== "split failed") {
      batchResults.innerHTML = '<div class="result-card error-card"><div class="error-msg">❌ Lỗi kết nối đến server (split)</div></div>';
    }
    batchBtn.disabled = false;
    batchSpinner.style.display = "none";
    stopBtn.style.display = "none";
    return;
  }

  const total = blocks.length;
  progressWrap.style.display = "block";
  setProgress(0, total);

  // Tạo pending cards trước cho cảm giác instant feedback
  blocks.forEach((_, i) => {
    const card = buildPendingCard(i + 1);
    card.dataset.index = i + 1;
    batchResults.appendChild(card);
  });

  let ok = 0, fail = 0, processed = 0;
  for (let i = 0; i < blocks.length; i++) {
    if (cancelRequested) break;

    const block = blocks[i];
    const idx = i + 1;
    const data = await callGenerate(block);
    data.index = idx;

    if (data.ok) ok++; else fail++;
    processed++;

    const newCard = buildCard(data, idx);
    newCard.dataset.index = idx;
    if (!data.ok) {
      newCard.appendChild(buildRetryButton(block, idx));
    }

    const pendingCard = document.getElementById(`card-pending-${idx}`);
    if (pendingCard) {
      pendingCard.replaceWith(newCard);
    } else {
      batchResults.appendChild(newCard);
    }

    setProgress(processed, total);

    // Throttle: né rate limit Netflix
    if (i < blocks.length - 1 && !cancelRequested) {
      await sleep(THROTTLE_MS);
    }
  }

  // Cleanup: xoá các pending card còn lại (nếu bị cancel)
  if (cancelRequested) {
    document.querySelectorAll(".result-card.pending").forEach((c) => c.remove());
    progressText.textContent = `Đã dừng — xử lý ${processed}/${total}`;
  }

  batchStats.style.display = "flex";
  batchStats.innerHTML = `
    <span>Tổng: <strong>${total}</strong></span>
    <span>Thành công: <span class="ok">${ok}</span></span>
    <span>Thất bại: <span class="fail">${fail}</span></span>
    ${cancelRequested ? `<span>Đã huỷ: <strong>${total - processed}</strong></span>` : ""}
  `;

  batchBtn.disabled = false;
  batchSpinner.style.display = "none";
  stopBtn.style.display = "none";
});
