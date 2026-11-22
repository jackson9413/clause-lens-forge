"""Scoring, structural caps and verdicts for Clause Lens."""

AXES = [
    {
        "key": "financial",
        "label": "Financial terms",
        "weight": 0.20,
        "about": "When money moves, how much, and what happens to the price later.",
    },
    {
        "key": "exit",
        "label": "Exit & flexibility",
        "weight": 0.20,
        "about": "How easily you leave, on what notice, and what the exit costs.",
    },
    {
        "key": "ip",
        "label": "IP & confidentiality",
        "weight": 0.20,
        "about": "Who owns the work, who may use it, and what stays secret.",
    },
    {
        "key": "risk",
        "label": "Risk allocation",
        "weight": 0.25,
        "about": "Who pays when it goes wrong: caps, indemnity, disputes.",
    },
    {
        "key": "completeness",
        "label": "Completeness & balance",
        "weight": 0.15,
        "about": "Whether the usual protections are present, and whether they are fair.",
    },
]

SEVERITY_PENALTY = {"critical": 30, "high": 16, "medium": 7, "low": 3, "positive": 0}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}
POSITIVE_BONUS = 3
MAX_POSITIVE_BONUS = 6
MISSING_PENALTY = 3
MAX_MISSING_PENALTY = 18

VERDICTS = [
    (85, "ready_to_sign", "Ready to sign",
     "No structural problems found. Sign it."),
    (70, "light_touch", "Sign with light edits",
     "Mostly balanced. Fix the top few items if the deal is worth negotiating."),
    (50, "negotiate", "Negotiate before signing",
     "The agreement is one-sided in places. Do not sign it as written."),
    (35, "high_risk", "High risk - escalate",
     "Several core protections are missing or point the wrong way. Get a human to look."),
    (0, "do_not_sign", "Do not sign as written",
     "Fundamental protections are absent. Walk away or get professional advice."),
]


def verdict_for(score):
    for threshold, key, label, advice in VERDICTS:
        if score >= threshold:
            return {"key": key, "label": label, "advice": advice}
    return {"key": "do_not_sign", "label": "Do not sign as written",
            "advice": VERDICTS[-1][3]}


def _cap_axes(ctx, findings, missing):
    """Return structural caps that limit how high a score may be.

    A cap is not a penalty: it says that a missing or dangerous structure keeps
    the score down no matter how clean the rest of the document is.
    """
    caps = []
    clauses = ctx.clauses

    def has(key):
        c = clauses.get(key)
        return bool(c and c.present)

    if not has("termination"):
        caps.append({
            "axis": "exit", "max": 30, "overall_max": 55,
            "reason": "No termination clause at all. Without an exit, every other risk is permanent.",
        })
    if has("term_renewal") and ctx.flags.get("auto_renew"):
        notice = ctx.flags.get("renewal_notice_days")
        if not notice or notice <= 14:
            caps.append({
                "axis": "exit", "max": 40, "overall_max": 62,
                "reason": "Auto-renewal with no usable notice window. You can be locked in without noticing.",
            })
        elif notice < 45:
            caps.append({
                "axis": "exit", "max": 55, "overall_max": 72,
                "reason": "Auto-renewal is in play and the notice window is tight. Diary the date.",
            })

    if not has("liability_cap"):
        caps.append({
            "axis": "risk", "max": 25, "overall_max": 50,
            "reason": "No limitation of liability. Exposure is uncapped.",
        })

    if ctx.flags.get("one_way_indemnity"):
        caps.append({
            "axis": "risk", "max": 35,
            "reason": "Indemnity runs one way only: you indemnify them, they do not indemnify you.",
        })

    if ctx.flags.get("ip_assignment_without_carveout"):
        caps.append({
            "axis": "ip", "max": 35, "overall_max": 58,
            "reason": "IP assignment with no carve-out for what you already owned.",
        })

    if ctx.contract_type == "nda" and not has("confidentiality"):
        caps.append({
            "axis": "ip", "max": 30, "overall_max": 50,
            "reason": "A non-disclosure agreement with no confidentiality obligation.",
        })

    if ctx.flags.get("perpetual_license"):
        caps.append({
            "axis": "ip", "max": 42,
            "reason": "A perpetual, irrevocable licence grant cannot practically be undone.",
        })

    if ctx.flags.get("net_days") and ctx.flags["net_days"] > 45:
        caps.append({
            "axis": "financial", "max": 45, "overall_max": 60,
            "reason": "Payment terms longer than 45 days push your cash behind their delivery.",
        })

    if not has("governing_law"):
        caps.append({
            "axis": "risk", "max": 45,
            "reason": "No governing law or venue. Disputes have no agreed forum.",
        })

    if has("termination") and not ctx.flags.get("termination_for_cause"):
        caps.append({
            "axis": "exit", "max": 45,
            "reason": "Termination exists but not for cause. You may have to walk away mid-term.",
        })

    return caps


def score_review(ctx, findings, missing):
    """Build the 0-100 scorecard with structural caps applied."""
    per_axis = {a["key"]: {"base": 100.0, "penalties": [], "positives": 0, "missing": 0}
                for a in AXES}

    for f in findings:
        bucket = per_axis.get(f["axis"])
        if not bucket:
            continue
        if f["severity"] == "positive":
            bucket["positives"] += 1
        else:
            bucket["penalties"].append(
                {"severity": f["severity"], "title": f["title"], "penalty": SEVERITY_PENALTY[f["severity"]]}
            )

    for m in missing:
        bucket = per_axis.get(m.get("axis", "completeness"))
        if bucket:
            bucket["missing"] += 1

    axis_scores = {}
    for a in AXES:
        b = per_axis[a["key"]]
        penalty = sum(p["penalty"] for p in b["penalties"])
        missing_penalty = min(MAX_MISSING_PENALTY, b["missing"] * MISSING_PENALTY)
        bonus = min(MAX_POSITIVE_BONUS, b["positives"] * POSITIVE_BONUS)
        value = 100.0 - penalty - missing_penalty + bonus
        axis_scores[a["key"]] = max(0.0, min(100.0, value))

    caps = _cap_axes(ctx, findings, missing)
    applied = []
    for cap in caps:
        key = cap["axis"]
        if key in axis_scores and axis_scores[key] > cap["max"]:
            applied.append(dict(cap))
            axis_scores[key] = cap["max"]

    overall = sum(axis_scores[a["key"]] * a["weight"] for a in AXES)

    overall_caps = [c["overall_max"] for c in caps if c.get("overall_max")]
    if overall_caps:
        limit = min(overall_caps)
        if overall > limit:
            overall = limit
            applied.append({
                "axis": "overall", "max": limit,
                "reason": "A structural problem elsewhere limits the overall score.",
            })

    overall = round(max(0.0, min(100.0, overall)), 1)
    verdict = verdict_for(overall)

    return {
        "overall": overall,
        "verdict": verdict["key"],
        "verdict_label": verdict["label"],
        "verdict_advice": verdict["advice"],
        "axes": [
            {
                "key": a["key"],
                "label": a["label"],
                "about": a["about"],
                "weight": a["weight"],
                "score": round(axis_scores[a["key"]], 1),
                "findings": len(per_axis[a["key"]]["penalties"]),
                "positives": per_axis[a["key"]]["positives"],
                "missing": per_axis[a["key"]]["missing"],
            }
            for a in AXES
        ],
        "caps": applied,
        "counts": {
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
            "positive": sum(1 for f in findings if f["severity"] == "positive"),
        },
    }
