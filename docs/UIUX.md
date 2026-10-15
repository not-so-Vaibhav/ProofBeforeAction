# ProofBeforeAction — UI/UX Design Document

Version 1.0 · Stack: React + Vite + TypeScript + Tailwind CSS + @xyflow/react + Recharts + Lucide

## 1. Design intent

ProofBeforeAction should feel like a **calm, trustworthy engineering console**, closer to a security or observability tool than a marketing site. The interface exists to answer three questions in this order:

1. **What is the decision?** (ALLOW, HUMAN_REVIEW, BLOCK)
2. **How do we know?** (evidence, with its tier)
3. **What do we do next?** (verified safer alternative)

### Principles

- **Decision first.** The verdict is the largest element on the report page.
- **Evidence is visible.** Every finding shows its tier badge. Proof is never hidden behind a click.
- **Honest uncertainty.** `UNKNOWN` and `NOT_RUN` are shown as clearly as failures.
- **Never colour alone.** Decisions and tiers use icon, label and colour.
- **Dense but quiet.** Dark surfaces, restrained accents, generous spacing between groups.
- **Demo-ready.** Every key screen can be reached in one click from presenter mode.

## 2. Design tokens

### Colour (dark theme, default)

| Token | Hex | Use |
|---|---|---|
| `bg` | `#0A1020` | App background |
| `surface` | `#101A30` | Cards and panels |
| `surface-2` | `#16223F` | Raised elements, table headers |
| `border` | `#22305A` | Dividers and outlines |
| `text` | `#E6EDF7` | Primary text |
| `text-muted` | `#93A4C3` | Secondary text |
| `accent` | `#4C8DFF` | Primary actions, focus ring |
| `accent-soft` | `#99CEFF` | Links, highlights (matches the architecture diagram) |
| `allow` | `#22C55E` | ALLOW |
| `review` | `#F5A524` | HUMAN_REVIEW |
| `block` | `#EF4444` | BLOCK |

### Evidence tier colours

| Tier | Colour | Icon (Lucide) |
|---|---|---|
| `REPRODUCED` | `#EF4444` red solid | `FlaskConical` |
| `PROVEN` | `#F97316` orange | `ShieldCheck` |
| `INFERRED` | `#EAB308` yellow outline | `GitBranch` |
| `UNKNOWN` | `#94A3B8` grey dashed | `HelpCircle` |

### Provenance styles (graph)

| Provenance | Style |
|---|---|
| `extracted` | Solid border |
| `declared` | Dashed border |
| `modeled` | Dotted border |

### Typography

- UI: **Inter** (fallback system-ui). Headings 600, body 400.
- Code, SQL, IDs: **JetBrains Mono** (fallback ui-monospace).
- Scale: 12 / 14 / 16 / 20 / 28 / 40 px. Decision verdict uses 40 px.

### Shape, spacing, motion

- Radius: 12 px cards, 8 px inputs and badges, 999 px pills.
- Spacing scale: 4, 8, 12, 16, 24, 32, 48.
- Elevation: borders instead of heavy shadows; one soft glow on the decision card tinted by decision colour.
- Motion: 150–250 ms ease-out. Animate: score count-up, graph path highlight, remediation steps appearing in sequence. Respect `prefers-reduced-motion`.

## 3. Information architecture

| Route | Screen | Purpose |
|---|---|---|
| `/` | Dashboard | Recent analyses, review queue, evaluation summary |
| `/new` | New Analysis | Pick a domain and scenario, submit a change |
| `/analyses/:id` | Report | The main screen: decision, evidence, graph, remediation |
| `/review` | Review Queue | Analyses awaiting a human decision (stretch) |
| `/history` | History | Past analyses and audit trail |
| `/eval` | Evaluation | Measured results from the scenario suite |

Persistent left sidebar with: Dashboard, New Analysis, Review Queue, History, Evaluation. Top bar with project selector, **role switcher** (Analyst / Reviewer) and a **Presenter mode** toggle.

## 4. Screens

### 4.1 Dashboard

```
+---------+------------------------------------------------------+
| Sidebar | Project: demo-code-01 v      Role: Analyst v  [Present] |
|         +------------------------------------------------------+
| Dash    |  [Analyses 24]  [Blocked 9]  [In review 3]  [Domains 2] |
| New     |                                                      |
| Review  |  Recent analyses                  | Evaluation        |
| History |  - BLOCK  Drop patient_id   86    | Critical caught   |
| Eval    |  - REVIEW Remove night shifts 52  | 100%  (n=12)      |
|         |  - ALLOW  Add index        12     | False blocks 0    |
|         |                                   | Mean latency 1.8s |
+---------+------------------------------------------------------+
```

Elements: four stat tiles, recent analyses list (decision pill, title, score, domain chip, time), evaluation summary card. Empty state: *"No analyses yet. Run a demo scenario."* with a primary button.

### 4.2 New Analysis

```
+------------------------------------------------------------+
| New analysis                                               |
| Domain  ( Coding & Data )  ( Healthcare Operations )       |
| Scenario  [ Drop referenced column v ]   [Load example]    |
| Change type  [ SQL migration v ]                           |
| Title    [ Remove patient identifier        ]              |
| Payload  +----------------------------------------------+ |
|          | ALTER TABLE patients DROP COLUMN patient_id; | |
|          +----------------------------------------------+ |
| [ Run analysis ]                                           |
+------------------------------------------------------------+
```

Behaviour: choosing a scenario fills the form with the fixture payload. The payload editor is a monospace textarea (no heavy editor needed). Submitting shows a **progress stepper** (Parse → Graph → Validate → Replay → Score → Decide) that advances as the request runs, then routes to the report.

### 4.3 Report (core screen)

Header band, then tabs. Tabs: **Overview**, **Evidence**, **Impact graph**, **Remediation**.

```
+------------------------------------------------------------------+
| <- Back   Remove patient identifier        domain: coding_data   |
+------------------------------------------------------------------+
|  [X] BLOCK            Risk score 86 / 100  (heuristic)           |
|  Critical rule failed: schema dependency                         |
|  Coverage 100%   Checks run 6/6   Graph v 9f3a   Rules v 2c1d    |
+------------------------------------------------------------------+
| Overview | Evidence | Impact graph | Remediation                  |
+------------------------------------------------------------------+
| Why this decision                                                |
|  1. Critical rule failed: dependent view still references column |
|  2. 4 downstream resources affected                              |
|                                                                  |
| Risk factors   S 90 ====== D 40 === V 100 ======= I 100 ===== U 0|
|                                                                  |
| Findings                                                         |
|  (flask) REPRODUCED  critical  View v_patient_report fails       |
|          error: no such column ...      [view evidence]          |
|  (branch) INFERRED   medium    Pipeline analytics_pipeline reads |
|          patients.patient_id             [view path]            |
+------------------------------------------------------------------+
```

**Decision card.** Large icon + label (`BLOCK`, `HUMAN REVIEW`, `ALLOW`), tinted glow, score gauge, one-line reason, and a small note: *"Score is a heuristic, not a failure probability."*

**Overview tab.** Reasons list (ordered by decision precedence), risk factor bars (S, D, V, I, U with tooltips explaining each), findings grouped by class (Confirmed, Potential, Unknown), with the explanation text from the explainer.

**Evidence tab.** Table of validations (check, status chip `PASSED`/`FAILED`/`NOT_RUN`, details) and an expandable finding list. Each finding expands to show raw evidence in monospace (the statement and the actual error). A filter row lets the user filter by tier.

**Impact graph tab.** See section 6.

**Remediation tab.** See section 7.

### 4.4 Review Queue and History (stretch / P1)

Table of analyses with filters (decision, domain). In the Report, a **Review panel** appears for `HUMAN_REVIEW` or `BLOCK` when role is Reviewer: Approve and Reject buttons with a required comment field. Role Analyst sees the panel disabled with the message *"Reviewer role required."* History shows an audit timeline per analysis.

### 4.5 Evaluation

Stat tiles (critical-risk detection, false-block rate, dependency precision and recall, mean latency) and a table of the 12 scenarios with expected versus actual decision and a match tick. A Recharts bar chart compares score by scenario, coloured by decision. A caption states: *"Measured on a labeled suite of 12 scenarios; not a general accuracy claim."*

## 5. Components

| Component | Notes |
|---|---|
| `DecisionBadge` | Props: decision, size. Icon + label + colour |
| `ScoreGauge` | Semi-circle or bar, 0–100, thresholds marked at 30 and 70 |
| `TierBadge` | Tier colour, icon, label, tooltip with definition |
| `StatusChip` | `PASSED`, `FAILED`, `NOT_RUN` |
| `FindingCard` | Severity, tier, message, expandable evidence |
| `FactorBar` | Label, value, tooltip explaining the factor |
| `GraphCanvas` | React Flow wrapper, see section 6 |
| `RemediationTimeline` | See section 7 |
| `ProgressStepper` | Analysis pipeline progress |
| `ScenarioPicker` | Domain-aware list with example payloads |
| `EmptyState`, `ErrorState`, `Skeleton` | Every data view has all three |
| `Layout` | Sidebar, top bar, role switcher, presenter toggle |

## 6. Impact graph specification

- **Library:** `@xyflow/react`. Layout via simple layered positioning (left to right by BFS depth). A small `dagre` or manual layout is acceptable.
- **Nodes:** rounded rectangles with a type icon, name and a provenance border. The changed resource is the **entry node**, highlighted in the accent colour with a pulsing ring.
- **Edges:** arrowed, labelled with the relationship on hover.
- **Affected paths:** edges and nodes on a path from the entry node are emphasised; unrelated nodes are dimmed to 35% opacity.
- **Finding link:** nodes with a `REPRODUCED` or `PROVEN` finding show a red or orange corner marker. Clicking a node opens a side panel with the node's metadata, its findings and the path(s) from the entry node.
- **Uncovered dependencies:** shown as grey dashed ghost nodes labelled *"Unresolved"*, so missing coverage is visible.
- **Legend:** provenance styles, tier markers, entry node.
- **Controls:** zoom, fit view, toggle *"Show only affected"*.
- **Healthcare view:** same canvas. Node types use department, ward, shift, slot and report icons.

## 7. Remediation timeline (signature feature)

Vertical stepper, one card per step:

```
[BLOCK 86]  Original change
     |
[1] Add replacement column / keep column        -> REVIEW 41
[2] Migrate dependent queries and view          -> REVIEW 33
[3] Re-validate in replay                       -> ALLOW 18
[4] Backup, then drop column (needs approval)   -> ALLOW 18
```

Each card shows description, the **re-verified decision and score** as a pill, and a mini change in score (down arrow). A header line states *"Verified by re-running the analysis engine on each step."* If any step is not `ALLOW` or `HUMAN_REVIEW` with all checks run, show *"Plan not fully verified"* in amber. Steps animate in sequentially. (The numbers above are illustrative; real values come from the engine.)

## 8. States, errors and copy

| State | Behaviour |
|---|---|
| Loading | Skeletons, never blank screens; analysis shows the progress stepper |
| Empty | Friendly message plus the next action |
| API error | Inline banner with the error message and Retry |
| Replay not run | Chip `NOT_RUN` with tooltip *"Replay could not run for this SQL; findings fall back to static evidence."* |
| Partial coverage | Amber banner: *"Coverage 72%. Some dependencies could not be resolved. Human review required."* |

Microcopy rules: plain language, no hype, no claims of certainty beyond the tier. Use *"potential consequence"* for inferred items.

## 9. Presenter mode (demo support)

A toggle in the top bar that:

- Adds a floating **scenario bar** with buttons: A1 Drop column, A2 Auth change, A3 Ambiguous, B1 Night shifts, B2 Department mapping, Agent demo.
- One click loads the scenario, runs the analysis and opens the report.
- Increases base font by one step and hides secondary chrome.
- Includes a **"Reset demo data"** button calling the seed script.

## 10. Responsiveness and accessibility

- Primary target: laptop or projector at 1280–1920 px. Tablet works with a collapsed sidebar. Mobile is not a priority, but pages must not break.
- Contrast at least WCAG AA on all text. Focus ring (2 px accent) on every interactive element.
- Decisions and tiers always include text labels and icons.
- Keyboard: tabs, buttons and graph side panel reachable by keyboard.
- `aria-live` region announces analysis completion.

## 11. Frontend implementation notes

- Types in `src/types/` mirror Pydantic models exactly (`Decision`, `Tier`, `Finding`, `AnalysisReport`, and so on).
- `src/services/api.ts` wraps axios with a base URL from `VITE_API_URL` and sends the `X-Role` header.
- React Query is optional; plain hooks are fine.
- **Mock mode:** if `VITE_USE_MOCK=true`, load JSON from `src/mocks/` that follows the Schema doc, so the UI can be built before the backend is ready.
- Do not reimplement scoring or decision logic in the frontend.

## 12. Visual quality checklist

- [ ] Decision is the most prominent element on the report
- [ ] Every finding shows a tier badge
- [ ] Graph highlights the path and dims the rest
- [ ] Unresolved dependencies are visible
- [ ] Remediation shows verified scores per step
- [ ] Presenter mode runs all six scenarios in one click each
- [ ] No screen is ever blank during loading or error
