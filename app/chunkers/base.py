from typing import List, Dict, Any
from abc import ABC, abstractmethod

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        
        """
        Returns list of chunks. Each chunk is a dict:
        {
            "text": str,
            "filename": str,
            "pageno": int,
            "bbox": tuple (x0, y0, x1, y1),
            "parano": int (optional)
        }
        """
        pass