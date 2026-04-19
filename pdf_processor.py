"""PDF text extraction helpers used to prepare documents for AI parsing."""
import pymupdf4llm

def extract_text_from_pdf(pdf_path: str) -> str:
    """Convert a PDF file to Markdown-formatted text.

    :param pdf_path: filesystem path to the PDF to read.
    :return: Markdown representation of the PDF contents.
    """
    markdown_text = pymupdf4llm.to_markdown(pdf_path)
    return markdown_text