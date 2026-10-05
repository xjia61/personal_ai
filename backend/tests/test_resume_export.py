from io import BytesIO

from docx import Document
from pypdf import PdfReader

from app.services.resume_export import (
    build_resume_docx,
    build_resume_pdf,
)


SAMPLE_RESUME = """
Xu Cao
Houston, TX

EXPERIENCE

Software Developer
Built applications using Python and React.

EDUCATION

Master of Science in Computer Science
"""


def test_docx_export():
    content = build_resume_docx(
        SAMPLE_RESUME
    )

    assert content[:2] == b"PK"

    document = Document(
        BytesIO(content)
    )

    text = "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
    )

    assert "Xu Cao" in text
    assert "Software Developer" in text


def test_pdf_export():
    content = build_resume_pdf(
        SAMPLE_RESUME
    )

    assert content[:4] == b"%PDF"

    reader = PdfReader(
        BytesIO(content)
    )

    assert len(reader.pages) >= 1

    text = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    assert "Xu Cao" in text
    assert "Software Developer" in text