#!/usr/bin/env python3
"""Command line entry point for Clause Lens.

    python3 cli.py contract.txt --type msa --perspective client
    python3 cli.py contract.txt --markdown report.md
    python3 cli.py --sample vendor-msa-one-sided
"""

import argparse
import json
import sys

import engine
from engine.samples import SAMPLES, by_id


def build_parser():
    p = argparse.ArgumentParser(
        prog="clause-lens",
        description="Review a contract for the clauses that decide what happens when it goes wrong.")
    p.add_argument("path", nargs="?", help="path to the contract text file")
    p.add_argument("--type", dest="contract_type", default="generic",
                   choices=[t["key"] for t in engine.CONTRACT_TYPES],
                   help="type of contract")
    p.add_argument("--perspective", default="party",
                   choices=sorted(engine.PERSPECTIVES),
                   help="which side you are reading it from")
    p.add_argument("--title", default=None, help="name for this contract")
    p.add_argument("--sample", default=None,
                   help="review a built-in sample instead of a file")
    p.add_argument("--markdown", default=None, help="write a markdown report to this path")
    p.add_argument("--json", default=None, help="write the full result as JSON to this path")
    p.add_argument("--calendar", default=None, help="write the deadlines as an .ics file")
    p.add_argument("--quiet", action="store_true", help="only print the score")
    return p


def read_contract(args):
    if args.sample:
        s = by_id(args.sample)
        if not s:
            print("clause-lens: unknown sample '{0}'".format(args.sample), file=sys.stderr)
            print("available: {0}".format(", ".join(x["id"] for x in SAMPLES)), file=sys.stderr)
            return None, None, None
        return s["text"], s["contract_type"], s["name"]
    if not args.path:
        print("clause-lens: give a file path or --sample", file=sys.stderr)
        return None, None, None
    try:
        with open(args.path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        print("clause-lens: {0}".format(exc), file=sys.stderr)
        return None, None, None
    title = args.title or args.path
    return text, args.contract_type, title


def main(argv=None):
    args = build_parser().parse_args(argv)
    text, contract_type, title = read_contract(args)
    if text is None:
        return 2
    if not text.strip():
        print("clause-lens: that file is empty", file=sys.stderr)
        return 2

    result = engine.review(text, contract_type, args.perspective, title)
    score = result["score"]

    if args.quiet:
        print("{0} {1}".format(score["overall"], score["verdict"]))
    else:
        print("Clause Lens - {0}".format(title))
        print("Type: {0} | Reading as: {1} | {2} words".format(
            contract_type, args.perspective, result["meta"]["stats"]["words"]))
        print("")
        print("SCORE {0}/100 - {1}".format(score["overall"], score["verdict_label"]))
        print(score["verdict_advice"])
        print("")
        for axis in score["axes"]:
            print("  {0:<26} {1:>5}   {2}".format(
                axis["label"], axis["score"], axis["about"]))
        if score["caps"]:
            print("")
            print("  Held down by:")
            for cap in score["caps"]:
                print("    - {0}".format(cap["reason"]))
        print("")
        print("  Findings: {0} critical, {1} high, {2} medium, {3} low, {4} positive".format(
            score["counts"]["critical"], score["counts"]["high"], score["counts"]["medium"],
            score["counts"]["low"], score["counts"]["positive"]))
        print("")
        for f in result["findings"]:
            print("  [{0}] {1} ({2})".format(f["id"], f["title"], f["severity"]))
            if f.get("evidence"):
                print("      \"{0}\"".format(f["evidence"][:160]))
            print("      fix: {0}".format(f["fix"][:220]))
        if result["missing"]:
            print("")
            print("  Missing clauses: {0}".format(
                ", ".join(m["label"] for m in result["missing"])))
        if result["deadlines"]:
            print("")
            print("  Dates to diarise:")
            for d in result["deadlines"]:
                print("    {0}  {1}".format(d["date"], d["label"]))
        print("")
        print("  Negotiation order:")
        for item in result["negotiation_plan"]:
            print("    {0}. {1} - {2}".format(item["rank"], item["title"], item["ask"][:160]))

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as fh:
            fh.write(engine.to_markdown(result))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
    if args.calendar:
        with open(args.calendar, "w", encoding="utf-8") as fh:
            fh.write(engine.to_ics(result["deadlines"], title))

    return 0


if __name__ == "__main__":
    sys.exit(main())
