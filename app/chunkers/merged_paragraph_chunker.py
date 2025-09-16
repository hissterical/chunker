import fitz
from .base import BaseChunker
from typing import List, Dict, Any

class MergedParagraphChunker(BaseChunker):
    def __init__(self, min_length=150, max_line_gap=15, max_line_height_diff=50):
        self.min_length = min_length  # Min chars for a standalone paragraph
        self.max_line_gap = max_line_gap  # Max vertical gap to merge lines
        self.max_line_height_diff = max_line_height_diff  # Max height diff to merge

    def chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        filename = pdf_path.split("/")[-1]
        chunks = []

        for page_num, page in enumerate(doc):
            # Get all text blocks with precise positioning
            blocks = page.get_text("dict")["blocks"]
            lines_data = []
            
            # Extract all lines with their positions
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    text = ""
                    for span in line["spans"]:
                        text += span["text"]
                    
                    if text.strip():
                        lines_data.append({
                            "text": text.strip(),
                            "bbox": line["bbox"],
                            "y_center": (line["bbox"][1] + line["bbox"][3]) / 2
                        })

            # Sort lines by vertical position
            lines_data.sort(key=lambda x: x["y_center"])
            
            # Merge lines into paragraphs
            i = 0
            para_count = 0
            
            while i < len(lines_data):
                current_lines = [lines_data[i]]
                current_text = lines_data[i]["text"]
                current_bbox = lines_data[i]["bbox"]
                
                # Keep merging while lines are close together
                while i + 1 < len(lines_data):
                    next_line = lines_data[i + 1]
                    current_line = lines_data[i]
                    
                    # Calculate gaps and differences
                    vertical_gap = next_line["bbox"][1] - current_line["bbox"][3]
                    height_diff = abs((current_line["bbox"][3] - current_line["bbox"][1]) - 
                                    (next_line["bbox"][3] - next_line["bbox"][1]))
                    horizontal_overlap = max(0, min(current_line["bbox"][2], next_line["bbox"][2]) - 
                                           max(current_line["bbox"][0], next_line["bbox"][0]))
                    
                    # Conditions for merging:
                    # 1. Small vertical gap
                    # 2. Similar line heights
                    # 3. Some horizontal overlap OR very small gap
                    # 4. Current text is still short OR next line is continuation
                    should_merge = (
                        vertical_gap <= self.max_line_gap and
                        height_diff <= self.max_line_height_diff and
                        (horizontal_overlap > 0 or vertical_gap < 5) and
                        (len(current_text) < self.min_length or 
                         self._looks_like_continuation(current_text, next_line["text"]))
                    )
                    
                    if should_merge:
                        current_lines.append(next_line)
                        current_text += " " + next_line["text"]
                        
                        # Update bounding box
                        x0 = min(current_bbox[0], next_line["bbox"][0])
                        y0 = min(current_bbox[1], next_line["bbox"][1])
                        x1 = max(current_bbox[2], next_line["bbox"][2])
                        y1 = max(current_bbox[3], next_line["bbox"][3])
                        current_bbox = (x0, y0, x1, y1)
                        
                        i += 1
                    else:
                        break
                
                # Add merged paragraph
                if current_text.strip():
                    chunks.append({
                        "text": current_text.strip(),
                        "filename": filename,
                        "pageno": page_num + 1,
                        "bbox": current_bbox,
                        "parano": para_count
                    })
                    para_count += 1
                
                i += 1

        doc.close()
        return chunks

    def _looks_like_continuation(self, current_text, next_text):
        """Heuristic to detect if next line is continuation of current"""
        # If current ends with dash, it's definitely continuation
        if current_text.endswith('-'):
            return True
        
        # If next starts with lowercase, likely continuation
        if next_text and next_text[0].islower():
            return True
            
        # If current doesn't end with sentence-ending punctuation
        if not current_text.endswith(('.', '!', '?')):
            return True
            
        return False