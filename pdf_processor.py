import pymupdf4llm

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file
    :param pdf_path:
    :return: Markdown text of the PDF file
    """
    markdown_text = pymupdf4llm.to_markdown(pdf_path)
    return markdown_text