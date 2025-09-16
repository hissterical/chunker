import fitz
import streamlit as st
from PIL import Image, ImageDraw

def render_page_with_boxes(pdf_path: str, page_num: int, chunks: list):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num - 1)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    draw = ImageDraw.Draw(img)
    page_chunks = [c for c in chunks if c["pageno"] == page_num]

    for chunk in page_chunks:
        x0, y0, x1, y1 = chunk["bbox"]
        x0 *= 2; y0 *= 2; x1 *= 2; y1 *= 2
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        if "parano" in chunk:
            draw.text((x0, y0 - 15), str(chunk["parano"]), fill="blue")

    doc.close()
    return img

def show_chunk_details(chunks: list, page_num: int):
    st.subheader(f"Chunks on Page {page_num}")
    for c in chunks:
        if c["pageno"] == page_num:
            with st.expander(f"Para {c.get('parano', '?')} [bbox: {c['bbox']}]"):
                st.write(c["text"])