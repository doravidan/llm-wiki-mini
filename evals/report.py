from __future__ import annotations
import json, sys
from pathlib import Path

def main(argv=None):
    argv = argv or sys.argv[1:]
    root = Path(argv[0] if argv else "eval_runs")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    print("# LLM Wiki Mini Eval Summary\n")
    print(f"Runs: {summary['runs']}")
    print("Winners:")
    for arm, count in summary["winners"].items():
        print(f"- {arm}: {count}")
    print("\nCases:")
    for case in summary["cases"]:
        print(f"- {case['case_id']}: winner={case['winner']} report={case['report']}")

if __name__ == "__main__":
    main()
