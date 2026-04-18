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
 *
 * Auth (v18e): every request attaches the stored JWT as
 * `Authorization: Bearer <token>` if a token is present. Token lives in
 * localStorage under `marketlens:auth:v1` as a JSON blob with
 * { token, username, role, expiresAt }. A 401 response anywhere clears
 * the token and (via a pluggable onUnauthorized callback set by the app
 * shell) redirects to /login. A 403 indicates wrong role — surfaced as a
 * normal error, not a logout trigger, because the token is still valid.
 */

const API_BASE = "/api";
const AUTH_STORAGE_KEY = "marketlens:auth:v1";

// The app shell sets this callback (see DiagnosisApp / EditorApp / LoginApp)
// so api.js can trigger a redirect to /login without knowing about React
// routing. Kept as a simple module-level variable rather than a more
// elaborate event bus; there's one React tree at a time.
let _onUnauthorized = null;

export function setUnauthorizedHandler(fn) {
  _onUnauthorized = fn;
}

// ─── Auth token storage ───
//
// localStorage is intentionally used rather than sessionStorage: a pitch
// demo often involves showing the tool, closing the tab, coming back a
// few minutes later. Keeping the token in localStorage survives that.
// The JWT has a 24-hour expiry enforced server-side regardless.

export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Don't hand back clearly expired tokens; treat as no auth.
    if (parsed.expiresAt && parsed.expiresAt < Date.now()) {
      clearStoredAuth();
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function setStoredAuth(auth) {
  // auth = { token, username, role }  — we add expiresAt client-side as
  // a best-effort (23h window; server enforces the real 24h expiry)
  const enriched = { ...auth, expiresAt: Date.now() + 23 * 60 * 60 * 1000 };
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(enriched));
}

export function clearStoredAuth() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

async function apiRequest(endpoint, options = {}) {
  const auth = getStoredAuth();
  const headers = {
    "Content-Type": "application/json",
    ...(auth?.token ? { Authorization: `Bearer ${auth.token}` } : {}),
    ...options.headers,
  };
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (!res.ok) {
      let detail = `Request failed with status ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch {
        // Response wasn't JSON. Stick with the status-code message.
      }
      // 401 → token missing/expired/invalid. Clear local auth and notify
      // the app shell (which will redirect to /login).
      if (res.status === 401) {
        clearStoredAuth();
        if (_onUnauthorized) _onUnauthorized();
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

// ─── Auth endpoints ───

export async function fetchDemoUsers() {
  return apiRequest("/auth/demo-users");
}

export async function login(username, password) {
  const result = await apiRequest("/auth/login-v2", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (result.data) {
    setStoredAuth({
      token: result.data.token,
      username: result.data.username,
      role: result.data.role,
    });
  }
  return result;
}

export function logout() {
  clearStoredAuth();
  if (_onUnauthorized) _onUnauthorized();
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

// ─── Scenarios screen ───

/**
 * Fetch the list of scenario presets the backend offers (Current,
 * Cut 20%, Increase 25%, Optimizer recommended). Computed dynamically
 * from current spend, so they always make sense for whatever data is
 * loaded.
 */
export async function fetchScenarioPresets() {
  return apiRequest("/scenario/presets");
}

/**
 * Fetch a scenario at a specific budget level. Returns the same payload
 * shape as fetchPlan plus a `comparison` block (scenario vs. baseline).
 */
export async function fetchScenario(opts = {}) {
  const params = new URLSearchParams();
  if (opts.totalBudget != null) params.set("total_budget", String(opts.totalBudget));
  if (opts.objective) params.set("objective", opts.objective);
  if (opts.view) params.set("view", opts.view);
  return apiRequest(`/scenario?${params.toString()}`);
}

/**
 * Cold-start variant: ensure analysis has run, fetch the current-spend
 * baseline scenario as the screen's initial state. Subsequent preset
 * clicks call fetchScenario directly.
 */
export async function ensureScenarioReady(view = "client", opts = {}) {
  let { data, error } = await fetchScenario({ ...opts, view });
  if (data) return { data, error: null };

  if (error && error.kind === "http" && error.status === 400) {
    const mock = await loadMockData();
    if (mock.error) return { data: null, error: mock.error };
    const analysis = await runAnalysis();
    if (analysis.error) return { data: null, error: analysis.error };
    return await fetchScenario({ ...opts, view });
  }

  return { data: null, error };
}
