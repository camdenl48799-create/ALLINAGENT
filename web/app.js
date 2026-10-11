(() => {
  "use strict";
  const STORAGE_KEY = "allinagent.browser-workspace.drafts.v1";
  const form = document.querySelector("#draft-form");
  const titleInput = document.querySelector("#draft-title");
  const bodyInput = document.querySelector("#draft-body");
  const list = document.querySelector("#draft-list");
  const status = document.querySelector("#storage-status");
  const view = document.querySelector("#draft-view");
  const viewTitle = document.querySelector("#view-title");
  const viewDate = document.querySelector("#view-date");
  const viewBody = document.querySelector("#view-body");
  const deleteButton = document.querySelector("#delete-draft");
  let drafts = [];
  let selectedId = null;
  let storageAvailable = true;

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts));
      status.textContent = "Saved in this browser only. No network sync is configured.";
      return true;
    } catch (_error) {
      storageAvailable = false;
      status.textContent = "Browser storage is unavailable or full. Draft changes cannot be saved.";
      return false;
    }
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.some(item => !item || typeof item.id !== "string" || typeof item.title !== "string" || typeof item.body !== "string")) {
        status.textContent = "Saved browser data has an invalid format. It was left untouched.";
        return;
      }
      drafts = parsed;
    } catch (_error) {
      storageAvailable = false;
      status.textContent = "Browser storage is unavailable or contains unreadable data. Nothing was overwritten.";
    }
  }

  function showDraft(id) {
    const draft = drafts.find(item => item.id === id);
    if (!draft) { view.hidden = true; selectedId = null; return; }
    selectedId = id;
    viewTitle.textContent = draft.title;
    viewDate.textContent = `Updated ${new Date(draft.updatedAt).toLocaleString()}`;
    viewBody.textContent = draft.body || "(No notes yet.)";
    view.hidden = false;
  }

  function render() {
    list.replaceChildren();
    if (!drafts.length) {
      const empty = document.createElement("li");
      empty.textContent = "No drafts saved yet.";
      list.append(empty);
      view.hidden = true;
      return;
    }
    for (const draft of drafts) {
      const item = document.createElement("li");
      const title = document.createElement("span");
      title.textContent = draft.title;
      const open = document.createElement("button");
      open.type = "button";
      open.textContent = "View";
      open.setAttribute("aria-label", `View ${draft.title}`);
      open.addEventListener("click", () => showDraft(draft.id));
      item.append(title, open);
      list.append(item);
    }
    if (selectedId) showDraft(selectedId);
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!storageAvailable) {
      status.textContent = "Cannot save because browser storage is unavailable.";
      return;
    }
    const title = titleInput.value.trim();
    if (!title) { titleInput.focus(); return; }
    const now = new Date().toISOString();
    const draft = { id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`, title, body: bodyInput.value, createdAt: now, updatedAt: now };
    drafts.unshift(draft);
    if (!save()) { drafts.shift(); return; }
    selectedId = draft.id;
    form.reset();
    render();
    titleInput.focus();
  });

  deleteButton.addEventListener("click", () => {
    if (!selectedId || !storageAvailable) return;
    const previous = drafts;
    drafts = drafts.filter(item => item.id !== selectedId);
    if (!save()) { drafts = previous; return; }
    selectedId = null;
    render();
  });

  load();
  render();
  if (storageAvailable && !status.textContent.startsWith("Saved browser data")) {
    status.textContent = "Drafts stay in this browser only. No network sync is configured.";
  }
})();
