"""
Smoke test for the PDF pipeline (structure extraction, redaction-based
deletion, page-splice addition, diffing, and the FastAPI routes).

The instruction_parser.parse_instructions call is monkeypatched here purely
because this sandbox has no network access to api.anthropic.com — it is
NOT mocked in the actual app. Run this against a real ANTHROPIC_API_KEY
to test that part for real.
"""

import sys

import fitz
from fastapi.testclient import TestClient

sys.path.insert(0, ".")

from app import main, store  # noqa: E402


def build_sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    def heading(text, y):
        page.insert_text((56, y), text, fontsize=16, fontname="hebo")

    def body(text, y):
        page.insert_textbox(fitz.Rect(56, y, 556, y + 80), text, fontsize=11, fontname="helv")

    heading("1. Payment Terms", 80)
    body("Customer agrees to pay invoices within thirty (30) days of receipt.", 105)

    heading("2. Termination Clause", 220)
    body("Either party may terminate this agreement with sixty (60) days written notice.", 245)

    heading("3. Confidentiality", 340)
    body("Each party shall keep the other's confidential information secret.", 365)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def fake_parse_instructions(sections, instructions):
    from app.store import ParsedOperation

    section_by_title = {s.title: s for s in sections}
    termination = section_by_title["2. Termination Clause"]
    payment = section_by_title["1. Payment Terms"]

    return [
        ParsedOperation(
            id="op1",
            op="delete_section",
            target_section_id=termination.id,
            candidate_section_ids=[],
            new_title=None,
            content=None,
            confidence=0.95,
            needs_confirmation=False,
            label=f'Delete "{termination.title}"',
            ambiguity_note=None,
        ),
        ParsedOperation(
            id="op2",
            op="append_to_section",
            target_section_id=payment.id,
            candidate_section_ids=[],
            new_title=None,
            content="Late payments accrue interest at 1.5% per month.",
            confidence=0.9,
            needs_confirmation=False,
            label=f'Add to "{payment.title}"',
            ambiguity_note=None,
        ),
    ]


def run():
    main.parse_instructions = fake_parse_instructions
    client = TestClient(main.app)

    pdf_bytes = build_sample_pdf()

    print("== /api/health ==")
    r = client.get("/api/health")
    print(r.status_code, r.json())
    assert r.status_code == 200

    print("\n== /api/analyze ==")
    r = client.post(
        "/api/analyze",
        files={"file": ("contract.pdf", pdf_bytes, "application/pdf")},
        data={"instructions": "Remove the termination clause and add a late fee note to payment terms"},
    )
    print(r.status_code, r.json())
    assert r.status_code == 200, r.text
    body = r.json()
    job_id = body["jobId"]
    assert len(body["operations"]) == 2
    assert all(not op["needsConfirmation"] for op in body["operations"])

    print("\n== /api/jobs/{job_id}/apply ==")
    r = client.post(f"/api/jobs/{job_id}/apply")
    print(r.status_code, r.json())
    assert r.status_code == 200, r.text
    apply_body = r.json()

    print("\n== /api/download/{token} ==")
    download_url = apply_body["downloadUrl"]
    token = download_url.rsplit("/", 1)[-1]
    r = client.get(f"/api/download/{token}")
    assert r.status_code == 200, r.text
    out_pdf = r.content
    print(f"Downloaded {len(out_pdf)} bytes, content-type={r.headers['content-type']}")

    out_doc = fitz.open(stream=out_pdf, filetype="pdf")
    full_text = "\n".join(p.get_text("text") for p in out_doc)
    out_doc.close()

    assert "Termination Clause" not in full_text, "deleted section text should be gone"
    assert "1.5% per month" in full_text, "appended content should be present"
    assert "Confidentiality" in full_text, "untouched section should survive"
    print("\nContent assertions passed: deletion removed, addition present, untouched section intact.")

    print("\n== expired/invalid token ==")
    r = client.get("/api/download/not-a-real-token")
    print(r.status_code)
    assert r.status_code == 404

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    run()
