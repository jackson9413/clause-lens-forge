# Clause Lens

A local-first contract clause reviewer. Paste an agreement and it reads the clauses that
actually decide what happens when things go wrong: the liability cap, the termination notice,
the renewal window, who owns the work, what happens to the money when you leave early.

It scores the contract out of 100, shows you the exact wording behind every finding, lists the
clauses that are missing for the type of contract you pasted, works out the dates you need to
diarise, ranks what to negotiate first, and drafts the email asking for the changes.

Everything runs on your machine. No API keys, no external services, no LLM, no telemetry.
The contract text never leaves the process.

## Why it exists

People sign agreements they have not read carefully, and then discover the important part was
in clause 14. The clauses that cause the most damage are a short, predictable list: an absent
liability cap, a one-way indemnity, auto-renewal with a 30 day notice window, IP assignment
with no carve-out for the tools you already owned.

Clause Lens checks for that list, shows the evidence, and tells you what to say about it.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open http://127.0.0.1:5057

The database is created automatically at data/reviews.db. Override it with the
`CLAUSE_LENS_DB` environment variable. Port and host come from `PORT` and `HOST`.

## Command line

The same engine from a terminal, which is handy for a contract file you already have:

```bash
python3 cli.py contract.txt --type msa --perspective client
python3 cli.py contract.txt --markdown review.md --calendar deadlines.ics
python3 cli.py --sample vendor-msa-one-sided
python3 cli.py contract.txt --quiet
```

## What it checks

Roughly fifty rules across five axes. Each one carries the sentence that triggered it, why it
matters, a concrete fix and a fallback position.

| Axis | Weight | What it looks at |
| --- | --- | --- |
| Financial terms | 20% | Payment window, late interest, prepayments, uncapped price rises, early exit fees |
| Exit & flexibility | 20% | Termination rights, notice periods, auto-renewal, assignment on a sale, suspension |
| IP & confidentiality | 20% | IP assignment and carve-outs, licence grants, confidentiality term, residuals, survival |
| Risk allocation | 25% | Liability caps and carve-outs, indemnity, warranties, governing law, arbitration, non-competes |
| Completeness & balance | 15% | Acceptance criteria, order of precedence, unfilled blanks, notices, survival |

### Structural caps

Some problems are not a matter of degree. A contract with no termination clause cannot score
above 55 even if everything else is perfect, because the missing exit dominates everything
that follows. The same applies to a missing liability cap, an IP assignment with no carve-out,
and auto-renewal with no usable notice window. When a cap applies, the UI says so and why.

### Negotiation order

Findings are ranked by severity, by how much damage they do if left alone (impact) and by how
likely the other side is to move (leverage). The draft reply takes the top five and turns them
into numbered asks, each with the wording to propose and a fallback if the ask is refused.

### Missing clauses

Each contract type has its own checklist of clauses that should be there. An NDA is checked for
exclusions, term, return or destruction and no implied licence. A lease is checked for rent,
deposit, maintenance, entry notice and subletting. Missing clauses come with suggested wording
you can paste in.

### Dates

The effective date, the end of the term, the notice deadline for stopping a renewal, the first
invoice date and the end of the confidentiality period are extracted and can be exported as an
.ics file to drop into a calendar.

## Built-in samples

Five contracts that are calibrated against known answers:

| Sample | Score | Verdict |
| --- | --- | --- |
| Vendor MSA written for the vendor | 40.5 | high risk |
| Balanced mutual MSA | 99.1 | ready to sign |
| NDA with residuals and one-way duties | 50.0 | negotiate |
| SaaS subscription with a silent renewal | 69.0 | negotiate |
| Freelance creator agreement | 85.4 | ready to sign |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | / | the interface |
| GET | /api/health | liveness check |
| GET | /api/meta | contract types, perspectives, sample list |
| POST | /api/review | review a contract, returns the full report |
| GET | /api/samples/{id} | fetch a built-in sample |
| GET | /api/history | list past reviews |
| POST | /api/history/{id} | save a 1-5 rating and a note |
| DELETE | /api/history/{id} | delete a review |
| GET | /api/export/{id}?format=md\|json\|ics | export a stored review |

## Tests

```bash
python3 -m pytest tests -q
```

40 tests covering the detection rules, the scoring caps, date extraction, the calendar export
and the API.

## Layout

```
clause-lens-forge/
├── app.py              Flask routes and JSON API
├── cli.py              command line front end
├── db.py               SQLite log of past reviews
├── engine/
│   ├── clauses.py      clause taxonomy and detection
│   ├── rules.py        the risk probes and the missing-clause library
│   ├── scoring.py      axes, structural caps, verdicts
│   ├── deadlines.py    date extraction and .ics export
│   ├── plan.py         negotiation order and draft reply
│   └── samples.py      the five built-in samples
├── static/             the interface
└── tests/              engine and API tests
```

## Limits

This is not legal advice and it is not a lawyer. It reads the document, not your situation: it
does not know your jurisdiction, your leverage, what the deal is worth to you, or what the
other side will actually accept. Restrictive covenants and indemnity terms are enforced
differently in different places. Use it to find the clauses worth a phone call, and take those
to someone who can advise properly.
