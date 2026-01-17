import { useEffect, useMemo, useRef, useState } from "react";

import {
  api,
  getCachedPlan,
  getCachedSchedule,
  getSettings,
  isoTodayAt,
  saveSettings,
} from "./api";

/* -------------------- small helpers -------------------- */
function Spinner({ label = "Loading..." }) {
  return (
    <span className="d-inline-flex align-items-center gap-2">
      <span
        className="spinner-border spinner-border-sm"
        role="status"
        aria-hidden="true"
      />
      <span>{label}</span>
    </span>
  );
}

function Alert({ variant = "warning", children }) {
  if (!children) return null;
  return <div className={`alert alert-${variant} mt-3 mb-0`}>{children}</div>;
}

function safeArray(v) {
  return Array.isArray(v) ? v : [];
}

function fmtTimeHHMM(t) {
  return t ? String(t).slice(0, 5) : "—";
}

function fmtIso(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const date = d.toLocaleDateString();
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${date} • ${time}`;
}

/* -------------------- views -------------------- */
function PlanView({ plan }) {
  if (!plan) return null;

  const meals = safeArray(plan.meals);
  const workouts = safeArray(plan.workouts);
  const totals = plan.totals || plan.total || plan.summary || {};

  const fmtMacros = (m = {}) =>
    ["protein", "carbs", "fat"]
      .map((k) =>
        m[k] != null ? `${k[0].toUpperCase()}${k.slice(1)} ${m[k]}g` : null,
      )
      .filter(Boolean)
      .join(" · ");

  return (
    <div className="mt-3">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h3 className="h6 text-white mb-0">Today’s Plan</h3>
        <span className="badge text-bg-secondary">Generated</span>
      </div>

      {/* Summary */}
      {(totals.kcal ??
        totals.calories ??
        totals.protein_g ??
        totals.carbs_g ??
        totals.fat_g) != null && (
        <div className="card card-soft mb-3">
          <div className="card-body py-3">
            <div className="fw-semibold mb-1">Daily Summary</div>
            <div className="small text-muted">
              {(totals.kcal != null || totals.calories != null) && (
                <span className="me-3">
                  Calories: {totals.kcal ?? totals.calories} kcal
                </span>
              )}
              {totals.protein_g != null && (
                <span className="me-3">Protein: {totals.protein_g} g</span>
              )}
              {totals.carbs_g != null && (
                <span className="me-3">Carbs: {totals.carbs_g} g</span>
              )}
              {totals.fat_g != null && <span>Fat: {totals.fat_g} g</span>}
            </div>
          </div>
        </div>
      )}

      {/* Meals */}
      {meals.length > 0 && (
        <div className="mb-3">
          <div className="d-flex align-items-center justify-content-between mb-2">
            <h3 className="h6 text-white mb-0">Meals</h3>
            <span className="badge text-bg-dark">{meals.length}</span>
          </div>
          <ul className="list-group list-group-soft">
            {meals.map((m, i) => (
              <li
                key={i}
                className="list-group-item d-flex flex-column flex-md-row justify-content-between align-items-start"
              >
                <div className="me-3">
                  <div className="fw-semibold">{m.name || `Meal ${i + 1}`}</div>
                  <small className="text-muted">
                    {fmtMacros(m.macros)}
                    {m.calories != null ? ` · ${m.calories} kcal` : ""}
                  </small>
                </div>
                <span className="badge text-bg-secondary align-self-md-center mt-2 mt-md-0">
                  {fmtTimeHHMM(m.when)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Workouts */}
      {workouts.length > 0 && (
        <div className="mb-2">
          <div className="d-flex align-items-center justify-content-between mb-2">
            <h3 className="h6 text-white mb-0">Workout</h3>
            <span className="badge text-bg-dark">{workouts.length}</span>
          </div>
          <ul className="list-group list-group-soft">
            {workouts.map((w, i) => (
              <li
                key={i}
                className="list-group-item d-flex flex-column flex-md-row justify-content-between align-items-start"
              >
                <div className="me-3">
                  <div className="fw-semibold">{w.name || "Workout"}</div>
                  <small className="text-muted">
                    {w.focus ? `${w.focus} · ` : ""}
                    {w.duration_min != null ? `${w.duration_min} min` : ""}
                    {w.calories != null ? ` · ${w.calories} kcal` : ""}
                  </small>
                </div>
                <span className="badge text-bg-secondary align-self-md-center mt-2 mt-md-0">
                  {fmtTimeHHMM(w.when)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ScheduleView({ result }) {
  if (!result) return null;

  const events = safeArray(result.events || result.items || result.scheduled);
  return (
    <div className="mt-3">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h3 className="h6 text-white mb-0">Scheduled Items</h3>
        <span className="badge text-bg-dark">{events.length}</span>
      </div>

      {events.length === 0 ? (
        <div className="card card-soft">
          <div className="card-body py-3 text-muted">
            No items were scheduled.
          </div>
        </div>
      ) : (
        <ul className="list-group list-group-soft">
          {events.map((e, i) => (
            <li
              key={e.id || i}
              className="list-group-item d-flex flex-column flex-md-row justify-content-between align-items-start"
            >
              <div className="me-3">
                <div className="fw-semibold">
                  {e.title ||
                    (e.type === "meal"
                      ? "Meal"
                      : e.type === "workout"
                        ? "Workout"
                        : "Item")}
                </div>
                <small className="text-muted">
                  {e.type ? `${e.type}` : "item"}
                  {e.status ? ` · ${e.status}` : ""}
                  {e.notes ? ` · ${e.notes}` : ""}
                  {e.calories ? ` · ${e.calories} kcal` : ""}
                  {e.id ? (
                    <>
                      {" "}
                      · ID: <code className="code-soft">{e.id}</code>
                    </>
                  ) : null}
                </small>
              </div>
              <span className="badge text-bg-secondary align-self-md-center mt-2 mt-md-0">
                {fmtIso(e.when)}
              </span>
            </li>
          ))}
        </ul>
      )}

      {result.message && (
        <div className="alert alert-dark border-0 mt-3">{result.message}</div>
      )}
    </div>
  );
}

function NudgeView({ result, tone, goal }) {
  if (!result) return null;

  const text =
    result.text ||
    result.message ||
    result.nudge ||
    result.content ||
    "Nudge sent.";
  const id = result.id || result.event_id || result.notification_id || null;
  const sentAt = result.sent_at || result.when || result.timestamp || null;
  const channel = result.channel || result.medium || null;

  return (
    <div className="mt-3">
      <div className="alert alert-success mb-3">
        <div className="fw-semibold">Nudge sent successfully</div>
        <div className="small text-muted">
          Tone: <span className="badge text-bg-secondary me-2">{tone}</span>
          Goal: <code className="code-soft">{goal}</code>
          {channel ? <span className="ms-2">· via {channel}</span> : null}
          {sentAt ? <span className="ms-2">· {fmtIso(sentAt)}</span> : null}
          {id ? (
            <span className="ms-2">
              · ID: <code className="code-soft">{id}</code>
            </span>
          ) : null}
        </div>
      </div>

      <div className="card card-soft">
        <div className="card-body">
          <div className="fw-semibold mb-2">Message</div>
          <p className="mb-0">{text}</p>
        </div>
      </div>
    </div>
  );
}

/* -------------------- local profile persistence -------------------- */
const PROFILE_KEY = "hc_profile_v1";

function loadProfileDefaults() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveProfile(profile) {
  try {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  } catch {
    // ignore
  }
}

/* -------------------- App -------------------- */
export default function App() {
  // ------- Settings -------
  const [gatewayUrl, setGatewayUrl] = useState(getSettings().gatewayUrl);
  const [userId, setUserId] = useState(getSettings().userId);
  const [ping, setPing] = useState(null);
  const didPingRef = useRef(false);

  useEffect(() => {
    saveSettings({ gatewayUrl, userId });
  }, [gatewayUrl, userId]);

  useEffect(() => {
    let cancelled = false;

    // Failsafe so UI never stays "Pinging..."
    const timeout = setTimeout(() => {
      if (!cancelled) setPing({ ok: false, error: "Ping timeout" });
    }, 3000);

    api
      .ping()
      .then((res) => {
        clearTimeout(timeout);
        if (!cancelled) setPing(res);
      })
      .catch((e) => {
        clearTimeout(timeout);
        if (!cancelled)
          setPing({ ok: false, error: e?.message || "Ping failed" });
      });

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, []);

  // ------- Profile & Goal (with persistence) -------
  const stored = useMemo(() => loadProfileDefaults(), []);
  const [age, setAge] = useState(stored?.age ?? 24);
  const [sex, setSex] = useState(stored?.sex ?? "M");
  const [height, setHeight] = useState(stored?.height ?? 178);
  const [weight, setWeight] = useState(stored?.weight ?? 78);
  const [activity, setActivity] = useState(stored?.activity ?? "moderate");
  const [goalType, setGoalType] = useState(
    stored?.goalType ?? "general_health",
  );
  const [deficit, setDeficit] = useState(stored?.deficit ?? 400);
  const [equipment, setEquipment] = useState(
    stored?.equipment ?? "dumbbells,pullup_bar",
  );

  useEffect(() => {
    saveProfile({
      age,
      sex,
      height,
      weight,
      activity,
      goalType,
      deficit,
      equipment,
    });
  }, [age, sex, height, weight, activity, goalType, deficit, equipment]);

  const [plan, setPlan] = useState(null);
  const [planMsg, setPlanMsg] = useState("");
  const [isPlanning, setIsPlanning] = useState(false);
  useEffect(() => {
    const cached = getCachedPlan();
    if (cached) setPlan(cached);
  }, []);

  async function handlePlanToday() {
    setIsPlanning(true);
    setPlanMsg("");
    try {
      // basic validation
      if (!userId?.trim()) throw new Error("User ID is required.");
      if (+age <= 0 || +height <= 0 || +weight <= 0)
        throw new Error("Enter valid profile numbers.");

      const payload = {
        profile: {
          age: +age,
          sex,
          height_cm: +height,
          weight_kg: +weight,
          activity,
        },
        goal: { type: goalType, deficit_kcal: +deficit },
        equipment: (equipment || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };

      const data = await api.planToday(payload);
      setPlan(data);
    } catch (e) {
      setPlan(null);
      setPlanMsg(`Error: ${e.message}`);
    } finally {
      setIsPlanning(false);
    }
  }

  // ------- Schedule -------
  const [mealTimes, setMealTimes] = useState("08:00,13:00,19:00");
  const [workoutTime, setWorkoutTime] = useState("18:00");
  const [schedule, setSchedule] = useState(getCachedSchedule());
  const [scheduleMsg, setScheduleMsg] = useState("");
  const [isScheduling, setIsScheduling] = useState(false);

  function parseTimes(csv) {
    return (csv || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .filter((t) => /^\d{2}:\d{2}$/.test(t)); // HH:MM only
  }

  async function handleSchedule() {
    setIsScheduling(true);
    setScheduleMsg("");
    try {
      const currentPlan = getCachedPlan();
      const planMeals = safeArray(currentPlan?.meals);
      const planWorkout = safeArray(currentPlan?.workouts)[0];

      if (!currentPlan) throw new Error("Please generate a plan first.");
      const times = parseTimes(mealTimes);
      if (times.length === 0)
        throw new Error("Enter meal times as HH:MM (comma-separated).");

      // Build meals with titles cycling through plan meals
      const mealItems = times.map((t, idx) => ({
        type: "meal",
        when: isoTodayAt(t),
        title:
          planMeals[idx % Math.max(planMeals.length, 1)]?.name ||
          `Meal ${idx + 1}`,
      }));

      const workoutItems =
        workoutTime && /^\d{2}:\d{2}$/.test(workoutTime)
          ? [
              {
                type: "workout",
                when: isoTodayAt(workoutTime),
                title: planWorkout?.name || "Workout",
              },
            ]
          : [];

      const data = await api.commitSchedule([...mealItems, ...workoutItems]);
      setSchedule(data);
    } catch (e) {
      setSchedule(null);
      setScheduleMsg(`Error: ${e.message}`);
    } finally {
      setIsScheduling(false);
    }
  }

  // ------- Nudge -------
  const [tone, setTone] = useState("coach");
  const [goalText, setGoalText] = useState("stay_consistent");
  const [nudge, setNudge] = useState(null);
  const [nudgeMsg, setNudgeMsg] = useState("");
  const [isNudging, setIsNudging] = useState(false);

  async function handleNudge() {
    setIsNudging(true);
    setNudgeMsg("");
    try {
      if (!goalText.trim()) throw new Error("Goal text is required.");
      const data = await api.sendNudge({ tone, goal: goalText.trim() });
      setNudge(data);
    } catch (e) {
      setNudge(null);
      setNudgeMsg(`Error: ${e.message}`);
    } finally {
      setIsNudging(false);
    }
  }

  // ------- Feedback -------
  const [eventId, setEventId] = useState("");
  const [rating, setRating] = useState(5);
  const [reason, setReason] = useState("felt great");
  const [banditArm, setBanditArm] = useState("");
  const [feedbackOut, setFeedbackOut] = useState("");
  const [isFeedback, setIsFeedback] = useState(false);

  async function handleFeedback() {
    setIsFeedback(true);
    setFeedbackOut("");
    try {
      if (!eventId.trim()) throw new Error("Event ID is required.");
      const r = Math.max(1, Math.min(5, +rating || 5));

      const data = await api.submitFeedback({
        event_id: eventId.trim(),
        rating: r,
        reason: reason?.trim() || "ok",
        bandit_arm: banditArm || undefined,
      });

      setFeedbackOut(JSON.stringify(data, null, 2));
    } catch (e) {
      setFeedbackOut(`Error: ${e.message}`);
    } finally {
      setIsFeedback(false);
    }
  }

  async function copyFeedback() {
    try {
      await navigator.clipboard.writeText(feedbackOut || "");
    } catch {
      // ignore
    }
  }

  const pingBadge = useMemo(() => {
    if (ping == null)
      return <span className="badge text-bg-secondary">Pinging…</span>;
    if (ping.ok)
      return <span className="badge text-bg-success">Gateway OK</span>;
    return (
      <span className="badge text-bg-danger">
        Gateway Error{ping?.error ? `: ${ping.error}` : ""}
      </span>
    );
  }, [ping]);

  return (
    <div className="app-shell">
      {/* Top Bar */}
      <div className="topbar">
        <div className="container d-flex align-items-center justify-content-between py-3">
          <div>
            <div className="app-title">Health Coach</div>
            <div className="app-subtitle text-muted">
              Plan meals & workouts · Schedule · Nudges · Feedback
            </div>
          </div>
          <div className="d-flex align-items-center gap-2">
            {pingBadge}
            <span className="badge text-bg-dark">User: {userId || "—"}</span>
          </div>
        </div>
      </div>

      <div className="container py-4">
        {/* Settings / User */}
        <div className="card card-soft mb-3">
          <div className="card-body">
            <h2 className="h5 mb-3">User</h2>
            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label">User ID</label>
                <input
                  className="form-control"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="demo-user"
                />
              </div>

              {/* Keep gateway hidden like you had it (you can re-enable if needed)
              <div className="col-md-6">
                <label className="form-label">Gateway URL</label>
                <input
                  className="form-control"
                  value={gatewayUrl}
                  onChange={(e) => setGatewayUrl(e.target.value)}
                  placeholder="http://127.0.0.1:8000"
                />
              </div>
              */}
            </div>
          </div>
        </div>

        {/* Profile & Goal */}
        <div className="card card-soft mb-3">
          <div className="card-body">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <h2 className="h5 mb-3 section-title">Profile & Goal</h2>

              <span className="badge text-bg-dark">Saved locally</span>
            </div>

            <div className="row g-3">
              <div className="col-md-3">
                <label className="form-label">Age</label>
                <input
                  type="number"
                  className="form-control"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                />
              </div>

              <div className="col-md-3">
                <label className="form-label">Sex</label>
                <select
                  className="form-select"
                  value={sex}
                  onChange={(e) => setSex(e.target.value)}
                >
                  <option>M</option>
                  <option>F</option>
                  <option>Other</option>
                </select>
              </div>

              <div className="col-md-3">
                <label className="form-label">Height (cm)</label>
                <input
                  type="number"
                  className="form-control"
                  value={height}
                  onChange={(e) => setHeight(e.target.value)}
                />
              </div>

              <div className="col-md-3">
                <label className="form-label">Weight (kg)</label>
                <input
                  type="number"
                  className="form-control"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                />
              </div>

              <div className="col-md-3">
                <label className="form-label">Activity</label>
                <select
                  className="form-select"
                  value={activity}
                  onChange={(e) => setActivity(e.target.value)}
                >
                  <option>sedentary</option>
                  <option>light</option>
                  <option>moderate</option>
                  <option>active</option>
                  <option>very_active</option>
                </select>
              </div>

              <div className="col-md-3">
                <label className="form-label">Goal Type</label>
                <select
                  className="form-select"
                  value={goalType}
                  onChange={(e) => setGoalType(e.target.value)}
                >
                  <option>fat_loss</option>
                  <option>muscle_gain</option>
                  <option>endurance</option>
                  <option>general_health</option>
                </select>
              </div>

              <div className="col-md-3">
                <label className="form-label">Deficit (kcal)</label>
                <input
                  type="number"
                  className="form-control"
                  value={deficit}
                  onChange={(e) => setDeficit(e.target.value)}
                />
              </div>

              <div className="col-md-3">
                <label className="form-label">
                  Equipment (comma-separated)
                </label>
                <input
                  className="form-control"
                  value={equipment}
                  onChange={(e) => setEquipment(e.target.value)}
                  placeholder="dumbbells,pullup_bar"
                />
              </div>
            </div>

            <div className="mt-3 d-flex gap-2">
              <button
                className="btn btn-primary fw-bold"
                onClick={handlePlanToday}
                disabled={isPlanning}
              >
                {isPlanning ? <Spinner label="Planning..." /> : "Plan Today"}
              </button>
            </div>

            <Alert variant="warning">{planMsg}</Alert>
            {plan && <PlanView plan={plan} />}
          </div>
        </div>

        {/* Schedule */}
        <div className="card card-soft mb-3">
          <div className="card-body">
            <h2 className="h5 mb-2">Schedule</h2>
            <p className="text-muted mb-3">
              After planning, commit items to the Scheduler.
            </p>

            <div className="row g-3">
              <div className="col-md-8">
                <label className="form-label">
                  Meal Time(s) (HH:MM, comma-separated)
                </label>
                <input
                  className="form-control"
                  value={mealTimes}
                  onChange={(e) => setMealTimes(e.target.value)}
                  placeholder="08:00,13:00,19:00"
                />
                <div className="form-hint text-muted mt-1">
                  Example: <code className="code-soft">08:00,13:00,19:00</code>
                </div>
              </div>

              <div className="col-md-4">
                <label className="form-label">Workout Time (HH:MM)</label>
                <input
                  className="form-control"
                  value={workoutTime}
                  onChange={(e) => setWorkoutTime(e.target.value)}
                  placeholder="18:00"
                />
              </div>
            </div>

            <div className="mt-3">
              <button
                className="btn btn-primary fw-bold"
                onClick={handleSchedule}
                disabled={isScheduling}
              >
                {isScheduling ? (
                  <Spinner label="Committing..." />
                ) : (
                  "Commit Schedule"
                )}
              </button>
            </div>

            <Alert variant="warning">{scheduleMsg}</Alert>
            {schedule && <ScheduleView result={schedule} />}
          </div>
        </div>

        {/* Nudge */}
        <div className="card card-soft mb-3">
          <div className="card-body">
            <h2 className="h5 mb-3">Motivation Nudge</h2>
            <div className="row g-3">
              <div className="col-md-4">
                <label className="form-label">Tone</label>
                <select
                  className="form-select"
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                >
                  <option>coach</option>
                  <option>friendly</option>
                </select>
              </div>

              <div className="col-md-8">
                <label className="form-label">Goal Text</label>
                <input
                  className="form-control"
                  value={goalText}
                  onChange={(e) => setGoalText(e.target.value)}
                  placeholder="stay_consistent"
                />
              </div>
            </div>

            <div className="mt-3">
              <button
                className="btn btn-primary fw-bold"
                onClick={handleNudge}
                disabled={isNudging}
              >
                {isNudging ? <Spinner label="Sending..." /> : "Send Nudge"}
              </button>
            </div>

            <Alert variant="warning">{nudgeMsg}</Alert>
            {nudge && <NudgeView result={nudge} tone={tone} goal={goalText} />}
          </div>
        </div>

        {/* Feedback */}
        <div className="card card-soft mb-4">
          <div className="card-body">
            <h2 className="h5 mb-2">Feedback</h2>
            <p className="text-muted mb-3">
              Use an event ID from the Schedule result above.
            </p>

            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label">Event ID</label>
                <input
                  className="form-control"
                  value={eventId}
                  onChange={(e) => setEventId(e.target.value)}
                  placeholder="paste event id here"
                />
              </div>

              <div className="col-md-2">
                <label className="form-label">Rating (1–5)</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  className="form-control"
                  value={rating}
                  onChange={(e) => setRating(e.target.value)}
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Reason</label>
                <input
                  className="form-control"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Bandit Arm (optional)</label>
                <select
                  className="form-select"
                  value={banditArm}
                  onChange={(e) => setBanditArm(e.target.value)}
                >
                  <option value="">(none)</option>
                  <option>coach</option>
                  <option>friendly</option>
                </select>
              </div>
            </div>

            <div className="mt-3 d-flex gap-2">
              <button
                className="btn btn-primary fw-bold"
                onClick={handleFeedback}
                disabled={isFeedback}
              >
                {isFeedback ? (
                  <Spinner label="Submitting..." />
                ) : (
                  "Submit Feedback"
                )}
              </button>

              <button
                className="btn btn-outline-light"
                type="button"
                onClick={copyFeedback}
                disabled={!feedbackOut || feedbackOut.startsWith("Submitting")}
              >
                Copy Output
              </button>
            </div>

            <pre className="out mt-3">{feedbackOut}</pre>
          </div>
        </div>

        <footer className="text-center pb-4">
          <small className="text-muted">
            Done By: Anthony, Chris, Omar, Zaed
          </small>
        </footer>
      </div>
    </div>
  );
}
