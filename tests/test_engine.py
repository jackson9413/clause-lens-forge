"""Engine tests for Clause Lens."""

from datetime import date

import pytest

import engine
from engine.deadlines import parse_date, to_ics
from engine.rules import build_context, net_days, renewal_notice_days, term_months
from engine.scoring import verdict_for
from engine.samples import SAMPLES, by_id

BALANCED = by_id("balanced-msa")
ONE_SIDED = by_id("vendor-msa-one-sided")
NDA = by_id("nda-with-residuals")
SAAS = by_id("saas-subscription")
FREELANCE = by_id("freelance-creator")


def test_every_sample_reviews_cleanly():
    for s in SAMPLES:
        result = engine.review(s["text"], s["contract_type"], s["perspective"], s["name"])
        assert result["score"]["overall"] >= 0
        assert result["score"]["overall"] <= 100
        assert len(result["score"]["axes"]) == 5
        assert result["clauses"]
        assert isinstance(result["findings"], list)
        assert isinstance(result["counter_proposal"], str)


def test_balanced_control_case_scores_ready_to_sign():
    result = engine.review(BALANCED["text"], "msa", "party", BALANCED["name"])
    assert result["score"]["overall"] >= 85
    assert result["score"]["verdict"] == "ready_to_sign"
    critical = [f for f in result["findings"] if f["severity"] == "critical"]
    assert critical == []


def test_one_sided_contract_scores_badly_and_flags_the_big_things():
    result = engine.review(ONE_SIDED["text"], "msa", "client", ONE_SIDED["name"])
    assert result["score"]["overall"] < 60
    assert result["score"]["verdict"] in ("high_risk", "do_not_sign")
    titles = " | ".join(f["title"] for f in result["findings"])
    assert "No limitation of liability" in titles
    assert "Indemnity runs one way only" in titles


def test_missing_liability_cap_is_critical_and_caps_the_score():
    text = ("This Agreement is made as of January 1, 2026 between A and B. "
            "B shall provide services. A shall pay $1000 per month. "
            "Either party may terminate on 30 days notice.")
    result = engine.review(text, "msa", "client")
    findings = {f["title"]: f for f in result["findings"]}
    assert "No limitation of liability" in findings
    assert findings["No limitation of liability"]["severity"] == "critical"
    risk = [a for a in result["score"]["axes"] if a["key"] == "risk"][0]
    assert risk["score"] <= 25
    assert result["score"]["caps"]


def test_missing_termination_is_critical():
    text = ("This Agreement is made as of January 1, 2026 between A and B. "
            "B shall provide services and A shall pay $1000 per month within 30 days. "
            "Each party's liability shall not exceed the fees paid in the 12 months before the claim.")
    result = engine.review(text, "msa", "client")
    titles = [f["title"] for f in result["findings"]]
    assert "No termination clause" in titles
    exit_axis = [a for a in result["score"]["axes"] if a["key"] == "exit"][0]
    assert exit_axis["score"] <= 30


def test_net_days_extraction():
    assert net_days("Invoices are payable net 30.") == 30
    assert net_days("Client shall remit payment within sixty (60) days of the invoice date.") == 60
    assert net_days("Payment is due upon receipt.") is None


def test_renewal_notice_days_extraction():
    assert renewal_notice_days(
        "The term renews automatically unless notice is given at least sixty (60) days in advance.") == 60
    assert renewal_notice_days("This Agreement shall renew automatically each year.") is None


def test_term_months_extraction():
    assert term_months("The initial term is twelve (12) months from the Effective Date.") == 12
    assert term_months("The initial term of this Agreement is thirty-six (36) months.") == 36
    assert term_months("The term is governed by the schedules.") is None


def test_auto_renewal_with_short_notice_is_flagged():
    text = ("This Agreement is made as of January 1, 2026. The initial term is twelve (12) months "
            "and shall automatically renew for successive twelve (12) month periods unless notice "
            "is given at least thirty (30) days prior to the end of the term. "
            "Either party may terminate for convenience on 30 days notice. "
            "Each party's liability shall not exceed fees paid in the 12 months before the claim.")
    result = engine.review(text, "msa", "client")
    titles = [f["title"] for f in result["findings"]]
    assert "Auto-renewal with a short or missing notice window" in titles


def test_ip_assignment_without_carveout_is_flagged_but_with_carveout_is_not():
    without = ("All deliverables and all right, title and interest therein shall be assigned to Client. "
               "Client shall pay within 30 days. Either party may terminate on 30 days notice.")
    with_carveout = ("All deliverables shall be assigned to Client. Provider retains ownership of its "
                     "pre-existing materials and tools. Client shall pay within 30 days. "
                     "Either party may terminate on 30 days notice.")
    a = engine.review(without, "msa", "vendor")
    b = engine.review(with_carveout, "msa", "vendor")
    assert "All IP is assigned with no carve-out for what you already owned" in [f["title"] for f in a["findings"]]
    assert "All IP is assigned with no carve-out for what you already owned" not in [f["title"] for f in b["findings"]]


def test_one_way_indemnity_is_detected():
    text = ("Contractor shall defend, indemnify and hold harmless Client from any claims. "
            "Client shall pay within 30 days. Either party may terminate on 30 days notice.")
    result = engine.review(text, "msa", "vendor")
    assert "Indemnity runs one way only" in [f["title"] for f in result["findings"]]


def test_perspective_changes_the_severity_of_one_sided_termination():
    text = ("Client may terminate this Agreement for convenience upon thirty (30) days written notice. "
            "Client shall pay within 30 days. "
            "Each party's liability shall not exceed fees paid in the 12 months before the claim.")
    vendor = engine.review(text, "msa", "vendor")
    client = engine.review(text, "msa", "client")
    v = [f for f in vendor["findings"] if f["title"] == "Only the other party can terminate for convenience"]
    c = [f for f in client["findings"] if f["title"] == "Only the other party can terminate for convenience"]
    assert v and c
    assert v[0]["severity"] == "high"
    assert c[0]["severity"] == "low"


def test_parse_date_formats():
    assert parse_date("effective as of January 15, 2026") == date(2026, 1, 15)
    assert parse_date("dated 15 January 2026") == date(2026, 1, 15)
    assert parse_date("on 03/04/2026") == date(2026, 3, 4)
    assert parse_date("no dates in here") is None


def test_deadlines_include_renewal_notice_date():
    result = engine.review(SAAS["text"], "saas", "client", SAAS["name"])
    labels = [d["label"] for d in result["deadlines"]]
    assert "Agreement effective" in labels
    assert "Auto-renewal date" in labels
    assert "Notice deadline to stop renewal" in labels
    notice = [d for d in result["deadlines"] if d["label"] == "Notice deadline to stop renewal"][0]
    renewal = [d for d in result["deadlines"] if d["label"] == "Auto-renewal date"][0]
    assert date.fromisoformat(notice["date"]) < date.fromisoformat(renewal["date"])


def test_ics_export_is_valid_calendar_text():
    result = engine.review(SAAS["text"], "saas", "client", SAAS["name"])
    ics = to_ics(result["deadlines"], "Test")
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "DTSTART;VALUE=DATE:" in ics
    assert ics.count("BEGIN:VEVENT") == ics.count("END:VEVENT")


def test_markdown_export_contains_report_sections():
    result = engine.review(NDA["text"], "nda", "party", NDA["name"])
    md = engine.to_markdown(result)
    assert "# Contract review" in md
    assert "## Findings" in md
    assert "## Negotiation order" in md
    assert "## Draft reply" in md


def test_counter_proposal_contains_the_asks():
    result = engine.review(ONE_SIDED["text"], "msa", "client", ONE_SIDED["name"])
    draft = result["counter_proposal"]
    assert "Subject: Comments on the agreement" in draft
    assert "Please use:" in draft
    assert len(draft.splitlines()) > 10


def test_negotiation_plan_is_ordered_by_priority():
    result = engine.review(ONE_SIDED["text"], "msa", "client", ONE_SIDED["name"])
    plan = result["negotiation_plan"]
    assert plan
    scores = [p["priority_score"] for p in plan]
    assert scores == sorted(scores, reverse=True)
    assert plan[0]["rank"] == 1
    assert all(p["ask"] for p in plan)


def test_missing_clauses_depend_on_contract_type():
    nda = engine.review("A short agreement about a meeting.", "nda", "party")
    assert any(m["key"] == "confidentiality" for m in nda["missing"])
    lease = engine.review("A short agreement about a meeting.", "lease", "party")
    assert any(m["key"] == "rent" for m in lease["missing"])


def test_empty_text_does_not_crash():
    result = engine.review("", "msa", "client")
    assert result["score"]["overall"] >= 0
    assert result["findings"] == [] or isinstance(result["findings"], list)


def test_verdict_thresholds():
    assert verdict_for(95)["key"] == "ready_to_sign"
    assert verdict_for(75)["key"] == "light_touch"
    assert verdict_for(55)["key"] == "negotiate"
    assert verdict_for(40)["key"] == "high_risk"
    assert verdict_for(10)["key"] == "do_not_sign"


def test_scores_are_stable_across_runs():
    a = engine.review(ONE_SIDED["text"], "msa", "client", ONE_SIDED["name"])
    b = engine.review(ONE_SIDED["text"], "msa", "client", ONE_SIDED["name"])
    assert a["score"]["overall"] == b["score"]["overall"]
    assert len(a["findings"]) == len(b["findings"])


def test_context_flags_are_populated():
    ctx = build_context(SAAS["text"], "saas", "client")
    assert ctx.flags["auto_renew"] is True
    assert ctx.flags["term_months"] == 12
    assert ctx.flags["one_way_indemnity"] is True


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_each_sample_has_expected_shape(sample):
    result = engine.review(sample["text"], sample["contract_type"], sample["perspective"])
    assert result["meta"]["contract_type"] == sample["contract_type"]
    assert result["score"]["counts"]["critical"] >= 0
    assert result["negotiation_plan"] is not None
