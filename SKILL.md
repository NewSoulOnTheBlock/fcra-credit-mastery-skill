---
name: fcra-credit-mastery
description: Comprehensive knowledge of the Fair Credit Reporting Act (FCRA), Equal Credit Opportunity Act (ECOA), US credit system mechanics, credit score optimization, dispute strategies, and credit building tactics for both personal AND business credit. Use when advising on credit building, analyzing credit reports, disputing errors, understanding consumer credit rights, planning credit improvement strategies, building authorized user strategies, building business credit for entrepreneurs, setting up vendor trade lines, understanding business credit bureaus (D&B PAYDEX, Experian Business, Equifax Business), SBA loan eligibility, ECOA anti-discrimination protections, or designing an autonomous credit-building agent. Covers FICO scoring, VantageScore, Regulation B, the three consumer bureaus, three business bureaus, furnisher obligations, certified mail automation via Lob API, and actionable credit repair workflows.
---

# FCRA & Credit Mastery

Complete foundation for understanding and leveraging the US credit system. Designed as the knowledge base for building an autonomous credit-building agent.

## The Credit System — How It Actually Works

### Three Players
1. **Consumer Reporting Agencies (CRAs/Bureaus):** Equifax, Experian, TransUnion — collect and sell your credit data
2. **Furnishers:** Creditors (banks, card companies, lenders) who report your account data to bureaus
3. **Users:** Companies that pull your report to make decisions (lenders, landlords, employers, insurers)

### What's In a Credit Report
- **Identifying info:** Name, SSN, DOB, addresses, employers
- **Trade lines:** Every credit account — type, open date, limit, balance, payment history
- **Inquiries:** Hard pulls (affect score) and soft pulls (don't)
- **Public records:** Bankruptcies (removed after 10 years), civil judgments
- **Collections:** Unpaid debts sold to collectors

### What's NOT In a Credit Report
- Income, bank balances, investments
- Race, religion, gender, marital status, national origin
- Criminal record (separate background check)
- Medical information (with limited exceptions)

## FICO Score Breakdown (300–850)

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Payment History | 35% | On-time payments, late payments, delinquencies, collections, bankruptcies |
| Amounts Owed (Utilization) | 30% | Credit utilization ratio, total balances, number of accounts with balances |
| Length of Credit History | 15% | Age of oldest account, average age of all accounts, age of newest account |
| Credit Mix | 10% | Variety: credit cards, installment loans, mortgage, auto, student loans |
| New Credit | 10% | Number of recent inquiries, recently opened accounts |

### Score Ranges
| Range | Rating | Impact |
|-------|--------|--------|
| 800–850 | Exceptional | Best rates on everything |
| 740–799 | Very Good | Excellent rates, easy approvals |
| 670–739 | Good | Approved for most products |
| 580–669 | Fair | Subprime rates, limited options |
| 300–579 | Poor | Secured cards only, high deposits required |

## FCRA — Your Legal Rights

Read `references/fcra-rights.md` for the full legal framework. Key rights:

1. **Right to know what's in your file** — free report from each bureau annually via AnnualCreditReport.com (currently weekly for free)
2. **Right to dispute inaccurate information** — bureaus must investigate within 30 days
3. **Right to have errors corrected or deleted** — if furnisher can't verify, it must be removed
4. **Right to know when your report is used against you** — adverse action notices required
5. **Right to consent for employment checks** — employer must get written permission
6. **Right to place fraud alerts and credit freezes** — free, no impact on score
7. **Right to sue for violations** — actual damages, statutory damages ($100–$1,000 per violation for willful), attorney's fees, punitive damages
8. **Negative info removal timelines:** Most negatives drop off after 7 years; bankruptcies after 10 years

## Credit Building Strategies

Read `references/credit-building-playbook.md` for detailed tactics. Summary:

### Phase 1: Foundation (Score 0–579 → 580–669)
- Open a **secured credit card** ($200–$500 deposit)
- Become an **authorized user** on a trusted person's old, high-limit, low-utilization card
- Open a **credit builder loan** (Self, MoneyLion, etc.)
- Set **all payments to autopay** — never miss a payment

### Phase 2: Acceleration (580–669 → 670–739)
- Keep utilization **under 30%** (ideal: under 10%)
- Request **credit limit increases** every 6 months (soft pull when possible)
- Add **1 new account** every 6–12 months for mix diversity
- Dispute **every inaccuracy** on all three reports
- Use **Experian Boost** for utility/streaming payment credit

### Phase 3: Optimization (670–739 → 740+)
- **AZEO strategy:** All Zero Except One — pay all cards to $0, leave one with small balance reporting
- Keep **oldest accounts open** indefinitely (cancel annual fee cards by product-changing to no-fee)
- **Backdate authorized user accounts** — old accounts with perfect history
- Minimize hard inquiries — rate shop within 14–45 day windows
- Let accounts **age** — stop opening new accounts

### Phase 4: Elite (740+ → 800+)
- Maintain **<5% utilization** across all cards
- Keep **zero late payments** for 24+ consecutive months
- Have **3+ account types** (revolving, installment, mortgage)
- Keep **average account age** above 7 years
- Only apply for credit when genuinely needed

## Dispute Workflow

Read `references/dispute-strategies.md` for templates and advanced tactics.

### Standard Dispute Process
1. Pull reports from all 3 bureaus (AnnualCreditReport.com)
2. Identify every error, inaccuracy, or unverifiable item
3. Send dispute letters via certified mail (creates paper trail)
4. Bureau has 30 days to investigate (45 if you provide additional info)
5. If furnisher can't verify → must be deleted
6. If dispute rejected → escalate to CFPB complaint
7. If CFPB fails → consult FCRA attorney (contingency, no upfront cost)

### What's Disputable
- Accounts that aren't yours
- Incorrect balances, limits, dates, or payment statuses
- Accounts reported past the 7-year statute
- Duplicate entries
- Hard inquiries you didn't authorize
- Incorrect personal information

## Agent Design Considerations

When building an autonomous credit-building agent:

### Data Inputs Needed
- User's current credit score (self-reported or via soft-pull API)
- Number and types of open accounts
- Current utilization percentage
- Negative items on report
- Monthly income (for DTI calculations)
- Credit goals and timeline

### Agent Actions
- Analyze current credit profile → identify weaknesses
- Generate prioritized action plan based on current phase
- Draft dispute letters for identified errors
- Recommend specific products (secured cards, credit builders)
- Set payment reminders and utilization alerts
- Track progress across scoring factors
- Advise on timing for applications (inquiry management)

### Rules for the Agent
- NEVER advise illegal credit repair tactics (CPN fraud, tradeline renting scams)
- ALWAYS recommend legitimate strategies only
- Disclose that agent provides education, not legal/financial advice
- Respect user's financial capacity — don't recommend accounts they can't maintain
- Prioritize payment history above all else (35% of score)

## Certified Mail Automation

The skill includes a complete Lob API integration for sending dispute letters as USPS Certified Mail with Return Receipt — programmatically.

**Script:** `scripts/certified_mail.py`

**Setup:**
```bash
pip install requests
export LOB_API_KEY="your_live_key"  # Get from dashboard.lob.com
```

**Python Usage:**
```python
from certified_mail import DisputeMailer

mailer = DisputeMailer()

# Send a basic bureau dispute to Equifax
result = mailer.send_dispute(
    client={"name": "John Doe", "address_line1": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701", "ssn_last4": "1234", "dob": "01/15/1990"},
    letter_type="basic_bureau",
    target="equifax",
    dispute_items=[{"account_name": "Chase", "account_number_last4": "5678", "reason": "Account shows 30-day late but was paid on time"}]
)

# Send same dispute to ALL 3 bureaus at once
results = mailer.send_to_all_bureaus(client, "basic_bureau", dispute_items)

# Check for overdue disputes (past 30-day deadline)
overdue = mailer.get_overdue_disputes()
```

**CLI Usage:**
```bash
# List all 19 letter types
python certified_mail.py types

# Send to one bureau
python certified_mail.py send --type basic_bureau --target equifax --name "John Doe" --address "123 Main St" --city Austin --state TX --zip 78701 --account Chase --reason "Wrong late payment"

# Send to all 3 bureaus
python certified_mail.py send-all --type basic_bureau --name "John Doe" --address "123 Main St" --city Austin --state TX --zip 78701

# Check pending disputes
python certified_mail.py pending

# Check overdue (ready for escalation)
python certified_mail.py overdue
```

**Cost:** ~$8-9 per letter (printing + certified mail + return receipt). No subscription.

**Features:**
- All 19 letter types with auto-populated HTML templates
- USPS Certified Mail with Return Receipt (legal proof of delivery)
- Address verification before sending
- Automatic 30-day deadline tracking
- Overdue detection for escalation triggers
- Delivery status monitoring via Lob tracking
- Batch send to all 3 bureaus in one call
- Local JSON dispute log for audit trail

## Business Credit (Entrepreneurs)

The skill includes a complete business credit building module covering:

- **Business credit bureaus:** D&B (PAYDEX), Experian Business (Intelliscore), Equifax Business
- **Entity foundation:** LLC formation, EIN, DUNS number, business bank account, NAP consistency
- **4-phase credit building:** Vendor credit → Store/fleet cards → Major business cards → No-PG lines of credit
- **Tier 1 vendor list:** 8+ vendors that extend Net-30 to new businesses and report to bureaus
- **No Personal Guarantee (No-PG) cards:** Brex, Ramp, Divvy — credit based on business financials only
- **SBA loans:** 7(a), 504, Microloan, Express programs
- **Equal Credit Opportunity Act (ECOA):** Full legal rights for business credit applicants, Regulation B coverage, anti-discrimination protections, adverse action rights, enforcement agencies
- **Timeline:** Zero to $100K+ in business credit in 12 months
- **Separation rules:** How to keep business and personal credit completely separate

Read `references/business-credit/BUSINESS-CREDIT.md` for the full guide.

## Resource Map

| Topic | Reference |
|-------|-----------|
| Full FCRA legal rights & sections | `references/fcra-rights.md` |
| Credit building playbook with timelines | `references/credit-building-playbook.md` |
| 19 dispute letter types with templates | `references/dispute-strategies.md` |
| Credit score myths & facts | `references/myths-and-facts.md` |
| Key contacts & resources | `references/resources.md` |
| Certified mail dispatch script | `scripts/certified_mail.py` |
| **Business credit full guide (ECOA)** | `references/business-credit/BUSINESS-CREDIT.md` |

Read references only when the task requires that specific depth.
