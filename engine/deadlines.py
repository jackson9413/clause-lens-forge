"""Deadline extraction and calendar export for Clause Lens.

The point of this module is the diary: renewal notice windows, term ends and
first payment dates are the dates people miss. They are pulled out of the text
and turned into real calendar entries.
"""

import re
from datetime import date, timedelta

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
MONTH_ALT = "|".join(MONTHS)


def _make_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_date(text):
    """Find the first date in a string. Returns a date or None."""
    if not text:
        return None
    m = re.search(r"\b(" + MONTH_ALT + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
                  text, re.I)
    if m:
        return _make_date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
    m = re.search(r"\b(\d{1,2})\s+(" + MONTH_ALT + r")\.?,?\s+(\d{4})\b", text, re.I)
    if m:
        return _make_date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if m:
        return _make_date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return _make_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _add_months(d, months):
    if d is None:
        return None
    total = (d.year * 12 + (d.month - 1)) + int(months)
    year, month = divmod(total, 12)
    month += 1
    day = d.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1
            if day < 1:
                return None


def effective_date(text):
    """The date the contract starts, if the document states one."""
    if not text:
        return None, None
    anchored = re.search(
        r"[^.\n]{0,80}?(?:effective\s+date|made\s+(?:effective|as\s+of)|dated\s+as\s+of|"
        r"as\s+of\s+the\s+date|commencement\s+date|dated\s+)[^.\n]{0,80}", text, re.I)
    if anchored:
        d = parse_date(anchored.group(0))
        if d:
            return d, anchored.group(0).strip()
    d = parse_date(text)
    if d:
        return d, "First date found in the document"
    return None, None


def extract_deadlines(ctx):
    """Build the diary of dates that matter for this contract."""
    out = []
    eff, eff_src = effective_date(ctx.text)
    if eff:
        out.append({
            "label": "Agreement effective",
            "date": eff.isoformat(),
            "source": eff_src,
            "note": "Start of the term. Every other date below is measured from here.",
        })

    months = ctx.flags.get("term_months")
    term_end = _add_months(eff, months) if (eff and months) else None
    if term_end:
        out.append({
            "label": "Initial term ends",
            "date": term_end.isoformat(),
            "source": "Term of {0} months".format(months),
            "note": "The agreement runs to this date unless terminated or renewed.",
        })
        if ctx.flags.get("auto_renew"):
            out.append({
                "label": "Auto-renewal date",
                "date": term_end.isoformat(),
                "source": "Auto-renewal language",
                "note": "The contract rolls over automatically on this date.",
            })
            notice = ctx.flags.get("renewal_notice_days")
            if notice:
                deadline = term_end - timedelta(days=notice)
                out.append({
                    "label": "Notice deadline to stop renewal",
                    "date": deadline.isoformat(),
                    "source": "{0} days notice required".format(notice),
                    "note": ("Write to them on or before this date. After it, the renewal "
                             "is locked in and you are committed to another term."),
                })

    net = ctx.flags.get("net_days")
    if eff and net:
        due = eff + timedelta(days=net)
        out.append({
            "label": "First invoice due",
            "date": due.isoformat(),
            "source": "Payment terms: net {0}".format(net),
            "note": "Working from the effective date. Check the actual invoice date.",
        })

    conf = ctx.flags.get("confidentiality_years")
    if eff and conf:
        end = _add_months(eff, int(round(conf * 12)))
        if end:
            out.append({
                "label": "Confidentiality obligations expire",
                "date": end.isoformat(),
                "source": "Confidentiality term of {0} year(s)".format(conf),
                "note": "After this date the duty to keep information secret ends.",
            })

    notice = ctx.flags.get("termination_notice_days")
    if eff and notice:
        out.append({
            "label": "Termination notice must be given by",
            "date": (eff + timedelta(days=notice)).isoformat(),
            "source": "{0} days termination notice".format(notice),
            "note": "A notice served later than this is not effective.",
        })

    seen = set()
    unique = []
    for d in out:
        key = (d["label"], d["date"])
        if key not in seen:
            seen.add(key)
            unique.append(d)
    unique.sort(key=lambda d: d["date"])
    return unique


def to_ics(deadlines, title="Clause Lens contract review"):
    """Render deadlines as a downloadable calendar file."""
    def esc(value):
        return (str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
                .replace("\n", "\\n"))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Clause Lens//Contract Deadlines//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    stamp = date.today().strftime("%Y%m%dT%H%M%SZ")
    for d in deadlines:
        try:
            start = date.fromisoformat(d["date"])
        except ValueError:
            continue
        end = start + timedelta(days=1)
        lines.append("BEGIN:VEVENT")
        lines.append("UID:{0}-{1}@clause-lens".format(
            start.strftime("%Y%m%d"), abs(hash(d["label"])) % 100000))
        lines.append("DTSTAMP:" + stamp)
        lines.append("DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"))
        lines.append("DTEND;VALUE=DATE:" + end.strftime("%Y%m%d"))
        lines.append("SUMMARY:" + esc("{0}: {1}".format(title, d["label"])))
        lines.append("DESCRIPTION:" + esc(d.get("note", "")))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
