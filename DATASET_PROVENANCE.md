# AICTE VerifyAI — Data Provenance & Source Grounding Documentation

This document describes the data strategy, official public reference sources, verified statutory rule citations with exact excerpts, and synthetic demo datasets used in the **AICTE VerifyAI** frontend prototype for the Smart India Hackathon (SIH).

---

## 1. Data Strategy Architecture

The application strictly separates data into two isolated, clearly identified tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AICTE VerifyAI Data Tier                        │
├──────────────────────────────────┬─────────────────────────────────────┤
│   1. Public Reference Data       │   2. Synthetic Demo Data            │
│  • Official AICTE Directory      │  • Featured Fictional Case:         │
│  • APH 2024–2027 Regulations     │    "Northstar Institute of Tech"    │
│  • AISHE HEI Classifications     │  • Synthetic Document Artifacts     │
│  • Verified Public Facts Only    │  • Synthetic Demo Validation Rules  │
│  • NO synthetic findings/risks   │  • Visible SAMPLE / DEMO Badges     │
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 2. Public Reference Data Sources & Rule Grounding

### Source 1: AICTE Approved Institutes Public Web Dashboard
- **Issuing Authority**: All India Council for Technical Education (AICTE), Ministry of Education, Govt. of India
- **Source URL**: [https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php](https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php)
- **Applicable Academic Year**: Academic Year 2024–2025
- **Retrieval Date**: October 23, 2026 (Verified)
- **Extracted Fields**: Institution Legal Name, Permanent AICTE Institute ID, State, District/City, Sponsoring Body.
- **Privacy & Minimization Policy**: **Zero personal data collected**. No faculty names, student records, phone numbers, or staff details are imported.
- **Limitations**: Static directory reference snapshot. Official real-time approval status and annual Extension of Approval (EoA) orders are exclusively determined via AICTE's live portal.

### Source 2: AICTE Approval Process Handbook (APH) 2024–2027
- **Title**: Approval Process Handbook (APH) 2024–2025 to 2026–2027
- **Issuing Authority**: All India Council for Technical Education (AICTE)
- **Official Source URL**: [https://www.aicte-india.org/sites/default/files/approval/APH%202024-27.pdf](https://www.aicte-india.org/sites/default/files/approval/APH%202024-27.pdf)
- **Applicable Cycle**: 2024–2027
- **Retrieval Date**: October 23, 2026 (Verified)
- **Verified Statutory Provisions & Excerpts**:

  1. **Faculty Requirements, Cadre Ratio & Qualifications (§6.14 and Annexure 5.2)**:
     - *Citation*: Chapter VI, §6.14 and Annexure 5.2 (*Faculty Cadre and Qualifications for Degree Engineering and Technology*).
     - *Handbook Excerpt*:
       > "Cadre Ratio shall be 1 : 2 : 6 (Professor : Associate Professor : Assistant Professor). Faculty:Student Ratio for UG Degree Engineering: 1:20." — APH Annexure 5.2
     - *Qualifications Nuance*:
       - **Professor**: Ph.D. degree in the relevant discipline and minimum 10 years experience in teaching/research/industry.
       - **Associate Professor**: Ph.D. degree in the relevant discipline and minimum 5 years experience.
       - **Assistant Professor**: Bachelor's and Master's degree in the relevant branch with First Class. **Ph.D. is NOT a blanket requirement for entry-level Assistant Professors**.
     - *Demo Application*: In the Northstar case, candidate Dr. P. Sangeetha’s doctorate is in Mechanical Engineering ("Dynamic Thermal Dissipation"), which fails the domain-relevance requirement specifically for the proposed AI & Data Science Associate Professor cadre slot.

  2. **Land Requirements, Title Ownership & Encumbrance Status (§6.17 and Annexure 1)**:
     - *Citation*: Chapter VI, §6.17 and Annexure 1 (*Norms for Land and Built-up Area Requirements*).
     - *Handbook Excerpt*:
       > "The Promoter Society/Trust/Company/University shall have lawful possession of the land with clear, marketable title registered in its name on or before the date of submission of application... The land shall be continuous without any division and free from any unrecorded liabilities... Encumbrance Certificate issued by the competent Registration Authority is mandatory." — APH §6.17 & Annexure 1
       > "Mortgaging of institutional land is permitted ONLY after the issuance of Letter of Approval (LoA) and strictly for raising funds for the development of the technical institution situated on that specific land, with prior intimation to AICTE." — APH §6.17
     - *Demo Application*: Flags the historical entity title divergence between the 1998 registered deed ("Northstar Technical Institute") and the 2024 application ("Northstar Institute of Technology") under the same sponsoring trust.

  3. **Computational Facilities, Software & Laboratory Equipment (§6.19 and Annexure 4)**:
     - *Citation*: Chapter VI, §6.19 and Annexure 4 (*Norms for Books, Library facilities, Computer, Software, Internet, Printers and Laboratory Equipment of the Technical Institutions*).
     - *Handbook Excerpt*:
       > "Every Department shall have a separate Computer Laboratory with at least 20 computers (PCs/workstations)... The Institution shall have a Centralized Computer Centre with at least 100 computers... System and Application Software packages must be legal and licensed. PCs for Faculty, Library, and Administrative Office shall be over and above the student computer quotas." — APH Annexure 4
     - *(Note: Arbitrary/unsupported 1:6 ratio figure removed; statutory quota specifies 20 PCs per departmental lab and 100 PCs in the centralized computer centre).*

  4. **Specialized GPU / HPC Laboratory Verification (Segregated Citation)**:
     - *Classification*: **Synthetic Demo Rule (Institutional Self-Declaration Reconciliation)**.
     - *Handbook Boundary*: The AICTE Approval Process Handbook 2024–2027 does **NOT** mandate specific GPU models (e.g. NVIDIA RTX A6000) or high-performance compute clusters.
     - *Demo Grounding*: Finding #fnd-001b is an automated consistency check comparing self-declared specialized hardware on proforma (30 workstations) against physical on-site serial inspection (16 verified operational; 14 unaccounted for without delivery challans). It is explicitly designated as a **Synthetic Demo Validation Rule**, not an AICTE statutory mandate.

### Source 3: AISHE Higher Education Institution (HEI) Directory
- **Issuing Authority**: Department of Higher Education, Ministry of Education, Govt. of India
- **Source URL**: [https://aishe.gov.in/aishe/heiDirectory](https://aishe.gov.in/aishe/heiDirectory)
- **Applicable Year**: 2022–2024
- **Retrieval Date**: October 23, 2026 (Verified)
- **Extracted Fields**: National AISHE Code, Institution Management Category (Government, Aided, Private Autonomous), Affiliated University.
- **Critical Limitation Disclaimer**: **AISHE listing reflects educational census participation only; it does NOT constitute proof of active AICTE technical approval**.

---

## 3. Verified Factual Institutions in Reference Directory

The Public Reference Directory contains only verified factual metadata from official institutional mandatory disclosures and AICTE/AISHE records. **Zero synthetic findings, risk scores, or negative discrepancies are ever attached to these institutions.**

| Institution Name | Location | AICTE Permanent ID | AISHE Code | Management Category | Direct Official Source URL | Retrieval Date |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PSG College of Technology** | Coimbatore, Tamil Nadu | `1-4165514` | `C-41124` | Government Aided Autonomous College | [https://www.psgtech.edu/approval.php](https://www.psgtech.edu/approval.php) | 2026-10-23 |
| **COEP Technological University** | Pune, Maharashtra | `1-14626132` | `U-1175` | State Public Technological University | [https://www.coeptech.ac.in](https://www.coeptech.ac.in) | 2026-10-23 |
| **Delhi Technological University (DTU)** | New Delhi, Delhi | `1-837103261` | `U-0098` | State Public Technological University | [https://www.dtu.ac.in](https://www.dtu.ac.in) | 2026-10-23 |
| **Veermata Jijabai Technological Institute (VJTI)** | Mumbai, Maharashtra | `1-5149491` | `C-34082` | Government Aided Autonomous Institute | [https://vjti.ac.in](https://vjti.ac.in) | 2026-10-23 |
| **Jadavpur University (Faculty of Engineering)** | Kolkata, West Bengal | `1-21569051` | `U-0573` | State Public University Faculty | [https://jadavpuruniversity.in](https://jadavpuruniversity.in) | 2026-10-23 |
| **BMS College of Engineering** | Bengaluru, Karnataka | `1-5884543` | `C-20924` | Private Autonomous College | [https://bmsce.ac.in/home/Mandatory-Disclosure](https://bmsce.ac.in/home/Mandatory-Disclosure) | 2026-10-23 |

*Note: Dynamic approved program counts and annual extensions of approval (EoA) vary by cycle and must be referenced directly from live AICTE portal queries rather than static extracts.*

---

## 4. Synthetic Demo Applications & The Fictional Case

### Featured Primary Case: Northstar Institute of Technology
- **Institution**: **Northstar Institute of Technology** (Fictional Institution)
- **Location**: Bengaluru, Karnataka (Simulated address: Tech Knowledge Park, Whitefield Extension)
- **Application ID**: `DEMO/2024-25/NPA/KA/001842`
- **Application Category**: `New Program Approval — B.Tech Artificial Intelligence & Data Science (Intake: 60)`
- **Priority Score**: `91 / 100` (Heuristic Priority Score)
- **Review Status**: `Escalated` (Simulated case requiring human scrutiny)

### Ethical Rule on Real Institutions
> **Mandatory Ethical Constraint**:
> **Never attach invented findings, risk scores, discrepancies, or regulatory sanctions to a real institution.**
> All active review cases, documents, discrepancies, and findings are strictly attached to fictional demo institutions (**Northstar Institute of Technology**, **Apex Technical Academy**, **Zenith Institute of Engineering**, **Horizon Institute**, **Vanguard Institute**).

### Synthetic Document Mockups & Disclaimers
1. **Document Watermark**: Every document mockup visibly displays:
   `SAMPLE / DEMO — NOT AN OFFICIAL CERTIFICATE`
2. **No Real Government Seals**: Document mockups use synthetic neutral styling and explicitly state:
   *"Fictional document generated for SIH VerifyAI evaluation only. Not an official regulatory instrument."*
3. **Cryptographic File-Integrity Checksums**:
   SHA-256 hashes are presented strictly as **file-integrity identifiers** (verifying that the binary file has not changed since upload). The system explicitly disclaims that hashes prove real-world authenticity or issuing authority.
4. **Advisory Heuristics**:
   All findings are labeled as advisory flags for human reviewer consideration, explicitly avoiding accusations of fraud.

---

## 5. Active Backend & API Contract Status

The active backend runs at `http://localhost:8000` via FastAPI (`backend/app/main.py`), with persistent SQLite storage (`backend/verifyai.db`). Routes are exposed symmetrically under both `/api` and `/api/v1` for seamless client communication.

---

## 6. Strict Data Classification & Provenance Architecture

VerifyAI explicitly tracks the origin, purpose, and classification tier of every record in the database:

1. **`SYNTHETIC_DEMO`**:
   - **Definition**: Synthetically generated demonstration submissions, documents, and compliance findings created for demonstration and testing.
   - **Primary Featured Case**: *Northstar Institute of Technology* (`DEMO/2024-25/NPA/KA/001842`).
   - **Safeguard**: Clearly badged as `SAMPLE / DEMO` in the UI and marked with `is_synthetic_demo = True` in the database. Never mixed with real data.

2. **`PUBLIC_REFERENCE`**:
   - **Definition**: Authentic institution directory records imported from verified, published public datasets (AICTE Approved Institutes Dashboard & AISHE Directory).
   - **Content**: Permanent AICTE Institute ID, Legal Institution Name, State, City, Management Type, Academic Year, Official Source URL, Retrieval Date, and SHA-256 Content Checksum.
   - **Scope**: Used strictly for statutory entity verification and rule citations. Zero synthetic violations, risk scores, or negative discrepancies are ever attached to public reference institutions.

3. **`AUTHENTIC_APPLICATION`**:
   - **Definition**: Real institutional approval applications submitted through authorized official AICTE portal workflows.
   - **Current Status**: Isolated / zero records connected. Because confidential institutional dossiers (affidavits, land registry deeds, pan cards, fee challans) require live institutional API integration and confidential credentials, this tier is kept distinct. VerifyAI transparently reports **0 submitted applications** in Real Data mode rather than fabricating real submissions or misrepresenting directory entries as applications.

---

## 7. Verified Public Dataset Import Pipeline

A reproducible, automated, and idempotent data import pipeline is located at [`backend/app/services/dataset_importer.py`](file:///c:/Users/Adhav/Downloads/AICTE-VerifyAI-2/backend/app/services/dataset_importer.py).

### Commands & Execution

- **Dry-run validation mode (no database writes)**:
  ```bash
  python -m app.services.dataset_importer --dry-run
  ```
- **Live ingestion into `public_reference_institutions` table**:
  ```bash
  python -m app.services.dataset_importer
  ```
- **Custom dataset file import**:
  ```bash
  python -m app.services.dataset_importer --file path/to/dataset.json
  ```

### Validation & Ingestion Rules

1. **Required Column Validation**: Each record must contain `aicte_permanent_id`, `institution_name`, `state`, `city_or_district`, `institution_type`, `source_publisher`, and `source_url`.
2. **Format Normalization**:
   - AICTE Permanent IDs are validated against regex `^1-\d{5,12}$`.
   - String normalization trims excess whitespace and harmonizes state/district naming.
3. **Cryptographic Content Checksum**:
   - Each record receives a deterministic SHA-256 hash computed over canonical fields (`aicte_permanent_id | institution_name | state | city_or_district | institution_type | academic_year`).
   - The entire import batch receives an aggregate batch checksum.
4. **Deduplication & Idempotency**:
   - Deduplication uses `aicte_permanent_id` as the primary natural key.
   - Rerunning the import multiple times on identical records produces `0 accepted, 0 updated, N skipped`, preventing duplicate rows.
   - Changes in source fields trigger non-destructive updates without touching synthetic or reviewer data.
5. **Transactional Safety**:
   - Database writes execute inside transactional session blocks with automatic rollback on error.

---

## 8. Real Data / Synthetic Data Toggle Specification

The top of the Overview Control Room features an interactive **[ Real Data ] [ Synthetic Data ]** toggle styled according to the Cherry Blossom Noir design system:

- **Synthetic Data Mode**:
  - Displays the 30 synthetic demo submissions (`sub-001` through `sub-030`).
  - Renders synthetic metrics (Total: 30, Pending: 18, Escalated: 4, Approved: 12, Critical: 8).
  - Renders Highest-Priority Cases list, Compact Case Summary panel, Pipeline Stage Progress, and Audit Event Feed.
  - Distinctly labeled with `SAMPLE / DEMO · Simulated Compliance Cycle`.

- **Real Data Mode**:
  - Displays **0 submitted applications** (genuine zero metrics), preventing any misrepresentation of directory data as submitted applications.
  - Displays the **Verified Public Reference Directory Table** showing real institutions with permanent AICTE IDs, state/city location, academic year, approval status, official source link, and SHA-256 verification status.
  - Includes instant search (by name, city, or AICTE ID) and state filtering.
  - Displays a dedicated Informative Alert Banner explaining that authentic application data has not yet been connected.

- **Data Separation & Isolation**:
  - Synthetic records and authentic reference records reside in separate database models (`applications` vs `public_reference_institutions`).
  - Switching modes only toggles the active view scope; it never mutates, overwrites, or deletes records.

---

## 9. Data Quality & Integrity Insights

VerifyAI includes automated data quality monitoring for public reference data:

- **Missing Required Fields**: 0 (100% complete for all required fields).
- **Duplicate Identifiers**: 0 (all AICTE Permanent IDs verified unique).
- **Checksum Verification**: PASS (SHA-256 canonical hashing verified).
- **Data Minimization Policy**: Zero personal faculty or student PII is imported or retained from public directories.

