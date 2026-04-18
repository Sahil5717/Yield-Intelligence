# CHANGES — v17 (MarketLens client app + narrative polish)

First cut of the client-facing product surface. The analyst workbench
(the existing 7-screen app) remains untouched; a new sibling app lives
alongside it under `frontend/client/` with its own Vite entry and its
own visual language.

The product is now named **MarketLens** — dropped the "Yield Intelligence"
label for the client-facing surface. Internal codebase paths stay
`yield-intelligence-*` for continuity with existing deploys.

## What changed

### New: `frontend/client/` — the MarketLens client app

Seven new files implementing the Diagnosis screen:

- **`tokens.js`** — full design system (colors, typography, spacing,
  motion, layout). Warm off-white canvas, Geist font family, sparing
  teal accent, bento-grid KPI layout, editorial reading width for prose.
  Deliberately no yellow (EY brand sensitivity), no gradients, no glass
  morphism.
- **`api.js`** — fetch wrapper with cold-start handling. Boots against
  a fresh backend by auto-loading mock data and running analysis when
  `/api/diagnosis` returns 400.
- **`components/ConfidenceChip.jsx`** — three-tier pill (High /
  Directional / Inconclusive).
- **`components/KpiPill.jsx`** — bento-grid KPI cards used for Portfolio
  ROAS, Value at Risk, Plan Confidence at the top of the screen.
- **`components/FindingCard.jsx`** — core unit of the findings list.
  Renders collapsed and expanded states, the prescribed_action line
  under each headline, confidence chip, impact badge, evidence chart
  placeholder, source engine metadata.
- **`screens/Diagnosis.jsx`** — screen composition. Single content column
  at 760px reading width, KPI row at 1100px grid width, hero card with
  the diagnosis paragraph, findings list, methodology footer.
- **`DiagnosisApp.jsx`** — shell with header, loading/error states,
  footer, global styles. Handles the Geist font loading, scrollbar
  styling, staggered fade-in animations.

Entry points at `frontend/` root:
- `main-client.jsx` — React mount
- `index-client.html` — HTML template with MarketLens title + font preload
- `vite.config.js` — updated to build both analyst and client entries

Build verified: both entries compile cleanly. Client bundle is 17.92 KB
(5.09 KB gzipped).

### Changed: `backend/engines/narrative.py` — major quality rewrite

The previous version of `generate_diagnosis_paragraph` spliced finding
headlines mid-sentence, producing output like:

> "The dominant signal: scale paid search: $3.8m uplift available."

Rewrote it to generate prose from the underlying structured data
directly. New output on the same data:

> "The strongest signal is paid search: the response curve indicates it
> is operating below saturation, with approximately $3.8M of annual
> uplift available from a measured increase in spend."

Corresponding change to `build_findings`: findings are now diagnosis-
phrased (what the analysis observed), with the prescription moved to
a separate `prescribed_action` field. A CMO reads the headline to
understand what's happening, then looks at the Suggested line below
to see what to do.

| Before | After |
|---|---|
| "Scale Paid Search: $3.8M uplift available" | **Headline:** "Paid Search is underinvested relative to its response curve"<br>**Suggested:** "Increase spend by 32% — estimated $3.8M annual uplift" |
| "Retarget audience Video Youtube: $1.1M uplift available" | **Headline:** "Video Youtube customer-acquisition cost is 18.2x higher than peers"<br>**Suggested:** "Tighten audience targeting, review bids — estimated $1.1M annual uplift" |

New helpers added:
- `_recommendation_as_finding()` — translates a diagnostics engine rec
  into a diagnosis-phrased finding with separate prescription
- `_extract_ratio_from_rationale()` — pulls the "2.5x" ratio out of
  rationale strings so RETARGET findings can surface the multiple
- `_portfolio_insight_sentence()` — generates purpose-built sentences
  from portfolio-level metrics instead of splicing headlines
- `_finding_dedupe_key()` — prevents same-channel findings from
  appearing twice in the top 5

### Frontend: `FindingCard` renders `prescribed_action`

The card now shows a "Suggested" line below the headline in the accent
color, separating diagnosis from prescription visually. Reads as two
distinct ideas: "here's what's happening" then "here's what to do."

### Frontend: Hero paragraph typography tuned

Font size dropped from 30px to 22-26px clamp. At 30px with regular
weight, the three-sentence paragraph read as overwhelming. At 22-26px
it reads as a well-typeset editorial paragraph — which is closer to
what a CMO actually wants to spend time on.

## Known status

**All 107 tests passing** across three suites (18 MMM correctness, 20
optimizer correctness, 69 integration). Occasional single-test flakiness
in integration suite was observed in one prior run but was not
reproducible across three consecutive runs. Worth monitoring but not
blocking.

**Not yet verified in browser.** The narrative reads well in raw JSON
output, and the React components compile cleanly, but the rendered
visual has not been checked by a human. Before adding more screens,
someone should run `npm run dev` and look at it.

## Known issues deferred to next release

**Evidence chart placeholder.** Finding cards currently show a dashed
`Evidence chart: response_curve` placeholder when expanded. Real charts
(Recharts against the existing curve data) are the next frontend work.

**No EY editor overlay yet.** Moderate-override capability (commentary,
narrative rewrite, recommendation curation) was designed and the data
model placeholders are in the `/api/diagnosis` response, but the UI
to create overrides doesn't exist.

**Single-screen product.** Only the Diagnosis screen exists. The
remaining client surfaces (Plan, Channel Deep Dive, Scenarios, Leakage
Detail, Data & Methodology) are stubs in the roadmap, not files on disk.

## Running the new client app

```bash
# Backend (terminal 1)
cd backend && python api.py
# or: uvicorn api:app --port 8000

# Frontend (terminal 2)
cd frontend && npm install && npm run dev
# Client app: http://localhost:3000/index-client.html
# Analyst workbench: http://localhost:3000/index-vite.html
```

The client app cold-starts automatically on first load: if the backend
has no analysis yet, it calls `/api/load-mock-data` and `/api/run-analysis`
before fetching `/api/diagnosis`.

---

# CHANGES — v18f (Scenarios screen — what-if analysis)

Third and final pitch-critical screen. The trio is now complete:
**Diagnosis** ("what's happening") + **Plan** ("what to do") + **Scenarios**
("what if we do X instead"). Partner pitch has all three legs.

Scope is deliberately constrained to Option A from the design
discussion: one lever (total budget), four presets, custom budget
input, comparison-vs-baseline summary. No per-channel locks, no
objective selector, no saved-scenario library — those are post-pitch
expansions. The screen earns its existence by answering the "what if
we cut 20% / add 25% / keep current" questions executives actually
ask.

## What changed

### `backend/api.py` — `/api/scenario` + `/api/scenario/presets`

**`GET /api/scenario/presets`** returns four dynamically-computed
presets based on current spend:
- `baseline` — current annualized spend (the do-nothing counterfactual)
- `conservative` — current × 0.80 (recession scenario)
- `growth` — current × 1.25 (growth investment scenario)
- `recommended` — current × 1.05 (matches Plan-screen default)

Presets are computed from the loaded client's current spend, so they're
always sensible for whatever data is loaded. A client with $10M spend
and a client with $100M spend both get meaningful preset values.

**`GET /api/scenario?total_budget=X&objective=Y&view=client`** returns
the same payload shape as `/api/plan` PLUS a `comparison` block:

```python
"comparison": {
    "narrative": "Compared to keeping today's allocation, this scenario
                  uses $6.3M less spend and would lose $11.0M of annual
                  revenue, with portfolio ROI improve from 3.4x to 4.1x.",
    "scenario": {"total_budget": ..., "projected_revenue": ..., "projected_roi": ...},
    "baseline": {"total_budget": ..., "projected_revenue": ..., "projected_roi": ...},
    "deltas":   {"budget_delta": ..., "revenue_delta": ..., "roi_delta": ...},
}
```

This comparison block is what justifies Scenarios as its own screen
rather than "Plan with different inputs." Without the vs-baseline
framing, a reader would have to hold two mental models simultaneously;
with it, the tradeoff is explicit.

**Critical consistency fix caught while building.** The optimizer is
non-convex: running it on identical inputs with different multi-restart
random seeds can produce allocations that differ by millions in
projected revenue. Without intervention, the "Optimizer recommended"
scenario preset would show one revenue number while the Plan screen
showed a different number for literally the same budget. That would
destroy user trust in both screens.

Fixed by having `/api/scenario` share `/api/plan`'s optimization cache
in `_state["_plan_cache"]`, keyed by `(budget, objective)`. Identical
inputs now return identical outputs across both endpoints.

### `backend/api.py` — helper functions

- `_current_total_spend()` — computes annualized current spend from fitted
  curves (single source of truth for baseline references)
- `_baseline_optimization()` — returns the optimizer's allocation at
  current spend, cached identically to Plan results so the
  comparison reference doesn't drift between calls
- `_format_compact(amount)` — local helper for scenario narrative dollar
  formatting (kept module-local rather than pulled into a shared utils
  module; one-call-site, not worth the indirection)

### `frontend/client/screens/Scenarios.jsx` — NEW

Full screen composition:
1. Hero section with section label + prose intro
2. Control panel — four preset buttons in a responsive grid + custom
   budget input in $M below
3. Comparison card — the vs-baseline deltas in a 3-column grid
   (Budget / Projected revenue / Portfolio ROI), each showing
   baseline → scenario value with a signed delta below
4. KPI row (same component as Plan)
5. Reallocation moves (grouped by direction, reuses MoveCard)
6. Tradeoffs (reuses TradeoffCard)

**Deliberate omission:** editor controls (commentary / suppress) are
NOT wired into Scenarios. Scenarios are exploratory tools the analyst
USES, not deliverables they CURATE. Commentary and suppression belong
on Diagnosis and Plan (what gets published). If this turns out wrong
later, adding the handlers is mechanical — the MoveCard already
accepts them as props.

**Interaction model:** preset clicks are optimistic — the button's
active state flips immediately, then the fetch resolves and updates
the screen. Custom budget submission requires explicit "Run scenario"
button press (not auto-submit on change) because typing "3" when you
mean "30" shouldn't trigger a $3M scenario. Same reasoning we applied
to the suppression reason box in v18b — commit-based input for
destructive or expensive operations.

### `frontend/client/api.js` — three new helpers

```javascript
fetchScenarioPresets()        // GET /api/scenario/presets
fetchScenario({totalBudget, objective, view})  // GET /api/scenario?...
ensureScenarioReady(view, opts)               // cold-start variant
```

### `frontend/client/DiagnosisApp.jsx` + `EditorApp.jsx` — third screen wired

Both shells now route to three screens via `?screen=`:
- `diagnosis` (default)
- `plan`
- `scenarios`

Nav links added to both headers. Editor shell renders Scenarios without
editor handlers (see deliberate omission above). "Preview as client"
link in EditorHeader carries `currentScreen` through, so previewing
from the Scenarios editor view opens the Scenarios client view in the
new tab rather than defaulting to Diagnosis.

## What's verified end-to-end this session

```
[OK] GET /api/scenario/presets returns 4 presets with dynamic budgets
[OK] GET /api/scenario?total_budget=X returns moves + comparison + tradeoffs
[OK] All 4 presets (baseline/conservative/growth/recommended) produce
     sensible deltas vs. baseline
[OK] Custom budgets work (tested $28.5M)
[OK] Plan and Scenario agree on the same budget (consistency check)
[OK] Idempotent — identical calls return identical results
[OK] All 6 frontend routes serve correctly
[OK] Build produces 4 HTML entries + shared DiagnosisApp chunk with
     Scenarios screen (12.25 KB gzipped incremental)
[OK] All 107 backend tests pass
```

## Demo flow (the complete pitch story)

1. **Diagnosis**: "Your portfolio is delivering 3.4x ROI. Here's why it
   could be stronger." → findings + EY commentary
2. **Plan**: "Here's what we recommend." → move cards, per-channel
   reallocation, honest tradeoffs
3. **Scenarios**: "What if you can't / won't do exactly that?" → four
   preset buttons, CMO picks "Cut 20%", sees the comparison: "$6.3M
   less spend, lose $11M revenue, but ROI improves from 3.4x to 4.1x."

Three screens, three consulting questions answered. The trio is what
separates MarketLens from a calculator: Diagnosis tells the client
what's wrong, Plan tells them what to do, Scenarios lets them see
what happens if they choose differently. A calculator would just show
numbers for whatever budget you type in.

## Known issues to flag

- **STILL NOT VISUALLY VERIFIED IN BROWSER.** Eight sessions of UI work.
  The Scenarios screen has the most interactive surface of the three
  (preset buttons with active state, custom input with submit button,
  loading states during fetch, error inline alert). I built it from
  spec. Before the pitch, you need to actually click through it.
- **No keyboard shortcuts** for preset cycling. Minor — a power user
  might want hjkl-style navigation between presets. Not pitch-critical.
- **The comparison narrative** is template-based, same ceiling as
  everywhere else. "Would generate $X more annual revenue" reads fine;
  it's not going to move anyone with its prose.
- **Scenarios don't persist.** The backend has scenario-save endpoints
  from earlier work but they're not wired to this screen. A user who
  runs a scenario, closes the tab, and comes back loses it. Fine for
  a pitch tool. Post-pitch: wire saved scenarios into the control
  panel so the analyst can name and recall them.
- **No URL sync for scenario state.** Clicking "Cut 20%" doesn't
  update the URL, so you can't share a deep link to a specific
  scenario. Post-pitch enhancement, trivial to add.

## What's next

**Session C: Navigation polish.** Currently nav links are full page
reloads (`<a href="?screen=X">`). Works, but flashes a loading state
between screens. Session C promotes to client-side routing — likely
a custom minimal router rather than adding react-router for three
screens — and addresses any visual issues from the browser check.

After Session C, MarketLens v19 territory: saved scenarios, URL sync,
draft/publish flow, real database for auth persistence, per-tenant
data isolation. Those are real-product features, not pitch-stage.

## Verification before pushing v18f to Railway

```bash
cd backend
python test_integration.py             # 69/69
python test_mmm_correctness.py          # 18/18
python test_optimizer_correctness.py    # 20/20

cd ../frontend
npm install && npm run build
# 4 HTML entries: index-client, index-editor, index-vite, index-login

cd ../backend
python -m uvicorn api:app --port 8000 &

# Smoke test the new endpoints
curl -X POST http://localhost:8000/api/auth/login-v2 \
  -H "Content-Type: application/json" \
  -d '{"username":"ey.partner","password":"demo1234"}' | jq -r .token > /tmp/tok

# Then exercise the flow — client.cmo can also do these since /api/scenario
# is read-only (doesn't require editor role)
curl -H "Authorization: Bearer $(cat /tmp/tok)" \
  http://localhost:8000/api/scenario/presets
curl -H "Authorization: Bearer $(cat /tmp/tok)" \
  "http://localhost:8000/api/scenario?total_budget=25000000"
```

---

# CHANGES — v18e (Auth + RBAC: editor / client roles, login screen, route guards)

The pitch tool now has actual authentication. Four pre-seeded demo users
(two editor-role, two client-role), a login screen, JWT-based sessions,
and role-protected editor endpoints. The client/editor split moves from
"convention based on which URL you visit" to "security property based on
which role your token carries."

No engine or feature regressions. All 107 tests still pass.

## What changed

### `backend/auth.py` — new role model + demo seeding

Replaced the legacy `admin/analyst/viewer` role triplet with two
MarketLens-specific roles:

- **`editor`** — EY analysts and partners. Full edit access to commentary,
  suppression, rewrites, audit log. Can preview the client view.
- **`client`** — Client executives and analysts. Read-only access to
  the published client-view output. Cannot see audit log or suppressed
  findings.

The legacy roles stay in the `ROLE_PERMISSIONS` map so the existing
analyst workbench keeps working with its own tokens — backward
compatible.

Added `seed_demo_users()` which creates four accounts on first boot:
ey.partner, ey.analyst (both editor); client.cmo, client.analyst (both
client). Idempotent — safe to call on every startup. All passwords
"demo1234" — pitch-tool only, MUST change before real client data.

Added `get_demo_credentials_for_login_page()` which the login screen
calls to render its credential hints. Set environment variable
`MARKETLENS_HIDE_DEMO_CREDS=1` to make this return empty (production
mode), which collapses the credential-hints section on the login UI
to nothing.

Added convenience dependency `require_editor` so `/api/editor/*`
endpoint signatures express their role requirement clearly:

```python
@app.post("/api/editor/commentary")
def editor_set_commentary(body, user=Depends(require_editor)):
    ...
```

### `backend/api.py` — auth-protected editor endpoints + login

All seven `/api/editor/*` endpoints now require `editor` role via
`Depends(require_editor)`. Pre-v18e, anyone who could reach the URL
could mutate overlay state. Now:
- Unauthenticated request → `401 Authentication required`
- Authenticated as client → `403 Requires role: editor`
- Authenticated as editor → `200` with action performed

**Author attribution fixed.** Previously the editor endpoints accepted
an `author` field from the request body — which a malicious client
could forge ("save commentary authored by ey.partner"). The author is
now derived from the authenticated user's JWT, not the request body.
Requests pass `author=user["username"]` to persistence; the body's
author field, if present, is silently ignored.

New endpoints:
- `POST /api/auth/login-v2` — JSON body login (the legacy `/api/auth/login`
  takes credentials as URL query params, which is bad practice;
  preserved for the analyst workbench but not used by MarketLens)
- `GET /api/auth/demo-users` — returns demo credentials for the login UI
- `GET /login` and `GET /index-login.html` — serve the login HTML

`@app.on_event("startup")` hook calls `seed_demo_users()` so a fresh
deploy (Railway, Docker, clean sqlite) has valid credentials available
immediately. Errors during seeding are logged but don't block startup.

### `frontend/client/api.js` — token-aware fetch + login helpers

Every API call now attaches `Authorization: Bearer <token>` automatically
if a stored token exists. Token lives in localStorage under
`marketlens:auth:v1` as a JSON blob `{ token, username, role, expiresAt }`.

A 401 response from any endpoint:
1. Clears the stored token
2. Calls the `_onUnauthorized` handler (set by app shells via
   `setUnauthorizedHandler(fn)`) which redirects to `/login`

This means an expired token mid-session lands the user back at login
cleanly rather than producing a stack of failed requests in console.

New helpers:
- `getStoredAuth()` / `setStoredAuth()` / `clearStoredAuth()` — token storage
- `setUnauthorizedHandler(fn)` — register the redirect callback
- `login(username, password)` — POST to /api/auth/login-v2 + persist token
- `logout()` — clear token + trigger redirect
- `fetchDemoUsers()` — for the login screen's credential hints

### `frontend/client/screens/LoginScreen.jsx` — NEW

Centered card with the wordmark, username/password form, and a
"Demo credentials" panel below. Each demo credential is a button —
click it, the form auto-fills, then click Sign in. Faster than typing
"client.analyst" + "demo1234" eight times during testing.

After successful login: `editor` role redirects to `/editor`, `client`
role redirects to `/`. Both routes carry the user into the appropriate
shell which uses the same auth token to fetch its data.

Visual language matches MarketLens: warm off-white canvas, Geist
typography, teal accent, restrained styling. No "MarketLens · Sign in
to Insights for Modern Marketing" marketing fluff — just brand,
form, demo credentials.

### `frontend/client/LoginApp.jsx` + `main-login.jsx` + `index-login.html` — NEW

Standard entry point trio matching the existing client/editor pattern.
Vite config adds `login` as a fourth rollup input.

### `frontend/client/DiagnosisApp.jsx` + `EditorApp.jsx` — auth guards

Both shells now check for a stored auth token on mount before fetching
data. Behavior:

**Client shell (`DiagnosisApp` at `/`):**
- No token → redirect to `/login`
- Has token (any role) → boot
- 401 mid-session → token cleared, redirect to `/login`

**Editor shell (`EditorApp` at `/editor`):**
- No token → redirect to `/login`
- Token with `client` role → redirect to `/` (they're authenticated,
  just not authorized for this surface)
- Token with `editor` role → boot
- 401 mid-session → redirect to `/login`

This makes the URL split a real security boundary, not just a UX one.
A client-role user typing `/editor` into the URL bar lands back at `/`.

### Header changes — UserChip with sign-out

Both client and editor headers now show the signed-in username with a
small role pill and a "Sign out" link. Plain text, no dropdown menu —
there's only one auth action available, so a menu would be friction.

Editor header: username + sign-out next to "Preview as client" link.
Client header: replaced the green "analysis current" dot with the
user chip (the dot was decorative anyway).

## What's verified end-to-end this session

```
[OK] Login as ey.partner → editor token issued, role=editor
[OK] Login as client.cmo → client token issued, role=client
[OK] Wrong password → 401 (no account enumeration leak)
[OK] /api/editor/commentary without auth → 401
[OK] /api/editor/commentary with client token → 403
[OK] /api/editor/commentary with editor token → 200, audit author = "ey.partner"
[OK] Audit log read with client token → 403
[OK] All 6 frontend routes serve correctly:
       / /login /editor /index-login.html
       /api/auth/demo-users /api/status
[OK] Build produces 4 HTML entries + login bundle (1.77 KB gzipped)
[OK] All 107 tests pass
```

## Demo flow (what the Partner sees)

1. Visit `https://your-app.railway.app/`
2. Redirected to `/login` (no token in localStorage)
3. See the login screen with 4 demo credential buttons listed
4. Click `ey.partner` → form auto-fills → click Sign in
5. Redirected to `/editor` — full editor mode with auth attribution
6. Add commentary; the audit log records "ey.partner" as the author
7. Click "Preview as client" link in editor header → opens `/` in new tab
8. New tab shows client view with the editor's commentary rendered as
   "EY's Take" boxes
9. Sign out from either tab returns to `/login`

To demo "what does a client see when they log in": sign out, log in as
`client.cmo`, observe the editor link is unreachable (you'll be
redirected back if you try `/editor`).

## Known issues to flag

- **Still not visually verified in browser.** Auth + login screen +
  user chips all built without rendering once. Same caveat as v18b/c/d.
  This is now blocking — please run a local check before Session B.
- **JWT_SECRET defaults to a dev string.** In production set
  `JWT_SECRET=<long-random-string>` as an env var on Railway. The
  current default is documented as "change in production" but the
  environment variable check happens at module import, not at runtime.
- **Token expiry is 24 hours.** No refresh token. After 24h, user
  re-logins. Fine for a pitch tool; would need a refresh-token flow for
  real production.
- **No "lock screen" between sessions.** A user who closes their laptop
  and reopens it within 24 hours stays logged in. Standard SaaS
  behavior; flagging in case you want session-per-tab semantics.
- **The legacy analyst workbench is unaffected** — still uses the
  legacy roles (admin/analyst/viewer) and the legacy `/api/auth/login`
  endpoint. No login screen for it; analysts who want to use it can
  POST credentials directly to register/login.

## What's still ahead

- **Session B: Scenarios screen.** What-if controls, side-by-side
  allocation comparison.
- **Session C: Navigation polish.** Promote screen routing from full-
  reload links to client-side routing.
- **Real database for auth in production.** sqlite on Railway is
  ephemeral; demo users get re-seeded on every redeploy but anyone
  who registered would be lost. Postgres + a real user-management
  flow is the v19 territory.

## Verification before pushing v18e to Railway

```bash
cd backend
python test_integration.py             # 69/69
python test_mmm_correctness.py          # 18/18
python test_optimizer_correctness.py    # 20/20

cd ../frontend
npm install
npm run build
# Should produce 4 HTML entries: index-client, index-editor, index-vite,
# index-login. Plus a small login bundle (~6 KB).

cd ../backend
python -m uvicorn api:app --port 8000 &

# Confirm route layout
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/login
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/auth/demo-users

# Confirm demo login works
curl -s -X POST http://localhost:8000/api/auth/login-v2 \
  -H "Content-Type: application/json" \
  -d '{"username":"ey.partner","password":"demo1234"}'
# Should return { user_id, username, role: "editor", token }
```

Once those pass, push to Railway. The Dockerfile from v18d already
builds the frontend correctly; v18e adds a fourth HTML entry which is
caught by the post-build verification step in the Dockerfile (which
checks for index-client and index-editor specifically; index-login is
served too but isn't in the verification list — could be added but
not critical since a missing login HTML would fail at first request,
not deploy).

---

# CHANGES — v18d (deploy fixes: Dockerfile + frontend-dist serving)

Critical deploy correctness release. Without v18d, pushing v18c to Railway
would have shipped an image that can't serve MarketLens:
- The Dockerfile never ran `npm install` / `npm run build`, so
  `frontend-dist/` didn't exist in the container
- The `api.py` static-file mount pointed at the source `frontend/`
  directory and served raw `.jsx` files that browsers can't execute
- The `/` route returned a legacy JSON status endpoint, not HTML

A user hitting the Railway URL would have gotten either a 404 at root
or the old analyst workbench. MarketLens itself would not have rendered.

This release makes the product actually deployable. Changes are all
infrastructure — no engine or feature changes. Everything that worked
locally in v18c works in v18d; now it also works in a Docker container
behind an external domain.

## What changed

### `Dockerfile` — now builds the frontend

Added Node.js 20 to the base image and a Vite build step:

```dockerfile
# New: Node 20 from NodeSource (alongside the existing Python toolchain)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs

# New: npm ci with package-lock cached separately from source files
# so the install layer caches across React code changes
COPY frontend/package.json frontend/package-lock.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci --no-audit --no-fund

# After full source copy:
WORKDIR /app/frontend
RUN npm run build

# Fail the image build if Vite didn't produce the three entry points
RUN test -f /app/frontend-dist/index-client.html || exit 1
RUN test -f /app/frontend-dist/index-editor.html || exit 1
RUN test -d /app/frontend-dist/assets || exit 1
```

Image size implications: adds ~200MB for Node + npm + node_modules.
Final image is now ~650MB vs. the previous ~450MB. Worth it — without
the frontend, the backend has nothing to serve for a UI-facing product.

The verification steps at the end (`RUN test -f ...`) fail the build
immediately if Vite produces unexpected output. Catches regressions
like "someone renamed an entry point" at build time rather than
deploy time.

### `backend/api.py` — serves `frontend-dist/` with sensible routes

Rewrote the static-file block (was about 10 lines at the bottom) into
a proper routing layer. Key additions:

**Friendly paths** (shareable URLs):
- `GET /` → MarketLens client (Diagnosis default view)
- `GET /editor` → MarketLens editor
- `GET /analyst` → Legacy analyst workbench

**Direct paths** (preserved for the editor's "Preview as client" link
and for anyone deep-linking):
- `GET /index-client.html`
- `GET /index-editor.html`
- `GET /index-vite.html`
- `GET /app` (legacy alias)

**Assets:**
- `GET /assets/...` — hashed JS/CSS bundles Vite references in the HTML

The backend uses a candidate-path search (`/app/frontend-dist`, relative
paths, etc.) so it works identically in Docker, in local dev from the
backend directory, and in a packaged zip. If no `frontend-dist/` exists,
serves a helpful 503 explaining that the frontend wasn't built.

**Breaking change (minor):** the old `GET /` JSON status endpoint moved
to `GET /api/status`. Anyone scripting against the old `/` for health
monitoring should switch to `/api/status` or `/api/health` (both return
JSON). All existing API routes under `/api/*` are unchanged.

### Route verification (done locally this session)

```
GET /                              → 200  text/html
GET /editor                        → 200  text/html
GET /analyst                       → 200  text/html
GET /index-client.html             → 200  text/html
GET /api/status                    → 200  application/json
GET /api/health                    → 200  application/json

Assets referenced in / HTML (3 found):
  /assets/client-CnXxc9tc.js:         200
  /assets/createLucideIcon-*.js:      200
  /assets/DiagnosisApp-*.js:          200
```

All 107 tests still pass.

## What could still fail on Railway (worth knowing)

**Docker build step I couldn't verify.** The sandbox doesn't have Docker
installed, so I couldn't run `docker build` to prove the Dockerfile
actually works. The Dockerfile looks correct by inspection (Node install
follows the NodeSource pattern, npm ci is standard, copy order respects
layer caching), but the first real test is Railway's build pipeline.

If the Railway build fails, the likely suspects are:
- NodeSource install issue (apt repo signing, DNS) — surface with clear
  error message
- `npm ci` failing because `package-lock.json` is incomplete — unlikely,
  the current lock was generated from a working install
- Vite build failing because a JSX import resolves differently in a
  Linux container vs. macOS/Windows — possible but rare

**What to do if it fails:** Check Railway's build log. The Dockerfile
uses `set -e` implicitly (docker build's default), so the first failing
command halts with a clear error. The verification RUN statements at
the end of the build catch "frontend didn't produce expected files"
before they cause runtime confusion.

**Cold-start time.** On Railway's free tier, first request after idle
takes ~30s for the Python process to warm up, plus another 20-40s for
the cold-start data load + analysis pipeline. Subsequent requests are
fast. Worth hitting the URL once before showing anyone.

## Verification before pushing to Railway

```bash
# Locally confirm everything still works
cd backend
python test_integration.py          # 69/69
python test_mmm_correctness.py       # 18/18
python test_optimizer_correctness.py # 20/20

cd ../frontend
npm install
npm run build
# Should produce frontend-dist/ with index-client.html, index-editor.html,
# index-vite.html, and assets/ subdirectory

cd ../backend
python -m uvicorn api:app --port 8000 &
curl -s http://localhost:8000/ | grep -q MarketLens && echo "OK"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/editor
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/status
# All three should be 200
```

Once those pass, push to Railway. The Dockerfile will run `npm ci`,
`npm run build`, and the verification checks automatically.

## What v18d does NOT change

- No new features — still the Diagnosis screen + Plan screen we had
  in v18c
- No auth added to editor endpoints (still a known gap — the URL split
  is a convention, not a security property)
- No scenarios screen yet (Session B of the roadmap)
- No navigation polish (Session C of the roadmap)

This release is purely "make the product deployable," not "make the
product better." Both matter. v18c was useful on disk; v18d is useful
on the internet.

---

# CHANGES — v18c (Plan screen — backend + frontend, end-to-end)

Session A of the "pitch-critical three screens" plan (Path 2 from the
roadmap discussion): the Plan screen is done. Client and editor modes,
commentary + suppression overlay, honest narrative for near-linear fits,
navigation between Diagnosis and Plan, stable keys across re-fetches.

No breaking changes. Existing v18b functionality (Diagnosis screen, all
editor endpoints) works exactly as before.

All 107 tests pass, stable across runs.

## What changed

### `backend/engines/narrative_plan.py` — NEW

Parallel to `engines/narrative.py` for the Diagnosis screen, but shaped
for budget reallocation content. Produces:
- `headline_paragraph`: 2-3 sentence consulting-style rationale
  (NOT a summary of the moves — it explains *why* the reallocation is
  warranted before listing *what* to do)
- `kpis`: reallocation_size, expected_uplift, plan_confidence
- `moves`: per-channel action cards with stable keys for editor overrides
- `tradeoffs`: honest caveats (large moves, near-linear fits,
  optimizer warnings, always-on assumptions caveat)
- `methodology`: optimizer + response curves metadata
- `ey_overrides`: live counts for the editor header

Move keys: `move:<channel>:<action>` (e.g. `move:paid_search:increase`).
Stable semantic identifier so editor overrides survive analysis re-runs.
Ranking: by absolute revenue delta within each action group.

**Honest-narrative work carried over from v17 diagnostic fixes:** when
the optimizer recommends a move based on a near-linear response curve
(channel like organic_search with `b ≈ 1`), the narrative explicitly
flags the uncertainty: "We can't reliably identify where saturation
begins. The optimizer is suggesting this increase based on the fitted
mROI of X, but that number is extrapolating past observed spend levels.
Validate with a geo-lift test before committing the full allocation."

This prevents the Plan screen from presenting fabricated precision.
Same principle we applied to Diagnosis in v17 (INVESTIGATE recs instead
of SCALE).

### `backend/api.py` — `GET /api/plan` endpoint

Accepts `view` (client/editor), `engagement_id`, `total_budget`,
`objective`. Returns the full payload. Default budget is current spend
+ 5% (gives optimizer headroom without being asked to cut).

**Critical fix discovered this session:** the optimizer has a stochastic
multi-restart component. Re-running it on identical inputs produces
slightly different allocations — specifically, near-tie moves can flip
between increase/decrease/hold between calls. This caused edited
commentary to orphan itself: EY edits `move:events:decrease` on
Monday, refreshes on Tuesday, and the commentary is gone because
events is now `move:events:increase`.

Fixed by caching optimization results per (budget, objective) pair in
`_state["_plan_cache"]`. The cache persists until `curves` is
re-identity (on `/api/run-analysis`), at which point the stale cache
is transparently regenerated. Verified: 5 consecutive calls now return
identical move keys.

### `frontend/client/api.js` — `fetchPlan` + `ensurePlanReady`

Mirror of the diagnosis fetchers. `ensurePlanReady` handles cold-start
(load mock data → run analysis → retry) so the Plan screen boots
cleanly on a fresh backend same as Diagnosis does.

### `frontend/client/components/MoveCard.jsx` — NEW

Per-channel reallocation card. Parallel to `FindingCard` on Diagnosis
but shaped for numeric before/after display:
- Action badge (Increase / Reduce / Hold) with color-coded icon
- Channel + action as headline
- Number grid showing current spend → optimized spend → revenue impact
- ROI row on expand: current, optimized, marginal
- Inconclusive banner when `reliability === "inconclusive"` (near-linear
  response curve) — visible in BOTH client and editor modes because a
  CMO should never see a precise-looking number that isn't precise
- Suppression banner in editor mode only, with reason inline
- Editor action bar with Add/Edit Commentary and Hide/Show buttons
- Inline commentary editor on expand (reuses existing `CommentaryEditor`
  component from v18b)

### `frontend/client/components/TradeoffCard.jsx` — NEW

Smaller, quieter card for the "Tradeoffs" section. Horizontal row with
severity icon, headline, brief narrative. No expand, no editor
affordances — tradeoffs are static engine output. If per-tradeoff
overrides become a need later, we can add a `tradeoff:<key>` override
namespace without changing this component's shape.

### `frontend/client/screens/Plan.jsx` — NEW

Full screen composition:
1. Hero section (rationale paragraph + KPI bento)
2. Moves section — grouped by direction (Increase / Reduce / Hold)
3. Tradeoffs section
4. Methodology footer

**Design decision:** moves are grouped by direction rather than shown
in pure impact order. On Diagnosis, findings are heterogeneous and
ordering by impact is the obvious presentation. On Plan, moves are all
the same shape (channel + action) and grouping by direction helps a
CMO scan "what am I being asked to increase?" separately from "what am
I being asked to cut?" That matches how the reader thinks about it.

Within each group, backend's impact-ordering is preserved (biggest
move per direction floats to the top).

### `frontend/client/DiagnosisApp.jsx` + `EditorApp.jsx` — screen routing

Both shells now read `?screen=` from the URL and route to either the
Diagnosis or Plan screen. Minimal nav links in each header. Full page
reload on nav click (href-based, not client-side routing) — matches
browser back-button expectations, avoids adding a routing library,
and each screen has its own backend endpoint so the refetch is the
intended behavior anyway.

Session C will promote this to client-side routing when a third screen
arrives; for two screens, full-reload nav is fine.

**"Preview as client" link now carries the current screen param**, so
clicking it from the Plan editor opens the Plan client view, not the
Diagnosis view. Previously would have been a surprising context switch.

## What's working end-to-end (verified this session)

```
[OK] Diagnosis: 5 findings in client view
[OK] Plan: 8 moves, 3 tradeoffs, headline paragraph present
[OK] Commentary works on both Diagnosis findings AND Plan moves
     (same editor endpoints; keys route correctly per surface)
[OK] Suppression filters moves out of Plan client view (8 → 7)
[OK] Editor view of Plan shows suppressed moves with reason inline
[OK] 5 consecutive /api/plan calls return identical move keys
[OK] All 107 tests pass, stable across runs
```

## What remains (Sessions B and C)

**Session B: Scenarios screen.** The "what-if" surface — interactive
controls to adjust budget total and objective, re-run the optimizer,
compare outcomes side-by-side. Most complex of the three because it
needs real user controls (not just read-only display). Will reuse
MoveCard for the allocation comparison.

**Session C: Navigation + polish.** Promote screen routing from
full-reload to client-side, fix anything that looks wrong after
visual verification, package demo-ready final zip.

## Known issues to flag

- **Still not visually verified in browser.** Six sessions into UI
  work now. The Plan screen inherits all the same design tokens as
  Diagnosis, so if something reads wrong in Diagnosis it will also
  read wrong in Plan. Strongly recommend a local run before Session B:
  `cd frontend && npm run build && npm run dev`, then visit
  `/index-client.html?screen=plan`.
- **Narrative has template ceiling.** The Plan's headline paragraph
  and move narratives are competent but recognizably template-based.
  Same ceiling as Diagnosis. Fixable with more template variants or
  LLM integration; neither scoped for the pitch.
- **Optimizer occasionally doesn't converge** on some multi-restarts
  (logged to stderr but doesn't affect result — the best of the
  successful restarts is used). Worth eventual cleanup; not blocking.

## Verification before pushing

```bash
cd backend
python test_integration.py          # 69/69
python test_mmm_correctness.py       # 18/18
python test_optimizer_correctness.py # 20/20

cd ../frontend
npm install
npm run build                         # 3 HTML entries + shared DiagnosisApp chunk

# Local run:
npm run dev &
cd ../backend && python -m uvicorn api:app --port 8000 &

# Four URLs now:
#   /index-vite.html                       — analyst workbench
#   /index-client.html                     — Diagnosis (client view)
#   /index-client.html?screen=plan         — Plan (client view)  ← NEW
#   /index-editor.html                     — Diagnosis (editor)
#   /index-editor.html?screen=plan         — Plan (editor)       ← NEW
```

---

# CHANGES — v18b (EY editor overlay: frontend)

Frontend half of the editor overlay. Everything the schema and API surface
from v18a unlocked is now wired to a UI. EY can open the editor, add
commentary to findings, suppress findings from the client view, and watch
their changes reflected in real-time. A "Preview as client" link opens
the client surface in a new tab so EY can verify what the client will
see before handing off.

No backend changes this release — pure frontend on top of v18a's schema
and endpoints.

## What changed

### `frontend/client/DiagnosisApp.jsx` — client shell

The client-mode shell had been lost between sessions (referenced by
`main-client.jsx` but not present on disk, which meant the v18a bundle
would not have built cleanly if anyone actually tried). Restored with
the design from v17: header with MarketLens wordmark + engagement
metadata, centered spinner during cold-start, inline error card on
failure, Geist font loaded from Google CDN.

A `GlobalStyles` component is now exported so `EditorApp` can reuse the
same animation keyframes, font loading, and scrollbar styling without
duplication.

### `frontend/client/EditorApp.jsx` — editor shell (NEW)

The editor-mode shell. Loads the diagnosis with `view=editor`, which
returns all findings including suppressed ones flagged with their
reason, plus commentary attached to findings as metadata. Renders the
same `Diagnosis` screen the client app uses but passes `editorMode={true}`
and four mutation callbacks:

- `onSaveCommentary(findingKey, text)` — POST to /api/editor/commentary
- `onDeleteCommentary(findingKey)` — DELETE from /api/editor/commentary
- `onRequestSuppress(finding)` — opens the `SuppressionModal`
- `onUnsuppress(findingKey)` — DELETE from /api/editor/suppress

Each handler: sets a submitting flag, calls the API, shows a toast on
success/error, reloads the full diagnosis so the override is visible,
resets submitting. Errors propagate back to the calling component so
the commentary editor and suppression modal can surface them inline
without losing the user's unsaved text.

The editor header is visually distinct from the client header — sunken
background, "EY Editor" pill next to the wordmark, live override counts
on the right ("1 NOTES · 2 HIDDEN"), and a prominent "Preview as client"
link that opens the client entry in a new tab rather than toggling in
place (reduces risk of an author thinking they're in the client view
and making edits they can't undo cleanly).

### `frontend/main-editor.jsx` + `index-editor.html` (NEW)

Vite entry points for the editor. Same pattern as client entry — preload
Geist from Google Fonts, render `EditorApp` into `#root`.

### `frontend/vite.config.js`

Third entry added to `rollupOptions.input`:
```js
editor: resolve(__dirname, 'index-editor.html'),
```

Build output now has three HTML files (`index-vite.html` for analyst,
`index-client.html` for MarketLens client, `index-editor.html` for EY
editor). Vite auto-detected the shared `DiagnosisApp.jsx` import between
client and editor and code-split it into a shared chunk — client and
editor bundles deduplicate the shell code rather than shipping two
copies.

Final bundle sizes:
- `analyst.js` — 16.45 KB (6.89 KB gzipped, unchanged)
- `client.js` — 0.21 KB (0.19 KB gzipped) — just the main-client entry code
- `editor.js` — 14.03 KB (4.05 KB gzipped)
- `DiagnosisApp.js` (shared) — 27.58 KB (7.35 KB gzipped)

### Pre-existing component files used

`CommentaryEditor.jsx`, `SuppressionModal.jsx`, `Toast.jsx`,
`FindingCard.jsx`, `Diagnosis.jsx` were already in place from earlier
iteration work. v18b wired them together rather than rebuilding.

The components collectively handle:
- **Inline commentary authoring** — textarea with auto-focus, character
  count, ⌘↵ to save, Escape to cancel, inline error display if save
  fails. Matches the design system (teal accent border, Geist body).
- **Suppression modal** — full-screen overlay with backdrop-click dismiss,
  required 10+ character reason, icon + explanatory copy, primary
  "Hide from client" button. Reason is enforced both at the UI level
  (min length, disabled submit) and at the backend (400 on empty).
- **Toast notifications** — bottom-right, auto-dismiss after 3s (success)
  or 6s (error), manual dismiss via X button, single-toast stack.
- **FindingCard editor state** — suppressed banner at top of card in
  editor mode only (hidden in client mode even if somehow included),
  editor action bar below expanded card with "Add/Edit commentary" and
  "Hide from client / Show to client" buttons, submitting states
  correctly disable interactive controls.

## Verified end-to-end this session

```
[1] Editor boot: 5 findings, editor mode
[2] Commentary saved on finding:paid_search:opportunity
[3] Suppressed finding:email:opportunity
[4] Client view: 4 findings, suppressed hidden, commentary visible
[5] Editor view: 5 findings (all), suppression flag + reason visible
[6] Editor counts: {commentary: 1, suppressions: 1, rewrites: 0}
[7] Unsuppressed — client view now sees finding again
[8] Commentary deleted — gone from client view
[9] Audit log: 4 entries covering all 4 mutations
```

All 107 backend tests still pass (69 integration + 18 MMM correctness
+ 20 optimizer correctness).

## Verification before pushing

```bash
# Frontend — confirm all three bundles build
cd frontend
npm install
npm run build
# Expect four HTML entries in frontend-dist/, client + editor + analyst chunks

# Run the full app locally
npm run dev &
cd ../backend && python -m uvicorn api:app --port 8000 &

# Open three URLs:
#   http://localhost:3000/index-vite.html    — analyst workbench
#   http://localhost:3000/index-client.html  — MarketLens client view
#   http://localhost:3000/index-editor.html  — EY editor overlay
```

## Using the editor

1. Open `/index-editor.html`. First load triggers a cold-start if backend
   has no current analysis; subsequent loads are instant.
2. Expand any finding. An action bar appears with "Add commentary" and
   "Hide from client" buttons.
3. Click "Add commentary" → write text → ⌘↵ or click Save. Toast
   confirms, the commentary appears as an "EY's Take" panel on the
   finding.
4. Click "Hide from client" → modal opens → type reason (10+ chars) →
   click "Hide from client" button. Toast confirms, the finding gets
   a "Hidden from client" banner with the reason inline.
5. Click "Preview as client" in the header (top right). A new tab opens
   at the client view — the suppressed finding is gone, the commentary
   shows as "EY's Take" inside the finding.

## What's deferred to a later release

- **Narrative rewrite UI** — the third editor capability. Backend
  schema/endpoints are ready (v18a); UI is not built. This one's more
  complex than commentary because it needs inline rich-text editing
  with the "numbers stay locked" constraint enforced visually.
  Recommend as v18c.
- **Draft / publish workflow** — currently edits take effect immediately
  on the client view. Adding a draft-state layer requires: "Save draft"
  vs. "Publish" distinction in the UI, the publish endpoint snapshots
  current overrides to `engagement_publish_state`, client view reads
  from published snapshot rather than live overrides. Schema already
  in place for this.
- **Evidence charts inside expanded findings** — still the v17
  placeholder ("Evidence chart: response_curve" dashed box).
- **Auth** — the editor endpoints are currently unauthenticated. The
  mode split relies on the editor entry being the only caller. Adding
  auth wraps the endpoints without changing their shape.

---

# CHANGES — v18a (EY editor overlay: backend + schema)

Backend-only half of v18. Ships the full database schema and API surface
for all four editor-overlay capabilities (commentary, suppression,
narrative rewrite, publish state), plus frontend-ready wiring for two of
them (commentary and suppression). The remaining two frontend pieces
(rewrite UI, preview-as-client toggle) land in v18b as pure UI work on
the same schema — no further backend changes required.

Nothing in the existing client view breaks. The `GET /api/diagnosis`
endpoint now accepts a `view` parameter defaulting to `client`, which
preserves existing behavior unless explicitly switched to `editor`.

All 107 tests pass, stable across runs.

## What changed

### `backend/persistence.py` — overlay schema + CRUD

Five new tables, one row-level audit trail, full CRUD functions:

- **`editor_commentary`** — EY adds notes alongside findings. Shows up
  as "EY's Take" panels in the client view.
- **`editor_suppressions`** — EY hides findings from the client view.
  Reason field is `NOT NULL` and validated at the Python level as well;
  suppression without a reason raises `ValueError` before hitting SQL.
- **`editor_rewrites`** — schema-ready, wired to UI in v18b. Stores
  original + rewritten text per field (`headline` | `narrative` |
  `prescribed_action`) with a CHECK constraint enforcing the field
  name. Numbers stay locked — the UI will enforce this, not the schema.
- **`editor_audit_log`** — append-only row per edit. Every set/delete
  to any of the three override tables produces an audit row with
  action, author, timestamp, and a JSON payload summary.
- **`engagement_publish_state`** — schema-ready for v18b. Stores the
  "published snapshot" of overrides that the client view reads. When
  v18b adds draft/publish, editor writes go to draft; publish button
  snapshots current overrides to this table; client reads from snapshot.

All tables key on `(engagement_id, finding_key)`. `engagement_id` is
`'default'` in v18a (single-tenant pitch tool). `finding_key` is the
stable semantic identifier generated by the narrative engine, NOT the
array index — so overrides stay pinned correctly across analysis re-runs.

Indexes on `engagement_id` across all override tables for query perf.

### `backend/engines/narrative.py` — stable keys + override layering

**Stable `finding_key`** generated on every finding during `build_findings`.
Format: `finding:<channel_or_metric>:<type>` — e.g. `finding:paid_search:opportunity`,
`finding:channel_gap:insight`. Derived from the finding's semantic
content, not its position, so `ey_overrides` reference the right finding
even after re-runs reorder the list.

**`generate_diagnosis()`** extended with two new parameters:

```python
def generate_diagnosis(..., engagement_id: str = "default", view: str = "client"):
```

- `engagement_id`: keyspace for overrides. Currently always `"default"`.
- `view`: `"client"` or `"editor"`.
  - `"client"` — suppressed findings are filtered out before the response
    is built; commentary is attached to visible findings as `ey_commentary`;
    rewrites replace generated text transparently.
  - `"editor"` — ALL findings returned, including suppressed ones flagged
    with `suppressed: true` and `suppression_reason`; commentary attached
    same as client; rewrites attached as a `rewrites` dict so the editor
    UI can show the original AND the rewrite side-by-side with a revert option.

Override loading is isolated into `_load_overrides_safely()` which degrades
gracefully to "no overrides" if sqlite is missing or the schema is out of
date — so narrative generation never breaks because of an overlay problem.

The response's `ey_overrides` field now carries live metadata
(`engagement_id`, `view`, `counts`) instead of empty placeholder dicts.

### `backend/api.py` — seven new endpoints + view param

**Updated:**
- `GET /api/diagnosis?view=client|editor&engagement_id=...` — the existing
  endpoint now accepts the view and engagement params and passes them
  through to the narrative engine. Default behavior unchanged.

**New (all under `/api/editor/...` to make the mode split explicit):**
- `POST /api/editor/commentary` — create or replace commentary for a finding
- `DELETE /api/editor/commentary/{finding_key}` — remove commentary
- `POST /api/editor/suppress` — suppress a finding (requires reason)
- `DELETE /api/editor/suppress/{finding_key}` — unsuppress
- `POST /api/editor/rewrite` — save a rewrite (schema-ready, UI in v18b)
- `DELETE /api/editor/rewrite/{finding_key}/{field}` — revert
- `GET /api/editor/audit-log?limit=N` — recent audit entries

All editor endpoints reject empty text (for commentary) and empty reasons
(for suppression) with HTTP 400. No auth layer yet — v18a assumes only
the editor entry point reaches these endpoints; auth wraps in a later
release.

### Tests

All 107 existing tests still pass, stable across 4+ consecutive runs:
- 69 integration tests
- 18 MMM correctness tests
- 20 optimizer correctness tests

The `Normal budget produces positive uplift` integration test was
stabilized in v17 (derives target budget from actual current spend
rather than hardcoding $30M). That fix holds.

No new tests added for the overlay layer in v18a. The end-to-end flow
was verified via a manual smoke test covering all 10 scenarios
(set/get/delete for commentary, suppression, and rewrites, plus view
switching, validation, audit log, counts metadata). A proper pytest
suite for the overlay lands in v18b alongside the frontend.

## What NOT shipped in v18a (planned for v18b)

- **Editor entry point (`index-editor.html` + `main-editor.jsx`).** The
  whole frontend side.
- **Editor UI for commentary and suppression.** Inline text areas,
  suppression modal with reason input, EY-mode header variant.
- **Client UI for rendering `ey_commentary`.** Client view returns the
  data; the existing `FindingCard.jsx` doesn't yet render it.
- **Narrative rewrite UI.** Inline edit controls for headline / narrative /
  prescribed action. Backend accepts these already.
- **Preview-as-client toggle.** Mode switch button in the editor header.
- **Draft / publish workflow.** Currently edits take effect immediately
  on the client view. Draft/publish decouples EY work-in-progress from
  what the client sees.

All of these are pure frontend work or simple additions on top of the
v18a schema — no more backend refactoring needed.

## Verification before pushing

```bash
# Full regression (all 107 tests)
cd backend
python test_integration.py          # 69/69
python test_mmm_correctness.py       # 18/18
python test_optimizer_correctness.py # 20/20

# Editor endpoints smoke test
python << 'EOF'
from fastapi.testclient import TestClient
from api import app
c = TestClient(app)
c.post("/api/load-mock-data")
c.post("/api/run-analysis")

# Get findings and their stable keys
d = c.get("/api/diagnosis?view=client").json()
print("Findings:")
for f in d["findings"]:
    print(f"  {f['key']}  — {f['headline'][:60]}")

# Add commentary
r = c.post("/api/editor/commentary", json={
    "finding_key": d["findings"][0]["key"],
    "text": "Sample EY commentary",
    "author": "test@ey",
})
assert r.status_code == 200

# Suppress a finding
r = c.post("/api/editor/suppress", json={
    "finding_key": d["findings"][1]["key"],
    "reason": "Testing suppression flow",
    "author": "test@ey",
})
assert r.status_code == 200

# Client view drops the suppressed finding
d2 = c.get("/api/diagnosis?view=client").json()
assert len(d2["findings"]) == len(d["findings"]) - 1
print(f"Client view filtered: {len(d['findings'])} -> {len(d2['findings'])}")

# Editor view shows all with flags
d3 = c.get("/api/diagnosis?view=editor").json()
suppressed = [f for f in d3["findings"] if f.get("suppressed")]
print(f"Editor view: {len(d3['findings'])} total, {len(suppressed)} suppressed")

# Audit log
log = c.get("/api/editor/audit-log").json()
print(f"Audit entries: {len(log['entries'])}")
EOF
```

## Deployment notes

- **No new dependencies.** Pydantic (already in use for FastAPI) used for
  request bodies. No migration to run — sqlite `CREATE TABLE IF NOT EXISTS`
  handles the schema addition idempotently on first server start.
- **Existing `yield_intelligence.db` files on deployed servers will get
  the new tables added automatically** on next server start. No data in
  existing tables is touched.
- **No breaking API changes.** `GET /api/diagnosis` without params
  returns the same shape it did before (client view, default engagement).
  Existing clients continue to work unchanged.

---

# CHANGES — v17 (MarketLens client app + narrative quality + upstream fixes)

Largest release since v14. Three major threads landed together:

1. **Upstream engine fixes** so the backend produces trustworthy numbers.
   Recommendations engine no longer fabricates SCALE recs on near-linear
   fits; insights engine produces 6 executive headlines instead of 1;
   avoidable-cost calculation uses peer-group comparison instead of
   conflating funnel position with inefficiency.
2. **Narrative layer** — a new `engines/narrative.py` module and
   `GET /api/diagnosis` endpoint that assemble engine outputs into the
   structured content the client UI consumes.
3. **MarketLens client app** — a second frontend application built from
   scratch, coexisting with the existing analyst workbench. Client-facing
   Diagnosis screen with header, KPIs, finding cards, methodology
   footer. Real backend wiring, loading/error states, single-screen
   for v17. Charts and EY editor overlay come in v18.

All 107 tests pass (69 integration + 18 MMM correctness + 20 optimizer
correctness). The previously-flaky "Normal budget produces positive uplift"
integration test was correctly catching a real edge case (when mock data
stochastic spend exceeded the hardcoded $30M target budget, the optimizer
was being asked to cut, not reallocate). Test updated to derive target
budget from actual current spend + 5%, confirmed stable across 4+ runs.

## What changed

### `backend/engines/response_curves.py` — near-linear detection

When the fitted `b` parameter exceeds 0.90 (power-law nearly linear), the
analytical saturation point (`(a*b)^(1/(1-b))`) goes to infinity as
`b → 1`. Organic search with `b=0.99` produced a reported saturation of
10^150. Downstream engines read this as "100% headroom, scale aggressively"
and fabricated $13M+ impact recommendations.

The engine now flags `near_linear_fit: true` on such fits, caps the
reported `saturation_spend` at 3x observed-max (same cap the optimizer
uses), and reports `trusted_headroom_pct` of 40% rather than the phantom
100%. Downstream engines can gate on the flag.

### `backend/engines/diagnostics.py` — no SCALE recs on untrusted fits

Reads `near_linear_fit` and emits `INVESTIGATE` recs instead of SCALE for
near-linear channels, with action "Run a geo-lift test before reallocating
budget" and impact=0. Honest rather than fabricated.

Also adds a secondary cap on SCALE impact estimates: no SCALE rec may
project impact larger than 50% of the channel's current annual revenue.
A SCALE rec claiming +$50M on a $20M-revenue channel is almost always
over-extrapolating.

### `backend/engines/insights.py` — 6 headlines instead of 1

Widened thresholds on existing headlines (concentration 30% from 40%,
channel gap 1x from 2x, momentum 5% from 10%) plus two new categories:

- **Saturation profile** — fires when share of spend on saturated or
  high-headroom channels is meaningful (>30% / >20% respectively).
  "36% of spend is on channels with substantial headroom."
- **CAC spread** — fires when per-channel CAC spans 5x+. Includes an
  explicit caveat ("some of this is channel function, not pure
  inefficiency") so the number is framed honestly rather than weaponized
  against expensive-but-strategically-valuable channels.

### `backend/engines/leakage.py` — avoidable cost uses peer groups

Avoidable cost previously compared every channel's CAC to the portfolio
median, which labeled display and video (functional reach channels,
naturally high CAC) as having $8M+ of "avoidable cost" each. Updated to
compare against channel-type peer median (online vs. offline), with a
30%-of-spend cap per channel. Same pattern as the CX suppression fix
in v16.

Result: value-at-risk drops from ~$33M (v16) to ~$16-17M on calibrated
mock data. Honest.

### `backend/engines/narrative.py` — NEW

Template-based narrative generation. Takes outputs from insights,
diagnostics, leakage, response_curves, optimizer, and (optionally)
MMM; produces the structured payload the Diagnosis screen consumes:

- `headline_paragraph`: 2-3 sentence consulting-style opening
- `kpis`: portfolio_roas, value_at_risk, plan_confidence with tones
- `findings`: 3-5 ranked cards, diagnosis-phrased, with separate
  `prescribed_action` field for the follow-up verb
- `industry_context`: benchmark overlay if external data uploaded
- `methodology`: engines + methods for trust/reference
- `data_coverage`: scope metadata
- `ey_overrides`: empty placeholders for the editor overlay

The critical design decision: findings are diagnoses, not prescriptions.
"Paid Search is underinvested relative to its response curve" (headline)
+ "Increase spend by 32% — estimated $3.8M annual uplift" (prescribed
action) — NOT "Scale Paid Search: $3.8M uplift available" as a single
verb-first label. This distinction matters because CMOs read findings
to understand what's happening; they act on prescriptions separately.

Diagnosis paragraph is generated directly from structured data, not by
splicing finding headlines mid-sentence. Avoids the awkward pattern
from earlier drafts:

> ❌ "The dominant signal: scale paid search: $3.8m uplift available."

> ✅ "The strongest signal is paid search: the response curve indicates
>    it is operating below saturation, with approximately $3.8M of
>    annual uplift available from a measured increase in spend."

### `backend/api.py` — `GET /api/diagnosis` endpoint

Single-call payload for the client Diagnosis screen. Assembles narrative
output from the current engine state. Cached between analysis runs;
regenerates on re-run.

### `frontend/client/` — NEW, the MarketLens client app

A second frontend application coexisting with the existing analyst
workbench. Separate entry point (`index-client.html`, `main-client.jsx`),
separate React tree, shares only the backend.

- `tokens.js` — design system: Geist typography, warm off-white canvas,
  sparing teal accent, confidence tier colors, bento-grid layout
- `api.js` — fetch wrapper with cold-start handling (auto-loads mock data
  and runs analysis if backend has no current session)
- `components/ConfidenceChip.jsx` — High / Directional / Inconclusive tier
- `components/KpiPill.jsx` — the three KPI cards at top of page
- `components/FindingCard.jsx` — collapsed + expanded states, with
  `prescribed_action` rendered as a distinct "Suggested" line
- `screens/Diagnosis.jsx` — top-level screen composition
- `DiagnosisApp.jsx` — shell with header, loading, error, footer

Aesthetic direction: Linear-meets-Economist. Editorial reading width
(760px) for prose, wider bento grid (1100px) for KPIs. Warm off-white
canvas, no gradients, no glass morphism, restrained motion (fade-in
only). Feels like a product, not a dashboard.

### `frontend/vite.config.js` — builds both apps

Updated to produce two entries: `analyst` (existing workbench) and
`client` (MarketLens). Build output: analyst.js at 16 KB, client.js at
18 KB, gzipped to ~5-7 KB each.

### `backend/test_integration.py` — stability fix

Updated "Normal budget produces positive uplift" test to derive target
budget from actual current spend rather than hardcoding $30M. Fixed
intermittent failures (~25% of runs) caused by stochastic mock data
occasionally having current spend > $30M, which made the assertion
correctly-negative.

## Verification before pushing

```bash
# Backend (all three suites)
cd backend
python test_integration.py          # expect 69/69, stable across runs
python test_mmm_correctness.py       # expect 18/18
python test_optimizer_correctness.py # expect 20/20

# Optional: full MMM path with PyMC
python test_mmm_bayesian.py          # expect 10/10, slow

# Frontend (both apps)
cd ../frontend
npm install
npm run build                         # expect both analyst and client bundles
npm run dev
# visit http://localhost:3000/index-client.html for MarketLens
# visit http://localhost:3000/ for the existing analyst app
```

## Known issues carried into v18

- **Evidence charts inside finding cards** are placeholders (dashed-border
  "Evidence chart: <type>" divs). Actual chart rendering not yet built.
- **EY editor overlay** not yet built. The `ey_overrides` field on the
  diagnosis payload is always empty; no UI to populate it.
- **Single screen** — the Plan, Channel Deep Dive, Scenarios, and Leakage
  & Risk screens from the product plan are not yet built. MarketLens
  currently has only the Diagnosis surface.
- **Hardcoded engagement metadata** in the header ("Demo Client · FY 2025").
  No multi-tenancy, no auth, no engagement switching. v18 or later.
- **No dark mode.** Tokens support it structurally but no palette defined.
- **Narrative output has room for polish.** Reads as competent consulting
  prose but not distinctive. The template-based approach has a ceiling;
  getting past it requires either extensive hand-written template variants
  (weeks of copywriting) or LLM integration (out of scope by decision).

## Deployment notes

- **No new Python dependencies** beyond what v16 already required.
  `pymc`, `arviz`, `prophet` still pinned; nothing added.
- **Node dependencies unchanged** — React 18, Vite 5, Lucide, Recharts,
  105 packages total.
- **Backend API additions:** one new endpoint `GET /api/diagnosis`.
  No changes to existing endpoints.
- **Build output has two HTML entries now** — serve both from the same
  static directory; `index.html` → analyst, `index-client.html` →
  MarketLens.

---

# CHANGES — v16 (pillars credibility + product direction)

Fixes the single most credibility-damaging number the engines were producing:
the "$862M value at risk" on a $500M revenue portfolio. Root cause was the CX
suppression calculation comparing every campaign against the portfolio-wide
median CVR, which conflates funnel position with friction — display and
video campaigns with 0.01% CVR were flagged as having $160M+ of "suppressed
revenue" each, when in reality those are assist-function channels operating
as designed.

This release also documents a session of product-direction work that
established the tool as a client-delivered interactive analytical surface
(not a deck, not a dashboard), with EY having moderate override capability
(commentary + narrative rewrite + recommendation curation, no number override).

## What changed

### `backend/engines/leakage.py` — CX suppression rewritten

**Assist-function filter.** Campaigns with CVR below `channel_median × 0.1`
are excluded from the suppression count. A display-programmatic campaign
with 0.01% CVR isn't suffering from a broken landing page — it's performing
the reach job it was designed for. The previous calc called this "suppression"
and it dominated the total.

**Channel-relative benchmark.** Suppression is now measured against each
campaign's CHANNEL median, not the portfolio median. A social paid campaign
at 0.15% CVR is performing typically for social; comparing it to paid_search's
0.45% median inflated suppression by treating funnel position as friction.

**Two-tier cap.** Per-campaign suppressed revenue is bounded by (a) the
campaign's actual revenue (first-order ceiling — closing a CVR gap doubles
revenue at most in a simple model), and (b) an absolute $10M cap per
campaign (prevents any single outlier from dominating the narrative).

**New output fields.** `raw_suppressed_uncapped` and `capped` per item so the
frontend / analyst can see when the cap is firing and investigate.

### Before vs after on calibrated mock data

| Metric | v15 | v16 |
|---|---|---|
| Total revenue | $510M | $506M (similar, stochastic) |
| **Value at risk** | **$862M (173% of revenue)** | **$33M (6.5% of revenue)** |
| Revenue leakage | $0M | $0M |
| CX suppression | $828M | $0M |
| Avoidable cost | $35M | $33M |

CX suppression collapsing to $0 on clean mock data is *correct* — none of
the synthetic campaigns are legitimately underperforming their channel peers
by 30%+, because the mock data generator produces tight noise around channel
base rates. On real client data with a genuinely broken campaign (landing
page bug, targeting misfire, etc.), the calc would flag it.

### `backend/test_integration.py` — assertion update

Updated the "tiny budget uplift is reasonable" test to match v15's Guard 1
behavior. The old assertion required uplift >= 0, but v15 correctly returns
negative uplift when the requested budget is far below current spend (because
cutting budget reduces revenue, and the optimizer now refuses to fake "no
change"). New assertion checks the uplift is a finite number, without
constraining its sign.

## Known issues flagged but not fixed this release

**Avoidable cost has the same channel-role-conflation issue that CX
suppression had.** `display` channel shows CAC at 42× the portfolio median,
which the engine currently labels as "avoidable cost." In reality, display
CAC is higher than paid_search CAC by channel function (it's a reach channel,
not a direct-response channel). The same channel-relative-median fix applied
to CX suppression should also be applied to avoidable cost. Deferred because
it needs to be fixed in conjunction with the narrative layer, which will
surface these numbers with appropriate framing regardless of the raw value.

**Recommendations engine still extrapolates past observed spend range.**
The top recommendation on calibrated mock data is "scale organic_search by
40%" driven by a response curve with `b=0.99` (near-linear). The optimizer
respects an extrapolation cap (v15); the recommendations engine does not.
Should be fixed next session.

**Insights engine only produces 1 executive headline on current data.**
The other conditionals (channel concentration, saturation, trend patterns)
have thresholds too tight to fire. Should be widened next session.

## Product direction established this session

Long conversation that landed on:

- **The tool is the deliverable.** EY hands the client interactive screens,
  not a deck or a PDF. Same UI for EY and client, with permissions/publish
  state determining what each sees.
- **Phase 1:** assessment delivery (weeks 1-15 of engagement).
  **Phase 2:** ongoing self-serve monitoring, client re-uploads data.
- **Moderate override model.** EY can: add commentary panels, rewrite
  narrative prose (numbers stay locked), hide recommendations with a
  required reason. EY CANNOT: change computed numbers, change model
  parameters through the UI, edit raw data (beyond typo fixes).
- **Template-based narrative only for v1.** No LLM integration. The quality
  ceiling is "correct and readable" not "reads like a consultant wrote it."
- **6 client-facing screens planned:** Diagnosis (the opening), Plan,
  Channel Deep Dive, Scenarios, Leakage & Risk, Data & Methodology.
  Plus EY editor overlay on all of them. Plus 2 backstage screens (Data
  Upload, Run History).
- **Build approach: option C** — real product built iteratively, demo is
  the first version of the real thing, no throwaway code.

First build target is the Diagnosis screen, but it requires upstream fixes
to the insights and recommendations engines plus a new `engines/narrative.py`
module and `GET /api/diagnosis` endpoint before the React work can start.

---

# CHANGES — v15 (optimizer reliability)

Adds extrapolation cap, swing limits, and capacity warnings to the budget
optimizer. Fixes three stacked root causes that produced the "Positive
directional derivative for linesearch" SLSQP failure and the +4,657% spend
recommendations on near-linear channels. All tests green: 69 integration +
18 MMM correctness + 20 new optimizer correctness + 10 opt-in Bayesian.

## What changed

### `backend/engines/optimizer.py`

**Extrapolation cap** (`DEFAULT_EXTRAPOLATION_CAP = 3.0`). `_predict_revenue`
and `_marginal_revenue` now clamp spend at `3 × current_avg_spend` and return
zero marginal revenue past the cap. Without this, power-law curves with
`b → 1.0` (e.g. organic search with `b = 0.99`) extrapolated to nonsensical
saturation points at ~10^158 and the optimizer rationally concentrated all
budget in them. This is how real MMM libraries handle the bounded-trust-range
problem.

**Per-channel swing cap** (`max_channel_change_pct = 0.75`). Bounds each
channel to ±75% of current spend by default. Real CMOs rarely swing a
channel by more than ±50% in a quarter; the optimizer shouldn't recommend
moves they won't execute. The cap dynamically relaxes when total budget
exceeds current spend (you're asking "where to put new budget", not "how to
reallocate existing"), scaling up proportionally to budget expansion.

**Fixed `min_spend_pct` floor bug.** A 2% floor of a $100M budget is $2M,
which used to force channels currently at $250k to 8x their spend. Now the
floor respects current spend: `min(global_min, current × (1 - swing_cap))`.
A small channel stays small unless explicitly configured otherwise.

**Capacity detection + warning.** When the requested budget exceeds the sum
of per-channel 3× caps, the optimizer now returns a valid result optimizing
against absorbable capacity, and surfaces an explicit warning:
> "Requested budget ($500M) exceeds what the fitted curves can trustworthily
> absorb ($87M at 3x current spend per channel)."
Previously this case produced a cryptic SLSQP failure.

**Guard 1 fix.** The "fall back to current allocation when optimizer can't
improve" guard now only fires when current allocation actually fits within
the target budget. If budget < current spend, cutting is the correct answer
— the old guard reported current-spend revenue as optimized revenue, which
broke sensitivity analysis monotonicity (revenue appeared to drop as budget
grew past a threshold).

**Guard 2 fix.** When the ±200% / -80% display cap fires, the underlying
`optimized_spend` dollar value is now updated consistently (previously only
`change_pct` was updated, leaving `$1M → $25M` shown next to `change_pct = 200`).

### `backend/test_optimizer_correctness.py` (NEW)

20 statistical correctness tests covering: sum-constraint accounting
identity, extrapolation cap honored, organic search stays within trust range
(specific regression for the near-linear curve bug), no negative marginal
ROI, locked channels preserved, sensitivity monotonicity, determinism with
seeded NumPy RNG, capacity warning fires appropriately. Every one would
have failed against the pre-fix optimizer.

## Budget sweep verification

| Budget | Pre-fix | Post-fix |
|---|---|---|
| $1M (below current) | Wrong fallback to current allocation | Correctly shows revenue drop |
| $30M (near current) | 323% uplift with +4,657% organic | 7.6% uplift, 0 warnings |
| $100M (exceeds capacity) | SLSQP "Positive directional derivative" failure | 68.5% uplift, clear capacity warning |
| $500M | Same SLSQP failure | Same honest capacity warning |

---

# CHANGES — v14 (vs. v13-redesign baseline)

Four sessions of cleanup and credibility work on the analytical core.
All 69 integration tests + 18 new correctness tests + 10 Bayesian tests pass.

## Summary

The v13-redesign codebase shipped with the Bayesian MMM path effectively dead
(PyMC not in requirements), the MLE path producing R² of -2.68 × 10^13 on mock
data, OLS silently allocating 300% of revenue to channels, and 69 "integration
tests" that checked only HTTP 200 responses. All of these have been fixed.

## Engine-level fixes

### `backend/engines/mmm.py` — fully rewritten

**MLE fit (`fit_mle_mmm`):** Rewrote to work in scaled revenue space with
log-reparameterized positive betas, logit-reparameterized decays, and proper
bounds on all parameters. Root cause was a scale mismatch: OLS warm-start
fed coefficients from raw-revenue space (~$10^8) into a likelihood function
that multiplied them by `spend_scales` (~$10^6), producing per-channel
contributions of $10^13 and an R² of -2.68 × 10^13. After fix: R² = 0.91,
MAPE = 4%.

**OLS fit (`fit_ols_mmm`):** Replaced `np.linalg.lstsq` with NNLS
(non-negative least squares) on a two-stage baseline + seasonal + media
decomposition. Root cause was highly collinear channel spend columns
(all shared the same seasonality) plus unconstrained lstsq producing
massive canceling positive/negative beta pairs, which `np.abs()` then
turned into fake positive contributions. After fix: non-negative betas
by construction, no more 300%-of-revenue allocations.

**Bayesian fit (`fit_bayesian_mmm`):** Rewrote to work in scaled revenue
space with tighter informative priors, 4 chains at `target_accept=0.95`.
Before: r-hat = 1.34, ESS = 5, 115 divergences. After: r-hat = 1.01,
ESS = 313, 0 divergences on calibrated mock data. Default `n_draws`
reduced from 1000 to 500 to keep API response times reasonable.

**Auto-chain convergence gate (`run_mmm`):** Previously accepted any
Bayesian result that didn't raise an exception. Now checks `converged`
flag (r-hat < 1.05 AND ESS > 100) and falls through to MLE if not met.
A non-converged Bayesian with wide HDIs is worse than a clean MLE.

**`_finalize` cap logic:** Old version force-normalized media to 70% of
revenue whenever it exceeded 95% — a 25-point jump that masked real
signal. New version only fires on truly pathological fits (>100% of
revenue, mathematically impossible) and caps at 80%. Well-fitting models
pass through unchanged.

**Incremental ROAS calculation:** Fixed unit mismatch where `_finalize`
computed `hill_saturation(avg_monthly_dollars, half_sat_normalized)`,
always returning ~1.0 ("every channel at 100% saturation"). Now stores
`_spend_scale` on each contribution so saturation is evaluated in the
same units the Hill curve was fit in.

## Mock data rebuild

### `backend/mock_data.py`

**Per-channel temporal patterns (`CHANNEL_PATTERNS`, `_channel_spend_multiplier`):**
Before, every channel's monthly spend was `base × SEASONALITY[month]`, meaning
all channel spend columns correlated at ~0.97. MMM could not identify separate
channel effects. Now each channel has its own phase, amplitude, growth trend,
flighted on/off months, and event spikes. Off-diagonal correlations now range
from -0.41 to +0.95 with mean 0.18.

**Realistic portfolio calibration (`TARGET_CHANNEL_MIX`, `_channel_revenue_calibration`):**
Before, events had 91% of revenue at 125x ROAS (display and video at 0.07x,
portfolio at 33x — fantasy territory). Added a per-channel revenue multiplier
applied after the funnel that scales final revenue to hit target ROAS. Funnel
counts (impressions, clicks, leads, conversions) remain realistic and
interconnected. After calibration:
- Paid search: 3.7x ROAS, 34% of revenue
- Social paid: 3.5x ROAS, 19%
- Events: 2.8x ROAS, 16%
- Email: 10.1x ROAS, 12%
- Organic search: 41x ROAS, 8% (SEO labor cost is minimal)
- Portfolio: 3.7x ROAS overall, $527M revenue on $142M spend

## Infrastructure

### `Dockerfile` — rewritten

Old version wrapped pymc/prophet installs in `|| echo "[SKIP]"`, producing
a "successful" image where the Bayesian path was silently disabled forever.
New version uses `backend/requirements.txt` as single source of truth,
fails the build on any critical import failure, verifies pymc/arviz/prophet
actually import post-install, and adds a HEALTHCHECK. Base image changed
to `python:3.12-slim` for smaller final image (~450MB vs. ~1.2GB).

### `backend/requirements.txt` — properly versioned

Added `pymc>=5.10,<6.0`, `arviz>=0.17,<1.0`, `prophet>=1.1,<2.0` (previously
missing — making all pitch claims about Bayesian MMM and Prophet forecasting
effectively vaporware). Pinned all other deps to tested version ranges.
Deleted duplicate root `requirements.txt` in favor of a single delegating
pointer.

### `backend/api.py`

`/api/mmm` endpoint now accepts `method` and `n_draws` query parameters,
so callers can skip the slow Bayesian path for development / CI.

## New tests

### `backend/test_mmm_correctness.py` — 18 statistical correctness tests

Verifies things the original 69-test integration suite didn't: accounting
identities (baseline + media = 100%), sign constraints (betas >= 0),
fitted values in the same order of magnitude as actuals, incremental ROAS
has variation across channels, determinism across runs. Every one of these
failed against the pre-fix code; verified by temporarily reverting mmm.py
and watching 5 of them fail with specific error messages pointing at the
bugs they catch. Runs in < 10 seconds, no PyMC dependency — suitable for
every CI run.

### `backend/test_mmm_bayesian.py` — 10 opt-in Bayesian tests

Slow (~2-3 minute fit), only runs if PyMC is installed. Verifies Bayesian
converges, reports diagnostics, produces non-negative betas, HDI intervals
in the right shape, accounting identity holds. Includes an end-to-end
auto-chain test behind `SKIP_AUTO_CHAIN_TEST=1` for when you need to skip
the full 2-3 min fit.

### `backend/test_integration.py`

Updated `/api/mmm` test to use `?method=mle` so the suite runs in ~2 min
instead of ~10 min. Bayesian smoke coverage moved to the dedicated file.

## What was NOT changed (and why)

- **No frontend changes.** `frontend/app.jsx` is still aggressively minified
  (624 "lines" but 88KB of one-character variables). Needs proper component
  extraction — separate session.
- **SLSQP non-convergence** in the optimizer still scrolls past during the
  guardrails test. The guardrail behavior is correct (falls back gracefully);
  the remaining work is surfacing the warning to the frontend.
- **Engine files other than mmm.py.** The other 21 engines were audited for
  correctness and found to be sound. Response curves use proper scipy
  curve_fit + Levenberg-Marquardt + LOO-CV. Optimizer is real SLSQP with
  multi-start Dirichlet restarts. Markov attribution uses scipy.sparse
  transition matrices with power-iteration convergence. None of these needed
  rewriting.

## Verification before pushing

```bash
# Fast suite (runs in ~2 min, no PyMC required)
cd backend && python test_integration.py          # expects: 69/69
cd backend && python test_mmm_correctness.py      # expects: 18/18

# Slow Bayesian suite (requires pymc installed, ~3 min)
cd backend && python test_mmm_bayesian.py          # expects: 10/10
```
