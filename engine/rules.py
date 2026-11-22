"""Risk probes and the missing-clause library for Clause Lens.

Every probe is a small function that inspects the contract text and returns a
finding (or nothing). Findings carry the evidence sentence that triggered them,
why it matters, a concrete fix, and a fallback position.
"""

import re
from dataclasses import dataclass, field

from .clauses import sentences_matching, split_sentences

PERSPECTIVES = {
    "client": "I am paying for the work (buyer of services).",
    "vendor": "I am providing the work (supplier of services).",
    "employee": "I am the employee or individual contractor.",
    "party": "Neutral: I have not said which side I am on.",
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "sixty": 60,
    "ninety": 90, "ninety-five": 95, "one hundred twenty": 120,
}


@dataclass
class Context:
    text: str
    contract_type: str = "generic"
    perspective: str = "party"
    clauses: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)

    def has(self, key):
        c = self.clauses.get(key)
        return bool(c and c.present)


def parse_number(token):
    if token is None:
        return None
    t = str(token).strip().lower().replace("-", " ")
    if t.isdigit():
        return int(t)
    if t in NUMBER_WORDS:
        return NUMBER_WORDS[t]
    if t.replace(" ", "_") in NUMBER_WORDS:
        return NUMBER_WORDS[t.replace(" ", "_")]
    return None


def _first_number(sentence, unit_pattern=r"(?:calendar\s+|business\s+)?days?"):
    if not sentence:
        return None
    m = re.search(r"(\d{1,3})\s*" + unit_pattern, sentence, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(" + "|".join(NUMBER_WORDS) + r")\s*(?:\(\d{1,3}\)\s*)?"
                  + unit_pattern, sentence, re.I)
    if m:
        return parse_number(m.group(1))
    return None


def net_days(text):
    """Payment window in days, from several common phrasings."""
    m = re.search(r"\bnet\s+(\d{1,3})\b", text, re.I)
    if m:
        return int(m.group(1))
    for s in sentences_matching(text, r"invoice|payment|fees|payable"):
        v = _first_number(s)
        if v:
            return v
    return None


def late_fee_percent(text):
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:per|a|each)\s*(?:month|monthly)", text, re.I)
    if m:
        return float(m.group(1))
    for s in sentences_matching(text, r"late\s+(?:charge|fee|payment)|interest|penalty"):
        m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", s, re.I)
        if m:
            return float(m.group(1))
    return None


def _notice_days(text, anchors):
    """Find a notice window in days near an anchor phrase."""
    for s in sentences_matching(text, "|".join(anchors)):
        v = _first_number(s)
        if v:
            return v
    return None


def renewal_notice_days(text):
    return _notice_days(text, [r"renew", r"auto[-\s]?renew"])


def termination_notice_days(text):
    return _notice_days(text, [r"terminat", r"end\s+the\s+agreement"])


def term_months(text):
    patterns = [
        r"(?:initial\s+|subscription\s+|renewal\s+)?term\b[^.]{0,80}?\(?(\d{1,3})\)?\s*"
        r"(year|month)s?\b",
        r"for\s+a\s+period\s+of\s+\(?(\d{1,3})\)?\s*(year|month)s?\b",
        r"\b(?:one|two|three|four|five|six|eight|ten|twelve|twenty|thirty|forty|fifty)\b\s*"
        r"\((\d{1,3})\)\s*(year|month)s?\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            n = int(m.group(1))
            return n * 12 if m.group(2).lower() == "year" else n
    return None


def confidentiality_years(text):
    for s in sentences_matching(text, r"confidential"):
        m = re.search(r"(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?(year|month)s?\b", s, re.I)
        if m:
            n = int(m.group(1))
            return n if m.group(2).lower() == "year" else round(n / 12.0, 2)
        m = re.search(r"\b(one|two|three|five|seven)\b\s*\((\d{1,3})\)\s*(year|month)s?\b", s, re.I)
        if m:
            n = int(m.group(2))
            return n if m.group(3).lower() == "year" else round(n / 12.0, 2)
    return None


def build_context(text, contract_type="generic", perspective="party"):
    text = text or ""
    ctx = Context(text=text, contract_type=contract_type, perspective=perspective)

    auto_renew = bool(re.search(r"auto[-\s]?renew\w*|automatically\s+renew\w*|"
                                r"renews?\s+automatically|shall\s+renew|"
                                r"renew\s+automatically", text, re.I))
    one_way_indemnity = bool(
        re.search(r"(?:vendor|contractor|provider|supplier|employee|client|customer|company|recipient)"
                  r"\s+(?:shall|will|agrees? to)\s+[^.]{0,30}?indemnif\w*", text, re.I)
    )
    ip_assignment = bool(re.search(r"assign(?:s|ment|ing)?[^.]{0,160}"
                                   r"(?:intellectual property|work product|"
                                   r"deliverables?|work made for hire)", text, re.I)
                         or re.search(r"all\s+rights?,\s*title\s+and\s+interest", text, re.I))
    carveout = bool(re.search(r"pre[-\s]?existing|background\s+ip|prior\s+know-how|"
                              r"residual\s+knowledge|tools?\s+and\s+technologies|"
                              r"nothing\s+herein\s+shall\s+be\s+interpreted\s+to\s+assign", text, re.I))
    perpetual_license = bool(re.search(r"perpetual[^.]{0,60}licen[cs]e|licen[cs]e[^.]{0,60}perpetual",
                                       text, re.I))
    # a perpetual licence to embedded pre-existing materials is ordinary practice,
    # so it does not set the flag
    if perpetual_license and re.search(r"as\s+embedded|pre[-\s]?existing\s+materials?|"
                                       r"general\s+know[-\s]?how", text, re.I):
        perpetual_license = False
    uncapped_carveouts = bool(re.search(r"(?:not\s+be\s+(?:subject|limited)\s+(?:to|by)[^.]{0,80}"
                                         r"(?:consequential|indirect|liability\s+cap|limitation))"
                                         r"|shall\s+not\s+apply\s+to[^.]{0,80}indemnif", text, re.I))
    termination_for_cause = bool(re.search(r"terminat\w*[^.]{0,140}?\b(?:for\s+cause|material\s+breach\w*|"
                                           r"materially\s+default\w*|materially\s+breach\w*|breach\w*\s+of\s+(?:this|the)\s+agreement|"
                                           r"failure\s+to\s+(?:perform|pay)|insolven)", text, re.I))

    ctx.flags = {
        "auto_renew": auto_renew,
        "renewal_notice_days": renewal_notice_days(text),
        "net_days": net_days(text),
        "late_fee_percent": late_fee_percent(text),
        "termination_notice_days": termination_notice_days(text),
        "term_months": term_months(text),
        "confidentiality_years": confidentiality_years(text),
        "one_way_indemnity": one_way_indemnity,
        "ip_assignment": ip_assignment,
        "ip_assignment_without_carveout": ip_assignment and not carveout,
        "perpetual_license": perpetual_license,
        "uncapped_carveouts": uncapped_carveouts,
        "termination_for_cause": termination_for_cause,
        "compounding_interest": bool(re.search(r"compoun", text, re.I)),
    }
    return ctx


# --------------------------------------------------------------------------
# probe registry
# --------------------------------------------------------------------------

PROBES = []


def probe(key, axis, severity, title, perspectives=None, severity_by_perspective=None,
          leverage=3, impact=3):
    def deco(fn):
        PROBES.append({
            "key": key,
            "axis": axis,
            "severity": severity,
            "title": title,
            "perspectives": tuple(perspectives) if perspectives else (),
            "severity_by_perspective": dict(severity_by_perspective or {}),
            "leverage": leverage,
            "impact": impact,
            "fn": fn,
        })
        return fn

    return deco


def ev(ctx, pattern, fallback=""):
    """First sentence matching a pattern, used as evidence."""
    hits = sentences_matching(ctx.text, pattern)
    return hits[0].strip() if hits else fallback


def _make(ctx, spec, res):
    out = []
    items = res if isinstance(res, list) else ([res] if res else [])
    for item in items:
        if not item:
            continue
        sev = item.get("severity")
        if not sev:
            sev = spec["severity_by_perspective"].get(ctx.perspective, spec["severity"])
        out.append({
            "clause": item.get("clause", spec["key"]),
            "axis": spec["axis"],
            "severity": sev,
            "title": item.get("title", spec["title"]),
            "evidence": item.get("evidence", ""),
            "why": item.get("why", ""),
            "fix": item.get("fix", ""),
            "fallback": item.get("fallback", ""),
            "leverage": item.get("leverage", spec["leverage"]),
            "impact": item.get("impact", spec["impact"]),
        })
    return out


# ---------------------------- financial -----------------------------------

@probe("net_days_long", "financial", "high",
       "Payment window is longer than 45 days",
       severity_by_perspective={"vendor": "low", "employee": "low"},
       leverage=4, impact=4)
def _net_days_long(ctx):
    n = ctx.flags.get("net_days")
    if not n or n <= 45:
        return None
    return {
        "clause": "payment_terms",
        "evidence": ev(ctx, r"net\s+\d{1,3}|payable\s+within|payment\s+terms",
                       "Payment terms found in the document."),
        "why": ("Net {0} means you wait two months for money you already earned. "
                "It also quietly signals who is short of cash.".format(n)),
        "fix": "Change the payment window to Net 30 from the invoice date.",
        "fallback": "Accept Net 45 only if the contract caps late-payment interest at 1% per month.",
    }


@probe("no_payment_terms", "financial", "medium",
       "No payment terms found", leverage=4, impact=3)
def _no_payment_terms(ctx):
    if ctx.has("payment_terms"):
        return None
    return {
        "clause": "payment_terms",
        "evidence": "No clause mentioning invoices, fees or payment timing was found.",
        "why": "Without payment terms, when you pay is whatever the other side says.",
        "fix": "Add: Client shall pay all undisputed invoices within thirty (30) days of receipt.",
        "fallback": "At minimum, state that undisputed invoices are payable within Net 30.",
    }


@probe("late_fee_high", "financial", "medium",
       "Late payment charge is on the aggressive side",
       severity_by_perspective={"vendor": "low"},
       leverage=3, impact=3)
def _late_fee_high(ctx):
    pct = ctx.flags.get("late_fee_percent")
    if not pct or pct <= 1.5:
        return None
    return {
        "clause": "payment_terms",
        "evidence": ev(ctx, r"late\s+(?:charge|fee|payment)|interest|penalty",
                       "Late payment terms found."),
        "why": ("A {0}% monthly late charge compounds quickly and is often unenforceable "
                "against a business, but it still shows up in collections.".format(pct)),
        "fix": "Cap late interest at 1% per month, non-compounding, on undisputed amounts only.",
        "fallback": "Keep the rate but limit it to undisputed invoices and add a 30-day cure period.",
    }


@probe("compounding_interest", "financial", "medium",
       "Interest compounds", severity_by_perspective={"vendor": "low"}, leverage=3, impact=3)
def _compounding(ctx):
    if not ctx.flags.get("compounding_interest"):
        return None
    return {
        "clause": "payment_terms",
        "evidence": ev(ctx, r"compoun", "Compounding interest language found."),
        "why": "Compounding turns a modest late fee into a large one over time.",
        "fix": "State that interest accrues on unpaid amounts and does not compound.",
    }


@probe("uncapped_fee_increase", "financial", "high",
       "Fees can be increased without a cap", leverage=3, impact=4)
def _fee_increase(ctx):
    hits = [s for s in sentences_matching(
        ctx.text, r"increase|adjust(?:ment)?\s+to\s+(?:the\s+)?(?:fees|rates|prices)")
        if not re.search(r"renew", s, re.I)]
    if not hits:
        return None
    if re.search(r"no\s+more\s+than|CPI|not\s+to\s+exceed|capped\s+at|maximum\s+of\s+\d", ctx.text, re.I):
        return None
    return {
        "clause": "payment_terms",
        "evidence": hits[0],
        "why": ("An uncapped price increase means your cost can move without a ceiling. "
                "Ask for a ceiling and notice before it applies."),
        "fix": "Add: Provider may adjust fees once per year with 60 days notice, capped at 5% or CPI.",
        "fallback": "Accept a change with 60 days written notice and a right to terminate without penalty.",
    }


@probe("annual_prepayment", "financial", "medium",
       "Payment is due in advance for a full term", leverage=4, impact=4)
def _annual_prepay(ctx):
    hits = [s for s in sentences_matching(
        ctx.text, r"payable\s+in\s+advance|payment\s+in\s+advance|\bupfront\b|"
                   r"prepayment\s+of|pay\s+annually|annual\s+(?:fee|charge)\s+of")
        if not re.search(r"refund", s, re.I)]
    if not hits:
        return None
    if not re.search(r"non[-\s]?refundable", ctx.text, re.I):
        return {
            "clause": "payment_terms",
            "evidence": hits[0],
            "why": "Paying before you receive the work puts all the credit risk on you.",
            "fix": "Pay monthly or quarterly in arrears, or make prepayments non-refundable only for the unused period.",
            "fallback": "Keep the prepayment but require a pro-rata refund if you terminate for cause.",
            "severity": "low",
        }
    return {
        "clause": "payment_terms",
        "evidence": hits[0],
        "why": "A full-term non-refundable prepayment is the most expensive risk in the document.",
        "fix": "Cap any prepayment at one month, credited against the total, and make the balance payable monthly.",
        "fallback": "Make prepayment non-refundable only for the period actually used.",
    }


@probe("early_termination_fee", "financial", "high",
       "Early termination carries a fee", severity_by_perspective={"vendor": "low"}, leverage=3, impact=4)
def _early_termination_fee(ctx):
    hits = sentences_matching(ctx.text, r"early\s+termination\s+(?:fee|charge|cost)")
    if not hits:
        return None
    m = re.search(r"(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?(?:months?|days?)", hits[0], re.I)
    detail = " for {0}".format(m.group(0).strip()) if m else ""
    return {
        "clause": "termination",
        "evidence": hits[0],
        "why": "An early exit fee{0} decides whether you can still walk away from a bad deal.".format(detail),
        "fix": "Limit the fee to costs actually incurred, capped at one month of fees.",
        "fallback": "No fee where the other party is in material breach.",
    }


@probe("no_refund_on_exit", "financial", "medium",
       "No refund position if you leave early", severity_by_perspective={"vendor": "low"},
       leverage=4, impact=3)
def _no_refund(ctx):
    if not ctx.has("termination"):
        return None
    if re.search(r"refund|prorat|pro[-\s]?rat", ctx.text, re.I):
        return None
    return {
        "clause": "termination",
        "evidence": ev(ctx, r"terminat", "Termination language found."),
        "why": "If you exit mid-term there is no rule for what happens to money you already paid.",
        "fix": "Add: On termination by Client, Provider shall refund prepaid fees for the unused term within 30 days.",
    }


@probe("disputed_invoice_open_ended", "financial", "medium",
       "Disputed invoices have no resolution deadline", leverage=3, impact=3)
def _disputed_invoice(ctx):
    hits = sentences_matching(ctx.text, r"dispute\w*\s+(?:the\s+)?(?:invoice|fees|payment)|"
                                         r"withhold\s+payment|good\s+faith\s+dispute")
    if not hits:
        return None
    if _first_number(hits[0]) or re.search(r"within\s+\w|promptly|reasonable\s+time",
                                                   hits[0], re.I):
        return None
    return {
        "clause": "payment_terms",
        "evidence": hits[0],
        "why": "An open-ended dispute right means a disputed invoice can sit unpaid indefinitely.",
        "fix": "Add: undisputed amounts shall be paid on time, and disputed amounts resolved in writing within 30 days.",
    }


@probe("expenses_uncapped", "financial", "low",
       "Expenses are reimbursed with no stated cap", leverage=3, impact=2)
def _expenses(ctx):
    hits = sentences_matching(ctx.text, r"reimburs\w+\s+expenses|expenses\s+(?:shall|will)\s+be")
    if not hits:
        return None
    if re.search(r"pre[-\s]?approv|\bnot\s+to\s+exceed|no\s+more\s+than|receipts?\s+(?:are\s+)?required",
                 ctx.text, re.I):
        return None
    return {
        "clause": "payment_terms",
        "evidence": hits[0],
        "why": "Uncapped expenses let the cost line grow without either side noticing.",
        "fix": "Require pre-approval for any single expense above a set amount, with receipts.",
    }


@probe("no_payment_window", "financial", "medium",
       "Fees are mentioned but no payment window is set", leverage=4, impact=3)
def _no_payment_window(ctx):
    if not ctx.has("payment_terms"):
        return None
    if re.search(r"net\s+\d{1,3}|payable\s+within|due\s+on\s+receipt|payable\s+on\s+the\s+first|"
                 r"due\s+on\s+the\s+first|within\s+\d{1,3}|within\s+\w+\s*\(\d{1,3}\)|"
                 r"days\s+(?:of|from|after)\s+(?:receipt|the\s+invoice)", ctx.text, re.I):
        return None
    return {
        "clause": "payment_terms",
        "evidence": ev(ctx, r"fees?|invoice", "Fees are mentioned in the document."),
        "why": "The document sets a price but never says when it is due. That becomes an argument later.",
        "fix": "Add: Undisputed invoices are payable within thirty (30) days of receipt.",
        "fallback": "State the due date relative to the invoice date.",
    }


# ------------------------------- exit --------------------------------------

@probe("no_termination_clause", "exit", "critical",
       "No termination clause", leverage=5, impact=5)
def _no_termination(ctx):
    if ctx.has("termination"):
        return None
    if ctx.contract_type == "nda":
        return None
    return {
        "clause": "termination",
        "evidence": "The document contains no termination or end-of-agreement language.",
        "why": "Without an exit you are locked to whatever was agreed, for as long as it lasts.",
        "fix": ("Add a termination clause: either party may terminate for convenience on thirty (30) days "
                "written notice, and immediately for material breach that is not cured within fifteen (15) days."),
        "fallback": "At least a termination-for-cause clause with a cure period.",
    }


@probe("no_termination_for_cause", "exit", "high",
       "Termination does not cover breach", leverage=4, impact=5)
def _no_for_cause(ctx):
    if not ctx.has("termination") or ctx.flags.get("termination_for_cause"):
        return None
    return {
        "clause": "termination",
        "evidence": ev(ctx, r"terminat", "Termination language found."),
        "why": "Termination that only works on notice leaves you paying for a service that is already broken.",
        "fix": "Add: Either party may terminate immediately for material breach, after a 15 day cure period.",
        "fallback": "Allow termination for material breach with a 30 day cure period.",
    }


@probe("termination_notice_long", "exit", "medium",
       "Notice period for termination is over 90 days", leverage=3, impact=4)
def _long_notice(ctx):
    n = ctx.flags.get("termination_notice_days")
    if not n or n <= 90:
        return None
    return {
        "clause": "termination",
        "evidence": ev(ctx, r"terminat", "Termination notice language found."),
        "why": "A {0} day notice period means you keep paying for {0} days of something you may not want.".format(n),
        "fix": "Reduce the convenience-termination notice to 30 days (60 days for a subscription).",
        "fallback": "Keep 60 days but add immediate termination for repeated service failures.",
    }


@probe("one_way_termination", "exit", "high",
       "Only the other party can terminate for convenience",
       severity_by_perspective={"client": "low", "party": "medium"},
       leverage=4, impact=5)
def _one_way_termination(ctx):
    hits = sentences_matching(ctx.text, r"(?:client|customer|company|recipient|purchaser)\s+"
                                         r"(?:may|can|shall\s+have\s+the\s+right\s+to)\s+"
                                         r"terminate[^.]{0,50}for\s+convenience")
    if not hits:
        return None
    if re.search(r"either\s+party[^.]{0,80}terminate\s+for\s+convenience", ctx.text, re.I):
        return None
    return {
        "clause": "termination",
        "evidence": hits[0],
        "why": "Convenience termination is one-sided: they can leave, you cannot.",
        "fix": "Make convenience termination mutual on the same notice period.",
        "fallback": "Add a right to terminate if the other party stops performing or becomes insolvent.",
    }


@probe("auto_renew_short_notice", "exit", "high",
       "Auto-renewal with a short or missing notice window", leverage=5, impact=5)
def _auto_renew_short(ctx):
    if not ctx.flags.get("auto_renew"):
        return None
    n = ctx.flags.get("renewal_notice_days")
    if n and n >= 45:
        return None
    detail = "{0} days notice".format(n) if n else "no stated notice window"
    return {
        "clause": "term_renewal",
        "evidence": ev(ctx, r"auto[-\s]?renew|automatically\s+renew|shall\s+renew",
                       "Auto-renewal language found."),
        "why": ("The contract renews automatically with {0}. Miss it and you are committed "
                "to another term without meaning to.".format(detail)),
        "fix": "Require at least 60 days written notice before the renewal date, and confirm the renewal price in advance.",
        "fallback": "If the window must stay short, require the renewal price to be fixed at least 90 days ahead.",
    }


@probe("auto_renew_workable_notice", "exit", "positive",
       "Auto-renewal has a workable notice window", leverage=1, impact=1)
def _auto_renew_ok(ctx):
    if not ctx.flags.get("auto_renew"):
        return None
    n = ctx.flags.get("renewal_notice_days")
    if not n or n < 45:
        return None
    return {
        "clause": "term_renewal",
        "evidence": ev(ctx, r"renew\w*", "Auto-renewal language found."),
        "why": "A {0} day notice window is enough notice to decide in time. Diary the date anyway.".format(n),
        "fix": "Keep this. Put the notice deadline in your calendar when you sign.",
        "severity": "positive",
    }


@probe("renewal_term_long", "exit", "medium", "Renewal terms are long", leverage=3, impact=4)
def _renewal_term_long(ctx):
    m = re.search(r"renewal\s+term[^.]{0,60}?(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?(year|month)s?", ctx.text, re.I)
    if not m:
        return None
    n = int(m.group(1))
    months = n * 12 if m.group(2).lower() == "year" else n
    if months < 12:
        return None
    return {
        "clause": "term_renewal",
        "evidence": m.group(0).strip(),
        "why": "A {0} month renewal is a long commitment made by accident.".format(months),
        "fix": "Shorten the renewal term to 12 months, or make it month-to-month after the first term.",
    }


@probe("renewal_price_increase", "exit", "high",
       "Price can rise at renewal with no cap", leverage=4, impact=4)
def _renewal_price(ctx):
    hits = sentences_matching(ctx.text, r"renew\w*[^.]{0,120}(?:increase|adjust)|"
                                         r"(?:increase|adjust)[^.]{0,60}renew")
    if not hits:
        return None
    if re.search(r"no\s+more\s+than|CPI|not\s+to\s+exceed|capped\s+at", ctx.text, re.I):
        return None
    return {
        "clause": "term_renewal",
        "evidence": hits[0],
        "why": "Renewal with a free hand on price means the same work costs more every year.",
        "fix": "Cap the renewal increase at the lower of 5% or CPI, with 60 days notice before the renewal date.",
    }


@probe("initial_term_long", "exit", "low", "Initial term is long", leverage=3, impact=3)
def _initial_term_long(ctx):
    months = ctx.flags.get("term_months")
    if not months or months <= 24:
        return None
    return {
        "clause": "term_renewal",
        "evidence": ev(ctx, r"\bterm\b", "Term language found."),
        "why": "A {0} month initial term is a long lock-in before you have seen the work.".format(months),
        "fix": "Shorten the initial term to 12 months with a termination right at the end of each year.",
    }


@probe("assignment_on_change_of_control", "exit", "medium",
       "The contract passes to a new owner automatically", leverage=3, impact=4)
def _change_of_control(ctx):
    hits = sentences_matching(ctx.text, r"change\s+of\s+control|merger\s+or\s+sale\s+of\s+assets|"
                                         r"assignment\s+of\s+this\s+agreement")
    if not hits:
        return None
    if re.search(r"prior\s+written\s+consent|without\s+consent", ctx.text, re.I):
        return None
    return {
        "clause": "assignment",
        "evidence": hits[0],
        "why": "If the other side is bought, you may end up in a contract with a stranger.",
        "fix": "Add: Assignment on a change of control requires the other party's prior written consent.",
    }


@probe("no_suspension_right", "exit", "low",
       "No right to suspend for non-payment", perspectives=("vendor", "employee", "party"),
       severity_by_perspective={"party": "low"}, leverage=2, impact=2)
def _suspension(ctx):
    if not ctx.has("termination"):
        return None
    if re.search(r"suspend[^.]{0,80}(?:non[-\s]?payment|failure\s+to\s+pay|overdue)", ctx.text, re.I):
        return None
    return {
        "clause": "termination",
        "evidence": ev(ctx, r"terminat", "Termination language found."),
        "why": "Without a suspension right you keep delivering for free after you stop being paid.",
        "fix": "Add: Provider may suspend performance on ten (10) days written notice of overdue undisputed amounts.",
        "severity": "low",
    }


# ----------------------------- ip / conf ----------------------------------

@probe("ip_assignment_without_carveout", "ip", "high",
       "All IP is assigned with no carve-out for what you already owned",
       severity_by_perspective={"client": "low", "party": "medium"},
       leverage=4, impact=5)
def _ip_no_carveout(ctx):
    if not ctx.flags.get("ip_assignment") or ctx.flags.get("ip_assignment_without_carveout") is False:
        return None
    if not ctx.flags.get("ip_assignment_without_carveout"):
        return None
    return {
        "clause": "ip_ownership",
        "evidence": ev(ctx, r"assign|all\s+rights,\s+title\s+and\s+interest",
                       "IP assignment language found."),
        "why": ("Taken literally, this hands over tools, templates and know-how you built "
                "before the project. It is also the clause most often argued about later."),
        "fix": ("Add: Pre-existing materials remain the original owner's property and are licensed to the "
                "other party for use with the deliverables."),
        "fallback": "Carve out only your pre-existing materials and general tools, not the know-how.",
    }


@probe("work_for_hire_only", "ip", "medium",
       "Work-for-hire wording with no assignment backstop", leverage=3, impact=4)
def _work_for_hire(ctx):
    if not re.search(r"work\s+made\s+for\s+hire", ctx.text, re.I):
        return None
    if re.search(r"assign(?:s|ment)?[^.]{0,160}(?:deliverables?|work\s+product|work)", ctx.text, re.I):
        return None
    return {
        "clause": "ip_ownership",
        "evidence": ev(ctx, r"work\s+made\s+for\s+hire", "Work made for hire language found."),
        "why": ("Work-for-hire only transfers copyright where the law recognises the category. "
                "For software, custom designs and commissioned art it often does not, so you keep owning what you made."),
        "fix": "Add an express written assignment of all right, title and interest in the deliverables.",
        "fallback": "Keep work-for-hire and add: to the extent any rights do not vest automatically, they are assigned.",
    }


@probe("perpetual_license", "ip", "high", "Perpetual, irrevocable licence",
       severity_by_perspective={"client": "low", "party": "medium"}, leverage=3, impact=4)
def _perpetual_license(ctx):
    if not ctx.flags.get("perpetual_license"):
        return None
    return {
        "clause": "license_grant",
        "evidence": ev(ctx, r"perpetual", "Perpetual licence language found."),
        "why": "A perpetual irrevocable licence cannot be taken back, even if the relationship ends badly.",
        "fix": "Limit the licence to the term of the agreement plus a short tail, or to the uses you actually need.",
        "fallback": "Keep perpetual but limit it to internal use of the deliverables, with no sublicensing.",
    }


@probe("no_license_back", "ip", "medium",
       "No right to keep using the work after the contract ends",
       severity_by_perspective={"client": "low"}, leverage=3, impact=4)
def _no_license_back(ctx):
    if not ctx.flags.get("ip_assignment"):
        return None
    if re.search(r"license\s+back|licence\s+back|continue\s+to\s+use|perpetual\s+licen[cs]e\s+to\s+use",
                 ctx.text, re.I):
        return None
    return {
        "clause": "ip_ownership",
        "evidence": ev(ctx, r"assign|intellectual\s+property", "IP assignment language found."),
        "why": "If the contract ends, the licence that lets you keep using what you built often ends too.",
        "fix": "Add: On termination, Provider grants Client a perpetual licence to use the paid-for deliverables.",
        "fallback": "Add a 12 month transition licence to wind down existing projects.",
    }


@probe("nda_missing_confidentiality", "ip", "critical",
       "A non-disclosure agreement with no confidentiality obligation", leverage=5, impact=5)
def _nda_missing(ctx):
    if ctx.contract_type != "nda" or ctx.has("confidentiality"):
        return None
    return {
        "clause": "confidentiality",
        "evidence": "The document is labelled as an NDA but contains no confidentiality clause.",
        "why": "An NDA without a confidentiality obligation protects nothing.",
        "fix": "Add a mutual confidentiality clause with definition, exclusions, term and return or destruction.",
    }


@probe("confidentiality_short", "ip", "medium",
       "Confidentiality obligations expire quickly", leverage=3, impact=3)
def _conf_short(ctx):
    years = ctx.flags.get("confidentiality_years")
    if not years or years >= 3:
        return None
    return {
        "clause": "confidentiality",
        "evidence": ev(ctx, r"confidential", "Confidentiality language found."),
        "why": "{0} year(s) of confidentiality is short for anything you would not want published.".format(years),
        "fix": "Extend confidentiality to 5 years after the last disclosure, and indefinitely for trade secrets.",
    }


@probe("residuals_clause", "ip", "medium",
       "Residuals clause lets the other side use remembered information",
       leverage=3, impact=3)
def _residuals(ctx):
    hits = sentences_matching(ctx.text, r"residual")
    if not hits:
        return None
    return {
        "clause": "confidentiality",
        "evidence": hits[0],
        "why": ("A residuals clause lets someone keep information they simply remember. "
                "That quietly defeats the confidentiality obligation itself."),
        "fix": "Delete the residuals clause, or limit it to unaided memory of general skills and ideas, not your data.",
    }


@probe("confidentiality_no_carveouts", "ip", "low",
       "Confidentiality has no standard carve-outs", leverage=3, impact=2)
def _conf_carveouts(ctx):
    if not ctx.has("confidentiality"):
        return None
    if re.search(r"publicly\s+(?:available|known)|already\s+known|independent\s+development|"
                 r"rightfully\s+(?:received|obtained)", ctx.text, re.I):
        return None
    return {
        "clause": "confidentiality",
        "evidence": ev(ctx, r"confidential", "Confidentiality language found."),
        "why": ("Confidentiality with no exclusions is hard to honour: it can cover information "
                "that was already public, which makes the clause look unfair and hard to enforce."),
        "fix": "Add standard exclusions: public information, already known, independently developed, lawfully received.",
    }


@probe("no_survival", "ip", "medium",
       "Obligations do not say they survive termination", severity_by_perspective={"client": "low"},
       leverage=3, impact=3)
def _no_survival(ctx):
    if ctx.has("survival"):
        return None
    return {
        "clause": "survival",
        "evidence": "No survival clause found.",
        "why": "Without survival, confidentiality and IP duties can be argued to end with the contract.",
        "fix": "Add: Clauses concerning confidentiality, intellectual property, indemnity, payment and dispute resolution survive termination.",
    }


@probe("portfolio_rights_missing", "ip", "low",
       "No right to show the work", perspectives=("vendor", "employee", "party"),
       severity_by_perspective={"party": "low"}, leverage=3, impact=2)
def _portfolio(ctx):
    if ctx.has("publicity"):
        return None
    if ctx.contract_type not in ("freelance", "msa", "sow", "generic"):
        return None
    return {
        "clause": "publicity",
        "evidence": "No publicity or portfolio clause found.",
        "why": "Without it you may have no right to show the work you did, which matters for your next pitch.",
        "fix": "Add: Provider may display completed deliverables in a portfolio after the work goes live, with client approval.",
    }


@probe("mutual_confidentiality", "ip", "positive",
       "Confidentiality obligations run both ways", leverage=1, impact=1)
def _mutual_conf(ctx):
    if not ctx.has("confidentiality"):
        return None
    if not re.search(r"each\s+party[^.]{0,120}confidential|both\s+parties[^.]{0,120}confidential|"
                     r"mutual(?:ly)?[^.]{0,60}confidential", ctx.text, re.I):
        return None
    return {
        "clause": "confidentiality",
        "evidence": ev(ctx, r"confidential", "Mutual confidentiality language found."),
        "why": "Mutual confidentiality is fair and is usually easy to keep.",
        "fix": "Keep this as drafted.",
        "severity": "positive",
    }


# --------------------------- risk allocation ------------------------------

@probe("no_liability_cap", "risk", "critical",
       "No limitation of liability", leverage=5, impact=5)
def _no_cap(ctx):
    if ctx.has("liability_cap"):
        return None
    return {
        "clause": "liability_cap",
        "evidence": "No limitation of liability clause found.",
        "why": ("Without a cap your exposure is theoretically unlimited, while the other side's is "
                "whatever they decide to accept. That asymmetry is how one bad week becomes a "
                "company-ending problem."),
        "fix": "Add: Each party's aggregate liability shall not exceed the fees paid or payable in the 12 months before the claim.",
        "fallback": "Cap at 12 months of fees and carve out only fraud and wilful misconduct.",
    }


@probe("liability_cap_too_low", "risk", "high",
       "Liability cap is set below a meaningful amount", leverage=3, impact=4)
def _cap_low(ctx):
    m = re.search(r"(?:fees|amounts?|charges?)\s+(?:paid\s+or\s+payable\s+)?(?:in\s+the\s+)?"
                  r"(?:preceding\s+)?(one|1|three|3|six|6|twelve|12)\s*"
                  r"(?:\(\d{1,3}\)\s*)?months?", ctx.text, re.I)
    if not m:
        return None
    word = m.group(1).lower()
    months = parse_number(word) or 1
    if months >= 6:
        return None
    return {
        "clause": "liability_cap",
        "evidence": m.group(0).strip(),
        "why": "A cap of one month of fees means a single serious incident can exceed the cap many times over.",
        "fix": "Raise the cap to at least 12 months of fees, or to a fixed floor such as $100,000.",
        "fallback": "Keep a lower cap but add a separate super-cap for confidentiality, IP and data protection breaches.",
    }


@probe("uncapped_carveouts", "risk", "high",
       "The liability cap does not apply to the biggest risks", leverage=4, impact=5)
def _carveouts(ctx):
    if not ctx.flags.get("uncapped_carveouts"):
        return None
    return {
        "clause": "liability_cap",
        "evidence": ev(ctx, r"not\s+(?:be\s+(?:subject|limited)|apply)|consequential|indirect",
                       "Carve-out language found."),
        "why": ("If confidentiality, IP and indemnity claims sit outside the cap, the cap is decoration "
                "for the disputes most likely to happen."),
        "fix": "Apply a separate super-cap (for example 2x the general cap) to carve-outs instead of uncapped exposure.",
        "fallback": "Limit the carve-outs to fraud, wilful misconduct and breach of confidentiality.",
    }


@probe("one_way_indemnity", "risk", "high",
       "Indemnity runs one way only", leverage=4, impact=5)
def _one_way_indem(ctx):
    if not ctx.flags.get("one_way_indemnity"):
        return None
    return {
        "clause": "indemnification",
        "evidence": ev(ctx, r"indemnif", "Indemnification language found."),
        "why": "You indemnify them, they do not indemnify you. Their claims and yours are then treated differently.",
        "fix": "Make the indemnity mutual, each party covering claims caused by its own breach, negligence or IP infringement.",
        "fallback": "Keep it one-way but narrow the scope and cap it at the contract value.",
    }


@probe("no_ip_indemnity", "risk", "medium",
       "Nobody indemnifies you for IP infringement", leverage=4, impact=4)
def _no_ip_indem(ctx):
    if not ctx.has("indemnification"):
        return None
    if re.search(r"intellectual\s+property[^.]{0,160}indemnif|indemnif[^.]{0,160}"
                 r"intellectual\s+property|infring\w+[^.]{0,80}indemnif", ctx.text, re.I):
        return None
    return {
        "clause": "indemnification",
        "evidence": ev(ctx, r"indemnif", "Indemnification language found."),
        "why": "If the deliverable infringes someone else's copyright, you are left holding the bill.",
        "fix": "Add: Provider shall defend and indemnify Client against third-party IP infringement claims arising from the deliverables.",
    }


@probe("warranty_disclaimer_only", "risk", "medium",
       "The only warranty is that nothing is warranted", severity_by_perspective={"vendor": "low"},
       leverage=3, impact=3)
def _warranty_disclaimer(ctx):
    if not re.search(r"\bas\s+is\b|\bas\s+available\b|no\s+warrant\w+", ctx.text, re.I):
        return None
    if re.search(r"warrant(?:y|ies)[^.]{0,120}(?:professional|workmanlike|conform|material\s+conform|"
                 r"free\s+of\s+defects|fit\s+for\s+(?:the\s+)?purpose)", ctx.text, re.I):
        return None
    return {
        "clause": "warranty",
        "evidence": ev(ctx, r"as\s+is|no\s+warrant", "Disclaimer language found."),
        "why": "An as-is disclaimer with no positive promise means you own the risk of ordinary bad work.",
        "fix": "Add a warranty that services are performed professionally and in accordance with the agreed scope.",
    }


@probe("no_authority_warranty", "risk", "low",
       "No warranty that the other side owns what it gives you", leverage=3, impact=3)
def _no_authority(ctx):
    if re.search(r"warrant\w+[^.]{0,140}(?:right\s+to|title\s+to|owns|entitled\s+to)", ctx.text, re.I):
        return None
    if not ctx.flags.get("ip_assignment"):
        return None
    return {
        "clause": "warranty",
        "evidence": ev(ctx, r"intellectual\s+property|assign", "IP language found."),
        "why": "Assigning rights you do not hold is a warranty nobody made.",
        "fix": "Add: Each party warrants it has the right to grant the rights it grants under this Agreement.",
    }


@probe("no_governing_law", "risk", "medium", "No governing law or venue", leverage=4, impact=4)
def _no_governing(ctx):
    if ctx.has("governing_law"):
        return None
    return {
        "clause": "governing_law",
        "evidence": "No governing law or venue clause found.",
        "why": "Without a forum, a dispute starts with an argument about where to argue.",
        "fix": "Add: This Agreement is governed by the laws of [State], and the parties submit to the courts of [County].",
    }


@probe("arbitration_costly", "risk", "medium",
       "Mandatory arbitration with a costly path", leverage=3, impact=3)
def _arbitration(ctx):
    hits = sentences_matching(ctx.text, r"arbitrat")
    if not hits:
        return None
    cost = []
    if re.search(r"prevailing\s+party[^.]{0,120}attorneys'?", ctx.text, re.I):
        cost.append("the prevailing party recovers its legal costs")
    if re.search(r"each\s+party[^.]{0,80}(?:bear|own)\s+(?:its|their)\s+own\s+(?:costs|fees|attorneys)",
                 ctx.text, re.I):
        cost.append("each side pays its own costs")
    if not cost:
        return None
    return {
        "clause": "dispute_resolution",
        "evidence": hits[0],
        "why": "Arbitration is private and can be expensive. Here {0}.".format(" and ".join(cost)),
        "fix": "Add a carve-out so either party may seek injunctive relief in court, and confirm the arbitration venue.",
        "fallback": "Keep arbitration but ask for a low-cost expedited tier for claims below a set amount.",
    }


@probe("jury_waiver", "risk", "low", "Right to a jury trial is waived", leverage=2, impact=2)
def _jury(ctx):
    if not re.search(r"waiv\w+[^.]{0,60}\bjury\b|trial\s+by\s+jury[^.]{0,40}waiv", ctx.text, re.I):
        return None
    return {
        "clause": "dispute_resolution",
        "evidence": ev(ctx, r"jury", "Jury trial waiver found."),
        "why": "A jury waiver is common, but it means your claim is decided by an arbitrator instead of a jury.",
        "fix": "Keep the waiver if you accept arbitration, but make sure the arbitration rules and venue are named.",
        "severity": "low",
    }


@probe("broad_exclusivity", "risk", "high",
       "Exclusivity blocks you from working with others", severity_by_perspective={"vendor": "low"},
       leverage=3, impact=4)
def _exclusivity(ctx):
    hits = [s for s in sentences_matching(ctx.text, r"exclusiv")
            if re.search(r"(?<!non-)(?<!non )\bexclusiv", s, re.I)
            and not re.search(r"jurisdiction|\bcourts?\b|venue|remed(y|ies)|no\s+other\s+remed|"
                              r"vest\b|\bassigned\b|ownership|right,\s*title", s, re.I)]
    if not hits:
        return None
    return {
        "clause": "exclusivity",
        "evidence": hits[0],
        "why": "Exclusivity removes a customer or market you cannot get back once the term ends.",
        "fix": "Limit exclusivity to the specific service or territory named, and add a right to terminate if sales fall below a floor.",
        "fallback": "Make exclusivity non-exclusive for any segment the other party does not actively serve.",
    }


@probe("non_compete_present", "risk", "high",
       "Non-compete restricts what you can do next", severity_by_perspective={"client": "low"},
       leverage=3, impact=4)
def _non_compete(ctx):
    hits = sentences_matching(ctx.text, r"non[-\s]?compete|competitive\s+business|shall\s+not[^.]{0,80}"
                                         r"engage\s+in[^.]{0,60}business")
    if not hits:
        return None
    months = ctx.flags.get("term_months")
    return {
        "clause": "non_compete",
        "evidence": hits[0],
        "why": ("A non-compete can block the work you would otherwise take next. It is also "
                "unenforceable in several states, so it may bind you in one place and not another."),
        "fix": "Narrow the restriction to specific competitors or a named market, and cut the duration to 12 months.",
        "fallback": "Replace it with a non-solicitation of named clients for 12 months.",
    }


@probe("non_solicit_long", "risk", "medium",
       "Non-solicit runs long or covers everyone", leverage=3, impact=3)
def _non_solicit(ctx):
    hits = sentences_matching(ctx.text, r"non[-\s]?solicit\w*")
    if not hits:
        return None
    tail = re.search(r"(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?(year|month)s?\s*(?:thereafter|after)",
                     ctx.text, re.I)
    broad = bool(re.search(r"any\s+(?:employee|person|individual|contractor)|all\s+employees",
                           ctx.text, re.I))
    if not tail and not broad:
        return None
    detail = "for {0} after termination".format(tail.group(0).strip()) if tail else "covering any person"
    return {
        "clause": "non_compete",
        "evidence": hits[0],
        "why": "A non-solicit {0} can freeze your hiring and your sales pipeline.".format(detail),
        "fix": "Limit it to named key employees or clients, 12 months, and exclude general advertisements.",
    }


@probe("no_compliance_obligation", "risk", "low",
       "No obligation to comply with applicable law", leverage=2, impact=2)
def _compliance(ctx):
    if ctx.has("compliance"):
        return None
    return {
        "clause": "compliance",
        "evidence": "No compliance with applicable laws clause found.",
        "why": "Anti-bribery, sanctions and export rules are usually assumed, but only a clause makes them enforceable.",
        "fix": "Add: Each party shall comply with all applicable laws, including anti-bribery and export control laws.",
        "severity": "low",
    }


@probe("no_insurance_requirement", "risk", "low",
       "No insurance requirement", severity_by_perspective={"vendor": "low"}, leverage=2, impact=2)
def _insurance(ctx):
    if ctx.has("insurance"):
        return None
    if ctx.contract_type not in ("msa", "vendor", "saas", "generic"):
        return None
    return {
        "clause": "insurance",
        "evidence": "No insurance clause found.",
        "why": "If someone is hurt on your site or a system fails, there may be nothing behind you.",
        "fix": "Add: Contractor shall maintain commercial general liability insurance of at least $1M per occurrence.",
        "severity": "low",
    }


@probe("personal_data_without_security", "risk", "medium",
       "Personal data is handled with no security terms", severity_by_perspective={"vendor": "low"},
       leverage=3, impact=4)
def _data_security(ctx):
    if not ctx.has("data_protection"):
        return None
    if re.search(r"security\s+measures|encrypt\w*|penetration\s+test|access\s+control|"
                 r"data\s+processing\s+agreement|breach\s+notification|security\s+incident",
                 ctx.text, re.I):
        return None
    return {
        "clause": "data_protection",
        "evidence": ev(ctx, r"personal\s+data|data\s+protection", "Data protection language found."),
        "why": "Handling personal data with no security obligations creates liability without any control.",
        "fix": "Add a data processing annex covering encryption, access control, breach notification within 48 hours and deletion on exit.",
    }


@probe("no_data_return_on_exit", "risk", "medium",
       "No data export or deletion obligation on exit", severity_by_perspective={"vendor": "low"},
       leverage=3, impact=4)
def _data_exit(ctx):
    if ctx.contract_type != "saas":
        return None
    if not ctx.has("data_protection"):
        return None
    if re.search(r"return[^.]{0,80}data|delet\w+[^.]{0,80}data|export[^.]{0,60}data", ctx.text, re.I):
        return None
    return {
        "clause": "data_protection",
        "evidence": ev(ctx, r"data", "Data clauses found."),
        "why": "If the contract ends, your data can leave with it unless export and deletion are spelled out.",
        "fix": "Add: On termination Provider shall make Customer data available for export for 30 days, then delete it within 60 days.",
    }


@probe("no_sla", "risk", "medium", "No service levels or uptime commitment",
       severity_by_perspective={"vendor": "low"}, leverage=3, impact=3)
def _no_sla(ctx):
    if ctx.contract_type != "saas":
        return None
    if ctx.has("sla"):
        return None
    return {
        "clause": "sla",
        "evidence": "No service level or uptime clause found.",
        "why": "Without an uptime target, availability is a matter of opinion.",
        "fix": "Add an availability SLA (for example 99.9% monthly) with service credits and a chronic-failure termination right.",
    }


# ----------------------------- completeness --------------------------------

@probe("unfilled_placeholders", "completeness", "medium",
       "The document still has blanks to fill", leverage=4, impact=4)
def _placeholders(ctx):
    hits = sentences_matching(ctx.text, r"_{3,}|\[insert|\[company|tbd|to\s+be\s+determined|"
                                         r"__+|\bxx+\b|\[name\]|\[date\]")
    if not hits:
        return None
    return {
        "clause": "parties",
        "evidence": hits[0],
        "why": "Unfilled blanks usually mean a term was never agreed. Whatever sits in that blank decides the risk.",
        "fix": "Complete every blank before signing, and treat any blank left in the document as a deal-breaker.",
        "fallback": "If a blank is intentional, write 'intentionally left blank' next to it.",
    }


@probe("no_notices_clause", "completeness", "low",
       "No clause on how formal notice is delivered", leverage=3, impact=2)
def _no_notices(ctx):
    if ctx.has("notices"):
        return None
    return {
        "clause": "notices",
        "evidence": "No notices clause found.",
        "why": "Without a notice mechanism, a termination notice you email may not count as notice.",
        "fix": "Add a notices clause naming email addresses, addresses and when each is deemed received.",
        "severity": "low",
    }


@probe("no_order_of_precedence", "completeness", "medium",
       "No order of precedence between the agreement and the statement of work",
       leverage=3, impact=3)
def _no_precedence(ctx):
    if not (re.search(r"statement\s+of\s+work", ctx.text, re.I) and ctx.has("scope_deliverables")):
        return None
    if re.search(r"order\s+of\s+precedence|in\s+the\s+event\s+of\s+a\s+conflict|conflict[^.]{0,80}prevail",
                 ctx.text, re.I):
        return None
    return {
        "clause": "change_control",
        "evidence": ev(ctx, r"statement\s+of\s+work", "Statement of work language found."),
        "why": "When the master terms and the work order disagree, nobody knows which wins.",
        "fix": "Add: In the event of conflict, this Agreement governs, except where the SOW expressly states otherwise.",
    }


@probe("no_acceptance_criteria", "completeness", "medium",
       "No acceptance process for deliverables", severity_by_perspective={"vendor": "low"},
       leverage=4, impact=4)
def _no_acceptance(ctx):
    if ctx.contract_type not in ("msa", "sow", "freelance", "vendor", "generic"):
        return None
    if not ctx.has("scope_deliverables"):
        return None
    if ctx.has("acceptance"):
        return None
    return {
        "clause": "acceptance",
        "evidence": ev(ctx, r"deliverables?|scope\s+of\s+work|services", "Scope language found."),
        "why": "Without an acceptance step, a deliverable is never officially finished, so payment and IP transfer never trigger.",
        "fix": "Add: Client shall accept or reject deliverables within 10 business days, with deemed acceptance if no response.",
        "fallback": "Add a written sign-off by email that counts as acceptance.",
    }


@probe("no_entire_agreement", "completeness", "low",
       "No entire agreement clause", leverage=2, impact=2)
def _no_entire(ctx):
    if ctx.has("entire_agreement"):
        return None
    return {
        "clause": "entire_agreement",
        "evidence": "No entire agreement or supersession clause found.",
        "why": "Email promises and side notes can otherwise be argued to be part of the deal.",
        "fix": "Add: This Agreement is the entire agreement and supersedes all prior discussions.",
        "severity": "low",
    }


@probe("no_boilerplate", "completeness", "low",
       "Standard closing boilerplate is missing", leverage=2, impact=2)
def _no_boilerplate(ctx):
    if ctx.has("boilerplate"):
        return None
    return {
        "clause": "boilerplate",
        "evidence": "No severability, counterparts or signature clauses found.",
        "why": "Minor clauses, but they are what makes the document hold together if a part is challenged.",
        "fix": "Add severability, headings, counterparts, electronic signature and no-third-party-beneficiary clauses.",
        "severity": "low",
    }


# --------------------------------------------------------------------------
# missing clause library
# --------------------------------------------------------------------------

MISSING_LIBRARY = {
    "msa": [
        ("liability_cap", "Limitation of liability", "risk",
         "Without a cap, one incident can exceed the whole contract value.",
         "Each party's aggregate liability under this Agreement shall not exceed the fees paid or payable in the twelve (12) months preceding the event giving rise to the claim."),
        ("termination", "Termination rights", "exit",
         "No exit means you are locked in for the full term.",
         "Either party may terminate this Agreement for convenience on thirty (30) days written notice, and immediately for material breach not cured within fifteen (15) days."),
        ("ip_ownership", "IP ownership with a carve-out", "ip",
         "Ownership without a carve-out can take your pre-existing tools with it.",
         "Provider assigns the deliverables, and retains ownership of its pre-existing materials, tools and general know-how."),
        ("acceptance", "Acceptance criteria", "completeness",
         "Deliverables that are never accepted are deliverables you are never paid for.",
         "Client shall accept or reject each deliverable in writing within ten (10) business days, with deemed acceptance if no response is given."),
        ("data_protection", "Data protection terms", "risk",
         "Personal data handled without terms is liability without control.",
         "The parties shall comply with applicable data protection law, including security measures, breach notice within 48 hours and deletion of data on termination."),
        ("governing_law", "Governing law and venue", "risk",
         "No forum means the first fight is about where to fight.",
         "This Agreement is governed by the laws of [State], and the parties submit to the exclusive courts of [County]."),
        ("notices", "Notices", "completeness",
         "A termination notice you never properly sent is not a termination.",
         "Notices shall be in writing and delivered by email to the addresses named in this Agreement, deemed received on the next business day."),
        ("survival", "Survival", "ip",
         "Duties that do not survive end when the contract does.",
         "Clauses concerning confidentiality, intellectual property, indemnity, payment and dispute resolution survive termination."),
    ],
    "sow": [
        ("acceptance", "Acceptance criteria", "completeness",
         "No definition of done means no trigger for payment.",
         "Deliverables are deemed accepted if Client does not respond within ten (10) business days of delivery."),
        ("change_control", "Change control", "completeness",
         "Scope creep without a process becomes a dispute about money.",
         "Any change to the scope, deliverables, timeline or fees must be documented in a written change order signed by both parties."),
        ("payment_terms", "Payment terms", "financial",
         "Nothing says when the work gets paid.",
         "Client shall pay each invoice within thirty (30) days of receipt."),
        ("liability_cap", "Limitation of liability", "risk",
         "A statement of work with no cap inherits unlimited risk.",
         "Liability under this Statement of Work is subject to the limitations of liability in the Master Agreement."),
        ("term_renewal", "Term and end date", "exit",
         "Work without an end date drifts.",
         "This Statement of Work begins on the Effective Date and continues until the final deliverable is accepted."),
    ],
    "nda": [
        ("confidentiality", "Confidentiality obligations", "ip",
         "An NDA without confidentiality language protects nothing.",
         "Each party shall hold the other party's Confidential Information in confidence and use it only for the Purpose."),
        ("exclusions", "Standard exclusions", "ip",
         "Without exclusions the obligation is impossible to honour.",
         "Confidential Information excludes information that is public, already known, independently developed or lawfully received."),
        ("term", "Term of the obligation", "ip",
         "No term means the duty is either infinite or absent.",
         "These obligations continue for five (5) years from disclosure, and indefinitely for trade secrets."),
        ("return", "Return or destruction", "ip",
         "If you keep copies after the deal ends, you are still bound.",
         "On request each party shall return or destroy Confidential Information within thirty (30) days, except archival copies held by law."),
        ("no_licence", "No implied licence", "ip",
         "Silence can be argued as permission.",
         "No licence or other right is granted under any intellectual property right except as expressly stated."),
        ("injunctive", "Right to injunctive relief", "risk",
         "Damages come too late when information is already gone.",
         "A breach of this Agreement is a breach of an obligation of confidence and entitles the other party to injunctive relief."),
    ],
    "freelance": [
        ("scope_deliverables", "Scope and deliverables", "completeness",
         "Unclear deliverables are unclear invoices.",
         "The deliverables are listed in Exhibit A. Work outside Exhibit A is additional work and separately charged."),
        ("acceptance", "Revision rounds and acceptance", "completeness",
         "Without a round limit, revisions are free labour.",
         "Deliverables include two (2) rounds of reasonable revisions. Further rounds are billed at the standard rate."),
        ("kill_fee", "Kill fee on cancellation", "financial",
         "If the project dies, you still deserve the work you did.",
         "On cancellation Client shall pay for work completed to date, plus fifty percent (50%) of the remaining balance."),
        ("ip_ownership", "IP with a carve-out", "ip",
         "A clean assignment without a carve-out can transfer your tools.",
         "Upon full payment the deliverables are assigned; Provider retains its pre-existing materials and grants a perpetual licence to use them as embedded."),
        ("portfolio", "Portfolio rights", "ip",
         "You should be able to show the work.",
         "Provider may display the deliverables in a portfolio after public launch, with Client's written approval."),
        ("payment_terms", "Payment terms", "financial",
         "Late payment has to be priced in or it just happens.",
         "Invoices are payable within thirty (30) days. Overdue invoices accrue interest at 1% per month."),
    ],
    "employment": [
        ("at_will", "Employment status", "completeness",
         "Ambiguous status is the most expensive gap in a contract.",
         "Employment is at will. Either party may end it at any time, with or without cause or notice."),
        ("duties", "Role and duties", "completeness",
         "Job descriptions drift without a written scope.",
         "The Employee shall perform the duties customarily associated with the position of [Title]."),
        ("confidentiality", "Confidentiality and IP assignment", "ip",
         "The most valuable work leaves with the person who made it.",
         "All work product created in the course of employment is work made for hire and assigned to the Company."),
        ("compensation", "Compensation and pay schedule", "financial",
         "Pay should be unambiguous on paper.",
         "Base salary is $X per year, paid semi-monthly, subject to withholdings."),
        ("termination", "Termination and final pay", "exit",
         "Ending a job without clear terms causes claims.",
         "Termination requires two weeks written notice and payment of accrued but unpaid salary."),
        ("non_compete", "Restrictive covenants", "risk",
         "Over-broad covenants are unenforceable and hard to sign.",
         "For twelve (12) months after termination the Employee shall not solicit clients of the Company."),
    ],
    "saas": [
        ("sla", "Uptime and service credits", "risk",
         "Availability is a matter of opinion without an SLA.",
         "Service will be available 99.9% of each month, measured monthly, with service credits and a termination right for chronic failure."),
        ("data_protection", "Data protection and security", "risk",
         "Your data is the product; its protection is the contract.",
         "Provider shall encrypt Customer Data at rest and in transit, and notify any Security Incident within 48 hours."),
        ("data_export", "Export and deletion on exit", "exit",
         "Leaving with your data should be routine, not a favour.",
         "On termination Provider shall make Customer Data available for export for thirty (30) days and delete it within sixty (60) days."),
        ("renewal", "Renewal price and notice", "exit",
         "Renewal is when pricing usually moves.",
         "Renewals are on a 12 month term with 60 days notice before the renewal date, and fees may not increase by more than 5%."),
        ("suspension", "Suspension rights", "risk",
         "Suspension rules should be known before you are suspended.",
         "Provider may suspend for non-payment only after 15 days written notice, and only for the affected service."),
        ("liability_cap", "Limitation of liability", "risk",
         "Data and uptime exposure needs a ceiling.",
         "Each party's aggregate liability shall not exceed the fees paid in the 12 months preceding the claim."),
    ],
    "lease": [
        ("rent", "Rent, due dates and escalators", "financial",
         "The number that matters most should be the clearest.",
         "Monthly rent is $X, due on the first day of each month, increasing by 3% each anniversary."),
        ("deposit", "Deposit and return", "financial",
         "Deposits are a classic source of end-of-tenancy disputes.",
         "Landlord holds a security deposit of $X, to be returned within 21 days of the end of the term less lawful deductions."),
        ("maintenance", "Repairs and maintenance", "exit",
         "Who fixes what should not be a monthly argument.",
         "Tenant shall maintain the interior in good repair; Landlord shall maintain the structure, roof and building systems."),
        ("entry", "Notice of entry", "completeness",
         "Entry without notice is the fastest way to lose a good tenant.",
         "Landlord may enter on 24 hours written notice, except in emergencies."),
        ("assignment", "Assignment and subletting", "exit",
         "Subletting rules decide whether you can move.",
         "Tenant shall not assign or sublet without Landlord's prior written consent, not to be unreasonably withheld."),
        ("termination", "Termination and breach", "exit",
         "Habitability and breach need a path out.",
         "Either party may terminate on 30 days notice; Tenant may terminate immediately for material breach or failure of habitability."),
    ],
    "generic": [
        ("liability_cap", "Limitation of liability", "risk",
         "No cap means no ceiling on exposure.",
         "Each party's aggregate liability shall not exceed the fees paid or payable in the 12 months preceding the claim."),
        ("termination", "Termination rights", "exit",
         "No exit means you cannot fix a bad deal.",
         "Either party may terminate for convenience on 30 days written notice and for material breach after a 15 day cure period."),
        ("governing_law", "Governing law and venue", "risk",
         "No forum means a dispute about the forum.",
         "This Agreement is governed by the laws of [State]; the parties submit to the courts of [County]."),
        ("confidentiality", "Confidentiality", "ip",
         "Information shared under an agreement should stay protected.",
         "Each party shall keep the other's confidential information confidential and use it only for this Agreement."),
        ("notices", "Notices", "completeness",
         "Notice mechanics decide whether a notice counts.",
         "Notices shall be in writing and delivered by email to the addresses named in this Agreement."),
        ("entire_agreement", "Entire agreement", "completeness",
         "Side promises are hard to prove without it.",
         "This Agreement is the entire agreement between the parties and supersedes prior discussions."),
    ],
}


def missing_clauses(ctx):
    """Clauses that a contract of this type should contain but does not."""
    library = MISSING_LIBRARY.get(ctx.contract_type, MISSING_LIBRARY["generic"])
    out = []
    for key, label, axis, why, suggested in library:
        if key in ("exclusions", "term", "return", "no_licence", "injunctive", "at_will", "duties",
                   "compensation", "kill_fee", "portfolio", "deposit", "maintenance", "entry",
                   "rent", "data_export", "renewal", "suspension", "order_of_precedence"):
            marker = {
                "exclusions": r"already\s+known|publicly\s+(?:available|known)|independent",
                "term": r"(?:confidential\w*[^.]{0,120}?)?(?:for|period\s+of)\s+(?:a\s+period\s+of\s+)?\d{1,3}",
                "return": r"return\s+or\s+destroy|destro\w+|return\s+confidential",
                "no_licence": r"no\s+licen[cs]e\s+is\s+granted|no\s+licen[cs]e\s+or\s+other\s+right",
                "injunctive": r"injunctive\s+relief|equitable\s+relief",
                "at_will": r"at[-\s]?will",
                "duties": r"duties\s+(?:customarily|of\s+the\s+role|set\s+out)",
                "compensation": r"(?:base\s+)?salary|compensation\s+of|hourly\s+rate",
                "kill_fee": r"kill\s+fee|cancellation\s+fee|pay\s+for\s+work\s+completed",
                "portfolio": r"portfolio|case\s+stud",
                "deposit": r"security\s+deposit",
                "maintenance": r"repair|maintenance",
                "entry": r"right\s+of\s+entry|enter\s+the\s+premises|entry\s+notice",
                "rent": r"monthly\s+rent|rent\s+of",
                "data_export": r"export\s+(?:your\s+|the\s+)?data|data\s+export|return\s+[^.]{0,40}data",
                "renewal": r"renew\w*[^.]{0,80}(?:notice|price|fee)",
                "suspension": r"suspend\w*[^.]{0,80}(?:non[-\s]?payment|overdue|notice)",
                "order_of_precedence": r"order\s+of\s+precedence|conflict[^.]{0,80}prevail",
            }[key]
        else:
            marker = {
                "liability_cap": r"limitation\s+of\s+liability|shall\s+not\s+exceed|maximum\s+liability",
                "termination": r"terminat\w+",
                "ip_ownership": r"intellectual\s+property|work\s+made\s+for\s+hire|assign\w*\s+(?:all\s+)?(?:right|title)",
                "acceptance": r"acceptance|accepted|deemed\s+accepted",
                "data_protection": r"data\s+protection|personal\s+data|security\s+measures|data\s+processing",
                "governing_law": r"governing\s+law|governed\s+by\s+the\s+laws",
                "notices": r"notices?\s+shall\s+be|notice\s+address|written\s+notice\s+to",
                "survival": r"surviv\w+",
                "confidentiality": r"confidential\w+",
                "scope_deliverables": r"deliverables?|scope\s+of\s+work|services",
                "change_control": r"change\s+(?:order|control|request)",
                "payment_terms": r"net\s+\d{1,3}|payable\s+within|invoice",
                "term_renewal": r"term\s+of|initial\s+term|effective\s+date",
                "entire_agreement": r"entire\s+agreement|supersedes",
                "sla": r"uptime|service\s+level|service\s+credit",
                "non_compete": r"non[-\s]?compete|non[-\s]?solicit",
            }.get(key)
        if marker and re.search(marker, ctx.text, re.I):
            continue
        out.append({
            "key": key,
            "label": label,
            "axis": axis,
            "why": why,
            "suggested": suggested,
        })
    return out


def run_probes(ctx):
    """Run every applicable probe and return the findings list."""
    findings = []
    for spec in PROBES:
        if spec["perspectives"] and ctx.perspective not in spec["perspectives"]:
            continue
        try:
            res = spec["fn"](ctx)
        except Exception:  # a broken probe must never take down the review
            res = None
        if not res:
            continue
        findings.extend(_make(ctx, spec, res))

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}
    findings.sort(key=lambda f: (order.get(f["severity"], 5), -f["impact"], f["title"]))
    for i, f in enumerate(findings, 1):
        f["id"] = "F-{0:02d}".format(i)
    return findings
