import { useEffect, useMemo, useState } from "react";
import ResultsSection from "./ResultsSection";

import {
  api,
  cacheCalendar,
  cachePlan,
  clearAuthSession,
  getCachedCalendar,
  getCachedPlan,
  getSettings,
  saveAuthSession,
  saveSettings,
} from "./api";
/* -------------------- Exports -------------------- */
export { App, NudgeView, CalendarView };

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

function fmtIso(iso) {
  if (!iso) return "--";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const date = d.toLocaleDateString();
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${date} - ${time}`;
}

function todayIsoLocal() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getPlanDays(plan) {
  return Array.isArray(plan?.plan_days) ? plan.plan_days : [];
}

function getActivePlanDate(plan, selectedDate) {
  const planDays = getPlanDays(plan);
  if (!planDays.length) return "";
  const availableDates = planDays.map((day) => String(day?.date || "").trim()).filter(Boolean);
  if (selectedDate && availableDates.includes(selectedDate)) return selectedDate;
  const today = todayIsoLocal();
  if (availableDates.includes(today)) return today;
  return availableDates[0] || "";
}

function getPlanSliceForDate(plan, selectedDate) {
  const planDays = getPlanDays(plan);
  if (!planDays.length) {
    return {
      activeDate: "",
      meals: Array.isArray(plan?.meals) ? plan.meals : [],
      workouts: Array.isArray(plan?.workouts) ? plan.workouts : [],
    };
  }

  const activeDate = getActivePlanDate(plan, selectedDate);
  const activeDay =
    planDays.find((day) => String(day?.date || "").trim() === activeDate) || planDays[0] || {};

  return {
    activeDate,
    meals: Array.isArray(activeDay?.meals) ? activeDay.meals : [],
    workouts: Array.isArray(activeDay?.workouts) ? activeDay.workouts : [],
  };
}

/* -------------------- CalendarView -------------------- */
function CalendarView({ result }) {
  if (!result) return null;

  const events = safeArray(result.events || result.items || result.scheduled);
  return (
    <div className="mt-3">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h3 className="h6 text-white mb-0">Calendar Schedule</h3>
        <span className="badge text-bg-dark">{events.length}</span>
      </div>

      {events.length === 0 ? (
        <div className="card card-soft">
          <div className="card-body py-3 text-muted">
            No calendar items yet.
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
                  {e.status ? ` - ${e.status}` : ""}
                  {e.notes ? ` - ${e.notes}` : ""}
                  {e.payload?.calories ? ` - ${e.payload.calories} kcal` : ""}
                  {e.id && (
                    <>
                      {" "}
                      - ID: <code className="code-soft">{e.id}</code>
                    </>
                  )}
                </small>
              </div>
              <span className="badge text-bg-secondary align-self-md-center mt-2 mt-md-0">
                {fmtIso(e.starts_at || e.when)}
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

/* -------------------- NudgeView (formerly second PlanView) -------------------- */
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
          {channel ? <span className="ms-2">- via {channel}</span> : null}
          {sentAt ? <span className="ms-2">- {fmtIso(sentAt)}</span> : null}
          {id ? (
            <span className="ms-2">
              - ID: <code className="code-soft">{id}</code>
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

const PROFILE_KEY = "hc_profile_v1";
const ACTIVE_QUIZ_STEPS = [
  0, 1, 3, 7, 8, 9, 10, 11, 12, 13, 20, 21, 22, 23, 28, 29, 27,
];

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

function FieldNote({ children }) {
  return <div className="field-note">{children}</div>;
}

function combineAssistantReplies(...replies) {
  const unique = replies
    .map((reply) => (typeof reply === "string" ? reply.trim() : ""))
    .filter(Boolean)
    .filter((reply, index, arr) => arr.indexOf(reply) === index);

  if (unique.length === 0) return "Plan updated.";
  return unique.join(" ");
}

function describeGoogleCalendarSync(syncResult) {
  const google = syncResult?.google_calendar;
  if (!google) return "";
  if (google.error) return `Error: ${google.error}`;
  if (Number.isFinite(google.created)) {
    return google.created > 0
      ? `Google Calendar synced ${google.created} event${google.created === 1 ? "" : "s"}.`
      : "Google Calendar sync ran, but there were no events to add.";
  }
  return "";
}

function feedbackRatingForStatus(status) {
  switch (status) {
    case "completed":
      return 5;
    case "partial":
      return 3;
    case "skipped":
      return 1;
    default:
      return 4;
  }
}

function feedbackReasonPrefix(status) {
  switch (status) {
    case "completed":
      return "completed";
    case "partial":
      return "partly completed";
    case "skipped":
      return "skipped";
    default:
      return "checked in";
  }
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

function homeStageFor(account) {
  if (!account) return "auth";
  return account.role === "dietitian" ? "dietitianHome" : "userHome";
}

function displayAccountName(account) {
  if (!account) return "Account";
  return account.display_name || account.email || "Account";
}

function toMetricHeight(value, unit) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return 0;
  return unit === "ft" ? Math.round(numeric * 30.48) : numeric;
}

function toMetricWeight(value, unit) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return 0;
  return unit === "lb" ? Math.round(numeric * 0.453592 * 10) / 10 : numeric;
}

function splitCommaList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function estimateGoalTimeline({
  currentWeight,
  targetWeight,
  weightUnit,
  goalType,
  deficit,
  activity,
  fitnessLevel,
  trainingFreq,
  age,
  bodyType,
}) {
  const currentKg = toMetricWeight(currentWeight, weightUnit);
  const targetKg = toMetricWeight(targetWeight, weightUnit);
  const deltaKg = Math.abs(targetKg - currentKg);

  if (!Number.isFinite(currentKg) || !Number.isFinite(targetKg) || deltaKg <= 0) {
    const fallbackDays = 14;
    return {
      days: fallbackDays,
      weeklyRateKg: 0,
      targetDate: new Date(Date.now() + fallbackDays * 86400000),
      summary: "You are already close to your target, so this is mainly about consistency.",
    };
  }

  const activityBoost = {
    sedentary: -0.04,
    light: 0,
    moderate: 0.05,
    active: 0.08,
    very_active: 0.1,
  }[activity] ?? 0;

  const fitnessBoost = {
    beginner: 0.03,
    amateur: 0,
    advanced: -0.02,
  }[fitnessLevel] ?? 0;

  const trainingBoost = {
    not_at_all: -0.03,
    "1_2": 0,
    "3": 0.03,
    more_3: 0.05,
  }[trainingFreq] ?? 0;

  const ageAdjustment =
    Number(age) >= 50 ? -0.05 : Number(age) >= 40 ? -0.02 : 0;

  let weeklyRateKg = 0.25;
  let summary = "A steady pace is more sustainable than an aggressive one.";

  if (targetKg < currentKg) {
    const deficitBased = Math.max(0.18, (Number(deficit || 0) * 7) / 7700);
    const bodyTypeBoost = bodyType === "heavy" ? 0.08 : bodyType === "big" ? 0.04 : 0;
    weeklyRateKg = deficitBased + activityBoost + fitnessBoost + trainingBoost + ageAdjustment + bodyTypeBoost;
    weeklyRateKg = Math.min(1.0, Math.max(0.2, weeklyRateKg));
    summary =
      goalType === "fat_loss"
        ? "This estimate uses your calorie deficit and training profile to project a realistic fat-loss pace."
        : "This estimate uses your weight gap, lifestyle, and activity level to project a safe pace.";
  } else if (targetKg > currentKg) {
    const goalBase = goalType === "muscle_gain" ? 0.28 : 0.2;
    const bodyTypeAdjustment = bodyType === "slim" ? 0.05 : 0;
    weeklyRateKg = goalBase + fitnessBoost + trainingBoost + ageAdjustment + bodyTypeAdjustment;
    weeklyRateKg = Math.min(0.5, Math.max(0.12, weeklyRateKg));
    summary =
      goalType === "muscle_gain"
        ? "This estimate assumes gradual lean mass gain with progressive training and consistent meals."
        : "This estimate assumes a gradual increase while keeping the plan sustainable.";
  } else {
    weeklyRateKg = 0.2;
  }

  const days = Math.max(14, Math.ceil((deltaKg / weeklyRateKg) * 7));
  return {
    days,
    weeklyRateKg,
    targetDate: new Date(Date.now() + days * 86400000),
    summary,
  };
}

function ProgressCurve({ startWeight, endWeight, unit }) {
  const width = 760;
  const height = 250;
  const padX = 36;
  const padY = 24;

  const isSame = Math.abs(endWeight - startWeight) < 0.01;
  const trendText = isSame
    ? "Maintenance trend"
    : endWeight < startWeight
      ? "Downward trend"
      : "Upward trend";

  const points = Array.from({ length: 8 }).map((_, idx) => {
    const t = idx / 7;
    const eased = 1 - (1 - t) ** 1.7;
    const base = startWeight + (endWeight - startWeight) * eased;
    const wave =
      Math.sin(t * Math.PI * 1.15) *
      Math.max(Math.abs(startWeight - endWeight) * 0.06, 0.25);
    return base + (idx === 0 || idx === 7 ? 0 : wave);
  });

  const minY = Math.min(...points);
  const maxY = Math.max(...points);
  const spread = Math.max(maxY - minY, 1);
  const yMin = minY - spread * 0.18;
  const yMax = maxY + spread * 0.18;

  const toXY = (value, idx) => {
    const x = padX + ((width - padX * 2) * idx) / (points.length - 1);
    const y = padY + ((value - yMin) / (yMax - yMin)) * (height - padY * 2);
    return [x, height - y];
  };

  const mapped = points.map((v, i) => toXY(v, i));

  const linePath = mapped
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  const areaPath = `${linePath} L ${mapped[mapped.length - 1][0].toFixed(1)},${(
    height - padY
  ).toFixed(1)} L ${mapped[0][0].toFixed(1)},${(height - padY).toFixed(1)} Z`;

  return (
    <div
      className="trend-chart mt-4"
      role="img"
      aria-label="Predicted weight trend chart"
    >
      <div className="trend-chart-header">
        <div className="trend-label">{trendText}</div>
        <div className="trend-range">
          {startWeight.toFixed(1)} {unit} to {endWeight.toFixed(1)} {unit}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="trend-svg"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="trendStroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#ff8a4a" />
            <stop offset="100%" stopColor="#ff4d00" />
          </linearGradient>

          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,77,0,0.35)" />
            <stop offset="100%" stopColor="rgba(255,77,0,0.04)" />
          </linearGradient>
        </defs>

        {[0.25, 0.5, 0.75].map((r) => {
          const gy = padY + (height - padY * 2) * r;
          return (
            <line
              key={r}
              x1={padX}
              x2={width - padX}
              y1={gy}
              y2={gy}
              className="trend-grid"
            />
          );
        })}

        <path d={areaPath} className="trend-area" />
        <path d={linePath} className="trend-line" />

        <circle r="5" className="trend-dot">
          <animateMotion dur="3.1s" repeatCount="indefinite" path={linePath} />
        </circle>

        {mapped.map(([x, y], idx) => (
          <circle key={idx} cx={x} cy={y} r="2.6" className="trend-node" />
        ))}
      </svg>

      <div className="trend-axis">
        <span>Today</span>
        <span>Goal date</span>
      </div>
    </div>
  );
}

/* -------------------- App -------------------- */
export default function App() {
  // ------- Settings -------
  const initialSettings = useMemo(() => getSettings(), []);
  const [gatewayUrl] = useState(initialSettings.gatewayUrl);
  const [userId, setUserId] = useState(initialSettings.userId || "");
  const [currentUser, setCurrentUser] = useState(initialSettings.currentUser || null);
  const [authMode, setAuthMode] = useState("login");
  const [authName, setAuthName] = useState(initialSettings.currentUser?.display_name || "");
  const [authEmail, setAuthEmail] = useState(initialSettings.currentUser?.email || "");
  const [authPassword, setAuthPassword] = useState("");
  const [authPasswordConfirm, setAuthPasswordConfirm] = useState("");
  const [authRole, setAuthRole] = useState("user");
  const [resetToken, setResetToken] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [changePasswordMsg, setChangePasswordMsg] = useState("");
  const [showChangePasswordForm, setShowChangePasswordForm] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isRestoringSession, setIsRestoringSession] = useState(
    Boolean(initialSettings.authToken),
  );
  const [managedClients, setManagedClients] = useState([]);
  const [viewedAccount, setViewedAccount] = useState(initialSettings.currentUser || null);
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPassword, setClientPassword] = useState("");
  const [isCreatingClient, setIsCreatingClient] = useState(false);
  const [clientMsg, setClientMsg] = useState("");
  const [activeChatPartner, setActiveChatPartner] = useState(null);
  const [privateMessages, setPrivateMessages] = useState([]);
  const [privateChatInput, setPrivateChatInput] = useState("");
  const [privateChatMsg, setPrivateChatMsg] = useState("");
  const [privateChatReturnStage, setPrivateChatReturnStage] = useState("userHome");
  const [isLoadingPrivateMessages, setIsLoadingPrivateMessages] = useState(false);
  const [isSendingPrivateMessage, setIsSendingPrivateMessage] = useState(false);
  const [googleCalendar, setGoogleCalendar] = useState({
    enabled: false,
    connected: false,
  });
  const [googleCalendarMsg, setGoogleCalendarMsg] = useState("");
  const [isGoogleCalendarBusy, setIsGoogleCalendarBusy] = useState(false);
  // Extra quiz answers (MadMuscles style)

  useEffect(() => {
    saveSettings({ gatewayUrl, userId });
  }, [gatewayUrl, userId]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const googleState = params.get("google_calendar");
    const resetTokenParam = params.get("reset_token");
    let shouldCleanUrl = false;
    if (resetTokenParam) {
      setResetToken(resetTokenParam);
      setAuthMode("reset");
      setStage("auth");
      setCheckUserMsg("");
      shouldCleanUrl = true;
    }
    if (googleState) {
      if (googleState === "connected") {
        setGoogleCalendarMsg("Google Calendar connected successfully.");
      } else if (googleState === "missing_code") {
        setGoogleCalendarMsg("Google Calendar connection was cancelled or incomplete.");
      } else if (googleState === "token_error") {
        setGoogleCalendarMsg("Google Calendar token exchange failed.");
      } else if (googleState === "invalid_state") {
        setGoogleCalendarMsg("Google Calendar state validation failed.");
      } else if (googleState === "not_configured") {
        setGoogleCalendarMsg("Google Calendar is not configured on the backend yet.");
      }
      shouldCleanUrl = true;
    }

    if (shouldCleanUrl) {
      const nextUrl = `${window.location.pathname}${window.location.hash || ""}`;
      window.history.replaceState({}, "", nextUrl);
    }
  }, []);

  const [isCheckingUser, setIsCheckingUser] = useState(false);
  const [checkUserMsg, setCheckUserMsg] = useState("");

  // ------- Funnel state (NEW) -------
  const [stage, setStage] = useState("auth"); // auth | userHome | dietitianHome | dietitianCreate | dietitianClients | privateChat | coachTools | quiz | results
  const [step, setStep] = useState(ACTIVE_QUIZ_STEPS[0]);
  const TOTAL_STEPS = ACTIVE_QUIZ_STEPS.length;
  const stepPosition = Math.max(0, ACTIVE_QUIZ_STEPS.indexOf(step));

  /* -------------------- Exports -------------------- */

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
  const [equipment] = useState(
    stored?.equipment ?? "dumbbells,pullup_bar",
  );
  const [gender, setGender] = useState(sex || "M"); // keep in sync with your existing sex
  const [bodyType, setBodyType] = useState("average"); // slim | average | big | heavy
  const [goalPick, setGoalPick] = useState(goalType || "fat_loss"); // reuse your goalType
  const [targetBody, setTargetBody] = useState("athlete"); // athlete | hero | bodybuilder
  const [bodyFatLevel, setBodyFatLevel] = useState(22); // slider number
  const [problemAreas, setProblemAreas] = useState([]); // multi select
  const [dietPref, setDietPref] = useState(stored?.dietPref ?? "none"); // none | vegetarian | vegan | keto | mediterranean
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
  const [allergiesInput, setAllergiesInput] = useState(stored?.allergiesInput ?? "");
  const [medicalConditionsInput, setMedicalConditionsInput] = useState(
    stored?.medicalConditionsInput ?? "",
  );
  const [injuriesInput, setInjuriesInput] = useState(stored?.injuriesInput ?? "");

  const [leadName, setLeadName] = useState("");
  const [leadDob, setLeadDob] = useState("");
  const [leadEmail, setLeadEmail] = useState("");
  const [fitnessAge, setFitnessAge] = useState(null);
  const [fitnessScore, setFitnessScore] = useState(null);
  const [fitnessMeterPercent, setFitnessMeterPercent] = useState(45);
  const [fitnessSummary, setFitnessSummary] = useState("");
  const [isLoadingFitnessScore, setIsLoadingFitnessScore] = useState(false);
  const ageBand =
    Number(age) < 25
      ? "under_25"
      : Number(age) < 35
        ? "25_34"
        : Number(age) < 50
          ? "35_49"
          : "50_plus";
  const timelineEstimate = useMemo(
    () =>
      estimateGoalTimeline({
        currentWeight: currentWeight || weight,
        targetWeight: targetWeight || currentWeight || weight,
        weightUnit,
        goalType,
        deficit,
        activity,
        fitnessLevel,
        trainingFreq,
        age,
        bodyType,
      }),
    [
      currentWeight,
      weight,
      targetWeight,
      weightUnit,
      goalType,
      deficit,
      activity,
      fitnessLevel,
      trainingFreq,
      age,
      bodyType,
    ],
  );
  useEffect(() => {
    if (step !== ACTIVE_QUIZ_STEPS[ACTIVE_QUIZ_STEPS.length - 1]) return;

    let cancelled = false;
    setIsLoadingFitnessScore(true);
    api
      .estimateFitnessScore({
        age,
        activity,
        fitness_level: fitnessLevel,
        training_freq: trainingFreq,
        workout_duration_pref: workoutDurationPref,
        water_intake: waterIntake,
        body_type: bodyType,
        goal_type: goalType,
        pushups_level: pushupsLevel,
        pullups_level: pullupsLevel,
        additional_goals: additionalGoals,
      })
      .then((data) => {
        if (cancelled) return;
        const assessment = data?.assessment || {};
        setFitnessAge(Number(assessment.fitness_age) || calcFitnessAge());
        setFitnessScore(Number(assessment.score) || null);
        setFitnessMeterPercent(Number(assessment.meter_percent) || 45);
        setFitnessSummary(String(assessment.summary || "").trim());
      })
      .catch(() => {
        if (cancelled) return;
        setFitnessAge(calcFitnessAge());
        setFitnessScore(null);
        setFitnessMeterPercent(45);
        setFitnessSummary("");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingFitnessScore(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    step,
    age,
    activity,
    fitnessLevel,
    trainingFreq,
    workoutDurationPref,
    waterIntake,
    bodyType,
    goalType,
    pushupsLevel,
    pullupsLevel,
    additionalGoals,
  ]);

  useEffect(() => {
    const metricHeight = toMetricHeight(heightValue, heightUnit);
    const metricWeight = toMetricWeight(currentWeight, weightUnit);
    if (metricHeight > 0) setHeight(metricHeight);
    if (metricWeight > 0) setWeight(metricWeight);
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
      dietPref,
      allergiesInput,
      medicalConditionsInput,
      injuriesInput,
    });
  }, [
    age,
    sex,
    height,
    weight,
    activity,
    goalType,
    deficit,
    equipment,
    dietPref,
    allergiesInput,
    medicalConditionsInput,
    injuriesInput,
  ]);

  // ------- Plan -------
  const [plan, setPlan] = useState(null);
  const [selectedPlanDate, setSelectedPlanDate] = useState("");
  const [planMsg, setPlanMsg] = useState("");
  const [isPlanning, setIsPlanning] = useState(false);
  const [dietChatInput, setDietChatInput] = useState("");
  const [dietChatMessages, setDietChatMessages] = useState([]);
  const [isDietChatting, setIsDietChatting] = useState(false);
  const [dietChatMsg, setDietChatMsg] = useState("");
  useEffect(() => {
    const cached = getCachedPlan();
    if (cached) setPlan(cached);
  }, []);

  useEffect(() => {
    if (!plan) {
      setSelectedPlanDate("");
      return;
    }
    setSelectedPlanDate((current) => getActivePlanDate(plan, current));
  }, [plan]);

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
          sex: gender || sex,
          height_cm: toMetricHeight(heightValue || height, heightUnit),
          weight_kg: toMetricWeight(currentWeight || weight, weightUnit),
          activity_level: activity,
          diet: {
            preference: dietPref,
            preferred_vegetables: letFoodDecide ? [] : veggies,
            allergies: splitCommaList(allergiesInput),
            medical_conditions: splitCommaList(medicalConditionsInput),
            sugar_frequency: sugarFreq,
            water_intake: waterIntake,
          },
          preferences: {
            target_weight_kg: toMetricWeight(targetWeight || currentWeight || weight, weightUnit),
            body_type: bodyType,
            target_body: targetBody,
            fitness_level: fitnessLevel,
            workout_location: workoutLocation,
            training_freq: trainingFreq,
            workout_duration_pref: workoutDurationPref,
            additional_goals: additionalGoals,
            pushups_level: pushupsLevel,
            pullups_level: pullupsLevel,
          },
          equipment: (equipment || "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          injuries: splitCommaList(injuriesInput),
        },
        goal: { type: goalType, deficit_kcal: +deficit },
        equipment: (equipment || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };

      const data = await api.planToday(payload);
      setPlan(data);
      setSelectedPlanDate(getActivePlanDate(data, ""));
      setCalendar(data?.calendar || null);
      if (data?.calendar) cacheCalendar(data.calendar);
      setCalendarMsg("");
      setDietChatMessages([
        {
          role: "assistant",
          text: "Your 30-day plan is ready. Ask me to modify meals, swap workouts, or explain the selected day.",
        },
      ]);
      // Persist profile so the user is recognised on next visit
      api.saveUserProfile(userId, {
        profile: payload.profile,
        goal: payload.goal,
        quizData: {
          ageBand, gender, bodyType, goalPick, targetBody, dietPref,
          fitnessLevel, workoutLocation, trainingFreq, workoutDurationPref,
          targetWeight, heightUnit, weightUnit, sugarFreq, waterIntake,
          additionalGoals, pushupsLevel, pullupsLevel, allergiesInput,
          medicalConditionsInput, injuriesInput,
        },
      }).catch(() => {}); // non-blocking; failures are silent
      if (autoGoResults) setStage("results");
    } catch (e) {
      setPlan(null);
      setPlanMsg(`Error: ${e.message}`);
    } finally {
      setIsPlanning(false);
    }
  }

  async function handleDietChat() {
    const message = dietChatInput.trim();
    if (!message) return;
    if (!plan) {
      setDietChatMsg("Generate a plan first.");
      return;
    }

    const activePlanSlice = getPlanSliceForDate(plan, selectedPlanDate);

    setIsDietChatting(true);
    setDietChatMsg("");
    setDietChatMessages((prev) => [...prev, { role: "user", text: message }]);
    setDietChatInput("");

    try {
      const payload = {
        profile: {
          age: +age,
          sex,
          height_cm: +height,
          weight_kg: +weight,
          activity_level: activity,
        },
        goal: { type: goalType, deficit_kcal: +deficit },
      };

      const dietData = await api.dietChat({
        message,
        current_plan: {
          user_id: plan?.user_id || userId || "anon",
          meals: activePlanSlice.meals,
          workouts: activePlanSlice.workouts,
        },
        selected_date: activePlanSlice.activeDate || selectedPlanDate || undefined,
        profile: payload.profile,
        goal: payload.goal,
        chat_history: dietChatMessages,
      });

      const nextPlan = dietData?.updated_plan || plan;
      const exerciseData = await api.exerciseChat({
        message,
        current_plan: {
          user_id: nextPlan?.user_id || userId || "anon",
          meals: getPlanSliceForDate(nextPlan, activePlanSlice.activeDate || selectedPlanDate).meals,
          workouts: getPlanSliceForDate(nextPlan, activePlanSlice.activeDate || selectedPlanDate).workouts,
        },
        selected_date: activePlanSlice.activeDate || selectedPlanDate || undefined,
        profile: payload.profile,
        goal: payload.goal,
        chat_history: [
          ...dietChatMessages,
          { role: "user", text: message },
        ],
      });

      const updatedPlan = exerciseData?.updated_plan || nextPlan;
      const nextCalendar = exerciseData?.calendar || dietData?.calendar || null;
      setPlan(updatedPlan);
      setSelectedPlanDate(getActivePlanDate(updatedPlan, activePlanSlice.activeDate || selectedPlanDate));
      cachePlan(updatedPlan);
      setCalendar(nextCalendar);
      if (nextCalendar) cacheCalendar(nextCalendar);
      setCalendarMsg("");

      setDietChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: combineAssistantReplies(
            dietData?.assistant_reply,
            exerciseData?.assistant_reply,
          ),
        },
      ]);
    } catch (e) {
      setDietChatMsg(`Error: ${e.message}`);
    } finally {
      setIsDietChatting(false);
    }
  }

  // ------- Calendar -------
  const [calendar, setCalendar] = useState(getCachedCalendar());
  const [calendarMsg, setCalendarMsg] = useState("");
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

  useEffect(() => {
    if (stage !== "results" || !userId?.trim()) return;

    let cancelled = false;
    api
      .getCalendar()
      .then(async (data) => {
        if (cancelled) return;
        const events = Array.isArray(data?.events) ? data.events : [];
        const nextCalendar =
          events.length === 0 && plan ? await api.syncCalendar(plan) : data;
        if (cancelled) return;
        setCalendar(nextCalendar);
        cacheCalendar(nextCalendar);
        setCalendarMsg("");
      })
      .catch((e) => {
        if (cancelled) return;
        setCalendar(null);
        setCalendarMsg(`Error: ${e.message}`);
      });

    return () => {
      cancelled = true;
    };
  }, [stage, userId]);

  useEffect(() => {
    if (stage !== "results" || !currentUser) return;

    let cancelled = false;
    api
      .getGoogleCalendarStatus()
      .then(async (data) => {
        if (cancelled) return;
        const nextStatus = {
          enabled: Boolean(data?.enabled),
          connected: Boolean(data?.connected),
        };
        setGoogleCalendar(nextStatus);
        if (nextStatus.connected) {
          setGoogleCalendarMsg("");
          try {
            const nextCalendar = await api.syncCalendar(plan || null);
            if (cancelled) return;
            setCalendar(nextCalendar);
            cacheCalendar(nextCalendar);
            setCalendarMsg("");
            const googleMsg = describeGoogleCalendarSync(nextCalendar);
            if (googleMsg) setGoogleCalendarMsg(googleMsg);
          } catch (e) {
            if (cancelled) return;
            setCalendarMsg(`Error: ${e.message}`);
          }
        }
      })
      .catch(() => {
        if (cancelled) return;
        setGoogleCalendar({ enabled: false, connected: false });
      });

    return () => {
      cancelled = true;
    };
  }, [stage, currentUser, plan]);

  async function handleGoogleCalendarConnect() {
    if (!currentUser) {
      setGoogleCalendarMsg("Log in first to connect Google Calendar.");
      return;
    }

    setIsGoogleCalendarBusy(true);
    setGoogleCalendarMsg("");
    try {
      const data = await api.startGoogleCalendarConnect();
      if (!data?.auth_url) throw new Error("Missing Google auth URL.");
      window.location.href = data.auth_url;
    } catch (e) {
      setGoogleCalendarMsg(`Error: ${e.message}`);
      setIsGoogleCalendarBusy(false);
    }
  }

  async function handleGoogleCalendarDisconnect() {
    setIsGoogleCalendarBusy(true);
    setGoogleCalendarMsg("");
    try {
      await api.disconnectGoogleCalendar();
      setGoogleCalendar({ enabled: true, connected: false });
      setGoogleCalendarMsg("Google Calendar disconnected.");
    } catch (e) {
      setGoogleCalendarMsg(`Error: ${e.message}`);
    } finally {
      setIsGoogleCalendarBusy(false);
    }
  }

  // ------- Nudge -------
  const [nudgeMsg, setNudgeMsg] = useState("");
  const [nudgeAutomationEnabled, setNudgeAutomationEnabled] = useState(false);
  const [nudgeSendTime, setNudgeSendTime] = useState("08:00");
  const [nudgeTimezone, setNudgeTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [isSavingNudgeSettings, setIsSavingNudgeSettings] = useState(false);

  // ------- Feedback -------
  const [eventId, setEventId] = useState("");
  const [rating, setRating] = useState(5);
  const [reason, setReason] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("completed");
  const [feedbackOut, setFeedbackOut] = useState("");
  const [isFeedback, setIsFeedback] = useState(false);
  const [progressWeight, setProgressWeight] = useState(currentWeight || weight || "");
  const [mealAdherence, setMealAdherence] = useState(80);
  const [workoutAdherence, setWorkoutAdherence] = useState(80);
  const [energyLevel, setEnergyLevel] = useState(3);
  const [progressNotes, setProgressNotes] = useState("");
  const [progressHistory, setProgressHistory] = useState([]);
  const [weeklyLock, setWeeklyLock] = useState(null);
  const [weeklyUpdate, setWeeklyUpdate] = useState(null);
  const [progressMsg, setProgressMsg] = useState("");
  const [isProgressBusy, setIsProgressBusy] = useState(false);

  useEffect(() => {
    if (stage !== "results" || !userId?.trim()) return;

    let cancelled = false;
    api
      .getProgress()
      .then((data) => {
        if (cancelled) return;
        setProgressHistory(Array.isArray(data?.checkins) ? data.checkins : []);
        setWeeklyLock(data?.weekly_lock || null);
        setWeeklyUpdate(data?.weekly_update || null);
      })
      .catch(() => {
        if (!cancelled) {
          setProgressHistory([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [stage, userId]);

  async function handleFeedback() {
    setIsFeedback(true);
    setFeedbackOut("");
    try {
      if (!eventId.trim()) throw new Error("Event ID is required.");
      const r = feedbackRatingForStatus(feedbackStatus);
      const reasonPrefix = feedbackReasonPrefix(feedbackStatus);
      const cleanReason = reason?.trim();
      const finalReason = cleanReason ? `${reasonPrefix}: ${cleanReason}` : reasonPrefix;

      const data = await api.submitFeedback({
        event_id: eventId.trim(),
        rating: r,
        reason: finalReason,
      });

      setRating(r);
      setFeedbackOut(
        data?.ok
          ? "Check-in saved. We will use this to improve future plans and reminders."
          : "Feedback submitted.",
      );
    } catch (e) {
      setFeedbackOut(`Error: ${e.message}`);
    } finally {
      setIsFeedback(false);
    }
  }

  const coachToolFeedbackItems = useMemo(() => {
    const events = Array.isArray(calendar?.events) ? calendar.events : [];
    const today = todayIsoLocal();
    return events.filter(
      (item) =>
        item?.id &&
        (item?.type === "meal" || item?.type === "workout") &&
        String(item?.starts_at || "").startsWith(today),
    );
  }, [calendar]);

  const selectedFeedbackItem = useMemo(
    () => coachToolFeedbackItems.find((item) => item.id === eventId) || null,
    [coachToolFeedbackItems, eventId],
  );

  function startQuiz() {
    if (!currentUser) {
      setCheckUserMsg("Create an account or log in to continue.");
      return;
    }
    if (isReadOnlyClientView) {
      setCheckUserMsg("Only the client can edit their profile or generate a plan.");
      return;
    }
    setStage("quiz");
    setStep(ACTIVE_QUIZ_STEPS[0]);
    setPlanMsg("");
    setCheckUserMsg("");
  }

  async function handleProgressCheckIn() {
    setIsProgressBusy(true);
    setProgressMsg("");
    try {
      const weightKg = toMetricWeight(progressWeight || currentWeight || weight, weightUnit);
      if (!weightKg) throw new Error("Enter a valid weight.");

      const data = await api.submitProgressCheckIn({
        weight_kg: weightKg,
        meal_adherence: Number(mealAdherence),
        workout_adherence: Number(workoutAdherence),
        energy_level: Number(energyLevel),
        notes: progressNotes,
      });

      setProgressHistory(Array.isArray(data?.checkins) ? data.checkins : []);
      setWeeklyLock(data?.weekly_lock || null);
      setProgressNotes("");
      setProgressMsg("Progress check-in saved.");
    } catch (e) {
      setProgressMsg(`Error: ${e.message}`);
    } finally {
      setIsProgressBusy(false);
    }
  }

  async function handleWeeklyUpdate() {
    setIsProgressBusy(true);
    setProgressMsg("");
    try {
      const data = await api.generateWeeklyUpdate();
      setWeeklyUpdate(data?.weekly_update || null);
      setProgressMsg("Weekly update generated.");
    } catch (e) {
      setProgressMsg(`Error: ${e.message}`);
    } finally {
      setIsProgressBusy(false);
    }
  }

  function hydrateSavedUser(data) {
    const p = data.profile || {};
    const g = data.goal || {};
    if (p.age) setAge(p.age);
    if (p.sex) {
      setSex(p.sex);
      setGender(p.sex);
    }
    if (p.height_cm) {
      setHeight(p.height_cm);
      setHeightValue(String(p.height_cm));
    }
    if (p.weight_kg) {
      setWeight(p.weight_kg);
      setCurrentWeight(String(p.weight_kg));
    }
    if (p.activity_level) setActivity(p.activity_level);
    if (g.type) {
      setGoalType(g.type);
      setGoalPick(g.type);
    }
    if (g.deficit_kcal != null) setDeficit(g.deficit_kcal);
    if (data.plan) {
      setPlan(data.plan);
      cachePlan(data.plan);
    } else {
      setPlan(null);
    }
    if (data.calendar) {
      setCalendar(data.calendar);
      cacheCalendar(data.calendar);
    }
  }

  async function loadAccountData(uid, { quiet = false, targetStage = null } = {}) {
    if (!uid) return;
    setIsCheckingUser(true);
    if (!quiet) setCheckUserMsg("");
    try {
      setUserId(uid);
      saveSettings({ userId: uid });
      const data = await api.checkUser(uid);
      const isManagedClientView =
        currentUser?.role === "dietitian" && uid !== currentUser.user_id;
      if (data.exists) {
        hydrateSavedUser(data);
        setViewedAccount(data.account || null);
        if (targetStage) {
          setStage(targetStage);
        } else {
          setStage(isManagedClientView ? "results" : data.plan ? "results" : "quiz");
        }
      } else {
        setViewedAccount(data.account || null);
        setPlan(null);
        setCalendar(null);
        if (isManagedClientView) {
          setStage("results");
          setCheckUserMsg("This client has not created a profile or plan yet. Only the client can do that from their own account.");
        } else {
          if (targetStage) {
            setStage(targetStage);
          } else {
            startQuiz();
          }
        }
      }
    } catch (e) {
      setCheckUserMsg(`Error: ${e.message}`);
    } finally {
      setIsCheckingUser(false);
    }
  }

  async function loadDietitianClients({ quiet = true, account = null } = {}) {
    const effectiveAccount = account || currentUser;
    if (effectiveAccount?.role !== "dietitian") {
      setManagedClients([]);
      return;
    }
    if (!quiet) setClientMsg("");
    try {
      const data = await api.listDietitianClients();
      setManagedClients(Array.isArray(data?.clients) ? data.clients : []);
    } catch (e) {
      if (!quiet) setClientMsg(`Error: ${e.message}`);
    }
  }

  useEffect(() => {
    if (stage !== "coachTools" || !currentUser || currentUser.role === "dietitian") return;
    let cancelled = false;
    api
      .getNudgeSettings()
      .then((data) => {
        if (cancelled) return;
        const settings = data?.settings || {};
        setNudgeAutomationEnabled(Boolean(settings.enabled));
        setNudgeSendTime(settings.send_time || "08:00");
        setNudgeTimezone(settings.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [stage, currentUser]);

  async function handleSaveNudgeAutomation() {
    setIsSavingNudgeSettings(true);
    setNudgeMsg("");
    try {
      const data = await api.saveNudgeSettings({
        enabled: nudgeAutomationEnabled,
        send_time: nudgeSendTime,
        timezone: nudgeTimezone,
      });
      const settings = data?.settings || {};
      setNudgeAutomationEnabled(Boolean(settings.enabled));
      setNudgeSendTime(settings.send_time || "08:00");
      setNudgeTimezone(settings.timezone || nudgeTimezone);
      setNudgeMsg(
        settings.enabled
          ? `Automatic email nudges are enabled for ${settings.send_time} (${settings.timezone}). No email is sent right away when you save this. The next email is sent by the first scheduled runner that checks after that time.`
          : "Automatic email nudges are disabled.",
      );
    } catch (e) {
      setNudgeMsg(`Error: ${e.message}`);
    } finally {
      setIsSavingNudgeSettings(false);
    }
  }

  function nextStep() {
    setStep((current) => {
      const idx = ACTIVE_QUIZ_STEPS.indexOf(current);
      if (idx === -1) return ACTIVE_QUIZ_STEPS[0];
      return ACTIVE_QUIZ_STEPS[Math.min(idx + 1, ACTIVE_QUIZ_STEPS.length - 1)];
    });
  }

  function prevStep() {
    setStep((current) => {
      const idx = ACTIVE_QUIZ_STEPS.indexOf(current);
      if (idx <= 0) return ACTIVE_QUIZ_STEPS[0];
      return ACTIVE_QUIZ_STEPS[idx - 1];
    });
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setIsAuthenticating(true);
    setCheckUserMsg("");

    try {
      if (authMode === "forgot") {
        if (!authEmail.trim()) throw new Error("Email is required.");
        const response = await api.forgotPassword({ email: authEmail.trim() });
        setCheckUserMsg(response.message || "If an account exists, a reset email has been sent.");
        setAuthMode("login");
        return;
      }

      if (authMode === "reset") {
        if (!resetToken.trim()) throw new Error("Reset token is missing.");
        if (!authPassword.trim() || authPassword.trim().length < 8) {
          throw new Error("New password must be at least 8 characters.");
        }
        if (authPassword !== authPasswordConfirm) {
          throw new Error("Passwords do not match.");
        }
        const response = await api.resetPassword({
          token: resetToken.trim(),
          new_password: authPassword,
        });
        saveAuthSession({ token: response.token, user: response.user });
        setCurrentUser(response.user);
      setViewedAccount(response.user);
      setUserId(response.user.user_id);
      setAuthEmail(response.user.email || authEmail.trim());
      setAuthName(response.user.display_name || authName.trim());
      setAuthPassword("");
      setAuthPasswordConfirm("");
      setResetToken("");
      setAuthRole(response.user.role || authRole);
      if (response.user.role === "dietitian") {
        await loadDietitianClients({ quiet: true, account: response.user });
      } else {
        setManagedClients([]);
      }
      setCheckUserMsg("Password reset successfully.");
      await loadAccountData(response.user.user_id, {
        quiet: true,
        targetStage: homeStageFor(response.user),
      });
        return;
      }

      if (!authEmail.trim()) throw new Error("Email is required.");
      if (!authPassword.trim()) throw new Error("Password is required.");
      if (authMode === "signup" && authPassword.trim().length < 8) {
        throw new Error("Password must be at least 8 characters.");
      }
      if (authMode === "signup" && authPassword !== authPasswordConfirm) {
        throw new Error("Passwords do not match.");
      }

      const response =
        authMode === "signup"
          ? await api.signup({
              display_name: authName.trim(),
              email: authEmail.trim(),
              password: authPassword,
              role: authRole,
            })
          : await api.login({
              email: authEmail.trim(),
              password: authPassword,
            });

      saveAuthSession({ token: response.token, user: response.user });
      setCurrentUser(response.user);
      setViewedAccount(response.user);
      setUserId(response.user.user_id);
      setAuthEmail(response.user.email || authEmail.trim());
      setAuthName(response.user.display_name || authName.trim());
      setAuthPassword("");
      setAuthPasswordConfirm("");
      setAuthRole(response.user.role || authRole);
      if (response.user.role === "dietitian") {
        await loadDietitianClients({ quiet: true, account: response.user });
      } else {
        setManagedClients([]);
      }
      await loadAccountData(response.user.user_id, {
        quiet: true,
        targetStage: homeStageFor(response.user),
      });
    } catch (e) {
      setCheckUserMsg(`Error: ${e.message}`);
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      // ignore logout network failures and clear local session anyway
    }
    clearAuthSession();
    setCurrentUser(null);
    setViewedAccount(null);
    setUserId("");
    setAuthPassword("");
    setAuthPasswordConfirm("");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmNewPassword("");
    setChangePasswordMsg("");
    setManagedClients([]);
    setClientMsg("");
    setActiveChatPartner(null);
    setPrivateMessages([]);
    setPrivateChatInput("");
    setPrivateChatMsg("");
    setPlan(null);
    setStage("auth");
    setCheckUserMsg("");
  }

  async function handleChangePassword(event) {
    event.preventDefault();
    setIsChangingPassword(true);
    setChangePasswordMsg("");

    try {
      if (!currentPassword.trim()) throw new Error("Current password is required.");
      if (!newPassword.trim() || newPassword.trim().length < 8) {
        throw new Error("New password must be at least 8 characters.");
      }
      if (newPassword !== confirmNewPassword) {
        throw new Error("New passwords do not match.");
      }

      const response = await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      saveAuthSession({ token: response.token, user: response.user });
      setCurrentUser(response.user);
      setViewedAccount((prev) =>
        prev?.user_id === response.user.user_id ? response.user : prev,
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
      setShowChangePasswordForm(false);
      setChangePasswordMsg(response.message || "Password updated successfully.");
    } catch (e) {
      setChangePasswordMsg(`Error: ${e.message}`);
    } finally {
      setIsChangingPassword(false);
    }
  }

  useEffect(() => {
    const token = initialSettings.authToken;
    if (!token) {
      setIsRestoringSession(false);
      return;
    }

    let cancelled = false;
    api
      .me()
      .then(async (res) => {
        if (cancelled) return;
        saveAuthSession({ token, user: res.user });
        setCurrentUser(res.user);
        setViewedAccount(res.user);
        setUserId(res.user.user_id);
        setAuthEmail(res.user.email || "");
        setAuthName(res.user.display_name || "");
        setAuthRole(res.user.role || "user");
        if (res.user.role === "dietitian") {
          loadDietitianClients({ quiet: true, account: res.user }).catch(() => {});
        }
        const data = await api.checkUser(res.user.user_id);
        if (cancelled) return;
        if (data.exists) {
          hydrateSavedUser(data);
          setViewedAccount(data.account || res.user);
          setStage(homeStageFor(res.user));
        } else {
          setStage(homeStageFor(res.user));
          setStep(ACTIVE_QUIZ_STEPS[0]);
          setPlanMsg("");
          setCheckUserMsg("");
        }
      })
      .catch(() => {
        if (cancelled) return;
        clearAuthSession();
        setCurrentUser(null);
        setUserId("");
      })
      .finally(() => {
        if (!cancelled) setIsRestoringSession(false);
      });

    return () => {
      cancelled = true;
    };
  }, [initialSettings.authToken]);

  async function handleCreateClient(event) {
    event.preventDefault();
    setIsCreatingClient(true);
    setClientMsg("");
    try {
      if (!clientEmail.trim()) throw new Error("Client email is required.");
      if (!clientPassword.trim() || clientPassword.trim().length < 8) {
        throw new Error("Client password must be at least 8 characters.");
      }
      const response = await api.createDietitianClient({
        display_name: clientName.trim(),
        email: clientEmail.trim(),
        password: clientPassword,
      });
      setManagedClients((prev) => [...prev, response.client]);
      setClientName("");
      setClientEmail("");
      setClientPassword("");
      setClientMsg("Client account created successfully.");
    } catch (e) {
      setClientMsg(`Error: ${e.message}`);
    } finally {
      setIsCreatingClient(false);
    }
  }

  async function handleUnsubscribeClient(client) {
    if (!client?.user_id) return;
    setClientMsg("");
    try {
      await api.unsubscribeDietitianClient(client.user_id);
      setManagedClients((prev) => prev.filter((entry) => entry.user_id !== client.user_id));
      if (userId === client.user_id) {
        await handleSelectOwnAccount();
      }
      setClientMsg("Client subscription cancelled.");
    } catch (e) {
      setClientMsg(`Error: ${e.message}`);
    }
  }

  async function openPrivateChat(partner, returnStage = null) {
    if (!partner?.user_id) return;
    setActiveChatPartner(partner);
    setPrivateChatReturnStage(
      returnStage || (currentUser?.role === "dietitian" ? "dietitianClients" : "userHome"),
    );
    setPrivateChatInput("");
    setPrivateChatMsg("");
    setPrivateMessages([]);
    setStage("privateChat");
    setIsLoadingPrivateMessages(true);
    try {
      const data = await api.getPrivateMessages(partner.user_id);
      setActiveChatPartner(data?.partner || partner);
      setPrivateMessages(Array.isArray(data?.messages) ? data.messages : []);
    } catch (e) {
      setPrivateChatMsg(`Error: ${e.message}`);
    } finally {
      setIsLoadingPrivateMessages(false);
    }
  }

  async function handleSendPrivateMessage(event) {
    event.preventDefault();
    if (!activeChatPartner?.user_id) return;
    const body = privateChatInput.trim();
    if (!body) {
      setPrivateChatMsg("Write a message first.");
      return;
    }

    setIsSendingPrivateMessage(true);
    setPrivateChatMsg("");
    try {
      const data = await api.sendPrivateMessage(activeChatPartner.user_id, body);
      setPrivateMessages(Array.isArray(data?.messages) ? data.messages : []);
      setActiveChatPartner(data?.partner || activeChatPartner);
      setPrivateChatInput("");
    } catch (e) {
      setPrivateChatMsg(`Error: ${e.message}`);
    } finally {
      setIsSendingPrivateMessage(false);
    }
  }

  useEffect(() => {
    if (stage !== "privateChat" || !currentUser || !activeChatPartner?.user_id) return;

    let cancelled = false;

    const refreshMessages = async ({ quiet = false } = {}) => {
      if (!quiet) setPrivateChatMsg("");
      try {
        const data = await api.getPrivateMessages(activeChatPartner.user_id);
        if (cancelled) return;
        setActiveChatPartner(data?.partner || activeChatPartner);
        setPrivateMessages(Array.isArray(data?.messages) ? data.messages : []);
      } catch (e) {
        if (cancelled || quiet) return;
        setPrivateChatMsg(`Error: ${e.message}`);
      }
    };

    const intervalId = window.setInterval(() => {
      refreshMessages({ quiet: true });
    }, 3000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        refreshMessages({ quiet: true });
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [stage, currentUser, activeChatPartner?.user_id]);

  async function handleSelectManagedClient(client) {
    if (!client?.user_id) return;
    await loadAccountData(client.user_id, { targetStage: "results" });
  }

  async function handleSelectOwnAccount() {
    if (!currentUser?.user_id) return;
    await loadAccountData(currentUser.user_id, { targetStage: homeStageFor(currentUser) });
  }

  const isReadOnlyClientView =
    currentUser?.role === "dietitian" &&
    viewedAccount?.user_id &&
    viewedAccount.user_id !== currentUser.user_id;

  const defaultHomeStage = homeStageFor(currentUser);

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

          <div className="topbar-actions">
            {currentUser ? (
              <button
                className="btn btn-outline-light topbar-action-btn"
                type="button"
                onClick={handleLogout}
              >
                Log Out
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="container py-4">
        {/* AUTH */}
        {stage === "auth" && (
          <div className="row justify-content-center">
            <div className="col-lg-6 col-xl-5">
              <div className="card card-soft h-100">
                <div className="card-body p-4">
                  <div className="results-kicker mb-2 text-center">Health Coach</div>
                  <h2 className="h3 section-title mb-4 text-center">Log In or Sign Up</h2>
                  {currentUser ? (
                    <>
                      <div className="account-summary">
                        <div className="account-summary-label">Signed in as</div>
                        <div className="account-summary-title">
                          {currentUser.display_name || "Health Coach User"}
                        </div>
                        <div className="account-summary-meta">
                          {currentUser.email}
                        </div>
                        <div className="account-summary-meta text-capitalize">
                          Role: {currentUser.role || "user"}
                        </div>
                        {currentUser.role === "user" && currentUser.managed_by ? (
                          <div className="account-summary-meta">
                            Under dietitian:{" "}
                            {currentUser.managed_by.display_name || currentUser.managed_by.email}
                          </div>
                        ) : null}
                        <div className="account-summary-meta">
                          ID: <code className="code-soft">{userId}</code>
                        </div>
                        {currentUser.role === "dietitian" && userId !== currentUser.user_id ? (
                          <div className="account-summary-meta">
                            Viewing client account: {viewedAccount?.display_name || viewedAccount?.email || userId}
                          </div>
                        ) : null}
                      </div>

                      <FieldNote>
                        Your account is ready. Continue to your dashboard.
                      </FieldNote>
                    </>
                  ) : (
                    <>
                      <div className="auth-tabs mb-3">
                        <button
                          type="button"
                          className={`auth-tab ${authMode === "login" || authMode === "forgot" || authMode === "reset" ? "active" : ""}`}
                          onClick={() => {
                            setAuthMode("login");
                            setResetToken("");
                            setAuthPassword("");
                            setAuthPasswordConfirm("");
                          }}
                        >
                          Log In
                        </button>
                        <button
                          type="button"
                          className={`auth-tab ${authMode === "signup" ? "active" : ""}`}
                          onClick={() => {
                            setAuthMode("signup");
                            setResetToken("");
                          }}
                        >
                          Sign Up
                        </button>
                      </div>

                      <form onSubmit={handleAuthSubmit}>
                        {authMode === "signup" ? (
                          <div className="mb-3">
                            <label className="form-label">Name</label>
                            <input
                              className="form-control"
                              value={authName}
                              onChange={(e) => setAuthName(e.target.value)}
                              placeholder="Your name"
                            />
                          </div>
                        ) : null}

                        {authMode === "signup" ? (
                          <div className="mb-3">
                            <label className="form-label">Account Type</label>
                            <select
                              className="form-select"
                              value={authRole}
                              onChange={(e) => setAuthRole(e.target.value)}
                            >
                              <option value="user">Single User</option>
                              <option value="dietitian">Dietitian</option>
                            </select>
                          </div>
                        ) : null}

                        <div className="mb-3">
                          <label className="form-label">Email</label>
                          <input
                            className="form-control"
                            type="email"
                            value={authEmail}
                            onChange={(e) => setAuthEmail(e.target.value)}
                            placeholder="name@example.com"
                            disabled={authMode === "reset"}
                          />
                        </div>

                        {authMode !== "forgot" ? (
                          <div>
                            <label className="form-label">
                              {authMode === "reset" ? "New Password" : "Password"}
                            </label>
                            <input
                              className="form-control"
                              type="password"
                              value={authPassword}
                              onChange={(e) => setAuthPassword(e.target.value)}
                              placeholder="At least 8 characters"
                            />
                          </div>
                        ) : null}

                        {authMode === "signup" || authMode === "reset" ? (
                          <div className="mt-3">
                            <label className="form-label">Confirm Password</label>
                            <input
                              className="form-control"
                              type="password"
                              value={authPasswordConfirm}
                              onChange={(e) => setAuthPasswordConfirm(e.target.value)}
                              placeholder="Repeat your password"
                            />
                          </div>
                        ) : null}

                        <FieldNote>
                          {authMode === "signup"
                            ? authRole === "dietitian"
                              ? "Create a dietitian account to manage client accounts and plan on their behalf."
                              : "Create one account and your profile and plan stay attached to it."
                            : authMode === "forgot"
                              ? "Enter your email and we will send a password reset link if the account exists."
                              : authMode === "reset"
                                ? "Create a new password to finish resetting your account."
                            : "Log in to continue with your saved progress and latest plan."}
                        </FieldNote>

                        <div className="mt-4">
                          <button
                            className="btn btn-primary w-100"
                            type="submit"
                            disabled={isAuthenticating || isRestoringSession}
                          >
                            {isAuthenticating ? (
                              <Spinner
                                label={
                                  authMode === "signup"
                                    ? "Creating account..."
                                    : authMode === "forgot"
                                      ? "Sending reset link..."
                                      : authMode === "reset"
                                        ? "Resetting password..."
                                        : "Logging in..."
                                }
                              />
                            ) : authMode === "signup" ? "Create Account" : authMode === "forgot" ? "Send Reset Link" : authMode === "reset" ? "Reset Password" : "Log In"}
                          </button>
                        </div>

                        {authMode === "login" ? (
                          <div className="mt-3 text-center">
                            <button
                              type="button"
                              className="btn btn-link p-0 auth-link"
                              onClick={() => {
                                setAuthMode("forgot");
                                setAuthPassword("");
                                setAuthPasswordConfirm("");
                                setCheckUserMsg("");
                              }}
                            >
                              Forgot password?
                            </button>
                          </div>
                        ) : null}

                        {(authMode === "forgot" || authMode === "reset") ? (
                          <div className="mt-3 text-center">
                            <button
                              type="button"
                              className="btn btn-link p-0 auth-link"
                              onClick={() => {
                                setAuthMode("login");
                                setResetToken("");
                                setAuthPassword("");
                                setAuthPasswordConfirm("");
                              }}
                            >
                              Back to log in
                            </button>
                          </div>
                        ) : null}
                      </form>
                    </>
                  )}

                  <div className="mt-4">
                    <div className="account-benefits">
                      <div className="fw-semibold mb-1">What you will get</div>
                      <ul className="mb-0 small text-muted">
                        <li>Daily calorie and macro summary when available</li>
                        <li>Meal and workout timing suggestions</li>
                        <li>One-click scheduling and motivational nudges</li>
                      </ul>
                    </div>
                  </div>

                  {checkUserMsg && (
                    <div className="alert alert-warning mt-3 mb-0 small">{checkUserMsg}</div>
                  )}

                  {currentUser ? (
                    <div className="mt-4">
                      <button
                        className="btn btn-primary w-100"
                        onClick={() => setStage(homeStageFor(currentUser))}
                        disabled={isCheckingUser || isRestoringSession}
                      >
                        {isCheckingUser ? <Spinner label="Loading account..." /> : "Continue"}
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* USER HOME */}
        {stage === "userHome" && currentUser?.role !== "dietitian" && (
          <div className="row g-4">
            <div className="col-lg-7">
              <div className="card card-soft h-100">
                <div className="card-body p-4 p-md-5">
                  <div className="results-kicker">Welcome Back</div>
                  <h1 className="results-title mb-3">
                    {currentUser?.display_name || "Your health dashboard"}
                  </h1>
                  <p className="text-muted mb-4">
                    Set up your plan, review your saved schedule, and keep your meals and workouts on track.
                  </p>

                  <div className="results-summary">
                    <div className="summary-card">
                      <div className="summary-label">Meals</div>
                      <div className="summary-value">{Array.isArray(plan?.meals) ? plan.meals.length : 0}</div>
                      <div className="summary-meta">{plan ? "Current saved plan" : "No plan yet"}</div>
                    </div>
                    <div className="summary-card">
                      <div className="summary-label">Workouts</div>
                      <div className="summary-value">{Array.isArray(plan?.workouts) ? plan.workouts.length : 0}</div>
                      <div className="summary-meta">{plan ? "Ready to review" : "Create your first plan"}</div>
                    </div>
                  </div>

                  <div className="d-flex flex-wrap gap-3 mt-4">
                    <button className="btn btn-primary btn-lg fw-bold" type="button" onClick={startQuiz}>
                      {plan ? "Update My Plan Setup" : "Start My Plan"}
                    </button>
                    <button
                      className="btn btn-outline-light btn-lg"
                      type="button"
                      onClick={() => setStage("results")}
                      disabled={!plan}
                    >
                      View My Plan
                    </button>
                    <button
                      className="btn btn-outline-light btn-lg"
                      type="button"
                      onClick={() => setStage("coachTools")}
                    >
                      Coach Tools
                    </button>
                    {currentUser?.managed_by ? (
                      <button
                        className="btn btn-outline-light btn-lg"
                        type="button"
                        onClick={() => openPrivateChat(currentUser.managed_by, "userHome")}
                      >
                        Chat with Dietitian
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>

            <div className="col-lg-5">
              <div className="card card-soft h-100">
                <div className="card-body p-4">
                  <h2 className="h5 section-title mb-3">Account</h2>
                  <div className="account-summary">
                    <div className="account-summary-label">Signed in as</div>
                    <div className="account-summary-title">
                      {currentUser.display_name || "Health Coach User"}
                    </div>
                    <div className="account-summary-meta">{currentUser.email}</div>
                    <div className="account-summary-meta text-capitalize">
                      Role: {currentUser.role || "user"}
                    </div>
                    {currentUser.managed_by ? (
                      <div className="account-summary-meta">
                        Under dietitian: {currentUser.managed_by.display_name || currentUser.managed_by.email}
                      </div>
                    ) : null}
                  </div>

                  <FieldNote>
                    {plan
                      ? "Your last saved plan is ready. Open it to review meals, workouts, calendar sync, and edits."
                      : "You do not have a saved plan yet. Start your plan setup to create one."}
                  </FieldNote>

                  {currentUser.managed_by ? (
                    <div className="mt-3">
                      <button
                        className="btn btn-outline-light w-100"
                        type="button"
                        onClick={() => openPrivateChat(currentUser.managed_by, "userHome")}
                      >
                        Message {displayAccountName(currentUser.managed_by)}
                      </button>
                    </div>
                  ) : null}

                  <div className="security-panel mt-4">
                    <div className="fw-semibold mb-2">Security</div>
                    {!showChangePasswordForm ? (
                      <button
                        className="btn btn-outline-light w-100"
                        type="button"
                        onClick={() => {
                          setShowChangePasswordForm(true);
                          setChangePasswordMsg("");
                        }}
                      >
                        Change Password
                      </button>
                    ) : (
                      <form onSubmit={handleChangePassword}>
                        <div className="mb-3">
                          <label className="form-label">Current Password</label>
                          <input
                            className="form-control"
                            type="password"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            placeholder="Current password"
                          />
                        </div>
                        <div className="mb-3">
                          <label className="form-label">New Password</label>
                          <input
                            className="form-control"
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            placeholder="At least 8 characters"
                          />
                        </div>
                        <div className="mb-3">
                          <label className="form-label">Confirm New Password</label>
                          <input
                            className="form-control"
                            type="password"
                            value={confirmNewPassword}
                            onChange={(e) => setConfirmNewPassword(e.target.value)}
                            placeholder="Repeat new password"
                          />
                        </div>
                        <div className="d-flex gap-2">
                          <button className="btn btn-outline-light flex-grow-1" type="submit" disabled={isChangingPassword}>
                            {isChangingPassword ? <Spinner label="Updating..." /> : "Save New Password"}
                          </button>
                          <button
                            className="btn btn-outline-light"
                            type="button"
                            onClick={() => {
                              setShowChangePasswordForm(false);
                              setCurrentPassword("");
                              setNewPassword("");
                              setConfirmNewPassword("");
                              setChangePasswordMsg("");
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    )}
                    {changePasswordMsg ? (
                      <div className={`alert ${String(changePasswordMsg).startsWith("Error:") ? "alert-warning" : "alert-success"} mt-3 mb-0 small`}>
                        {changePasswordMsg}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DIETITIAN HOME */}
        {stage === "dietitianHome" && currentUser?.role === "dietitian" && (
          <div className="row g-4">
            <div className="col-lg-8">
              <div className="card card-soft">
                <div className="card-body p-4 p-md-5">
                  <div className="results-kicker">Dietitian Dashboard</div>
                  <h1 className="results-title mb-3">
                    Manage your subscribed clients
                  </h1>
                  <p className="text-muted mb-4">
                    Choose what you want to do next. Client plans can be viewed here, but only each client can create or change their own plan.
                  </p>

                  <div className="results-summary">
                    <button type="button" className="summary-card text-start" onClick={() => setStage("dietitianCreate")}>
                      <div className="summary-label">Create User</div>
                      <div className="summary-value">+</div>
                      <div className="summary-meta">Create a new client account under your subscription.</div>
                    </button>

                    <button type="button" className="summary-card text-start" onClick={() => setStage("dietitianClients")}>
                      <div className="summary-label">View Users</div>
                      <div className="summary-value">{managedClients.length}</div>
                      <div className="summary-meta">Open a subscribed client and review their saved plan.</div>
                    </button>

                    <button type="button" className="summary-card text-start" onClick={() => setStage("dietitianClients")}>
                      <div className="summary-label">Cancel Subscription</div>
                      <div className="summary-value">-</div>
                      <div className="summary-meta">Remove a client from your managed subscription list.</div>
                    </button>

                    <button type="button" className="summary-card text-start" onClick={() => setStage("dietitianClients")}>
                      <div className="summary-label">Private Chats</div>
                      <div className="summary-value">{managedClients.length}</div>
                      <div className="summary-meta">Open a private conversation with any subscribed client.</div>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="col-lg-4">
              <div className="card card-soft h-100">
                <div className="card-body p-4">
                  <h2 className="h5 section-title mb-3">Security</h2>
                  <div className="account-summary mb-3">
                    <div className="account-summary-label">Signed in as</div>
                    <div className="account-summary-title">
                      {currentUser.display_name || "Dietitian"}
                    </div>
                    <div className="account-summary-meta">{currentUser.email}</div>
                  </div>
                  {!showChangePasswordForm ? (
                    <button
                      className="btn btn-outline-light w-100"
                      type="button"
                      onClick={() => {
                        setShowChangePasswordForm(true);
                        setChangePasswordMsg("");
                      }}
                    >
                      Change Password
                    </button>
                  ) : (
                    <form onSubmit={handleChangePassword}>
                      <div className="mb-3">
                        <label className="form-label">Current Password</label>
                        <input
                          className="form-control"
                          type="password"
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          placeholder="Current password"
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">New Password</label>
                        <input
                          className="form-control"
                          type="password"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder="At least 8 characters"
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">Confirm New Password</label>
                        <input
                          className="form-control"
                          type="password"
                          value={confirmNewPassword}
                          onChange={(e) => setConfirmNewPassword(e.target.value)}
                          placeholder="Repeat new password"
                        />
                      </div>
                      <div className="d-flex gap-2">
                        <button className="btn btn-outline-light flex-grow-1" type="submit" disabled={isChangingPassword}>
                          {isChangingPassword ? <Spinner label="Updating..." /> : "Save New Password"}
                        </button>
                        <button
                          className="btn btn-outline-light"
                          type="button"
                          onClick={() => {
                            setShowChangePasswordForm(false);
                            setCurrentPassword("");
                            setNewPassword("");
                            setConfirmNewPassword("");
                            setChangePasswordMsg("");
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                  {changePasswordMsg ? (
                    <div className={`alert ${String(changePasswordMsg).startsWith("Error:") ? "alert-warning" : "alert-success"} mt-3 mb-0 small`}>
                      {changePasswordMsg}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DIETITIAN CREATE */}
        {stage === "dietitianCreate" && currentUser?.role === "dietitian" && (
          <div className="row justify-content-center">
            <div className="col-lg-7">
              <div className="card card-soft">
                <div className="card-body p-4 p-md-5">
                  <div className="results-kicker">Dietitian Dashboard</div>
                  <h2 className="section-title mb-3">Create Client Account</h2>
                  <p className="text-muted mb-4">
                    Create a client login that will appear under your subscription list.
                  </p>

                  <form onSubmit={handleCreateClient}>
                    <div className="mb-3">
                      <label className="form-label">Client Name</label>
                      <input
                        className="form-control"
                        value={clientName}
                        onChange={(e) => setClientName(e.target.value)}
                        placeholder="Client name"
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label">Client Email</label>
                      <input
                        className="form-control"
                        type="email"
                        value={clientEmail}
                        onChange={(e) => setClientEmail(e.target.value)}
                        placeholder="client@example.com"
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label">Temporary Password</label>
                      <input
                        className="form-control"
                        type="password"
                        value={clientPassword}
                        onChange={(e) => setClientPassword(e.target.value)}
                        placeholder="Temporary password"
                      />
                    </div>
                    <div className="d-flex gap-2">
                      <button className="btn btn-primary fw-bold flex-grow-1" type="submit" disabled={isCreatingClient}>
                        {isCreatingClient ? <Spinner label="Creating client..." /> : "Create Client"}
                      </button>
                      <button className="btn btn-outline-light" type="button" onClick={() => setStage("dietitianHome")}>
                        Back
                      </button>
                    </div>
                  </form>

                  {clientMsg ? <div className="alert alert-warning mt-3 mb-0 small">{clientMsg}</div> : null}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DIETITIAN CLIENTS */}
        {stage === "dietitianClients" && currentUser?.role === "dietitian" && (
          <div className="row justify-content-center">
            <div className="col-lg-9">
              <div className="card card-soft">
                <div className="card-body p-4 p-md-5">
                  <div className="results-kicker">Dietitian Dashboard</div>
                  <h2 className="section-title mb-3">Subscribed Clients</h2>
                  <p className="text-muted mb-4">
                    View saved client plans, open private chats, or cancel a subscription. Clients must log into their own accounts to create or edit plans.
                  </p>

                  <div className="list-group list-group-soft">
                    {managedClients.length === 0 ? (
                      <div className="list-group-item text-muted">No subscribed clients yet.</div>
                    ) : (
                      managedClients.map((client) => (
                        <div key={client.user_id} className="list-group-item">
                          <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
                            <div>
                              <div className="fw-semibold">{client.display_name || "Client account"}</div>
                              <div className="small text-muted">{client.email}</div>
                            </div>
                            <div className="d-flex gap-2">
                              <button
                                type="button"
                                className="btn btn-outline-light btn-sm"
                                onClick={() => handleSelectManagedClient(client)}
                              >
                                View Plan
                              </button>
                              <button
                                type="button"
                                className="btn btn-outline-light btn-sm"
                                onClick={() => openPrivateChat(client, "dietitianClients")}
                              >
                                Open Chat
                              </button>
                              <button
                                type="button"
                                className="btn btn-outline-danger btn-sm"
                                onClick={() => handleUnsubscribeClient(client)}
                              >
                                Cancel Subscription
                              </button>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {clientMsg ? <div className="alert alert-warning mt-3 mb-0 small">{clientMsg}</div> : null}

                  <div className="mt-4">
                    <button className="btn btn-outline-light" type="button" onClick={() => setStage("dietitianHome")}>
                      Back to Dashboard
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* PRIVATE CHAT */}
        {stage === "privateChat" && currentUser && activeChatPartner && (
          <div className="row justify-content-center">
            <div className="col-lg-9 col-xl-8">
              <div className="card card-soft">
                <div className="card-body p-4 p-md-5">
                  <div className="results-kicker">
                    {currentUser.role === "dietitian" ? "Dietitian Chat" : "Private Chat"}
                  </div>
                  <h2 className="section-title mb-3">
                    Chat with {displayAccountName(activeChatPartner)}
                  </h2>
                  <p className="text-muted mb-4">
                    This conversation is private between you and this {currentUser.role === "dietitian" ? "client" : "dietitian"}.
                  </p>

                  <div className="account-summary mb-4">
                    <div className="account-summary-label">
                      {currentUser.role === "dietitian" ? "Client account" : "Dietitian account"}
                    </div>
                    <div className="account-summary-title">
                      {displayAccountName(activeChatPartner)}
                    </div>
                    <div className="account-summary-meta">{activeChatPartner.email}</div>
                  </div>

                  {isLoadingPrivateMessages ? (
                    <div className="chat-empty">Loading conversation...</div>
                  ) : (
                    <div className="chat-shell private-chat-shell mb-3">
                      {privateMessages.length === 0 ? (
                        <div className="chat-empty">
                          No messages yet. Start the conversation here.
                        </div>
                      ) : (
                        privateMessages.map((message) => {
                          const isOwnMessage = message.sender_user_id === currentUser.user_id;
                          return (
                            <div
                              key={`${message.id}-${message.created_at}`}
                              className={`chat-message ${isOwnMessage ? "chat-user" : "chat-assistant"}`}
                            >
                              <div>{message.body}</div>
                              <div className="chat-meta">
                                {isOwnMessage ? "You" : displayAccountName(activeChatPartner)} · {fmtIso(message.created_at)}
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  )}

                  <form onSubmit={handleSendPrivateMessage}>
                    <div className="private-chat-composer">
                      <textarea
                        className="form-control private-chat-input"
                        rows={3}
                        value={privateChatInput}
                        onChange={(e) => setPrivateChatInput(e.target.value)}
                        placeholder={
                          currentUser.role === "dietitian"
                            ? "Write a message for your client..."
                            : "Write a message for your dietitian..."
                        }
                      />
                      <div className="d-flex gap-2 flex-wrap">
                        <button
                          className="btn btn-primary fw-bold"
                          type="submit"
                          disabled={isSendingPrivateMessage || isLoadingPrivateMessages}
                        >
                          {isSendingPrivateMessage ? <Spinner label="Sending..." /> : "Send Message"}
                        </button>
                        <button
                          className="btn btn-outline-light"
                          type="button"
                          onClick={() => {
                            setPrivateChatMsg("");
                            setPrivateChatInput("");
                            setStage(privateChatReturnStage || defaultHomeStage);
                          }}
                        >
                          Back
                        </button>
                      </div>
                    </div>
                  </form>

                  {privateChatMsg ? (
                    <div className="alert alert-warning mt-3 mb-0 small">{privateChatMsg}</div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* COACH TOOLS */}
        {stage === "coachTools" && currentUser?.role !== "dietitian" && (
          <div className="row g-4">
            <div className="col-lg-6">
              <div className="card card-soft">
                <div className="card-body p-4">
                  <h2 className="h5 panel-title mb-3">Motivation</h2>
                  <p className="text-muted mb-3">
                    Daily motivation emails are sent automatically to the account email when the schedule reaches the selected time. The system picks the message style and content from the user's goal, meals, and workout plan.
                  </p>

                  <div className="row g-3">
                    <div className="col-12">
                      <div className="form-check form-switch automation-toggle">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id="auto-nudge-toggle"
                          checked={nudgeAutomationEnabled}
                          onChange={(e) => setNudgeAutomationEnabled(e.target.checked)}
                        />
                        <label className="form-check-label ms-2" htmlFor="auto-nudge-toggle">
                          Enable automatic daily email nudges
                        </label>
                      </div>
                      <div className="automation-note mt-3">
                        Emails are personalized automatically, so there is nothing extra to configure beyond the schedule. Saving this does not send a message immediately.
                      </div>
                    </div>

                    <div className="col-md-6">
                      <label className="form-label">Send Time</label>
                      <input
                        className="form-control"
                        type="time"
                        value={nudgeSendTime}
                        onChange={(e) => setNudgeSendTime(e.target.value)}
                      />
                    </div>

                    <div className="col-md-6">
                      <label className="form-label">Timezone</label>
                      <input
                        className="form-control"
                        value={nudgeTimezone}
                        onChange={(e) => setNudgeTimezone(e.target.value)}
                        placeholder="Asia/Beirut"
                      />
                    </div>
                  </div>

                  <div className="d-flex gap-2 mt-3">
                    <button
                      className="btn btn-primary fw-bold flex-grow-1"
                      type="button"
                      onClick={handleSaveNudgeAutomation}
                      disabled={isSavingNudgeSettings}
                    >
                      {isSavingNudgeSettings ? <Spinner label="Saving..." /> : "Save Automation"}
                    </button>
                  </div>

                  <Alert variant="warning">{nudgeMsg}</Alert>
                </div>
              </div>
            </div>

            <div className="col-lg-6">
              <div className="card card-soft">
                <div className="card-body p-4">
                  <h2 className="h5 panel-title mb-3">Feedback</h2>
                  <p className="text-muted mb-3">
                    Check in on today&apos;s meals and workouts so the system can adapt future plans around what actually works for you.
                  </p>

                  {coachToolFeedbackItems.length === 0 ? (
                    <div className="feedback-empty">
                      No meal or workout items are available yet. Generate a plan first, then come back here to log how the day went.
                    </div>
                  ) : (
                    <>
                      <div className="feedback-section-label">Choose an item</div>
                      <div className="feedback-item-list mb-3">
                        {coachToolFeedbackItems.map((item) => {
                          const selected = eventId === item.id;
                          return (
                            <button
                              key={item.id}
                              type="button"
                              className={`feedback-item-card ${selected ? "active" : ""}`}
                              onClick={() => setEventId(item.id)}
                            >
                              <div className="feedback-item-top">
                                <span className="feedback-item-type">
                                  {item.type === "meal" ? "Meal" : "Workout"}
                                </span>
                                <span className="feedback-item-time">
                                  {fmtIso(item.starts_at || item.when)}
                                </span>
                              </div>
                              <div className="feedback-item-title">
                                {item.title || (item.type === "meal" ? "Meal" : "Workout")}
                              </div>
                            </button>
                          );
                        })}
                      </div>

                      <div className="feedback-section-label">How did it go?</div>
                      <div className="feedback-status-grid mb-3">
                        {[
                          ["completed", "Completed", "I followed the plan"],
                          ["partial", "Partly completed", "I only did some of it"],
                          ["skipped", "Skipped", "I could not do it today"],
                        ].map(([key, title, subtitle]) => (
                          <button
                            key={key}
                            type="button"
                            className={`feedback-status-card ${feedbackStatus === key ? "active" : ""}`}
                            onClick={() => setFeedbackStatus(key)}
                          >
                            <div className="feedback-status-title">{title}</div>
                            <div className="feedback-status-sub">{subtitle}</div>
                          </button>
                        ))}
                      </div>

                      <div className="row g-3">
                        <div className="col-12">
                          <label className="form-label">Optional note</label>
                          <input
                            className="form-control"
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Too busy, felt strong, wanted a different meal, prefer a later workout..."
                          />
                        </div>
                      </div>

                      {selectedFeedbackItem ? (
                        <div className="feedback-selected-note mt-3">
                          You are checking in for <strong>{selectedFeedbackItem.title || "this item"}</strong>.
                        </div>
                      ) : null}
                    </>
                  )}

                  <div className="d-flex gap-2 mt-3">
                    <button
                      className="btn btn-primary fw-bold"
                      type="button"
                      onClick={handleFeedback}
                      disabled={isFeedback || coachToolFeedbackItems.length === 0 || !eventId}
                    >
                      {isFeedback ? <Spinner label="Saving..." /> : "Save Check-In"}
                    </button>
                  </div>

                  <Alert variant={String(feedbackOut).startsWith("Error:") ? "warning" : "success"}>
                    {feedbackOut}
                  </Alert>
                </div>
              </div>
            </div>

            <div className="col-12">
              <button className="btn btn-outline-light" type="button" onClick={() => setStage("userHome")}>
                {"<-"} Back to Dashboard
              </button>
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
              <ProgressPills step={stepPosition} total={TOTAL_STEPS} />{" "}
            </div>

            <div className="card card-soft">
              <div className="card-body p-4 p-md-5">
                {/* Step 0 */}
                {step === 0 && (
                  <>
                    <h3 className="quiz-title">How old are you?</h3>{" "}
                    <div className="quiz-sub">
                      We only ask your age once to personalize calorie and
                      workout targets.{" "}
                    </div>
                    <div className="mt-4">
                      <input
                        type="number"
                        min={14}
                        max={90}
                        className="line-input"
                        value={age}
                        onChange={(e) => setAge(e.target.value)}
                        placeholder="Enter your age"
                      />
                    </div>
                    <div className="d-flex flex-wrap gap-2 mt-3">
                      {[20, 25, 30, 35, 40, 50].map((presetAge) => (
                        <button
                          key={presetAge}
                          type="button"
                          className={`btn btn-outline-light btn-sm ${+age === presetAge ? "active" : ""}`}
                          onClick={() => setAge(presetAge)}
                        >
                          {presetAge}
                        </button>
                      ))}
                    </div>
                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={
                        !Number(age) || Number(age) < 14 || Number(age) > 90
                      }
                    >
                      Continue
                    </button>
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
                          setSex("M");
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
                          setSex("F");
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
                          right={<span className="icon-ph">Diet</span>}
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
                        right={<span className="icon-ph">Low</span>}
                      />
                      <LongSelect
                        title="3–5 times a week"
                        active={sugarFreq === "3_5_week"}
                        onClick={() => {
                          setSugarFreq("3_5_week");
                          nextStep();
                        }}
                        right={<span className="icon-ph">Mid</span>}
                      />
                      <LongSelect
                        title="Pretty much every day"
                        active={sugarFreq === "daily"}
                        onClick={() => {
                          setSugarFreq("daily");
                          nextStep();
                        }}
                        right={<span className="icon-ph">High</span>}
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

                    <button className="btn btn-primary w-100 mt-4" onClick={nextStep}>
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

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                      disabled={!heightValue || toMetricHeight(heightValue, heightUnit) <= 0}
                    >
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
                      {timelineEstimate.targetDate.toDateString()}
                    </h4>

                    <p className="quiz-sub mt-2">
                      Estimated pace:{" "}
                      <strong>
                        {timelineEstimate.weeklyRateKg > 0
                          ? `${timelineEstimate.weeklyRateKg.toFixed(2)} kg/week`
                          : "maintenance"}
                      </strong>
                      {" · "}
                      around <strong>{timelineEstimate.days} days</strong>
                    </p>

                    <FieldNote>{timelineEstimate.summary}</FieldNote>

                    <ProgressCurve
                      startWeight={
                        Number(currentWeight) || Number(weight) || 70
                      }
                      endWeight={
                        Number(targetWeight) ||
                        Number(currentWeight) ||
                        Number(weight) ||
                        70
                      }
                      unit={weightUnit}
                    />

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
                                ? "??"
                                : r === "neutral"
                                  ? "??"
                                  : "??"}
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

                    <button className="btn btn-primary w-100 mt-4" onClick={nextStep}>
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
                        <span className="xMark">x</span>
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
                {step === 28 && (
                  <>
                    <h3 className="quiz-title">
                      Any food allergies or medical conditions?
                    </h3>
                    <p className="quiz-sub">
                      Add anything the plan should avoid or treat with caution.
                    </p>

                    <input
                      className="line-input"
                      placeholder="Allergies, comma separated"
                      value={allergiesInput}
                      onChange={(e) => setAllergiesInput(e.target.value)}
                    />

                    <input
                      className="line-input mt-3"
                      placeholder="Medical conditions, comma separated"
                      value={medicalConditionsInput}
                      onChange={(e) => setMedicalConditionsInput(e.target.value)}
                    />

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={nextStep}
                    >
                      Continue
                    </button>
                  </>
                )}
                {/*Step 29*/}
                {step === 29 && (
                  <>
                    <h3 className="quiz-title">
                      Any injuries or movement limitations?
                    </h3>
                    <p className="quiz-sub">
                      This helps avoid exercises that may not fit your body right now.
                    </p>

                    <input
                      className="line-input"
                      placeholder="Examples: knee, shoulder, back"
                      value={injuriesInput}
                      onChange={(e) => setInjuriesInput(e.target.value)}
                    />

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
                      Your personalized workout plan is ready.
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
                      Your personalized workout plan is ready.
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
                      Your personalized workout plan is ready.
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
                      We respect your privacy and take protecting it seriously.
                      No spam.
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
                    <h3 className="quiz-title">Your current fitness score</h3>
                    <div className="age-pill">
                      {isLoadingFitnessScore ? "..." : fitnessAge || Number(age) || 24} years{" "}
                    </div>

                    <div className="quiz-sub mt-3">
                      Fitness score:{" "}
                      <strong>{isLoadingFitnessScore ? "Calculating..." : fitnessScore ?? "Pending"}</strong>
                    </div>

                    <div className="fitness-copy">
                      {fitnessSummary ? (
                        fitnessSummary.split(/\n\s*\n/).map((paragraph, idx) => (
                          <p key={idx}>{paragraph}</p>
                        ))
                      ) : (
                        <>
                          <p>
                            This score blends your activity level, recent training history, workout preference, recovery habits, and strength markers.
                          </p>
                          <p>
                            As your consistency improves, this score and your projected fitness age should improve with it.
                          </p>
                        </>
                      )}
                    </div>

                    <div className="meter-card">
                      <div className="meter-bar">
                        <span
                          className="meter-pin"
                          style={{ left: `${fitnessMeterPercent}%` }}
                        />
                      </div>
                      <div className="meter-text">
                        {fitnessScore != null
                          ? `Your current fitness baseline is ${fitnessScore}/100 and can improve with plan consistency.`
                          : "Your current fitness baseline can be improved."}
                      </div>
                    </div>

                    <button
                      className="btn btn-primary w-100 mt-4"
                      onClick={() => handlePlanToday({ autoGoResults: true })}
                      disabled={isPlanning}
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
                      step === 0 ? setStage(defaultHomeStage) : prevStep()
                    }
                  >
                    Back
                  </button>

                  {/* {step < TOTAL_STEPS - 1 - (
                    <button
                      className="btn btn-primary fw-bold"
                      onClick={nextStep}
                    >
                      Continue
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
          selectedPlanDate={selectedPlanDate}
          setSelectedPlanDate={setSelectedPlanDate}
          setStage={setStage}
          handleGoHome={() => setStage(isReadOnlyClientView ? "dietitianClients" : defaultHomeStage)}
          isPlanning={isPlanning}
          handlePlanToday={handlePlanToday}
          isReadOnlyClientView={isReadOnlyClientView}
          viewedAccount={viewedAccount}
          eventId={eventId}
          setEventId={setEventId}
          rating={rating}
          setRating={setRating}
          reason={reason}
          setReason={setReason}
          isFeedback={isFeedback}
          handleFeedback={handleFeedback}
          feedbackOut={feedbackOut}
          calendar={calendar}
          calendarMsg={calendarMsg}
          progressWeight={progressWeight}
          setProgressWeight={setProgressWeight}
          mealAdherence={mealAdherence}
          setMealAdherence={setMealAdherence}
          workoutAdherence={workoutAdherence}
          setWorkoutAdherence={setWorkoutAdherence}
          energyLevel={energyLevel}
          setEnergyLevel={setEnergyLevel}
          progressNotes={progressNotes}
          setProgressNotes={setProgressNotes}
          progressHistory={progressHistory}
          weeklyLock={weeklyLock}
          weeklyUpdate={weeklyUpdate}
          progressMsg={progressMsg}
          isProgressBusy={isProgressBusy}
          handleProgressCheckIn={handleProgressCheckIn}
          handleWeeklyUpdate={handleWeeklyUpdate}
          googleCalendar={googleCalendar}
          googleCalendarMsg={googleCalendarMsg}
          isGoogleCalendarBusy={isGoogleCalendarBusy}
          handleGoogleCalendarConnect={handleGoogleCalendarConnect}
          handleGoogleCalendarDisconnect={handleGoogleCalendarDisconnect}
          nudgeMsg={nudgeMsg}
          dietChatInput={dietChatInput}
          setDietChatInput={setDietChatInput}
          dietChatMessages={dietChatMessages}
          isDietChatting={isDietChatting}
          dietChatMsg={dietChatMsg}
          handleDietChat={handleDietChat}
          CalendarView={CalendarView}
          NudgeView={NudgeView}
          Spinner={Spinner}
          Alert={Alert}
          showAdvancedPanels={false}
        />
      </div>

      <footer className="text-center pb-4 pt-4">
        <div className="d-flex justify-content-center flex-wrap gap-3 mb-2">
          <a
            className="text-decoration-none text-muted"
            href="/privacy.html"
            target="_blank"
            rel="noreferrer"
          >
            Privacy Policy
          </a>
          <a
            className="text-decoration-none text-muted"
            href="/terms.html"
            target="_blank"
            rel="noreferrer"
          >
            Terms of Service
          </a>
          <a
            className="text-decoration-none text-muted"
            href="/support.html"
            target="_blank"
            rel="noreferrer"
          >
            Support
          </a>
        </div>
        <small className="text-muted">Done By: Anthony, Chris, Omar, Zaed</small>
      </footer>
    </div>
  );
}
