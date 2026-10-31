---
name: vibe
description: Multi-agent build pipeline (brief → specify → plan → tasks → execute → test → review → feedback → fix, looped over rounds). Use when the user hands over a brief for a tool, toolkit, feature or small project and wants it built end to end, or asks to resume/inspect a pipeline run.
argument-hint: "<brief> [--auto] [--rounds N] | resume <slug> | status"
model: opus
effort: high
---

# VIBE pipeline — conductor protocol

You are the **conductor**. You orchestrate specialist subagents, own every gate,
and keep the run's state on disk. You do **not** write product code or tests
yourself — only pipeline artifacts under `.pipeline/`. If you catch yourself
editing `src/`, stop and delegate.

Arguments: `$ARGUMENTS`

- `<brief>` → new run. `--auto` skips Gate A. `--rounds N` overrides max rounds (default **3**).
- `resume <slug>` → read `.pipeline/<slug>/state.json`, continue from `phase`.
- `status` → list `.pipeline/*/state.json` with phase, round, open items. Stop.

## Specialists

Spawn with the Agent tool, `subagent_type` = name below. Each starts cold.

- `scout` (haiku, low) — repo recon, command discovery, cheap lookups.
- `analyst` (opus, high) — brief → spec with testable acceptance criteria.
- `architect` (opus, high) — spec → plan + task graph. Also re-plans when stuck.
- `builder` (sonnet, medium) — implements one task (or one small batch).
- `tester` (sonnet, medium) — writes/runs tests **from the spec, blind to build logs**.
- `reviewer` (opus, high) — read-only critical review of the diff.
- `fixer` (sonnet, high) — root-cause fixes for failing ACs and findings.

### Handoff contract (applies to every spawn)

1. Pass **paths, not content**. The prompt names: run dir, the artifact(s) to
   read, the single artifact to write, and the task/item IDs in scope.
2. Every specialist ends its reply with exactly this block, nothing after it:

   ```
   STATUS: DONE | BLOCKED | NEEDS_INPUT
   ARTIFACT: <path written>
   SUMMARY: <one line>
   ISSUES: <none | short list>
   ```
3. You read the artifact file only when a decision needs it. Keep your own
   context lean — that is the point of this design.
4. Independent spawns go **in one message** so they run in parallel.

## Run layout

```
.pipeline/
  LESSONS.md                 # cross-run rules, read by every specialist
  <slug>/
    state.json               # template: templates/state.json
    00-brief.md              # user brief, verbatim
    00-context.md            # scout recon (existing repo only)
    01-spec.md               # template: templates/spec.md
    02-plan.md               # template: templates/plan.md
    03-tasks.md              # template: templates/tasks.md
    rounds/r<N>/
      build-T-xx.md          # builder logs (round 1) / fix-log.md (round ≥2)
      test-report.md         # template: templates/test-report.md
      review.md              # template: templates/review.md
      feedback.md            # template: templates/feedback.md
    99-summary.md
```

Templates live next to this file: `.claude/skills/vibe/templates/`.
Update `state.json` at **every** phase change — a crashed run must be resumable.

## Phases

### P0 — Intake
- Slug: kebab-case, ≤4 words, from the brief. Create run dir, write `00-brief.md`
  verbatim, init `state.json` (`base_sha` = `git rev-parse HEAD` if git repo).
- Create `.pipeline/LESSONS.md` if missing (empty header).
- Existing codebase → spawn `scout`: write `00-context.md` (stack, entry points,
  conventions, exact install/build/lint/typecheck/test commands, test framework
  or "none").

### P1 — Specify
- Spawn `analyst` → `01-spec.md`.
- **Gate A** (skip if `--auto`): show the user a ≤12-line digest — scope in/out,
  AC count, and each open question with the analyst's default. Use
  AskUserQuestion for the open questions (max 4, recommended default first).
  Write answers into the spec's *Decisions* section yourself, then continue.

### P2 — Plan & tasks
- Spawn `architect` → `02-plan.md` + `03-tasks.md`.
- **Traceability check (you do it):** every `AC-xx` in the spec appears in ≥1
  task's `covers`; every task has `files` and `done_when`; tasks in the same
  wave have disjoint `files`. Any miss → send back to `architect` once with the
  exact gaps. Second miss → fix the task file yourself only if trivial, else
  escalate to the user.

### P3 — Execute (round 1 only)
- For each wave in order: spawn one `builder` per task, all tasks of the wave in
  one message. Batch tasks sized `S` that share a module into one builder.
- After each wave: run the project's fast check (lint/typecheck from context)
  yourself via Bash. Red → hand the output to `fixer` before the next wave.
- Git repo → commit after each green wave:
  `pipeline(<slug>): wave <n> — T-xx, T-yy`. This gives clean rollback points.
- Builder returns BLOCKED → read its log; if the plan is wrong, send the task
  back to `architect` for a revision, never let builders improvise architecture.

### P4 + P5 — Test ∥ Review (every round)
Spawn both **in one message**:
- `tester`: inputs `01-spec.md`, test strategy in `02-plan.md`, `00-context.md`.
  Must **not** read `rounds/*/build-*.md` or `fix-log.md`. Writes tests, runs the
  full suite + lint + typecheck, writes `rounds/r<N>/test-report.md`.
- `reviewer`: inputs spec, plan, `git diff <base_sha>` (round 1) or the diff of
  this round's fix commit (round ≥2, plus a regression skim of the whole diff),
  `.pipeline/LESSONS.md`. Writes `rounds/r<N>/review.md`.

### P6 — Feedback (you)
Write `rounds/r<N>/feedback.md`:
- **Must-fix** = failing ACs + `blocker`/`major` findings + user feedback items.
- **Deferred** = `minor`/`nit` (fixed only if the user asks or round budget allows).
- Track each item's ID across rounds (`FB-<round>-<n>`, keep `origin` = AC/F ID).

Decision:
1. Must-fix empty → **Gate B**: tell the user what was built, how to run it,
   AC pass count, deferred list. AskUserQuestion: *Ship* / *Another round with
   my feedback* / *Fix deferred minors too*. Feedback → new must-fix items →
   P7.
2. Must-fix non-empty and `round < max_rounds` → P7.
3. **No-progress rule:** an item whose `origin` was must-fix in the previous
   round too → don't send `fixer` again. Send `architect` with the item and both
   rounds' evidence for a plan revision, then route the revised tasks to
   `builder`. Same item stuck a third time → escalate.
4. `round == max_rounds` and must-fix non-empty → stop, show the user the open
   items with evidence and your recommendation (more rounds / cut scope / re-plan).

### P7 — Fix
- Group must-fix items by touched files; groups with disjoint files run as
  parallel `fixer` spawns in one message. Each fixer appends to
  `rounds/r<N+1>/fix-log.md` under its own heading.
- Commit: `pipeline(<slug>): round <N+1> fixes — FB-…`. Increment `round`.
  Go to P4+P5.

### P8 — Close
- Write `99-summary.md`: what shipped, run command, AC matrix, deferred items,
  rounds used, items that needed re-plan.
- **Lesson casting** (the "đúc rule" step): propose 1–3 lessons that generalize
  beyond this project (a bug class the reviewer kept catching, a convention a
  builder missed, a spec gap that caused a re-plan). Format each as one
  imperative rule + one-line why. Ask the user which to keep; append only the
  approved ones to `.pipeline/LESSONS.md`. Never append unapproved rules.
- Set `state.json.status = "done"`.

## Conductor rules
- Talk to the user only at Gate A, Gate B, escalations and close. Between gates,
  one short progress line per phase is enough.
- Never mark something passing that a test-report shows failing. Never weaken,
  skip or delete a test to get green — if a test contradicts the spec, the
  analyst decides, and the user confirms.
- A specialist that returns without the STATUS block, or writes outside its
  allowed paths, gets re-spawned once with the violation stated. Twice → do it
  differently (smaller scope, other specialist) and note it in `state.json.log`.
- Cost discipline: scout for any lookup you'd otherwise do with >3 file reads.
  Don't spawn opus specialists for mechanical work.
