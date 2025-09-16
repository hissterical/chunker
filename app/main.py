import streamlit as st
import os
from chunkers.paragraph_chunker import ParagraphChunker
from viewer import render_page_with_boxes, show_chunk_details
import fitz

CHUNKER = ParagraphChunker()
FILES_DIR = "files"
PDF_FILES = [f for f in os.listdir(FILES_DIR) if f.endswith(".pdf")]

st.set_page_config(layout="wide")
st.title("📄 PDF Chunking Visualizer")

if not PDF_FILES:
    st.error(f"No PDFs found in `{FILES_DIR}/`")
    st.stop()

selected_pdf = st.selectbox("Choose PDF", PDF_FILES)
pdf_path = os.path.join(FILES_DIR, selected_pdf)

if st.button("Chunk & Visualize"):
    with st.spinner("Chunking..."):
        chunks = CHUNKER.chunk(pdf_path)
        st.session_state["chunks"] = chunks
        st.session_state["pdf_path"] = pdf_path
        st.session_state["total_pages"] = len(fitz.open(pdf_path))

if "chunks" in st.session_state:
    chunks = st.session_state["chunks"]
    pdf_path = st.session_state["pdf_path"]
    total_pages = st.session_state["total_pages"]

    st.sidebar.title("📄 Page Navigator")
    page_num = st.sidebar.selectbox("Go to page", range(1, total_pages + 1), index=0)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📄 PDF with Chunk Boxes")
        img = render_page_with_boxes(pdf_path, page_num, chunks)
        st.image(img, use_column_width=True)

    with col2:
        show_chunk_details(chunks, page_num)