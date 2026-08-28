const messagesEl = document.getElementById("messages");
const composerEl = document.getElementById("composer");
const inputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const sessionDisplay = document.getElementById("session-display");
const statusDisplay = document.getElementById("status-display");
const newChatBtn = document.getElementById("new-chat-btn");
const promptList = document.getElementById("prompt-list");
const template = document.getElementById("message-template");

let sessionId = null;
let isSending = false;

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatAnswer(text) {
  let safe = escapeHtml(text);

  safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(
    /\[([^\]]+?)\s&gt;\s([^\]]+?)\]/g,
    '<span class="citation" title="$1 › $2">[$1]</span>',
  );

  const paragraphs = safe.split(/\n{2,}/).map((part) => part.replace(/\n/g, "<br />"));
  return paragraphs.map((part) => `<p>${part}</p>`).join("");
}

function shortSessionId(id) {
  if (!id) return "—";
  return `${id.slice(0, 8)}…`;
}

function setStatus(text) {
  statusDisplay.textContent = text;
}

function setBusy(busy) {
  isSending = busy;
  sendBtn.disabled = busy;
  inputEl.disabled = busy;
  promptList.querySelectorAll("button").forEach((btn) => {
    btn.disabled = busy;
  });
}

function showError(message) {
  const toast = document.createElement("div");
  toast.className = "error-toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  window.setTimeout(() => toast.remove(), 4500);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function createMessage(role, html, meta = null) {
  const node = template.content.firstElementChild.cloneNode(true);
  node.classList.add(role === "user" ? "message-user" : "message-agent");
  node.querySelector(".message-body").innerHTML = html;

  if (meta) {
    const footer = node.querySelector(".message-meta");
    footer.classList.remove("hidden");
    footer.innerHTML = meta;
  }

  messagesEl.appendChild(node);
  scrollToBottom();
  return node;
}

function showTyping() {
  const node = createMessage(
    "agent",
    '<div class="typing" aria-label="Thinking"><span></span><span></span><span></span></div>',
  );
  node.dataset.typing = "true";
  return node;
}

function removeTyping() {
  const typing = messagesEl.querySelector('[data-typing="true"]');
  if (typing) typing.remove();
}

function buildMeta(response) {
  const parts = [];

  if (response.handoff_recommended) {
    parts.push(`
      <div class="handoff-banner">
        <div>
          <strong>We recommend speaking with our team</strong>
          This situation may need a human review before we can proceed.
        </div>
      </div>
    `);
  }

  if (response.source_files?.length) {
    const tags = response.source_files
      .map((file) => `<li>${escapeHtml(file)}</li>`)
      .join("");
    parts.push(`
      <p class="sources-label">Referenced policies</p>
      <ul class="source-tags">${tags}</ul>
    `);
  }

  return parts.length ? parts.join("") : null;
}

async function createSession() {
  const response = await fetch("/api/sessions", { method: "POST" });
  if (!response.ok) {
    throw new Error("Could not start a new session.");
  }
  const data = await response.json();
  sessionId = data.session_id;
  sessionDisplay.textContent = shortSessionId(sessionId);
}

function resetConversation() {
  messagesEl.innerHTML = `
    <article class="message message-agent welcome">
      <div class="message-body">
        <p>Hello — I can help with returns, shipping, warranties, and order status.</p>
        <p class="muted">If you have an order question, include your order ID (for example, ORD-1007).</p>
      </div>
    </article>
  `;
}

async function sendMessage(text) {
  const trimmed = text.trim();
  if (!trimmed || isSending) return;

  if (!sessionId) {
    await createSession();
  }

  createMessage("user", `<p>${escapeHtml(trimmed)}</p>`);
  inputEl.value = "";
  autoResize();
  setBusy(true);
  setStatus("Thinking");
  const typingNode = showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: trimmed }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Something went wrong. Please try again.");
    }

    removeTyping();
    const meta = buildMeta(payload);
    createMessage("agent", formatAnswer(payload.answer), meta || null);
    setStatus(payload.handoff_recommended ? "Handoff suggested" : "Ready");
  } catch (error) {
    removeTyping();
    setStatus("Error");
    showError(error.message || "Could not send your message.");
  } finally {
    setBusy(false);
    inputEl.focus();
  }
}

function autoResize() {
  inputEl.style.height = "auto";
  inputEl.style.height = `${Math.min(inputEl.scrollHeight, 160)}px`;
}

composerEl.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(inputEl.value);
});

inputEl.addEventListener("input", autoResize);

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(inputEl.value);
  }
});

promptList.addEventListener("click", (event) => {
  const button = event.target.closest(".prompt-btn");
  if (!button) return;
  inputEl.value = button.dataset.prompt;
  autoResize();
  inputEl.focus();
});

newChatBtn.addEventListener("click", async () => {
  if (isSending) return;
  try {
    resetConversation();
    await createSession();
    setStatus("Ready");
    inputEl.focus();
  } catch (error) {
    showError(error.message);
  }
});

createSession()
  .then(() => setStatus("Ready"))
  .catch(() => {
    sessionDisplay.textContent = "—";
    setStatus("Offline");
    showError("Could not connect to the support service.");
  });

inputEl.focus();
