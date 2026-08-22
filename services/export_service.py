"""
AttendAI - Multi-Format Export Service
Generates official attendance documents in PDF (via PDF.co Cloud API + local ReportLab engine),
XML, JSON, CSV, and Plain Text formats.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.dom import minidom

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from api.attendance_api import (
    get_all_subjects as repo_get_all_subjects,
    get_raw_attendance_summary as repo_get_raw_summary,
    get_student as repo_get_student,
)

# User's PDF.co Cloud API Key
PDFCO_API_KEY = os.getenv(
    "PDFCO_API_KEY",
    "sank7687s@gmail.com_OBiYPcUlfyFlpuFZ2G68Th1LfdZDIOsGtw2YqvJUkjgXvDm6jcGqYMvTocsueUVH"
)

# Contact registry for students
STUDENT_CONTACTS: Dict[str, Dict[str, str]] = {
    "S001": {"phone": "9042778493", "email": "wellz.bot@gmail.com"},
    "S002": {"phone": "9876543210", "email": "priya.patel@student.college.edu"},
    "S003": {"phone": "9876543211", "email": "rohan.iyer@student.college.edu"},
    "S004": {"phone": "9876543212", "email": "ananya.gupta@student.college.edu"},
    "S005": {"phone": "9876543213", "email": "vikram.malhotra@student.college.edu"},
    "S006": {"phone": "9876543214", "email": "sneha.reddy@student.college.edu"},
    "S007": {"phone": "9876543215", "email": "rahul.verma@student.college.edu"},
    "S008": {"phone": "9876543216", "email": "neha.nair@student.college.edu"},
    "S009": {"phone": "9876543217", "email": "siddharth.rao@student.college.edu"},
    "S010": {"phone": "9876543218", "email": "pooja.joshi@student.college.edu"},
    "S011": {"phone": "9876543219", "email": "karan.mehta@student.college.edu"},
    "S012": {"phone": "9876543220", "email": "divya.deshmukh@student.college.edu"},
    "S013": {"phone": "9876543221", "email": "aditya.kulkarni@student.college.edu"},
    "S014": {"phone": "9876543222", "email": "ritu.choudhury@student.college.edu"},
    "S015": {"phone": "9876543223", "email": "varun.kapoor@student.college.edu"},
    "S016": {"phone": "9876543224", "email": "ishita.sen@student.college.edu"},
    "S017": {"phone": "9876543225", "email": "manish.pandey@student.college.edu"},
    "S018": {"phone": "9876543226", "email": "tanvi.bhat@student.college.edu"},
    "S019": {"phone": "9876543227", "email": "nikhil.saxena@student.college.edu"},
    "S020": {"phone": "9876543228", "email": "meera.pillai@student.college.edu"},
}


def get_student_contact(student_id: str) -> Dict[str, str]:
    return STUDENT_CONTACTS.get(
        student_id,
        {"phone": "9042778493", "email": "wellz.bot@gmail.com"}
    )


class ExportService:
    """
    Service to generate structured attendance reports in PDF, XML, JSON, CSV, and Text.
    Supports PDF.co cloud rendering with ReportLab fallback.
    """

    @classmethod
    def get_full_student_report_data(cls, student_id: str) -> Dict[str, Any]:
        student = repo_get_student(student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found")

        summary = repo_get_raw_summary(student_id)
        contact = get_student_contact(student_id)

        conducted = summary["total_conducted"]
        attended = summary["total_attended"]
        absent = summary["total_absent"]
        overall_rate = round((attended / conducted * 100.0), 2) if conducted > 0 else 0.0

        needed_for_80 = 0
        if overall_rate < 80.0 and conducted > 0:
            needed_for_80 = max(0, math.ceil(round((0.80 * conducted - attended) / 0.20, 9)))

        status = "SAFE (DISTINCTION)" if overall_rate >= 80.0 else ("BORDERLINE (CONDONATION REQUIRED)" if overall_rate >= 75.0 else "CRITICAL SHORTAGE (DEBARMENT RISK)")

        subject_list = []
        for s_id, s_stats in summary["subjects"].items():
            s_cond = s_stats["conducted"]
            s_att = s_stats["attended"]
            s_abs = s_stats["absent"]
            s_rate = round((s_att / s_cond * 100.0), 2) if s_cond > 0 else 0.0

            sub_needed = 0
            if s_rate < 80.0 and s_cond > 0:
                sub_needed = max(0, math.ceil(round((0.80 * s_cond - s_att) / 0.20, 9)))

            sub_status = "SAFE" if s_rate >= 80.0 else ("BORDERLINE" if s_rate >= 75.0 else "SHORTAGE")

            subject_list.append({
                "subject_id": s_id,
                "subject_code": s_stats["subject_code"],
                "subject_name": s_stats["subject_name"],
                "conducted": s_cond,
                "attended": s_att,
                "absent": s_abs,
                "percentage": s_rate,
                "needed_for_80": sub_needed,
                "status": sub_status
            })

        return {
            "student_id": student["student_id"],
            "student_name": student["name"],
            "department": student["department"],
            "year": student["year"],
            "semester": student["semester"],
            "contact": contact,
            "overall_conducted": conducted,
            "overall_attended": attended,
            "overall_absent": absent,
            "overall_percentage": overall_rate,
            "needed_for_80": needed_for_80,
            "status": status,
            "subjects": subject_list,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # 1. Generate HTML Transcript (for PDF.co and Web Preview)
    # =========================================================================
    @classmethod
    def generate_html_transcript(cls, student_id: str) -> str:
        data = cls.get_full_student_report_data(student_id)
        is_safe = data["overall_percentage"] >= 80.0
        is_borderline = 75.0 <= data["overall_percentage"] < 80.0
        badge_color = "#059669" if is_safe else ("#d97706" if is_borderline else "#e11d48")
        bg_color = "#ecfdf5" if is_safe else ("#fffbeb" if is_borderline else "#fff1f2")

        rows_html = ""
        for s in data["subjects"]:
            rate_c = "#059669" if s["percentage"] >= 80.0 else ("#d97706" if s["percentage"] >= 75.0 else "#e11d48")
            rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
              <td style="padding: 8px 12px; font-weight: bold; color: #334155;">{s['subject_code']}</td>
              <td style="padding: 8px 12px; color: #0f172a;">{s['subject_name']}</td>
              <td style="padding: 8px 12px; text-align: center;">{s['conducted']}</td>
              <td style="padding: 8px 12px; text-align: center;">{s['attended']}</td>
              <td style="padding: 8px 12px; text-align: center;">{s['absent']}</td>
              <td style="padding: 8px 12px; text-align: center; font-weight: bold; color: {rate_c};">{s['percentage']:.2f}%</td>
              <td style="padding: 8px 12px; text-align: center;">{s['status']}</td>
              <td style="padding: 8px 12px; text-align: center; font-weight: bold; color: #2563eb;">+{s['needed_for_80'] if s['needed_for_80'] > 0 else 0}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Attendance Transcript - {data['student_name']}</title>
          <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 30px; color: #0f172a; font-size: 13px; }}
            .header {{ text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; font-size: 20px; color: #0f172a; }}
            .header p {{ margin: 4px 0 0; font-size: 12px; color: #64748b; }}
            .info-box {{ display: flex; justify-content: space-between; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-bottom: 16px; font-size: 12px; }}
            .metric-card {{ background: {bg_color}; border: 1px solid {badge_color}; border-radius: 8px; padding: 14px; text-align: center; margin-bottom: 20px; }}
            .metric-card .pct {{ font-size: 28px; font-weight: 800; color: {badge_color}; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }}
            th {{ background: #f1f5f9; padding: 10px 12px; text-align: left; border-bottom: 2px solid #cbd5e1; color: #334155; }}
            .policy-box {{ background: #f8fafc; border-left: 4px solid #2563eb; padding: 12px; font-size: 11px; line-height: 1.5; color: #334155; margin-bottom: 25px; }}
            .signatures {{ display: flex; justify-content: space-between; margin-top: 40px; text-align: center; font-size: 12px; }}
            .sig-line {{ border-top: 1px solid #94a3b8; width: 160px; padding-top: 6px; }}
          </style>
        </head>
        <body>
          <div class="header">
            <h1>DEMO COLLEGE OF ENGINEERING & TECHNOLOGY</h1>
            <p>Official Attendance Transcript & Exam Clearance Clearance Report</p>
          </div>

          <div class="info-box">
            <div>
              <div><strong>Student Name:</strong> {data['student_name']}</div>
              <div><strong>Student ID:</strong> {data['student_id']}</div>
              <div><strong>Department:</strong> {data['department']} (Year {data['year']}, Sem {data['semester']})</div>
            </div>
            <div style="text-align: right;">
              <div><strong>Registered Phone:</strong> {data['contact']['phone']}</div>
              <div><strong>Registered Email:</strong> {data['contact']['email']}</div>
              <div><strong>Generated Date:</strong> {data['generated_at'][:10]}</div>
            </div>
          </div>

          <div class="metric-card">
            <div>AGGREGATE ATTENDANCE STANDING</div>
            <div class="pct">{data['overall_percentage']:.2f}%</div>
            <div style="margin-top: 4px; font-weight: bold; color: {badge_color};">{data['status']}</div>
            <div style="font-size: 12px; margin-top: 4px; color: #475569;">
              Attended {data['overall_attended']} of {data['overall_conducted']} conducted lectures | Deficit to 80%: <strong>+{data['needed_for_80']} consecutive lectures</strong>
            </div>
          </div>

          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Subject Name</th>
                <th style="text-align: center;">Conducted</th>
                <th style="text-align: center;">Attended</th>
                <th style="text-align: center;">Absent</th>
                <th style="text-align: center;">Percentage</th>
                <th style="text-align: center;">Status</th>
                <th style="text-align: center;">Need for 80%</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>

          <div class="policy-box">
            <strong>College Academic Regulations:</strong><br/>
            1. Minimum 80.0% aggregate attendance is mandatory for regular End-Semester Examination Hall Ticket clearance.<br/>
            2. Attendance between 75.0% and 79.9% requires formal Dean & HOD Condonation Approval with an active recovery plan.<br/>
            3. Attendance below 75.0% results in direct course debarment unless compensated through remedial sessions.
          </div>

          <div class="signatures">
            <div class="sig-line">Student Signature</div>
            <div class="sig-line">Academic Counselor</div>
            <div class="sig-line">Head of Department</div>
          </div>
        </body>
        </html>
        """

    # =========================================================================
    # 2. Generate PDF (PDF.co Cloud API with Local Fallback)
    # =========================================================================
    @classmethod
    def generate_pdf_cloud(cls, student_id: str) -> Dict[str, Any]:
        """
        Uses user's PDF.co API Key to render cloud PDF with direct S3 link.
        """
        data = cls.get_full_student_report_data(student_id)
        html_content = cls.generate_html_transcript(student_id)

        try:
            headers = {
                "x-api-key": PDFCO_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "html": html_content,
                "name": f"Attendance_Report_{student_id}.pdf",
                "margins": "10mm 10mm 10mm 10mm",
                "paperSize": "Letter",
                "orientation": "Portrait",
                "async": False
            }

            res = requests.post(
                "https://api.pdf.co/v1/pdf/convert/from/html",
                headers=headers,
                json=payload,
                timeout=15
            )

            if res.status_code == 200:
                res_data = res.json()
                if not res_data.get("error"):
                    return {
                        "success": True,
                        "engine": "PDF.co Cloud API",
                        "cloud_pdf_url": res_data.get("url"),
                        "remaining_credits": res_data.get("remainingCredits"),
                        "student_id": student_id,
                        "file_name": f"Attendance_Report_{student_id}.pdf"
                    }
        except Exception as e:
            print(f"PDF.co API warning: {e}, falling back to local ReportLab.")

        # Fallback to local ReportLab
        return {
            "success": True,
            "engine": "ReportLab Native Engine",
            "cloud_pdf_url": f"/api/export/{student_id}/pdf",
            "student_id": student_id,
            "file_name": f"Attendance_Report_{student_id}.pdf"
        }

    @classmethod
    def generate_pdf(cls, student_id: str) -> bytes:
        """
        Generates binary PDF stream via ReportLab.
        """
        data = cls.get_full_student_report_data(student_id)
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            alignment=1,
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=12
        )

        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6
        )

        normal_style = ParagraphStyle(
            "NormalText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155")
        )

        bold_style = ParagraphStyle(
            "BoldText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a")
        )

        story = []

        # Title and Header
        story.append(Paragraph("DEMO COLLEGE OF ENGINEERING & TECHNOLOGY", title_style))
        story.append(Paragraph("OFFICIAL ATTENDANCE TRANSCRIPT & RECOVERY CLEARANCE REPORT", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

        # Student Details & Metadata Box
        student_info_table_data = [
            [
                Paragraph(f"<b>Student Name:</b> {data['student_name']}", normal_style),
                Paragraph(f"<b>Student ID:</b> {data['student_id']}", normal_style),
            ],
            [
                Paragraph(f"<b>Department:</b> {data['department']}", normal_style),
                Paragraph(f"<b>Year / Semester:</b> Year {data['year']}, Sem {data['semester']}", normal_style),
            ],
            [
                Paragraph(f"<b>Phone:</b> {data['contact']['phone']}", normal_style),
                Paragraph(f"<b>Email:</b> {data['contact']['email']}", normal_style),
            ],
            [
                Paragraph(f"<b>Generated At:</b> {data['generated_at'][:19].replace('T', ' ')} UTC", normal_style),
                Paragraph(f"<b>Engine:</b> PDF.co & AttendAI Multi-Agent", normal_style),
            ],
        ]

        info_table = Table(student_info_table_data, colWidths=[270, 270])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10))

        # Overall Attendance Summary Card
        is_safe = data["overall_percentage"] >= 80.0
        is_borderline = 75.0 <= data["overall_percentage"] < 80.0
        status_bg = colors.HexColor("#ecfdf5") if is_safe else (colors.HexColor("#fffbeb") if is_borderline else colors.HexColor("#fff1f2"))
        status_border = colors.HexColor("#10b981") if is_safe else (colors.HexColor("#f59e0b") if is_borderline else colors.HexColor("#f43f5e"))

        summary_table_data = [
            [
                Paragraph("<b>Total Conducted</b>", normal_style),
                Paragraph("<b>Total Attended</b>", normal_style),
                Paragraph("<b>Overall %</b>", normal_style),
                Paragraph("<b>Classes Needed for 80%</b>", normal_style),
                Paragraph("<b>Eligibility Status</b>", normal_style),
            ],
            [
                Paragraph(f"{data['overall_conducted']}", bold_style),
                Paragraph(f"{data['overall_attended']}", bold_style),
                Paragraph(f"<b>{data['overall_percentage']:.2f}%</b>", ParagraphStyle("Pct", parent=bold_style, fontSize=11, textColor=colors.HexColor("#1e40af"))),
                Paragraph(f"<b>+{data['needed_for_80']} classes</b>" if data['needed_for_80'] > 0 else "<b>0 (Met)</b>", bold_style),
                Paragraph(f"<b>{data['status']}</b>", normal_style),
            ]
        ]

        summary_table = Table(summary_table_data, colWidths=[80, 80, 80, 130, 170])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("BOX", (0, 0), (-1, -1), 1, status_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))

        # Subject-Wise Breakdown Table
        story.append(Paragraph("Subject-Wise Attendance Breakdown (8 Curriculum Subjects)", section_style))

        subject_table_data = [
            [
                Paragraph("<b>Code</b>", bold_style),
                Paragraph("<b>Subject Name</b>", bold_style),
                Paragraph("<b>Conducted</b>", bold_style),
                Paragraph("<b>Attended</b>", bold_style),
                Paragraph("<b>Absent</b>", bold_style),
                Paragraph("<b>Rate (%)</b>", bold_style),
                Paragraph("<b>Status</b>", bold_style),
                Paragraph("<b>For 80%</b>", bold_style),
            ]
        ]

        for s in data["subjects"]:
            s_rate = s["percentage"]
            rate_color = "#10b981" if s_rate >= 80.0 else ("#d97706" if s_rate >= 75.0 else "#e11d48")
            rate_p = Paragraph(f"<font color='{rate_color}'><b>{s_rate:.2f}%</b></font>", bold_style)
            needed_p = Paragraph(f"+{s['needed_for_80']}" if s['needed_for_80'] > 0 else "-", normal_style)

            subject_table_data.append([
                Paragraph(s["subject_code"], normal_style),
                Paragraph(s["subject_name"], bold_style),
                Paragraph(str(s["conducted"]), normal_style),
                Paragraph(str(s["attended"]), normal_style),
                Paragraph(str(s["absent"]), normal_style),
                rate_p,
                Paragraph(s["status"], normal_style),
                needed_p,
            ])

        sub_table = Table(subject_table_data, colWidths=[55, 170, 50, 50, 45, 55, 65, 50])
        sub_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(sub_table)
        story.append(Spacer(1, 12))

        # College Policy & Regulatory Certification
        policy_text = (
            "<b>Official Examination Policy Certification:</b><br/>"
            "1. <b>Mandatory Minimum:</b> A minimum of 80.0% overall attendance is required for regular End-Semester Examination eligibility.<br/>"
            "2. <b>Condonation Zone (75.0% – 79.9%):</b> Allowed only upon submission of an approved recovery schedule signed by the Academic Counselor and HOD.<br/>"
            "3. <b>Critical Shortage (< 75.0%):</b> Direct debarment risk. Immediate remedial class attendance is mandatory."
        )
        story.append(Paragraph(policy_text, normal_style))
        story.append(Spacer(1, 25))

        # Signatures
        sig_data = [
            [
                Paragraph("__________________________<br/><b>Student Signature</b>", normal_style),
                Paragraph("__________________________<br/><b>Academic Counselor</b>", normal_style),
                Paragraph("__________________________<br/><b>Head of Department</b>", normal_style),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[180, 180, 180])
        sig_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(sig_table)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    # =========================================================================
    # 3. Generate XML
    # =========================================================================
    @classmethod
    def generate_xml(cls, student_id: str) -> str:
        data = cls.get_full_student_report_data(student_id)

        root = ET.Element("AttendanceReport", {
            "system": "AttendAI Agentic Recovery Platform",
            "version": "2.0",
            "generatedAt": data["generated_at"],
            "academicYear": "2025-2026",
            "semester": str(data["semester"])
        })

        student_el = ET.SubElement(root, "Student", {
            "id": data["student_id"],
            "name": data["student_name"],
            "department": data["department"],
            "year": str(data["year"]),
            "semester": str(data["semester"])
        })

        ET.SubElement(student_el, "Contact", {
            "phone": data["contact"]["phone"],
            "email": data["contact"]["email"]
        })

        ET.SubElement(student_el, "OverallSummary", {
            "totalConducted": str(data["overall_conducted"]),
            "totalAttended": str(data["overall_attended"]),
            "totalAbsent": str(data["overall_absent"]),
            "percentage": f"{data['overall_percentage']:.2f}",
            "status": data["status"],
            "classesNeededFor80": str(data["needed_for_80"])
        })

        subjects_el = ET.SubElement(student_el, "Subjects")
        for sub in data["subjects"]:
            ET.SubElement(subjects_el, "Subject", {
                "id": sub["subject_id"],
                "code": sub["subject_code"],
                "name": sub["subject_name"],
                "conducted": str(sub["conducted"]),
                "attended": str(sub["attended"]),
                "absent": str(sub["absent"]),
                "percentage": f"{sub['percentage']:.2f}",
                "neededFor80": str(sub["needed_for_80"]),
                "status": sub["status"]
            })

        ET.SubElement(root, "PolicyGuidelines", {
            "minimumRequirement": "80.0%",
            "condonationBracket": "75.0% - 79.9%",
            "debarmentThreshold": "< 75.0%",
            "maxWeeklyRecoveryClasses": "3 per subject"
        })

        xml_bytes = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_bytes)
        return parsed.toprettyxml(indent="  ")

    # =========================================================================
    # 4. Generate JSON
    # =========================================================================
    @classmethod
    def generate_json(cls, student_id: str) -> str:
        data = cls.get_full_student_report_data(student_id)
        return json.dumps(data, indent=2)

    # =========================================================================
    # 5. Generate CSV
    # =========================================================================
    @classmethod
    def generate_csv(cls, student_id: str) -> str:
        data = cls.get_full_student_report_data(student_id)
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["ATTENDAI - OFFICIAL ATTENDANCE TRANSCRIPT"])
        writer.writerow(["Student ID", data["student_id"]])
        writer.writerow(["Student Name", data["student_name"]])
        writer.writerow(["Department", data["department"]])
        writer.writerow(["Year / Semester", f"Year {data['year']}, Semester {data['semester']}"])
        writer.writerow(["Phone", data["contact"]["phone"]])
        writer.writerow(["Email", data["contact"]["email"]])
        writer.writerow(["Generated At", data["generated_at"]])
        writer.writerow([])
        writer.writerow(["OVERALL SUMMARY"])
        writer.writerow(["Conducted", "Attended", "Absent", "Percentage (%)", "Status", "Classes Needed for 80%"])
        writer.writerow([
            data["overall_conducted"],
            data["overall_attended"],
            data["overall_absent"],
            data["overall_percentage"],
            data["status"],
            data["needed_for_80"]
        ])
        writer.writerow([])
        writer.writerow(["SUBJECT-WISE ATTENDANCE BREAKDOWN"])
        writer.writerow(["Subject Code", "Subject Name", "Conducted", "Attended", "Absent", "Percentage (%)", "Status", "Needed for 80%"])
        for sub in data["subjects"]:
            writer.writerow([
                sub["subject_code"],
                sub["subject_name"],
                sub["conducted"],
                sub["attended"],
                sub["absent"],
                sub["percentage"],
                sub["status"],
                sub["needed_for_80"]
            ])

        return output.getvalue()

    # =========================================================================
    # 6. Generate Text Dossier
    # =========================================================================
    @classmethod
    def generate_text_dossier(cls, student_id: str) -> str:
        data = cls.get_full_student_report_data(student_id)
        text = "=" * 70 + "\n"
        text += "        ATTENDAI - OFFICIAL COLLEGE ATTENDANCE DOSSIER\n"
        text += "=" * 70 + "\n\n"
        text += f"Student: {data['student_name']} ({data['student_id']})\n"
        text += f"Department: {data['department']} | Year {data['year']}, Sem {data['semester']}\n"
        text += f"Contact: Phone: {data['contact']['phone']} | Email: {data['contact']['email']}\n"
        text += f"Date: {data['generated_at']}\n\n"
        text += "-" * 70 + "\n"
        text += f"OVERALL ATTENDANCE: {data['overall_percentage']:.2f}% ({data['overall_attended']}/{data['overall_conducted']} classes attended)\n"
        text += f"STATUS: {data['status']}\n"
        text += f"CLASSES REQUIRED FOR 80% TARGET: {data['needed_for_80']} consecutive lectures\n"
        text += "-" * 70 + "\n\n"
        text += "SUBJECT BREAKDOWN:\n"
        text += f"{'Code':<8} {'Subject Name':<24} {'Att/Cond':<10} {'%':<8} {'Status':<12} {'Needed'}\n"
        text += "-" * 70 + "\n"
        for s in data["subjects"]:
            att_cond = f"{s['attended']}/{s['conducted']}"
            needed_str = f"+{s['needed_for_80']}" if s['needed_for_80'] > 0 else "0"
            text += f"{s['subject_code']:<8} {s['subject_name']:<24} {att_cond:<10} {s['percentage']:<8.2f} {s['status']:<12} {needed_str}\n"
        text += "-" * 70 + "\n\n"
        text += "COLLEGE REGULATIONS & SAFEGUARDS:\n"
        text += "1. Minimum 80.0% aggregate attendance required for regular examination eligibility.\n"
        text += "2. 75.0% - 79.9% falls into condonation bracket subject to approved recovery plan.\n"
        text += "3. Attendance recovery is capped at 3 recovery classes/week per subject.\n\n"
        text += "Signed: AI Academic Safeguards Controller\n"
        return text
