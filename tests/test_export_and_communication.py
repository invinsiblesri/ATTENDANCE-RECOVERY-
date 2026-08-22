import xml.etree.ElementTree as ET
import json
from fastapi.testclient import TestClient
from agent.api import app
from services.export_service import ExportService, get_student_contact
from services.communication_service import CommunicationService
from agent.multi_agent import multi_agent_system

client = TestClient(app)


def test_student_contacts_mapping():
    c1 = get_student_contact("S001")
    assert c1["phone"] == "9042778493"
    assert c1["email"] == "wellz.bot@gmail.com"


def test_export_pdf():
    pdf_bytes = ExportService.generate_pdf("S001")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")


def test_export_xml():
    xml_str = ExportService.generate_xml("S001")
    assert isinstance(xml_str, str)
    assert "<AttendanceReport" in xml_str
    assert "9042778493" in xml_str
    assert "wellz.bot@gmail.com" in xml_str
    assert "78.75" in xml_str
    # Verify valid XML
    root = ET.fromstring(xml_str)
    assert root.tag == "AttendanceReport"


def test_export_json():
    json_str = ExportService.generate_json("S001")
    data = json.loads(json_str)
    assert data["student_id"] == "S001"
    assert data["overall_percentage"] == 78.75
    assert data["needed_for_80"] == 15
    assert data["contact"]["phone"] == "9042778493"
    assert data["contact"]["email"] == "wellz.bot@gmail.com"
    assert len(data["subjects"]) == 8


def test_export_csv():
    csv_str = ExportService.generate_csv("S001")
    assert "ATTENDAI - OFFICIAL ATTENDANCE TRANSCRIPT" in csv_str
    assert "9042778493" in csv_str
    assert "wellz.bot@gmail.com" in csv_str


def test_communication_sms_and_email():
    res = CommunicationService.broadcast_multi_channel("S001")
    assert res["success"] is True
    assert res["sms"]["recipient_phone"] == "9042778493"
    assert res["sms"]["status"] == "DELIVERED"
    assert res["email"]["recipient_email"] == "wellz.bot@gmail.com"
    assert res["email"]["status"] == "DELIVERED"


def test_api_export_endpoints():
    res_pdf = client.get("/api/export/S001/pdf")
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert res_pdf.content.startswith(b"%PDF-")

    res_xml = client.get("/api/export/S001/xml")
    assert res_xml.status_code == 200
    assert "application/xml" in res_xml.headers["content-type"]
    assert "<AttendanceReport" in res_xml.text

    res_json = client.get("/api/export/S001/json")
    assert res_json.status_code == 200
    assert res_json.json()["student_id"] == "S001"


def test_api_communication_endpoint():
    payload = {
        "student_id": "S001",
        "channel": "both",
        "phone": "9042778493",
        "email": "wellz.bot@gmail.com",
        "message": "Urgent recovery alert test"
    }
    res = client.post("/api/communication/send", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["results"]["sms"]["recipient_phone"] == "9042778493"
    assert data["results"]["email"]["recipient_email"] == "wellz.bot@gmail.com"


def test_orchestrator_export_query():
    res = multi_agent_system.process_query("S001", "Give me the attendance percentage as PDF")
    assert "Export Agent" in res["active_agent"]
    assert res["download_url"] == "/api/export/S001/pdf"
    assert "Download Official PDF" in res["answer"]

    res_xml = multi_agent_system.process_query("S001", "Give me the report as XML")
    assert "XML" in res_xml["active_agent"]
    assert res_xml["download_url"] == "/api/export/S001/xml"


def test_orchestrator_notification_query():
    res = multi_agent_system.process_query("S001", "Send notification via phone number 9042778493 or email wellz.bot@gmail.com")
    assert "Communication Agent" in res["active_agent"]
    assert "9042778493" in res["answer"]
    assert "wellz.bot@gmail.com" in res["answer"]
    assert "DELIVERED" in res["answer"]
