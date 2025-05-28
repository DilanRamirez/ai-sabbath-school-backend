from PyPDF2 import PdfReader
import pymupdf4llm
from pathlib import Path
from typing import List, Optional


def sanitize(obj):
    """
    Recursively convert Rect instances and any non-serializable objects into JSON-friendly types.
    """
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if (
        hasattr(obj, "x0")
        and hasattr(obj, "y0")
        and hasattr(obj, "x1")
        and hasattr(obj, "y1")
    ):
        # Treat as Rect
        return {"x0": obj.x0, "y0": obj.y0, "x1": obj.x1, "y1": obj.y1}
    # Add more type checks if needed
    return obj


def extract_pdf_to_json(
    pdf_path: str, pages: Optional[List[int]] = None, page_chunks: bool = True
) -> dict:
    """
    Extracts markdown chunks from the PDF and gathers its metadata, returning a JSON-serializable dict.

    :param pdf_path: Path to the PDF file
    :param pages: Optional list of 0-based page indices to extract; None means all pages
    :param page_chunks: Whether to break pages into smaller chunks
    :return: Dict containing file, metadata, and chunks
    """
    # 1) Load PDF metadata via PyPDF2
    reader = PdfReader(pdf_path)
    # Extract standard PDF metadata as a dict
    info = reader.metadata if hasattr(reader, "metadata") else reader.getDocumentInfo()
    # Convert metadata to a plain dict
    pdf_meta = {key[1:]: value for key, value in info.items()} if info else {}

    # 2) Extract markdown chunks
    md_chunks = pymupdf4llm.to_markdown(
        doc=pdf_path, pages=pages, page_chunks=page_chunks
    )

    # Recursively sanitize all chunk content
    md_chunks = sanitize(md_chunks)

    # 3) Build output structure
    output = {"file": pdf_path, "metadata": pdf_meta, "chunks": md_chunks}
    return output


# if __name__ == "__main__":
#     # Adjust path as needed
#     pdf_path = "app/data/2025/Q2/lesson-08/lesson.pdf"
#     # Extract only first two pages as example
#     result = extract_pdf_to_json(pdf_path, pages=None, page_chunks=True)

#     # Build markdown output from chunks (ignore metadata)
#     chunks = result.get("chunks", [])
#     md_lines = []
#     for chunk in chunks:
#         if isinstance(chunk, dict):
#             text = chunk.get("text", "")
#         else:
#             text = str(chunk)
#         md_lines.append(text)
#     markdown_content = "\n\n".join(md_lines)

#     # Print to stdout
#     print(markdown_content)

#     # Write to .md file beside the PDF
#     out_file = Path(pdf_path).with_suffix(".md")
#     out_file.write_text(markdown_content, encoding="utf-8")
#     print(f"✅ Saved extracted Markdown to: {out_file}")
