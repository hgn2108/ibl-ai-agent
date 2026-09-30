---
name: data-ingest
description: Use this skill when ingesting a raw dataset into a standardised dataset package, converting documented source data into the layout a later agent can analyse without re-reading the source. Ingestion only, not analysis of an existing package.
---

# Data Ingest

**Status: v0, not yet run on a real package.** The first run is the aging/autism
pilot. Revise this file from that package's `ingestion/ingestion-log.md` and
`ingestion/open-questions.md`, and from discussion with the user about what went
wrong.

## The idea
Ingestion happens once. Its output is a directory from which any later agent
instance can start analysing straight away, without re-reading the raw source or
repeating ingestion. This skill describes **that end point**. How to get there
from a given lab's files, whether NWB, DANDI or an in-house format, is for you
to work out.

**You lead.** Users will not know what you need, and their data will always be
missing something that shows up only when you try to convert it. Ask for what you
need, and whenever you get stuck, go back to the user with a specific question.
Never fill a gap by guessing.

Do not load this skill to analyse an existing package. Analysis reads the
package's own prose files plus `skills/ibl-analyze/` where it applies.

## The end point
One dataset at one version, in `<dataset_root>/<dataset_name>/<version>/`,
registered under `datasets:` in `data_locations.local.yaml`. The exact tree,
headings and YAML shapes are defined in `project-structure.md`. Read it before
writing anything, and do not restate it or diverge from it.

What each part must let the next agent do:

- **`README.md`**: decide from one paragraph whether it needs this dataset at
  all. Species, subject and session counts, modalities, scientific aim, key
  paper. The other files are read only if the answer is yes.
- **`experiment.md`**: understand what was done, as in a paper's methods
  section. It describes the experiment, not an interpretation of it.
- **`modalities.md`**: know, for each recording modality, what it is and how to
  trust it.
- **`scientific-context.md`**: know what the study was for and, above all, what
  could mislead an analysis of it. Required for every package; see below.
- **`schema.yaml` + `metadata/*.parquet` + stores**: load any table or signal
  with its units and clock known, with no need to guess.
- **`ingestion/`**: rebuild the package (`convert.py`), see what was asked and
  inferred (`ingestion-log.md`), and see what is still unresolved
  (`open-questions.md`).

### What the next agent needs to know, by what the experiment contains
Use this as a checklist of information the package must contain. Ask the user for
anything the documentation does not state.

- **Every dataset**: the paper, preprint, thesis chapter or methods text; what
  each source file contains; the units and clock of every quantity; how clocks
  are synchronised across devices; subject metadata (line, genotype, sex, date of
  birth, cohort); the experimental design (factors, grain, intended comparison);
  how many labs and rigs recorded the data; whether subjects fall into groups
  that are compared; the period the sessions span.
- **Trials**: whether the experiment is trial-based at all (free exploration is
  not); what defines a trial's start and end; stimulus, response and outcome;
  which task and protocol were run; whether there are blocks or priors.
- **If the user confirms the IBL task** (`ibl_choice_world`): whether the
  protocol uses biased blocks. Analysis will use `skills/ibl-analyze/`, whose
  guidance comes from BWM, so the design caveats below matter most here.
- **Spikes / units**: sorter and version; which units were kept and why (the
  source-selection rule); what QC exists.
- **Two-photon / calcium**: indicator; frame rate; whether traces are raw,
  ΔF/F or deconvolved, and with what; ROI selection. A deconvolved trace is a
  timeseries, not spike times.
- **Video / pose**: camera frame times and clock; which tracking was run.
- **LFP and other bulk signals**: whether they are converted or referenced in
  place. If referenced, record what re-resolves them, never only a local path.

### Writing `scientific-context.md`
Users often won't know the confounds or caveats of their own data, so don't ask
for them. Derive them from design facts the user can answer, which the checklist
above already collects. The file has two kinds of content:

- **Caveats from the design (required).** Write the consequence for every fact
  that applies:

  | Fact | Caveat to write |
  | --- | --- |
  | Subjects compared in groups (age, genotype, line) | N is the number of subjects. Recording quality (yield, stability, drift, engagement) may differ by group, so compare it before claiming a neural difference. |
  | One lab or a few | Lab is not a meaningful source of variation. |
  | Sessions span learning or a long period | Neural and behavioural drift across sessions; don't pool naively. |
  | Groups recorded in different regions or depths | Region differences can look like group differences. |
  | Calcium traces deconvolved | They are rate estimates, not spikes. |
  | Not trial-based | Trial-aligned guidance does not apply. |
  | IBL task without biased blocks | `probabilityLeft` and `prior_and_block_semantics.md` do not apply. |
  | Analysis will use `skills/ibl-analyze/` | Its QC and reproducibility guidance is BWM evidence (12 labs, one group of mice), not a general law. |

  Add a row to this table when the pilot turns up a new one.
- **What the user knows (optional).** The aim and hypotheses, the associated
  papers, and any confounds the table can't see (a rig change midway, a cohort
  with surgery problems). Ask once. "Not stated" and "none known" are valid
  answers. Never fill them in yourself.

## Hard rules
These hold whatever route you take.

1. **Never invent a unit, a time base or any other blocking fact.** Stop and ask.
   The minimum a package cannot ship without is listed in `project-structure.md`
   ("Minimum viable package").
2. **Measure before converting in bulk** (the repo's "Start small" policy): take
   the raw size per session, convert 2–3 sessions, estimate the full run, and get
   the user's approval before starting it.
3. **Use the repo's tools; don't rewrite them.** Spikes go through
   `spikepack.write_blosc` only; see `references/spike-shards.md` (read it
   before anything else if there are spikes to convert). IBL-task trials go
   through the existing extraction, but only when the task is
   `ibl_choice_world`; see `references/ibl-trials.md`. If a helper you need does
   not exist yet, check `references/pending-interfaces.md`.

   **Pilot exception (remove after the aging/autism pilot).** Most of those
   helpers don't exist yet. During the pilot, when one is missing, tell the user
   and then write a minimal stand-in inside `ingestion/convert.py`. Mark it with a
   `# PILOT STAND-IN for <helper>` comment and list each one in
   `ingestion/ingestion-log.md` with what it had to do. This is so the pilot shows
   what the real helpers need. The stand-ins are not the final route. Outside the
   pilot, stop and say so instead.
4. **Leave BWM untouched**: its data, schemas, builder output and analysis
   guidance.
5. **Never overwrite or delete an existing package version** without asking.
   A fix is a new version (semver, see `project-structure.md`). How local
   versions are managed is still open.
6. **Log everything.** Every question and its answer, everything inferred and
   everything skipped goes in `ingestion/ingestion-log.md`. Anything unresolved
   also goes in `ingestion/open-questions.md`.

## Suggested route
1. Read the source and its documentation. Draft `README.md`, `experiment.md`
   and `modalities.md` from what the documentation states.
2. Work through the checklist above and ask the user about the gaps.
3. Measure, convert 2–3 sessions, estimate, get approval.
4. Write `schema.yaml`, the metadata tables and the stores. Reference in place
   whatever is not converted.
5. Write `provenance.yaml`, `manifest.json`, `SUMMARY.md` and the `ingestion/`
   files. Register the package.
6. Check the result as a fresh agent would (see the quality gates below).

## Quality gates
- Reading only `README.md`, a fresh agent can judge whether the dataset is
  relevant.
- Reading the package alone, a fresh agent can load data and start an analysis
  without the raw source and without re-ingesting.
- No blocking gap was closed by inference. Every question and answer is in
  `ingestion/ingestion-log.md`.
- `scientific-context.md` has a caveat for every design fact that applies.
- Every table and store names a declared `time_base`, and every column has a
  `units` key.
- The full run was estimated from 2–3 sessions and approved before it started.
- `ingestion/convert.py` reproduces the build and calls the repo's tools rather
  than restating them.
