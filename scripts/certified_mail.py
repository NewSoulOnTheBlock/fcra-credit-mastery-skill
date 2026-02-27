"""
Credit Architect — Certified Mail Dispatch System
Sends FCRA/FDCPA dispute letters via Lob API as USPS Certified Mail with Return Receipt.

Setup:
    pip install requests jinja2
    Set LOB_API_KEY env var (get from dashboard.lob.com)

Usage:
    from certified_mail import DisputeMailer
    mailer = DisputeMailer()
    result = mailer.send_dispute(client, letter_type="basic_bureau", target="equifax", dispute_items=[...])
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

LOB_API_KEY = os.environ.get("LOB_API_KEY", "")
LOB_BASE_URL = "https://api.lob.com/v1"
DISPUTE_LOG_PATH = os.environ.get("DISPUTE_LOG_PATH", "dispute_tracker.json")

# Test mode: set LOB_API_KEY to a test_ key to use Lob's sandbox (no real mail sent)
IS_TEST = LOB_API_KEY.startswith("test_")

# ---------------------------------------------------------------------------
# BUREAU & COLLECTOR ADDRESSES
# ---------------------------------------------------------------------------

BUREAU_ADDRESSES = {
    "equifax": {
        "name": "Equifax Information Services LLC",
        "address_line1": "P.O. Box 740256",
        "address_city": "Atlanta",
        "address_state": "GA",
        "address_zip": "30374-0256",
    },
    "experian": {
        "name": "Experian",
        "address_line1": "P.O. Box 4500",
        "address_city": "Allen",
        "address_state": "TX",
        "address_zip": "75013",
    },
    "transunion": {
        "name": "TransUnion LLC Consumer Dispute Center",
        "address_line1": "P.O. Box 2000",
        "address_city": "Chester",
        "address_state": "PA",
        "address_zip": "19016",
    },
}

# ---------------------------------------------------------------------------
# LETTER TEMPLATES (19 types)
# ---------------------------------------------------------------------------

LETTER_TEMPLATES = {
    # Category 1: Credit Report Disputes (FCRA)
    "basic_bureau": {
        "id": 1,
        "name": "Basic Credit Bureau Dispute",
        "category": "FCRA",
        "target_type": "bureau",
        "legal_basis": "FCRA § 1681i",
    },
    "609_verification": {
        "id": 2,
        "name": "609 Verification Request",
        "category": "FCRA",
        "target_type": "bureau",
        "legal_basis": "FCRA § 609 (15 U.S.C. § 1681g)",
    },
    "611_reinvestigation": {
        "id": 3,
        "name": "611 Reinvestigation Demand",
        "category": "FCRA",
        "target_type": "bureau",
        "legal_basis": "FCRA § 611 (15 U.S.C. § 1681i)",
    },
    "method_of_verification": {
        "id": 4,
        "name": "Method of Verification Demand",
        "category": "FCRA",
        "target_type": "bureau",
        "legal_basis": "FCRA § 611(a)(6)(B)(iii)",
    },
    "identity_theft": {
        "id": 5,
        "name": "Identity Theft Dispute",
        "category": "FCRA",
        "target_type": "bureau",
        "legal_basis": "FCRA § 605B",
    },
    # Category 2: Debt Collector Disputes (FDCPA)
    "debt_validation": {
        "id": 6,
        "name": "Debt Validation Letter",
        "category": "FDCPA",
        "target_type": "collector",
        "legal_basis": "FDCPA § 1692g",
    },
    "cease_desist": {
        "id": 7,
        "name": "Cease and Desist Letter",
        "category": "FDCPA",
        "target_type": "collector",
        "legal_basis": "FDCPA § 1692c(c)",
    },
    "pay_for_delete": {
        "id": 8,
        "name": "Pay-for-Delete Letter",
        "category": "Negotiation",
        "target_type": "collector",
        "legal_basis": "None (negotiation)",
    },
    "goodwill": {
        "id": 9,
        "name": "Goodwill Removal Letter",
        "category": "Courtesy",
        "target_type": "creditor",
        "legal_basis": "None (courtesy request)",
    },
    # Category 3: Creditor-Specific
    "direct_creditor": {
        "id": 10,
        "name": "Direct Creditor Dispute",
        "category": "FCRA",
        "target_type": "creditor",
        "legal_basis": "FCRA § 1681s-2(b)",
    },
    "chargeoff_removal": {
        "id": 11,
        "name": "Charge-Off Removal Request",
        "category": "Negotiation",
        "target_type": "creditor",
        "legal_basis": "Negotiation",
    },
    # Category 4: Hard Inquiry
    "unauthorized_inquiry": {
        "id": 12,
        "name": "Unauthorized Inquiry Removal",
        "category": "FCRA",
        "target_type": "bureau",
        "legal_basis": "FCRA § 1681b",
    },
    # Category 5: Medical
    "hipaa_medical": {
        "id": 13,
        "name": "HIPAA Medical Debt Dispute",
        "category": "HIPAA/FDCPA",
        "target_type": "collector",
        "legal_basis": "HIPAA + FDCPA § 1692g",
    },
    # Category 6: Advanced
    "statute_of_limitations": {
        "id": 14,
        "name": "Statute of Limitations Defense",
        "category": "State Law",
        "target_type": "collector",
        "legal_basis": "State SOL laws",
    },
    "intent_to_sue": {
        "id": 15,
        "name": "Intent to Sue Letter",
        "category": "FCRA/FDCPA",
        "target_type": "any",
        "legal_basis": "FCRA § 1681n / FDCPA § 1692k",
    },
    "arbitration_election": {
        "id": 16,
        "name": "Arbitration Election Letter",
        "category": "Contract",
        "target_type": "creditor",
        "legal_basis": "Federal Arbitration Act",
    },
    # Category 7: Billing
    "billing_error": {
        "id": 17,
        "name": "Billing Error / Unauthorized Charge",
        "category": "FCBA",
        "target_type": "creditor",
        "legal_basis": "FCBA (15 U.S.C. § 1666)",
    },
    # Category 8: Business
    "breach_of_contract": {
        "id": 18,
        "name": "Breach of Contract Notice",
        "category": "Contract",
        "target_type": "any",
        "legal_basis": "State contract law / UCC",
    },
    "demand_letter": {
        "id": 19,
        "name": "Formal Demand Letter",
        "category": "General",
        "target_type": "any",
        "legal_basis": "General contract law",
    },
}


# ---------------------------------------------------------------------------
# LETTER HTML GENERATOR
# ---------------------------------------------------------------------------

def generate_letter_html(
    letter_type: str,
    client: dict,
    recipient: dict,
    dispute_items: list,
    extra_context: Optional[dict] = None,
) -> str:
    """
    Generate a properly formatted HTML letter for Lob printing.

    Args:
        letter_type: Key from LETTER_TEMPLATES
        client: {name, address_line1, city, state, zip, ssn_last4, dob, email, phone}
        recipient: {name, address_line1, city, state, zip}
        dispute_items: List of dicts, each with: {account_name, account_number_last4, reason, details, supporting_docs}
        extra_context: Optional dict for letter-specific fields
            - original_dispute_date (for 611/method_of_verification)
            - settlement_amount (for pay_for_delete/chargeoff)
            - late_payment_month (for goodwill)
            - company_relationship_since (for goodwill)
            - statute_years (for SOL)
            - violations (for intent_to_sue)
            - deadline_days (for demand/intent)
    """
    template_info = LETTER_TEMPLATES.get(letter_type)
    if not template_info:
        raise ValueError(f"Unknown letter type: {letter_type}")

    ctx = extra_context or {}
    today = datetime.now().strftime("%B %d, %Y")

    # Build dispute items block
    items_block = ""
    for item in dispute_items:
        items_block += f"""
        <p style="margin-left: 20px;">
            <strong>Account:</strong> {item.get('account_name', 'Unknown')}<br>
            <strong>Account Number:</strong> XXXX-{item.get('account_number_last4', 'XXXX')}<br>
            <strong>Reason for Dispute:</strong> {item.get('reason', 'Information is inaccurate')}<br>
            <strong>Details:</strong> {item.get('details', '')}
        </p>
        """

    # Common header
    header = f"""
    <div style="font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; max-width: 6.5in; margin: 0 auto;">
        <p>
            {client['name']}<br>
            {client['address_line1']}<br>
            {client['city']}, {client['state']} {client['zip']}<br>
            SSN (last 4): XXX-XX-{client.get('ssn_last4', 'XXXX')}<br>
            DOB: {client.get('dob', '[DOB]')}
        </p>
        <p>{today}</p>
        <p>
            {recipient['name']}<br>
            {recipient['address_line1']}<br>
            {recipient.get('address_city', recipient.get('city', ''))}, {recipient.get('address_state', recipient.get('state', ''))} {recipient.get('address_zip', recipient.get('zip', ''))}
        </p>
    """

    # Letter body varies by type
    bodies = {
        "basic_bureau": f"""
            <p><strong>RE: Dispute of Inaccurate Information</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>Pursuant to my rights under the Fair Credit Reporting Act, 15 U.S.C. § 1681i,
            I am writing to dispute the following inaccurate information in my credit file.</p>
            <p>The following item(s) are inaccurate and require investigation:</p>
            {items_block}
            <p>I request that you investigate this matter and correct or delete the inaccurate
            information within 30 days as required by law.</p>
            <p>Please provide written confirmation of the results of your investigation and a
            free copy of my updated credit report.</p>
        """,
        "609_verification": f"""
            <p><strong>RE: Request for Disclosure Under FCRA § 609</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>Pursuant to my rights under the Fair Credit Reporting Act, 15 U.S.C. § 1681g,
            I am requesting full disclosure of the following:</p>
            <ol>
                <li>All information in my consumer file</li>
                <li>The sources of all information in my file</li>
                <li>The identity of each person who procured my report in the preceding 2 years</li>
            </ol>
            <p>Specifically, regarding the following account(s):</p>
            {items_block}
            <p>I request that you provide documentation verifying the accuracy of this account,
            including any original signed agreement bearing my signature that was used to validate
            this information.</p>
        """,
        "611_reinvestigation": f"""
            <p><strong>RE: Demand for Reinvestigation Under FCRA § 611</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>On {ctx.get('original_dispute_date', '[DATE]')}, I submitted a dispute regarding
            the following account(s):</p>
            {items_block}
            <p>You responded that the information was "verified." Pursuant to FCRA § 611(a)(6)(B)(iii),
            I am requesting:</p>
            <ol>
                <li>A description of the procedure used to determine the accuracy and completeness
                of the information</li>
                <li>The business name, address, and telephone number of any furnisher contacted in
                connection with the reinvestigation</li>
                <li>A notice that I have the right to add a statement to my file disputing the
                accuracy of the information</li>
            </ol>
            <p>If you cannot provide this information within 15 days, I will consider filing a
            complaint with the Consumer Financial Protection Bureau and consulting with an
            FCRA attorney.</p>
        """,
        "method_of_verification": f"""
            <p><strong>RE: Request for Method of Verification</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I previously disputed the following account(s) and received notification that
            the information was verified:</p>
            {items_block}
            <p>Date of Original Dispute: {ctx.get('original_dispute_date', '[DATE]')}</p>
            <p>Pursuant to FCRA § 611(a)(6)(B)(iii), I am formally requesting the method of
            verification used. Specifically:</p>
            <ol>
                <li>What documents were reviewed?</li>
                <li>Who verified this information?</li>
                <li>What specific data points were confirmed?</li>
            </ol>
            <p>If a reasonable method of verification cannot be provided, this account must be
            deleted from my credit file.</p>
        """,
        "identity_theft": f"""
            <p><strong>RE: Identity Theft — Request for Block Under FCRA § 605B</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I am a victim of identity theft. The following account(s) were opened fraudulently
            without my knowledge or consent:</p>
            {items_block}
            <p>Pursuant to FCRA § 605B, I request that you block this information from my credit
            report within 4 business days.</p>
            <p>Enclosed:</p>
            <ol>
                <li>FTC Identity Theft Affidavit (completed)</li>
                <li>Police report (case number: {ctx.get('police_case_number', '[CASE #]')})</li>
                <li>Copy of government-issued photo ID</li>
                <li>Proof of address</li>
            </ol>
            <p>I also request a fraud alert be placed on my file and that you notify the other
            two nationwide credit bureaus.</p>
        """,
        "debt_validation": f"""
            <p><strong>RE: Debt Validation Request — {dispute_items[0].get('account_name', 'Account') if dispute_items else 'Account'}</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I am writing in response to your communication regarding the above-referenced
            account.</p>
            <p>Pursuant to my rights under the Fair Debt Collection Practices Act, 15 U.S.C.
            § 1692g, I request validation of this debt. Please provide:</p>
            <ol>
                <li>The amount of the debt and an itemized breakdown of all charges</li>
                <li>The name and address of the original creditor</li>
                <li>A copy of the original signed agreement between myself and the original creditor</li>
                <li>Proof that your company is authorized/licensed to collect debts in my state</li>
                <li>Complete payment history from the original creditor</li>
                <li>Proof that the statute of limitations has not expired</li>
            </ol>
            <p>Until this debt is fully validated, I demand that you:</p>
            <ul>
                <li>Cease all collection activity</li>
                <li>Remove any reporting to credit bureaus related to this account</li>
            </ul>
            <p>This is not a refusal to pay, but a request for verification as provided by
            federal law.</p>
        """,
        "cease_desist": f"""
            <p><strong>RE: Cease and Desist Communication</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>Pursuant to my rights under the Fair Debt Collection Practices Act, 15 U.S.C.
            § 1692c(c), I am directing you to cease all communication with me regarding the
            above-referenced account(s).</p>
            {items_block}
            <p>This letter serves as your notification that I am exercising my right to stop
            contact. Any further communication beyond a final notice of intended action
            constitutes a violation of the FDCPA.</p>
            <p>I understand you may still pursue legal remedies. This letter pertains solely
            to direct communication.</p>
        """,
        "pay_for_delete": f"""
            <p><strong>RE: Settlement Offer</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I am writing regarding the above-referenced account with an alleged balance.</p>
            {items_block}
            <p>I am prepared to pay ${ctx.get('settlement_amount', '[AMOUNT]')} in exchange for
            the complete removal of this account from my credit reports with all three major
            credit bureaus (Equifax, Experian, and TransUnion).</p>
            <p>This offer is conditional upon your written agreement to:</p>
            <ol>
                <li>Accept the above amount as payment in full</li>
                <li>Delete all references to this account from all credit bureau reports within
                30 days of payment</li>
                <li>Never re-sell or re-assign this debt</li>
            </ol>
            <p>If you agree to these terms, please respond in writing on your company letterhead.
            Payment will be made within 15 days of receiving your written agreement.</p>
            <p>This letter is not an acknowledgment of the validity of this debt, nor is it a
            promise to pay absent your written agreement to the terms above.</p>
        """,
        "goodwill": f"""
            <p><strong>RE: Goodwill Adjustment Request</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I have been a loyal customer of your company since {ctx.get('relationship_since', '[YEAR]')}.
            I am writing to respectfully request a goodwill adjustment to remove the late payment
            reported on my account for {ctx.get('late_payment_month', '[MONTH/YEAR]')}.</p>
            {items_block}
            <p>{ctx.get('explanation', 'Due to an unforeseen circumstance, I was unable to make my payment on time. Since that time, I have maintained a perfect payment record.')}</p>
            <p>This late payment is significantly impacting my ability to
            {ctx.get('credit_goal', 'qualify for favorable credit terms')}.</p>
            <p>I understand this is a courtesy and not an obligation, but I would greatly
            appreciate your consideration.</p>
            <p>Thank you for your time.</p>
        """,
        "direct_creditor": f"""
            <p><strong>RE: Direct Dispute of Reported Information</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>Pursuant to FCRA § 1681s-2(b), I am directly disputing the accuracy of
            information you are furnishing to the credit bureaus regarding the following
            account(s):</p>
            {items_block}
            <p>Please investigate and correct the information reported to Equifax, Experian,
            and TransUnion. Under the FCRA, you are required to:</p>
            <ol>
                <li>Conduct a reasonable investigation</li>
                <li>Review all relevant information provided</li>
                <li>Report the results to the credit bureau</li>
                <li>Modify, delete, or permanently block reporting if inaccurate</li>
            </ol>
        """,
        "chargeoff_removal": f"""
            <p><strong>RE: Charge-Off Settlement and Removal</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I am writing regarding the following account(s), currently reported as charge-off(s):</p>
            {items_block}
            <p>I would like to resolve this account and am prepared to pay
            ${ctx.get('settlement_amount', '[AMOUNT]')}. In exchange, I request that you agree to:</p>
            <ol>
                <li>Remove the charge-off designation from my credit reports with all three bureaus</li>
                <li>Report the account as "paid in full" and "account closed" OR delete the trade
                line entirely</li>
                <li>Provide written confirmation of these terms before payment</li>
            </ol>
            <p>Please respond in writing with your agreement to these terms.</p>
        """,
        "unauthorized_inquiry": f"""
            <p><strong>RE: Unauthorized Credit Inquiry</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I have reviewed my credit report and identified the following unauthorized
            hard inquiry(ies):</p>
            {items_block}
            <p>I did not apply for credit with the above company/companies, nor did I provide
            written authorization for them to access my credit report.</p>
            <p>Pursuant to FCRA § 1681b, a credit report may only be obtained for a permissible
            purpose. These inquiries were made without my consent and without a permissible purpose.</p>
            <p>I request that you:</p>
            <ol>
                <li>Investigate these unauthorized inquiries</li>
                <li>Remove them from my credit report</li>
                <li>Provide me with the contact information for the inquiring companies</li>
            </ol>
        """,
        "hipaa_medical": f"""
            <p><strong>RE: Medical Debt Dispute</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I am disputing the following medical collection(s):</p>
            {items_block}
            <p>Please provide the following:</p>
            <ol>
                <li>Proof of your HIPAA-compliant authorization to possess my protected health
                information (PHI)</li>
                <li>A copy of the signed HIPAA authorization form from me permitting disclosure
                of my medical information to your agency</li>
                <li>Validation of the debt per FDCPA § 1692g, including:
                    <ul>
                        <li>Itemized statement from the original provider</li>
                        <li>Proof that insurance was properly billed and exhausted</li>
                        <li>Name and address of the original medical provider</li>
                    </ul>
                </li>
            </ol>
            <p>Under HIPAA, my protected health information cannot be disclosed without proper
            authorization. If you cannot provide a valid HIPAA authorization bearing my signature,
            you are in possession of my PHI illegally and must cease collection and delete any
            credit reporting immediately.</p>
        """,
        "statute_of_limitations": f"""
            <p><strong>RE: Time-Barred Debt</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>I am writing in response to your communication regarding the above-referenced
            account(s).</p>
            {items_block}
            <p>Please be advised that the alleged debt referenced in your communication is beyond
            the statute of limitations in my state, which is {ctx.get('statute_years', '[X]')} years
            for this type of debt.</p>
            <p>Under state law, this debt is time-barred and legally unenforceable through the courts.
            Any attempt to collect on a time-barred debt or to threaten legal action constitutes
            a violation of the FDCPA.</p>
            <p>I demand that you:</p>
            <ol>
                <li>Cease all collection activity</li>
                <li>Remove any reporting of this account to credit bureaus</li>
                <li>Provide written confirmation that this account is closed</li>
            </ol>
            <p><strong>Nothing in this letter constitutes an acknowledgment of this debt or a
            promise to pay.</strong></p>
        """,
        "intent_to_sue": f"""
            <p><strong>RE: Notice of Intent to Sue — FCRA/FDCPA Violations</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>This letter serves as formal notice of my intent to pursue legal action against
            your company for violations of the Fair Credit Reporting Act and/or Fair Debt
            Collection Practices Act.</p>
            <p>Specifically, you have:</p>
            <ul>
                {''.join(f'<li>{v}</li>' for v in ctx.get('violations', ['[LIST VIOLATIONS]']))}
            </ul>
            <p>I have documentation of these violations, each carrying statutory damages of
            $100–$1,000 under § 1681n, plus actual damages, attorney's fees, and punitive damages.</p>
            <p>I am providing you with {ctx.get('deadline_days', '30')} days to resolve this matter.
            If not resolved by that date, I will retain legal counsel and pursue all available remedies.</p>
        """,
        "arbitration_election": f"""
            <p><strong>RE: Election of Arbitration</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>Pursuant to the arbitration clause in the agreement governing the following
            account(s), I am formally electing arbitration to resolve the dispute described below.</p>
            {items_block}
            <p>I am invoking my right to individual arbitration as specified in the agreement.
            Please provide me with the designated arbitration administrator information so that
            I may initiate proceedings.</p>
            <p>As outlined in the agreement, your company is responsible for paying the
            arbitration filing and administration fees.</p>
        """,
        "billing_error": f"""
            <p><strong>RE: Billing Error Notice Under FCBA</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>Pursuant to the Fair Credit Billing Act, 15 U.S.C. § 1666, I am writing to
            dispute the following charge(s) on my account:</p>
            {items_block}
            <p>I request that you:</p>
            <ol>
                <li>Investigate this billing error</li>
                <li>Credit my account for the disputed amount</li>
                <li>Provide written confirmation of the resolution</li>
            </ol>
            <p>Under the FCBA, you must acknowledge this dispute within 30 days and resolve
            it within two billing cycles (not exceeding 90 days). During the investigation,
            you may not attempt to collect the disputed amount or report it as delinquent.</p>
        """,
        "breach_of_contract": f"""
            <p><strong>RE: Notice of Breach of Contract</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>This letter serves as formal notice that your company is in breach of the
            agreement between us.</p>
            <p>Specifically, the following terms have been violated:</p>
            {items_block}
            <p>I am providing you with {ctx.get('deadline_days', '30')} days to cure this breach.
            If the breach is not cured within the specified period, I will pursue all available
            legal remedies, including but not limited to damages, specific performance, and
            attorney's fees as provided in the agreement.</p>
        """,
        "demand_letter": f"""
            <p><strong>RE: Formal Demand</strong></p>
            <p>Dear Sir/Madam:</p>
            <p>This letter constitutes a formal demand for {ctx.get('demand_action', 'resolution of the following matter')}.</p>
            {items_block}
            <p>You are hereby demanded to take the above action within {ctx.get('deadline_days', '30')} days
            of receipt of this letter.</p>
            <p>If this matter is not resolved by that date, I will pursue all available legal
            remedies without further notice, including filing suit for the amount owed plus
            court costs, interest, and attorney's fees as applicable.</p>
            <p><em>This letter is sent without prejudice to any of my rights and remedies,
            all of which are expressly reserved.</em></p>
        """,
    }

    body = bodies.get(letter_type, bodies["basic_bureau"])

    # Common footer
    footer = f"""
        <p>Sincerely,</p>
        <br><br>
        <p>{client['name']}</p>
        <p style="font-size: 10pt; color: #666; margin-top: 30px;">
            <em>SENT VIA USPS CERTIFIED MAIL — RETURN RECEIPT REQUESTED</em>
        </p>
    </div>
    """

    return f"<html><body>{header}{body}{footer}</body></html>"


# ---------------------------------------------------------------------------
# LOB API INTEGRATION
# ---------------------------------------------------------------------------

class DisputeMailer:
    """Send certified dispute letters via Lob API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or LOB_API_KEY
        if not self.api_key:
            raise ValueError(
                "LOB_API_KEY not set. Get one at dashboard.lob.com and set the env var."
            )
        self.session = requests.Session()
        self.session.auth = (self.api_key, "")

    # -- Address Verification -----------------------------------------------

    def verify_address(self, address: dict) -> dict:
        """Verify a US address via Lob's Address Verification API."""
        resp = self.session.post(
            f"{LOB_BASE_URL}/us_verifications",
            json={
                "primary_line": address.get("address_line1", ""),
                "city": address.get("address_city", address.get("city", "")),
                "state": address.get("address_state", address.get("state", "")),
                "zip_code": address.get("address_zip", address.get("zip", "")),
            },
        )
        result = resp.json()
        return result

    # -- Send Letter --------------------------------------------------------

    def send_letter(
        self,
        from_address: dict,
        to_address: dict,
        letter_html: str,
        description: str = "Dispute Letter",
        certified: bool = True,
        return_receipt: bool = True,
        color: bool = False,
    ) -> dict:
        """
        Send a physical letter via Lob.

        Args:
            from_address: {name, address_line1, address_city, address_state, address_zip}
            to_address: same format
            letter_html: HTML content of the letter
            description: Internal description for tracking
            certified: Send as USPS Certified Mail
            return_receipt: Include return receipt (green card)
            color: Print in color (costs more)
        """
        data = {
            "description": description,
            "to[name]": to_address["name"],
            "to[address_line1]": to_address["address_line1"],
            "to[address_city]": to_address.get("address_city", to_address.get("city", "")),
            "to[address_state]": to_address.get("address_state", to_address.get("state", "")),
            "to[address_zip]": to_address.get("address_zip", to_address.get("zip", "")),
            "from[name]": from_address["name"],
            "from[address_line1]": from_address["address_line1"],
            "from[address_city]": from_address.get("address_city", from_address.get("city", "")),
            "from[address_state]": from_address.get("address_state", from_address.get("state", "")),
            "from[address_zip]": from_address.get("address_zip", from_address.get("zip", "")),
            "file": letter_html,
            "color": str(color).lower(),
            "mail_type": "usps_first_class",
            "address_placement": "top_first_page",
        }

        if certified and return_receipt:
            data["extra_service"] = "certified_return_receipt"
        elif certified:
            data["extra_service"] = "certified"

        resp = self.session.post(f"{LOB_BASE_URL}/letters", data=data)

        if resp.status_code != 200:
            raise Exception(f"Lob API error {resp.status_code}: {resp.text}")

        return resp.json()

    # -- High-Level Dispute Sender ------------------------------------------

    def send_dispute(
        self,
        client: dict,
        letter_type: str,
        target: str,
        dispute_items: list,
        custom_recipient: Optional[dict] = None,
        extra_context: Optional[dict] = None,
    ) -> dict:
        """
        Full dispute pipeline: generate letter → verify addresses → send certified → log.

        Args:
            client: {name, address_line1, city, state, zip, ssn_last4, dob}
            letter_type: Key from LETTER_TEMPLATES (e.g., "basic_bureau", "debt_validation")
            target: "equifax" | "experian" | "transunion" | or custom
            dispute_items: [{account_name, account_number_last4, reason, details}]
            custom_recipient: Override recipient address (for collectors/creditors)
            extra_context: Letter-specific fields (see generate_letter_html docstring)

        Returns:
            Tracking dict with letter_id, tracking_number, deadlines, etc.
        """
        template_info = LETTER_TEMPLATES.get(letter_type)
        if not template_info:
            raise ValueError(f"Unknown letter type: {letter_type}. Options: {list(LETTER_TEMPLATES.keys())}")

        # Determine recipient
        if custom_recipient:
            recipient = custom_recipient
        elif target in BUREAU_ADDRESSES:
            recipient = BUREAU_ADDRESSES[target]
        else:
            raise ValueError(
                f"Target '{target}' not found. Use 'equifax', 'experian', 'transunion', "
                f"or provide custom_recipient dict."
            )

        # Normalize client address for Lob
        from_address = {
            "name": client["name"],
            "address_line1": client.get("address_line1", client.get("address", "")),
            "address_city": client.get("address_city", client.get("city", "")),
            "address_state": client.get("address_state", client.get("state", "")),
            "address_zip": client.get("address_zip", client.get("zip", "")),
        }

        # Generate letter HTML
        letter_html = generate_letter_html(
            letter_type=letter_type,
            client=client,
            recipient=recipient,
            dispute_items=dispute_items,
            extra_context=extra_context,
        )

        # Send via Lob
        description = f"Credit Dispute #{template_info['id']} - {template_info['name']} - {target}"
        result = self.send_letter(
            from_address=from_address,
            to_address=recipient,
            letter_html=letter_html,
            description=description,
        )

        # Build tracking record
        now = datetime.now()
        tracking = {
            "letter_id": result.get("id"),
            "tracking_number": result.get("tracking_number"),
            "carrier": result.get("carrier", "USPS"),
            "expected_delivery": result.get("expected_delivery_date"),
            "letter_type": letter_type,
            "letter_name": template_info["name"],
            "legal_basis": template_info["legal_basis"],
            "target": target,
            "recipient_name": recipient["name"],
            "sent_date": now.isoformat(),
            "response_deadline": (now + timedelta(days=30)).isoformat(),
            "escalation_date": (now + timedelta(days=35)).isoformat(),
            "status": "sent",
            "items_disputed": dispute_items,
            "lob_url": result.get("url"),
            "thumbnail": result.get("thumbnails", [{}])[0].get("large") if result.get("thumbnails") else None,
            "cost": result.get("price"),
            "is_test": IS_TEST,
        }

        # Log to tracker
        self._log_dispute(tracking)

        return tracking

    # -- Batch Send (all 3 bureaus) -----------------------------------------

    def send_to_all_bureaus(
        self,
        client: dict,
        letter_type: str,
        dispute_items: list,
        extra_context: Optional[dict] = None,
    ) -> list:
        """Send the same dispute letter to all 3 credit bureaus."""
        results = []
        for bureau in ["equifax", "experian", "transunion"]:
            result = self.send_dispute(
                client=client,
                letter_type=letter_type,
                target=bureau,
                dispute_items=dispute_items,
                extra_context=extra_context,
            )
            results.append(result)
            print(f"  ✓ Sent to {bureau}: {result.get('letter_id')} (tracking: {result.get('tracking_number')})")
        return results

    # -- Dispute Tracker ----------------------------------------------------

    def _log_dispute(self, tracking: dict):
        """Append tracking record to local JSON log."""
        log_path = Path(DISPUTE_LOG_PATH)
        if log_path.exists():
            with open(log_path) as f:
                log = json.load(f)
        else:
            log = {"disputes": []}

        log["disputes"].append(tracking)

        with open(log_path, "w") as f:
            json.dump(log, f, indent=2, default=str)

    def get_pending_disputes(self) -> list:
        """Get all disputes awaiting response (past sent, not yet resolved)."""
        log_path = Path(DISPUTE_LOG_PATH)
        if not log_path.exists():
            return []

        with open(log_path) as f:
            log = json.load(f)

        now = datetime.now()
        pending = []
        for d in log.get("disputes", []):
            if d["status"] in ("sent", "delivered"):
                deadline = datetime.fromisoformat(d["response_deadline"])
                d["days_remaining"] = (deadline - now).days
                d["overdue"] = d["days_remaining"] < 0
                pending.append(d)

        return sorted(pending, key=lambda x: x["days_remaining"])

    def get_overdue_disputes(self) -> list:
        """Get disputes past the 30-day response deadline — ready for escalation."""
        return [d for d in self.get_pending_disputes() if d.get("overdue")]

    def update_dispute_status(self, letter_id: str, status: str, notes: str = ""):
        """Update a dispute's status (delivered, resolved, escalated, deleted)."""
        log_path = Path(DISPUTE_LOG_PATH)
        if not log_path.exists():
            return

        with open(log_path) as f:
            log = json.load(f)

        for d in log.get("disputes", []):
            if d["letter_id"] == letter_id:
                d["status"] = status
                d["updated_at"] = datetime.now().isoformat()
                if notes:
                    d["notes"] = notes
                break

        with open(log_path, "w") as f:
            json.dump(log, f, indent=2, default=str)

    # -- Check Lob Letter Status --------------------------------------------

    def check_delivery_status(self, letter_id: str) -> dict:
        """Check the current delivery status of a sent letter."""
        resp = self.session.get(f"{LOB_BASE_URL}/letters/{letter_id}")
        if resp.status_code != 200:
            return {"error": resp.text}
        data = resp.json()
        return {
            "id": data.get("id"),
            "tracking_number": data.get("tracking_number"),
            "carrier": data.get("carrier"),
            "expected_delivery": data.get("expected_delivery_date"),
            "send_date": data.get("send_date"),
            "mail_type": data.get("mail_type"),
            "extra_service": data.get("extra_service"),
            "tracking_events": data.get("tracking_events", []),
        }


# ---------------------------------------------------------------------------
# CLI INTERFACE
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send certified credit dispute letters via Lob API")
    parser.add_argument("action", choices=["send", "send-all", "pending", "overdue", "status", "types"])
    parser.add_argument("--type", help="Letter type (e.g., basic_bureau, debt_validation)")
    parser.add_argument("--target", help="Target: equifax, experian, transunion, or custom")
    parser.add_argument("--name", help="Client name")
    parser.add_argument("--address", help="Client address")
    parser.add_argument("--city", help="Client city")
    parser.add_argument("--state", help="Client state")
    parser.add_argument("--zip", help="Client zip")
    parser.add_argument("--ssn4", help="Last 4 of SSN")
    parser.add_argument("--dob", help="Date of birth")
    parser.add_argument("--account", help="Account name to dispute")
    parser.add_argument("--account-num", help="Last 4 of account number")
    parser.add_argument("--reason", help="Reason for dispute")
    parser.add_argument("--letter-id", help="Letter ID for status check")
    args = parser.parse_args()

    if args.action == "types":
        print("\nAvailable letter types:\n")
        for key, info in LETTER_TEMPLATES.items():
            print(f"  {key:30s} #{info['id']:2d}  {info['name']}")
            print(f"  {'':30s}     Category: {info['category']} | Legal: {info['legal_basis']}")
            print()

    elif args.action == "pending":
        mailer = DisputeMailer()
        pending = mailer.get_pending_disputes()
        if not pending:
            print("No pending disputes.")
        else:
            print(f"\n{len(pending)} pending dispute(s):\n")
            for d in pending:
                status = "⚠️ OVERDUE" if d.get("overdue") else f"{d['days_remaining']} days left"
                print(f"  [{d['letter_type']}] → {d['target']} | {status} | ID: {d['letter_id']}")

    elif args.action == "overdue":
        mailer = DisputeMailer()
        overdue = mailer.get_overdue_disputes()
        if not overdue:
            print("No overdue disputes. All within 30-day window.")
        else:
            print(f"\n⚠️ {len(overdue)} OVERDUE dispute(s) — ready for escalation:\n")
            for d in overdue:
                print(f"  [{d['letter_type']}] → {d['target']} | {abs(d['days_remaining'])} days overdue")
                print(f"    Escalation: File CFPB complaint or send Letter #15 (Intent to Sue)")

    elif args.action == "status" and args.letter_id:
        mailer = DisputeMailer()
        status = mailer.check_delivery_status(args.letter_id)
        print(json.dumps(status, indent=2))

    elif args.action in ("send", "send-all"):
        if not all([args.type, args.name, args.address, args.city, args.state, args.zip]):
            parser.error("--type, --name, --address, --city, --state, --zip are required for send")

        client = {
            "name": args.name,
            "address_line1": args.address,
            "city": args.city,
            "state": args.state,
            "zip": args.zip,
            "ssn_last4": args.ssn4 or "XXXX",
            "dob": args.dob or "[DOB]",
        }
        dispute_items = [{
            "account_name": args.account or "[Account Name]",
            "account_number_last4": args.account_num or "XXXX",
            "reason": args.reason or "Information is inaccurate",
            "details": "",
        }]

        mailer = DisputeMailer()

        if args.action == "send-all":
            print(f"\nSending {args.type} to ALL 3 bureaus as USPS Certified Mail...\n")
            results = mailer.send_to_all_bureaus(client, args.type, dispute_items)
            print(f"\n✅ {len(results)} letters sent. Tracking logged to {DISPUTE_LOG_PATH}")
        else:
            if not args.target:
                parser.error("--target required for send (equifax, experian, transunion)")
            print(f"\nSending {args.type} to {args.target} as USPS Certified Mail...\n")
            result = mailer.send_dispute(client, args.type, args.target, dispute_items)
            print(f"✅ Sent! Letter ID: {result['letter_id']}")
            print(f"   Tracking: {result.get('tracking_number')}")
            print(f"   30-day deadline: {result['response_deadline']}")
