"""Built-in sample contracts for Clause Lens.

These are the five shapes of agreement that come up most often. They exist so
the engine can be calibrated against known-good and known-bad documents.
"""

SAMPLES = [
    {
        "id": "vendor-msa-one-sided",
        "name": "Vendor MSA written for the vendor",
        "contract_type": "msa",
        "perspective": "client",
        "blurb": "The classic one-sided master agreement. Everything runs the supplier's way.",
        "text": """MASTER SERVICES AGREEMENT

This Master Services Agreement (the "Agreement") is entered into as of January 15, 2026 by and between Northwind Analytics LLC ("Provider") and Lakeside Retail Group ("Client").

1. SERVICES. Provider shall perform the services described in one or more statements of work executed by the parties (each, an "SOW"). Provider determines the manner and means of performing the services.

2. TERM. The initial term of this Agreement is thirty-six (36) months and shall automatically renew for successive twelve (12) month renewal terms unless either party gives written notice at least thirty (30) days prior to the end of the then-current term.

3. FEES AND PAYMENT. Client shall pay Provider the fees set out in each SOW. Client shall remit payment within sixty (60) days of the invoice date. All fees are non-refundable and payable in advance for the full term. Provider may adjust fees upon each renewal upon thirty (30) days notice.

4. CHANGES. Any change to the scope of an SOW must be documented in writing and is subject to Provider's approval at its sole discretion. Additional work performed at Provider's request is billable at Provider's then-current rates.

5. TERMINATION. Client may terminate this Agreement for convenience upon ninety (90) days prior written notice. Provider may terminate immediately if Client fails to pay any undisputed amount when due.

6. OWNERSHIP. All deliverables, work product and all right, title and interest therein shall be assigned to and vest exclusively in Provider. Client retains no right, title or interest in any deliverables.

7. LICENCE. Client is granted a perpetual, irrevocable, royalty-free licence to use the deliverables for any purpose.

8. CONFIDENTIALITY. Each party shall keep the other party's Confidential Information in confidence and shall not disclose it to third parties, for a period of three (3) years.

9. INDEMNIFICATION. Client shall defend, indemnify and hold harmless Provider from and against any and all claims, losses and expenses arising out of Client's use of the deliverables or Client's breach of this Agreement. Provider shall have no obligation to indemnify Client.

10. LIABILITY. Provider shall not be liable for any indirect, incidental, special or consequential damages. Client's liability under this Agreement shall be unlimited and Client shall indemnify Provider against all damages Provider incurs.

11. WARRANTIES. The services are provided "as is" and Provider disclaims all warranties, express or implied, including any warranty of merchantability or fitness for a particular purpose.

12. ASSIGNMENT. Provider may assign this Agreement in connection with a merger or sale of assets without the prior written consent of Client.

13. GOVERNING LAW. This Agreement shall be governed by the laws of the State of Delaware and the parties consent to the exclusive jurisdiction of the courts of Wilmington, Delaware.

14. DISPUTES. Any dispute shall be resolved by binding arbitration administered in Wilmington, Delaware. Each party shall bear its own attorneys' fees. The parties waive any right to a jury trial.""",
    },
    {
        "id": "balanced-msa",
        "name": "Balanced mutual MSA",
        "contract_type": "msa",
        "perspective": "party",
        "blurb": "A well drafted mutual agreement. The control case.",
        "text": """MASTER SERVICES AGREEMENT

This Master Services Agreement (the "Agreement") is made effective as of February 1, 2026 between Meridian Studio LLC ("Provider") and Halcyon Brands Inc ("Client").

1. SERVICES AND STATEMENTS OF WORK. The parties shall perform the services described in mutually executed statements of work (each an "SOW"). Each SOW is incorporated into this Agreement. In the event of a conflict between this Agreement and an SOW, this Agreement governs except where the SOW expressly states otherwise.

2. TERM AND RENEWAL. The initial term is twelve (12) months from the Effective Date and renews automatically for successive twelve (12) month periods unless either party gives written notice of non-renewal at least sixty (60) days before the end of the then-current term.

3. FEES AND PAYMENT. Client shall pay the fees set out in each SOW. Undisputed invoices are payable within thirty (30) days of receipt. Late payments accrue interest at one percent (1%) per month on undisputed amounts. Client may withhold amounts it disputes in good faith provided it notifies Provider within ten (10) days and the parties work to resolve the dispute promptly.

4. CHANGES. Any change to the scope, deliverables, timeline or fees must be documented in a written change order signed by both parties before the additional work begins.

5. TERMINATION. Either party may terminate this Agreement for convenience on thirty (30) days written notice. Either party may terminate for material breach if the breach is not cured within fifteen (15) days of written notice. On termination, Client shall pay for services performed to date and Provider shall refund prepaid fees for the unused term within thirty (30) days.

6. DELIVERABLES AND ACCEPTANCE. Each SOW lists the deliverables. Client shall accept or reject each deliverable in writing within ten (10) business days of delivery, and a deliverable is accepted if no written rejection is given within that period.

7. INTELLECTUAL PROPERTY. Upon full payment, Provider assigns to Client all right, title and interest in the deliverables created specifically for Client. Each party warrants that it has the right to grant the rights it grants under this Agreement. Provider retains ownership of its pre-existing materials, tools, templates and general know-how, and grants Client a perpetual licence to use them as embedded in the deliverables.

8. CONFIDENTIALITY. Each party shall keep the other party's Confidential Information in confidence, use it only to perform this Agreement, and protect it with at least reasonable care. Confidential Information excludes information that is publicly available, already known to the receiving party, independently developed, or lawfully received from a third party. These obligations continue for five (5) years after disclosure, and indefinitely for trade secrets.

9. INDEMNIFICATION. Each party shall defend, indemnify and hold harmless the other from third-party claims arising from its own negligence, breach of this Agreement, or infringement of intellectual property rights by its own materials.

10. WARRANTY. Provider warrants that the services will be performed in a professional and workmanlike manner and will materially conform to the applicable SOW. Provider does not warrant that the services will be uninterrupted or error free.

11. LIMITATION OF LIABILITY. Except for fraud, wilful misconduct, breach of confidentiality, or infringement of intellectual property rights, each party's aggregate liability under this Agreement shall not exceed the fees paid or payable in the twelve (12) months preceding the event giving rise to the claim. Neither party is liable for indirect or consequential damages.

12. DATA PROTECTION. Where Provider processes personal data on Client's behalf, the parties shall comply with applicable data protection law. Provider shall encrypt personal data at rest and in transit and notify Client of any security incident within forty-eight (48) hours.

13. INSURANCE. Provider shall maintain commercial general liability insurance of not less than one million dollars ($1,000,000) per occurrence.

14. ASSIGNMENT. Neither party may assign this Agreement without the other's prior written consent, except to a successor in connection with a merger or sale of substantially all assets, provided the assignee is not a competitor.

15. GOVERNING LAW. This Agreement is governed by the laws of the State of New York. The parties submit to the exclusive jurisdiction of the state and federal courts located in New York County.

16. NOTICES. Notices under this Agreement shall be in writing and delivered by email to the addresses named in the signature block, and are deemed received on the next business day.

17. COMPLIANCE. Each party shall comply with all applicable laws, including anti-bribery and export control laws.

18. GENERAL. This Agreement is the entire agreement between the parties and supersedes prior discussions. Any amendment must be in writing and signed by both parties. Clauses concerning confidentiality, intellectual property, indemnification, payment, limitation of liability and dispute resolution survive termination. If any provision is unenforceable, it will be modified to the minimum extent necessary and the remaining provisions stay in force. This Agreement may be executed in counterparts and by electronic signature.""",
    },
    {
        "id": "nda-with-residuals",
        "name": "NDA with residuals and one-way duties",
        "contract_type": "nda",
        "perspective": "party",
        "blurb": "A mutual NDA that quietly lets one side keep whatever it remembers.",
        "text": """MUTUAL NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement is entered into as of March 3, 2026 between Brightline Robotics Inc ("Company") and Alder & Finch Ltd ("Advisor").

1. PURPOSE. The parties wish to explore a potential commercial relationship (the "Purpose") and may disclose confidential information to each other.

2. CONFIDENTIAL INFORMATION. Confidential Information means non-public information disclosed by one party to the other that is identified as confidential or that reasonably should be understood to be confidential given its nature.

3. OBLIGATIONS. Company shall hold all Confidential Information of Advisor in confidence and shall not disclose it to any third party. Advisor may use information disclosed by Company for any purpose, including to develop its own products, without restriction.

4. RESIDUALS. Advisor retains the right to use information retained in the unaided memory of its personnel, including information relating to Company's products and technical approach.

5. TERM. These obligations continue for one (1) year from the date of disclosure.

6. RETURN OF MATERIALS. On request, each party shall return or destroy Confidential Information within thirty (30) days.

7. NO LICENCE. Nothing in this Agreement grants any licence or other right under any intellectual property right except as expressly stated in writing.

8. REMEDIES. The parties agree that damages alone may not be an adequate remedy for breach of this Agreement.

9. GOVERNING LAW. This Agreement is governed by the laws of the State of California.""",
    },
    {
        "id": "saas-subscription",
        "name": "SaaS subscription with a silent renewal",
        "contract_type": "saas",
        "perspective": "client",
        "blurb": "The subscription that renews before you remember it.",
        "text": """SUBSCRIPTION AGREEMENT

This Subscription Agreement is made effective as of April 1, 2026 between Nimbus Analytics, Inc. ("Provider") and Harbor Logistics Corp ("Customer").

1. SUBSCRIPTION. Provider grants Customer a non-exclusive, non-transferable right to access the hosted analytics service during the Subscription Term.

2. TERM AND RENEWAL. The Subscription Term is twelve (12) months beginning on the Effective Date and renews automatically for successive twelve (12) month renewal terms unless Customer delivers written notice of non-renewal at least thirty (30) days before the then-current term ends. Provider may increase the fees payable at each renewal.

3. FEES AND PAYMENT. The subscription fee is $2,400 per month, payable in advance on the first day of each month. Overdue amounts accrue interest at two percent (2%) per month. Provider may suspend access to the Service for non-payment without further notice.

4. SUPPORT AND AVAILABILITY. Provider will use commercially reasonable efforts to make the Service available. Service credits are provided at Provider's discretion.

5. CUSTOMER DATA. Customer Data remains Customer's property. Provider may use Customer Data to improve and market its products and services.

6. CONFIDENTIALITY. Each party shall protect the other party's Confidential Information for three (3) years from disclosure.

7. INDEMNIFICATION. Customer shall defend, indemnify and hold harmless Provider from any third-party claim arising out of Customer's use of the Service or Customer's breach of this Agreement.

8. LIMITATION OF LIABILITY. Provider's aggregate liability shall not exceed the fees paid by Customer in the one (1) month preceding the event giving rise to the claim. No limitation of liability applies to a party's confidentiality obligations, data protection obligations or indemnification obligations, and neither party is liable for indirect or consequential damages.

9. TERMINATION. Either party may terminate this Agreement if the other party materially breaches and fails to cure within thirty (30) days of written notice. Fees paid for the remainder of the then-current term are non-refundable.

10. ASSIGNMENT. Provider may assign this Agreement without Customer's consent in connection with a merger, sale of assets or change of control.

11. NOTICES. Notices shall be in writing and delivered to the addresses set out in the order form.

12. GOVERNING LAW. This Agreement is governed by the laws of the State of Delaware, and the parties submit to the exclusive jurisdiction of the courts of Wilmington, Delaware.""",
    },
    {
        "id": "freelance-creator",
        "name": "Freelance creator agreement",
        "contract_type": "freelance",
        "perspective": "vendor",
        "blurb": "A decent freelance contract with a missing acceptance step.",
        "text": """FREELANCE SERVICES AGREEMENT

This Freelance Services Agreement is made as of May 12, 2026 between Wren Studio ("Freelancer") and Tidewater Coffee Co ("Client").

1. SERVICES. Freelancer shall design and deliver the brand identity package described in Exhibit A, including logo files, colour palette, typography guidance and a 30-page brand guide.

2. FEES AND PAYMENT. Client shall pay Freelancer $6,000, invoiced 50 percent on signing and 50 percent on delivery. Invoices are payable within thirty (30) days of receipt. Overdue invoices accrue interest at one percent (1%) per month.

3. REVISIONS. Deliverables include two (2) rounds of reasonable revisions. Additional rounds are billed at $150 per hour.

4. ACCEPTANCE. Deliverables are considered final when Client issues written approval.

5. CANCELLATION. If Client cancels the project, Client shall pay for work completed to date plus a kill fee of fifty percent (50%) of the remaining balance.

6. INTELLECTUAL PROPERTY. Upon receipt of full payment, Freelancer assigns to Client all right, title and interest in the final deliverables. Freelancer retains ownership of its pre-existing materials, tools and general know-how, and grants Client a perpetual licence to use those materials as embedded in the deliverables.

7. PORTFOLIO. Freelancer may display the final work in a portfolio and in case studies after the project has launched publicly, provided Client approval is requested before publication.

8. CONFIDENTIALITY. Each party shall keep the other party's Confidential Information in confidence for two (2) years and shall not use it except to perform this Agreement.

9. WARRANTIES. Freelancer warrants that the deliverables are original work and that Freelancer owns the rights granted under this Agreement.

10. LIMITATION OF LIABILITY. Each party's aggregate liability shall not exceed the fees paid under this Agreement. Neither party is liable for indirect or consequential damages.

11. TERMINATION. Either party may terminate this Agreement for convenience on thirty (30) days written notice. On termination, Client shall pay for all work completed and accepted to date.

12. INDEPENDENT CONTRACTOR. Freelancer is an independent contractor and is responsible for all taxes on amounts paid under this Agreement.

13. GOVERNING LAW. This Agreement is governed by the laws of the State of Oregon and the parties submit to the exclusive jurisdiction of the courts of Multnomah County, Oregon.

14. GENERAL. This Agreement is the entire agreement between the parties. Any amendment must be in writing and signed by both parties. Clauses concerning confidentiality, intellectual property, payment and dispute resolution survive termination. If any provision is unenforceable it shall be modified to the minimum extent necessary. This Agreement may be executed electronically.""",
    },
]


def by_id(sample_id):
    for s in SAMPLES:
        if s["id"] == sample_id:
            return s
    return None
