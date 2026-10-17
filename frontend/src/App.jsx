import { useEffect, useState } from "react";
import AutomationCenter from "./AutomationCenter";
import "./App.css";

const API = "http://127.0.0.1:8000";

// Shared API helper: automatically attaches the logged-in user's bearer token.
async function apiFetch(url, options = {}) {
  const token = sessionStorage.getItem("gendba_access_token");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

function App() {
  const [authUser, setAuthUser] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("gendba_user") || "null");
    } catch {
      return null;
    }
  });
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      // Current FastAPI endpoint accepts username/password as query parameters.
      const params = new URLSearchParams({ username: loginUsername.trim(), password: loginPassword });
      const response = await fetch(`${API}/auth/login?${params.toString()}`, { method: "POST" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Login failed. Check your credentials.");
      if (!data.access_token || !data.user) throw new Error("Login response did not contain a token and user.");
      sessionStorage.setItem("gendba_access_token", data.access_token);
      sessionStorage.setItem("gendba_user", JSON.stringify(data.user));
      setAuthUser(data.user);
      setLoginPassword("");
    } catch (error) {
      setLoginError(error.message || "Unable to login.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("gendba_access_token");
    sessionStorage.removeItem("gendba_user");
    setAuthUser(null);
    setActivePage("dashboard");
  };


  // =========================================================
  // GENERAL STATE
  // =========================================================

  const [activePage, setActivePage] = useState("dashboard");

  const [dashboard, setDashboard] = useState({
    summary: {},
    top_queries: [],
    recent_recommendations: [],
    recent_audit_logs: []
  });

  const [loadingDashboard, setLoadingDashboard] = useState(true);


  // =========================================================
  // QUERY ANALYZER STATE
  // =========================================================

  const [query, setQuery] = useState("");

  const [analysisResult, setAnalysisResult] = useState(null);

  const [analyzing, setAnalyzing] = useState(false);

  const [analyzerError, setAnalyzerError] = useState("");


  // =========================================================
  // WORKLOAD STATE
  // =========================================================

  const [workload, setWorkload] = useState([]);

  const [workloadLoading, setWorkloadLoading] = useState(false);

  const [workloadError, setWorkloadError] = useState("");


  // =========================================================
  // COMPARE STATE
  // =========================================================

  const [originalQuery, setOriginalQuery] = useState("");

  const [optimizedQuery, setOptimizedQuery] = useState("");

  const [compareResult, setCompareResult] = useState(null);

  const [comparing, setComparing] = useState(false);

  const [compareError, setCompareError] = useState("");


  // =========================================================
  // RECOMMENDATION / APPROVAL STATE
  // =========================================================

  const [recommendations, setRecommendations] = useState([]);

  const [auditLogs, setAuditLogs] = useState([]);

  const [actionLoading, setActionLoading] = useState(false);


  // =========================================================
  // LOAD DASHBOARD
  // =========================================================

  const loadDashboard = async () => {

    try {

      setLoadingDashboard(true);

      const response = await apiFetch(
        `${API}/dashboard-summary`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load dashboard."
        );
      }

      const data = await response.json();

      setDashboard(data);

    } catch (error) {

      console.error(
        "Dashboard error:",
        error
      );

    } finally {

      setLoadingDashboard(false);

    }
  };


  // =========================================================
  // LOAD WORKLOAD
  // =========================================================

  const loadWorkload = async () => {

    try {

      setWorkloadLoading(true);

      setWorkloadError("");

      const response = await apiFetch(
        `${API}/workload-summary`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load workload."
        );
      }

      const data = await response.json();

      setWorkload(
        data.workload || []
      );

    } catch (error) {

      setWorkloadError(
        error.message
      );

    } finally {

      setWorkloadLoading(false);

    }
  };


  // =========================================================
  // LOAD RECOMMENDATIONS
  // =========================================================

  const loadRecommendations = async () => {

    try {

      const response = await apiFetch(
        `${API}/recommendations`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load recommendations."
        );
      }

      const data = await response.json();

      if (Array.isArray(data)) {

        setRecommendations(data);

      } else if (data.recommendations) {

        setRecommendations(
          data.recommendations
        );

      } else {

        setRecommendations([]);

      }

    } catch (error) {

      console.error(
        "Recommendation error:",
        error
      );

    }
  };


  // =========================================================
  // LOAD AUDIT LOGS
  // =========================================================

  const loadAuditLogs = async () => {

    try {

      const response = await apiFetch(
        `${API}/audit-logs`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load audit logs."
        );
      }

      const data = await response.json();

      if (Array.isArray(data)) {

        setAuditLogs(data);

      } else if (data.audit_logs) {

        setAuditLogs(
          data.audit_logs
        );

      } else {

        setAuditLogs([]);

      }

    } catch (error) {

      console.error(
        "Audit error:",
        error
      );

    }
  };


  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    if (!authUser) return;
    loadDashboard();
    loadWorkload();
    loadRecommendations();
    loadAuditLogs();
  }, [authUser]);


  // =========================================================
  // NAVIGATION PAGE DATA REFRESH
  // =========================================================

  useEffect(() => {
    if (!authUser) return;
    if (activePage === "dashboard") {
      loadDashboard();
    }

    if (activePage === "workload") {
      loadWorkload();
    }

    if (activePage === "recommendations") {
      loadRecommendations();
    }

    if (activePage === "approvals") {
      loadRecommendations();
    }

    if (activePage === "audit") {
      loadAuditLogs();
    }

  }, [activePage, authUser]);


  // =========================================================
  // QUERY ANALYZER
  // =========================================================

  const analyzeQuery = async () => {

    if (!query.trim()) {

      setAnalyzerError(
        "Please enter a SQL query."
      );

      return;
    }

    try {

      setAnalyzing(true);

      setAnalyzerError("");

      setAnalysisResult(null);

      const response = await apiFetch(
        `${API}/analyze-query?query=${encodeURIComponent(
          query
        )}`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Query analysis failed."
        );

      }

      setAnalysisResult(data);

      await loadDashboard();
      await loadRecommendations();
      await loadAuditLogs();

    } catch (error) {

      setAnalyzerError(
        error.message
      );

    } finally {

      setAnalyzing(false);

    }
  };


  // =========================================================
  // COMPARE QUERIES
  // =========================================================

  const compareQueries = async () => {

    if (
      !originalQuery.trim() ||
      !optimizedQuery.trim()
    ) {

      setCompareError(
        "Please enter both queries."
      );

      return;
    }

    try {

      setComparing(true);

      setCompareError("");

      setCompareResult(null);

      const url =
        `${API}/compare-queries?` +
        `original_query=${encodeURIComponent(
          originalQuery
        )}` +
        `&optimized_query=${encodeURIComponent(
          optimizedQuery
        )}`;

      const response = await apiFetch(
        url,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Comparison failed."
        );

      }

      setCompareResult(data);

    } catch (error) {

      setCompareError(
        error.message
      );

    } finally {

      setComparing(false);

    }
  };


  // =========================================================
  // APPROVE RECOMMENDATION
  // =========================================================

  const approveRecommendation = async (
    recommendationId
  ) => {
    if (!canManage) {
      alert("Your account role cannot approve recommendations.");
      return;
    }

    try {

      setActionLoading(true);

      const response = await apiFetch(
        `${API}/recommendations/${recommendationId}/approve`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Approval failed."
        );

      }

      await loadRecommendations();
      await loadAuditLogs();
      await loadDashboard();

    } catch (error) {

      alert(error.message);

    } finally {

      setActionLoading(false);

    }
  };


  // =========================================================
  // REJECT RECOMMENDATION
  // =========================================================

  const rejectRecommendation = async (
    recommendationId
  ) => {
    if (!canManage) {
      alert("Your account role cannot reject recommendations.");
      return;
    }

    try {

      setActionLoading(true);

      const response = await apiFetch(
        `${API}/recommendations/${recommendationId}/reject`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Rejection failed."
        );

      }

      await loadRecommendations();
      await loadAuditLogs();
      await loadDashboard();

    } catch (error) {

      alert(error.message);

    } finally {

      setActionLoading(false);

    }
  };


  // =========================================================
  // NAVIGATION
  // =========================================================

  const allNavigation = [
    { id: "dashboard", label: "Dashboard", icon: "◉" },
    { id: "analyzer", label: "Query Analyzer", icon: "⌕" },
    { id: "workload", label: "Workload Intelligence", icon: "◈" },
    { id: "automation", label: "Automation Center", icon: "⚡" },
    { id: "recommendations", label: "AI Recommendations", icon: "✦" },
    { id: "compare", label: "Performance Compare", icon: "⇄" },
    { id: "approvals", label: "Approvals", icon: "✓" },
    { id: "audit", label: "Audit Logs", icon: "▤" }
  ];

  // UI permissions are role-based; backend must enforce these permissions too.
  const userRole = String(authUser?.role || "").toLowerCase();
  const isAdmin = userRole === "admin" || userRole === "administrator";
  const isDBA = userRole === "dba";
  const canManage = isAdmin || isDBA;
  const allowedPageIds = isAdmin
    ? allNavigation.map((item) => item.id)
    : isDBA
      ? ["dashboard", "analyzer", "workload", "automation", "recommendations", "compare", "approvals", "audit"]
      : ["dashboard", "workload", "recommendations", "audit"];
  const navigation = allNavigation.filter((item) => allowedPageIds.includes(item.id));


  // =========================================================
  // HELPER FUNCTIONS
  // =========================================================

  const formatNumber = (value) => {

    if (
      value === null ||
      value === undefined
    ) {
      return "0";
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
      return "0";
    }

    return number.toFixed(2);

  };


  const formatDate = (value) => {

    if (!value) {
      return "N/A";
    }

    try {

      return new Date(
        value
      ).toLocaleString();

    } catch {

      return value;

    }
  };


  const getPriorityClass = (
    priority
  ) => {

    if (
      priority === "Critical"
    ) {
      return "priority-critical";
    }

    if (
      priority === "High"
    ) {
      return "priority-high";
    }

    if (
      priority === "Medium"
    ) {
      return "priority-medium";
    }

    return "priority-low";
  };


  const getSeverityClass = (
    severity
  ) => {

    if (severity === "High") {
      return "severity-high";
    }

    if (severity === "Medium") {
      return "severity-medium";
    }

    return "severity-low";
  };


  // =========================================================
  // DASHBOARD
  // =========================================================

  const renderDashboard = () => {

    const summary =
      dashboard.summary || {};

    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              DATABASE PERFORMANCE INTELLIGENCE
            </div>

            <h1>
              Gen-DBA Dashboard
            </h1>

            <p>
              AI-assisted SQL performance
              monitoring and optimization.
            </p>

          </div>

          <div className="dashboard-live">
            <span className="live-dot"></span>
            System Online
          </div>

        </div>


        <div className="stats-grid">

          <div className="stat-card">

            <span className="stat-label">
              TOTAL QUERIES
            </span>

            <strong className="stat-value">
              {summary.total_queries || 0}
            </strong>

            <span className="stat-sub">
              Analyzed workload
            </span>

          </div>


          <div className="stat-card">

            <span className="stat-label">
              HIGH RISK
            </span>

            <strong className="stat-value">
              {summary.high_risk_queries || 0}
            </strong>

            <span className="stat-sub">
              Queries requiring attention
            </span>

          </div>


          <div className="stat-card">

            <span className="stat-label">
              PENDING APPROVALS
            </span>

            <strong className="stat-value">
              {summary.pending_recommendations || 0}
            </strong>

            <span className="stat-sub">
              Waiting for DBA
            </span>

          </div>


          <div className="stat-card">

            <span className="stat-label">
              AVG EXECUTION
            </span>

            <strong className="stat-value">
              {formatNumber(
                summary.average_execution_time
              )} ms
            </strong>

            <span className="stat-sub">
              Average workload time
            </span>

          </div>

        </div>


        <div className="dashboard-grid">

          <div className="dashboard-panel">

            <div className="panel-heading">

              <div>

                <div className="panel-kicker">
                  WORKLOAD
                </div>

                <h2>
                  Top Query Impact
                </h2>

              </div>

              <button
                className="refresh-button"
                onClick={() => {
                  loadDashboard();
                  loadWorkload();
                }}
              >
                ↻ Refresh
              </button>

            </div>


            <div className="table-wrapper">

              <table className="data-table">

                <thead>

                  <tr>

                    <th>QUERY</th>
                    <th>TIME</th>
                    <th>RISK</th>
                    <th>PRIORITY</th>

                  </tr>

                </thead>

                <tbody>

                  {(
                    dashboard.top_queries || []
                  ).length === 0 ? (

                    <tr>

                      <td colSpan="4">
                        No query data available.
                      </td>

                    </tr>

                  ) : (

                    dashboard.top_queries
                      .slice(0, 6)
                      .map(
                        (item, index) => (

                          <tr
                            key={
                              item.query ||
                              index
                            }
                          >

                            <td className="query-cell">
                              {item.query ||
                                item.query_text ||
                                "N/A"}
                            </td>

                            <td>
                              {formatNumber(
                                item.average_execution_time ||
                                item.avg_execution_time ||
                                0
                              )}{" "}
                              ms
                            </td>

                            <td>
                              {formatNumber(
                                item.risk_score || 0
                              )}
                            </td>

                            <td>

                              <span
                                className={`priority-badge ${getPriorityClass(
                                  item.priority
                                )}`}
                              >
                                {item.priority ||
                                  "Low"}
                              </span>

                            </td>

                          </tr>

                        )
                      )

                  )}

                </tbody>

              </table>

            </div>

          </div>


          <div className="dashboard-panel ai-dashboard-panel">

            <div className="panel-kicker">
              AI INTELLIGENCE
            </div>

            <h2>
              Explainable Optimization
            </h2>

            <p className="ai-dashboard-text">
              Gen-DBA analyzes execution plans,
              detects performance issues and
              generates explainable optimization
              recommendations using Gemini.
            </p>


            <div className="ai-flow">

              <div className="ai-flow-item">
                <span>01</span>
                Detect
              </div>

              <div className="ai-flow-item">
                <span>02</span>
                Analyze
              </div>

              <div className="ai-flow-item">
                <span>03</span>
                Recommend
              </div>

              <div className="ai-flow-item">
                <span>04</span>
                Approve
              </div>

            </div>

          </div>

        </div>


        <div className="dashboard-panel">

          <div className="panel-heading">

            <div>

              <div className="panel-kicker">
                RECENT ACTIVITY
              </div>

              <h2>
                AI Recommendations
              </h2>

            </div>

          </div>


          <div className="recommendation-list">

            {(
              dashboard.recent_recommendations || []
            ).length === 0 ? (

              <div className="empty-state">
                No recent recommendations.
              </div>

            ) : (

              dashboard.recent_recommendations
                .map(
                  (rec, index) => (

                    <div
                      className="recommendation-item"
                      key={
                        rec.recommendation_id ||
                        index
                      }
                    >

                      <div className="recommendation-number">
                        {index + 1}
                      </div>

                      <div className="recommendation-content">

                        <strong>
                          Recommendation #
                          {
                            rec.recommendation_id
                          }
                        </strong>

                        <p>
                          {(
                            rec.recommendation_text ||
                            "Optimization recommendation available."
                          ).slice(
                            0,
                            220
                          )}
                        </p>

                      </div>

                      <span
                        className={`status-badge ${
                          rec.status ===
                          "APPROVED"
                            ? "status-approved"
                            : rec.status ===
                              "REJECTED"
                            ? "status-rejected"
                            : "status-pending"
                        }`}
                      >
                        {rec.status ||
                          "PENDING"}
                      </span>

                    </div>

                  )
                )

            )}

          </div>

        </div>

      </div>

    );

  };


  // =========================================================
  // QUERY ANALYZER
  // =========================================================

  const renderAnalyzer = () => {

    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              SQL INTELLIGENCE
            </div>

            <h1>
              Query Analyzer
            </h1>

            <p>
              Analyze SQL execution behaviour,
              detect issues and get AI recommendations.
            </p>

          </div>

        </div>


        <div className="analyzer-layout">

          <div className="analyzer-input-panel">

            <div className="panel-kicker">
              SQL QUERY
            </div>

            <h2>
              Analyze a Query
            </h2>

            <textarea
              className="sql-editor"
              value={query}
              onChange={(e) =>
                setQuery(e.target.value)
              }
              placeholder={
                "SELECT * FROM users WHERE LOWER(city) = 'pune';"
              }
            />

            <button
              className="primary-button"
              onClick={analyzeQuery}
              disabled={analyzing}
            >
              {analyzing
                ? "Analyzing..."
                : "Analyze Query →"}
            </button>

            {analyzerError && (

              <div className="error-message">
                {analyzerError}
              </div>

            )}

          </div>


          {analysisResult && (

            <div className="analysis-result-panel">

              <div className="panel-kicker">
                ANALYSIS RESULT
              </div>

              <h2>
                Performance Findings
              </h2>


              <div className="analysis-score-grid">

                <div className="analysis-score-card">

                  <span>
                    RISK SCORE
                  </span>

                  <strong>
                    {formatNumber(
                      analysisResult.risk_score
                    )}
                  </strong>

                </div>


                <div className="analysis-score-card">

                  <span>
                    EXECUTION TIME
                  </span>

                  <strong>
                    {formatNumber(
                      analysisResult.execution_time
                    )}{" "}
                    ms
                  </strong>

                </div>


                <div className="analysis-score-card">

                  <span>
                    IMPACT SCORE
                  </span>

                  <strong>
                    {formatNumber(
                      analysisResult.impact_score
                    )}
                  </strong>

                </div>

              </div>


              <div className="issues-section">

                <div className="panel-kicker">
                  DETECTED ISSUES
                </div>

                {(
                  analysisResult.issues || []
                ).length === 0 ? (

                  <div className="empty-state">
                    No major issues detected.
                  </div>

                ) : (

                  analysisResult.issues.map(
                    (issue, index) => (

                      <div
                        className="issue-card"
                        key={index}
                      >

                        <div className="issue-top">

                          <strong>
                            {
                              issue.issue_type ||
                              "Performance Issue"
                            }
                          </strong>

                          <span
                            className={`severity-badge ${getSeverityClass(
                              issue.severity
                            )}`}
                          >
                            {issue.severity}
                          </span>

                        </div>

                        <p>
                          {
                            issue.explanation ||
                            "No explanation available."
                          }
                        </p>

                        <small>
                          Suggested action:{" "}
                          {
                            issue.suggested_action ||
                            "Review execution plan."
                          }
                        </small>

                      </div>

                    )
                  )

                )}

              </div>


              <div className="ai-recommendation-box">

                <div className="ai-box-title">
                  ✦ Gemini Recommendation
                </div>

                <p>
                  {analysisResult.ai_recommendation ||
                    "No AI recommendation returned."}
                </p>

              </div>

            </div>

          )}

        </div>

      </div>

    );

  };


  // =========================================================
  // WORKLOAD
  // =========================================================

  const renderWorkload = () => {

    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              WORKLOAD INTELLIGENCE
            </div>

            <h1>
              Query Prioritization
            </h1>

            <p>
              Queries ranked by workload impact,
              risk and frequency.
            </p>

          </div>

          <button
            className="refresh-button"
            onClick={loadWorkload}
          >
            ↻ Refresh
          </button>

        </div>


        {workloadError && (

          <div className="error-message">
            {workloadError}
          </div>

        )}


        <div className="dashboard-panel">

          {workloadLoading ? (

            <div className="empty-state">
              Loading workload...
            </div>

          ) : (

            <div className="table-wrapper">

              <table className="data-table">

                <thead>

                  <tr>

                    <th>#</th>
                    <th>QUERY</th>
                    <th>FREQUENCY</th>
                    <th>AVG TIME</th>
                    <th>IMPACT</th>
                    <th>RISK</th>
                    <th>PRIORITY</th>

                  </tr>

                </thead>

                <tbody>

                  {workload.length === 0 ? (

                    <tr>

                      <td colSpan="7">
                        No workload data available.
                      </td>

                    </tr>

                  ) : (

                    workload.map(
                      (item, index) => (

                        <tr key={index}>

                          <td>
                            {item.rank ||
                              index + 1}
                          </td>

                          <td className="query-cell">
                            {item.query ||
                              item.query_text}
                          </td>

                          <td>
                            {
                              item.frequency
                            }
                          </td>

                          <td>
                            {formatNumber(
                              item.average_execution_time ||
                              item.avg_execution_time
                            )}{" "}
                            ms
                          </td>

                          <td>
                            {formatNumber(
                              item.impact_score
                            )}
                          </td>

                          <td>
                            {formatNumber(
                              item.risk_score
                            )}
                          </td>

                          <td>

                            <span
                              className={`priority-badge ${getPriorityClass(
                                item.priority
                              )}`}
                            >
                              {
                                item.priority ||
                                "Low"
                              }
                            </span>

                          </td>

                        </tr>

                      )
                    )

                  )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      </div>

    );

  };


  // =========================================================
  // RECOMMENDATIONS
  // =========================================================

  const renderRecommendations = () => {

    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              AI OPTIMIZATION ENGINE
            </div>

            <h1>
              AI Recommendations
            </h1>

            <p>
              Explainable optimization suggestions
              generated from query analysis.
            </p>

          </div>

          <button
            className="refresh-button"
            onClick={loadRecommendations}
          >
            ↻ Refresh
          </button>

        </div>


        <div className="recommendations-grid">

          {recommendations.length === 0 ? (

            <div className="dashboard-panel empty-state">
              No recommendations available.
            </div>

          ) : (

            recommendations.map(
              (rec, index) => (

                <div
                  className="recommendation-large-card"
                  key={
                    rec.recommendation_id ||
                    index
                  }
                >

                  <div className="recommendation-card-top">

                    <span className="recommendation-id">
                      #{rec.recommendation_id}
                    </span>

                    <span
                      className={`status-badge ${
                        rec.status ===
                        "APPROVED"
                          ? "status-approved"
                          : rec.status ===
                            "REJECTED"
                          ? "status-rejected"
                          : "status-pending"
                      }`}
                    >
                      {rec.status ||
                        "PENDING"}
                    </span>

                  </div>

                  <div className="recommendation-risk">
                    Risk:{" "}
                    <strong>
                      {rec.risk_level ||
                        "Low"}
                    </strong>
                  </div>

                  <div className="recommendation-text">

                    {rec.recommendation_text ||
                      "No recommendation text available."}

                  </div>

                  <div className="recommendation-date">
                    Created:{" "}
                    {formatDate(
                      rec.created_at
                    )}
                  </div>

                </div>

              )
            )

          )}

        </div>

      </div>

    );

  };


  // =========================================================
  // PERFORMANCE COMPARE
  // =========================================================

  const renderCompare = () => {

    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              PERFORMANCE VALIDATION
            </div>

            <h1>
              Performance Compare
            </h1>

            <p>
              Benchmark original and optimized
              queries before approval.
            </p>

          </div>

        </div>


        <div className="compare-input-grid">

          <div className="dashboard-panel">

            <div className="panel-kicker">
              ORIGINAL QUERY
            </div>

            <textarea
              className="sql-editor"
              value={originalQuery}
              onChange={(e) =>
                setOriginalQuery(
                  e.target.value
                )
              }
              placeholder={
                "SELECT * FROM users WHERE LOWER(city) = 'pune';"
              }
            />

          </div>


          <div className="dashboard-panel">

            <div className="panel-kicker">
              OPTIMIZED QUERY
            </div>

            <textarea
              className="sql-editor"
              value={optimizedQuery}
              onChange={(e) =>
                setOptimizedQuery(
                  e.target.value
                )
              }
              placeholder={
                "SELECT * FROM users WHERE city = 'Pune';"
              }
            />

          </div>

        </div>


        <button
          className="primary-button"
          onClick={compareQueries}
          disabled={comparing}
        >
          {comparing
            ? "Benchmarking..."
            : "Run Performance Comparison →"}
        </button>


        {compareError && (

          <div className="error-message">
            {compareError}
          </div>

        )}


        {compareResult && (

          <div className="dashboard-panel compare-result-panel">

            <div className="panel-kicker">
              BENCHMARK RESULT
            </div>

            <h2>
              Performance Comparison
            </h2>


            <div className="comparison-score-grid">

              <div className="comparison-card">

                <span>
                  ORIGINAL MEDIAN
                </span>

                <strong>
                  {formatNumber(
                    compareResult.original_median_time
                  )}{" "}
                  ms
                </strong>

              </div>


              <div className="comparison-card">

                <span>
                  OPTIMIZED MEDIAN
                </span>

                <strong>
                  {formatNumber(
                    compareResult.optimized_median_time
                  )}{" "}
                  ms
                </strong>

              </div>


              <div className="comparison-card improvement-card">

                <span>
                  IMPROVEMENT
                </span>

                <strong>
                  {formatNumber(
                    compareResult.improvement_percentage
                  )}%
                </strong>

              </div>

            </div>


            <div className="comparison-status">

              Performance Status:{" "}

              <strong>
                {
                  compareResult.performance_status ||
                  compareResult.validation_status ||
                  "Completed"
                }
              </strong>

            </div>


            <div className="benchmark-runs">

              <div className="panel-kicker">
                BENCHMARK RUNS
              </div>

              <div className="run-columns">

                <div>

                  <h3>
                    Original
                  </h3>

                  {(compareResult.original_execution_times || [])
                    .map(
                      (time, index) => (
                        <div
                          className="run-item"
                          key={index}
                        >
                          Run {index + 1}:{" "}
                          {formatNumber(time)} ms
                        </div>
                      )
                    )}

                </div>


                <div>

                  <h3>
                    Optimized
                  </h3>

                  {(compareResult.optimized_execution_times || [])
                    .map(
                      (time, index) => (
                        <div
                          className="run-item"
                          key={index}
                        >
                          Run {index + 1}:{" "}
                          {formatNumber(time)} ms
                        </div>
                      )
                    )}

                </div>

              </div>

            </div>

          </div>

        )}

      </div>

    );

  };


  // =========================================================
  // APPROVALS
  // =========================================================

  const renderApprovals = () => {

    const pending =
      recommendations.filter(
        (rec) =>
          rec.status === "PENDING"
      );

    const approved =
      recommendations.filter(
        (rec) =>
          rec.status === "APPROVED"
      );

    const rejected =
      recommendations.filter(
        (rec) =>
          rec.status === "REJECTED"
      );


    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              HUMAN-IN-THE-LOOP
            </div>

            <h1>
              DBA Approvals
            </h1>

            <p>
              Review AI recommendations before
              any database optimization action.
            </p>

          </div>

          <button
            className="refresh-button"
            onClick={loadRecommendations}
          >
            ↻ Refresh
          </button>

        </div>


        <div className="approval-stats">

          <div className="approval-stat pending">
            <span>
              PENDING REVIEW
            </span>

            <strong>
              {pending.length}
            </strong>
          </div>

          <div className="approval-stat approved">
            <span>
              APPROVED
            </span>

            <strong>
              {approved.length}
            </strong>
          </div>

          <div className="approval-stat rejected">
            <span>
              REJECTED
            </span>

            <strong>
              {rejected.length}
            </strong>
          </div>

        </div>


        <div className="approval-list">

          {pending.length === 0 ? (

            <div className="dashboard-panel empty-state">
              No pending recommendations.
            </div>

          ) : (

            pending.map(
              (rec) => (

                <div
                  className="approval-card"
                  key={
                    rec.recommendation_id
                  }
                >

                  <div className="approval-header">

                    <div>

                      <div className="panel-kicker">
                        RECOMMENDATION
                      </div>

                      <h2>
                        #
                        {
                          rec.recommendation_id
                        }
                      </h2>

                    </div>

                    <span className="status-badge status-pending">
                      PENDING
                    </span>

                  </div>


                  <div className="approval-risk">

                    Risk Level:{" "}

                    <strong>
                      {rec.risk_level ||
                        "Low"}
                    </strong>

                  </div>


                  <div className="approval-recommendation">

                    {
                      rec.recommendation_text ||
                      "No recommendation text."
                    }

                  </div>


                  {(["admin", "dba"].includes(String(authUser.role || "").toLowerCase())) && <div className="approval-actions">

                    <button
                      className="approve-button"
                      onClick={() =>
                        approveRecommendation(
                          rec.recommendation_id
                        )
                      }
                      disabled={actionLoading}
                    >
                      ✓ Approve
                    </button>


                    <button
                      className="reject-button"
                      onClick={() =>
                        rejectRecommendation(
                          rec.recommendation_id
                        )
                      }
                      disabled={actionLoading}
                    >
                      × Reject
                    </button>

                  </div>}

                </div>

              )
            )

          )}

        </div>


        {!(["admin", "dba"].includes(String(authUser.role || "").toLowerCase())) && <div className="approval-safety-box"><strong>Read-only access</strong><p>Your account role can review recommendations but cannot approve or reject them.</p></div>}

        <div className="approval-safety-box">

          <strong>
            🔐 Controlled Execution
          </strong>

          <p>
            Approval only records the DBA decision.
            Gen-DBA does not automatically modify
            the database.
          </p>

        </div>

      </div>

    );

  };


  // =========================================================
  // AUDIT LOGS
  // =========================================================

  const renderAudit = () => {

    return (

      <div className="page-content">

        <div className="page-header">

          <div>

            <div className="page-kicker">
              GOVERNANCE
            </div>

            <h1>
              Audit Logs
            </h1>

            <p>
              Complete history of automated and
              DBA actions.
            </p>

          </div>

          <button
            className="refresh-button"
            onClick={loadAuditLogs}
          >
            ↻ Refresh
          </button>

        </div>


        <div className="dashboard-panel">

          {auditLogs.length === 0 ? (

            <div className="empty-state">
              No audit logs available.
            </div>

          ) : (

            <div className="audit-timeline">

              {auditLogs.map(
                (log, index) => (

                  <div
                    className="audit-item"
                    key={
                      log.audit_id ||
                      index
                    }
                  >

                    <div className="audit-marker">
                      ✓
                    </div>

                    <div className="audit-content">

                      <div className="audit-top">

                        <strong>
                          {
                            log.action ||
                            "ACTION"
                          }
                        </strong>

                        <span>
                          {formatDate(
                            log.created_at
                          )}
                        </span>

                      </div>

                      <p>
                        {
                          log.details ||
                          "No details available."
                        }
                      </p>

                      <small>
                        Performed by:{" "}
                        {
                          log.performed_by ||
                          "DBA"
                        }
                      </small>

                    </div>

                  </div>

                )
              )}

            </div>

          )}

        </div>

      </div>

    );

  };


  // =========================================================
  // MAIN PAGE SWITCH
  // =========================================================

  const renderPage = () => {
    if (!allowedPageIds.includes(activePage)) {
      return renderDashboard();
    }

    switch (activePage) {

      case "dashboard":
        return renderDashboard();

      case "analyzer":
        return renderAnalyzer();

      case "workload":
        return renderWorkload();

      case "automation":
        return canManage ? <AutomationCenter /> : renderDashboard();

      case "recommendations":
        return renderRecommendations();

      case "compare":
        return renderCompare();

      case "approvals":
        return renderApprovals();

      case "audit":
        return renderAudit();

      default:
        return renderDashboard();

    }

  };


  // =========================================================
  // APP LAYOUT
  // =========================================================

  if (!authUser) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, background: "#080d18", color: "#e8edf7", fontFamily: "Inter, system-ui, sans-serif" }}>
        <form onSubmit={handleLogin} style={{ width: "100%", maxWidth: 420, boxSizing: "border-box", padding: 32, border: "1px solid #26344b", borderRadius: 18, background: "#111a2a", boxShadow: "0 24px 70px rgba(0,0,0,.35)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 26 }}>
            <div style={{ width: 44, height: 44, display: "grid", placeItems: "center", borderRadius: 12, background: "#263b60", color: "#8fb8ff", fontSize: 24, fontWeight: 800 }}>G</div>
            <div><div style={{ fontSize: 23, fontWeight: 750 }}>Gen-DBA</div><div style={{ color: "#98a9c4", fontSize: 13 }}>SQL Intelligence · Secure Login</div></div>
          </div>
          <h2 style={{ margin: "0 0 8px", fontSize: 22 }}>Welcome back</h2>
          <p style={{ margin: "0 0 24px", color: "#98a9c4", fontSize: 14 }}>Sign in to access the performance dashboard.</p>
          <label style={{ display: "block", marginBottom: 7, color: "#cbd5e5", fontSize: 13 }}>Username</label>
          <input autoComplete="username" value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} required style={{ width: "100%", boxSizing: "border-box", padding: "12px 13px", marginBottom: 17, borderRadius: 9, border: "1px solid #34435c", background: "#0a1220", color: "#f4f7ff", outline: "none" }} />
          <label style={{ display: "block", marginBottom: 7, color: "#cbd5e5", fontSize: 13 }}>Password</label>
          <input type="password" autoComplete="current-password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} required style={{ width: "100%", boxSizing: "border-box", padding: "12px 13px", marginBottom: 18, borderRadius: 9, border: "1px solid #34435c", background: "#0a1220", color: "#f4f7ff", outline: "none" }} />
          {loginError && <div role="alert" style={{ padding: 11, marginBottom: 16, borderRadius: 8, background: "#421f2b", color: "#ffb9c4", fontSize: 13 }}>{loginError}</div>}
          <button type="submit" disabled={loginLoading} style={{ width: "100%", padding: 13, border: 0, borderRadius: 9, background: loginLoading ? "#40506a" : "#477fe8", color: "white", fontWeight: 700, cursor: loginLoading ? "wait" : "pointer" }}>{loginLoading ? "Signing in…" : "Sign in →"}</button>
          <p style={{ margin: "18px 0 0", color: "#7f91ad", fontSize: 12, lineHeight: 1.5 }}>Access is controlled by your Gen-DBA account role. Do not share your password.</p>
        </form>
      </div>
    );
  }

  return (

    <div className="app-shell">


      {/* =====================================================
          SIDEBAR
      ===================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-logo">
            G
          </div>

          <div className="brand-text">

            <strong>
              Gen-DBA
            </strong>

            <span>
              SQL Intelligence
            </span>

          </div>

        </div>


        <div className="sidebar-section-title">
          MAIN
        </div>


        <nav className="navigation">

          {navigation.map(
            (item) => (

              <button
                key={item.id}
                className={
                  activePage === item.id
                    ? "nav-item active"
                    : "nav-item"
                }
                onClick={() =>
                  setActivePage(
                    item.id
                  )
                }
              >

                <span className="nav-icon">
                  {item.icon}
                </span>

                <span>
                  {item.label}
                </span>

              </button>

            )
          )}

        </nav>


        <div className="sidebar-bottom">

          <div className="system-status">

            <span className="live-dot"></span>

            <div>

              <strong>
                System Active
              </strong>

              <span>
                Monitoring enabled
              </span>

            </div>

          </div>

          <div className="sidebar-version">
            Gen-DBA v1.0
          </div>

        </div>

      </aside>


      {/* =====================================================
          MAIN AREA
      ===================================================== */}

      <main className="main-area">


        {/* ===================================================
            TOP BAR
        =================================================== */}

        <header className="topbar">

          <div className="topbar-left">

            <span className="topbar-path">
              Gen-DBA
            </span>

            <span className="topbar-separator">
              /
            </span>

            <span className="topbar-current">
              {
                navigation.find(
                  (item) =>
                    item.id === activePage
                )?.label ||
                "Dashboard"
              }
            </span>

          </div>


          <div className="topbar-right">

            <div className="topbar-ai-status">

              <span className="live-dot"></span>

              Gemini AI Connected

            </div>


            <div className="user-badge">
              <div className="user-avatar">{(authUser.username || "U").charAt(0).toUpperCase()}</div>
              <div>
                <strong>{authUser.username}</strong>
                <span>{authUser.role}</span>
              </div>
            </div>
            <button type="button" onClick={handleLogout} title="Sign out" style={{ marginLeft: 12, padding: "9px 12px", border: "1px solid #34435c", borderRadius: 8, background: "transparent", color: "#d5deed", cursor: "pointer" }}>Logout</button>

          </div>

        </header>


        {/* ===================================================
            PAGE
        =================================================== */}

        <section className="content-area">

          {loadingDashboard &&
          activePage === "dashboard" ? (

            <div className="loading-screen">
              Loading Gen-DBA...
            </div>

          ) : (

            renderPage()

          )}

        </section>

      </main>

    </div>

  );

}


export default App;