const messagesEl = document.getElementById("messages");
const emptyState = document.getElementById("emptyState");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const sessionListEl = document.getElementById("sessionList");
const newChatBtn = document.getElementById("newChatBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

let currentSessionId = null;
let isStreaming = false;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res;
}

function addMessageRow(role, text) {
  emptyState.style.display = "none";
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const inner = document.createElement("div");
  inner.className = "msg-inner";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "U" : "AI";

  const content = document.createElement("div");
  content.className = "msg-content";
  content.textContent = text; // textContent only -> safe against XSS

  inner.appendChild(avatar);
  inner.appendChild(content);
  row.appendChild(inner);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return content;
}

function clearMessages() {
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyState);
  emptyState.style.display = "block";
}

async function loadSessions() {
  const res = await api("/api/sessions");
  const sessions = await res.json();
  sessionListEl.innerHTML = "";
  for (const s of sessions) {
    const item = document.createElement("div");
    item.className = "session-item" + (s.id === currentSessionId ? " active" : "");
    item.dataset.id = s.id;

    const title = document.createElement("span");
    title.className = "title";
    title.textContent = s.title;

    const delBtn = document.createElement("button");
    delBtn.className = "delete-btn";
    delBtn.textContent = "✕";
    delBtn.onclick = async (e) => {
      e.stopPropagation();
      await api(`/api/sessions/${s.id}`, { method: "DELETE" });
      if (currentSessionId === s.id) {
        currentSessionId = null;
        clearMessages();
      }
      await loadSessions();
    };

    item.onclick = () => selectSession(s.id);
    item.appendChild(title);
    item.appendChild(delBtn);
    sessionListEl.appendChild(item);
  }
  return sessions;
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  await loadSessions();
  clearMessages();
  const res = await api(`/api/sessions/${sessionId}/messages`);
  const msgs = await res.json();
  if (msgs.length > 0) {
    emptyState.style.display = "none";
  }
  for (const m of msgs) {
    addMessageRow(m.role, m.content);
  }
}

async function createNewSession() {
  const res = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ title: "New chat" }),
  });
  const session = await res.json();
  await selectSession(session.id);
}

async function ensureSession() {
  if (currentSessionId) return currentSessionId;
  const sessions = await loadSessions();
  if (sessions.length > 0) {
    await selectSession(sessions[0].id);
  } else {
    await createNewSession();
  }
  return currentSessionId;
}

function autoResizeInput() {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + "px";
}

async function sendMessage(text) {
  const sessionId = await ensureSession();
  isStreaming = true;
  sendBtn.disabled = true;

  addMessageRow("user", text);
  const assistantContentEl = addMessageRow("assistant", "");
  const cursor = document.createElement("span");
  cursor.className = "cursor";
  assistantContentEl.appendChild(cursor);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    if (!res.ok || !res.body) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Request failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      fullText += decoder.decode(value, { stream: true });
      assistantContentEl.textContent = fullText;
      assistantContentEl.appendChild(cursor);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    cursor.remove();
  } catch (err) {
    assistantContentEl.textContent = `Error: ${err.message}`;
    cursor.remove();
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    await loadSessions(); // refresh auto-generated title
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (isStreaming) return;
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = "";
  autoResizeInput();
  sendMessage(text);
});

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});
messageInput.addEventListener("input", autoResizeInput);

newChatBtn.addEventListener("click", () => {
  currentSessionId = null;
  clearMessages();
  createNewSession();
});

async function pollHealth() {
  try {
    const res = await api("/api/health");
    const health = await res.json();
    if (health.ollama_reachable) {
      statusDot.className = "status-dot online";
      statusText.textContent = `${health.ollama_model} online`;
    } else {
      statusDot.className = "status-dot offline";
      statusText.textContent = "Ollama offline";
    }
  } catch {
    statusDot.className = "status-dot offline";
    statusText.textContent = "backend offline";
  }
}

(async function init() {
  await loadSessions();
  pollHealth();
  setInterval(pollHealth, 15000);
})();
