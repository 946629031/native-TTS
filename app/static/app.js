const $ = (id) => document.getElementById(id);

const SAMPLE = "说实话，这个 feature 我觉得吧，还差点意思。不过 API 的 latency 确实降下来了，从 800ms 到 200ms，体验完全不一样。";

let voices = [];
let current = null;
let busy = false;

/* ---------- 初始化 ---------- */

async function init() {
  try {
    voices = await (await fetch("/api/voices")).json();
    const sel = $("voice");
    sel.innerHTML = voices
      .map((v) => `<option value="${v.name}">${v.name} · ${v.desc}（${v.native}）</option>`)
      .join("");
    sel.value = "Serena";
  } catch (e) {
    showError("无法获取音色列表：" + e.message);
  }
  pollHealth();
  loadHistory();
  bind();
  updateMeta();
}

function bind() {
  $("text").addEventListener("input", updateMeta);
  $("generate").addEventListener("click", generate);
  $("sample").addEventListener("click", () => {
    $("text").value = SAMPLE;
    updateMeta();
    $("text").focus();
  });
  $("clear").addEventListener("click", () => {
    $("text").value = "";
    updateMeta();
    $("text").focus();
  });
  $("refresh").addEventListener("click", loadHistory);
  $("regen").addEventListener("click", generate);
  $("copy").addEventListener("click", copyPath);

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      $("instruct").value = chip.dataset.instruct || "";
    });
  });

  $("instruct").addEventListener("input", () => {
    document.querySelectorAll(".chip").forEach((c) => {
      const v = c.dataset.instruct || "";
      c.classList.toggle("active", v === $("instruct").value);
    });
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      generate();
    }
  });
}

/* ---------- 状态 ---------- */

async function pollHealth() {
  const set = (cls, text) => {
    $("status").className = "status " + cls;
    $("statusText").textContent = text;
  };
  try {
    const h = await (await fetch("/api/health")).json();
    if (h.status === "ready") {
      set("ready", "模型就绪");
      $("generate").disabled = false;
      return;
    }
    if (h.status === "error") {
      set("error", "模型加载失败");
      $("generate").disabled = true;
      showError(h.error || "模型加载失败");
      return;
    }
    set("loading", "模型加载中…");
  } catch {
    set("loading", "服务连接中…");
  }
  setTimeout(pollHealth, 900);
}

/* ---------- 生成 ---------- */

async function generate() {
  if (busy) return;
  const text = $("text").value.trim();
  if (!text) {
    showError("先输入一点文本。");
    $("text").focus();
    return;
  }

  busy = true;
  hideError();
  $("generate").disabled = true;
  $("progress").classList.remove("hidden");
  $("progressText").textContent = "生成中…";
  const t0 = performance.now();

  try {
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        voice: $("voice").value,
        lang: $("lang").value,
        instruct: $("instruct").value,
        normalize: $("normalize").checked,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

    current = data;
    showPlayer(data);
    loadHistory();
    $("progressText").textContent = `完成 · ${((performance.now() - t0) / 1000).toFixed(1)}s`;
    setTimeout(() => $("progress").classList.add("hidden"), 1200);
  } catch (e) {
    showError("生成失败：" + e.message);
    $("progress").classList.add("hidden");
  } finally {
    busy = false;
    $("generate").disabled = $("status").classList.contains("error");
  }
}

function showPlayer(item) {
  $("playerCard").classList.remove("hidden");
  $("playerVoice").textContent = item.voice;
  $("playerDur").textContent = `${item.duration.toFixed(2)} 秒 · ${item.text.length} 字`;
  const player = $("player");
  player.src = item.url + "?t=" + Date.now();
  player.play().catch(() => {}); // 浏览器可能拦截自动播放
  $("download").href = item.url;
  $("download").download = `${item.voice}-${item.id}.wav`;
}

async function copyPath() {
  if (!current) return;
  try {
    await navigator.clipboard.writeText(current.path);
    const btn = $("copy");
    const old = btn.textContent;
    btn.textContent = "已复制 ✓";
    setTimeout(() => (btn.textContent = old), 1200);
  } catch {
    showError("复制失败，路径：" + current.path);
  }
}

/* ---------- 历史 ---------- */

async function loadHistory() {
  const list = $("historyList");
  try {
    const items = await (await fetch("/api/history")).json();
    if (!items.length) {
      list.innerHTML = '<li class="empty">还没有生成记录</li>';
      return;
    }
    list.innerHTML = items
      .slice(0, 8)
      .map(
        (it) => `<li data-id="${it.id}">
          <button class="h-play" title="播放">▶</button>
          <span class="h-text" title="${esc(it.text)}">${esc(it.text)}</span>
          <span class="h-voice">${esc(it.voice)}</span>
          <span class="h-dur">${it.duration.toFixed(1)}s</span>
        </li>`
      )
      .join("");

    list.querySelectorAll("li").forEach((li) => {
      li.querySelector(".h-play").addEventListener("click", () => {
        const item = items.find((x) => x.id === li.dataset.id);
        if (item) {
          current = item;
          showPlayer(item);
        }
      });
    });
  } catch {
    list.innerHTML = '<li class="empty">历史记录加载失败</li>';
  }
}

/* ---------- 小工具 ---------- */

function updateMeta() {
  const text = $("text").value;
  const cjk = (text.match(/[\u4e00-\u9fff]/g) || []).length;
  const words = (text.match(/[A-Za-z]+/g) || []).length;
  const other = text.replace(/[\u4e00-\u9fff]|[A-Za-z]+|\s/g, "").length;
  const secs = cjk / 3.6 + words / 2.4 + other / 6 + (text.trim() ? 0.3 : 0);
  $("count").textContent = `${text.length} 字`;
  $("estimate").textContent = `约 ${secs.toFixed(1)} 秒`;
}

function showError(msg) {
  const el = $("error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  $("error").classList.add("hidden");
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

init();
