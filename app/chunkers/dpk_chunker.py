import os
import glob
import shutil
import pandas as pd
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from .base import BaseChunker

from dpk_pdf2parquet.transform_python import Pdf2Parquet
from dpk_pdf2parquet.transform import pdf2parquet_contents_types
from dpk_ededup.transform_python import Ededup
from dpk_doc_chunk.transform_python import DocChunk

# --- Concrete Implementation using Data Prep Kit ---
class DpkChunker(BaseChunker):
    def __init__(self, job_dir: str = "job/"):
        self.job_dir = job_dir
        self.input_dir = os.path.join(job_dir, "input")
        self.output_dir = os.path.join(job_dir, "output")

    def _prepare_dirs(self, pdf_path: str) -> str:
        """Reset input/output dirs and copy the PDF into input_dir."""
        # Reset dirs
        shutil.rmtree(self.input_dir, ignore_errors=True)
        shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Copy single PDF into input_dir
        pdf_filename = os.path.basename(pdf_path)
        input_pdf_path = os.path.join(self.input_dir, pdf_filename)
        shutil.copy(pdf_path, input_pdf_path)

        return pdf_filename

    def chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Run the full pipeline and return structured chunks."""
        if not pdf_path.lower().endswith(".pdf"):
            raise ValueError(f"Invalid file type: {pdf_path}. Must be a .pdf file.")

        pdf_filename = self._prepare_dirs(pdf_path)

        # Prepare pipeline subdirectories
        output_parquet_dir = os.path.join(self.output_dir, "01_parquet_out")
        output_exact_dedupe_dir = os.path.join(self.output_dir, "02_dedupe_out")
        output_chunk_dir = os.path.join(self.output_dir, "03_chunk_out")
        for folder in [output_parquet_dir, output_exact_dedupe_dir, output_chunk_dir]:
            os.makedirs(folder, exist_ok=True)

        # --- Step 1: PDF → Parquet ---
        Pdf2Parquet(
            input_folder=self.input_dir,
            output_folder=output_parquet_dir,
            data_files_to_use=[".pdf"],
            pdf2parquet_do_ocr=False,
            pdf2parquet_contents_type=pdf2parquet_contents_types.JSON,
        ).transform()

        # --- Step 2: Deduplicate ---
        Ededup(
            input_folder=output_parquet_dir,
            output_folder=output_exact_dedupe_dir,
            ededup_doc_column="contents",
            ededup_doc_id_column="document_id",
        ).transform()

        # --- Step 3: Chunking ---
        DocChunk(
            input_folder=output_exact_dedupe_dir,
            output_folder=output_chunk_dir,
            doc_chunk_chunking_type="dl_json",  # JSON mode
            doc_chunk_chunk_size_tokens=128,
            doc_chunk_chunk_overlap_tokens=30,
            doc_chunk_output_pageno_column_name="pageno",
            doc_chunk_output_bbox_column_name="bbox",
        ).transform()

        # --- Step 4: Collect results ---
        chunks: List[Dict[str, Any]] = []
        parquet_files = glob.glob(os.path.join(output_chunk_dir, "*.parquet"))

        for parquet_file in parquet_files:
            df = pd.read_parquet(parquet_file)
            for _, row in df.iterrows():
                text = row.get("contents", "")
                filename = row.get("filename", pdf_filename)
                page = int(row.get("pageno", -1))
                bbox_data = row.get("bbox")
                bbox = tuple(bbox_data) if bbox_data is not None and len(bbox_data) > 0 else None
                parano = None
                if "doc_jsonpath" in row and isinstance(row["doc_jsonpath"], str):
                    try:
                        parano = int(row["doc_jsonpath"].split("/")[-1])
                    except Exception:
                        parano = None

                chunks.append({
                    "text": text,
                    "filename": filename,
                    "pageno": page,
                    "bbox": bbox,
                    "parano": parano,
                })

        print(f"✅ Extracted {len(chunks)} chunks from {pdf_filename}")
        return chunks
