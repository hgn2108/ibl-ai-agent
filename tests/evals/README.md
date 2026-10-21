# Evals

Questions that test whether a model can use this repo's guidance to load and query the
IBL datasets. They run as [Inspect](https://inspect.aisi.org.uk) tasks, against any
model Inspect supports, with model-written code executed in a Docker sandbox. Every
night CI runs them against one model per provider.

## Layout

| Path | Role |
|---|---|
| `questions/*.json` | Questions with their `expected` answer |
| `questions.py` | Loads questions and builds prompts (stdlib only) |
| `checks.py` | Grading: the reply's final JSON object must equal `expected` |
| `skill_router.py` | Maps the Required Load Packets of AGENTS.md to skill files |
| `tasks.py` | The Inspect tasks: `dataloading`, `skill_selection` |
| `sandbox/` | Dockerfile, compose file and dataset paths for the code sandbox |
| `models.json` | The default list of models, as Inspect ids |
| `run.py` | Runs the tasks on those models; shared by CI and ad hoc runs |
| `summarize.py` | Model x question table from a directory of logs |

## Running

Unit tests need no keys, data, Docker or network (those that need `inspect-ai` skip
without the `evals` extra):

```bash
uv sync --extra dev --extra evals
uv run pytest tests/evals
```

Evals call model APIs and need Docker plus `bwm_ephys` (`scripts/download_datasets.py`).
Copy `tests/evals/.env.template` to `.env` at the repo root and fill in the keys, then:

```bash
uv run python -m tests.evals.run                    # every task on the models of models.json
uv run python -m tests.evals.run --models anthropic/claude-haiku-4-5 --task skill_selection
uv run python tests/evals/summarize.py tests/evals/logs
uv run inspect view   # browse transcripts, tool calls and token usage
```

The models come from `models.json`, a JSON list of Inspect ids; `--models` (comma-separated)
or `--models-file` override it, and any model Inspect knows works. `run.py` exits 1 when a
run breaks, not when answers are wrong. `inspect eval tests/evals/tasks.py --model <id>`
also works for a single run. `EVAL_DATA_DIR` points the sandbox at datasets outside
`reports/datasets`.

### Lightning AI and other OpenAI-compatible providers

Inspect reaches any OpenAI-compatible endpoint as `openai-api/<provider>/<model>`,
reading `<PROVIDER>_API_KEY` and `<PROVIDER>_BASE_URL` (hyphens become underscores).
For Lightning AI set `LIGHTNING_API_KEY` and `LIGHTNING_BASE_URL=https://lightning.ai/api/v1/`
in `.env`, then:

```bash
uv run python -m tests.evals.run --models openai-api/lightning/openai/gpt-5-mini
```

Not yet verified against Lightning. Provider quirks are set per run, not in code:
`-M strict_tools=false` if the endpoint rejects strict tool schemas, `--max-tokens` if a
model wants `max_completion_tokens`. A model that returns empty or malformed tool calls
shows up as a failed sample: read its transcript in `inspect view`. For the nightly CI add
the model to `models.json` or pass it in the workflow's `models` input; the
`LIGHTNING_API_KEY` secret is optional.

## The sandbox

Model-written code runs in a container (`sandbox/compose.yaml`) with no network, a
read-only repo, the datasets mounted read-only at `/data` and `IBL_AGENT_DATA_OFFLINE=1`.
Nothing a model writes touches your machine. Add packages the analyses need to
`sandbox/Dockerfile`.

## Writing a question

Each entry in `questions/*.json` has an `id`, the `question`, a `task`, the `packets`
of AGENTS.md whose skill files go in the prompt, `requires_data`, and `expected`: a flat
`{key: number}` dict. The prompt tells the model to end with a JSON object with those
keys, and the scorer compares it to `expected`, so a new question is data only.
Skill-selection questions use `expected_skills` instead. Prefer answers a plausible
mistake gets wrong: `bwm_visual_hemisphere.json` documents its traps in `_notes`.

## Reading results

Inspect logs hold every message, tool call and token count per sample. A model that
stops without a JSON answer scores as a failure, as does a wrong value: look at the
transcript to tell them apart.
