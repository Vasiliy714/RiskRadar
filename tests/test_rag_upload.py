from app.rag.parsers import SourceFormat, detect_source_format


def test_detect_source_format_from_filename() -> None:
    assert detect_source_format(filename="report.pdf", content_type=None) == SourceFormat.PDF
    assert detect_source_format(filename="page.html", content_type=None) == SourceFormat.HTML
    assert detect_source_format(filename="notes.txt", content_type=None) == SourceFormat.TEXT


def test_detect_source_format_from_content_type() -> None:
    assert (
        detect_source_format(filename=None, content_type="application/pdf")
        == SourceFormat.PDF
    )
