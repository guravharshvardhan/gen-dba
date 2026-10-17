import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

function AutomationCenter() {
  const [history, setHistory] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [executionHistory, setExecutionHistory] = useState([]);

  const [latestRun, setLatestRun] = useState(null);
  const [latestExecution, setLatestExecution] = useState(null);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  // =========================================================
  // LOAD AUTOMATION HISTORY
  // =========================================================

  const loadAutomationHistory = async () => {
    const response = await fetch(
      `${API}/automation/history?limit=10`
    );

    if (!response.ok) {
      throw new Error("Failed to load automation history.");
    }

    const data = await response.json();

    const runs = data.history || [];

    setHistory(runs);
    setLatestRun(runs.length > 0 ? runs[0] : null);
  };

  // =========================================================
  // LOAD RECOMMENDATIONS
  // =========================================================

  const loadRecommendations = async () => {
    const response = await fetch(
      `${API}/recommendations`
    );

    if (!response.ok) {
      throw new Error("Failed to load recommendations.");
    }

    const data = await response.json();

    if (Array.isArray(data)) {
      setRecommendations(data);
    } else {
      setRecommendations(data.recommendations || []);
    }
  };

  // =========================================================
  // LOAD EXECUTION HISTORY
  // =========================================================

  const loadExecutionHistory = async () => {
    const response = await fetch(
      `${API}/execution-history?limit=20`
    );

    if (!response.ok) {
      throw new Error("Failed to load execution history.");
    }

    const data = await response.json();

    const executions =
      data.execution_history || [];

    setExecutionHistory(executions);
    setLatestExecution(
      executions.length > 0
        ? executions[0]
        : null
    );
  };

  // =========================================================
  // LOAD ALL DATA
  // =========================================================

  const loadAutomationData = async () => {
    try {
      setError("");

      await Promise.all([
        loadAutomationHistory(),
        loadRecommendations(),
        loadExecutionHistory()
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // INITIAL LOAD + AUTO REFRESH
  // =========================================================

  useEffect(() => {
    loadAutomationData();

    const interval = setInterval(
      loadAutomationData,
      30000
    );

    return () => {
      clearInterval(interval);
    };
  }, []);

  // =========================================================
  // APPROVE RECOMMENDATION
  // =========================================================

  const approveRecommendation = async (
    recommendationId
  ) => {
    try {
      setActionLoading(true);
      setError("");

      const response = await fetch(
        `${API}/recommendations/${recommendationId}/approve`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Approval failed."
        );
      }

      await loadAutomationData();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // // =========================================================
  // // REJECT RECOMMENDATION
  // // =========================================================

  const rejectRecommendation = async (
    recommendationId
  ) => {
    try {
      setActionLoading(true);
      setError("");

      const response = await fetch(
        `${API}/recommendations/${recommendationId}/reject`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Rejection failed."
        );
      }

      await loadAutomationData();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // =========================================================
  // HELPERS
  // =========================================================

  const formatDate = (value) => {
    if (!value) {
      return "N/A";
    }

    try {
      return new Date(value).toLocaleString();
    } catch {
      return "N/A";
    }
  };

  const formatNumber = (value) => {
    const number = Number(value);

    if (Number.isNaN(number)) {
      return "0.000";
    }

    return number.toFixed(3);
  };

  // =========================================================
  // FILTERS
  // =========================================================

  const pendingRecommendations =
    recommendations.filter(
      (item) => item.status === "PENDING"
    );

  const approvedRecommendations =
    recommendations.filter(
      (item) => item.status === "APPROVED"
    );

  const rejectedRecommendations =
    recommendations.filter(
      (item) => item.status === "REJECTED"
    );

  const rolledBackExecutions =
    executionHistory.filter(
      (item) =>
        item.status === "ROLLED_BACK"
    );

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <div className="page-content">
        <div className="automation-loading-screen">
          <div className="automation-loader"></div>

          <h2>
            Loading Automation Center
          </h2>

          <p>
            Connecting to Gen-DBA automation engine...
          </p>
        </div>
      </div>
    );
  }

  // =========================================================
  // MAIN UI
  // =========================================================

  return (
    <div className="page-content automation-page">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="page-header automation-header">

        <div>
          <div className="page-kicker">
            AUTONOMOUS WORKLOAD INTELLIGENCE
          </div>

          <h1>
            Automation Center
          </h1>

          <p>
            Continuous workload monitoring,
            AI recommendations and controlled
            optimization verification.
          </p>
        </div>

        <div className="automation-header-actions">

          <div className="automation-live-badge">
            <span className="live-dot"></span>
            Monitoring Active
          </div>

          <button
            className="refresh-button"
            onClick={loadAutomationData}
          >
            ↻ Refresh
          </button>

        </div>
      </div>

      {/* =====================================================
          ERROR
      ===================================================== */}

      {error && (
        <div className="automation-error">
          <strong>
            Automation Error
          </strong>

          <span>
            {error}
          </span>
        </div>
      )}

      {/* =====================================================
          KPI CARDS
      ===================================================== */}

      <div className="automation-stats">

        <div className="automation-stat-card">

          <div className="automation-stat-icon">
            ◉
          </div>

          <div className="automation-stat-label">
            MONITORING
          </div>

          <div className="automation-stat-value online">
            ACTIVE
          </div>

          <div className="automation-stat-sub">
            Scheduler running every 5 minutes
          </div>

        </div>


        <div className="automation-stat-card">

          <div className="automation-stat-icon blue">
            ◫
          </div>

          <div className="automation-stat-label">
            LAST SCAN
          </div>

          <div className="automation-stat-value small-value">
            {latestRun
              ? formatDate(
                  latestRun.completed_at
                )
              : "No runs"}
          </div>

          <div className="automation-stat-sub">
            Latest workload scan
          </div>

        </div>


        <div className="automation-stat-card">

          <div className="automation-stat-icon purple">
            ✦
          </div>

          <div className="automation-stat-label">
            PENDING REVIEW
          </div>

          <div className="automation-stat-value purple">
            {pendingRecommendations.length}
          </div>

          <div className="automation-stat-sub">
            Waiting for DBA approval
          </div>

        </div>


         <div className="automation-stat-card">

          <div className="automation-stat-icon green">
            ✓
          </div>

          <div className="automation-stat-label">
            OPTIMIZATION RESULT
          </div>

          <div className="automation-stat-value">
            {latestExecution
              ? latestExecution.status
              : "NONE"}
          </div>

          <div className="automation-stat-sub">
            Latest execution state
          </div>

        </div> 

      </div>

      {/* =====================================================
          CURRENT AUTOMATION OVERVIEW
      ===================================================== */}

      {latestRun && (
        <div className="automation-overview-card">

          <div className="automation-overview-left">

            <div className="panel-kicker">
              CURRENT AUTOMATION STATUS
            </div>

            <h2>
              System is actively monitoring your workload
            </h2>

            <p>
              The automation engine checks high-impact
              queries, analyzes execution plans and
              generates recommendations when optimization
              opportunities are detected.
            </p>

          </div>


          <div className="automation-overview-metrics">

            <div>
              <span>
                Queries Checked
              </span>

              <strong>
                {latestRun.queries_checked}
              </strong>
            </div>

            <div>
              <span>
                Unique Queries
              </span>

              <strong>
                {latestRun.unique_queries_detected}
              </strong>
            </div>

            <div>
              <span>
                AI Created
              </span>

              <strong>
                {latestRun.recommendations_created}
              </strong>
            </div>

            <div>
              <span>
                Already Pending
              </span>

              <strong>
                {latestRun.already_pending}
              </strong>
            </div>

          </div>

        </div>
      )}

      {/* =====================================================
          LATEST OPTIMIZATION RESULT
      ===================================================== */}
 
      {latestExecution && (
        <div className="execution-result-card">

          <div className="execution-result-header">

            <div> 

              <div className="panel-kicker">
                LATEST OPTIMIZATION RESULT
              </div>

              <h2>
                Execution #
                {latestExecution.execution_id}
              </h2>

            </div>


            <div
              className={
                latestExecution.status ===
                "VERIFIED"
                  ? "execution-result-status verified"
                  : latestExecution.status ===
                    "ROLLED_BACK"
                  ? "execution-result-status rollback"
                  : "execution-result-status"
              }
            >
              {latestExecution.status}
            </div>

          </div>


          <div className="execution-result-grid">

            <div className="execution-result-metric">

              <span>
                ORIGINAL MEDIAN
              </span>

              <strong>
                {formatNumber(
                  latestExecution.original_median_time
                )}{" "}
                ms
              </strong>

            </div>


            <div className="execution-arrow">
              →
            </div>


            <div className="execution-result-metric optimized">

              <span>
                OPTIMIZED MEDIAN
              </span>

              <strong>
                {formatNumber(
                  latestExecution.optimized_median_time
                )}{" "}
                ms
              </strong>

            </div>


            <div className="execution-result-metric improvement">

              <span>
                IMPROVEMENT
              </span>

              <strong>
                {formatNumber(
                  latestExecution.improvement_percentage
                )}%
              </strong>

            </div>

          </div>


          <div className="execution-result-footer">

            <span>
              Recommendation #
              {latestExecution.recommendation_id}
            </span>

            <span>
              Comparison #
              {latestExecution.comparison_id}
            </span>

            <span>
              Observed:{" "}
              {formatNumber(
                latestExecution.execution_time
              )}{" "}
              ms
            </span>

            <span>
              {formatDate(
                latestExecution.created_at
              )}
            </span>

          </div>


          <div className="execution-message">
            {latestExecution.message}
          </div>

        </div>
      )} 

      {/* =====================================================
          ROLLBACK PROTECTION
      ===================================================== */}

      <div className="rollback-protection-card">

        <div className="rollback-protection-icon">
          ↶
        </div>

        <div className="rollback-protection-content">

          {/* <div className="panel-kicker">
            ROLLBACK PROTECTION
          </div> */}

          <h2>
            Automatic Recovery Enabled
          </h2>

          <p>
            If an applied optimization degrades
            performance, Gen-DBA can trigger the
            stored rollback action and record the
            event in the audit trail.
          </p>

        </div>

        <div className="rollback-protection-status">

          <span className="live-dot"></span>

          ACTIVE

        </div>

      </div>

      {/* =====================================================
          PENDING RECOMMENDATIONS
      ===================================================== */}

      <div className="automation-section">

        <div className="automation-section-header">

          <div>

            <div className="panel-kicker">
              HUMAN-IN-THE-LOOP
            </div>

            {/* <h2>
              Pending Optimization Decisions
            </h2> */}

            <p>
              AI recommendations waiting for DBA review.
            </p>

          </div>

          <div className="pending-counter">

            {pendingRecommendations.length}

            <span>
              pending
            </span>

          </div>

        </div>


        {pendingRecommendations.length === 0 ? (

          <div className="automation-empty-card">

            <div className="automation-empty-icon">
              ✓
            </div>

            <h3>
              No Pending Decisions
            </h3>

            <p>
              All current recommendations have been reviewed.
            </p>

          </div>

        ) : (

          <div className="automation-recommendation-grid">

            {pendingRecommendations.map(
              (rec) => (

                <div
                  className="automation-recommendation-card"
                  key={
                    rec.recommendation_id
                  }
                >

                  <div className="recommendation-card-header">

                    <div>

                      <span className="recommendation-label">
                        AI RECOMMENDATION
                      </span>

                      <h3>
                        Recommendation #
                        {rec.recommendation_id}
                      </h3>

                    </div>

                    <span className="status-badge status-pending">
                      PENDING
                    </span>

                  </div>


                  <div className="recommendation-meta-row">

                    <span>
                      Risk
                    </span>

                    <strong>
                      {rec.risk_level || "Low"}
                    </strong>

                  </div>


                  <div className="recommendation-body">

                    {rec.recommendation_text ||
                      "No recommendation details available."}

                  </div>


                  <div className="recommendation-created">

                    Created{" "}
                    {formatDate(
                      rec.created_at
                    )}

                  </div>


                  <div className="recommendation-actions">

                    <button
                      className="approve-button large-action"
                      onClick={() =>
                        approveRecommendation(
                          rec.recommendation_id
                        )
                      }
                      disabled={actionLoading}
                    >
                      ✓ Approve Recommendation
                    </button>


                    <button
                      className="reject-button large-action"
                      onClick={() =>
                        rejectRecommendation(
                          rec.recommendation_id
                        )
                      }
                      disabled={actionLoading}
                    >
                      × Reject
                    </button>

                  </div>


                  <div className="recommendation-safety">

                    🔐

                    <span>
                      Approval records the DBA decision.
                      Database changes are not executed
                      without the controlled workflow.
                    </span>

                  </div>

                </div>

              )
            )}

          </div>

        )}

      </div>

      {/* =====================================================
          DECISION PIPELINE
      ===================================================== */}

      <div className="automation-panel automation-pipeline-panel">

       <div className="panel-kicker">
          GEN-DBA DECISION PIPELINE
        </div> 

        <h2>
          From Detection to Verification
        </h2>


        <div className="automation-pipeline">

          <div className="pipeline-step completed">

            <div className="pipeline-number">
              01
            </div>

            <div>
              <strong>
                Monitor
              </strong>

              <span>
                Workload
              </span>
            </div>

          </div>


          <div className="pipeline-connector"></div>


          <div className="pipeline-step completed">

            <div className="pipeline-number">
              02
            </div>

            <div>
              <strong>
                Detect
              </strong>

              <span>
                Issues
              </span>
            </div>

          </div>


          <div className="pipeline-connector"></div>


          <div className="pipeline-step completed">

            <div className="pipeline-number">
              03
            </div>

            <div>
              <strong>
                Gemini AI
              </strong>

              <span>
                Recommend
              </span>
            </div>

          </div>


          <div className="pipeline-connector"></div>


          <div className="pipeline-step completed">

            <div className="pipeline-number">
              04
            </div>

            <div>
              <strong>
                DBA
              </strong>

              <span>
                Approve
              </span>
            </div>

          </div>


          <div className="pipeline-connector"></div>


          <div className="pipeline-step completed">

            <div className="pipeline-number">
              05
            </div>

            <div>
              <strong>
                Execute
              </strong>

              <span>
                Optimize
              </span>
            </div>

          </div>


          <div className="pipeline-connector"></div>


          <div className="pipeline-step waiting">

            <div className="pipeline-number">
              06
            </div>

            <div>
              <strong>
                Verify
              </strong>

              <span>
                Keep / Rollback
              </span>
            </div>

          </div>

        </div>

      </div>

      {/* =====================================================
          EXECUTION HISTORY
      ===================================================== */}

      <div className="automation-section">

        <div className="automation-section-header">

          <div>

             <div className="panel-kicker">
              EXECUTION HISTORY
            </div> 

            <h2>
              Optimization Events
            </h2>

            <p>
              Complete execution and verification history.
            </p>

          </div>

        </div>


        <div className="automation-history-panel">

          {executionHistory.length === 0 ? (

            <div className="automation-empty-card compact">
              No optimization executions recorded.
            </div>

          ) : (

            <div className="table-wrapper">

              <table className="automation-table">

                <thead>

                  <tr>

                    <th>
                      EXECUTION
                    </th>

                    <th>
                      TYPE
                    </th>

                    <th>
                      STATUS
                    </th>

                    <th>
                      ORIGINAL
                    </th>

                    <th>
                      OPTIMIZED
                    </th>

                    <th>
                      IMPROVEMENT
                    </th>

                    <th>
                      TIME
                    </th>

                    <th>
                      PERFORMED BY
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {executionHistory.map(
                    (execution) => (

                      <tr
                        key={
                          execution.execution_id
                        }
                      >

                        <td>

                          <span className="run-id">
                            #
                            {execution.execution_id}
                          </span>

                        </td>


                        <td>
                          {execution.execution_type}
                        </td>


                        <td>

                          <span
                            className={
                              execution.status ===
                              "VERIFIED"
                                ? "status-badge status-approved"
                                : execution.status ===
                                  "ROLLED_BACK"
                                ? "status-badge status-rejected"
                                : "status-badge status-pending"
                            }
                          >
                            {execution.status}
                          </span>

                        </td>


                        <td>

                          {execution.original_median_time
                            ? `${formatNumber(
                                execution.original_median_time
                              )} ms`
                            : "—"}

                        </td>


                        <td>

                          {execution.optimized_median_time
                            ? `${formatNumber(
                                execution.optimized_median_time
                              )} ms`
                            : "—"}

                        </td>


                        <td>

                          <span className="improvement-value">
                            {execution.improvement_percentage !==
                            null &&
                            execution.improvement_percentage !==
                            undefined
                              ? `${formatNumber(
                                  execution.improvement_percentage
                                )}%`
                              : "—"}
                          </span>

                        </td>


                        <td>
                          {formatDate(
                            execution.created_at
                          )}
                        </td>


                        <td>
                          {execution.performed_by ||
                            "SYSTEM"}
                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      </div>

      {/* =====================================================
          ROLLBACK HISTORY
      ===================================================== */}
 
      <div className="automation-section">

        <div className="automation-section-header">

          <div>

            <div className="panel-kicker">
              RECOVERY EVENTS
            </div> 

            <h2>
              Rollback History
            </h2> 

             <p>
              Optimizations reverted after performance degradation.
            </p>

          </div>


          <div className="rollback-count">

            {rolledBackExecutions.length}

            <span>
              rollback events
            </span>

          </div>

        </div>


        {rolledBackExecutions.length === 0 ? (

          <div className="rollback-empty-card">

            <div className="rollback-empty-icon">
              ✓
            </div>

            <div>

              <h3>
                No Rollbacks Required
              </h3>

              <p>
                All verified optimizations have remained
                performance-safe so far.
              </p>

            </div>

          </div>

        ) : (

          <div className="rollback-events-list">

            {rolledBackExecutions.map(
              (item) => (

                <div
                  className="rollback-event"
                  key={
                    item.execution_id
                  }
                >

                  <div className="rollback-event-icon">
                    ↶
                  </div>


                  <div className="rollback-event-main">

                    <strong>
                      Optimization #
                      {item.execution_id}
                      {" "}
                      Automatically Rolled Back
                    </strong>

                    <p>
                      {item.message}
                    </p>

                    <span>
                      Recommendation #
                      {item.recommendation_id}
                      {" • "}
                      {formatDate(
                        item.created_at
                      )}
                    </span>

                  </div>


                  <div className="rollback-status">
                    ROLLED BACK
                  </div>

                </div>

              )
            )}

          </div>

        )}

      </div> 

      {/* =====================================================
          FOOTER
      ===================================================== */}

      <div className="automation-footer-grid">

        <div className="automation-footer-card">

          <span className="footer-icon green">
            ✓
          </span>

          <div>

            <strong>
              {approvedRecommendations.length}
            </strong>

            <span>
              Approved
            </span>

          </div>

        </div> 


        <div className="automation-footer-card">

          <span className="footer-icon yellow">
            ◌
          </span>

          <div>

            <strong>
              {pendingRecommendations.length}
            </strong>

            <span>
              Pending
            </span>

          </div>

        </div>


        <div className="automation-footer-card">

          <span className="footer-icon red">
            ×
          </span>

          <div>

            <strong>
              {rejectedRecommendations.length}
            </strong>

            <span>
              Rejected
            </span> 

          </div>

        </div>


         <div className="automation-footer-card security">

          <span className="footer-icon">
            🔐
          </span>

          <div>

            <strong>
              Human Approval
            </strong> 

            <span>
              Required before changes
            </span>

          </div>

        </div> 

      </div>

    </div>
  );
}

export default AutomationCenter;