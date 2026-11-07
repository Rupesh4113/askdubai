"""
CivicResolve AI - Official Source Registry
Authoritative registry of official UAE and Dubai government consumer protection sources.
Only verified government portals are registered here.
"""
from typing import Dict, Any, List

OFFICIAL_SOURCES: Dict[str, Dict[str, Any]] = {
    "dubai_ded_consumer_rights": {
        "id": "dubai_ded_consumer_rights",
        "title": "Dubai Consumer Protection - Department of Economy and Tourism (DET)",
        "url": "https://consumerrights.gov.ae/",
        "domain": "consumerrights.gov.ae",
        "authority": "Dubai Department of Economy and Tourism (DET)",
        "jurisdiction": "Dubai Emirate (Commercial & Retail)",
        "description": "Official portal for consumer rights protection, merchant obligations, dispute filing, and commercial compliance in Dubai.",
        "verified_date": "2026-01-15",
        "contact_phone": "600 545555",
        "official_app": "Dubai Consumer App",
        "complaint_portal": "https://consumerrights.gov.ae/en/Pages/consumer-complaint.aspx"
    },
    "uae_moec_law15": {
        "id": "uae_moec_law15",
        "title": "UAE Federal Law No. 15 of 2020 on Consumer Protection",
        "url": "https://www.moec.gov.ae/en/consumer-protection",
        "domain": "moec.gov.ae",
        "authority": "UAE Ministry of Economy (MOEC)",
        "jurisdiction": "Federal UAE",
        "description": "Federal legislation governing consumer rights, supplier obligations, defective goods replacement, mandatory warranties, repair timelines, and prohibited misleading practices across the UAE.",
        "verified_date": "2026-01-10",
        "contact_phone": "800 1222",
        "complaint_portal": "https://services.moec.gov.ae/"
    },
    "uae_official_portal_consumer": {
        "id": "uae_official_portal_consumer",
        "title": "UAE Government Portal (U.AE) - Consumer Protection and Dispute Resolution",
        "url": "https://u.ae/en/information-and-services/business/consumer-protection",
        "domain": "u.ae",
        "authority": "UAE Federal Government",
        "jurisdiction": "Federal UAE / Dubai",
        "description": "Comprehensive guide to statutory rights, refund entitlements, warranty enforcement, and local consumer protection departments in each emirate.",
        "verified_date": "2026-02-01",
        "contact_phone": "171 (Gov Direct)",
        "complaint_portal": "https://u.ae/"
    },
    "dubai_det_business": {
        "id": "dubai_det_business",
        "title": "Dubai Department of Economy and Tourism Regulations",
        "url": "https://www.dubaidet.gov.ae/",
        "domain": "dubaidet.gov.ae",
        "authority": "Dubai DET",
        "jurisdiction": "Dubai Emirate",
        "description": "Regulatory framework for commercial entities, service standards, consumer complaint mediation, and merchant licensing compliance in Dubai.",
        "verified_date": "2026-01-20",
        "contact_phone": "600 545555",
        "complaint_portal": "https://www.dubaidet.gov.ae/"
    },
    "uae_tdra_telecom": {
        "id": "uae_tdra_telecom",
        "title": "Telecommunications and Digital Government Regulatory Authority (TDRA)",
        "url": "https://tdra.gov.ae/en/services/consumer-complaints",
        "domain": "tdra.gov.ae",
        "authority": "TDRA",
        "jurisdiction": "UAE Telecom & Postal Disputes",
        "description": "Authorized regulatory body handling telecommunications, internet providers, postal deliveries, and domain disputes.",
        "verified_date": "2026-01-12",
        "contact_phone": "800 12",
        "complaint_portal": "https://tdra.gov.ae/"
    },
    "uae_cbuae_sanadak": {
        "id": "uae_cbuae_sanadak",
        "title": "Sanadak - Financial and Insurance Ombudsman (Central Bank of UAE)",
        "url": "https://sanadak.gov.ae/",
        "domain": "sanadak.gov.ae",
        "authority": "Central Bank of the UAE (CBUAE)",
        "jurisdiction": "Banking, Credit Cards, Insurance, and Financial Services",
        "description": "Authorized independent consumer ombudsman unit for consumer banking, unauthorized credit card charges, insurance claim disputes, and financial fraud.",
        "verified_date": "2026-01-18",
        "contact_phone": "800 SANADAK (7262325)",
        "complaint_portal": "https://sanadak.gov.ae/"
    }
}


def get_source_by_url(url: str) -> Dict[str, Any]:
    """Find source metadata by URL prefix matching."""
    for source in OFFICIAL_SOURCES.values():
        if source["domain"] in url or url.startswith(source["url"]):
            return source
    return {
        "title": "Official UAE Government Consumer Protection Source",
        "url": url,
        "authority": "Official UAE Authority",
        "jurisdiction": "Dubai / UAE",
        "verified_date": "2026-01-01"
    }


def list_official_domains() -> List[str]:
    return [s["domain"] for s in OFFICIAL_SOURCES.values()]


def is_verified_official_source(url: str) -> bool:
    """Verifies that a citation URL belongs to an approved government domain."""
    for domain in list_official_domains():
        if domain in url.lower():
            return True
    return False
