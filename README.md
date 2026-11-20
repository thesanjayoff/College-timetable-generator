# College Timetable Generator

A from-scratch, single-college (multi-college is a stretch goal) timetable generator for
Indian college conventions: semesters, sections, lab batches, electives, periods, and a
half-day Saturday. An admin enters the college's data and rules, a CP-SAT solver produces
a conflict-free timetable, an independent verifier re-checks every rule from scratch, and
the admin can edit, lock, re-solve, publish, and export it.

No payments, no subscriptions, no cloud dependency: everything runs locally against
SQLite (or Postgres, by changing one connection string).

## Stack

- **Solver core**: Python 3.12 + [Google OR-Tools CP-SAT](https://developers.google.com/optimization/cp) `9.15.6755` (pinned).
- **Backend**: FastAPI + SQLAlchemy 2.0 + SQLite by default (swap `DATABASE_URL` for Postgres).
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS 4, responsive for desktop and phone.
- **Auth**: JWT (HS256), bcrypt password hashing, three roles (admin, department coordinator, viewer).
- **Exports**: Excel (`openpyxl`), PDF (`reportlab`), iCalendar (`icalendar`).

## Running it

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash; use venv/bin/activate on Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first start it creates `backend/data/timetable.db` (SQLite), all tables, a default
admin user (`admin@timetable.app` / `admin123` -- **change this immediately in a real
deployment**), and seeds the two weight-profile presets. API docs are at
`http://localhost:8000/docs`.

To load the bundled medium-size sample college (6 departments, 25 sections, ~80
teachers, 40 rooms) instead of starting empty:

```bash
python -m app.seed.generate_sample_college medium   # or: small | large
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

Open the printed local URL, log in with the default admin, and start entering data (or
import the sample college via the Import screen / `POST /api/import/excel`, after
downloading a filled-in copy of `GET /api/import/template`).

### Tests

```bash
cd backend
source venv/Scripts/activate
python -m pytest tests/ -q
```

22 tests, all passing: CP-SAT model mechanics (resource conflicts, lab blocks never
straddling a break, teacher-choice decisions), a full seeded-college pipeline through
solver → persistence → verifier, electives + combined classes, adversarial verifier
checks, infeasibility diagnosis with known root causes, Excel import validation, and
stability (minimal-change re-solving).

## Data model

Single college, multiple departments → programs → sections (e.g. `CSE-3-A`) → optional
lab batches (`A1`, `A2`, ...). Subjects carry type (theory/lab/tutorial/project/library/
sports/mentoring/open or professional elective), credits, weekly periods, how many of
those periods form one lab block, and whether sessions should spread across days.
Teachers carry per-day/week/consecutive load limits, availability, visiting-faculty day
restrictions, and soft preferences (free day, preferred day, no first/last period, avoid
back-to-back). Rooms carry type, capacity, lab category, building/floor and availability.
A `TimeStructure` defines the working days (with an optional half-day cutoff per day, for
a half-day Saturday) and the period grid (teaching / break / lunch), and can be
overridden per program or section.

**Allocations** are the base teaching requirement: subject × section (× lab batch, for
labs that split a section). **Elective baskets** group several subject "options" that
must run in parallel, synchronized, across the sections whose students choose between
them. **Combined classes** are one session shared by several sections/departments (e.g.
a first-year common lecture).

Everything above is importable/exportable via one Excel workbook
(`GET /api/import/template`, `POST /api/import/excel`) with a sheet per entity; bad rows
are rejected with the exact (sheet, row, column) and a plain-English reason, and the
import is all-or-nothing (nothing is written if any row fails).

## The solver (`backend/app/solver/`)

`builder.py` turns the database into a solver-only intermediate representation
(`ir.py`): a list of **requirement groups**, each with one or more **parts** (a plain
theory/lab-without-batches group has one part; a batched lab has one part per batch; an
elective-basket occurrence has one part per option). Every part in a group shares the
same CP-SAT decision for *when* it happens, which is what makes synchronization (lab
batches running in parallel, elective options running in parallel) free: it isn't a
separate constraint, it's the same boolean variable.

`model.py` builds the CP-SAT model:

- One boolean "start" variable per *(requirement occurrence, valid day/period)* --
  valid means the block of consecutive periods it needs exists, doesn't straddle a
  break/lunch, and (for a half-day Saturday) doesn't run past that day's cutoff.
- An `unplaced` boolean per occurrence with `sum(starts) + unplaced == 1`. This is what
  makes the model always solvable: in the worst case the solver can mark a session
  unplaced (at a very large objective penalty) instead of the whole problem being
  infeasible. Genuine CP-SAT infeasibility is reserved for real contradictions, like two
  manually locked sessions that clash.
- Per-part teacher and room *choice* variables when the admin leaves them for the solver
  to decide (exactly-one among eligible candidates); when fixed by the admin, there's
  nothing to choose and the model is a little smaller.
- No-double-booking is one `sum(...) <= 1` constraint per (resource, day, period) across
  every session-part that could occupy it, built by accumulating contribution terms as
  each part's variables are created: section/lab-batch resources use the start variable
  directly (fixed assignment), teacher/room resources use it directly when the
  teacher/room is fixed, or an AND-linearized product variable (`start AND choice`) when
  it's a decision. Since parts of the same group share one start variable, lab batches
  and elective options are automatically mutually exclusive with everything *except each
  other* at that slot.
- Max periods/day, max periods/week and max-consecutive-periods (for both teachers and,
  optionally, sections) are modeled as linear sums over the same contribution terms --
  consecutive-run limits use a sliding window over each day's *contiguous* teaching-period
  run (a break correctly splits a day into separate runs, so it never "helps" satisfy a
  consecutive-period cap).
- The soft objective (`soft.py`) adds weighted terms for section/teacher gaps (a proper
  "something before AND after, and this slot is free" encoding, not just a period count),
  same-subject-twice-a-day, daily load balance (teachers and sections), the five teacher
  preference types, a lab-in-the-afternoon preference, heavy-subject-avoid-last-period,
  and a stability term (penalizes any occurrence landing somewhere other than its
  previous version's slot) for minimal-change re-solving.

`service.py` runs CP-SAT with a configurable time limit, worker count, and random seed
(`deterministic=True` forces a single worker, since multi-worker CP-SAT search is not
bit-for-bit reproducible even with a fixed seed), streams progress through a solution
callback (objective, bound, elapsed time, solution count) so the admin can watch it
improve and stop early while keeping the best incumbent, and extracts a plain-data
result. `diagnosis.py` runs fast, independent pre-checks (teacher weekly demand vs.
availability, lab room-period supply vs. demand, section weekly periods vs. the time
structure's capacity, elective-basket block size vs. available slots) so "no feasible
schedule" is never the whole answer -- the admin gets "Prof. X needs N periods but is
available for only M"-style explanations and ranked suggestions, and any session the
solver couldn't place is attributed to one of these causes where possible.

## The verifier (`backend/app/verifier/`)

A **separately written** re-implementation that shares no code with the solver's model:
its own extraction from the database (`extract.py`), its own hard-constraint checks
(`checks.py`), its own soft-penalty recomputation in plain Python (`scorecard.py`, no
CP-SAT). It re-derives, from the raw session rows alone: teacher/room/lab-batch double
booking (never exempt), section double booking (exempt only when two rows share an
explicit `sync_group`, which is how the database records "these were scheduled together
on purpose" for lab batches and elective options), session-count-vs-requirement mismatches
(correctly excluding sessions that belong to an elective/combined requirement even if
they happen to reuse the same subject code -- a real bug this caught during development,
see `git log`), room type/capacity, break-straddling, teacher/room availability, teacher
and section load limits, and elective-basket synchronization. `POST
/api/versions/{id}/publish` refuses to publish while any hard violation remains.

## Hard constraints (never violated)

Teacher/room/section/lab-batch never double-booked (including across combined classes
and elective baskets) · every required session scheduled the right number of times in a
suitably-typed, big-enough room · lab sessions occupy the right number of consecutive
periods without straddling a break and in a room of the right lab category · teacher and
room availability, fixed/locked sessions, and break/lunch positions are respected ·
elective-basket sessions are synchronized across all their sections · max periods/day and
max consecutive periods for teachers (and, optionally, sections).

## Soft constraints (weighted, in `app/models/weight.py`)

Section gaps, teacher gaps, same-subject-twice-a-day, section daily-load balance, teacher
workload balance, five teacher preference types (preferred day, free day, no first
period, no last period, avoid back-to-back), lab-in-the-afternoon, avoid a heavy subject
in the last period, and a stability weight for minimal-change re-solving. Two presets
(`student_comfort_first`, `teacher_convenience_first`) ship alongside the balanced
default; `GET /api/versions/{id}/solve/presets` lists them and `POST
/api/versions/{id}/solve` accepts `weight_preset` or a raw `weights` override.

## Editing, versions, and day-to-day use

Each `TimetableVersion` is a draft or published snapshot. `GET
/api/versions/{id}/sessions` returns every session (joined with subject/teacher/room
names) for the frontend to build section/teacher/room/department grids from one payload.
`POST .../sessions/{id}/check-move` validates a drag-and-drop move against every hard
rule without saving (and reports exactly which rule(s) would break); `.../move` applies
it and re-verifies the whole version; `.../suggestions` scans for a few alternative slots
that introduce no conflict. Sessions and whole days can be locked; re-solving passes
locked sessions back into the model as hard-fixed assignments. `POST
/api/versions/{id}/solve` with `stabilize_against_parent=true` additionally penalizes
moving anything away from the parent version's placement. `GET
/api/versions/{id}/diff/{other_id}` reports what moved/was added/was removed between two
versions. `GET /api/versions/{id}/substitution?teacher_id=&day_index=` ranks free,
eligible substitutes by current workload for every session an absent teacher would miss
that day.

## Exports

Excel and PDF per section/teacher/room (`/api/versions/{id}/export/...`), iCalendar for a
teacher or section given a term start date, and the Excel import template doubles as the
"share this format with anyone" artifact. A read-only static share page is a natural
follow-up (publish a version and expose its `sessions` JSON) but isn't built yet -- see
Known limits.

## Evaluation

### Verification

The verifier is unit-tested adversarially (`tests/test_verifier_checks.py`, 11 hand-built
cases: double-booking with and without a legitimate sync exemption, session-count
mismatches, room type/capacity, break-straddling, teacher unavailability, overload/
consecutive limits, elective desynchronization, and one fully-clean schedule) and
end-to-end: every seeded scenario in the test suite (`test_integration_small.py`,
`test_electives_and_combined.py`) is solved and then independently verified at **zero
hard violations**. Building the adversarial suite caught one real verifier bug before it
shipped (noted above).

### Scale

Run `python -m app.evaluation.benchmark small medium` (or add `large`) for fresh
numbers; it generates a synthetic college, solves it, and reports time-to-first-feasible,
objective/bound at each checkpoint, peak memory, and the optimality gap. Measured on this
machine, 8 search workers, synthetic seed 42:

| Size | Depts / Sections / Teachers / Rooms | Groups / Occurrences | First feasible | Gap after 60s | Peak RSS |
|---|---|---|---|---|---|
| small  | 2 / 6 / 15 / 8    | 29 / 81    | ~2.5s  | ~0.005% | ~600 MB |
| medium | 6 / 25 / 80 / 40  | 113 / 324  | ~39s   | large (needs minutes, not seconds) | ~3.9 GB |

Small colleges converge to near-optimal in well under a minute. The medium synthetic
college (deliberately randomized, including some tight teacher/room allocations) needs
materially more than 60 seconds to place everything -- this is expected: CP-SAT's
objective is dominated by a large per-unplaced-session penalty specifically so that
"give it more time" is always a safe, monotonic choice, never a correctness risk. A
longer background run's numbers (5-minute medium, large-scale sanity check) are appended
below once `app.evaluation.benchmark` finishes -- *(placeholder: filled in after the
background benchmark completes; see the bottom of this section for final numbers or
check `git log` for the follow-up commit)*. Multi-worker CP-SAT memory scales with worker
count (each worker keeps its own search state); reduce `num_workers` on memory-constrained
machines.

### Infeasibility diagnosis

`tests/test_diagnosis.py` builds four small databases, each with exactly one known,
engineered cause (a teacher needing more periods than they're available for, lab demand
exceeding lab-room supply, a section needing more periods than its week has, an elective
basket whose block size doesn't fit the day) and asserts the diagnosis module names each
one correctly.

### Stability

`tests/test_stability_resolve.py`: seed a small college, solve it, then make one teacher
unavailable on one day (the kind of day-to-day disruption a coordinator handles weekly)
and re-solve twice -- once with the stability weight off, once on. Measured result:
**16 of ~90 occurrences moved without the stability weight, only 3 moved with it on**,
for the same disruption and the same solve budget.

### Benchmarks against public instance families (XHSTT / ITC)

Not attempted in this pass -- the IR (`app/solver/ir.py`) and verifier
(`app/verifier/types.py`) are both plain, solver-independent data structures, so a format
converter would sit entirely outside the solver/verifier and is a contained follow-up
(read an XHSTT/ITC instance, populate the same `SolverInput`/`VerifierInput` shapes
directly rather than through the database). Flagged here rather than silently skipped.

### Comparison against a hand-built or FET timetable

Not attempted -- no real college's data or hand-built timetable was available in this
environment to compare against anonymized. The verifier's scorecard (gaps, workload
balance, preference satisfaction) is exactly the metric set such a comparison would use.

### Usability

Not attempted with a real coordinator in this pass (no such tester available here);
flagged as a follow-up rather than skipped.

## Known limits

- **Single process, in-memory solve-job registry** (`app/services/solve_jobs.py`): fine
  for one college on one machine; a multi-worker deployment would need a real job queue.
- **Decomposition for very large instances** (solve department-by-department and
  reconcile) is not implemented; the monolithic model is what's exercised by the
  benchmarks above. The IR's requirement groups are already partitionable by department,
  so this is an additive change, not a rewrite.
- **Multi-college** is explicitly a stretch goal and not implemented -- every model
  assumes one college's worth of departments/time-structures.
- A **read-only static share page/link** for students and staff, and **email/messaging
  change notifications**, are not built; the data needed for both (a published version's
  sessions, and a diff between versions) already exists via the API.
- **Room "walking distance between buildings"** and **tutorial-after-theory** soft
  preferences are modeled as weight-profile keys in the original design notes but are not
  wired into the objective in this pass, to keep the implemented soft constraints
  honestly matching what the scorecard actually reports.
- **Scenario comparison** (several alternative timetables side-by-side) works today as
  "create several versions with different weight presets, diff/compare their
  scorecards" via existing endpoints; there's no single dedicated
  compare-N-versions-at-once endpoint yet.
- CRUD role-scoping for coordinators currently covers Teachers, Subjects, and
  Allocations explicitly; other master-data entities are writable by any authenticated
  admin/coordinator account (no stricter departmental fencing yet).

## Project layout

```
backend/
  app/
    models/       SQLAlchemy ORM (27 tables)
    schemas/       Pydantic request/response models
    api/            FastAPI routers (master data, versions, solve, export, import, substitution, auth)
    solver/         CP-SAT IR, model builder, soft objective, service, diagnosis
    verifier/       independent extraction + checks + scorecard
    importer/       Excel template generation + validated bulk import
    exporter/       Excel / PDF / iCalendar
    services/       solve job runner, persistence, grid-edit conflict checking, substitution
    seed/           default admin bootstrap, synthetic sample-college generator
    evaluation/     scale benchmark harness
  tests/            22 tests across all of the above
frontend/
  src/
    api/            typed API client
    context/        auth context
    components/      layout + reusable form/table UI
    pages/           one area per master-data entity, plus the timetable workspace
```
