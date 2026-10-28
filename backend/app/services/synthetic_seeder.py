"""
Synthetic Demo Seeder for AICTE VerifyAI.
Populates applications, documents, validation findings, reviewer notes,
cross-document comparisons, and baseline audit events into the active database.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatus,
    AuditEvent,
    CrossDocComparison,
    DataClassification,
    Document,
    DocumentProcessingStatus,
    FindingReviewStatus,
    FindingSeverity,
    ReviewerNote,
    ValidationFinding,
)


def _parse_iso(iso_str: str) -> datetime:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def seed_synthetic_applications_if_empty(db: Session, force: bool = False) -> int:
    """
    Seed 30 coherent synthetic demo applications if the applications table is empty.
    Preserves all existing records if applications already exist (unless force=True).
    """
    existing_count = db.query(Application).count()
    if existing_count >= 25 and not force:
        return existing_count

    print(f"[VerifyAI Seeder] Seeding synthetic applications (existing: {existing_count})...")

    # Clean up synthetic records if forcing
    if force and existing_count > 0:
        db.query(AuditEvent).filter(AuditEvent.application_id.like("sub-%")).delete(synchronize_session=False)
        db.query(ReviewerNote).delete(synchronize_session=False)
        db.query(CrossDocComparison).delete(synchronize_session=False)
        db.query(ValidationFinding).delete(synchronize_session=False)
        db.query(Document).delete(synchronize_session=False)
        db.query(Application).filter(Application.is_synthetic_demo == True).delete(synchronize_session=False)
        db.commit()

    institutions_meta = {
        "inst-001": ("Northstar Institute of Technology", "Bengaluru", "Karnataka", "college", "DEMO-KA-ENG-2015-88"),
        "inst-002": ("Zenith Institute of Engineering & Technology", "Pune", "Maharashtra", "college", "DEMO-MH-ENG-2008-11"),
        "inst-003": ("Apex Technical Academy", "Coimbatore", "Tamil Nadu", "college", "DEMO-TN-ENG-1994-41"),
        "inst-004": ("Horizon Institute of Technology", "New Delhi", "Delhi", "university", "DEMO-DL-ENG-2011-01"),
        "inst-005": ("Vanguard Institute of Engineering", "Jaipur", "Rajasthan", "university", "DEMO-RJ-ENG-2009-03"),
        "inst-006": ("Summit Institute of Technology", "Ahmedabad", "Gujarat", "deemed", "DEMO-GJ-ENG-2016-07"),
        "inst-007": ("Pinnacle Institute of Technology", "Kolkata", "West Bengal", "college", "DEMO-WB-ENG-2010-52"),
        "inst-008": ("Deccan College of Engineering & Research", "Hyderabad", "Telangana", "college", "DEMO-TS-ENG-2005-22"),
        "inst-009": ("Malabar Institute of Technology", "Kozhikode", "Kerala", "college", "DEMO-KL-ENG-2012-39"),
        "inst-010": ("Kalinga Academy of Technical Sciences", "Bhubaneswar", "Odisha", "university", "DEMO-OD-ENG-2007-15"),
        "inst-011": ("Shivalik Institute of Engineering & Technology", "Chandigarh", "Punjab", "college", "DEMO-PB-ENG-2014-63"),
        "inst-012": ("Bundelkhand Polytechnic Institute", "Jhansi", "Uttar Pradesh", "polytechnic", "DEMO-UP-POLY-2013-18"),
        "inst-013": ("Royal College of Architecture & Planning", "Bhopal", "Madhya Pradesh", "college", "DEMO-MP-ARCH-2018-04"),
        "inst-014": ("Brahmaputra Valley Technical Institute", "Guwahati", "Assam", "college", "DEMO-AS-ENG-2009-31"),
        "inst-015": ("Metro Institute of Management Studies", "Gurugram", "Haryana", "college", "DEMO-HR-MGT-2011-82"),
        "inst-016": ("Vidarbha Institute of Technology", "Nagpur", "Maharashtra", "college", "DEMO-MH-ENG-2004-55"),
        "inst-017": ("Cauvery College of Engineering", "Mysuru", "Karnataka", "college", "DEMO-KA-ENG-2013-19"),
        "inst-018": ("Thar Desert Technical University", "Jodhpur", "Rajasthan", "university", "DEMO-RJ-ENG-2017-09"),
        "inst-019": ("Coromandel Institute of Maritime Studies", "Chennai", "Tamil Nadu", "college", "DEMO-TN-ENG-2009-84"),
        "inst-020": ("Gomti Institute of Pharmacy & Allied Sciences", "Lucknow", "Uttar Pradesh", "college", "DEMO-UP-PHARM-2015-77"),
        "inst-021": ("Nilgiri Polytechnic College", "Ooty", "Tamil Nadu", "polytechnic", "DEMO-TN-POLY-1998-12"),
        "inst-022": ("Chanakya Management Academy", "Patna", "Bihar", "college", "DEMO-BR-MGT-2016-44"),
        "inst-023": ("Western Ghats Institute of Technology", "Mangaluru", "Karnataka", "college", "DEMO-KA-ENG-2010-73"),
        "inst-024": ("Sabarmati College of Engineering", "Surat", "Gujarat", "college", "DEMO-GJ-ENG-2008-88"),
        "inst-025": ("Vindhya Institute of Technology", "Indore", "Madhya Pradesh", "college", "DEMO-MP-ENG-2016-51"),
        "inst-026": ("Godavari Institute of Technical Studies", "Rajahmundry", "Andhra Pradesh", "college", "DEMO-AP-ENG-2015-19"),
        "inst-027": ("Rohtak College of Engineering", "Rohtak", "Haryana", "college", "DEMO-HR-ENG-2012-61"),
        "inst-028": ("Konkan Institute of Technology", "Ratnagiri", "Maharashtra", "college", "DEMO-MH-ENG-2014-38"),
        "inst-029": ("Siliguri Institute of Technology & Management", "Siliguri", "West Bengal", "college", "DEMO-WB-ENG-2011-29"),
        "inst-030": ("Capital Engineering College", "Dehradun", "Uttarakhand", "college", "DEMO-UK-ENG-2015-42"),
    }

    submissions_meta = [
        ("sub-001", "DEMO/2026-27/NPA/KA/001842", "inst-001", "2026-10-12T09:15:00Z", "2026-10-24T14:30:00Z", "escalated", "New Program Approval — B.Tech AI & DS", "Priya Venkataraman", 91, "2026-11-05T00:00:00Z", "Critical doctoral qualification gap for proposed Associate Professor cadre; disputed GPU workstation inventory."),
        ("sub-002", "DEMO/2026-27/ACF/MH/003317", "inst-002", "2026-10-14T11:45:00Z", "2026-10-25T10:00:00Z", "under_review", "Annual Compliance Filing", "Priya Venkataraman", 68, "2026-11-15T00:00:00Z", "Tuition fee disclosure mismatch flagged during website automated crawl."),
        ("sub-003", "DEMO/2026-27/EXT/TN/007891", "inst-003", "2026-10-08T08:30:00Z", "2026-10-25T16:00:00Z", "approved", "Intake Extension — MBA (60 seats)", "Ramesh Iyer", 22, "2026-11-01T00:00:00Z", "All proformas verified; MBA intake expansion recommended for approval."),
        ("sub-004", "DEMO/2026-27/NPA/DL/002254", "inst-004", "2026-10-18T14:00:00Z", "2026-10-25T11:30:00Z", "pending_review", "New Program Approval — M.Tech Robotics", "Unassigned", 55, "2026-11-20T00:00:00Z", "Initial triage complete; pending reviewer assignment."),
        ("sub-005", "DEMO/2026-27/ACF/RJ/005502", "inst-005", "2026-10-10T10:00:00Z", "2026-10-24T16:00:00Z", "on_hold", "Annual Compliance Filing", "Sunita Sharma", 74, "2026-11-10T00:00:00Z", "Awaiting university affiliation renewal certificate and anti-ragging committee reconstitution."),
        ("sub-006", "DEMO/2026-27/NPA/GJ/009103", "inst-006", "2026-10-19T13:00:00Z", "2026-10-25T14:00:00Z", "pending_review", "New Program Approval — B.Des Interaction Design", "Unassigned", 41, "2026-11-25T00:00:00Z", "Awaiting initial automated syllabus and studio facility validation."),
        ("sub-007", "DEMO/2026-27/ACF/WB/006614", "inst-007", "2026-10-09T09:00:00Z", "2026-10-24T13:00:00Z", "rejected", "Annual Compliance Filing", "Ramesh Iyer", 15, "2026-10-28T00:00:00Z", "Application rejected: Persistent statutory financial audit non-compliance after three notice cycles."),
        ("sub-008", "DEMO/2026-27/EOA/TS/004812", "inst-008", "2026-10-11T10:20:00Z", "2026-10-25T11:00:00Z", "escalated", "Extension of Approval (EoA) — Engineering", "Priya Venkataraman", 88, "2026-11-04T00:00:00Z", "Escalated for senior legal review: Bank mortgage lien detected on campus parcel Survey No. 48/2."),
        ("sub-009", "DEMO/2026-27/EXT/KL/002341", "inst-009", "2026-10-13T12:00:00Z", "2026-10-25T15:20:00Z", "under_review", "Increase in Intake — B.Tech CSE (60 to 120)", "Sunita Sharma", 62, "2026-11-12T00:00:00Z", "Teacher Student Ratio computes to 1:24 vs mandated 1:20 under proposed 120-seat expansion."),
        ("sub-010", "DEMO/2026-27/EOA/OD/005118", "inst-010", "2026-10-07T11:00:00Z", "2026-10-24T18:00:00Z", "approved", "Extension of Approval (EoA) — All Programs", "Ramesh Iyer", 20, "2026-11-02T00:00:00Z", "All NAAC A++ and NBA accreditations valid; clean annual renewal approved."),
        ("sub-011", "DEMO/2026-27/NPA/PB/003890", "inst-011", "2026-10-17T09:30:00Z", "2026-10-25T13:45:00Z", "pending_review", "New Program Approval — B.Tech Data Analytics", "Unassigned", 48, "2026-11-18T00:00:00Z", "Broken grievance redressal URL flagged during intake crawl."),
        ("sub-012", "DEMO/2026-27/EXT/UP/004412", "inst-012", "2026-10-12T14:15:00Z", "2026-10-25T12:00:00Z", "on_hold", "Diploma in Electrical Engineering Extension", "Priya Venkataraman", 71, "2026-11-08T00:00:00Z", "Awaiting State Technical Education Board curriculum concurrence renewal order."),
        ("sub-013", "DEMO/2026-27/NPA/MP/001920", "inst-013", "2026-10-15T15:00:00Z", "2026-10-25T14:30:00Z", "under_review", "New Program Approval — B.Arch (40 seats)", "Sunita Sharma", 58, "2026-11-16T00:00:00Z", "Drafting studio floor area shortfall flagged against Council of Architecture norms."),
        ("sub-014", "DEMO/2026-27/EOA/AS/008819", "inst-014", "2026-10-06T10:00:00Z", "2026-10-24T17:00:00Z", "approved", "Annual Extension of Approval (EoA)", "Ramesh Iyer", 18, "2026-11-01T00:00:00Z", "Dossier scrutiny cleared; clean annual renewal recommended."),
        ("sub-015", "DEMO/2026-27/ACF/HR/007321", "inst-015", "2026-10-11T13:45:00Z", "2026-10-25T16:15:00Z", "escalated", "Annual Compliance Filing — PGDM", "Priya Venkataraman", 85, "2026-11-03T00:00:00Z", "Director doctoral qualification issued by foreign institution without AIU equivalence."),
        ("sub-016", "DEMO/2026-27/EOA/MH/002241", "inst-016", "2026-10-08T09:20:00Z", "2026-10-25T11:00:00Z", "approved", "Annual Extension of Approval", "Ramesh Iyer", 24, "2026-11-04T00:00:00Z", "Statutory financial returns and faculty ratios verified satisfactorily."),
        ("sub-017", "DEMO/2026-27/ACF/KA/003889", "inst-017", "2026-10-14T16:00:00Z", "2026-10-25T10:30:00Z", "under_review", "Annual Compliance Filing", "Sunita Sharma", 64, "2026-11-14T00:00:00Z", "Central computing facility has 82 operational PC terminals vs statutory minimum of 100."),
        ("sub-018", "DEMO/2026-27/NPA/RJ/001102", "inst-018", "2026-10-05T08:00:00Z", "2026-10-24T12:00:00Z", "rejected", "New Technical Campus Establishment", "Ramesh Iyer", 12, "2026-10-26T00:00:00Z", "Application rejected: Fire NOC revoked and non-contiguous land parcel exceed statutory limits."),
        ("sub-019", "DEMO/2026-27/ACF/TN/006122", "inst-019", "2026-10-20T10:45:00Z", "2026-10-25T11:00:00Z", "pending_review", "Annual Compliance Filing — Marine Engg", "Unassigned", 38, "2026-11-28T00:00:00Z", "Automated document ingestion complete; queued for technical scrutinizer."),
        ("sub-020", "DEMO/2026-27/ACF/UP/005510", "inst-020", "2026-10-13T14:00:00Z", "2026-10-25T14:40:00Z", "on_hold", "Annual Compliance — B.Pharm", "Sunita Sharma", 69, "2026-11-09T00:00:00Z", "PCI annual compliance certificate awaited from regulatory body."),
        ("sub-021", "DEMO/2026-27/EOA/TN/003418", "inst-021", "2026-10-09T11:20:00Z", "2026-10-24T15:30:00Z", "approved", "Extension of Approval — Diploma Courses", "Ramesh Iyer", 19, "2026-11-05T00:00:00Z", "Polytechnic annual extension approved; all workshops inspected and cleared."),
        ("sub-022", "DEMO/2026-27/ACF/BR/008129", "inst-022", "2026-10-18T16:00:00Z", "2026-10-25T12:30:00Z", "pending_review", "Annual Compliance Filing — MBA", "Unassigned", 45, "2026-11-22T00:00:00Z", "Minor website ICC disclosure discrepancy noted."),
        ("sub-023", "DEMO/2026-27/EXT/KA/004921", "inst-023", "2026-10-14T10:00:00Z", "2026-10-25T16:00:00Z", "under_review", "Intake Extension — B.Tech ECE (60 seats)", "Priya Venkataraman", 60, "2026-11-13T00:00:00Z", "Advanced VLSI test bench calibration certificates requested from applicant."),
        ("sub-024", "DEMO/2026-27/EOA/GJ/003310", "inst-024", "2026-10-09T13:30:00Z", "2026-10-24T16:45:00Z", "approved", "Annual Extension of Approval", "Ramesh Iyer", 25, "2026-11-06T00:00:00Z", "Engineering programs cleared with continuous NAAC accreditation."),
        ("sub-025", "DEMO/2026-27/NPA/MP/002298", "inst-025", "2026-10-06T14:00:00Z", "2026-10-24T11:00:00Z", "rejected", "New Program Approval — B.Tech Civil", "Ramesh Iyer", 14, "2026-10-27T00:00:00Z", "Rejected: Inauthentic municipal occupancy certificate detected during civic ledger verification."),
        ("sub-026", "DEMO/2026-27/NPA/AP/007712", "inst-026", "2026-10-21T11:30:00Z", "2026-10-25T13:00:00Z", "pending_review", "New Program Approval — B.Tech Cyber Security", "Unassigned", 39, "2026-11-26T00:00:00Z", "Cybersecurity curriculum and lab network isolation dossier in review queue."),
        ("sub-027", "DEMO/2026-27/ACF/HR/001929", "inst-027", "2026-10-13T10:15:00Z", "2026-10-25T15:00:00Z", "on_hold", "Annual Compliance Filing", "Sunita Sharma", 72, "2026-11-11T00:00:00Z", "Awaiting certified bank salary disbursement statements for Q1 and Q2."),
        ("sub-028", "DEMO/2026-27/ACF/MH/004819", "inst-028", "2026-10-16T14:30:00Z", "2026-10-25T11:15:00Z", "under_review", "Annual Compliance Filing", "Priya Venkataraman", 56, "2026-11-17T00:00:00Z", "Campus leased line bandwidth shows 80 Mbps vs 100 Mbps mandatory quota."),
        ("sub-029", "DEMO/2026-27/EOA/WB/006190", "inst-029", "2026-10-08T11:00:00Z", "2026-10-24T14:00:00Z", "approved", "Annual Extension of Approval", "Ramesh Iyer", 21, "2026-11-05T00:00:00Z", "Technical and management streams cleared without deficiency."),
        ("sub-030", "DEMO/2026-27/NPA/UK/003821", "inst-030", "2026-10-20T15:00:00Z", "2026-10-25T14:00:00Z", "pending_review", "New Program Approval — B.Tech Artificial Intelligence", "Unassigned", 44, "2026-11-27T00:00:00Z", "Emerging technology proposal queued for Expert Scrutiny Committee assignment."),
    ]

    status_map = {
        "escalated": ApplicationStatus.UNDER_REVIEW,
        "under_review": ApplicationStatus.UNDER_REVIEW,
        "approved": ApplicationStatus.VALIDATED,
        "pending_review": ApplicationStatus.SUBMITTED,
        "on_hold": ApplicationStatus.REQUIRES_CLARIFICATION,
        "rejected": ApplicationStatus.REJECTED,
    }

    # 1. Insert Applications
    for s_id, app_num, i_id, sub_at, up_at, st, cat, ass_to, score, due, notes in submissions_meta:
        inst_name, city, state, itype, aicte_id = institutions_meta[i_id]
        app_obj = Application(
            id=s_id,
            application_number=app_num,
            institution_name=inst_name,
            institution_city=city,
            institution_state=state,
            institution_type=itype,
            aicte_id=aicte_id,
            application_category=cat,
            academic_year="2026-2027",
            status=status_map.get(st, ApplicationStatus.SUBMITTED),
            created_at=_parse_iso(sub_at),
            updated_at=_parse_iso(up_at),
            review_status=st,
            review_notes=notes,
            reviewer_actor=ass_to if ass_to != "Unassigned" else None,
            priority_score=score,
            due_date=due[:10],
            data_classification=DataClassification.SYNTHETIC_DEMO.value,
            is_synthetic_demo=True,
            source_name="AICTE VerifyAI Synthetic Scenario Suite",
            source_record_id=s_id,
            import_batch_id="SYNTH-DEMO-2026-V1",
        )
        db.add(app_obj)

    db.flush()

    # 2. Documents for sub-001 (Northstar)
    ev1a_content = {
        "documentId": "ev-001a",
        "headerTitle": "[SAMPLE / DEMO] GOVERNMENT OF KARNATAKA — HIGHER EDUCATION DEPARTMENT",
        "subHeader": "Directorate of Technical Education · No Objection Certificate (NOC) Proforma",
        "referenceNo": "ED/DTE/NOC/2024/BLR-0198",
        "issueDate": "12 October 2024",
        "issuingAuthority": "Directorate of Technical Education, Bengaluru",
        "sealText": "GOVERNMENT OF KARNATAKA · TECHNICAL EDUCATION SECRETARIAT",
        "pages": [
            {
                "pageNumber": 1,
                "paragraphs": [
                    {
                        "id": "p-noc-1",
                        "text": "1. STATE CLEARANCE: The Government of Karnataka conveys 'No Objection' for introduction of B.Tech in Artificial Intelligence & Data Science with an annual intake of sixty (60) seats at Northstar Institute of Technology, Knowledge Park, Whitefield Extension, Bengaluru.",
                        "isDiscrepancy": False,
                    },
                    {
                        "id": "p-noc-2",
                        "text": "2. REGULATORY CONDITIONALITY: This clearance is strictly subject to adherence to AICTE Approval Process Handbook (APH) 2024–2027 statutory provisions, including prescribed Faculty Cadre ratios (1:2:6) and mandatory doctoral qualifications under §6.14.",
                        "isDiscrepancy": False,
                    },
                ],
            }
        ],
    }

    ev1b_content = {
        "documentId": "ev-001b",
        "headerTitle": "[SAMPLE / DEMO] EXPERT VISIT COMMITTEE (EVC) — REGIONAL INSPECTION RECORD",
        "subHeader": "Physical On-Site Inspection & Computational Infrastructure Audit — DEMO PROFORMA",
        "referenceNo": "DEMO/AICTE/EVC-REP/2026/KA-0423/88",
        "issueDate": "18 October 2026",
        "issuingAuthority": "Expert Visit Committee Panel (Simulated Evaluation Record)",
        "sealText": "SAMPLE / DEMO PROFORMA · Physical Infrastructure Audit Form 4-EVC",
        "pages": [
            {
                "pageNumber": 1,
                "paragraphs": [
                    {
                        "id": "p-evc-p1-1",
                        "text": "1. INSPECTION MANDATE: The Expert Visit Committee conducted physical verification of Northstar Institute of Technology campus, Knowledge Park, Whitefield Extension, Bengaluru on Monday, 18th October 2026 for physical infrastructure verification.",
                        "isDiscrepancy": False,
                    },
                    {
                        "id": "p-evc-p1-2",
                        "text": "2. INFRASTRUCTURE ASSESSMENT: The committee inspected instructional spaces, computing laboratories, digital library servers, barrier-free access elevators, and power backup installations.",
                        "isDiscrepancy": False,
                    },
                ],
            },
            {
                "pageNumber": 2,
                "paragraphs": [
                    {
                        "id": "snip-infra-01",
                        "findingId": "fnd-001b",
                        "text": "3. COMPUTING LABORATORY DISCREPANCY (SYNTHETIC DEMO VALIDATION RULE): In Room CS-302, the self-disclosure declared thirty (30) specialized workstations equipped with high-performance GPUs. Physical on-site serial audit verified only sixteen (16) operational units. Fourteen (14) workstations were neither installed nor present in stores; lab superintendent cited vendor delay without furnishing verified delivery challans. [Rule Grounding: Evaluated under Synthetic Demo Validation Rule for institutional self-declaration reconciliation; AICTE statutory norms under APH 2024–2027 §6.19 and Annexure 4 prescribe departmental lab minimums of 20 PCs, centralized computer centre minimums of 100 PCs, and legal system/application software, rather than specific GPU hardware mandates].",
                        "isDiscrepancy": True,
                        "highlightSeverity": "major",
                        "annotationTitle": "Synthetic Demo Rule: GPU Lab Inventory Discrepancy (14 units unaccounted for)",
                        "fieldKey": "HPC Laboratory Inventory",
                    },
                    {
                        "id": "p-evc-p2-2",
                        "text": "4. INTAKE RECOMMENDATION: In view of the specialized compute shortfall and pending doctoral cadre review, the EVC recommends restricting provisional introductory intake to 30 seats.",
                        "isDiscrepancy": False,
                    },
                ],
            },
        ],
    }

    ev1c_content = {
        "documentId": "ev-001c",
        "headerTitle": "[SAMPLE / DEMO] HIGHER EDUCATION SCRUTINY CELL — STATE AFFILIATION BOARD",
        "subHeader": "Faculty Qualification Dossier & Cadre Scrutiny (B.Tech AI & Data Science) — DEMO PROFORMA",
        "referenceNo": "DEMO/VTU/FAC-QUAL/2026-27/AI-881",
        "issueDate": "12 October 2026",
        "issuingAuthority": "Academic Scrutiny Committee (Simulated Evaluation Record)",
        "sealText": "SAMPLE / DEMO PROFORMA · Technical Education Verification Cell",
        "pages": [
            {
                "pageNumber": 1,
                "paragraphs": [
                    {
                        "id": "p-fac-p1-1",
                        "text": "1. PREAMBLE: The applicant institution, Northstar Institute of Technology, has submitted an application for introductory sanction of intake for 60 seats in B.Tech Artificial Intelligence & Data Science under the Faculty of Engineering & Technology.",
                        "isDiscrepancy": False,
                    },
                    {
                        "id": "p-fac-p1-2",
                        "text": "2. STATUTORY CADRE REQUIREMENT: Under AICTE Approval Process Handbook (APH) 2024–2027 §6.14 and Annexure 5 (specifically Annexure 5.2: Faculty Cadre and Qualifications for Degree Engineering and Technology), for an approved intake of 60 students in Under Graduate Degree Engineering, the prescribed teacher-student ratio is 1:20 with a cadre ratio of Professor : Associate Professor : Assistant Professor = 1 : 2 : 6. Mandatory awarded doctoral degrees (Ph.D.) apply to Professor and Associate Professor posts.",
                        "isDiscrepancy": False,
                    },
                ],
            },
            {
                "pageNumber": 2,
                "paragraphs": [
                    {
                        "id": "p-fac-p2-1",
                        "text": "3. SUBMITTED FACULTY SUMMARY: The institution submitted biodata, identity tokens, and qualification certificates for eight (8) proposed full-time teaching faculty for the introductory academic cycles.",
                        "isDiscrepancy": False,
                    },
                    {
                        "id": "p-fac-p2-2",
                        "text": "4. VERIFICATION OF QUALIFICATIONS: Primary verification against educational repository records was conducted on 12-10-2026.",
                        "isDiscrepancy": False,
                    },
                ],
            },
            {
                "pageNumber": 3,
                "paragraphs": [
                    {
                        "id": "snip-faculty-01",
                        "findingId": "fnd-001a",
                        "text": "5. DOCTORAL QUALIFICATION DISCREPANCY: Scrutiny reveals that among proposed senior cadre posts, only 3 of the designated faculty hold awarded Ph.D. degrees. Dr. P. Sangeetha's thesis titled 'Dynamic Thermal Dissipation in High-Pressure Mechanical Turbines' (awarded 2018) reflects specialization in Mechanical Engineering rather than Computing/Data Sciences. Under AICTE APH 2024–2027 §6.14 and Annexure 5.2, specialized programmes require domain-relevant doctoral qualifications for core Professor and Associate Professor cadre positions.",
                        "isDiscrepancy": True,
                        "highlightSeverity": "critical",
                        "annotationTitle": "Critical Cadre & Ph.D. Norm Shortfall",
                        "fieldKey": "Faculty Doctoral Ratio",
                    },
                    {
                        "id": "p-fac-p3-2",
                        "text": "6. INSTITUTIONAL UNDERTAKING: The Principal has appended an undertaking stating that two Assistant Professors have submitted their Ph.D. theses and await viva-voce examination in December 2026.",
                        "isDiscrepancy": False,
                    },
                    {
                        "id": "p-fac-p3-3",
                        "text": "7. RECOMMENDATION: The Scrutiny Committee places this matter under CONDITIONAL ESCALATION pending submission of domain-specific doctoral award certificates or induction of qualified faculty.",
                        "isDiscrepancy": False,
                    },
                ],
            },
        ],
    }

    ev1d_content = {
        "documentId": "ev-001d",
        "headerTitle": "[SAMPLE / DEMO] CHARTERED ACCOUNTANT STATUTORY AUDIT REPORT",
        "subHeader": "Balance Sheet & Financial Solvency Certification — FY 2025–26",
        "referenceNo": "CA/AUD/2026/KA-8812",
        "issueDate": "13 October 2026",
        "issuingAuthority": "Statutory Auditor Desk (Simulated)",
        "sealText": "INSTITUTE OF CHARTERED ACCOUNTANTS OF INDIA · UDIN VERIFIED",
        "pages": [
            {
                "pageNumber": 1,
                "paragraphs": [
                    {
                        "id": "p-fin-1",
                        "text": "1. CORPUS VERIFICATION: We have audited the accompanying financial statements of Northstar Educational Trust. As of 31 March 2026, the Trust maintains unencumbered fixed deposit corpus of INR 12.80 Crores earmarked for institutional development.",
                        "isDiscrepancy": False,
                    },
                    {
                        "id": "p-fin-2",
                        "text": "2. STATUTORY COMPLIANCE: The institution satisfies the minimum financial viability and capital fund provisions prescribed under AICTE APH Chapter I norms.",
                        "isDiscrepancy": False,
                    },
                ],
            }
        ],
    }

    ev1e_content = {
        "documentId": "ev-001e",
        "headerTitle": "[SAMPLE / DEMO] SUB-REGISTRAR REVENUE TITLE CONVEYANCE DEED",
        "subHeader": "Registered Land Conveyance Deed & Revenue Schedule — DEMO PROFORMA",
        "referenceNo": "BLR/SR/BOOK-I/1998/VOL-412/P-88",
        "issueDate": "12 October 2026",
        "issuingAuthority": "Sub-Registrar Office, Bengaluru East",
        "sealText": "DEPARTMENT OF STAMPS AND REGISTRATION · GOVERNMENT OF KARNATAKA",
        "pages": [
            {
                "pageNumber": 1,
                "paragraphs": [
                    {
                        "id": "snip-legal-01",
                        "findingId": "fnd-001c",
                        "text": "1. TITLE CONVEYANCE & ENTITY NAME: This indenture executed on 14th August 1998 conveys contiguous agricultural land admeasuring 23.0 Acres in Survey Nos. 34/1, 34/2, and 35/B in favor of 'Northstar Technical Institute'. Note: 2026 regulatory application is filed under the modernized nomenclature 'Northstar Institute of Technology'. [Rule Grounding: AICTE APH 2024–2027 §6.17 and Annexure 1 require clear registered marketable title in the name of the applicant entity without ambiguity].",
                        "isDiscrepancy": True,
                        "highlightSeverity": "minor",
                        "annotationTitle": "Entity Title Discrepancy (Northstar Technical Institute vs Northstar Institute of Technology)",
                        "fieldKey": "Entity Name Reconciliation",
                    },
                    {
                        "id": "p-land-2",
                        "text": "2. ENCUMBRANCE STATUS: The property is free from all encumbrances, charges, mortgage liens, or pending revenue litigation as corroborated by Form 15 Nil-Encumbrance Certificate.",
                        "isDiscrepancy": False,
                    },
                ],
            }
        ],
    }

    docs_sub1 = [
        Document(
            id="ev-001a",
            application_id="sub-001",
            original_filename="State Government NOC",
            filename="DEMO_State_Govt_NOC_Karnataka_Northstar.pdf",
            document_type="approval_letter",
            storage_reference="demo/sub-001/ev-001a.pdf",
            mime_type="application/pdf",
            file_size=1840000,
            sha256_hash="5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            issuer_name="Directorate of Technical Education, Bengaluru",
            extracted_text="State Government No Objection Certificate issued by the Directorate of Technical Education.",
            content_json=json.dumps(ev1a_content),
            created_at=_parse_iso("2026-10-12T09:20:00Z"),
        ),
        Document(
            id="ev-001b",
            application_id="sub-001",
            original_filename="Expert Committee Physical Inspection Report",
            filename="DEMO_EVC_Physical_Inspection_Report_Northstar.pdf",
            document_type="inspection_report",
            storage_reference="demo/sub-001/ev-001b.pdf",
            mime_type="application/pdf",
            file_size=4210000,
            sha256_hash="3e7a1b9f2c8d4e5f6a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=2,
            issuer_name="Expert Visit Committee Panel (Simulated Evaluation Record)",
            extracted_text="Official physical inspection report by appointed AICTE Expert Visit Committee.",
            content_json=json.dumps(ev1b_content),
            created_at=_parse_iso("2026-10-18T14:00:00Z"),
        ),
        Document(
            id="ev-001c",
            application_id="sub-001",
            original_filename="Faculty Qualification Dossier & Ph.D. Certificates",
            filename="DEMO_Faculty_Dossier_Northstar_AI_DS.pdf",
            document_type="document",
            storage_reference="demo/sub-001/ev-001c.pdf",
            mime_type="application/pdf",
            file_size=8740200,
            sha256_hash="9f8b4e2d7c1a89f3b5e4d2c1a89f7b6e5d4c3b2a19f8e7d6c5b4a3f2e1d0c9b8",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=3,
            issuer_name="Educational Scrutiny Desk (Simulated)",
            extracted_text="Comprehensive faculty biodata roster and doctoral certificates for proposed AI & DS cadre.",
            content_json=json.dumps(ev1c_content),
            created_at=_parse_iso("2026-10-12T09:25:00Z"),
        ),
        Document(
            id="ev-001d",
            application_id="sub-001",
            original_filename="Audited Financial Statement FY 2025–26",
            filename="DEMO_Audited_Financial_Statement_Northstar.pdf",
            document_type="financial_report",
            storage_reference="demo/sub-001/ev-001d.pdf",
            mime_type="application/pdf",
            file_size=3420000,
            sha256_hash="7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            issuer_name="Statutory Auditor Desk (Simulated)",
            extracted_text="Statutory chartered accountant report on balance sheet and fixed deposits.",
            content_json=json.dumps(ev1d_content),
            created_at=_parse_iso("2026-10-13T10:00:00Z"),
        ),
        Document(
            id="ev-001e",
            application_id="sub-001",
            original_filename="Registered Land Conveyance Deed Extract",
            filename="DEMO_Registered_Land_Conveyance_Deed_Northstar.pdf",
            document_type="document",
            storage_reference="demo/sub-001/ev-001e.pdf",
            mime_type="application/pdf",
            file_size=6150000,
            sha256_hash="b4a8e2f1c9d03e5a7b6c8d1f2a3e4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            issuer_name="Land Title Registry Desk (Simulated)",
            extracted_text="Certified extract of the registered land conveyance deed and revenue schedule.",
            content_json=json.dumps(ev1e_content),
            created_at=_parse_iso("2026-10-12T09:30:00Z"),
        ),
    ]
    db.add_all(docs_sub1)

    # Documents for other applications
    for s_id, _, _, _, _, _, _, _, _, _, _ in submissions_meta[1:]:
        inst_name = institutions_meta[f"inst-{int(s_id[4:]):03d}"][0]
        db.add(
            Document(
                id=f"ev-{s_id}-01",
                application_id=s_id,
                original_filename="AICTE Online Proforma Application",
                filename=f"DEMO_Proforma_Application_{s_id}.pdf",
                document_type="document",
                storage_reference=f"demo/{s_id}/proforma.pdf",
                mime_type="application/pdf",
                file_size=2100000,
                sha256_hash=f"{s_id}8e2f1c9d03e5a7b6c8d1f2a3e4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a"[:64],
                processing_status=DocumentProcessingStatus.COMPLETED,
                page_count=1,
                issuer_name="AICTE Online Portal (Simulated)",
                extracted_text=f"Official submission application proforma for {inst_name}.",
                content_json=None,
                created_at=_parse_iso("2026-10-14T10:00:00Z"),
            )
        )

    # 3. Validation Findings
    findings_data = [
        # Sub-001 (Northstar)
        ValidationFinding(
            id="fnd-001a",
            application_id="sub-001",
            document_id="ev-001c",
            document_name="DEMO_Faculty_Dossier_Northstar_AI_DS.pdf",
            finding_code="Faculty Cadre & Doctoral Ratio",
            severity=FindingSeverity.CRITICAL,
            title="Faculty Cadre & Doctoral Ratio",
            explanation="Cadre imbalance: Proposed department lacks required domain-relevant doctoral qualifications for core cadre posts (Dr. P. Sangeetha Ph.D. is in Mechanical Engineering). Under AICTE APH 2024–2027 §6.14 and Annexure 5.2, Professor and Associate Professor posts strictly require an awarded Ph.D. in the relevant discipline. Dr. Sangeetha's doctorate is in Mechanical Engineering, leaving the proposed AI & DS department deficient in mandated doctoral computing leadership.",
            evidence_reference="DEMO_Faculty_Dossier_Northstar_AI_DS.pdf, Page 3",
            recommended_action="Issue formal clarification query requiring submission of computing doctoral award certificates or consider provisional restriction of intake to 30 seats.",
            review_status=FindingReviewStatus.PENDING,
            highlight_snippet_id="snip-faculty-01",
            page_number=3,
            finding_type="rule_violation",
            status_notice="Awaiting human reviewer decision",
            rule_citation="AICTE Approval Process Handbook (APH) 2024–2027, §6.14 and Annexure 5.2 (UG Engineering & Technology Cadre 1:2:6 & Domain Relevance)",
            created_at=_parse_iso("2026-10-18T11:00:00Z"),
        ),
        ValidationFinding(
            id="fnd-001b",
            application_id="sub-001",
            document_id="ev-001b",
            document_name="DEMO_EVC_Physical_Inspection_Report_Northstar.pdf",
            finding_code="Lab Inventory Reconciliation",
            severity=FindingSeverity.HIGH,
            title="Lab Inventory Reconciliation (Synthetic Demo Rule)",
            explanation="Submitted GPU lab inventory declaration (30 workstations) mismatches physical on-site inspection (16 verified operational; 14 unaccounted for). Physical serial-number audit by Expert Visit Committee in Room CS-302 verified only 16 operational workstation units against proforma declaration of 30 specialized workstations without delivery challans.",
            evidence_reference="DEMO_EVC_Physical_Inspection_Report_Northstar.pdf, Page 2",
            recommended_action="Request OEM purchase orders, delivery challans, and physical asset register for the 14 unaccounted workstations in Room CS-302.",
            review_status=FindingReviewStatus.PENDING,
            highlight_snippet_id="snip-infra-01",
            page_number=2,
            finding_type="inconsistent_information",
            status_notice="Awaiting documentary reconciliation",
            rule_citation="Synthetic demo rule: Institutional Lab Specification & Inventory Reconciliation (Referenced alongside AICTE APH 2024–2027 §6.19 / Annexure 4)",
            created_at=_parse_iso("2026-10-19T09:30:00Z"),
        ),
        ValidationFinding(
            id="fnd-001c",
            application_id="sub-001",
            document_id="ev-001e",
            document_name="DEMO_Registered_Land_Conveyance_Deed_Northstar.pdf",
            finding_code="Entity Legal Identity Reconciliation",
            severity=FindingSeverity.LOW,
            title="Entity Legal Identity Reconciliation",
            explanation="Entity name discrepancy: Land conveyance deed (1998) cites 'Northstar Technical Institute' vs 2026 application 'Northstar Institute of Technology'. The 1998 registered title deed was executed in favor of 'Northstar Technical Institute'. A certified copy of the trust resolution confirming legal transition to 'Northstar Institute of Technology' is required.",
            evidence_reference="DEMO_Registered_Land_Conveyance_Deed_Northstar.pdf, Page 1",
            recommended_action="Verify certified copy of trust resolution confirming entity continuity before final approval issuance.",
            review_status=FindingReviewStatus.PENDING,
            highlight_snippet_id="snip-legal-01",
            page_number=1,
            finding_type="inconsistent_information",
            status_notice="Inconclusive pending trust resolution submission",
            rule_citation="AICTE Approval Process Handbook (APH) 2024–2027, §6.17 and Annexure 1 (Land Requirements, Lawful Title & Encumbrance Status)",
            created_at=_parse_iso("2026-10-21T16:00:00Z"),
        ),
        # Findings for other high-risk cases
        ValidationFinding(
            id="fnd-002a",
            application_id="sub-002",
            finding_code="Tuition Fee Disclosure",
            severity=FindingSeverity.HIGH,
            title="Tuition Fee Disclosure",
            explanation="Tuition fee adjustment not published on public portal 60 days prior as prescribed under mandatory disclosure guidelines.",
            rule_citation="AICTE Mandatory Public Disclosure Norms §3.8",
            finding_type="rule_violation",
            created_at=_parse_iso("2026-10-20T13:00:00Z"),
        ),
        ValidationFinding(
            id="fnd-005a",
            application_id="sub-005",
            finding_code="Affiliation Validity",
            severity=FindingSeverity.CRITICAL,
            title="Affiliation Validity",
            explanation="State university affiliation renewal certificate not uploaded for current academic calendar.",
            rule_citation="AICTE APH 2024–2027 Chapter I (Affiliation Prerequisites)",
            finding_type="missing_information",
            created_at=_parse_iso("2026-10-16T10:00:00Z"),
        ),
        ValidationFinding(
            id="fnd-007a",
            application_id="sub-007",
            finding_code="Statutory Financial Audit",
            severity=FindingSeverity.CRITICAL,
            title="Statutory Financial Audit",
            explanation="Statutory audit report for prior financial year not submitted; persistent reporting non-compliance.",
            rule_citation="AICTE APH 2024–2027 Chapter II (Financial Viability & Annual Returns)",
            finding_type="rule_violation",
            created_at=_parse_iso("2026-10-15T10:00:00Z"),
        ),
        ValidationFinding(
            id="fnd-008a",
            application_id="sub-008",
            finding_code="Land Title & Encumbrance Status",
            severity=FindingSeverity.CRITICAL,
            title="Land Title & Encumbrance Status",
            explanation="Encumbrance Certificate reveals unrecorded commercial bank mortgage lien on campus parcel Survey No. 48/2.",
            rule_citation="AICTE APH 2024–2027 §6.17 & Annexure 1 (Lawful Freehold Land Possession)",
            finding_type="inconsistent_information",
            created_at=_parse_iso("2026-10-17T11:30:00Z"),
        ),
        ValidationFinding(
            id="fnd-009a",
            application_id="sub-009",
            finding_code="Faculty Student Ratio",
            severity=FindingSeverity.HIGH,
            title="Faculty Student Ratio",
            explanation="Teacher Student Ratio computes to 1:24 vs mandated 1:20 under proposed 120-seat expansion.",
            rule_citation="AICTE APH 2024–2027 §6.14 and Annexure 5.2",
            finding_type="rule_violation",
            created_at=_parse_iso("2026-10-21T09:45:00Z"),
        ),
        ValidationFinding(
            id="fnd-015a",
            application_id="sub-015",
            finding_code="Director Statutory Qualification",
            severity=FindingSeverity.CRITICAL,
            title="Director Statutory Qualification",
            explanation="Director doctoral qualification issued by unaccredited foreign institution without AIU equivalence certificate.",
            rule_citation="AICTE APH 2024–2027 §6.14 & AIU Equivalence Requirements",
            finding_type="rule_violation",
            created_at=_parse_iso("2026-10-18T15:20:00Z"),
        ),
        ValidationFinding(
            id="fnd-018a",
            application_id="sub-018",
            finding_code="Fire Safety NOC Clearance",
            severity=FindingSeverity.CRITICAL,
            title="Fire Safety NOC Clearance",
            explanation="Municipal Chief Fire Officer revoked provisional fire NOC due to lack of secondary emergency exits.",
            rule_citation="National Building Code NBC 2016 Part 4 & AICTE §6.17",
            finding_type="rule_violation",
            created_at=_parse_iso("2026-10-12T09:00:00Z"),
        ),
        ValidationFinding(
            id="fnd-025a",
            application_id="sub-025",
            finding_code="Municipal Occupancy Certificate Authenticity",
            severity=FindingSeverity.CRITICAL,
            title="Municipal Occupancy Certificate Authenticity",
            explanation="Municipal occupancy certificate number (MCO-2024-8819) does not exist in Indore Municipal Corporation registered ledger.",
            rule_citation="AICTE APH 2024–2027 §6.17",
            finding_type="potential_anomaly",
            created_at=_parse_iso("2026-10-15T12:00:00Z"),
        ),
    ]
    db.add_all(findings_data)

    # 4. Cross-Document Comparisons
    cross_docs = [
        CrossDocComparison(
            id="cdc-001",
            submission_id="sub-001",
            field_name="Specialized Computing Hardware Count",
            description="Self-declared high-performance GPU workstations vs on-site physical count",
            has_discrepancy=True,
            status_text="Discrepancy (14 Units Unaccounted)",
            entries_json=json.dumps([
                {"documentName": "Institutional Proforma Part B", "documentType": "Self-Declaration", "extractedValue": "30 Units (NVIDIA RTX A6000)", "sourcePage": 14, "isMismatched": True, "confidenceScore": 0.98},
                {"documentName": "EVC Physical Inspection Report", "documentType": "Expert Visit Audit", "extractedValue": "16 Operational Units (Room CS-302)", "sourcePage": 2, "isMismatched": True, "confidenceScore": 0.96},
            ]),
            human_review_recommendation="Seek purchase invoices and delivery challans for the 14 unverified workstations before granting program approval.",
        ),
        CrossDocComparison(
            id="cdc-002",
            submission_id="sub-001",
            field_name="Institution Legal Entity Name",
            description="Entity legal title comparison across submitted statutory deeds, state approvals, and regulatory filing.",
            has_discrepancy=True,
            status_text="Discrepancy Flagged for Human Review",
            entries_json=json.dumps([
                {"documentName": "AICTE Online Application Form (2026–27 Demo)", "documentType": "Regulatory Application", "extractedValue": "Northstar Institute of Technology", "sourcePage": 1, "isMismatched": False, "confidenceScore": 0.99},
                {"documentName": "State Government NOC", "documentType": "State Government NOC", "extractedValue": "Northstar Institute of Technology, Knowledge Park, Whitefield Extension", "sourcePage": 1, "isMismatched": False, "confidenceScore": 0.98},
                {"documentName": "Registered Land Conveyance Deed Extract", "documentType": "Land Revenue Title", "extractedValue": "Northstar Technical Institute", "sourcePage": 1, "isMismatched": True, "confidenceScore": 0.94},
            ]),
            human_review_recommendation="Reconcile entity title between 1998 Land Deed ('Northstar Technical Institute') and 2026 AICTE Application ('Northstar Institute of Technology'). Verify that a formal Government gazette renaming order or trust deed amendment is on record.",
        ),
        CrossDocComparison(
            id="cdc-003",
            submission_id="sub-001",
            field_name="Campus Land Area & Survey Coordinates",
            description="Physical campus land extent and survey numbers across revenue deed, municipal NOC, and application.",
            has_discrepancy=False,
            status_text="Concordant Across 3 Documents",
            entries_json=json.dumps([
                {"documentName": "AICTE Online Application Form (2026–27 Demo)", "documentType": "Regulatory Application", "extractedValue": "23.0 Acres (Survey Nos. 34/1, 34/2, 35/B)", "sourcePage": 4, "isMismatched": False, "confidenceScore": 0.99},
                {"documentName": "Registered Land Conveyance Deed Extract", "documentType": "Land Revenue Title", "extractedValue": "23.0 Acres (Survey Nos. 34/1, 34/2, 35/B, Bengaluru East)", "sourcePage": 1, "isMismatched": False, "confidenceScore": 0.98},
                {"documentName": "State Government NOC", "documentType": "State Government NOC", "extractedValue": "23.0 Acres Educational Complex, Knowledge Park", "sourcePage": 1, "isMismatched": False, "confidenceScore": 0.98},
            ]),
            human_review_recommendation="All 3 statutory instruments corroborate contiguous 23.0 Acres in Survey Nos. 34/1, 34/2, and 35/B.",
        ),
        CrossDocComparison(
            id="cdc-004",
            submission_id="sub-001",
            field_name="Proposed AI & DS Student Intake",
            description="Sanctioned student intake declared by applicant versus expert inspection recommendation.",
            has_discrepancy=True,
            status_text="Intake Divergence Flagged",
            entries_json=json.dumps([
                {"documentName": "AICTE Online Application Form (2026–27 Demo)", "documentType": "Regulatory Application", "extractedValue": "60 Seats (Single Division / Shift 1)", "sourcePage": 2, "isMismatched": False, "confidenceScore": 1.0},
                {"documentName": "State Government NOC", "documentType": "State Government NOC", "extractedValue": "No Objection for 60 Seats (Subject to AICTE)", "sourcePage": 1, "isMismatched": False, "confidenceScore": 0.99},
                {"documentName": "Expert Committee Physical Inspection Report", "documentType": "Inspection Report", "extractedValue": "Recommended: Provisional 30 Seats (Subject to Faculty Rectification)", "sourcePage": 2, "isMismatched": True, "confidenceScore": 0.97},
            ]),
            human_review_recommendation="Applicant applied for 60 seats; EVC inspection committee recommends restricting provisional sanction to 30 seats until faculty doctoral cadre deficiency is resolved under APH 2024–2027 §6.14 and Annexure 5.2.",
        ),
        CrossDocComparison(
            id="cdc-008",
            submission_id="sub-008",
            field_name="Land Encumbrance & Mortgage Status",
            description="Institutional land ownership vs commercial bank encumbrance search",
            has_discrepancy=True,
            status_text="Bank Mortgage Lien Flagged",
            entries_json=json.dumps([
                {"documentName": "Applicant Land Self-Declaration", "documentType": "Affidavit", "extractedValue": "Unencumbered, Free from All Charges", "sourcePage": 1, "isMismatched": True, "confidenceScore": 0.99},
                {"documentName": "Sub-Registrar Encumbrance Certificate", "documentType": "Revenue Extract", "extractedValue": "Registered Mortgage Charge in favor of Canara Bank (INR 4.5 Cr)", "sourcePage": 3, "isMismatched": True, "confidenceScore": 0.96},
            ]),
            human_review_recommendation="Under AICTE APH §6.17, institutional land must have clear, marketable title without unrecorded liabilities. Require NOC / No Dues Certificate from the lending bank.",
        ),
    ]
    db.add_all(cross_docs)

    # 5. Reviewer Notes
    notes_list = [
        ReviewerNote(
            id="note-001",
            application_id="sub-001",
            author="Priya Venkataraman",
            role="Senior Compliance Reviewer",
            text="Escalated to Senior Hearing Committee. The doctoral domain gap in AI/DS cadre requires official committee decision per APH §6.14.",
            category="faculty",
            created_at=_parse_iso("2026-10-24T10:15:00Z"),
        ),
        ReviewerNote(
            id="note-002",
            application_id="sub-001",
            author="Dr. Anand Joshi",
            role="Regional Scrutiny Officer",
            text="On-site EVC noted missing 14 workstations in CS-302. Institution principal stated OEM delivery was delayed. Requested purchase orders and delivery challans.",
            category="infrastructure",
            created_at=_parse_iso("2026-10-25T11:45:00Z"),
        ),
    ]
    db.add_all(notes_list)

    # 6. Baseline Audit Events
    audit_events = [
        AuditEvent(
            id="aud-001",
            application_id="sub-001",
            event_type="escalated",
            actor="Priya Venkataraman (Senior Compliance Reviewer)",
            details="Escalated to Hearing Committee due to unresolved faculty cadre doctoral deficiency and disputed GPU hardware declaration.",
            created_at=_parse_iso("2026-10-26T18:30:00Z"),
        ),
        AuditEvent(
            id="aud-002",
            application_id="sub-008",
            event_type="escalated",
            actor="Priya Venkataraman (Senior Compliance Reviewer)",
            details="Escalated for senior legal review: Bank mortgage lien detected on campus parcel Survey No. 48/2.",
            created_at=_parse_iso("2026-10-26T15:00:00Z"),
        ),
        AuditEvent(
            id="aud-003",
            application_id="sub-003",
            event_type="decision_approved",
            actor="Ramesh Iyer (Reviewer)",
            details="Simulated decision: MBA intake extension approved — all statutory proformas and faculty rosters cleared.",
            created_at=_parse_iso("2026-10-25T16:00:00Z"),
        ),
        AuditEvent(
            id="aud-004",
            application_id="sub-025",
            event_type="decision_rejected",
            actor="Ramesh Iyer (Reviewer)",
            details="Simulated decision: Application rejected — inauthentic municipal occupancy certificate detected.",
            created_at=_parse_iso("2026-10-24T11:00:00Z"),
        ),
        AuditEvent(
            id="aud-005",
            application_id="sub-001",
            event_type="finding_flagged",
            actor="VerifyAI Automated Heuristic Engine",
            details="Flagged APH §6.14 doctoral cadre mismatch: Proposed Associate Professor doctorate is in Mechanical Engineering.",
            created_at=_parse_iso("2026-10-18T11:00:00Z"),
        ),
        AuditEvent(
            id="aud-006",
            application_id="sub-005",
            event_type="evidence_requested",
            actor="Sunita Sharma (Reviewer)",
            details="Clarification requested: State university affiliation renewal order and reconstituted Anti-Ragging committee roster.",
            created_at=_parse_iso("2026-10-24T16:00:00Z"),
        ),
        AuditEvent(
            id="aud-007",
            application_id="sub-007",
            event_type="decision_rejected",
            actor="Ramesh Iyer (Reviewer)",
            details="Simulated decision: Rejected — Persistent statutory financial audit non-compliance after three notice cycles.",
            created_at=_parse_iso("2026-10-24T13:00:00Z"),
        ),
        AuditEvent(
            id="aud-008",
            application_id="sub-002",
            event_type="review_started",
            actor="Priya Venkataraman (Senior Compliance Reviewer)",
            details="Dossier scrutiny initiated for annual fee disclosure and enrollment figures.",
            created_at=_parse_iso("2026-10-25T10:00:00Z"),
        ),
        AuditEvent(
            id="aud-009",
            application_id="sub-018",
            event_type="decision_rejected",
            actor="Ramesh Iyer (Reviewer)",
            details="Simulated decision: Rejected — Revoked municipal fire safety NOC and non-contiguous campus land parcels.",
            created_at=_parse_iso("2026-10-24T12:00:00Z"),
        ),
        AuditEvent(
            id="aud-010",
            application_id="sub-010",
            event_type="decision_approved",
            actor="Ramesh Iyer (Reviewer)",
            details="Simulated decision: Annual Extension of Approval approved — NBA Tier-1 accreditation confirmed.",
            created_at=_parse_iso("2026-10-24T18:00:00Z"),
        ),
        AuditEvent(
            id="aud-011",
            application_id="sub-015",
            event_type="finding_flagged",
            actor="VerifyAI Automated Heuristic Engine",
            details="Flagged APH §6.14: Director doctoral degree from foreign institution lacks AIU equivalence certification.",
            created_at=_parse_iso("2026-10-18T15:20:00Z"),
        ),
        AuditEvent(
            id="aud-012",
            application_id="sub-027",
            event_type="evidence_requested",
            actor="Sunita Sharma (Reviewer)",
            details="Bank ECS salary disbursement statements requested for Q1 and Q2 per 7th CPC guidelines.",
            created_at=_parse_iso("2026-10-25T15:00:00Z"),
        ),
    ]
    db.add_all(audit_events)

    db.commit()
    print("[VerifyAI Seeder] Successfully seeded 30 synthetic applications and audit trail into active database.")
    return 30

