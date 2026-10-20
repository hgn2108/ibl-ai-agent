"""Private scientific benchmark runner."""
import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from tests.evals.actors import build_actor

FIELDS = [
    "timestamp", "question_id", "category", "model", "status",
    "stop_reason", "duration_seconds", "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_tokens", "cost_usd",
    "num_turns", "scientific_score", "error_type",
]


def load_questions(path):
    questions = json.loads(Path(path).read_text())
    if not isinstance(questions, list):
        raise ValueError("Questions must be a JSON list")
    seen = set()
    for question in questions:
        if not isinstance(question, dict) or not all(
            isinstance(question.get(key), str) and question[key].strip()
            for key in ("id", "question")
        ):
            raise ValueError("Each question needs a nonempty id and question")
        if question["id"] in seen:
            raise ValueError(f"Duplicate question ID: {question['id']}")
        seen.add(question["id"])
    return questions


def run_question(actor, question):
    start = time.perf_counter()
    row = dict.fromkeys(FIELDS, "")
    row.update({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question_id": question["id"],
        "category": question.get("category", ""),
        "model": getattr(actor, "name", type(actor).__name__),
        "status": "error",
    })
    try:
        result = actor.run(question["question"])
        usage = result.usage
        row.update({
            "stop_reason": usage.stop_reason,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": usage.cache_read_tokens,
            "cache_write_tokens": usage.cache_write_tokens,
            "cost_usd": usage.cost_usd if usage.cost_usd else "",
            "num_turns": usage.num_turns,
            "status": (
                "completed"
                if usage.stop_reason == "answered" and result.reply.strip()
                else "incomplete"
            ),
        })
    except Exception as exc:
        row["error_type"] = type(exc).__name__
        row["stop_reason"] = type(exc).__name__
    finally:
        row["duration_seconds"] = round(time.perf_counter() - start, 3)
    return row


def append_result(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    questions = load_questions(args.questions)
    if args.ids:
        unknown = set(args.ids) - {q["id"] for q in questions}
        if unknown:
            parser.error(f"Unknown question IDs: {sorted(unknown)}")
        questions = [q for q in questions if q["id"] in args.ids]

    config = json.loads(args.model_config.read_text())
    if not isinstance(config, dict) or not all(
        config.get(key) for key in ("provider", "model")
    ):
        parser.error("Model configuration requires provider and model")

    print(f"Validated {len(questions)} questions; model: {config['model']}")

    if not args.execute:
        print("Dry run: no model calls or results written")
        return 0

    actor = build_actor(config, cwd=Path(__file__).resolve().parents[2])
    failures = 0
    for question in questions:
        row = run_question(actor, question)
        append_result(args.output, row)
        print(question["id"], row["status"], row["duration_seconds"])
        failures += row["status"] != "completed"
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
