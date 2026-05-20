/* Oasis Reader — SPA frontend */

const SOURCES = [
  { key: "all", label: "All Sources", icon: "explore" },
  { key: "hackernews", label: "HackerNews", icon: "code" },
  { key: "reddit", label: "Reddit", icon: "forum" },
  { key: "tldr", label: "TLDR AI", icon: "newspaper" },
  { key: "papers", label: "HF Papers", icon: "science" },
];

let state = {
  bulletin: null,
  preferences: {},
  availableDates: [],
  currentDate: null,
  activeSource: "all",
  activeFilter: "recommended",
  calendarMonth: null, // { year, month } 0-based month
};

// ── Bootstrap ────────────────────────────────────────────────────────────────

async function init() {
  const initialDate = document.body.dataset.initialDate || null;

  const [datesRes, prefsRes] = await Promise.all([
    fetch("/api/bulletins/dates"),
    fetch("/api/preferences"),
  ]);
  const datesData = await datesRes.json();
  const prefsData = await prefsRes.json();

  state.availableDates = datesData.dates || [];
  state.preferences = prefsData.votes || {};

  // Pick the date to show
  const target = initialDate && state.availableDates.includes(initialDate)
    ? initialDate
    : state.availableDates[0] || null;

  // Initialise calendar month to the target date's month, or today
  const base = target ? new Date(target) : new Date();
  state.calendarMonth = { year: base.getFullYear(), month: base.getMonth() };

  renderCalendar();
  wireSourceNav();
  wireFilterButtons();
  wireSearch();
  wireRefreshButton();

  if (target) {
    await loadBulletin(target);
  } else {
    renderEmpty("No bulletins yet. Hit Refresh to run the pipeline.");
  }
}

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadBulletin(date) {
  state.currentDate = date;
  updateCalendarSelection();

  const res = await fetch(`/api/bulletins/${date}`);
  if (!res.ok) {
    renderEmpty(`No bulletin for ${date}.`);
    return;
  }
  state.bulletin = await res.json();
  renderBulletin();
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function renderBulletin() {
  const { bulletin } = state;

  document.getElementById("bulletin-date-label").textContent =
    `Sand Edition — ${bulletin.date}`;

  const meta = document.getElementById("bulletin-meta");
  meta.innerHTML = `
    <p class="font-semibold uppercase tracking-wider">Generated</p>
    <p>${bulletin.generated_at ? bulletin.generated_at.replace("T", " ").slice(0, 16) : "—"}</p>
    <p>${bulletin.items.length} articles</p>
  `;

  renderArticles();
}

function renderArticles() {
  const { bulletin, activeSource, activeFilter, preferences } = state;
  if (!bulletin) return;

  let items = [...bulletin.items];

  // Apply source filter
  if (activeSource !== "all") {
    items = items.filter(it => it.source === activeSource);
  }

  // Apply sort (items from API are already sorted by recommendation_score)
  if (activeFilter === "newest") {
    items.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  } else if (activeFilter === "top") {
    items.sort((a, b) => (b.score || 0) - (a.score || 0));
  }
  // "recommended" keeps server order (score desc, then timestamp desc)

  const grid = document.getElementById("articles-grid");

  if (!items.length) {
    grid.innerHTML = `
      <div class="col-span-3 text-center py-24 text-orange-300">
        <span class="material-symbols-outlined text-6xl block mb-4">hourglass_empty</span>
        <p class="text-lg font-semibold">No articles for this filter.</p>
      </div>`;
    document.getElementById("articles-count").textContent = "";
    return;
  }

  grid.innerHTML = items.map(item => articleCard(item)).join("");
  document.getElementById("articles-count").textContent =
    `${items.length} articles • ${bulletin.date}`;

  // Wire vote buttons
  grid.querySelectorAll(".vote-btn").forEach(btn => {
    btn.addEventListener("click", () => handleVote(btn));
  });

  applyVoteStates();
}

function articleCard(item) {
  const safeUrl = (url) => (url && (url.startsWith("http://") || url.startsWith("https://"))) ? url : "#";
  const score = item.recommendation_score != null ? item.recommendation_score : null;
  const reason = item.recommendation_reason || "";

  return `
  <article class="article-card break-inside-avoid mb-8 bg-white border border-orange-100/50 rounded-2xl overflow-hidden shadow-sm hover:shadow-xl hover:shadow-orange-900/5 transition-all group flex flex-col"
           data-source="${escHtml(item.source)}"
           data-timestamp="${escHtml(item.timestamp)}"
           data-score="${item.score || 0}"
           data-id="${escHtml(item.id)}">
    <div class="p-6 flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <span class="inline-block bg-orange-950/80 px-3 py-1 rounded-lg text-[10px] font-black text-white uppercase tracking-[0.15em]">${escHtml(item.category)}</span>
        ${score != null ? `<span class="text-[10px] font-bold text-orange-300 uppercase tracking-wider" title="${escHtml(reason)}">★ ${score}</span>` : ""}
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[11px] font-bold text-orange-400 uppercase tracking-wider">
          ${escHtml(item.timestamp.slice(0, 10))} • ${escHtml(item.source)}
          ${item.score ? ` • ▲ ${item.score}` : ""}
        </span>
      </div>
      <h2 class="text-xl font-bold leading-tight text-orange-950 group-hover:text-sunset-orange transition-colors">
        <a href="${safeUrl(item.url)}" target="_blank" rel="noopener">${escHtml(item.title)}</a>
      </h2>
      ${item.summary ? `<p class="text-sm text-orange-900/70 leading-relaxed line-clamp-4">${escHtml(item.summary)}</p>` : ""}
      <div class="mt-2 pt-5 border-t border-orange-50 flex items-center justify-between">
        <a class="text-sm font-extrabold text-sunset-orange flex items-center gap-2 group/link" href="${safeUrl(item.url)}" target="_blank" rel="noopener">
          Read Story
          <span class="material-symbols-outlined text-lg group-hover/link:translate-x-1 transition-transform">arrow_right_alt</span>
        </a>
        <div class="flex gap-1">
          <button class="vote-btn" data-id="${escHtml(item.id)}" data-vote="like" title="Like">👍</button>
          <button class="vote-btn" data-id="${escHtml(item.id)}" data-vote="dislike" title="Dislike">👎</button>
        </div>
      </div>
    </div>
  </article>`;
}

function applyVoteStates() {
  document.querySelectorAll(".vote-btn").forEach(btn => {
    const id = btn.dataset.id;
    const vote = btn.dataset.vote;
    const currentVote = state.preferences[id];
    btn.classList.remove("liked", "disliked");
    if (currentVote === vote) {
      btn.classList.add(vote === "like" ? "liked" : "disliked");
    }
  });
}

function renderEmpty(msg) {
  document.getElementById("articles-grid").innerHTML = `
    <div class="col-span-3 text-center py-24 text-orange-300">
      <span class="material-symbols-outlined text-6xl block mb-4">hourglass_empty</span>
      <p class="text-lg font-semibold">${escHtml(msg)}</p>
    </div>`;
  document.getElementById("loading-placeholder")?.remove();
}

// ── Vote handling ─────────────────────────────────────────────────────────────

async function handleVote(btn) {
  const id = btn.dataset.id;
  const vote = btn.dataset.vote;
  const currentVote = state.preferences[id];

  // Optimistic update
  const prev = state.preferences[id];
  if (currentVote === vote) {
    delete state.preferences[id];
  } else {
    state.preferences[id] = vote;
  }
  applyVoteStates();

  try {
    if (currentVote === vote) {
      const res = await fetch(`/api/preferences/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
    } else {
      const res = await fetch("/api/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: id, vote }),
      });
      if (!res.ok) throw new Error();
    }
  } catch {
    // Revert
    if (prev === undefined) delete state.preferences[id];
    else state.preferences[id] = prev;
    applyVoteStates();
  }
}

// ── Calendar ──────────────────────────────────────────────────────────────────

function renderCalendar() {
  const root = document.getElementById("calendar-root");
  if (!root) return;

  const { year, month } = state.calendarMonth;
  const available = new Set(state.availableDates);
  const today = new Date().toISOString().slice(0, 10);

  // Month navigation header
  const monthName = new Date(year, month, 1).toLocaleString("default", { month: "long", year: "numeric" });

  // First day of month and total days
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Prev/next bounds
  const allDates = state.availableDates;
  const earliest = allDates.length ? new Date(allDates[allDates.length - 1]) : null;
  const latest = allDates.length ? new Date(allDates[0]) : null;

  const canPrev = earliest && new Date(year, month - 1, 1) >= new Date(earliest.getFullYear(), earliest.getMonth(), 1);
  const canNext = latest && new Date(year, month + 1, 1) <= new Date(latest.getFullYear(), latest.getMonth(), 1);

  let dayCells = "";
  // Empty cells for days before month start
  for (let i = 0; i < firstDay; i++) {
    dayCells += `<div></div>`;
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const isoDate = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const hasData = available.has(isoDate);
    const isToday = isoDate === today;
    const isSelected = isoDate === state.currentDate;

    let cls = "text-center text-xs py-1 ";
    if (hasData) {
      cls += "font-bold cursor-pointer hover:bg-orange-100 rounded-lg ";
      if (isSelected) cls += "bg-orange-950 !text-white rounded-lg ";
      else cls += "text-orange-950 ";
    } else {
      cls += "text-orange-200 ";
    }
    if (isToday && !isSelected) cls += "ring-1 ring-sunset-orange rounded-lg ";

    const onclick = hasData ? `data-cal-date="${isoDate}"` : "";
    dayCells += `<div class="${cls}" ${onclick}>${d}</div>`;
  }

  root.innerHTML = `
    <div class="space-y-2">
      <div class="flex items-center justify-between px-1">
        <button id="cal-prev" class="text-orange-400 hover:text-orange-950 transition-colors ${canPrev ? "" : "opacity-30 pointer-events-none"}">
          <span class="material-symbols-outlined text-sm">chevron_left</span>
        </button>
        <span class="text-xs font-bold text-orange-700">${monthName}</span>
        <button id="cal-next" class="text-orange-400 hover:text-orange-950 transition-colors ${canNext ? "" : "opacity-30 pointer-events-none"}">
          <span class="material-symbols-outlined text-sm">chevron_right</span>
        </button>
      </div>
      <div class="grid grid-cols-7 gap-0.5 text-center">
        ${["S","M","T","W","T","F","S"].map(d => `<div class="text-[10px] font-black text-orange-300 py-1">${d}</div>`).join("")}
        ${dayCells}
      </div>
    </div>`;

  root.querySelectorAll("[data-cal-date]").forEach(el => {
    el.addEventListener("click", () => {
      const d = el.dataset.calDate;
      if (d) {
        const url = new URL(window.location.href);
        url.searchParams.set("date", d);
        window.history.pushState({}, "", url);
        loadBulletin(d);
      }
    });
  });

  document.getElementById("cal-prev")?.addEventListener("click", () => {
    if (!canPrev) return;
    state.calendarMonth = { year: month === 0 ? year - 1 : year, month: month === 0 ? 11 : month - 1 };
    renderCalendar();
  });
  document.getElementById("cal-next")?.addEventListener("click", () => {
    if (!canNext) return;
    state.calendarMonth = { year: month === 11 ? year + 1 : year, month: month === 11 ? 0 : month + 1 };
    renderCalendar();
  });
}

function updateCalendarSelection() {
  // Re-render the calendar to update the selected date highlight
  renderCalendar();
}

// ── Controls wiring ───────────────────────────────────────────────────────────

function wireSourceNav() {
  document.querySelectorAll(".source-link").forEach(link => {
    link.addEventListener("click", () => {
      document.querySelectorAll(".source-link").forEach(l => {
        l.classList.remove("bg-white", "text-sunset-orange", "font-bold", "shadow-sm", "border", "border-orange-100");
        l.classList.add("text-orange-800/70", "hover:bg-white/60");
      });
      link.classList.add("bg-white", "text-sunset-orange", "font-bold", "shadow-sm", "border", "border-orange-100");
      link.classList.remove("text-orange-800/70");
      state.activeSource = link.dataset.source;
      renderArticles();
    });
  });
}

function wireFilterButtons() {
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => {
        b.classList.remove("bg-orange-950", "text-white");
        b.classList.add("bg-white", "text-orange-600");
      });
      btn.classList.add("bg-orange-950", "text-white");
      btn.classList.remove("bg-white", "text-orange-600");
      state.activeFilter = btn.dataset.filter;
      renderArticles();
    });
  });
}

function wireSearch() {
  document.getElementById("search-input").addEventListener("input", function () {
    const q = this.value.toLowerCase();
    document.querySelectorAll(".article-card").forEach(card => {
      const text = card.innerText.toLowerCase();
      card.style.display = (!q || text.includes(q)) ? "" : "none";
    });
  });
}

function wireRefreshButton() {
  document.getElementById("refresh-btn").addEventListener("click", async () => {
    const btn = document.getElementById("refresh-btn");
    btn.disabled = true;
    btn.querySelector("span.material-symbols-outlined").textContent = "hourglass_empty";
    try {
      const res = await fetch("/api/refresh", { method: "POST" });
      if (res.status === 409) {
        alert("Pipeline is already running.");
      } else if (res.ok) {
        alert("Refresh started! Check back in a few minutes.");
      } else {
        alert("Failed to start refresh.");
      }
    } finally {
      btn.disabled = false;
      btn.querySelector("span.material-symbols-outlined").textContent = "refresh";
    }
  });
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Start ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", init);
