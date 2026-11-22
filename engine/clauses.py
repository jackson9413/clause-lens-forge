"""Clause taxonomy and detection for Clause Lens.

Standard library only. Detection is pattern based: every clause type owns a
list of regular expressions. A clause counts as present when any pattern hits.
Evidence snippets are the sentences that contain the hit, so a reviewer can
always see the wording that triggered a finding.
"""

import re
from dataclasses import dataclass, field

AXIS_KEYS = ("financial", "exit", "ip", "risk", "completeness")


@dataclass
class ClauseSpec:
    key: str
    label: str
    axis: str
    patterns: list
    description: str = ""


@dataclass
class Clause:
    key: str
    label: str
    axis: str
    description: str
    present: bool = False
    snippets: list = field(default_factory=list)

    @property
    def count(self):
        return len(self.snippets)

    def to_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "axis": self.axis,
            "description": self.description,
            "present": self.present,
            "count": self.count,
            "snippets": self.snippets,
        }


CLAUSE_SPECS = [
    ClauseSpec(
        "parties", "Parties & effective date", "completeness",
        [r"\bthis\s+(?:agreement|contract)\b[^.]{0,60}\bbetween\b",
         r"\beffective\s+date\b", r"\bdated\s+as\s+of\b", r"\bas\s+of\s+the\s+date\b",
         r"\bhereinafter\b", r"\bmade\s+as\s+of\b"],
        "Who is bound and from when.",
    ),
    ClauseSpec(
        "term_renewal", "Term, renewal & auto-renewal", "exit",
        [r"\bauto[-\s]?renew\w*", r"\brenews?\s+automatically", r"\brenewal\s+term\b",
         r"\binitial\s+term\b", r"\bcommencement\s+date\b", r"\bsubscription\s+term\b",
         r"\bshall\s+renew\b"],
        "How long the deal lasts and whether it rolls over.",
    ),
    ClauseSpec(
        "termination", "Termination", "exit",
        [r"\bterminat(?:e|ion|ing)\b", r"\bend\s+the\s+agreement\b",
         r"\bnotice\s+of\s+termination\b"],
        "How you get out, on what notice, and for what.",
    ),
    ClauseSpec(
        "payment_terms", "Fees & payment terms", "financial",
        [r"\bnet\s+\d{1,3}\b", r"\binvoice\b", r"\bpayment\s+terms\b",
         r"\bpayable\s+within\b", r"\bmonthly\s+(?:fee|charge|subscription)\b",
         r"\bfees?\s+(?:of|shall|will)\b", r"\bbilling\b"],
        "When money moves, and how much.",
    ),
    ClauseSpec(
        "liability_cap", "Limitation of liability", "risk",
        [r"\blimitation\s+of\s+liability\b",
         r"\bliability[^.]{0,40}(?:shall\s+not\s+exceed|be\s+limited|capped\s+at)\b",
         r"\bmaximum\s+(?:aggregate\s+)?liability\b", r"\bin\s+no\s+event\s+shall\b",
         r"\bliability\s+cap\b"],
        "The ceiling on what you can be sued for.",
    ),
    ClauseSpec(
        "indemnification", "Indemnification", "risk",
        [r"\bindemnif\w+\b", r"\bhold\s+harmless\b", r"\bdefend\s+and\s+indemnify\b",
         r"\bassume\s+all\s+liabilit"],
        "Who pays when a third party sues.",
    ),
    ClauseSpec(
        "ip_ownership", "Intellectual property ownership", "ip",
        [r"\bintellectual\s+property\b", r"\bwork\s+made\s+for\s+hire\b",
         r"\ball\s+rights?,\s*title\s+and\s+interest\b", r"\bcopyright\b",
         r"\bownership\s+of\s+deliverables?\b"],
        "Who owns the work that gets made.",
    ),
    ClauseSpec(
        "license_grant", "Licence grants", "ip",
        [r"\blicen[cs]e\b", r"\bgrants?\b[^.]{0,40}\blicen[cs]e\b", r"\broyalty[-\s]?free\b",
         r"\bnon[-\s]?exclusive\s+licen[cs]e\b"],
        "Rights you grant beyond ownership.",
    ),
    ClauseSpec(
        "confidentiality", "Confidentiality", "ip",
        [r"\bconfidential(?:ity|\s+information)?\b", r"\bnon[-\s]?disclosure\b",
         r"\bproprietary\s+information\b", r"\bnda\b",
         r"\bnon[-\s]?use\b"],
        "What stays secret and for how long.",
    ),
    ClauseSpec(
        "non_compete", "Non-compete & non-solicit", "risk",
        [r"\bnon[-\s]?compete\b", r"\bnon[-\s]?solicit\w*\b",
         r"\brestrictive\s+covenant\b", r"\bcompetitive\s+business\b",
         r"\bnot\s+(?:to\s+)?engage\s+in\b"],
        "Limits on what you can do afterwards.",
    ),
    ClauseSpec(
        "exclusivity", "Exclusivity", "risk",
        [r"\bexclusiv\w+\b", r"\bnon[-\s]?exclusiv\w+\b", r"\bsole\s+(?:provider|distributor|agent)\b"],
        "Whether you must or must not work with others.",
    ),
    ClauseSpec(
        "warranty", "Warranties & disclaimers", "risk",
        [r"\bwarrant(?:y|ies|ant)\b", r"\bas\s+is\b", r"\bdisclaim\w+\b",
         r"\bno\s+warrant\w+\b"],
        "What is guaranteed about the work.",
    ),
    ClauseSpec(
        "governing_law", "Governing law & venue", "risk",
        [r"\bgoverning\s+law\b", r"\bgoverned\s+by\s+the\s+laws\b",
         r"\bexclusive\s+jurisdiction\b", r"\bvenue\s+(?:shall|will)\b",
         r"\bcourts?\s+of\b"],
        "Which law and which courtroom.",
    ),
    ClauseSpec(
        "dispute_resolution", "Dispute resolution", "risk",
        [r"\barbitrat\w+\b", r"\bjury\s+trial\b", r"\bmediation\b",
         r"\bdispute\s+resolution\b", r"\bclass\s+action\b",
         r"\bwaiv\w+[^.]{0,30}\bjury\b", r"\bbinding\s+arbitration\b"],
        "Where disputes go and what they cost.",
    ),
    ClauseSpec(
        "force_majeure", "Force majeure", "completeness",
        [r"\bforce\s+majeure\b", r"\bact\s+of\s+god\b", r"\bact\s+of\s+war\b"],
        "Excuses for not performing.",
    ),
    ClauseSpec(
        "assignment", "Assignment & change of control", "exit",
        [r"\bassign(?:ment|able)?\b", r"\bchange\s+of\s+control\b",
         r"\bmerger\s+or\s+sale\s+of\s+assets\b", r"\bsuccessor\s+and\s+assign"],
        "Who can take over the contract.",
    ),
    ClauseSpec(
        "notices", "Notices", "completeness",
        [r"\bnotices?\s+shall\s+be\s+(?:given|delivered|sent|in\s+writing)\b",
         r"\bwritten\s+notice\s+to\b", r"\bnotice\s+address\b",
         r"\baddress\s+for\s+notices\b"],
        "How formal notice is delivered.",
    ),
    ClauseSpec(
        "insurance", "Insurance", "risk",
        [r"\binsurance\b", r"\bcertificate\s+of\s+insurance\b",
         r"\bcommercial\s+general\s+liability\b"],
        "Proof that risk is covered.",
    ),
    ClauseSpec(
        "data_protection", "Data protection & security", "risk",
        [r"\bdata\s+protection\b", r"\bpersonal\s+data\b", r"\bgdpr\b",
         r"\bsecurity\s+measures\b", r"\bdata\s+processing\b",
         r"\bprivacy\s+policy\b", r"\bsub[-\s]?processor\b"],
        "Handling of customer or personal data.",
    ),
    ClauseSpec(
        "publicity", "Publicity & name use", "ip",
        [r"\bpublicity\b", r"\buse\s+of\s+(?:your\s+|the\s+)?name\b",
         r"\bportfolio\b", r"\bpress\s+release\b", r"\bcase\s+stud\w+\b",
         r"\bmarketing\s+materials?\b"],
        "Whether your name or work can be used to sell.",
    ),
    ClauseSpec(
        "sla", "Service levels & credits", "risk",
        [r"\buptime\b", r"\bservice\s+level\w*\b", r"\bservice\s+credit\w*\b",
         r"\bsla\b", r"\bresponse\s+time\w*\b", r"\bsupport\s+response\b"],
        "The performance promise and what happens if it is missed.",
    ),
    ClauseSpec(
        "scope_deliverables", "Scope & deliverables", "completeness",
        [r"\bdeliverables?\b", r"\bscope\s+of\s+(?:work|services)\b",
         r"\bstatement\s+of\s+work\b", r"\bservices?\s+include\b",
         r"\bmilestones?\b", r"\bwork\s+product\b"],
        "What you are actually buying or doing.",
    ),
    ClauseSpec(
        "acceptance", "Acceptance & review", "completeness",
        [r"\bacceptance\b", r"\bapproval\s+of\s+(?:deliverables?|work)\b",
         r"\breview\s+period\b", r"\bacceptance\s+criteria\b",
         r"\bshall\s+not\s+be\s+deemed\s+accepted\b"],
        "How work is judged and when it is locked in.",
    ),
    ClauseSpec(
        "change_control", "Change control", "completeness",
        r"\bchange\s+(?:order|control|request)s?\b".split("|"),
        "How scope changes are priced and agreed.",
    ),
    ClauseSpec(
        "survival", "Survival", "completeness",
        [r"\bsurviv\w+\b", r"\bshall\s+survive\b", r"\boutlive\b"],
        "Which obligations outlive the contract.",
    ),
    ClauseSpec(
        "entire_agreement", "Entire agreement & amendments", "completeness",
        [r"\bentire\s+agreement\b", r"\bsupersedes?\b", r"\bamendment\w*\b",
         r"\bmodifications?\s+must\s+be\s+in\s+writing\b"],
        "What the final document replaces.",
    ),
    ClauseSpec(
        "boilerplate", "Miscellaneous boilerplate", "completeness",
        [r"\bseverab\w+\b", r"\bcounterparts\b", r"\belectronic\s+signatures?\b",
         r"\bheadings\b", r"\bagencies\b", r"\bno\s+third[-\s]party\s+beneficiaries\b"],
        "Standard closing legal language.",
    ),
    ClauseSpec(
        "compliance", "Compliance with law", "risk",
        [r"\bcomply\s+with\s+(?:all\s+)?applicable\s+law\w*\b",
         r"\banti[-\s]?bribery\b", r"\bsanctions\b", r"\bexport\s+control\w*\b",
         r"\bexport\s+sanction\w*\b", r"\bfcpa\b", r"\bgdpr\b"],
        "Obligations to obey the law.",
    ),
]

# the change_control spec above needs real regexes
for _spec in CLAUSE_SPECS:
    if _spec.key == "change_control":
        _spec.patterns = [r"\bchange\s+(?:order|control|request)s?\b",
                          r"\bscope\s+change\w*\b",
                          r"\badditional\s+work\s+require\w*\b"]


def split_sentences(text):
    """Split text into (start, end, sentence) triples."""
    out = []
    for m in re.finditer(r"[^.!?\n]+[.!?]?", text):
        chunk = m.group(0)
        if chunk.strip():
            out.append((m.start(), m.end(), chunk.strip()))
    return out


def sentences_matching(text, pattern):
    """Return the sentences that match a regex (case insensitive)."""
    rx = pattern if isinstance(pattern, str) else "|".join(pattern)
    return [s for _, _, s in split_sentences(text) if re.search(rx, s, re.I)]


def _sentence_for(sentences, position):
    for start, end, body in sentences:
        if start <= position < end:
            return body
    return None


def detect_clauses(text, contract_type="generic"):
    """Detect which clause types are present in the contract text."""
    text = text or ""
    sentences = split_sentences(text)
    clauses = []
    for spec in CLAUSE_SPECS:
        snippets = []
        for pat in spec.patterns:
            for m in re.finditer(pat, text, re.I):
                snippet = _sentence_for(sentences, m.start())
                if snippet and snippet not in snippets:
                    snippets.append(snippet)
                if len(snippets) >= 3:
                    break
            if len(snippets) >= 3:
                break
        clauses.append(
            Clause(spec.key, spec.label, spec.axis, spec.description, bool(snippets), snippets)
        )
    return clauses


def text_stats(text):
    text = text or ""
    sentences = split_sentences(text)
    words = re.findall(r"[\w'$-]+", text)
    headings = re.findall(r"^\s*(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.|ARTICLE\s+\w+)\s+\S", text, re.M)
    return {
        "characters": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
        "headings": len(headings),
        "average_sentence_words": round(len(words) / len(sentences), 1) if sentences else 0,
    }
