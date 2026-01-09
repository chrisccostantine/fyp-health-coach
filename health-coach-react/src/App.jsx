import { useEffect, useMemo, useState } from "react";
import {
  api,
  getCachedPlan,
  getCachedSchedule,
  getSettings,
  isoTodayAt,
  saveSettings,
} from "./api";

function PlanView({ plan }) {
  if (!plan) return null;

  const meals = Array.isArray(plan.meals) ? plan.meals : [];
  const workouts = Array.isArray(plan.workouts) ? plan.workouts : [];
  const totals = plan.totals || plan.total || plan.summary || {};

  const fmtTime = (t) => (t ? String(t).slice(0, 5) : "—");
  const fmtMacros = (m = {}) =>
    ["protein", "carbs", "fat"]
      .map((k) =>
        m[k] != null ? `${k[0].toUpperCase()}${k.slice(1)} ${m[k]}g` : null
      )
      .filter(Boolean)
      .join(" · ");

  return (
    <div className="mt-3">
      {/* Meals */}
      {meals.length > 0 && (
        <>
          <h3 className="h6 text-white mb-2">Meals</h3>
          <ul className="list-group mb-3">
            {meals.map((m, i) => (
              <li
                key={i}
                className="list-group-item d-flex flex-column flex-md-row justify-content-between align-items-start"
              >
                <div className="me-3">
                  <div className="fw-semibold">{m.name || "Meal"}</div>
                  <small className="text-muted">
                    {fmtMacros(m.macros)}{" "}
                    {m.calories != null ? `· ${m.calories} kcal` : ""}
                  </small>
                </div>
                <span className="badge text-bg-secondary align-self-md-center mt-2 mt-md-0">
                  {fmtTime(m.when)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {/* Workouts */}
      {workouts.length > 0 && (
        <>
          <h3 className="h6 text-white mb-2">Workout</h3>
          <ul className="list-group mb-3">
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
                  {fmtTime(w.when)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {/* Totals (if provided) */}
      {(totals.kcal ||
        totals.calories ||
        totals.protein_g ||
        totals.carbs_g ||
        totals.fat_g) && (
        <div className="alert alert-dark border-0">
          <div className="fw-semibold mb-1">Daily Summary</div>
          <div className="small">
            {totals.kcal != null || totals.calories != null ? (
              <span className="me-3">
                Calories: {totals.kcal ?? totals.calories} kcal
              </span>
            ) : null}
            {totals.protein_g != null && (
              <span className="me-3">Protein: {totals.protein_g} g</span>
            )}
            {totals.carbs_g != null && (
              <span className="me-3">Carbs: {totals.carbs_g} g</span>
            )}
            {totals.fat_g != null && <span>Fat: {totals.fat_g} g</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function ScheduleView({ result }) {
  if (!result) return null;

  // be flexible with API shapes:
  const events = result.events || result.items || result.scheduled || [];
  const fmt = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    // If parse fails (e.g., no timezone), just show the raw string:
    if (isNaN(d.getTime())) return iso;
    const date = d.toLocaleDateString();
    const time = d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${date} • ${time}`;
  };

  return (
    <div className="mt-3">
      <h3 className="h6 text-white mb-2">Scheduled Items</h3>
      {events.length === 0 ? (
        <div className="alert alert-dark border-0">
          No items were scheduled.
        </div>
      ) : (
        <ul className="list-group">
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
                </small>
                {/* {e.id && (
                  <div className="mt-1">
                    <small className="text-muted">
                      Event ID: <code>{e.id}</code>
                    </small>
                  </div>
                )} */}
              </div>
              <span className="badge text-bg-secondary align-self-md-center mt-2 mt-md-0">
                {fmt(e.when)}
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

  // Be flexible with API shapes
  const text =
    result.text ||
    result.message ||
    result.nudge ||
    result.content ||
    "Nudge sent.";
  const id = result.id || result.event_id || result.notification_id || null;
  const sentAt = result.sent_at || result.when || result.timestamp || null;
  const channel = result.channel || result.medium || null;

  const fmt = (iso) => {
    if (!iso) return null;
    const d = new Date(iso);
    return isNaN(d.getTime())
      ? String(iso)
      : `${d.toLocaleDateString()} • ${d.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}`;
  };

  return (
    <div className="mt-3">
      <div className="alert alert-success mb-3">
        <div className="fw-semibold">Nudge sent successfully</div>
        <div className="small text-muted">
          Tone: <span className="badge text-bg-secondary me-2">{tone}</span>
          Goal: <code>{goal}</code>
          {channel ? <span className="ms-2">· via {channel}</span> : null}
          {sentAt ? <span className="ms-2">· {fmt(sentAt)}</span> : null}
          {id ? (
            <span className="ms-2">
              · ID: <code>{id}</code>
            </span>
          ) : null}
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="fw-semibold mb-2">Message</div>
          <p className="mb-0">{text}</p>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  // ------- Settings -------
  const [gatewayUrl, setGatewayUrl] = useState(getSettings().gatewayUrl);
  const [userId, setUserId] = useState(getSettings().userId);
  const [ping, setPing] = useState(null);

  useEffect(() => {
    saveSettings({ gatewayUrl, userId });
  }, [gatewayUrl, userId]);

  useEffect(() => {
    api.ping().then(setPing);
  }, [gatewayUrl]);

  // ------- Profile & Goal -------
  const [age, setAge] = useState(24);
  const [sex, setSex] = useState("M");
  const [height, setHeight] = useState(178);
  const [weight, setWeight] = useState(78);
  const [activity, setActivity] = useState("moderate");
  const [goalType, setGoalType] = useState("general_health");
  const [deficit, setDeficit] = useState(400);
  const [equipment, setEquipment] = useState("dumbbells,pullup_bar");

  const [plan, setPlan] = useState(getCachedPlan());
  const [planMsg, setPlanMsg] = useState("");

  const [isPlanning, setIsPlanning] = useState(false);

  async function handlePlanToday() {
    setIsPlanning(true);
    setPlanMsg("Planning...");
    try {
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
      setPlan(data); // store object
      setPlanMsg(""); // clear message
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

  async function handleSchedule() {
    setIsScheduling(true);
    setScheduleMsg("Committing schedule...");
    try {
      const plan = getCachedPlan();

      const meals = (mealTimes || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((t) => ({ type: "meal", when: isoTodayAt(t) }));

      const workouts = workoutTime
        ? [{ type: "workout", when: isoTodayAt(workoutTime) }]
        : [];

      const items = [...meals, ...workouts].map((e, idx) => ({
        ...e,
        title:
          e.type === "meal"
            ? plan?.meals?.[idx % (plan?.meals?.length || 1)]?.name || "Meal"
            : plan?.workouts?.[0]?.name || "Workout",
      }));

      const data = await api.commitSchedule(items);
      setSchedule(data); // store the object
      setScheduleMsg(""); // clear message
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
    setNudgeMsg("Sending nudge...");
    try {
      const data = await api.sendNudge({ tone, goal: goalText });
      setNudge(data); // keep the object
      setNudgeMsg(""); // clear status
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
    setFeedbackOut("Submitting feedback...");
    try {
      const data = await api.submitFeedback({
        event_id: eventId,
        rating: +rating,
        reason,
        bandit_arm: banditArm || undefined,
      });
      setFeedbackOut(JSON.stringify(data, null, 2));
    } catch (e) {
      setFeedbackOut(`Error: ${e.message}`);
    } finally {
      setIsFeedback(false);
    }
  }

  const pingBadge = useMemo(() => {
    if (ping == null) return null;
    if (ping.ok)
      return <span className="badge text-bg-success">Gateway OK</span>;
    return (
      <span className="badge text-bg-danger">
        Gateway Error{ping?.error ? `: ${ping.error}` : ""}
      </span>
    );
  }, [ping]);

  return (
    <div className="container py-4">
      <header className="text-center mb-4">
        <h1 className="mb-1">Health Coach</h1>
        <p className="text-muted">
          Plan meals & workouts, schedule them, send nudges, and log feedback.
        </p>
      </header>

      {/* Gateway Settings */}
      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h5 mb-3">User Profile</h2>
          <div className="row g-3">
            {/* <div className="col-md-6">
              <label className="form-label">Gateway URL</label>
              <input
                className="form-control"
                value={gatewayUrl}
                onChange={(e) => setGatewayUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
              />
            </div> */}
            <div className="col-md-6">
              <label className="form-label">User ID</label>
              <input
                className="form-control"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="demo-user"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Profile & Goal */}
      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h5 mb-3">Profile &amp; Goal</h2>
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
              <label className="form-label">Equipment (comma-separated)</label>
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
              {isPlanning ? "Planning..." : "Plan Today"}
            </button>
          </div>

          {planMsg && <div className="alert alert-warning mt-3">{planMsg}</div>}
          {plan && <PlanView plan={plan} />}
        </div>
      </div>

      {/* Schedule */}
      <div className="card mb-3">
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
              />
            </div>
            <div className="col-md-4">
              <label className="form-label">Workout Time (HH:MM)</label>
              <input
                className="form-control"
                value={workoutTime}
                onChange={(e) => setWorkoutTime(e.target.value)}
              />
            </div>
          </div>

          <div className="mt-3">
            <button
              className="btn btn-primary fw-bold"
              onClick={handleSchedule}
              disabled={isScheduling}
            >
              {isScheduling ? "Committing..." : "Commit Schedule"}
            </button>
          </div>

          {scheduleMsg && (
            <div className="alert alert-warning mt-3">{scheduleMsg}</div>
          )}
          {schedule && <ScheduleView result={schedule} />}
        </div>
      </div>

      {/* Motivation Nudge */}
      <div className="card mb-3">
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
              {isNudging ? "Sending..." : "Send Nudge"}
            </button>
          </div>

          {nudgeMsg && (
            <div className="alert alert-warning mt-3">{nudgeMsg}</div>
          )}
          {nudge && <NudgeView result={nudge} tone={tone} goal={goalText} />}
        </div>
      </div>

      {/* Feedback */}
      <div className="card mb-4">
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

          <div className="mt-3">
            <button
              className="btn btn-primary fw-bold"
              onClick={handleFeedback}
              disabled={isFeedback}
            >
              {isFeedback ? "Submitting..." : "Submit Feedback"}
            </button>
          </div>

          <pre className="out mt-3">{feedbackOut}</pre>
        </div>
      </div>

      <footer className="text-center">
        <small>Done By: Anthony, Chris, Omar, Zaed</small>
      </footer>
    </div>
  );
}
