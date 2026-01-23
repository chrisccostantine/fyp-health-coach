import React from "react";

export default function ResultsSection({
  stage,
  plan,
  setStage,
  isPlanning,
  handlePlanToday,

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

  // schedule
  mealTimes,
  setMealTimes,
  workoutTime,
  setWorkoutTime,
  isScheduling,
  handleSchedule,
  scheduleMsg,
  schedule,

  // nudge
  tone,
  setTone,
  goalText,
  setGoalText,
  isNudging,
  handleNudge,
  nudgeMsg,
  nudge,

  // views
  PlanView,
  ScheduleView,
  NudgeView,
  Spinner,
  Alert,
}) {
  if (stage !== "results") return null;

  const meals = plan && plan.meals ? plan.meals : [];
  const workouts = plan && plan.workouts ? plan.workouts : [];

  return (
    <div className="row g-4">
      {/* LEFT */}
      <div className="col-lg-8">
        <div className="card card-soft results-card">
          <div className="card-body p-4">
            <div className="results-header">
              <div>
                <div className="text-muted small">Results</div>
                <h1 className="results-title mb-1">Your plan for today</h1>
                <div className="text-muted results-subtitle">
                  Quiz → Plan → Schedule
                </div>
              </div>

              <div className="d-flex gap-2">
                <button
                  className="btn btn-outline-light"
                  type="button"
                  onClick={() => setStage("quiz")}
                >
                  Edit Quiz
                </button>

                <button
                  className="btn btn-primary fw-bold"
                  type="button"
                  onClick={() => handlePlanToday({ autoGoResults: false })}
                  disabled={isPlanning}
                >
                  {isPlanning ? (
                    <Spinner label="Refreshing..." />
                  ) : (
                    "Regenerate"
                  )}
                </button>
              </div>
            </div>

            {!plan ? (
              <div className="empty-state mt-4">
                <div className="text-muted mb-2">No plan yet.</div>
                <button
                  className="btn btn-primary fw-bold"
                  type="button"
                  onClick={() => setStage("quiz")}
                >
                  Go to Quiz
                </button>
              </div>
            ) : (
              <React.Fragment>
                {/* Summary */}
                <div className="row g-3 mt-3">
                  <div className="col-md-4">
                    <div className="mini-stat">
                      <div className="mini-stat-label">Meals</div>
                      <div className="mini-stat-value">{meals.length}</div>
                    </div>
                  </div>

                  <div className="col-md-4">
                    <div className="mini-stat">
                      <div className="mini-stat-label">Workouts</div>
                      <div className="mini-stat-value">{workouts.length}</div>
                    </div>
                  </div>

                  <div className="col-md-4">
                    <div className="mini-stat">
                      <div className="mini-stat-label">Generated</div>
                      <div className="mini-stat-value">
                        {new Date().toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Meals */}
                <div className="mt-4">
                  <div className="section-head">
                    <h2 className="section-title mb-0">Meals</h2>
                    <span className="badge rounded-pill text-bg-dark-soft">
                      {meals.length}
                    </span>
                  </div>

                  <div className="list-stack mt-2">
                    {meals.map((m, idx) => (
                      <div key={idx} className="list-item">
                        <div className="list-item-main">
                          <div className="list-item-title">{m.title}</div>
                          <div className="list-item-meta text-muted">
                            Protein {m.protein}g · Carbs {m.carbs}g · Fat{" "}
                            {m.fat}g · {m.kcal} kcal
                          </div>
                        </div>

                        <div className="list-item-right">
                          <span className="time-pill">{m.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Workouts */}
                <div className="mt-4">
                  <div className="section-head">
                    <h2 className="section-title mb-0">Workout</h2>
                    <span className="badge rounded-pill text-bg-dark-soft">
                      {workouts.length}
                    </span>
                  </div>

                  <div className="list-stack mt-2">
                    {workouts.map((w, idx) => (
                      <div key={idx} className="list-item">
                        <div className="list-item-main">
                          <div className="list-item-title">{w.title}</div>
                          <div className="list-item-meta text-muted">
                            {w.duration} min
                          </div>
                        </div>

                        <div className="list-item-right">
                          <span className="time-pill">{w.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Raw Plan */}
                <div className="mt-4">
                  <details className="details-soft">
                    <summary className="details-summary">
                      View full raw plan output
                    </summary>
                    <div className="mt-3">
                      <PlanView plan={plan} />
                    </div>
                  </details>
                </div>
              </React.Fragment>
            )}
          </div>
        </div>

        {/* Feedback */}
        <div className="card card-soft mt-4">
          <div className="card-body p-4">
            <details className="details-soft">
              <summary className="details-summary">Feedback (Advanced)</summary>

              <div className="mt-3">
                <p className="text-muted mb-3">
                  Use an event ID from schedule.
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
                    {isFeedback ? <Spinner label="Submitting..." /> : "Submit"}
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
      </div>

      {/* RIGHT */}
      <div className="col-lg-4">
        <div className="card card-soft">
          <div className="card-body p-4">
            <h2 className="h5 section-title mb-2">Schedule</h2>
            <p className="text-muted mb-3">Commit items to the Scheduler.</p>

            <div className="mb-3">
              <label className="form-label">
                Meal Times (HH:MM, comma-separated)
              </label>
              <input
                className="form-control"
                value={mealTimes}
                onChange={(e) => setMealTimes(e.target.value)}
                placeholder="08:00,13:00,19:00"
              />
              <div className="text-muted small mt-1">
                Example: <code className="code-soft">08:00,13:00,19:00</code>
              </div>
            </div>

            <div className="mb-3">
              <label className="form-label">Workout Time (HH:MM)</label>
              <input
                className="form-control"
                value={workoutTime}
                onChange={(e) => setWorkoutTime(e.target.value)}
                placeholder="18:00"
              />
            </div>

            <button
              className="btn btn-primary fw-bold w-100"
              type="button"
              onClick={handleSchedule}
              disabled={isScheduling}
            >
              {isScheduling ? (
                <Spinner label="Committing..." />
              ) : (
                "Commit Schedule"
              )}
            </button>

            <Alert variant="warning">{scheduleMsg}</Alert>
            {schedule ? <ScheduleView result={schedule} /> : null}
          </div>
        </div>

        <div className="card card-soft mt-4">
          <div className="card-body p-4">
            <h2 className="h5 section-title mb-3">Motivation</h2>

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
              {isNudging ? <Spinner label="Sending..." /> : "Send Nudge"}
            </button>

            <Alert variant="warning">{nudgeMsg}</Alert>
            {nudge ? (
              <NudgeView result={nudge} tone={tone} goal={goalText} />
            ) : null}
          </div>
        </div>

        <div className="mt-4">
          <button
            className="btn btn-outline-light w-100"
            type="button"
            onClick={() => setStage("landing")}
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
