from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import evaluate, summarize
from .models import Trace
from .server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="AI evaluation and observability lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve_parser = subparsers.add_parser("serve", help="Run the local dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--database", default="signalforge.db")
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a JSON or JSONL file")
    eval_parser.add_argument("file", type=Path)
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.host, args.port, args.database)
        return
    raw = args.file.read_text()
    data = json.loads(raw) if args.file.suffix == ".json" else [json.loads(line) for line in raw.splitlines() if line]
    results = [evaluate(Trace.from_dict(item)) for item in (data if isinstance(data, list) else [data])]
    print(json.dumps({"summary": summarize(results), "results": [result.to_dict() for result in results]}, indent=2))


if __name__ == "__main__":
    main()
