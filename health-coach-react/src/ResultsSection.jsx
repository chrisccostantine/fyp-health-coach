function sumBy(items, keys) {
  return items.reduce((acc, item) => {
    const value = keys
      .map((key) => Number(item?.[key]))
      .find((num) => Number.isFinite(num));
    return acc + (value || 0);
  }, 0);
}

function cleanTime(value) {
  if (!value) return "Any time";
  if (typeof value === "string" && value.includes("T")) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  }
  return String(value);
}

function describeWorkout(workout) {
  const parts = [];
  const duration = workout?.duration ?? workout?.duration_min;
  const focus = workout?.focus || workout?.type || workout?.category;
  const intensity = workout?.intensity || workout?.level;

  if (Number.isFinite(Number(duration))) parts.push(`${duration} min`);
  if (focus) parts.push(String(focus));
  if (intensity) parts.push(String(intensity));

  return parts.length > 0 ? parts.join(" | ") : "Scheduled workout";
}

export default function ResultsSection({
  stage,
  plan,
  selectedPlanDate,
  setSelectedPlanDate,
  setStage,
  handleGoHome,
  isPlanning,
  handlePlanToday,
  isReadOnlyClientView,
  viewedAccount,

  // feedback
  eventId,
  setEventId,
  rating,
  setRating,
  reason,
  setReason,
  banditArm,
  setBanditArm,
  isFeedback,
  handleFeedback,
  feedbackOut,
  copyFeedback,

  // progress
  progressWeight,
  setProgressWeight,
  mealAdherence,
  setMealAdherence,
  workoutAdherence,
  setWorkoutAdherence,
  energyLevel,
  setEnergyLevel,
  progressNotes,
  setProgressNotes,
  progressHistory,
  weeklyUpdate,
  progressMsg,
  isProgressBusy,
  handleProgressCheckIn,
  handleWeeklyUpdate,

  // calendar
  calendar,
  calendarMsg,
  googleCalendar,
  googleCalendarMsg,
  isGoogleCalendarBusy,
  handleGoogleCalendarConnect,
  handleGoogleCalendarDisconnect,

  // nudge
  tone,
  setTone,
  goalText,
  setGoalText,
  isNudging,
  handleNudge,
  nudgeMsg,
  nudge,

  // diet chat
  dietChatInput,
  setDietChatInput,
  dietChatMessages,
  isDietChatting,
  dietChatMsg,
  handleDietChat,

  // views
  CalendarView,
  NudgeView,
  Spinner,
  Alert,
  showAdvancedPanels = true,
}) {
  if (stage !== "results") return null;

  const Calendar = CalendarView;
  const Nudge = NudgeView;
  const Loading = Spinner;
  const StatusAlert = Alert;

  const planDays = Array.isArray(plan?.plan_days) ? plan.plan_days : [];
  const availableDates = planDays
    .map((day) => String(day?.date || "").trim())
    .filter(Boolean);
  const activeDate =
    availableDates.includes(selectedPlanDate) ? selectedPlanDate : availableDates[0] || "";
  const activeDay =
    planDays.find((day) => String(day?.date || "").trim() === activeDate) || null;
  const meals = activeDay
    ? Array.isArray(activeDay?.meals) ? activeDay.meals : []
    : Array.isArray(plan?.meals) ? plan.meals : [];
  const workouts = activeDay
    ? Array.isArray(activeDay?.workouts) ? activeDay.workouts : []
    : Array.isArray(plan?.workouts) ? plan.workouts : [];
  const chatMessages = Array.isArray(dietChatMessages) ? dietChatMessages : [];
  const totalMealCalories = sumBy(meals, ["kcal", "calories"]);
  const totalWorkoutMinutes = sumBy(workouts, ["duration", "duration_min"]);
  const safety = plan?.safety || {};
  const safetyWarnings = Array.isArray(safety?.warnings) ? safety.warnings : [];
  const safetyDisclaimer = safety?.disclaimer || "";
  const recentProgress = Array.isArray(progressHistory) ? progressHistory.slice(0, 3) : [];
  const activeDateLabel = activeDate
    ? new Date(`${activeDate}T00:00:00`).toLocaleDateString([], {
        weekday: "long",
        month: "short",
        day: "numeric",
      })
    : new Date().toLocaleDateString();
  const calendarForDisplay =
    calendar && activeDate
      ? {
          ...calendar,
          events: Array.isArray(calendar?.events)
            ? calendar.events.filter((event) =>
                String(event?.starts_at || "").startsWith(activeDate),
              )
            : [],
        }
      : calendar;

  return (
    <div className="row g-4">
      <div className="col-lg-8">
        <div className="card card-soft results-shell">
          <div className="card-body p-4 p-md-5">
            <div className="results-header">
              <div>
                <div className="results-kicker">
                  {planDays.length > 0 ? "Monthly plan dashboard" : "Daily plan dashboard"}
                </div>
                <h1 className="results-title">
                  {planDays.length > 0 ? `Your plan for ${activeDateLabel}` : "Your plan for today"}
                </h1>
                <div className="text-muted">
                  {planDays.length > 0
                    ? "Your month is generated once. Pick a day and review only that day's meals and workout."
                    : "Nutrition, training, calendar, and coaching in one view."}
                </div>
                {isReadOnlyClientView && viewedAccount ? (
                  <div className="alert alert-info mt-3 mb-0 small">
                    Viewing {viewedAccount.display_name || viewedAccount.email}'s plan in read-only mode.
                    Only the client account can generate or change this plan.
                  </div>
                ) : null}
                {safetyWarnings.length > 0 ? (
                  <div className="alert alert-warning mt-3 mb-0 small">
                    <div className="fw-semibold mb-1">Safety notes</div>
                    <ul className="mb-0 ps-3">
                      {safetyWarnings.map((warning, idx) => (
                        <li key={idx}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {safetyDisclaimer ? (
                  <div className="alert alert-info mt-3 mb-0 small">
                    {safetyDisclaimer}
                  </div>
                ) : null}
              </div>

              <div className="results-actions">
                <button
                  className="btn btn-outline-light results-action-btn"
                  type="button"
                  onClick={() => setStage("quiz")}
                  disabled={isReadOnlyClientView}
                >
                  Edit Plan Setup
                </button>

                <button
                  className="btn btn-primary fw-bold results-action-btn"
                  type="button"
                  onClick={() => handlePlanToday({ autoGoResults: false })}
                  disabled={isPlanning || isReadOnlyClientView}
                >
                  {isPlanning ? (
                    <Loading label="Refreshing..." />
                  ) : (
                    "Regenerate"
                  )}
                </button>
              </div>
            </div>

            {!plan ? (
              <div className="empty-state mt-4">
                <div className="empty-state-title">No plan generated yet</div>
                <p className="text-muted mb-3">
                  Complete your plan setup to generate a personalized meal and workout
                  plan.
                </p>
                <button
                  className="btn btn-primary fw-bold"
                  type="button"
                  onClick={() => setStage("quiz")}
                  disabled={isReadOnlyClientView}
                >
                  {isReadOnlyClientView ? "Client Must Log In" : "Start My Plan"}
                </button>
              </div>
            ) : (
              <>
                <div className="results-summary">
                  <div className="summary-card">
                    <div className="summary-label">Meals</div>
                    <div className="summary-value">{meals.length}</div>
                    <div className="summary-meta">
                      {totalMealCalories} kcal planned
                    </div>
                  </div>

                  <div className="summary-card">
                    <div className="summary-label">Workouts</div>
                    <div className="summary-value">{workouts.length}</div>
                    <div className="summary-meta">
                      {totalWorkoutMinutes} total minutes
                    </div>
                  </div>

                  <div className="summary-card">
                    <div className="summary-label">{planDays.length > 0 ? "Selected Day" : "Generated"}</div>
                    <div className="summary-value summary-date">
                      {planDays.length > 0 ? activeDateLabel : new Date().toLocaleDateString()}
                    </div>
                    <div className="summary-meta">
                      {planDays.length > 0 ? `${planDays.length} days planned` : "Calendar synced automatically"}
                    </div>
                  </div>
                </div>

                {planDays.length > 0 ? (
                  <section className="results-section">
                    <div className="section-head">
                      <h2 className="section-h">Plan Day</h2>
                      <span className="count-pill">{planDays.length}</span>
                    </div>

                    <div className="results-date-picker">
                      <select
                        className="form-select"
                        value={activeDate}
                        onChange={(e) => setSelectedPlanDate?.(e.target.value)}
                      >
                        {planDays.map((day) => {
                          const value = String(day?.date || "");
                          const label = new Date(`${value}T00:00:00`).toLocaleDateString([], {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          });
                          return (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          );
                        })}
                      </select>
                    </div>
                  </section>
                ) : null}

                {/* Meals */}
                <section className="results-section">
                  <div className="section-head">
                    <h2 className="section-h">Meals</h2>
                    <span className="count-pill">{meals.length}</span>
                  </div>

                  <div className="results-list">
                    {meals.length === 0 ? (
                      <div className="result-item result-empty">
                        No meals in this plan.
                      </div>
                    ) : (
                      meals.map((meal, idx) => (
                        <div key={idx} className="result-item">
                          <div className="result-left">
                            <div className="result-icon" aria-hidden="true">
                              Meal
                            </div>
                            <div>
                              <div className="result-title">
                                {meal.title || meal.name || `Meal ${idx + 1}`}
                              </div>
                              <div className="result-sub">
                                Protein{" "}
                                {meal.protein ?? meal.macros?.protein ?? 0}g | Carbs{" "}
                                {meal.carbs ?? meal.macros?.carbs ?? 0}g | Fat{" "}
                                {meal.fat ?? meal.macros?.fat ?? 0}g |{" "}
                                {meal.kcal ?? meal.calories ?? 0} kcal
                              </div>
                            </div>
                          </div>

                          <span className="time-pill">
                            {cleanTime(meal.time || meal.when)}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </section>

                {/* Workouts */}
                <section className="results-section">
                  <div className="section-head">
                    <h2 className="section-h">Workout</h2>
                    <span className="count-pill">{workouts.length}</span>
                  </div>

                  <div className="results-list">
                    {workouts.length === 0 ? (
                      <div className="result-item result-empty">
                        No workouts in this plan.
                      </div>
                    ) : (
                      workouts.map((w, idx) => (
                        <div key={idx} className="result-item">
                          <div className="result-left">
                            <div className="result-icon" aria-hidden="true">
                              Move
                            </div>
                            <div>
                              <div className="result-title">
                                {w.title || w.name || `Workout ${idx + 1}`}
                              </div>
                              <div className="result-sub">{describeWorkout(w)}</div>
                            </div>
                          </div>

                          <span className="time-pill">
                            {cleanTime(w.time || w.when)}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </section>

                {/* Plan Chat */}
                <div className="mt-4">
                  <details className="details-soft compact-details">
                    <summary className="details-summary">
                      Plan Chat
                    </summary>

                    <div className="list-group list-group-soft mb-3 mt-3">
                      {chatMessages.length === 0 ? (
                        <div className="list-group-item text-muted">
                          Ask to swap meals, modify workouts, adjust calories, or explain the selected day.
                        </div>
                      ) : (
                        chatMessages.map((m, idx) => (
                          <div key={idx} className="list-group-item">
                            <strong>
                              {m.role === "user" ? "You" : "Coach"}:
                            </strong>{" "}
                            {m.text}
                          </div>
                        ))
                      )}
                    </div>

                    <div className="d-flex gap-2 flex-wrap">
                      <input
                        className="form-control"
                        value={dietChatInput}
                        onChange={(e) => setDietChatInput(e.target.value)}
                        placeholder="e.g. replace tuna lunch and make my workout lower impact"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleDietChat();
                        }}
                        disabled={isReadOnlyClientView}
                      />
                      <button
                        className="btn btn-primary fw-bold"
                        type="button"
                        onClick={handleDietChat}
                        disabled={isDietChatting || isReadOnlyClientView}
                      >
                        {isDietChatting ? <Loading label="Sending..." /> : "Send"}
                      </button>
                    </div>

                    {isReadOnlyClientView ? (
                      <StatusAlert variant="info">
                        Dietitians can review client plans here, but only the client can change meals or workouts.
                      </StatusAlert>
                    ) : null}
                    <StatusAlert variant="warning">{dietChatMsg}</StatusAlert>
                  </details>
                </div>
              </>
            )}
          </div>
        </div>

        {showAdvancedPanels ? (
          <div className="card card-soft mt-4">
            <div className="card-body p-4">
              <details className="details-soft">
                <summary className="details-summary">Feedback (Advanced)</summary>

                <div className="mt-3">
                  <p className="text-muted mb-3">
                    Use an event ID from the calendar.
                  </p>

                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label">Event ID</label>
                      <input
                        className="form-control"
                        value={eventId}
                        onChange={(e) => setEventId(e.target.value)}
                      />
                    </div>

                    <div className="col-md-2">
                      <label className="form-label">Rating (1-5)</label>
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
                        <option value="coach">coach</option>
                        <option value="friendly">friendly</option>
                      </select>
                    </div>
                  </div>

                  <div className="mt-3 d-flex gap-2">
                    <button
                      className="btn btn-primary fw-bold"
                      type="button"
                      onClick={handleFeedback}
                      disabled={isFeedback}
                    >
                      {isFeedback ? <Loading label="Submitting..." /> : "Submit"}
                    </button>

                    <button
                      className="btn btn-outline-light"
                      type="button"
                      onClick={copyFeedback}
                      disabled={
                        !feedbackOut ||
                        String(feedbackOut).startsWith("Submitting")
                      }
                    >
                      Copy Output
                    </button>
                  </div>

                  <pre className="out mt-3">{feedbackOut}</pre>
                </div>
              </details>
            </div>
          </div>
        ) : null}
      </div>

      {/* Right column */}
      <div className="col-lg-4">
        <div className="card card-soft">
          <div className="card-body p-4">
            <details className="details-soft compact-details" open>
              <summary className="details-summary">Progress</summary>

              <div className="row g-3 mt-2">
                <div className="col-12">
                  <label className="form-label">Current weight (kg)</label>
                  <input
                    className="form-control"
                    type="number"
                    min="30"
                    max="300"
                    step="0.1"
                    value={progressWeight}
                    onChange={(e) => setProgressWeight?.(e.target.value)}
                    disabled={isReadOnlyClientView}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label">Meal adherence: {mealAdherence}%</label>
                  <input
                    className="form-range"
                    type="range"
                    min="0"
                    max="100"
                    value={mealAdherence}
                    onChange={(e) => setMealAdherence?.(e.target.value)}
                    disabled={isReadOnlyClientView}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label">Workout adherence: {workoutAdherence}%</label>
                  <input
                    className="form-range"
                    type="range"
                    min="0"
                    max="100"
                    value={workoutAdherence}
                    onChange={(e) => setWorkoutAdherence?.(e.target.value)}
                    disabled={isReadOnlyClientView}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label">Energy: {energyLevel}/5</label>
                  <input
                    className="form-range"
                    type="range"
                    min="1"
                    max="5"
                    value={energyLevel}
                    onChange={(e) => setEnergyLevel?.(e.target.value)}
                    disabled={isReadOnlyClientView}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label">Notes</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    value={progressNotes}
                    onChange={(e) => setProgressNotes?.(e.target.value)}
                    placeholder="Sleep, hunger, soreness, missed meals..."
                    disabled={isReadOnlyClientView}
                  />
                </div>
              </div>

              <div className="d-grid gap-2 mt-3">
                <button
                  className="btn btn-primary fw-bold"
                  type="button"
                  onClick={handleProgressCheckIn}
                  disabled={isProgressBusy || isReadOnlyClientView}
                >
                  {isProgressBusy ? <Loading label="Saving..." /> : "Save Check-In"}
                </button>
                <button
                  className="btn btn-outline-light"
                  type="button"
                  onClick={handleWeeklyUpdate}
                  disabled={isProgressBusy || isReadOnlyClientView}
                >
                  Generate Weekly Update
                </button>
              </div>

              <StatusAlert variant={String(progressMsg).startsWith("Error:") ? "warning" : "success"}>
                {progressMsg}
              </StatusAlert>

              {weeklyUpdate ? (
                <div className="alert alert-dark border-0 mt-3 small">
                  <div className="fw-semibold mb-1">This week's adjustment</div>
                  <div>{weeklyUpdate.summary}</div>
                  {weeklyUpdate.adjustments ? (
                    <div className="text-muted mt-2">
                      Calories: {weeklyUpdate.adjustments.calorie_adjustment_kcal || 0} kcal |
                      Workouts: {weeklyUpdate.adjustments.workout_adjustment || "keep_current"}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {recentProgress.length > 0 ? (
                <div className="list-group list-group-soft mt-3">
                  {recentProgress.map((item) => (
                    <div key={item.id} className="list-group-item">
                      <div className="d-flex justify-content-between gap-2">
                        <strong>{item.checked_in_on || "Check-in"}</strong>
                        <span>{item.weight_kg ? `${item.weight_kg} kg` : "No weight"}</span>
                      </div>
                      <small className="text-muted">
                        Meals {item.meal_adherence}% | Workouts {item.workout_adherence}% | Energy {item.energy_level}/5
                      </small>
                    </div>
                  ))}
                </div>
              ) : null}
            </details>
          </div>
        </div>

        <div className="card card-soft mt-4">
          <div className="card-body p-4">
            <details className="details-soft compact-details">
              <summary className="details-summary">Calendar</summary>

              <p className="text-muted mt-3 mb-3">
                Meals and workouts are added, removed, and updated automatically when your plan changes.
              </p>

              <div className="d-flex gap-2 mb-3 flex-wrap">
                <button
                  className="btn btn-primary fw-bold flex-grow-1"
                  type="button"
                  onClick={handleGoogleCalendarConnect}
                  disabled={isGoogleCalendarBusy || googleCalendar?.connected}
                >
                  {isGoogleCalendarBusy && !googleCalendar?.connected ? (
                    <Loading label="Connecting..." />
                  ) : googleCalendar?.connected ? (
                    "Google Calendar Connected"
                  ) : (
                    "Connect Google Calendar"
                  )}
                </button>

                {googleCalendar?.connected ? (
                  <button
                    className="btn btn-outline-light"
                    type="button"
                    onClick={handleGoogleCalendarDisconnect}
                    disabled={isGoogleCalendarBusy}
                  >
                    Disconnect
                  </button>
                ) : null}
              </div>

              <div className="text-muted small mb-3">
                {googleCalendar?.connected
                  ? "Your plan changes will also sync to your Google Calendar."
                  : googleCalendar?.enabled
                    ? "Connect Google Calendar to mirror these events in your personal calendar."
                    : "Google Calendar is not configured for this environment yet."}
              </div>

              <StatusAlert variant="warning">{calendarMsg}</StatusAlert>
              <StatusAlert variant="info">{googleCalendarMsg}</StatusAlert>
              {calendarForDisplay ? <Calendar result={calendarForDisplay} /> : null}
            </details>
          </div>
        </div>

        {showAdvancedPanels ? (
          <div className="card card-soft mt-4">
            <div className="card-body p-4">
              <h2 className="h5 panel-title mb-3">Motivation</h2>

              <div className="row g-3">
                <div className="col-12">
                  <label className="form-label">Tone</label>
                  <select
                    className="form-select"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                  >
                    <option value="coach">coach</option>
                    <option value="friendly">friendly</option>
                  </select>
                </div>

                <div className="col-12">
                  <label className="form-label">Goal Text</label>
                  <input
                    className="form-control"
                    value={goalText}
                    onChange={(e) => setGoalText(e.target.value)}
                    placeholder="stay_consistent"
                  />
                </div>
              </div>

              <button
                className="btn btn-primary fw-bold w-100 mt-3"
                type="button"
                onClick={handleNudge}
                disabled={isNudging}
              >
                {isNudging ? <Loading label="Sending..." /> : "Send Nudge"}
              </button>

              <StatusAlert variant="warning">{nudgeMsg}</StatusAlert>
              {nudge ? (
                <Nudge result={nudge} tone={tone} goal={goalText} />
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="mt-4">
            <button
              className="btn btn-outline-light w-100"
              type="button"
              onClick={handleGoHome || (() => setStage("auth"))}
            >
              {"<-"} Back
            </button>
          </div>
        </div>
    </div>
  );
}
