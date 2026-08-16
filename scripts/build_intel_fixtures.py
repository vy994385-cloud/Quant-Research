"""
Build committed recorded intel fixtures for the real companies.

Generates fixtures/real_data/{company}_intel.json for each company in
the verified universe. The fixtures feed the deep company intelligence
layer (src.research.company_intel) through the recorded intel source
provider, exactly like the market / financial / source fixtures feed
the rest of the recorded verification path.

The content is curated, dated, recorded fixture material. Source URLs
are placeholders (example.invalid) and every file carries a note so
the content is never mistaken for live reporting. Each company includes
one deliberately future-dated candidate used to verify that the
point-in-time gate rejects evidence that was unavailable at the
research as-of timestamp.

Usage:
    .venv/bin/python scripts/build_intel_fixtures.py

Re-running produces identical, deterministic output.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "fixtures" / "real_data"

CAPTURED_AT = "2026-08-15T18:49:10+00:00"

# Point-in-time gate: the recorded research as-of (see
# src/verification/real_data.DEFAULT_AS_OF) is 2026-08-10T12:00:00+00:00.
# All real content must be available on or before that timestamp.
FUTURE_AVAILABLE_AT = "2026-08-14T09:00:00+05:30"

NOTE = (
    "Recorded intel candidates curated as dated fixture material for "
    "the deep company intelligence layer. Content is illustrative and "
    "clearly labeled: source URLs are placeholders and every candidate "
    "carries an explicit verification status. The "
    "{future}-candidate is a deliberate future-dated contamination "
    "record used to verify that the point-in-time gate rejects "
    "evidence unavailable at the research as-of timestamp."
)


def _candidate(
    *,
    candidate_id: str,
    company: str,
    title: str,
    body: str,
    published_at: str,
    available_at: str,
    kind: str,
    source_type: str,
    source_name: str,
    reliability_tier: int,
    verification_status: str = "REPORTED",
    event_type: str | None = None,
    semantic_category: str | None = None,
    topic: str | None = None,
    stance: str = "NEUTRAL",
    direction: str = "UNKNOWN",
    related_entities: list[str] | None = None,
    relevance: str | None = None,
    confidence: str | None = None,
    source_url: str | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "company": company,
        "source_name": source_name,
        "source_type": source_type,
        "source_url": source_url or "https://example.invalid/",
        "title": title,
        "body": body,
        "published_at": published_at,
        "available_at": available_at,
        "reliability_tier": reliability_tier,
        "kind": kind,
        "event_type": event_type,
        "semantic_category": semantic_category,
        "verification_status": verification_status,
        "topic": topic,
        "stance": stance,
        "direction": direction,
        "related_entities": related_entities or [],
        "relevance": relevance,
        "confidence": confidence,
    }


def _future_candidate(company: str, name: str) -> dict:
    return _candidate(
        candidate_id=f"{company.lower()}-future-intel-fixture",
        company=company,
        title=(
            f"{name} future-dated intelligence fixture used to verify "
            "point-in-time rejection (available after the research "
            "as-of timestamp)"
        ),
        body=(
            "Recorded fixture content. This candidate is dated after "
            "the research as-of and must never appear in a point-in-time "
            "intelligence snapshot."
        ),
        published_at="2026-08-13T09:00:00+05:30",
        available_at=FUTURE_AVAILABLE_AT,
        kind="BUSINESS_EVENT",
        event_type="OTHER",
        source_type="NEWS",
        source_name="Recorded Intel Feed",
        reliability_tier=2,
        verification_status="REPORTED",
        topic="future_fixture",
    )


def _tcs() -> list[dict]:
    company = "TCS"
    name = "Tata Consultancy Services"

    return [
        _candidate(
            candidate_id="tcs-intel-q1fy27-results",
            company=company,
            title=(
                "TCS reported Q1 FY27 revenue of Rs 72,275 crore "
                "(up 13.93% YoY) and net profit of Rs 13,349 crore "
                "(up 4.62% YoY)"
            ),
            body=(
                "Q1 FY27 results were published on July 9, 2026. Revenue "
                "grew 13.93% year on year to Rs 72,275 crore and net "
                "profit grew 4.62% to Rs 13,349 crore. The quarter ended "
                "June 30, 2026."
            ),
            published_at="2026-07-09T18:30:00+05:30",
            available_at="2026-07-09T18:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="EARNINGS",
            source_type="REGULATORY",
            source_name="TCS Exchange Filing (Recorded)",
            reliability_tier=1,
            verification_status="CONFIRMED",
            topic="quarterly_results",
            stance="NEUTRAL",
            direction="NEUTRAL",
            confidence="0.95",
        ),
        _candidate(
            candidate_id="tcs-intel-interim-dividend-fy27",
            company=company,
            title=(
                "TCS declared an interim dividend of Rs 12 per share "
                "for FY27"
            ),
            body=(
                "The board declared an interim dividend of Rs 12 per "
                "equity share for FY27, payable to shareholders on the "
                "record date of July 15, 2026."
            ),
            published_at="2026-07-09T19:00:00+05:30",
            available_at="2026-07-09T19:00:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="DIVIDEND",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="capital_allocation",
            stance="SUPPORTIVE",
            direction="NEUTRAL",
            confidence="0.90",
        ),
        _candidate(
            candidate_id="tcs-intel-ai-partnerships",
            company=company,
            title=(
                "TCS expanded strategic AI partnerships with Anthropic "
                "and Mistral AI and deepened the Google Cloud collaboration"
            ),
            body=(
                "TCS reported that its AI initiatives include strategic "
                "partnerships with Anthropic and Mistral AI plus an "
                "expanded Google Cloud collaboration, with annualized "
                "AI-related revenue of $2.6 billion."
            ),
            published_at="2026-07-10T09:30:00+05:30",
            available_at="2026-07-10T09:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PARTNERSHIP",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="ai_partnerships",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            related_entities=["Anthropic", "Mistral AI", "Google Cloud"],
            confidence="0.90",
        ),
        _candidate(
            candidate_id="tcs-intel-management-demand",
            company=company,
            title=(
                "TCS management: the demand environment remains strong "
                "with a healthy order pipeline"
            ),
            body=(
                "On the Q1 FY27 earnings call, management described the "
                "demand environment as strong and cited a $9.5 billion "
                "order book for the quarter. This is a management "
                "statement, not an independent fact."
            ),
            published_at="2026-07-09T20:30:00+05:30",
            available_at="2026-07-09T20:30:00+05:30",
            kind="MANAGEMENT_COMMENTARY",
            source_type="NEWS",
            source_name="Recorded Earnings Call Notes",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="demand_environment",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            related_entities=["Board", "CEO"],
            confidence="0.70",
        ),
        _candidate(
            candidate_id="tcs-intel-order-intake-decline",
            company=company,
            title=(
                "Reported: TCS order intake declined sequentially for a "
                "second consecutive quarter"
            ),
            body=(
                "A recorded press report suggested order intake declined "
                "on a sequential basis for the second consecutive "
                "quarter, in apparent tension with management commentary "
                "about a strong demand environment. This is a reported "
                "claim, not an established fact."
            ),
            published_at="2026-07-11T09:00:00+05:30",
            available_at="2026-07-11T09:00:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="CONTRACT_LOSS",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="demand_environment",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.50",
        ),
        _candidate(
            candidate_id="tcs-intel-margin-risk",
            company=company,
            title=(
                "TCS flagged wage inflation, attrition, and currency "
                "volatility as near-term margin risks"
            ),
            body=(
                "TCS noted that wage inflation, attrition pressure, and "
                "INR/USD volatility remain the main near-term risks to "
                "operating margins. This is a disclosed risk statement."
            ),
            published_at="2026-07-15T10:00:00+05:30",
            available_at="2026-07-15T10:00:00+05:30",
            kind="RISK_DEVELOPMENT",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="margin_risks",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.60",
        ),
        _candidate(
            candidate_id="tcs-intel-sector-demand",
            company=company,
            title=(
                "Indian IT services order momentum stays cautious as "
                "clients defer discretionary spending"
            ),
            body=(
                "Sector-level reporting indicates clients continue to "
                "defer discretionary spending, keeping order momentum "
                "cautious across the Indian IT services sector. "
                "INR/USD volatility adds uncertainty. This is "
                "indirect, outside-in intelligence."
            ),
            published_at="2026-07-20T09:00:00+05:30",
            available_at="2026-07-20T09:00:00+05:30",
            kind="INDIRECT_INTELLIGENCE",
            source_type="NEWS",
            source_name="Recorded Sector Review",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="sector_demand",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.40",
        ),
        _future_candidate(company, name),
    ]


def _reliance() -> list[dict]:
    company = "RELIANCE"
    name = "Reliance Industries"

    return [
        _candidate(
            candidate_id="reliance-intel-q1fy27-results",
            company=company,
            title=(
                "Reliance reported Q1 FY27 consolidated revenue of "
                "Rs 2.68 lakh crore with EBITDA of Rs 49,912 crore"
            ),
            body=(
                "Q1 FY27 consolidated results were published on July 17, "
                "2026. Consolidated revenue stood at Rs 2.68 lakh crore "
                "and EBITDA at Rs 49,912 crore, driven by energy and "
                "retail segments."
            ),
            published_at="2026-07-17T18:30:00+05:30",
            available_at="2026-07-17T18:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="EARNINGS",
            source_type="REGULATORY",
            source_name="Reliance Exchange Filing (Recorded)",
            reliability_tier=1,
            verification_status="CONFIRMED",
            topic="quarterly_results",
            direction="NEUTRAL",
            confidence="0.95",
        ),
        _candidate(
            candidate_id="reliance-intel-dividend",
            company=company,
            title="Reliance board approved a dividend of Rs 10 per share",
            body=(
                "The board approved a dividend of Rs 10 per fully paid "
                "equity share, subject to shareholder approval at the "
                "annual general meeting."
            ),
            published_at="2026-07-17T19:00:00+05:30",
            available_at="2026-07-17T19:00:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="DIVIDEND",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="capital_allocation",
            stance="SUPPORTIVE",
            confidence="0.90",
        ),
        _candidate(
            candidate_id="reliance-intel-jio-partnership",
            company=company,
            title=(
                "Reliance Jio expanded its 5G enterprise partnership "
                "with a global network equipment vendor"
            ),
            body=(
                "Jio announced an expanded enterprise 5G partnership "
                "covering private networks and edge services. The "
                "commercial impact was not quantified."
            ),
            published_at="2026-07-22T09:30:00+05:30",
            available_at="2026-07-22T09:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PARTNERSHIP",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="digital_services",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.85",
        ),
        _candidate(
            candidate_id="reliance-intel-management-energy",
            company=company,
            title=(
                "Reliance management: energy demand remains robust with "
                "record Jamnagar throughput"
            ),
            body=(
                "Management said energy demand remained robust and "
                "highlighted record throughput at the Jamnagar complex. "
                "This is a management statement, not an independent fact."
            ),
            published_at="2026-07-17T20:30:00+05:30",
            available_at="2026-07-17T20:30:00+05:30",
            kind="MANAGEMENT_COMMENTARY",
            source_type="NEWS",
            source_name="Recorded Earnings Call Notes",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="energy_demand",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.70",
        ),
        _candidate(
            candidate_id="reliance-intel-crude-risk",
            company=company,
            title=(
                "Rising global crude prices increase input-cost exposure "
                "for refining and petrochemicals"
            ),
            body=(
                "A reported analysis flagged that rising global crude "
                "prices increase input-cost exposure for the refining "
                "and petrochemicals business. This is a reported claim."
            ),
            published_at="2026-07-25T09:00:00+05:30",
            available_at="2026-07-25T09:00:00+05:30",
            kind="RISK_DEVELOPMENT",
            source_type="NEWS",
            source_name="Recorded Sector Analysis",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="input_costs",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.50",
        ),
        _candidate(
            candidate_id="reliance-intel-petrochem-margins",
            company=company,
            title=(
                "Regional petrochemical margins remain under pressure"
            ),
            body=(
                "Outside-in sector reporting indicates petrochemical "
                "margins remain under pressure across the region due to "
                "new capacity. This is indirect, outside-in intelligence."
            ),
            published_at="2026-07-28T09:00:00+05:30",
            available_at="2026-07-28T09:00:00+05:30",
            kind="INDIRECT_INTELLIGENCE",
            source_type="NEWS",
            source_name="Recorded Sector Review",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="petrochemical_margins",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.40",
        ),
        _future_candidate(company, name),
    ]


def _infy() -> list[dict]:
    company = "INFY"
    name = "Infosys"

    return [
        _candidate(
            candidate_id="infy-intel-q1fy27-results",
            company=company,
            title=(
                "Infosys reported Q1 FY27 revenue of Rs 42,363 crore "
                "(up 8.4% YoY) with an EBIT margin of 21.1%"
            ),
            body=(
                "Q1 FY27 results were published on July 16, 2026. "
                "Revenue grew 8.4% year on year to Rs 42,363 crore with "
                "an EBIT margin of 21.1% for the quarter."
            ),
            published_at="2026-07-16T18:30:00+05:30",
            available_at="2026-07-16T18:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="EARNINGS",
            source_type="REGULATORY",
            source_name="Infosys Exchange Filing (Recorded)",
            reliability_tier=1,
            verification_status="CONFIRMED",
            topic="quarterly_results",
            direction="NEUTRAL",
            confidence="0.95",
        ),
        _candidate(
            candidate_id="infy-intel-dividend",
            company=company,
            title="Infosys declared an interim dividend for FY27",
            body=(
                "The board declared an interim dividend for FY27 as part "
                "of its capital-return policy, alongside the Q1 results."
            ),
            published_at="2026-07-16T19:00:00+05:30",
            available_at="2026-07-16T19:00:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="DIVIDEND",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="capital_allocation",
            stance="SUPPORTIVE",
            confidence="0.90",
        ),
        _candidate(
            candidate_id="infy-intel-ai-collaboration",
            company=company,
            title=(
                "Infosys expanded its enterprise AI collaboration with "
                "NVIDIA"
            ),
            body=(
                "Infosys announced an expanded collaboration with NVIDIA "
                "focused on enterprise AI platforms and inference "
                "workloads. Commercial terms were not disclosed."
            ),
            published_at="2026-07-21T09:30:00+05:30",
            available_at="2026-07-21T09:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PARTNERSHIP",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="ai_partnerships",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            related_entities=["NVIDIA"],
            confidence="0.85",
        ),
        _candidate(
            candidate_id="infy-intel-management-guidance",
            company=company,
            title=(
                "Infosys management guided FY27 revenue growth of 8-10% "
                "in constant currency"
            ),
            body=(
                "On the Q1 earnings call, management guided FY27 revenue "
                "growth of 8-10% in constant currency. This is a "
                "management forecast, not an established fact."
            ),
            published_at="2026-07-16T20:30:00+05:30",
            available_at="2026-07-16T20:30:00+05:30",
            kind="MANAGEMENT_COMMENTARY",
            source_type="NEWS",
            source_name="Recorded Earnings Call Notes",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="revenue_guidance",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.70",
        ),
        _candidate(
            candidate_id="infy-intel-bfsi-risk",
            company=company,
            title=(
                "Client-side budget cuts were reported in the BFSI "
                "segment"
            ),
            body=(
                "A recorded report suggested budget cuts among BFSI "
                "clients could weigh on near-term revenue. This is a "
                "reported claim, not an established fact."
            ),
            published_at="2026-07-24T09:00:00+05:30",
            available_at="2026-07-24T09:00:00+05:30",
            kind="RISK_DEVELOPMENT",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="client_budgets",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.50",
        ),
        _candidate(
            candidate_id="infy-intel-sector-spending",
            company=company,
            title=(
                "Global IT services spending outlook remains cautious"
            ),
            body=(
                "Outside-in sector reporting indicates cautious global IT "
                "services spending as enterprises defer discretionary "
                "projects. This is indirect, outside-in intelligence."
            ),
            published_at="2026-07-27T09:00:00+05:30",
            available_at="2026-07-27T09:00:00+05:30",
            kind="INDIRECT_INTELLIGENCE",
            source_type="NEWS",
            source_name="Recorded Sector Review",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="sector_spending",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.40",
        ),
        _future_candidate(company, name),
    ]


def _hdfcbank() -> list[dict]:
    company = "HDFCBANK"
    name = "HDFC Bank"

    return [
        _candidate(
            candidate_id="hdfcbank-intel-q1fy27-results",
            company=company,
            title=(
                "HDFC Bank reported Q1 FY27 net profit of Rs 17,728 "
                "crore and net interest income of Rs 44,124 crore"
            ),
            body=(
                "Q1 FY27 results were published on July 21, 2026. Net "
                "profit was Rs 17,728 crore and net interest income "
                "Rs 44,124 crore for the quarter."
            ),
            published_at="2026-07-21T18:30:00+05:30",
            available_at="2026-07-21T18:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="EARNINGS",
            source_type="REGULATORY",
            source_name="HDFC Bank Exchange Filing (Recorded)",
            reliability_tier=1,
            verification_status="CONFIRMED",
            topic="quarterly_results",
            direction="NEUTRAL",
            confidence="0.95",
        ),
        _candidate(
            candidate_id="hdfcbank-intel-capital",
            company=company,
            title=(
                "HDFC Bank board approved raising additional capital "
                "via perpetual bonds"
            ),
            body=(
                "The board approved raising additional capital through "
                "the issuance of perpetual (AT1) bonds, subject to "
                "regulatory and shareholder approvals."
            ),
            published_at="2026-07-21T19:00:00+05:30",
            available_at="2026-07-21T19:00:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="CREDIT_ACTION",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="capital_management",
            stance="SUPPORTIVE",
            confidence="0.90",
        ),
        _candidate(
            candidate_id="hdfcbank-intel-lending-partnership",
            company=company,
            title=(
                "HDFC Bank expanded its digital lending partnership "
                "network"
            ),
            body=(
                "HDFC Bank announced an expanded digital lending "
                "partnership network covering co-lending arrangements "
                "with fintech partners. Commercial details were not "
                "disclosed."
            ),
            published_at="2026-07-25T09:30:00+05:30",
            available_at="2026-07-25T09:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PARTNERSHIP",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="digital_lending",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.85",
        ),
        _candidate(
            candidate_id="hdfcbank-intel-management-loans",
            company=company,
            title=(
                "HDFC Bank management: loan growth continues to outpace "
                "system growth with stable margins"
            ),
            body=(
                "On the Q1 earnings call, management said loan growth "
                "continues to outpace system growth and margins are "
                "stable. This is a management statement, not an "
                "independent fact."
            ),
            published_at="2026-07-21T20:30:00+05:30",
            available_at="2026-07-21T20:30:00+05:30",
            kind="MANAGEMENT_COMMENTARY",
            source_type="NEWS",
            source_name="Recorded Earnings Call Notes",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="loan_growth",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.70",
        ),
        _candidate(
            candidate_id="hdfcbank-intel-nim-risk",
            company=company,
            title=(
                "Rising deposit competition pressures net interest "
                "margins across the banking sector"
            ),
            body=(
                "A recorded analysis flagged that rising deposit "
                "competition is pressuring net interest margins across "
                "the banking sector. This is a reported claim."
            ),
            published_at="2026-07-27T09:00:00+05:30",
            available_at="2026-07-27T09:00:00+05:30",
            kind="RISK_DEVELOPMENT",
            source_type="NEWS",
            source_name="Recorded Sector Analysis",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="net_interest_margins",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.50",
        ),
        _candidate(
            candidate_id="hdfcbank-intel-liquidity",
            company=company,
            title=(
                "Indian banking system liquidity tightened in July 2026"
            ),
            body=(
                "Outside-in reporting indicated the Indian banking "
                "system's liquidity tightened in July 2026, with "
                "implications for deposit pricing. This is indirect, "
                "outside-in intelligence."
            ),
            published_at="2026-07-29T09:00:00+05:30",
            available_at="2026-07-29T09:00:00+05:30",
            kind="INDIRECT_INTELLIGENCE",
            source_type="NEWS",
            source_name="Recorded Sector Review",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="system_liquidity",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.40",
        ),
        _future_candidate(company, name),
    ]


def _sunpharma() -> list[dict]:
    company = "SUNPHARMA"
    name = "Sun Pharmaceutical Industries"

    return [
        _candidate(
            candidate_id="sunpharma-intel-q1fy27-results",
            company=company,
            title=(
                "Sun Pharma reported Q1 FY27 consolidated revenue of "
                "Rs 14,293 crore (up 10% YoY)"
            ),
            body=(
                "Q1 FY27 consolidated results were published on "
                "July 28, 2026. Consolidated revenue was Rs 14,293 crore, "
                "up 10% year on year, led by specialty and India "
                "formulations."
            ),
            published_at="2026-07-28T18:30:00+05:30",
            available_at="2026-07-28T18:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="EARNINGS",
            source_type="REGULATORY",
            source_name="Sun Pharma Exchange Filing (Recorded)",
            reliability_tier=1,
            verification_status="CONFIRMED",
            topic="quarterly_results",
            direction="NEUTRAL",
            confidence="0.95",
        ),
        _candidate(
            candidate_id="sunpharma-intel-usfda-approval",
            company=company,
            title=(
                "Sun Pharma received USFDA approval for a specialty "
                "dermatology product"
            ),
            body=(
                "The USFDA approved a specialty dermatology product, "
                "expanding the US specialty portfolio. Launch timing was "
                "not disclosed."
            ),
            published_at="2026-07-29T09:00:00+05:30",
            available_at="2026-07-29T09:00:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PRODUCT_LAUNCH",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="product_approvals",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.90",
        ),
        _candidate(
            candidate_id="sunpharma-intel-specialty-traction",
            company=company,
            title=(
                "Sun Pharma management: specialty portfolio traction "
                "remains strong in the US"
            ),
            body=(
                "On the Q1 earnings call, management said specialty "
                "portfolio traction remains strong in the US market. "
                "This is a management statement, not an independent fact."
            ),
            published_at="2026-07-28T20:30:00+05:30",
            available_at="2026-07-28T20:30:00+05:30",
            kind="MANAGEMENT_COMMENTARY",
            source_type="NEWS",
            source_name="Recorded Earnings Call Notes",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="specialty_traction",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.70",
        ),
        _candidate(
            candidate_id="sunpharma-intel-quality-allegation",
            company=company,
            title=(
                "Allegation: quality-control lapses at an Indian "
                "manufacturing unit"
            ),
            body=(
                "A recorded report alleged quality-control lapses at an "
                "Indian manufacturing unit. The company has not "
                "commented and the claim is unproven. This is an "
                "allegation, not an established fact."
            ),
            published_at="2026-07-30T09:00:00+05:30",
            available_at="2026-07-30T09:00:00+05:30",
            kind="RISK_DEVELOPMENT",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=3,
            verification_status="ALLEGED",
            topic="quality_compliance",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.30",
        ),
        _candidate(
            candidate_id="sunpharma-intel-pricing-pressure",
            company=company,
            title=(
                "US generic pricing pressure continues across the "
                "pharmaceutical sector"
            ),
            body=(
                "Outside-in sector reporting indicates continued US "
                "generic pricing pressure. This is indirect, outside-in "
                "intelligence."
            ),
            published_at="2026-08-03T09:00:00+05:30",
            available_at="2026-08-03T09:00:00+05:30",
            kind="INDIRECT_INTELLIGENCE",
            source_type="NEWS",
            source_name="Recorded Sector Review",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="generic_pricing",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.40",
        ),
        _future_candidate(company, name),
    ]


def _mahindra() -> list[dict]:
    company = "M&M"
    name = "Mahindra & Mahindra"

    return [
        _candidate(
            candidate_id="mahindra-intel-q1fy27-results",
            company=company,
            title=(
                "Mahindra & Mahindra reported Q1 FY27 standalone revenue "
                "of Rs 32,530 crore (up 12% YoY)"
            ),
            body=(
                "Q1 FY27 standalone results were published on "
                "August 6, 2026. Revenue was Rs 32,530 crore, up 12% "
                "year on year, with SUV and tractor volumes growing."
            ),
            published_at="2026-08-06T18:30:00+05:30",
            available_at="2026-08-06T18:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="EARNINGS",
            source_type="REGULATORY",
            source_name="Mahindra Exchange Filing (Recorded)",
            reliability_tier=1,
            verification_status="CONFIRMED",
            topic="quarterly_results",
            direction="NEUTRAL",
            confidence="0.95",
        ),
        _candidate(
            candidate_id="mahindra-intel-suv-launch",
            company=company,
            title="Mahindra launched the new-generation Thar.e SUV",
            body=(
                "Mahindra launched the new-generation Thar.e SUV in the "
                "domestic market, expanding its SUV portfolio. Order "
                "book details were not disclosed."
            ),
            published_at="2026-08-07T09:30:00+05:30",
            available_at="2026-08-07T09:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PRODUCT_LAUNCH",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="product_launches",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.90",
        ),
        _candidate(
            candidate_id="mahindra-intel-ev-partnership",
            company=company,
            title=(
                "Mahindra deepened its EV ecosystem partnership for "
                "last-mile mobility"
            ),
            body=(
                "Mahindra announced a deepened EV ecosystem partnership "
                "for last-mile mobility, covering battery and charging "
                "infrastructure. Commercial terms were not disclosed."
            ),
            published_at="2026-08-08T09:30:00+05:30",
            available_at="2026-08-08T09:30:00+05:30",
            kind="BUSINESS_EVENT",
            event_type="PARTNERSHIP",
            source_type="NEWS",
            source_name="Recorded Press Coverage",
            reliability_tier=2,
            verification_status="CONFIRMED",
            topic="ev_ecosystem",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.85",
        ),
        _candidate(
            candidate_id="mahindra-intel-management-demand",
            company=company,
            title=(
                "Mahindra management: SUV demand remains strong with a "
                "healthy order pipeline"
            ),
            body=(
                "On the Q1 earnings call, management said SUV demand "
                "remains strong with a healthy order pipeline. This is "
                "a management statement, not an independent fact."
            ),
            published_at="2026-08-06T20:30:00+05:30",
            available_at="2026-08-06T20:30:00+05:30",
            kind="MANAGEMENT_COMMENTARY",
            source_type="NEWS",
            source_name="Recorded Earnings Call Notes",
            reliability_tier=2,
            verification_status="REPORTED",
            topic="suv_demand",
            stance="SUPPORTIVE",
            direction="POSITIVE",
            confidence="0.70",
        ),
        _candidate(
            candidate_id="mahindra-intel-input-costs",
            company=company,
            title=(
                "Rising steel and battery prices were flagged as input "
                "cost risks"
            ),
            body=(
                "A recorded analysis flagged rising steel and battery "
                "prices as input cost risks for the auto sector. This "
                "is a reported claim."
            ),
            published_at="2026-08-09T09:00:00+05:30",
            available_at="2026-08-09T09:00:00+05:30",
            kind="RISK_DEVELOPMENT",
            source_type="NEWS",
            source_name="Recorded Sector Analysis",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="input_costs",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.50",
        ),
        _candidate(
            candidate_id="mahindra-intel-rural-demand",
            company=company,
            title=(
                "Rural demand recovery remains uneven across the auto "
                "sector"
            ),
            body=(
                "Outside-in sector reporting indicates rural demand "
                "recovery remains uneven across the auto sector. This "
                "is indirect, outside-in intelligence."
            ),
            published_at="2026-08-09T10:00:00+05:30",
            available_at="2026-08-09T10:00:00+05:30",
            kind="INDIRECT_INTELLIGENCE",
            source_type="NEWS",
            source_name="Recorded Sector Review",
            reliability_tier=3,
            verification_status="REPORTED",
            topic="rural_demand",
            stance="CONTRARY",
            direction="NEGATIVE",
            confidence="0.40",
        ),
        _future_candidate(company, name),
    ]


_BUILDERS = {
    "tcs": _tcs,
    "reliance": _reliance,
    "infy": _infy,
    "hdfcbank": _hdfcbank,
    "sunpharma": _sunpharma,
    "m&m": _mahindra,
}

_NAMES = {
    "tcs": "Tata Consultancy Services",
    "reliance": "Reliance Industries",
    "infy": "Infosys",
    "hdfcbank": "HDFC Bank",
    "sunpharma": "Sun Pharmaceutical Industries",
    "m&m": "Mahindra & Mahindra",
}


def build_fixture(company_key: str) -> dict:
    builder = _BUILDERS[company_key]

    candidates = builder()

    return {
        "company": candidates[0]["company"],
        "captured_at": CAPTURED_AT,
        "note": NOTE,
        "candidates": candidates,
    }


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    for key in sorted(_BUILDERS):
        fixture = build_fixture(key)

        target = FIXTURE_DIR / f"{key}_intel.json"

        target.write_text(
            json.dumps(
                fixture,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        written.append(target.name)

    for name in written:
        print(f"wrote fixtures/real_data/{name}")


if __name__ == "__main__":
    main()
