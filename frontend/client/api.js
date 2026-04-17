/**
 * MarketLens API client.
 *
 * Thin fetch wrapper around the backend. Lives separately from the existing
 * analyst app's API layer so the two don't accidentally share assumptions
 * (the client app has stricter error UX -- we can't just console.warn and
 * render a half-broken screen in front of a Partner).
 *
 * Conventions:
 * - All calls are async, return { data, error } rather than throwing.
 * - Error states carry a human-readable message suitable for UI display.
 * - Network errors and HTTP errors are reported distinctly so the UI can
 *   differentiate "can't reach server" vs "server returned 400."
 */

const API_BASE = "/api";

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
    if (!res.ok) {
      let detail = `Request failed with status ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch {
        // Response wasn't JSON. Stick with the status-code message.
      }
      return { data: null, error: { kind: "http", status: res.status, message: detail } };
    }
    const data = await res.json();
    return { data, error: null };
  } catch (e) {
    return {
      data: null,
      error: { kind: "network", message: e.message || "Network error" },
    };
  }
}

export async function fetchDiagnosis(view = "client") {
  return apiRequest(`/diagnosis?view=${encodeURIComponent(view)}`);
}

/**
 * Fetch the Plan screen payload. Like fetchDiagnosis, supports view switching.
 *
 * Optional params:
 *   totalBudget — if provided, re-optimizes at this budget before returning
 *     the plan. If omitted, the backend picks a sensible default (current
 *     spend + 5%). This matters because the Plan is the action-side of the
 *     diagnosis: there's always an implicit "at what budget level?" question,
 *     and leaving it implicit on first load is the right default.
 *   objective — optimizer objective ("balanced" | "max_revenue" | "max_roi").
 *     Defaults to "balanced" which the backend understands.
 */
export async function fetchPlan(view = "client", opts = {}) {
  const params = new URLSearchParams({ view });
  if (opts.totalBudget != null) params.set("total_budget", String(opts.totalBudget));
  if (opts.objective) params.set("objective", opts.objective);
  return apiRequest(`/plan?${params.toString()}`);
}

export async function loadMockData() {
  return apiRequest("/load-mock-data", { method: "POST" });
}

export async function runAnalysis() {
  return apiRequest("/run-analysis", { method: "POST" });
}

// ─── Editor overlay endpoints ───
//
// These mutate state in the persistence layer. Only the editor entry
// point calls them; the client app never does. No auth yet — the split
// relies on the editor entry point being the only caller.

export async function saveCommentary(findingKey, text, author = null) {
  return apiRequest("/editor/commentary", {
    method: "POST",
    body: JSON.stringify({ finding_key: findingKey, text, author }),
  });
}

export async function deleteCommentary(findingKey, author = null) {
  const qs = author ? `?author=${encodeURIComponent(author)}` : "";
  return apiRequest(
    `/editor/commentary/${encodeURIComponent(findingKey)}${qs}`,
    { method: "DELETE" },
  );
}

export async function suppressFinding(findingKey, reason, author = null) {
  return apiRequest("/editor/suppress", {
    method: "POST",
    body: JSON.stringify({ finding_key: findingKey, reason, author }),
  });
}

export async function unsuppressFinding(findingKey, author = null) {
  const qs = author ? `?author=${encodeURIComponent(author)}` : "";
  return apiRequest(
    `/editor/suppress/${encodeURIComponent(findingKey)}${qs}`,
    { method: "DELETE" },
  );
}

export async function fetchAuditLog(limit = 50) {
  return apiRequest(`/editor/audit-log?limit=${limit}`);
}

/**
 * Combined "cold-start" helper: ensures mock data is loaded and analysis
 * has run, then fetches the diagnosis. Used when the client app boots
 * against a fresh backend (e.g., a dev environment or a demo deploy that
 * doesn't have a persisted analysis yet).
 *
 * In the real product, data loading happens on the EY-editor side before
 * the client ever sees the surface; the client-side fetchDiagnosis() call
 * alone is sufficient.
 */
export async function ensureDiagnosisReady(view = "client") {
  // Try diagnosis first — if it works, no cold-start needed.
  let { data, error } = await fetchDiagnosis(view);
  if (data) return { data, error: null };

  // Diagnosis failed because analysis hasn't run. Cold-start.
  if (error && error.kind === "http" && error.status === 400) {
    const mock = await loadMockData();
    if (mock.error) return { data: null, error: mock.error };
    const analysis = await runAnalysis();
    if (analysis.error) return { data: null, error: analysis.error };
    return await fetchDiagnosis(view);
  }

  return { data: null, error };
}

/**
 * Plan screen equivalent of ensureDiagnosisReady. Handles the same
 * cold-start path (load mock → run analysis → retry) and passes through
 * budget/objective opts to fetchPlan.
 */
export async function ensurePlanReady(view = "client", opts = {}) {
  let { data, error } = await fetchPlan(view, opts);
  if (data) return { data, error: null };

  if (error && error.kind === "http" && error.status === 400) {
    const mock = await loadMockData();
    if (mock.error) return { data: null, error: mock.error };
    const analysis = await runAnalysis();
    if (analysis.error) return { data: null, error: analysis.error };
    return await fetchPlan(view, opts);
  }

  return { data: null, error };
}
