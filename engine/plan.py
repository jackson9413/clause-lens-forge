"""Negotiation plan and counter-proposal drafting for Clause Lens."""

SEVERITY_WEIGHT = {"critical": 3.0, "high": 2.4, "medium": 1.4, "low": 0.7, "positive": 0.0}

LEVERAGE_NOTE = {
    5: "Standard ask. Very likely to be accepted.",
    4: "Common ask. Usually conceded if you give a reason.",
    3: "Reasonable but contested. Pair it with a trade.",
    2: "Hard sell. Ask anyway if the issue matters to you.",
    1: "Unlikely to move. Raise it once, then decide.",
}


def priority_score(finding):
    return round(SEVERITY_WEIGHT.get(finding["severity"], 1.0)
                 * finding.get("impact", 3)
                 * finding.get("leverage", 3), 1)


def negotiation_plan(ctx, findings, limit=8):
    """Rank the actionable findings into an order worth negotiating in."""
    actionable = [f for f in findings if f["severity"] != "positive"]
    for f in actionable:
        f["priority_score"] = priority_score(f)
    actionable.sort(key=lambda f: (-f["priority_score"], f["title"]))

    plan = []
    for i, f in enumerate(actionable[:limit], 1):
        plan.append({
            "rank": i,
            "finding_id": f["id"],
            "title": f["title"],
            "severity": f["severity"],
            "axis": f["axis"],
            "ask": f.get("fix", ""),
            "fallback": f.get("fallback", ""),
            "why": f.get("why", ""),
            "leverage": f.get("leverage", 3),
            "impact": f.get("impact", 3),
            "priority_score": f["priority_score"],
            "leverage_note": LEVERAGE_NOTE.get(f.get("leverage", 3), ""),
            "evidence": f.get("evidence", ""),
        })
    return plan


def counter_proposal(ctx, findings, plan, top=5):
    """Draft the email that asks for the changes."""
    picks = plan[:top]
    positives = [f for f in findings if f["severity"] == "positive"]

    lines = [
        "Subject: Comments on the agreement",
        "",
        "Hi,",
        "",
        "Thanks for sending this over. I have read it through and I am happy to sign, "
        "with a few changes. They are listed below with the wording I have in mind, so "
        "we can get this done quickly.",
        "",
    ]

    if picks:
        for i, item in enumerate(picks, 1):
            lines.append("{0}. {1}".format(i, item["title"]))
            if item.get("ask"):
                lines.append("   Please use: \"{0}\"".format(item["ask"]))
            if item.get("fallback"):
                lines.append("   If that is awkward, I can live with: {0}".format(item["fallback"]))
            lines.append("")

    if positives:
        lines.append("Everything else looks good to me, including {0}.".format(
            ", ".join(p["title"].lower() for p in positives[:2])))
        lines.append("")

    lines.append("If you have any questions on any of the above, give me a call and we can "
                 "sort it out quickly. I will send the signed copy as soon as we are aligned.")
    lines.append("")
    lines.append("Thanks,")
    return "\n".join(lines)
