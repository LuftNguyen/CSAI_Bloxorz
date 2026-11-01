# Experimental evaluation package

Entry point: [Section 4 draft in Vietnamese](report_notes/section4_vi.md).

## Data cohorts and evidence

- Main comparison: **350 historical macOS runs**, 10 levels × 7 configurations × 5 repetitions, weighted λ=0.25. Includes DFS. Exact source/level hashes and summaries audited; original timing never rerun or replaced.
- Other historical data: **350 unit-cost + 360 lambda-sweep runs**, separate snapshots in `metadata/historical_datasets/`. No pooling into main timings.
- New Windows cost survey: **140 measured solves**, 10 levels × 7 lambda values × BFS/UCS, one observation per combination. All actions, step traces and measured F are retained. Historical CSVs lack those fields; missing evidence cannot be filled by guessing or dividing by lambda.
- Cases: levels 2 and 4 selected after the full survey; **70 additional measured solves**, giving 7 level/lambda pairs × 4 configurations × 3 trials = 84 case rows (14 BFS/UCS trial-1 rows reused from survey).
- Historical reproduction: **46 additional untimed solves**, reusing 24 existing level/config solutions at lambda=0.25 to verify all 70 unique configurations. Matches all 350 historical structural rows. These are reconstructed solutions, not recovered historical action sequences.
- Total new stored direct solutions: **256**. All are replayed again from JSONL. Three further cross-replays demonstrate equal-cost alternatives without claiming new solver timings.

Do not compare or aggregate Windows timing with macOS timing. Search-phase/precompute-phase traced peaks are separate; neither is combined memory or whole-process RAM. Main median aggregation gives equal weight to levels. Survey timing is descriptive only.

## Git and preservation

Branch: `experiment/cost-analysis`, based on `7cf7463`, integrating `origin/main=c4cc318` with `git merge --no-commit --no-ff`. Conflict in `tests/test_foundation.py` resolved by explicitly selecting unit cost in that test. No unresolved index entries. No commit or push was created. This is an intentionally uncommitted merge; inspect `git status` before doing other Git work.

`metadata/preservation/preintegration_evidence.zip` preserves 35 original files, including the old lambda=3 evidence and untracked audit. Hashes and original Git status are in `metadata/preservation/manifest.json`. Readable copies of the old script and CSV are in `metadata/preservation/legacy/`; the old script relies on the old constructor default, so treat it as historical source, not the new experiment entry point.

`metadata/integrated_source.zip` contains exact source, campaign levels, tests, fixtures, requirements and analysis scripts. It makes this package reproducible independently of an uncommitted merge. Raw/LF source hashes and environment package versions are recorded separately. CRLF/LF normalization applies only to source equivalence checks, never to measured data values.

## Rebuild without running a solver

From repository root, in PowerShell, using the recorded environment:

```powershell
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/audit_history.py
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/build_analysis.py
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/diagnose_deadlines.py
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/finalize.py
```

`build_analysis.py` replays stored paths and rebuilds derived CSV/PNG/Markdown; it does **not** call solvers. Replays run outside all measurements. Rebuilding changes derived outputs only; historical raw files are byte-preserved. `finalize.py` refuses a changed source snapshot: use a new versioned output if source changes.

## Reproduce new solves

```powershell
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/run_supplement.py --stage survey
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/run_supplement.py --stage cases
.\.venv\Scripts\python.exe -B benchmarks/report_analysis/scripts/run_supplement.py --stage verify
```

Completed keys in append-only raw JSONL are skipped. To obtain a genuinely fresh cohort, copy the source/package to a new workspace/output tree and keep existing raw data independently; do not delete the current evidence. Preserve the recorded OS/Python/dependency versions and production hashes; do not resume after changing the environment. The resume guard checks production source and OS/Python; package versions are recorded for manual environment matching. Default limits: 60 seconds / 1,000,000 expanded nodes; seed 20261030; sequential jobs; fresh Problem/cache every solve.

Unit tests (may take about two minutes on this machine):

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Saved execution: `metadata/unit_tests.json` and `unit_tests.txt` — 208 PASS, 0 FAIL/ERROR/SKIP. This is separate from the deliberately inconsistent deadline diagnostic, which is documented rather than presented as a passed uniform-policy test.

## Main artifacts

- `main_comparison/raw/upstream_weighted/`: exact historical input.
- `main_comparison/summary/{per_level,overall,optimality,direct_verification}.csv`.
- `main_comparison/charts/`: time, separate memory phases, expanded/generated, actions, cost (all seven configurations).
- `cost_sensitivity/raw/{survey,cases_additional}.jsonl`: full actions and replay traces; survey CSV also supplied.
- `cost_sensitivity/summary/`: all 140 points, level changes, observed transition brackets, cases and cost checks.
- `cost_sensitivity/case_studies/`: case figures, selection rule and directly cross-replayed equal-cost paths.
- `heuristic_comparison/summary/`: per-level, overall, group comparison and metric-specific winners.
- `metadata/`: provenance, hashes, validations, source snapshot, deadline diagnostic and manifests.
- `report_notes/section4_vi.md`: report draft; `main_per_level_tables.md`: full per-algorithm numerical tables.

All 16 generated figures derive from their registered CSV/JSONL inputs. `metadata/chart_manifest.json` records hashes of the figures, inputs and plotting script. `metadata/file_manifest.json` registers the delivery files. Selected figures are visually checked; captions distinguish cohort, units, phase and sampled-point interpolation.

## Limits that must accompany report claims

Historical metadata lacks detailed CPU/dependency freeze and original actions. Timing uses tracemalloc and contains noise. Heuristic precompute is outside solver timeout and search node counts. The fake-clock diagnostic finds BFS/UCS `solved` versus DFS/A* `timeout` at a deadline-crossing goal transition. None of the campaign runs used here hits a failure limit. Level 4 at lambda=1.5 has a third path (24 actions, 3 penalties, cost 28.5), so the old two-line intersection is not an established optimal threshold. Do not change core algorithms to remove an inconvenient outcome.
