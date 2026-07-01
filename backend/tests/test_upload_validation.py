"""Resume upload hardening: type allowlist, size cap, empty rejection.

The upload endpoint must reject bad input BEFORE parsing, never buffer more
than the size cap, and audit-log rejections (extension only, never contents).
"""

import io

from docx import Document

from app.models import AuditEvent
from app.services.resume_file import MAX_FILE_BYTES


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _upload(client, filename: str, data: bytes, content_type: str):
    return client.post(
        "/profile/resume-file",
        files={"file": (filename, io.BytesIO(data), content_type)},
    )


def test_rejects_unsupported_extension(client):
    res = _upload(client, "resume.txt", b"plain text resume", "text/plain")
    assert res.status_code == 400


def test_rejects_dangerous_extension_with_allowed_content_type(client):
    # Content-type is spoofable; the extension allowlist must still reject.
    res = _upload(client, "resume.exe", b"MZ....", "application/pdf")
    assert res.status_code == 400


def test_rejects_oversized_file(client):
    res = _upload(
        client, "resume.pdf", b"x" * (MAX_FILE_BYTES + 1), "application/pdf"
    )
    assert res.status_code == 413


def test_rejects_empty_file(client):
    res = _upload(client, "resume.pdf", b"", "application/pdf")
    assert res.status_code == 400


def test_accepts_valid_docx(client):
    data = _docx_bytes(
        "Ayşe Yılmaz\nJunior backend engineer. Skills: Python, FastAPI, SQL."
    )
    res = _upload(
        client,
        "resume.docx",
        data,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert res.status_code == 200
    body = res.json()
    assert "Python" in body["skills"]


def test_rejections_are_audit_logged(client, db_session):
    _upload(client, "resume.txt", b"nope", "text/plain")
    events = db_session.query(AuditEvent).filter(AuditEvent.event == "upload_rejected").all()
    assert len(events) >= 1
    # Only the filename tail is recorded — never file contents.
    assert all(e.note is None or len(e.note) <= 20 for e in events)
