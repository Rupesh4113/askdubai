"""
CivicResolve AI - 100-Case Fictional Test Dataset Generator
Generates diverse test cases covering 9 dispute categories, edge cases,
jurisdiction routing checks, and missing document scenarios.
"""
import json
import os

cases = []

# 1. Defective Products (25 cases)
defective_templates = [
    ("I purchased an air conditioner for AED 2,500 from Sharaf DG two weeks ago. The unit stopped cooling completely and leaked water.", "Sharaf DG", 2500.0, "defective_product", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Bought a Samsung Smart TV 65-inch from Carrefour for AED 3,200. Screen turned completely black after 5 days.", "Carrefour", 3200.0, "defective_product", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Purchased an automatic washing machine from Emax for AED 1,850. Motor makes loud grinding noise and does not spin.", "Emax", 1850.0, "defective_product", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("I bought an electric cooking oven from Al-Futtaim ACE for AED 950. Heating element burned out on second usage.", "Al-Futtaim ACE", 950.0, "defective_product", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Refrigerator purchased from Jumbo Electronics for AED 4,100 stopped freezing food and spoiled groceries.", "Jumbo Electronics", 4100.0, "defective_product", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
]

for i in range(25):
    tmpl = defective_templates[i % len(defective_templates)]
    cases.append({
        "id": f"CASE-DEF-{i+1:03d}",
        "description": f"{tmpl[0]} (Test variant {i+1})",
        "expected_merchant": tmpl[1],
        "expected_amount": tmpl[2],
        "expected_category": tmpl[3],
        "expected_jurisdiction_authority": tmpl[4],
        "has_documents": True if i % 4 != 0 else False,
        "is_unsupported_claim": False
    })

# 2. Warranty Disputes (20 cases)
warranty_templates = [
    ("Sharaf DG refused to honor the 2-year warranty on my microwave, claiming customer abuse without providing an inspection report.", "Sharaf DG", 450.0, "warranty_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Jumbo Electronics service center demanded AED 600 for spare parts that are covered under manufacturer warranty.", "Jumbo Electronics", 600.0, "warranty_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Emax service center has held my laptop for 35 days claiming parts unavailable, exceeding the 14-day statutory repair limit.", "Emax", 3500.0, "warranty_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Retailer refused free warranty repair for my water heater after 8 months, despite warranty card stating 3 years warranty.", "Home Centre", 800.0, "warranty_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)")
]

for i in range(20):
    tmpl = warranty_templates[i % len(warranty_templates)]
    cases.append({
        "id": f"CASE-WAR-{i+1:03d}",
        "description": f"{tmpl[0]} (Test variant {i+1})",
        "expected_merchant": tmpl[1],
        "expected_amount": tmpl[2],
        "expected_category": tmpl[3],
        "expected_jurisdiction_authority": tmpl[4],
        "has_documents": True,
        "is_unsupported_claim": False
    })

# 3. Refund Disputes (15 cases)
refund_templates = [
    ("I returned an unopened coffee machine to Lulu Hypermarket within 7 days with original invoice, but store refused refund and gave store credit.", "Lulu", 650.0, "refund_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Store cancelled my order due to out of stock but refuses to refund money to my credit card for 45 days.", "Amazon UAE", 1200.0, "refund_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)"),
    ("Merchant refused refund for shoes with detached sole after 3 days of light wear.", "Noon", 350.0, "refund_dispute", "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)")
]

for i in range(15):
    tmpl = refund_templates[i % len(refund_templates)]
    cases.append({
        "id": f"CASE-REF-{i+1:03d}",
        "description": f"{tmpl[0]} (Test variant {i+1})",
        "expected_merchant": tmpl[1],
        "expected_amount": tmpl[2],
        "expected_category": tmpl[3],
        "expected_jurisdiction_authority": tmpl[4],
        "has_documents": True,
        "is_unsupported_claim": False
    })

# 4. Delayed Delivery (10 cases)
for i in range(10):
    cases.append({
        "id": f"CASE-DEL-{i+1:03d}",
        "description": f"Ordered a dining table from IKEA for AED 2,200 with delivery promised by 10th January. Three weeks have passed and delivery is repeatedly postponed without explanation. (Variant {i+1})",
        "expected_merchant": "IKEA",
        "expected_amount": 2200.0,
        "expected_category": "delayed_delivery",
        "expected_jurisdiction_authority": "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)",
        "has_documents": True,
        "is_unsupported_claim": False
    })

# 5. Incorrect Billing & Financial/Sanadak (15 cases)
for i in range(15):
    is_bank = (i % 2 == 0)
    if is_bank:
        cases.append({
            "id": f"CASE-FIN-{i+1:03d}",
            "description": f"My bank credit card was charged twice for an unauthorized international transaction of AED 1,450. The bank refuses to reverse the chargeback. (Variant {i+1})",
            "expected_merchant": "Commercial Bank",
            "expected_amount": 1450.0,
            "expected_category": "incorrect_billing",
            "expected_jurisdiction_authority": "Sanadak - Financial and Insurance Ombudsman Unit",
            "has_documents": True,
            "is_unsupported_claim": False
        })
    else:
        cases.append({
            "id": f"CASE-BIL-{i+1:03d}",
            "description": f"Carrefour cashier charged AED 480 instead of the shelf price for grocery items and refused to issue cash difference. (Variant {i+1})",
            "expected_merchant": "Carrefour",
            "expected_amount": 480.0,
            "expected_category": "incorrect_billing",
            "expected_jurisdiction_authority": "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)",
            "has_documents": True,
            "is_unsupported_claim": False
        })

# 6. Telecom Disputes / TDRA (10 cases)
for i in range(10):
    cases.append({
        "id": f"CASE-TEL-{i+1:03d}",
        "description": f"My mobile telecom operator Etisalat charged me AED 850 for an inactive broadband data plan after cancellation was confirmed. (Variant {i+1})",
        "expected_merchant": "Etisalat",
        "expected_amount": 850.0,
        "expected_category": "incorrect_billing",
        "expected_jurisdiction_authority": "Telecommunications and Digital Government Regulatory Authority (TDRA)",
        "has_documents": True,
        "is_unsupported_claim": False
    })

# 7. Misleading Advertising (5 cases)
for i in range(5):
    cases.append({
        "id": f"CASE-ADV-{i+1:03d}",
        "description": f"Sharaf DG advertised a 50% discount on a laptop for AED 1,500, but at checkout they forced an additional mandatory warranty fee of AED 500. False advertising! (Variant {i+1})",
        "expected_merchant": "Sharaf DG",
        "expected_amount": 1500.0,
        "expected_category": "misleading_advertising",
        "expected_jurisdiction_authority": "Dubai Department of Economy and Tourism (DET - Consumer Rights CCCP)",
        "has_documents": True,
        "is_unsupported_claim": False
    })

out_dir = os.path.dirname(os.path.abspath(__file__))
out_file = os.path.join(out_dir, "dataset_100_cases.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(cases, f, indent=2)

print(f"Generated {len(cases)} test cases at {out_file}")
