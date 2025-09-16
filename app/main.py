import streamlit as st
import os
import inspect
from chunkers.base import BaseChunker
from chunkers import *
from viewer import render_page_with_boxes, show_chunk_details
import chunkers
import fitz
from PIL import Image, ImageDraw

st.set_page_config(layout="wide")
st.title("📄 PDF Chunking Visualizer")

# Auto-discover all chunkers
def get_available_chunkers():
    chunkers = {}
    for name, obj in inspect.getmembers(chunkers):
        if (inspect.isclass(obj) and 
            issubclass(obj, BaseChunker) and 
            obj != BaseChunker):
            chunkers[obj.__name__] = obj()
    return chunkers

# Get all available chunkers dynamically
CHUNKER_CLASSES = {}
for name, obj in inspect.getmembers(chunkers):
    if (inspect.isclass(obj) and 
        issubclass(obj, BaseChunker) and 
        obj != BaseChunker):
        CHUNKER_CLASSES[obj.__name__] = obj

FILES_DIR = "files"
PDF_FILES = [f for f in os.listdir(FILES_DIR) if f.endswith(".pdf")]

if not PDF_FILES:
    st.error(f"No PDFs found in `{FILES_DIR}/`")
    st.stop()

# UI for chunker selection
selected_pdf = st.selectbox("Choose PDF", PDF_FILES)
pdf_path = os.path.join(FILES_DIR, selected_pdf)

# Multi-select for chunkers
chunker_names = st.multiselect(
    "Select Chunkers to Compare", 
    list(CHUNKER_CLASSES.keys()),
    default=list(CHUNKER_CLASSES.keys())[:1]  # Select first by default
)

if st.button("Chunk & Visualize") and chunker_names:
    all_chunks = {}
    
    for name in chunker_names:
        with st.spinner(f"Chunking with {name}..."):
            chunker = CHUNKER_CLASSES[name]()
            chunks = chunker.chunk(pdf_path)
            all_chunks[name] = chunks
    
    st.session_state["all_chunks"] = all_chunks
    st.session_state["pdf_path"] = pdf_path
    st.session_state["total_pages"] = len(fitz.open(pdf_path))

if "all_chunks" in st.session_state:
    all_chunks = st.session_state["all_chunks"]
    pdf_path = st.session_state["pdf_path"]
    total_pages = st.session_state["total_pages"]

    st.sidebar.title("📄 Page Navigator")
    page_num = st.sidebar.selectbox("Go to page", range(1, total_pages + 1), index=0)
    
    # Color coding for different chunkers
    colors = ["red", "blue", "green", "orange", "purple", "brown"]
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📄 PDF with Chunk Boxes")
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)
        
        # Draw boxes for each chunker
        for idx, (chunker_name, chunks) in enumerate(all_chunks.items()):
            color = colors[idx % len(colors)]
            page_chunks = [c for c in chunks if c["pageno"] == page_num]
            
            for chunk in page_chunks:
                x0, y0, x1, y1 = chunk["bbox"]
                x0 *= 2; y0 *= 2; x1 *= 2; y1 *= 2
                draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
                
                # Show chunker name and para number
                label = f"{chunker_name[:3]}:{chunk.get('parano', '?')}"
                draw.text((x0, y0 - 15), label, fill=color)
        
        doc.close()
        st.image(img, use_column_width=True)

    with col2:
        st.subheader(f"Chunks on Page {page_num}")
        for idx, (chunker_name, chunks) in enumerate(all_chunks.items()):
            color = colors[idx % len(colors)]
            st.markdown(f"**<span style='color:{color}'>{chunker_name}</span>**", unsafe_allow_html=True)
            
            page_chunks = [c for c in chunks if c["pageno"] == page_num]
            for c in page_chunks:
                with st.expander(f"Para {c.get('parano', '?')} [bbox: {c['bbox']}]"):
                    st.write(c["text"])