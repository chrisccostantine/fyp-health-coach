// api.js — shared settings + API calls + simple storage (upgraded)

const SETTINGS_KEY = "hc.settings.v1";
const PLAN_KEY = "hc.lastPlan.v1";
const SCHEDULE_KEY = "hc.lastSchedule.v1";

const DEFAULT_SETTINGS = {
  gatewayUrl: "http://127.0.0.1:8000",
  userId: "demo-user",
};

// Toggle debug logs if needed
const DEBUG = false;

// ---------- tiny utils ----------
function safeJsonParse(raw, fallback) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function apiBase() {
  const { gatewayUrl } = getSettings();
  return String(gatewayUrl || "").replace(/\/+$/, "");
}

function withUserId(body = {}) {
  const { userId } = getSettings();
  return { user_id: userId, ...body };
}

function buildErrorMessage(data, res) {
  // FastAPI typical: { detail: "..." } or { detail: [ { msg, loc } ] }
  const d = data?.detail ?? data?.message ?? data?.error ?? null;

  if (Array.isArray(d)) {
    // validation errors
    const parts = d
      .map((x) => {
        const loc = Array.isArray(x.loc) ? x.loc.join(".") : x.loc;
        return loc ? `${loc}: ${x.msg}` : x.msg;
      })
      .filter(Boolean);
    if (parts.length) return parts.join(" | ");
  }

  if (typeof d === "string" && d.trim()) return d;

  // if server returned something else
  if (typeof data?.raw === "string" && data.raw.trim()) return data.raw;

  return res?.statusText || `Request failed: ${res?.status || "unknown"}`;
}

// ---------- Settings ----------
export function getSettings() {
  const saved = safeJsonParse(localStorage.getItem(SETTINGS_KEY), null);
  return { ...DEFAULT_SETTINGS, ...(saved || {}) };
}

export function saveSettings(partial) {
  const merged = { ...getSettings(), ...(partial || {}) };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(merged));
  return merged;
}

export function resetSettings() {
  localStorage.removeItem(SETTINGS_KEY);
  return getSettings();
}

// ---------- Local cache ----------
export function cachePlan(plan) {
  localStorage.setItem(PLAN_KEY, JSON.stringify(plan || {}));
}
export function getCachedPlan() {
  return safeJsonParse(localStorage.getItem(PLAN_KEY), null);
}

export function cacheSchedule(s) {
  localStorage.setItem(SCHEDULE_KEY, JSON.stringify(s || {}));
}
export function getCachedSchedule() {
  return safeJsonParse(localStorage.getItem(SCHEDULE_KEY), {});
}

// ---------- HTTP helpers ----------
async function fetchJSON(path, options = {}) {
  const base = apiBase();
  const url = path.startsWith("http") ? path : `${base}${path}`;

  const timeoutMs = options.timeoutMs ?? 15000; // 15s default
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  try {
    if (DEBUG) console.log("[fetchJSON]", url, options);

    const res = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    const text = await res.text();
    const data = safeJsonParse(text, text ? { raw: text } : {});

    if (!res.ok) {
      throw new Error(buildErrorMessage(data, res));
    }

    return data;
  } catch (e) {
    if (e.name === "AbortError")
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

// ---------- API surface ----------
export const api = {
  async ping() {
    const base = apiBase();
    try {
      const res = await fetch(`${base}/health`, { method: "GET" });
      return res.ok
        ? { ok: true }
        : { ok: false, error: `Status ${res.status}` };
    } catch (e) {
      return { ok: false, error: e?.message || "Ping failed" };
    }
  },

  async planToday(payload) {
    const body = withUserId({
      profile: payload?.profile,
      goal: payload?.goal,
      equipment: payload?.equipment || [],
    });

    const data = await fetchJSON("/plan/today", {
      method: "POST",
      body: JSON.stringify(body),
    });

    cachePlan(data);
    return data;
  },

  async commitSchedule(events) {
    const body = withUserId({ events });

    const data = await fetchJSON("/schedule/commit", {
      method: "POST",
      body: JSON.stringify(body),
    });

    cacheSchedule(data);
    return data;
  },

  async sendNudge({ tone, goal }) {
    return await fetchJSON("/nudge/send", {
      method: "POST",
      body: JSON.stringify(withUserId({ tone, goal })),
    });
  },

  async submitFeedback({ event_id, rating, reason, bandit_arm }) {
    const body = withUserId({ event_id, rating, reason });
    if (bandit_arm) body.bandit_arm = bandit_arm;

    return await fetchJSON("/feedback", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};

// ---------- Shared utils ----------
export function isoTodayAt(hhmm) {
  const [h, m] = String(hhmm || "00:00")
    .split(":")
    .map((n) => Number(n));

  const d = new Date();
  d.setHours(Number.isFinite(h) ? h : 0, Number.isFinite(m) ? m : 0, 0, 0);

  // Backend-friendly: "YYYY-MM-DDTHH:MM:SS"
  // (no timezone suffix, consistent with your existing behavior)
  return d.toISOString().slice(0, 19);
}
