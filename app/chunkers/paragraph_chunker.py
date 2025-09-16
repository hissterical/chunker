import fitz
from .base import BaseChunker
from typing import List, Dict, Any

class ParagraphChunker(BaseChunker):
    def chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        filename = pdf_path.split("/")[-1]
        chunks = []

        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            para_count = 0

            for block in blocks:
                if "lines" not in block:
                    continue

                para_text = ""
                bbox = None

                for line in block["lines"]:
                    for span in line["spans"]:
                        para_text += span["text"] + " "
                    if bbox is None:
                        bbox = line["bbox"]

                para_text = para_text.strip()
                if not para_text:
                    continue

                chunks.append({
                    "text": para_text,
                    "filename": filename,
                    "pageno": page_num + 1,
                    "bbox": bbox,
                    "parano": para_count
                })
                para_count += 1

        doc.close()
        return chunks