---
name: vibe
description: Four-agent build pipeline for vibe projects (brief → spec → plan → build → test ∥ review → feedback → fix, looped over rounds). Use when the user hands over a brief for a tool, toolkit, feature or small app and wants it built end to end, or asks to resume/inspect a pipeline run.
argument-hint: "<brief> [--auto] [--rounds N] | adopt | roadmap <file> | fix <file|text> | resume <slug> | status"
model: opus
effort: high
---

# VIBE pipeline v2 — conductor protocol

Four roles. Each one exists because it adds something the others can't:

- **conductor** (you, Opus, high) — *decides.* Recon, spec, plan, task split,
  routing, gates, feedback synthesis, re-plans, lessons. Writes only `.pipeline/`.
- **builder** (Sonnet, high) — *makes.* Implements tasks and fixes must-fix items.
- **tester** (Sonnet, medium) — *checks behaviour, blind.* Tests from the spec,
  never from build logs. Screenshots for UI.
- **reviewer** (Opus, high) — *checks quality, read-only.* Second strong model
  looking at the diff with fresh eyes.

Why not more: spec and plan are judgment work on one shared mental model —
splitting them across agents adds cold starts and loses intent. Fixing is
building with a bug report. Recon is a few Greps. The independent *checks*
(tester, reviewer) are the only places where separation buys quality.

Arguments: `$ARGUMENTS`

- `<brief>` → new run. `--auto` skips Gate A. `--rounds N` overrides max rounds (default **3**).
- `resume <slug>` → read `.pipeline/<slug>/state.json`, continue from `phase`.
- `status` → list `.pipeline/*/state.json` with phase, round, open items. Stop.
- `adopt` / `roadmap <file>` / `fix <file|text>` → brownfield modes, below.

## Tiers — pick at intake, record in `state.json.tier`

- **Lite** (one module, ≲300 LOC, no external API): conductor → builder →
  reviewer (runs the tests too) → builder fixes. Spec ≤ **6 ACs**.
- **Standard** (small app, a UI, one external API): all four roles. Builders
  sequential by default. Spec ≤ **15 ACs**.

Bigger than Standard → split into milestones (`roadmap` mode), don't add agents.

## Handoff contract (every spawn)

1. Pass **paths, not content**: run dir, artifacts to read, the one artifact
   to write, the task/item IDs in scope.
2. Every specialist ends its reply with exactly:
   ```
   STATUS: DONE | BLOCKED | NEEDS_INPUT
   ARTIFACT: <path written>
   SUMMARY: <one line>
   ISSUES: <none | short list>
   ```
3. Read an artifact only when a decision needs it. Your context is the
   scarcest resource in the run.
4. Independent spawns go **in one message** so they run in parallel.

## Run layout

```
.pipeline/
  LESSONS.md                 # cross-run rules, read by every role
  _project/                  # brownfield only: context, baseline, roadmap
  <slug>/
    state.json  00-brief.md  00-context.md
    01-spec.md  02-plan.md   03-tasks.md
    rounds/r<N>/  build-T-xx.md | fix-log.md  test-report.md  review.md
                  feedback.md   shots/
    99-summary.md
```

Templates: `.claude/skills/vibe/templates/`. Update `state.json` at every
phase change so a crashed run is resumable.

## Phases

### P0 — Intake (you)
- Slug (kebab-case, ≤4 words), run dir, `00-brief.md` verbatim, `state.json`
  (`base_sha` = `git rev-parse HEAD`). Create `.pipeline/LESSONS.md` if missing.
- Existing code → write `00-context.md` yourself: stack, layout, conventions,
  exact install/build/lint/typecheck/test commands (from manifests/CI, never
  guessed), test framework. ≤40 lines. Pick the tier.

### P1 — Specify (you) + Gate A
- Write `01-spec.md` from the template. Rules:
  - AC = a behaviour that would **hurt the user if it broke**, checkable by a
    program. Edge cases live inside tests, not as extra ACs. Respect the cap.
  - Scope Out is mandatory and specific.
  - Open questions only when the answer changes the build; max 4, each with
    your default.
- **Gate A** (skip with `--auto`): ≤12-line digest + open questions. Record
  answers under *Decisions*.

### P2 — Plan (you)
- Write `02-plan.md` and `03-tasks.md`. Every AC covered by ≥1 task; every task
  has `files`, `covers`, `done_when`, size S/M. Same-wave tasks must have
  disjoint files. Test strategy precise enough for a blind tester.
- UI project: wave 1 = **clickable skeleton** (real layout and components,
  fake data). After it, **mini-gate**: show the user screenshots before the
  remaining waves. Cheapest moment to change UX.

### P3 — Build (round 1)
- One `builder` per task or per batch of small tasks in the same module.
  Parallel only for disjoint-file tasks in the same wave.
- After each wave, run lint/typecheck yourself. Red → back to the builder.
- Commit per green wave: `pipeline(<slug>): wave <n> — T-xx, T-yy`.
- Builder BLOCKED because the plan is wrong → you revise the plan. Never let a
  builder improvise architecture.

### P4 ∥ P5 — Test ∥ Review (every round, one message)
- `tester`: reads spec, plan's *Test strategy* + *Commands*, context. Must not
  read build/fix logs. Writes tests, runs suite + lint + typecheck, UI
  screenshots (1280px + 390px) → `rounds/r<N>/test-report.md`.
- `reviewer`: spec, plan, `LESSONS.md`, diff (`git diff <base_sha>` in round 1;
  the round's fix commit + regression skim after) → `rounds/r<N>/review.md`.

### P6 — Feedback (you)
Write `rounds/r<N>/feedback.md`: **must-fix** = failing ACs + blocker/major
findings + user feedback; **deferred** = minor/nit. IDs `FB-<round>-<n>` with
`origin`.
1. Must-fix empty → **Gate B**: what was built, how to run, AC pass count,
   screenshots, deferred list. User: Ship / feedback → next round / fix minors.
2. Must-fix non-empty and `round < max_rounds` → P7.
3. **No-progress rule:** an item must-fix two rounds running → don't resend
   it. Re-plan it yourself with both rounds' evidence, then send the revised
   task to a builder. Third time → escalate.
4. Out of rounds → stop, show open items with evidence and your recommendation.

### P7 — Fix
- `builder` in fix mode, grouped by files (disjoint groups in parallel).
  Appends to `rounds/r<N+1>/fix-log.md`. Commit
  `pipeline(<slug>): round <N+1> fixes — FB-…`. round++ → P4 ∥ P5.

### P8 — Close
- `99-summary.md`: what shipped, run command, AC matrix, deferred, rounds,
  re-plans.
- **Lesson casting:** propose 1–3 lessons that generalize beyond this project,
  one imperative rule + one-line why each. Append only the ones the user
  approves to `.pipeline/LESSONS.md`. `state.json.status = "done"`.

## Brownfield modes

- **`adopt`** (once per repo): write `_project/context.md` (P0 recon + churn
  hotspots from `git log --stat -50`, TODO count, docs found) and
  `_project/baseline-spec.md` (what the app does today as `BL-xx`, each
  `verified`/`assumed`, sourced from code and docs only). `tester` runs the
  existing suite → `_project/baseline-report.md`. Show health + untested core;
  recommend a `safety-net` run (tester only: one characterization test per
  untested core `BL-xx`) before any feature work.
- **`roadmap <file>`** (needs `adopt`): split into shippable milestones
  `M1..Mn` in `_project/roadmap.md` (goal, items, deps, risk, size, brief).
  User approves order, then run each milestone as a normal run, one at a time.
- **`fix <file|text>`**: skip P1–P3. Write `rounds/r1/feedback.md` directly
  (one `FB-1-n` per bug, repro if known), then P7 → P4∥P5 → P6. Items that are
  really features go back to the user for a roadmap run.

Later runs in an adopted repo reuse `_project/context.md`; the reviewer also
checks the `BL-xx` list for regressions.

## Rules
- Talk to the user at gates, escalations and close; one progress line per
  phase otherwise.
- Never call something passing that a report shows failing. Never weaken,
  skip or delete a test to go green — a test that contradicts the spec is
  your call to arbitrate, and the user confirms.
- Paid or rate-limited external APIs are mocked in tests. A real smoke call
  uses the user's key and only after asking.
- A specialist missing the STATUS block or writing outside its paths gets one
  re-spawn with the violation stated; twice → change approach, log it.
