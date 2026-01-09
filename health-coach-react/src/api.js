// api.js — shared settings + API calls + simple storage

const SETTINGS_KEY = "hc.settings.v1";
const PLAN_KEY = "hc.lastPlan.v1";
const SCHEDULE_KEY = "hc.lastSchedule.v1";

const DEFAULT_SETTINGS = {
  gatewayUrl: "http://127.0.0.1:8000",
  userId: "demo-user",
};

// ---------- Settings ----------
export function getSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {}
  return { ...DEFAULT_SETTINGS };
}

export function saveSettings(partial) {
  const merged = { ...getSettings(), ...partial };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(merged));
  return merged;
}

export function resetSettings() {
  localStorage.removeItem(SETTINGS_KEY);
  return getSettings();
}

// ---------- Local cache (plan/schedule) ----------
export function cachePlan(plan) {
  localStorage.setItem(PLAN_KEY, JSON.stringify(plan || {}));
}
export function getCachedPlan() {
  try {
    return JSON.parse(localStorage.getItem(PLAN_KEY) || "{}");
  } catch {
    return {};
  }
}
export function cacheSchedule(s) {
  localStorage.setItem(SCHEDULE_KEY, JSON.stringify(s || {}));
}
export function getCachedSchedule() {
  try {
    return JSON.parse(localStorage.getItem(SCHEDULE_KEY) || "{}");
  } catch {
    return {};
  }
}

// ---------- HTTP helpers ----------
async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || res.statusText;
    throw new Error(msg || `Request failed: ${res.status}`);
  }
  return data;
}

function apiBase() {
  const { gatewayUrl } = getSettings();
  return gatewayUrl.replace(/\/+$/, "");
}

// ---------- API surface ----------
export const api = {
  async ping() {
    const base = apiBase();
    try {
      const tryHealth = await fetch(`${base}/health`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);
      if (tryHealth) return { ok: true, data: tryHealth };
      const root = await fetch(`${base}/`)
        .then((r) => ({ ok: r.ok, status: r.status }))
        .catch(() => ({ ok: false }));
      return root.ok
        ? { ok: true }
        : { ok: false, error: `Status ${root.status}` };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  },

  async planToday(payload) {
    const { userId } = getSettings();
    const body = {
      user_id: userId,
      profile: payload.profile,
      goal: payload.goal,
      equipment: payload.equipment || [],
    };
    const data = await fetchJSON(`${apiBase()}/plan/today`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    cachePlan(data);
    return data;
  },

  async commitSchedule(events) {
    const { userId } = getSettings();
    const data = await fetchJSON(`${apiBase()}/schedule/commit`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, events }),
    });
    cacheSchedule(data);
    return data;
  },

  async sendNudge({ tone, goal }) {
    const { userId } = getSettings();
    return await fetchJSON(`${apiBase()}/nudge/send`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, tone, goal }),
    });
  },

  async submitFeedback({ event_id, rating, reason, bandit_arm }) {
    const { userId } = getSettings();
    const body = { event_id, user_id: userId, rating, reason };
    if (bandit_arm) body.bandit_arm = bandit_arm;
    return await fetchJSON(`${apiBase()}/feedback`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};

// ---------- Shared utils ----------
export function isoTodayAt(hhmm) {
  const [h, m] = (hhmm || "00:00").split(":").map(Number);
  const d = new Date();
  d.setHours(h || 0, m || 0, 0, 0);
  return d.toISOString().slice(0, 19);
}
