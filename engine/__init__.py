"""Clause Lens - a local-first contract clause reviewer.

Standard library analysis engine. No network calls, no LLM, no API keys.
Everything happens on this machine.
"""

from .clauses import CLAUSE_SPECS, detect_clauses, text_stats
from .rules import PERSPECTIVES, build_context, missing_clauses, run_probes
from .scoring import AXES, VERDICTS, score_review, verdict_for
from .deadlines import extract_deadlines, parse_date, to_ics
from .plan import counter_proposal, negotiation_plan

__all__ = [
    "CLAUSE_SPECS",
    "CONTRACT_TYPES",
    "PERSPECTIVES",
    "review",
    "to_markdown",
    "detect_clauses",
    "text_stats",
]

FENCE = chr(96) * 3

CONTRACT_TYPES = [
    {"key": "msa", "label": "Master services / vendor agreement"},
    {"key": "sow", "label": "Statement of work"},
    {"key": "nda", "label": "Non-disclosure agreement"},
    {"key": "freelance", "label": "Freelance / creator agreement"},
    {"key": "employment", "label": "Employment agreement"},
    {"key": "saas", "label": "SaaS subscription"},
    {"key": "lease", "label": "Lease"},
    {"key": "generic", "label": "Something else"},
]


def review(text, contract_type="generic", perspective="party", title="Untitled agreement"):
    """Run the full review and return a plain dict."""
    text = text or ""
    contract_type = contract_type if contract_type else "generic"
    perspective = perspective if perspective in PERSPECTIVES else "party"

    stats = text_stats(text)
    ctx = build_context(text, contract_type, perspective)
    clauses = detect_clauses(text, contract_type)
    ctx.clauses = {c.key: c for c in clauses}

    findings = run_probes(ctx)
    missing = missing_clauses(ctx)
    score = score_review(ctx, findings, missing)
    dl = extract_deadlines(ctx)
    nplan = negotiation_plan(ctx, findings)
    proposal = counter_proposal(ctx, findings, nplan)

    return {
        "meta": {
            "title": title,
            "contract_type": contract_type,
            "perspective": perspective,
            "perspective_meaning": PERSPECTIVES[perspective],
            "stats": stats,
            "clauses_found": sum(1 for c in clauses if c.present),
            "clauses_total": len(clauses),
        },
        "score": score,
        "findings": findings,
        "clauses": [c.to_dict() for c in clauses],
        "missing": missing,
        "deadlines": dl,
        "negotiation_plan": nplan,
        "counter_proposal": proposal,
    }


def to_markdown(result):
    """Render a review as a markdown report."""
    meta = result["meta"]
    score = result["score"]
    lines = []
    lines.append("# Contract review: {0}".format(meta.get("title") or "Untitled agreement"))
    lines.append("")
    lines.append("- **Contract type:** {0}".format(meta["contract_type"]))
    lines.append("- **Reading as:** {0}".format(meta["perspective"]))
    lines.append("- **Length:** {0} words, {1} clauses detected".format(
        meta["stats"]["words"], meta["clauses_found"]))
    lines.append("")
    lines.append("## Score: {0} / 100 - {1}".format(score["overall"], score["verdict_label"]))
    lines.append("")
    lines.append(score["verdict_advice"])
    lines.append("")
    lines.append("| Axis | Score | Findings |")
    lines.append("| --- | --- | --- |")
    for a in score["axes"]:
        lines.append("| {0} | {1} | {2} |".format(a["label"], a["score"], a["findings"]))
    lines.append("")

    if score["caps"]:
        lines.append("### Structural caps")
        lines.append("")
        for c in score["caps"]:
            lines.append("- {0}".format(c["reason"]))
        lines.append("")

    lines.append("## Findings")
    lines.append("")
    if not result["findings"]:
        lines.append("No issues found.")
    for f in result["findings"]:
        lines.append("### [{0}] {1} ({2})".format(f["id"], f["title"], f["severity"]))
        lines.append("")
        if f.get("evidence"):
            lines.append("> {0}".format(f["evidence"]))
            lines.append("")
        lines.append("**Why it matters:** {0}".format(f["why"]))
        lines.append("")
        lines.append("**Fix:** {0}".format(f["fix"]))
        if f.get("fallback"):
            lines.append("")
            lines.append("**Fallback:** {0}".format(f["fallback"]))
        lines.append("")

    if result["missing"]:
        lines.append("## Missing clauses")
        lines.append("")
        for m in result["missing"]:
            lines.append("### {0}".format(m["label"]))
            lines.append("")
            lines.append("{0}".format(m["why"]))
            lines.append("")
            lines.append("Suggested: \"{0}\"".format(m["suggested"]))
            lines.append("")

    if result["deadlines"]:
        lines.append("## Dates to diarise")
        lines.append("")
        for d in result["deadlines"]:
            lines.append("- **{0}** ({1}) - {2}".format(d["label"], d["date"], d.get("note", "")))
        lines.append("")

    lines.append("## Negotiation order")
    lines.append("")
    for item in result["negotiation_plan"]:
        lines.append("{0}. **{1}** ({2}) - {3}".format(
            item["rank"], item["title"], item["severity"], item["ask"]))
        if item.get("fallback"):
            lines.append("   Fallback: {0}".format(item["fallback"]))
    lines.append("")

    lines.append("## Draft reply")
    lines.append("")
    lines.append(FENCE)
    lines.append(result["counter_proposal"])
    lines.append(FENCE)
    return "\n".join(lines)
