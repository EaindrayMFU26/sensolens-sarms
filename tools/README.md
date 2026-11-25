# tools/ — scripts that drive sarms

Run every script from the repository root: `uv run python tools/<script>.py …`. The scripts import `sarms`
like any user would, and the package never imports them. They stay in one flat folder on purpose: the frozen
protocol (`docs/repo-selection.md`) and the reports cite them by path. Every script's docstring has its full
usage, and `docs/runbook-commands.md` has the commands in the order they are run.

## Step 1a: choosing the subject repositories (`docs/repo-selection.md`)

| Script | What it does | Writes |
| --- | --- | --- |
| `reduce_longlist.py` | Reduces the team's long list with rules R1–R4, with one recorded reason per dropped row. | `data/longlist_decisions.csv`, `data/longlist.txt` |
| `rawscan.py` | Fast first pass: import-linter contracts at the repository root, read from raw.githubusercontent.com (no clone). | `data/rawscan.json` |
| `adrscan.py` | Fast first pass: ADRs in the common folders (no clone). | stdout |
| `screen.py` | Full screening on the eight criteria, using a partial clone of each repository. | `data/candidates.csv`, clones in `data/raw/` |
| `check_tests.sh` | Criterion 3: times one documented test run at HEAD in a fresh virtual environment. | `data/tests.csv`, `reports/tests/` |

## Steps 1b–1c: history, record and baseline

| Script | What it does | Writes |
| --- | --- | --- |
| `run_step1.py` | Runs `first_parent` → `record_history` → `proxy_lint` → `baseline.report` for one repository, with timings. | `data/<repo>/…`, `reports/awareness-gap-baseline*` |
| `draw_sample.py` | Draws the seeded labelling samples the evaluation protocol fixes. | `data/samples/precision_100.csv`, `rootcause_50.csv`, `docs/spec/pilot-sheet.csv` |

## Evaluation harnesses: measuring the system

| Script | What it does | Writes |
| --- | --- | --- |
| `check_against_replay.py` | The Differ's correctness test: compiler + Differ + ledger must reproduce the Step 1c replay. | `data/<repo>/rms/`, PASS/FAIL |
| `fault_injection.py` | Plants rule-breaking pushes, one branch each (setup half of `docs/spec/fault-injection.md`). | `data/<repo>/rms/fi/plants.json` |
| `eval_drafts.py` | Detects every plant and drafts a fix with each model (measurement half). | `data/<repo>/rms/fi/results-<run>.md` |
| `eval_learned_rules.py` | Hidden-contract benchmark: can the learner rediscover the team's written rules? | `data/<repo>/rms/learn/eval.json`, `reports/learned-rules.md` |
| `benchmark_batch.py` | Runs `eval_learned_rules.py` over many repositories, verifying their contracts first. | `reports/learned-rules-batch.csv` |
| `product_batch.py` | Runs the product loop (dry run, template drafter) over many repositories. | `reports/product-batch.csv` |

## Studies: research questions answered from data on disk

| Script | What it does | Writes |
| --- | --- | --- |
| `rule_viability.py` | Are the learned rules viable as rules, judged on their own merits? | `reports/rule-viability.md`, `data/samples/rule_review.csv` |
| `axiom_study.py` | Is the six-axiom specification (A1–A6) enough? Run over every benchmark repository. | `reports/axiom-study.md` |
| `behavioural_evidence.py` | Do hotspots, change coupling and authorship help the learner find better rules? | `reports/behavioural-evidence.md` |
| `hotspots.py` | CodeScene-style hotspots, change coupling and erosion pressure per component. | `data/<repo>/rms/hotspots/` |
| `track_c.py` | Track C end to end: learn on the first 70 % of the history, replay the last 30 % with belief functions. | `data/<repo>/rms/track-c/`, `reports/track-c.md` |

## Presenting results

| Script | What it does | Writes |
| --- | --- | --- |
| `demo.py` | Shows what Steps 1–2 produced for one repository, in plain words. Read-only. | stdout |
| `render_graph.py` | Draws the package import graph that `sarms.graph.extract` wrote (needs Graphviz). | `reports/figures/` |

## The specification

| Script | What it does | Writes |
| --- | --- | --- |
| `validate_spec.py` | Checks `docs/spec` (labels, gate lines, schemas, ledger DDL) and prints the protocol hash. | stdout |
| `make_pack.py` | Fills the P1 pack with the frozen files' hashes and the check results. | `reports/p1-pack.md` |
