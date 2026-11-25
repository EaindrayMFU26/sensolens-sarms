# sarms — Self-Adaptive Repository Management System (Senso-Lens)

Keeps code faithful to its recorded architecture after each push. After a push lands, the
system compares the change with the architecture recorded in the repository's ADRs and
dependency rules, drafts a conforming version where the change deviates, verifies the draft
with tools (gate G0–G8), and applies it itself; only real architecture decisions reach a human.

1305394 Seminar in Software Engineering, Mae Fah Luang University, 1/2569 · advisor Dr. Nacha
Chondamrongkul · team: Danielle Jerick M. Jusayan, Eaindray, Kanthi Phoosorn, Withuwit Ninphan.

## The product in one line

`sarms mine` → `sarms certify-ledger` → `sarms run`: mining, the hypergraph ledger, architecture certificates, and the repair loop (draft, gate, kernel). See `docs/product.md`.

## Layout

```
src/sarms/             the package; docs/architecture.md maps every module and how they connect
  cli.py               `sarms <command>`: the command table
  product.py           the whole workflow: mine -> certify-ledger -> run, status, clean
  core/                foundations: data paths, git, import-linter records, the lint worker, pseudonyms
  mining/              history: first-parent chain (Step 1b), change stream, ADRs
  graph/               the import graph of one commit, written to files
  ledger/              the system's memory: hypergraph ledger (STHG), spec ledger (DuckDB), episodes
  rules/               the rule compiler, record history, the learner, viability, certificates (A1–A6)
  differ/              the Monitor: one commit or a whole history against the rules -> the four labels
  synthesize/          the only package that calls a model: drafted fixes, rule adoption
  verify/              gate G0–G8 -> a signed decision record
  kernel/              applies an accepted record as the system's own commit
  baseline/            research: the Step 1c proxy run and awareness-gap report
  trackc/              research: Track C (co-change, hypergraph network, belief functions)
tests/unit/            single modules, no git repository needed (about a minute)
tests/integration/     end to end on a tiny subject repository driven through real git
tools/                 scripts: selection, Step 1 pipeline, evaluation, studies, figures, spec (tools/README.md)
docs/                  product, runbook, build plan, research notes; docs/spec/ = the frozen specification
data/samples/          labelling samples and small example outputs (tracked)
data/raw/, data/*/rms/ clones and everything the product writes (git-ignored)
reports/               generated reports
```

`.importlinter` holds sarms's own contracts: the layering above (core at the bottom, research on
top), and the rule that the Differ, the gate and the kernel never import the model step.

## Setup

```bash
uv sync --all-groups            # --all-groups adds torch for Track C's encoder; plain `uv sync` is enough otherwise
uv run lint-imports             # sarms's own architecture: 2 contracts kept
uv run ruff check .
uv run pytest -q tests/unit     # fast
uv run pytest -q                # everything, about 3 minutes
uv run sarms --help             # or: python -m sarms --help
```

Mining author pseudonyms (`sarms.mining.first_parent`) needs the team's secret salt: put it in a
file named `.salt` in the repository root (git-ignored, never commit it) or set `RMS_SALT`.

The loop on kedro, end to end: `docs/runbook-commands.md`, section "Weeks 2–3".

Step-by-step commands: `docs/runbook-commands.md`. Every script in `tools/`: `tools/README.md`.
