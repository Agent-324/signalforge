from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluator import evaluate, summarize
from .models import Trace
from .regression import compare
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
    compare_parser = subparsers.add_parser("compare", help="Detect regressions between two trace files")
    compare_parser.add_argument("baseline", type=Path)
    compare_parser.add_argument("candidate", type=Path)
    compare_parser.add_argument("--threshold", type=float, default=0.1)
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.host, args.port, args.database)
        return
    if args.command == "compare":
        def load(path: Path) -> list[Trace]:
            raw = path.read_text()
            data = json.loads(raw) if path.suffix == ".json" else [json.loads(line) for line in raw.splitlines() if line]
            return [Trace.from_dict(item) for item in (data if isinstance(data, list) else [data])]

        result = compare(load(args.baseline), load(args.candidate), args.threshold)
        print(json.dumps(result, indent=2))
        if not result["pass"]:
            sys.exit(1)
        return
    raw = args.file.read_text()
    data = json.loads(raw) if args.file.suffix == ".json" else [json.loads(line) for line in raw.splitlines() if line]
    results = [evaluate(Trace.from_dict(item)) for item in (data if isinstance(data, list) else [data])]
    print(json.dumps({"summary": summarize(results), "results": [result.to_dict() for result in results]}, indent=2))


if __name__ == "__main__":
    main()
