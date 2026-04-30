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

  const meals = Array.isArray(plan?.meals) ? plan.meals : [];
  const workouts = Array.isArray(plan?.workouts) ? plan.workouts : [];
  const chatMessages = Array.isArray(dietChatMessages) ? dietChatMessages : [];
  const totalMealCalories = sumBy(meals, ["kcal", "calories"]);
  const totalWorkoutMinutes = sumBy(workouts, ["duration", "duration_min"]);

  return (
    <div className="row g-4">
      <div className="col-lg-8">
        <div className="card card-soft results-shell">
          <div className="card-body p-4 p-md-5">
            <div className="results-header">
              <div>
                <div className="results-kicker">Daily plan dashboard</div>
                <h1 className="results-title">Your plan for today</h1>
                <div className="text-muted">
                  Nutrition, training, calendar, and coaching in one view.
                </div>
                {isReadOnlyClientView && viewedAccount ? (
                  <div className="alert alert-info mt-3 mb-0 small">
                    Viewing {viewedAccount.display_name || viewedAccount.email}'s plan in read-only mode.
                    Only the client account can generate or change this plan.
                  </div>
                ) : null}
              </div>

              <div className="results-actions">
                <button
                  className="btn btn-outline-light"
                  type="button"
                  onClick={() => setStage("quiz")}
                  disabled={isReadOnlyClientView}
                >
                  Edit Quiz
                </button>

                <button
                  className="btn btn-primary fw-bold"
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
                  Complete the quiz to generate a personalized meal and workout
                  plan.
                </p>
                <button
                  className="btn btn-primary fw-bold"
                  type="button"
                  onClick={() => setStage("quiz")}
                  disabled={isReadOnlyClientView}
                >
                  {isReadOnlyClientView ? "Client Must Log In" : "Start Quiz"}
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
                    <div className="summary-label">Generated</div>
                    <div className="summary-value summary-date">
                      {new Date().toLocaleDateString()}
                    </div>
                    <div className="summary-meta">Calendar synced automatically</div>
                  </div>
                </div>

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
                  <h2 className="section-h mb-2">Plan Chat</h2>

                  <div className="list-group list-group-soft mb-3">
                    {chatMessages.length === 0 ? (
                      <div className="list-group-item text-muted">
                        Ask to swap meals, modify workouts, adjust calories, or explain the plan.
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

                  <div className="d-flex gap-2">
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
            <h2 className="h5 panel-title mb-2">Calendar</h2>
            <p className="text-muted mb-3">
              Meals and workouts are added, removed, and updated automatically when your plan changes.
            </p>

            <div className="d-flex gap-2 mb-3">
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
            {calendar ? <Calendar result={calendar} /> : null}
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
