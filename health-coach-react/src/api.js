// api.js — shared settings + API calls + simple storage (upgraded)

const SETTINGS_KEY = "hc.settings.v1";
const PLAN_KEY = "hc.lastPlan.v1";
const CALENDAR_KEY = "hc.calendar.v1";

const ENV_GATEWAY_URL = (import.meta.env.VITE_GATEWAY_URL || "").trim();

function isLoopbackUrl(value) {
  return /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?/i.test(String(value || ""));
}

function resolveDefaultGatewayUrl() {
  if (ENV_GATEWAY_URL) return ENV_GATEWAY_URL.replace(/\/+$/, "");
  return "http://127.0.0.1:8000";
}

const DEFAULT_SETTINGS = {
  gatewayUrl: resolveDefaultGatewayUrl(),
  userId: "",
  authToken: "",
  currentUser: null,
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

function getAuthToken() {
  return getSettings().authToken || "";
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
  const merged = { ...DEFAULT_SETTINGS, ...(saved || {}) };

  // If the app is deployed and a real backend URL is provided, prefer it over stale localhost settings.
  if (ENV_GATEWAY_URL && isLoopbackUrl(merged.gatewayUrl)) {
    merged.gatewayUrl = resolveDefaultGatewayUrl();
  }

  return merged;
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

export function saveAuthSession({ token, user }) {
  return saveSettings({
    authToken: token || "",
    currentUser: user || null,
    userId: user?.user_id || "",
  });
}

export function clearAuthSession() {
  return saveSettings({
    authToken: "",
    currentUser: null,
    userId: "",
  });
}

// ---------- Local cache ----------
export function cachePlan(plan) {
  localStorage.setItem(PLAN_KEY, JSON.stringify(plan || {}));
}
export function getCachedPlan() {
  return safeJsonParse(localStorage.getItem(PLAN_KEY), null);
}

export function cacheCalendar(calendar) {
  localStorage.setItem(CALENDAR_KEY, JSON.stringify(calendar || {}));
}
export function getCachedCalendar() {
  return safeJsonParse(localStorage.getItem(CALENDAR_KEY), {});
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
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;

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

  async signup({ display_name, email, password, role = "user" }) {
    return await fetchJSON("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ display_name, email, password, role }),
    });
  },

  async login({ email, password }) {
    return await fetchJSON("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async me() {
    return await fetchJSON("/auth/me", { method: "GET" });
  },

  async logout() {
    return await fetchJSON("/auth/logout", {
      method: "POST",
      body: JSON.stringify({}),
    });
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
    if (data?.calendar) cacheCalendar(data.calendar);
    return data;
  },

  async getCalendar() {
    const data = await fetchJSON(`/calendar?user_id=${encodeURIComponent(getSettings().userId || "anon")}`, {
      method: "GET",
    });
    cacheCalendar(data);
    return data;
  },

  async syncCalendar(plan = null) {
    const body = withUserId(plan ? { plan } : {});
    const data = await fetchJSON("/calendar/sync", {
      method: "POST",
      body: JSON.stringify(body),
    });
    cacheCalendar(data);
    return data;
  },

  async getGoogleCalendarStatus() {
    return await fetchJSON("/google/calendar/status", { method: "GET" });
  },

  async startGoogleCalendarConnect() {
    return await fetchJSON("/google/calendar/connect", {
      method: "POST",
      body: JSON.stringify({}),
    });
  },

  async disconnectGoogleCalendar() {
    return await fetchJSON("/google/calendar/disconnect", {
      method: "POST",
      body: JSON.stringify({}),
    });
  },

  async listDietitianClients() {
    return await fetchJSON("/dietitian/clients", { method: "GET" });
  },

  async createDietitianClient({ display_name, email, password }) {
    return await fetchJSON("/dietitian/clients", {
      method: "POST",
      body: JSON.stringify({ display_name, email, password }),
    });
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

  async checkUser(userId) {
    return await fetchJSON(`/user/${encodeURIComponent(userId)}`, { method: "GET" });
  },

  async saveUserProfile(userId, { profile, goal, quizData = {} }) {
    return await fetchJSON(`/user/${encodeURIComponent(userId)}/profile`, {
      method: "POST",
      body: JSON.stringify({ profile, goal, quiz_data: quizData }),
    });
  },

  async dietChat({ message, current_plan, profile, goal, chat_history = [] }) {
    const body = withUserId({
      message,
      current_plan,
      profile,
      goal,
      chat_history,
    });
    const data = await fetchJSON("/diet/chat", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 30000,
    });
    if (data?.updated_plan) cachePlan(data.updated_plan);
    if (data?.calendar) cacheCalendar(data.calendar);
    return data;
  },

  async exerciseChat({ message, current_plan, profile, goal, chat_history = [] }) {
    const body = withUserId({
      message,
      current_plan,
      profile,
      goal,
      chat_history,
    });
    const data = await fetchJSON("/exercise/chat", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 30000,
    });
    if (data?.updated_plan) cachePlan(data.updated_plan);
    if (data?.calendar) cacheCalendar(data.calendar);
    return data;
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
