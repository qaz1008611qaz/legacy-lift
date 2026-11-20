"""CLI: python -m legacy_lift <repo> [--max-risk N] [--prompts]"""
import argparse

from .planner import plan
from .scanner import scan_repo
from .tasks import devin_prompt, markdown_plan


def main(argv=None):
    ap = argparse.ArgumentParser(prog="legacy_lift")
    ap.add_argument("repo", help="path to the Python 2 code base")
    ap.add_argument("--max-risk", type=int, default=20, help="risk budget per batch / PR")
    ap.add_argument("--prompts", action="store_true", help="also print Devin Bot task prompts")
    args = ap.parse_args(argv)
    reports = scan_repo(args.repo)
    batches = plan(reports, args.max_risk)
    print(markdown_plan(batches, reports))
    if args.prompts:
        for b in batches:
            print("-" * 60)
            print(devin_prompt(b, reports))


if __name__ == "__main__":
    main()
