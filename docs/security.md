# CivicResolve AI - Security, Governance & Responsible AI Policy

## 1. Zero Unauthorized Actions Policy
Under no circumstances does CivicResolve AI autonomously submit complaints to government portals or dispatch external emails without affirmative, explicit human approval.
- Every action draft is held at the **Human Approval Gate**.
- Users must explicitly check the authorization checkbox before submission links and payloads become active.

## 2. Data Minimization & Privacy
- **No Sensitive Credential Storage**: CivicResolve AI never asks for bank passwords, ATM PINs, CVVs, or OTP codes.
- **Session Isolation**: Document uploads and complaints are linked to unique session identifiers and are never exposed across user boundaries.
- **Administrative Privacy Safeguards**: Administrator KPI dashboards only display aggregated performance metrics (classification accuracy, agent success rates) and never expose private invoices or user personal identities.

## 3. Provenance & Hallucination Defense
- RAG searches are restricted to verified government domains (`consumerrights.gov.ae`, `moec.gov.ae`, `u.ae`, `dubaidet.gov.ae`).
- Unverified third-party blogs or internet search snippets are strictly excluded.
- The Verification Agent checks statutory citations against known legislation before finalizing dossiers.
