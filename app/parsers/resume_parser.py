import io

from pypdf import PdfReader
import docx2txt


class UnsupportedResumeFormat(Exception):
    pass


def extract_text(file_bytes: bytes, file_name: str) -> str:
    ext = file_name.lower().rsplit(".", 1)[-1]

    if ext == "pdf":
        return _extract_pdf(file_bytes)
    elif ext == "docx":
        return _extract_docx(file_bytes)
    else:
        raise UnsupportedResumeFormat(f"Unsupported format '{ext}' for {file_name}")


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes) -> str:
    with io.BytesIO(file_bytes) as buf:
        return docx2txt.process(buf) or ""