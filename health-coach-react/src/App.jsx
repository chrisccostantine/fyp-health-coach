import { useEffect, useMemo, useRef, useState } from "react";
import ResultsSection from "./ResultsSection";

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

/* -------------------- views (kept) -------------------- */
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

/* -------------------- tiny UI blocks -------------------- */
function ProgressPills({ step, total }) {
  return (
    <div className="d-flex align-items-center gap-2">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`pill ${i === step ? "pill-active" : ""}`}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

function QuickStat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
function OptionCard({ title, subtitle, active, onClick }) {
  return (
    <button
      type="button"
      className={`option-card ${active ? "active" : ""}`}
      onClick={onClick}
    >
      <div className="option-title">{title}</div>
      {subtitle ? <div className="option-sub">{subtitle}</div> : null}
    </button>
  );
}
function LongSelect({ title, subtitle, active, onClick, right }) {
  return (
    <button
      type="button"
      className={`long-card ${active ? "active" : ""}`}
      onClick={onClick}
    >
      <div className="long-left">
        <div className="long-title">{title}</div>
        {subtitle ? <div className="long-sub">{subtitle}</div> : null}
      </div>
      <div className="long-right">{right}</div>
    </button>
  );
}

function OptionGrid({ children }) {
  return <div className="option-grid">{children}</div>;
}

/* -------------------- App -------------------- */
export default function App() {
  // ------- Settings -------
  const [gatewayUrl, setGatewayUrl] = useState(getSettings().gatewayUrl);
  const [userId, setUserId] = useState(getSettings().userId);
  const [ping, setPing] = useState(null);
  const didPingRef = useRef(false);
  // Extra quiz answers (MadMuscles style)

  useEffect(() => {
    saveSettings({ gatewayUrl, userId });
  }, [gatewayUrl, userId]);

  useEffect(() => {
    let cancelled = false;

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

  // ------- Funnel state (NEW) -------
  const [stage, setStage] = useState("landing"); // landing | quiz | results
  const [step, setStep] = useState(0); // 0..3
  const TOTAL_STEPS = 28;

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
  const [ageBand, setAgeBand] = useState("18-29");
  const [gender, setGender] = useState(sex || "M"); // keep in sync with your existing sex
  const [bodyType, setBodyType] = useState("average"); // slim | average | big | heavy
  const [goalPick, setGoalPick] = useState(goalType || "fat_loss"); // reuse your goalType
  const [targetBody, setTargetBody] = useState("athlete"); // athlete | hero | bodybuilder
  const [bodyFatLevel, setBodyFatLevel] = useState(22); // slider number
  const [problemAreas, setProblemAreas] = useState([]); // multi select
  const [dietPref, setDietPref] = useState("none"); // none | vegetarian | vegan | keto | mediterranean
  const [sugarFreq, setSugarFreq] = useState("not_often"); // not_often | 3_5_week | daily
  const [waterIntake, setWaterIntake] = useState("2_6"); // lt2 | 2_6 | 7_10 | gt10 | coffee_tea
  // Height & weight units
  const [heightUnit, setHeightUnit] = useState("cm"); // cm | ft
  const [weightUnit, setWeightUnit] = useState("kg"); // kg | lb

  const [heightValue, setHeightValue] = useState(height || "");
  const [currentWeight, setCurrentWeight] = useState(weight || "");
  const [targetWeight, setTargetWeight] = useState("");

  // Fitness level
  const [fitnessLevel, setFitnessLevel] = useState("beginner");

  // Exercise preferences (like / neutral / dislike)
  const [exercisePrefs, setExercisePrefs] = useState({});

  // Sports interests
  const [sports, setSports] = useState([]);
  // ---- New quiz states ----
  const [additionalGoals, setAdditionalGoals] = useState([]);
  const [pushupsLevel, setPushupsLevel] = useState("");
  const [pullupsLevel, setPullupsLevel] = useState("");
  const [workoutLocation, setWorkoutLocation] = useState(""); // home|gym|mixed
  const [trainingFreq, setTrainingFreq] = useState(""); // not_at_all|1_2|3|more_3
  const [workoutDurationPref, setWorkoutDurationPref] = useState(""); // 10_15|20_30|30_40|40_60|auto

  const [letFoodDecide, setLetFoodDecide] = useState(false);
  const [veggies, setVeggies] = useState([]);

  const [leadName, setLeadName] = useState("");
  const [leadDob, setLeadDob] = useState("");
  const [leadEmail, setLeadEmail] = useState("");
  const [fitnessAge, setFitnessAge] = useState(null);
  useEffect(() => {
    if (step === 27) {
      setFitnessAge(calcFitnessAge());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  useEffect(() => {
    if (heightUnit === "cm") setHeight(+heightValue || height);
    if (weightUnit === "kg") setWeight(+currentWeight || weight);
  }, [heightValue, currentWeight, heightUnit, weightUnit]);

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

  // ------- Plan -------
  const [plan, setPlan] = useState(null);
  const [planMsg, setPlanMsg] = useState("");
  const [isPlanning, setIsPlanning] = useState(false);
  useEffect(() => {
    const cached = getCachedPlan();
    if (cached) setPlan(cached);
  }, []);

  async function handlePlanToday({ autoGoResults = true } = {}) {
    setIsPlanning(true);
    setPlanMsg("");
    try {
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
      if (autoGoResults) setStage("results");
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
  function calcFitnessAge() {
    // super simple placeholder logic (you can improve later)
    const base = Number(age) || 24;

    let score = 0;
    if (trainingFreq === "not_at_all") score += 4;
    if (trainingFreq === "1_2") score += 2;
    if (trainingFreq === "3") score += 1;

    if (additionalGoals.includes("Improve sleep")) score += 1;
    if (additionalGoals.includes("Reduce Stress")) score += 1;

    // If user drinks very little water, add a bit
    if (waterIntake === "lt2") score += 1;

    return Math.max(14, base + score);
  }
  function toggleInArray(arr, item) {
    return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
  }

  function pickSingle(setter, value) {
    setter(value);
    nextStep();
  }

  function parseTimes(csv) {
    return (csv || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .filter((t) => /^\d{2}:\d{2}$/.test(t));
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
      return <span className="badge text-bg-secondary">Connecting…</span>;
    if (ping.ok) return <span className="badge text-bg-success">Online</span>;
    return (
      <span className="badge text-bg-danger">
        Offline{ping?.error ? `: ${ping.error}` : ""}
      </span>
    );
  }, [ping]);

  function startQuiz() {
    setStage("quiz");
    setStep(0);
    setPlanMsg("");
  }

  function nextStep() {
    setStep((s) => Math.min(TOTAL_STEPS - 1, s + 1));
  }

  function prevStep() {
    setStep((s) => Math.max(0, s - 1));
  }

  function goResults() {
    setStage("results");
  }

  return (
    <div className="app-shell">
      {/* Top Bar */}
      <div className="topbar">
        <div className="container d-flex align-items-center justify-content-between py-3">
          <div className="d-flex flex-column">
            <div className="app-title">Health Coach</div>
            <div className="app-subtitle text-muted">
              Personalized meals & workouts in minutes
            </div>
          </div>

          <div className="d-flex align-items-center gap-2">
            {pingBadge}
            <span className="badge text-bg-dark">User: {userId || "—"}</span>
          </div>
        </div>
      </div>

      <div className="container py-4">
        {/* LANDING */}
        {stage === "landing" && (
          <div className="row g-4 align-items-stretch">
            <div className="col-lg-7">
              <div className="hero card card-soft">
                <div className="card-body p-4 p-md-5">
                  <div className="hero-kicker">AI-Powered Daily Plan</div>
                  <h1 className="hero-title">
                    Build your plan for today — meals + workouts + schedule.
                  </h1>
                  <p className="hero-sub text-muted">
                    Answer a quick quiz and get a plan that matches your goal,
                    body, and equipment.
                  </p>

                  <div className="d-flex flex-wrap gap-3 mt-4">
                    <button
                      className="btn btn-primary btn-lg fw-bold"
                      onClick={startQuiz}
                    >
                      Start Quiz
                    </button>
                    <button
                      className="btn btn-outline-light btn-lg"
                      onClick={() => setStage("results")}
                      disabled={!getCachedPlan()}
                      title={!getCachedPlan() ? "Generate a plan first" : ""}
                    >
                      View My Plan
                    </button>
                  </div>

                  <div className="mt-4 hero-stats">
                    <QuickStat label="Time" value="~60 sec" />
                    <QuickStat label="Workouts" value="Home / Gym" />
                    <QuickStat label="Nutrition" value="Daily meals" />
                  </div>
                </div>
              </div>
            </div>

            <div className="col-lg-5">
              <div className="card card-soft h-100">
                <div className="card-body p-4">
                  <h2 className="h5 section-title mb-3">Your Account</h2>
                  <label className="form-label">User ID</label>
                  <input
                    className="form-control"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="demo-user"
                  />
                  <div className="text-muted small mt-2">
                    This ID is used for planning, scheduling, nudges, and
                    feedback.
                  </div>

                  {/* Optional: keep gateway hidden */}
                  {/* <div className="mt-3">
                    <label className="form-label">Gateway URL</label>
                    <input
                      className="form-control"
                      value={gatewayUrl}
                      onChange={(e) => setGatewayUrl(e.target.value)}
                    />
                  </div> */}

                  <div className="mt-4">
                    <div className="card card-soft">
                      <div className="card-body">
                        <div className="fw-semibold mb-1">What you’ll get</div>
                        <ul className="mb-0 small text-muted">
                          <li>Daily calorie & macro summary (if available)</li>
                          <li>Meal + workout timing suggestions</li>
                          <li>One-click scheduling + motivational nudges</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <button
                      className="btn btn-outline-light w-100"
                      onClick={startQuiz}
                    >
                      Continue →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* QUIZ */}
        {stage === "quiz" && (
          <div className="quiz-wrap">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <div>
                <div className="text-muted small">Quiz</div>
                <h2 className="h4 section-title mb-0">
                  Build your personalized plan
                </h2>
              </div>
              <ProgressPills step={step} total={TOTAL_STEPS} />
            </div>

            <div className="card card-soft">
              <div className="card-body p-4 p-md-5">
                {/* Step 0 */}
                {step === 0 && (
                  <>
                    <h3 className="quiz-title">BUILD YOUR PERFECT BODY</h3>
                    <div className="quiz-sub">
                      According to your age and BMI
                    </div>

                    <div className="age-grid mt-4">
                      {[
                        { k: "18-29", t: "Age: 18–29" },
                        { k: "30-39", t: "Age: 30–39" },
                        { k: "40-49", t: "Age: 40–49" },
                        { k: "50+", t: "Age: 50+" },
                      ].map((x) => (
                        <button
                          key={x.k}
                          type="button"
                          className={`age-card ${ageBand === x.k ? "active" : ""}`}
                          onClick={() => {
                            setAgeBand(x.k);
                            // Optional: set a reasonable default age
                            const midpoint =
                              x.k === "18-29"
                                ? 24
                                : x.k === "30-39"
                                  ? 35
                                  : x.k === "40-49"
                                    ? 45
                                    : 55;
                            setAge(midpoint);
                            nextStep();
                          }}
                        >
                          <div className="age-card-label">{x.t}</div>
                          <div className="age-card-arrow">›</div>
                        </button>
                      ))}
                    </div>
                  </>
                )}

                {/* Step 1 */}
                {step === 1 && (
                  <>
                    <h3 className="quiz-title">Choose your gender</h3>

                    <div className="long-stack mt-4">
                      <LongSelect
                        title="Male"
                        active={gender === "M"}
                        onClick={() => {
                          setGender("M");
                          nextStep();
                        }}
                        right={
                          <div className="long-right">
                            <img
                              className="long-img"
                              src="/images/male.png"
                              alt="Male"
                            />
                          </div>
                        }
                      />
                      <LongSelect
                        title="Female"
                        active={gender === "F"}
                        onClick={() => {
                          setGender("F");
                          nextStep();
                        }}
                        right={
                          <div className="long-right">
                            <img
                              className="long-img"
                              src="/images/female.png"
                              alt="Male"
                            />
                          </div>
                        }
                      />
                    </div>
                  </>
                )}

                {/* Step 2 */}
                {step === 2 && (
                  <>
                    <h3 className="quiz-title">Choose your body type</h3>

                    <OptionGrid>
                      {[
                        {
                          k: "slim",
                          t: "Slim",
                          img: "/images/slim-body-male.png",
                        },
                        {
                          k: "average",
                          t: "Average",
                          img: "/images/average-body-male.png",
                        },
                        {
                          k: "big",
                          t: "Big",
                          img: "/images/big-body-male.png",
                        },
                        {
                          k: "heavy",
                          t: "Heavy",
                          img: "/images/heavy-body-male.png",
                        },
                      ].map((x) => (
                        <button
                          key={x.k}
                          type="button"
                          className={`img-card ${bodyType === x.k ? "active" : ""}`}
                          onClick={() => {
                            setBodyType(x.k);
                            nextStep();
                          }}
                        >
                          <div className="img-card-top">
                            <img
                              className="img-card-img"
                              src={x.img}
                              alt={x.t}
                            />
                          </div>
                          <div className="img-card-bottom">{x.t}</div>
                        </button>
                      ))}
                    </OptionGrid>
                  </>
                )}

                {/* Step 3 */}
                {step === 3 && (
                  <>
                    <h3 className="quiz-title">Choose your goal</h3>

                    <div className="long-stack mt-4">
                      <LongSelect
                        title="Lose Weight"
                        active={goalPick === "fat_loss"}
                        onClick={() => {
                          setGoalPick("fat_loss");
                          setGoalType("fat_loss");
                          nextStep();
                        }}
                      />
                      <LongSelect
                        title="Gain Muscle Mass"
                        active={goalPick === "muscle_gain"}
                        onClick={() => {
                          setGoalPick("muscle_gain");
                          setGoalType("muscle_gain");
                          nextStep();
                        }}
                      />
                      <LongSelect
                        title="Get Shredded"
                        active={goalPick === "endurance"} // map however you want
                        onClick={() => {
                          setGoalPick("endurance");
                          setGoalType("endurance");
                          nextStep();
                        }}
                      />
                    </div>
                  </>
                )}
                {/*Step 4*/}
                {step === 4 && (
                  <>
                    <h3 className="quiz-title">Choose the body you want</h3>

                    <div className="long-stack mt-4">
                      {[
                        { k: "athlete", t: "Athlete" },
                        { k: "hero", t: "Hero" },
                        { k: "bodybuilder", t: "Bodybuilder" },
                      ].map((x) => (
                        <LongSelect
                          key={x.k}
                          title={x.t}
                          active={targetBody === x.k}
                          onClick={() => {
                            setTargetBody(x.k);
                            nextStep();
                          }}
                        />
                      ))}
                    </div>
                  </>
                )}
                {/*Step 5*/}
                {step === 5 && (
                  <>
                    <h3 className="quiz-title">
                      Choose your level of body fat
                    </h3>

                    <div className="slider-wrap mt-4">
                      <div className="slider-card mt-3">
                        {/* ❌ REMOVE THIS */}
                        {/* <div className="slider-pill">{bodyFatLevel}%</div> */}

                        <input
                          type="range"
                          min={5}
                          max={45}
                          value={bodyFatLevel}
                          onChange={(e) => setBodyFatLevel(+e.target.value)}
                          className="range"
                        />

                        <div className="slider-labels">
                          <span>5–9%</span>
                          <span>&gt;40%</span>
                        </div>
                      </div>

                      <button
                        className="btn btn-primary fw-bold btn-lg w-100 mt-4"
                        onClick={nextStep}
                      >
                        Continue
                      </button>
                    </div>
                  </>
                )}

                {/*Step 6*/}
                {step === 6 && (
                  <>
                    <h3 className="quiz-title">Select problem areas</h3>

                    <div className="problem-layout mt-4">
                      <div className="img-ph tall">
                        <img
                          src="/images/average-body-male.png"
                          alt="Preview"
                        />
                      </div>

                      <div className="problem-stack">
                        {["Chest", "Arms", "Belly", "Legs", "Full body"].map(
                          (p) => {
                            const key = p.toLowerCase().replace(" ", "_");
                            const active = problemAreas.includes(key);
                            return (
                              <button
                                key={key}
                                type="button"
                                className={`pill-btn ${active ? "active" : ""}`}
                                onClick={() => {
                                  setProblemAreas((prev) =>
                                    active
                                      ? prev.filter((x) => x !== key)
                                      : [...prev, key],
                                  );
                                }}
                              >
                                {p}
                              </button>
                            );
                          },
                        )}
                      </div>
                    </div>

                    <button
                      className="btn btn-primary fw-bold btn-lg w-100 mt-4"
                      onClick={nextStep}
                      disabled={problemAreas.length === 0}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 7*/}
                {step === 7 && (
                  <>
                    <h3 className="quiz-title">
                      Do you follow any of these diets?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        {
                          k: "vegetarian",
                          t: "Vegetarian",
                          s: "Excludes meat",
                        },
                        {
                          k: "vegan",
                          t: "Vegan",
                          s: "Excludes all animal products",
                        },
                        { k: "keto", t: "Keto", s: "Low-carb, high-fat" },
                        {
                          k: "mediterranean",
                          t: "Mediterranean",
                          s: "Rich in plant-based foods",
                        },
                        {
                          k: "I don't follow any diet",
                          t: "I don't follow any diet",
                          // s: "Rich in plant-based foods",
                        },
                      ].map((x) => (
                        <LongSelect
                          key={x.k}
                          title={x.t}
                          subtitle={x.s}
                          active={dietPref === x.k}
                          onClick={() => {
                            setDietPref(x.k);
                            nextStep();
                          }}
                          right={<span className="icon-ph">◦</span>}
                        />
                      ))}
                    </div>
                  </>
                )}
                {/*Step 8*/}
                {step === 8 && (
                  <>
                    <h3 className="quiz-title">
                      How often do you have sugary foods or drinks?
                    </h3>

                    <div className="long-stack mt-4">
                      <LongSelect
                        title="Not often. I'm not big on sweets"
                        active={sugarFreq === "not_often"}
                        onClick={() => {
                          setSugarFreq("not_often");
                          nextStep();
                        }}
                        right={<span className="icon-ph">🙂</span>}
                      />
                      <LongSelect
                        title="3–5 times a week"
                        active={sugarFreq === "3_5_week"}
                        onClick={() => {
                          setSugarFreq("3_5_week");
                          nextStep();
                        }}
                        right={<span className="icon-ph">🍦</span>}
                      />
                      <LongSelect
                        title="Pretty much every day"
                        active={sugarFreq === "daily"}
                        onClick={() => {
                          setSugarFreq("daily");
                          nextStep();
                        }}
                        right={<span className="icon-ph">🧁</span>}
                      />
                    </div>
                  </>
                )}
                {/*Step 9*/}
                {step === 9 && (
                  <>
                    <h3 className="quiz-title">
                      How much water do you drink daily?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        {
                          k: "lt2",
                          t: "Less than 2 glasses",
                          s: "up to 0.5L / 17oz",
                          ic: "💧",
                        },
                        {
                          k: "2_6",
                          t: "2–6 glasses",
                          s: "0.5–1.5L / 17–50oz",
                          ic: "💧💧",
                        },
                        {
                          k: "7_10",
                          t: "7–10 glasses",
                          s: "1.5–2.5L / 50–85oz",
                          ic: "💧💧💧",
                        },
                        {
                          k: "gt10",
                          t: "More than 10 glasses",
                          s: "more than 2.5L / 85oz",
                          ic: "🌧️",
                        },
                        {
                          k: "coffee_tea",
                          t: "I drink only coffee or tea",
                          s: "",
                          ic: "☕",
                        },
                      ].map((x) => (
                        <LongSelect
                          key={x.k}
                          title={x.t}
                          subtitle={x.s}
                          active={waterIntake === x.k}
                          onClick={() => setWaterIntake(x.k)}
                          right={<span className="icon-ph">{x.ic}</span>}
                        />
                      ))}
                    </div>

                    <button className="btn btn-primary ..." onClick={nextStep}>
                      Continue
                    </button>
                  </>
                )}
                {/*Step 10*/}
                {step === 10 && (
                  <>
                    <h3 className="quiz-title">What’s your height?</h3>

                    <div className="unit-toggle">
                      <button
                        className={heightUnit === "cm" ? "active" : ""}
                        onClick={() => setHeightUnit("cm")}
                      >
                        cm
                      </button>
                      <button
                        className={heightUnit === "ft" ? "active" : ""}
                        onClick={() => setHeightUnit("ft")}
                      >
                        ft
                      </button>
                    </div>

                    <input
                      className="line-input"
                      placeholder={`Height, ${heightUnit}`}
                      value={heightValue}
                      onChange={(e) => setHeightValue(e.target.value)}
                    />

                    <button className="btn btn-primary ..." onClick={nextStep}>
                      Continue
                    </button>
                  </>
                )}
                {/*Step 11*/}
                {step === 11 && (
                  <>
                    <h3 className="quiz-title">What’s your current weight?</h3>

                    <div className="unit-toggle">
                      <button
                        className={weightUnit === "kg" ? "active" : ""}
                        onClick={() => setWeightUnit("kg")}
                      >
                        kg
                      </button>
                      <button
                        className={weightUnit === "lb" ? "active" : ""}
                        onClick={() => setWeightUnit("lb")}
                      >
                        lb
                      </button>
                    </div>

                    <input
                      className="line-input"
                      placeholder={`Current weight, ${weightUnit}`}
                      value={currentWeight}
                      onChange={(e) => setCurrentWeight(e.target.value)}
                    />

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!currentWeight}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 12*/}
                {step === 12 && (
                  <>
                    <h3 className="quiz-title">What’s your target weight?</h3>

                    <div className="unit-toggle">
                      <button
                        className={weightUnit === "kg" ? "active" : ""}
                        onClick={() => setWeightUnit("kg")}
                      >
                        kg
                      </button>
                      <button
                        className={weightUnit === "lb" ? "active" : ""}
                        onClick={() => setWeightUnit("lb")}
                      >
                        lb
                      </button>
                    </div>

                    <input
                      className="line-input"
                      placeholder={`Target weight, ${weightUnit}`}
                      value={targetWeight}
                      onChange={(e) => setTargetWeight(e.target.value)}
                    />

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!targetWeight}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 13*/}
                {step === 13 && (
                  <>
                    <h3 className="quiz-title">
                      The last plan you’ll ever need to{" "}
                      <span style={{ color: "#ff4d00" }}>
                        finally get in shape
                      </span>
                    </h3>

                    <p className="quiz-sub mt-3">
                      Based on our calculations, you may hit your goal weight of{" "}
                      <strong>
                        {targetWeight} {weightUnit}
                      </strong>{" "}
                      by
                    </p>

                    <h4 className="mt-2" style={{ color: "#ff4d00" }}>
                      {new Date(Date.now() + 50 * 86400000).toDateString()}
                    </h4>

                    <div className="chart-placeholder mt-4">
                      📉 Progress Curve
                    </div>

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 14*/}
                {step === 14 && (
                  <>
                    <h3 className="quiz-title">
                      What’s your level of fitness?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        {
                          k: "beginner",
                          t: "Beginner",
                          s: "Standing up from the floor is hard.",
                        },
                        {
                          k: "amateur",
                          t: "Amateur",
                          s: "Exercise once a week, not consistent.",
                        },
                        {
                          k: "advanced",
                          t: "Advanced",
                          s: "I’m in the best shape of my life.",
                        },
                      ].map((x) => (
                        <LongSelect
                          key={x.k}
                          title={x.t}
                          subtitle={x.s}
                          active={fitnessLevel === x.k}
                          onClick={() => {
                            setFitnessLevel(x.k);
                            nextStep();
                          }}
                        />
                      ))}
                    </div>
                  </>
                )}
                {/*Step 15*/}
                {step === 15 && (
                  <>
                    <h3 className="quiz-title">Like it or dislike it</h3>

                    {[
                      { name: "Cardio", img: "/images/exercises/cardio.png" },
                      {
                        name: "Yoga / Stretching",
                        img: "/images/exercises/yoga.png",
                      },
                      {
                        name: "Lifting weights",
                        img: "/images/exercises/lifting.png",
                      },
                      {
                        name: "Pull-ups",
                        img: "/images/exercises/pullups.png",
                      },
                    ].map((item) => (
                      <div key={item.name} className="exercise-card">
                        <div className="exercise-img-box">
                          <img
                            className="exercise-img"
                            src={item.img}
                            alt={item.name}
                          />
                        </div>

                        <div className="exercise-name">{item.name}</div>

                        <div className="reaction-row">
                          {["dislike", "neutral", "like"].map((r) => (
                            <button
                              key={r}
                              className={`reaction-btn ${exercisePrefs[item.name] === r ? "active" : ""}`}
                              onClick={() =>
                                setExercisePrefs((prev) => ({
                                  ...prev,
                                  [item.name]: r,
                                }))
                              }
                            >
                              {r === "dislike"
                                ? "👎"
                                : r === "neutral"
                                  ? "😐"
                                  : "👍"}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                    >
                      Continue
                    </button>
                  </>
                )}

                {/*Step 16*/}
                {step === 16 && (
                  <>
                    <h3 className="quiz-title">
                      What sports are you interested in?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        "Gym Workouts",
                        "Workouts at home",
                        "Boxing",
                        "Other martial arts",
                        "Jogging",
                      ].map((s) => {
                        const active = sports.includes(s);
                        return (
                          <button
                            key={s}
                            className={`long-card ${active ? "active" : ""}`}
                            onClick={() =>
                              setSports((prev) =>
                                active
                                  ? prev.filter((x) => x !== s)
                                  : [...prev, s],
                              )
                            }
                          >
                            {s}
                          </button>
                        );
                      })}
                    </div>

                    <button className="btn btn-primary ..." onClick={nextStep}>
                      Continue
                    </button>
                  </>
                )}
                {/*Step 17*/}
                {step === 17 && (
                  <>
                    <h3 className="quiz-title">
                      Tick your additional goals below:
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        "Improve sleep",
                        "Form a physical habit",
                        "Feel healthier",
                        "Reduce Stress",
                        "Increase energy",
                        "Boost metabolism",
                      ].map((g) => {
                        const active = additionalGoals.includes(g);
                        return (
                          <button
                            key={g}
                            className={`long-card check ${active ? "active" : ""}`}
                            onClick={() =>
                              setAdditionalGoals((prev) =>
                                toggleInArray(prev, g),
                              )
                            }
                          >
                            <span className="long-card-title">{g}</span>
                            <span className={`box ${active ? "on" : ""}`} />
                          </button>
                        );
                      })}

                      <button
                        className={`long-card danger ${additionalGoals.length === 0 ? "active" : ""}`}
                        onClick={() => setAdditionalGoals([])}
                      >
                        <span className="long-card-title">
                          None of the above
                        </span>
                        <span className="xMark">✕</span>
                      </button>
                    </div>

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 18*/}
                {step === 18 && (
                  <>
                    <h3 className="quiz-title">
                      How many push-ups can you do in one round?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        { k: "lt10", t: "Less than 10" },
                        { k: "10_20", t: "10 to 20" },
                        { k: "21_30", t: "21 to 30" },
                        { k: "gt30", t: "More than 30" },
                      ].map((o) => (
                        <button
                          key={o.k}
                          className={`long-card ${pushupsLevel === o.k ? "active" : ""}`}
                          onClick={() => pickSingle(setPushupsLevel, o.k)}
                        >
                          <span className="long-card-title">{o.t}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {/*Step 19*/}
                {step === 19 && (
                  <>
                    <h3 className="quiz-title">
                      How many pull-ups can you do in one round?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        { k: "none", t: "I can't do a single pull-up" },
                        { k: "lt5", t: "Less than 5" },
                        { k: "5_10", t: "5 to 10" },
                        { k: "gt10", t: "More than 10" },
                      ].map((o) => (
                        <button
                          key={o.k}
                          className={`long-card ${pullupsLevel === o.k ? "active" : ""}`}
                          onClick={() => pickSingle(setPullupsLevel, o.k)}
                        >
                          <span className="long-card-title">{o.t}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {/*Step 20*/}
                {step === 20 && (
                  <>
                    <h3 className="quiz-title">Choose your workout location</h3>

                    <div className="long-stack mt-4">
                      {[
                        { k: "home", t: "Home" },
                        { k: "gym", t: "Gym" },
                        { k: "mixed", t: "Mixed" },
                      ].map((o) => (
                        <button
                          key={o.k}
                          className={`long-card ${workoutLocation === o.k ? "active" : ""}`}
                          onClick={() => pickSingle(setWorkoutLocation, o.k)}
                        >
                          <span className="long-card-title">{o.t}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {/*Step 21*/}
                {step === 21 && (
                  <>
                    <h3 className="quiz-title">
                      How many times per week have you trained in the last 3
                      months?
                    </h3>

                    <div className="long-stack mt-4">
                      {[
                        {
                          k: "not_at_all",
                          t: "Not at all",
                          s: "I haven't trained, but I will after claiming my program!",
                        },
                        { k: "1_2", t: "1-2 times a week" },
                        { k: "3", t: "3 times a week" },
                        { k: "more_3", t: "More than 3 times a week" },
                      ].map((o) => (
                        <button
                          key={o.k}
                          className={`long-card ${trainingFreq === o.k ? "active" : ""}`}
                          onClick={() => pickSingle(setTrainingFreq, o.k)}
                        >
                          <div>
                            <div className="long-card-title">{o.t}</div>
                            {o.s ? (
                              <div className="long-card-sub">{o.s}</div>
                            ) : null}
                          </div>
                        </button>
                      ))}
                    </div>

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!trainingFreq}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 22*/}
                {step === 22 && (
                  <>
                    <h3 className="quiz-title">
                      How long do you want your workouts to be?
                    </h3>

                    <div className="grid-2 mt-4">
                      {[
                        { k: "10_15", t: "10–15 minutes" },
                        { k: "20_30", t: "20–30 minutes" },
                        { k: "30_40", t: "30–40 minutes" },
                        { k: "40_60", t: "40–60 minutes" },
                      ].map((o) => (
                        <button
                          key={o.k}
                          className={`grid-card ${workoutDurationPref === o.k ? "active" : ""}`}
                          onClick={() => {
                            setWorkoutDurationPref(o.k);
                            nextStep();
                          }}
                        >
                          {o.t}
                        </button>
                      ))}
                      <button
                        className={`grid-card wide ${workoutDurationPref === "auto" ? "active" : ""}`}
                        onClick={() => {
                          setWorkoutDurationPref("auto");
                          nextStep();
                        }}
                      >
                        Let Health Coach decide
                      </button>
                    </div>
                  </>
                )}
                {/*Step 23*/}
                {step === 23 && (
                  <>
                    <h3 className="quiz-title">Choose the products you like</h3>
                    <p className="quiz-sub">
                      Let us create a meal plan based on your preferences. You
                      can always adjust it later.
                    </p>

                    <div className="toggle-row mt-4">
                      <span
                        className={`toggle-label ${letFoodDecide ? "on" : ""}`}
                      >
                        Let Health Coach choose
                      </span>

                      <button
                        className={`switch ${letFoodDecide ? "on" : ""}`}
                        onClick={() => {
                          setLetFoodDecide((v) => !v);
                          if (!letFoodDecide) setVeggies([]);
                        }}
                        type="button"
                      >
                        <span className="knob" />
                      </button>
                    </div>

                    <h4 className="chips-title mt-4">Veggies</h4>

                    <div className={`chips ${letFoodDecide ? "disabled" : ""}`}>
                      {[
                        "Broccoli",
                        "Cauliflower",
                        "Onion",
                        "Bell pepper",
                        "Eggplant",
                        "Cabbage",
                        "Asparagus",
                        "Spinach",
                        "Cucumber",
                        "Tomato",
                      ].map((v) => {
                        const active = veggies.includes(v);
                        return (
                          <button
                            key={v}
                            className={`chip ${active ? "active" : ""}`}
                            onClick={() =>
                              setVeggies((prev) => toggleInArray(prev, v))
                            }
                            disabled={letFoodDecide}
                            type="button"
                          >
                            {v}
                          </button>
                        );
                      })}
                    </div>

                    {/* IMPORTANT: DO NOT go to results here */}
                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 24*/}
                {step === 24 && (
                  <>
                    <div className="ready-banner">
                      ✅ Your personalized workout plan is ready!
                    </div>

                    <h3 className="quiz-title mt-4">What’s your name?</h3>

                    <input
                      className="line-input"
                      placeholder="Name"
                      value={leadName}
                      onChange={(e) => setLeadName(e.target.value)}
                    />

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!leadName.trim()}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 25*/}
                {step === 25 && (
                  <>
                    <div className="ready-banner">
                      ✅ Your personalized workout plan is ready!
                    </div>

                    <h3 className="quiz-title mt-4">
                      What’s your date of birth?
                    </h3>

                    <input
                      className="line-input"
                      placeholder="DD / MM / YYYY"
                      value={leadDob}
                      onChange={(e) => setLeadDob(e.target.value)}
                    />

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!leadDob.trim()}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 26*/}
                {step === 26 && (
                  <>
                    <div className="ready-banner">
                      ✅ Your personalized workout plan is ready!
                    </div>

                    <h3 className="quiz-title mt-4">Enter your email</h3>

                    <input
                      className="line-input"
                      placeholder="name@example.com"
                      value={leadEmail}
                      onChange={(e) => setLeadEmail(e.target.value)}
                      type="email"
                    />

                    <div className="privacy-row">
                      🔒 We respect your privacy and take protecting it very
                      seriously — no spam
                    </div>

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!leadDob.trim()}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 27*/}
                {step === 27 && (
                  <>
                    <h3 className="quiz-title">Your fitness age is</h3>

                    <div className="age-pill">
                      {fitnessAge ?? Number(age) ?? 24} years
                    </div>

                    <div className="fitness-copy">
                      <p>
                        This indicates a slight aging of the body. Irregular
                        exercise and sleeping late at night can lead to
                        metabolic aging.
                      </p>
                      <p>
                        People with a low metabolism are more likely to gain
                        weight and tire quickly.
                      </p>
                    </div>

                    <div className="meter-card">
                      <div className="meter-bar">
                        <span
                          className="meter-pin"
                          style={{ left: "45%" }} // you can compute this later
                        />
                      </div>
                      <div className="meter-text">
                        Your body age is older than your actual age
                      </div>
                    </div>

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={() => handlePlanToday({ autoGoResults: true })}
                      disabled={!leadEmail.trim() || isPlanning}
                    >
                      {isPlanning ? (
                        <Spinner label="Generating..." />
                      ) : (
                        "Continue"
                      )}
                    </button>
                  </>
                )}

                {/* Nav buttons */}
                <div className="d-flex flex-wrap gap-2 mt-4">
                  <button
                    className="btn btn-outline-light"
                    onClick={() =>
                      step === 0 ? setStage("landing") : prevStep()
                    }
                  >
                    ← Back
                  </button>

                  {/* {step < TOTAL_STEPS - 1 ? (
                    <button
                      className="btn btn-primary fw-bold"
                      onClick={nextStep}
                    >
                      Continue →
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary fw-bold"
                      onClick={() => handlePlanToday({ autoGoResults: true })}
                      disabled={isPlanning}
                    >
                      {isPlanning ? (
                        <Spinner label="Generating..." />
                      ) : (
                        "Get My Plan"
                      )}
                    </button>
                  )} */}
                </div>

                <Alert variant="warning">{planMsg}</Alert>
              </div>
            </div>
          </div>
        )}

        {/* RESULTS */}
        <ResultsSection
          stage={stage}
          plan={plan}
          setStage={setStage}
          isPlanning={isPlanning}
          handlePlanToday={handlePlanToday}
          eventId={eventId}
          setEventId={setEventId}
          rating={rating}
          setRating={setRating}
          reason={reason}
          setReason={setReason}
          banditArm={banditArm}
          setBanditArm={setBanditArm}
          isFeedback={isFeedback}
          handleFeedback={handleFeedback}
          feedbackOut={feedbackOut}
          copyFeedback={copyFeedback}
          mealTimes={mealTimes}
          setMealTimes={setMealTimes}
          workoutTime={workoutTime}
          setWorkoutTime={setWorkoutTime}
          isScheduling={isScheduling}
          handleSchedule={handleSchedule}
          scheduleMsg={scheduleMsg}
          schedule={schedule}
          tone={tone}
          setTone={setTone}
          goalText={goalText}
          setGoalText={setGoalText}
          isNudging={isNudging}
          handleNudge={handleNudge}
          nudgeMsg={nudgeMsg}
          nudge={nudge}
          PlanView={PlanView}
          ScheduleView={ScheduleView}
          NudgeView={NudgeView}
          Spinner={Spinner}
          Alert={Alert}
        />
      </div>

      <footer className="text-center pb-4 pt-4">
        <small className="text-muted">
          Done By: Anthony, Chris, Omar, Zaed
        </small>
      </footer>
    </div>
  );
}
