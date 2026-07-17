import json
import re
from pathlib import Path
import sys

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", 
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", 
    "Nagaland", "Odisha", "Orissa", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", 
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", 
    "Jammu & Kashmir", "Jammu", "Kashmir", "J&K", "Ladakh"
]

CROPS = [
    "Rice", "Paddy", "Wheat", "Maize", "Sugarcane", "Cotton", "Jute", 
    "Soyabean", "Soybean", "Groundnut", "Mustard", "Arhar", "Tur", 
    "Urad", "Moong", "Gram", "Masur", "Bajra", "Jowar", "Ragi", "Sesamum", 
    "Sunflower", "Pulses", "Oilseeds", "Cereals"
]

class SemanticChunker:
    """Chunks Docling output into agricultural semantic observations."""

    def __init__(self):
        # Compiled regex for fast lookup
        self.state_patterns = [(state, re.compile(rf"\b{re.escape(state)}\b", re.IGNORECASE)) for state in STATES]
        self.crop_patterns = [(crop, re.compile(rf"\b{re.escape(crop)}\b", re.IGNORECASE)) for crop in CROPS]

    def _detect_entities(self, text: str):
        """Simple regex-based detection of crop and state in a text segment."""
        detected_state = None
        detected_crop = None
        
        for state, pattern in self.state_patterns:
            if pattern.search(text):
                detected_state = state
                break
        
        for crop, pattern in self.crop_patterns:
            if pattern.search(text):
                detected_crop = crop
                break
                
        return detected_crop, detected_state

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split paragraph text into individual sentences."""
        if not text:
            return []
        # Basic sentence splitting (handles dots, exclamation, question marks)
        sentences = re.split(r'(?<=[.!?]) +', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _table_to_rows(self, table_obj: dict) -> list[dict]:
        """Convert a table object to a list of row descriptions."""
        grid = table_obj.get("data", {}).get("grid", [])
        if not grid:
            return []
            
        headers = []
        rows_data = []
        
        # Identify headers (usually first row, or column_header=True)
        first_row = grid[0] if grid else []
        headers = [cell.get("text", "").strip() for cell in first_row]
        
        # If headers are empty or placeholder-like, use index numbers
        headers = [h if h else f"Col_{i}" for i, h in enumerate(headers)]
        
        # Reconstruct rows
        for r_idx, row in enumerate(grid):
            # Skip header row if it is exactly the first one
            if r_idx == 0 and any(cell.get("column_header", False) for cell in row):
                continue
            
            row_cells = []
            row_dict = {}
            for c_idx, cell in enumerate(row):
                header = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
                val = cell.get("text", "").strip()
                row_dict[header] = val
                row_cells.append(f"{header}: {val}")
            
            rows_data.append({
                "text": " | ".join(row_cells),
                "structured": row_dict
            })
            
        return rows_data

    def chunk_document(self, doc_dict: dict, source_pdf: str) -> list[dict]:
        """
        Chunks the document based on semantic boundaries:
        heading changes, crop changes, state changes, and list items/tables.
        """
        body = doc_dict.get("body", {})
        
        # Flatten the children tree of body to get order of reading
        items = []
        def traverse(node):
            ref = node.get("$ref")
            if ref:
                parts = ref.strip("#/").split("/")
                if len(parts) == 2:
                    key, idx = parts[0], int(parts[1])
                    target_list = doc_dict.get(key, [])
                    if idx < len(target_list):
                        item = target_list[idx].copy()
                        item["type"] = key
                        items.append(item)
            for child in node.get("children", []):
                traverse(child)
                
        traverse(body)
        
        chunks = []
        current_heading = "Root"
        current_crop = None
        current_state = None
        
        chunk_idx = 0
        
        for item in items:
            item_type = item.get("type")
            page_no = 1
            if "prov" in item and item["prov"]:
                page_no = item["prov"][0].get("page_no", 1)

            if item_type == "texts":
                label = item.get("label", "paragraph")
                text = item.get("text", "").strip()
                if not text:
                    continue

                # Section Heading changes
                if label == "section_header":
                    current_heading = text
                    # Heading is its own chunk
                    chunks.append({
                        "chunk_id": f"{source_pdf}_{chunk_idx}",
                        "text": text,
                        "heading": current_heading,
                        "page_number": page_no,
                        "source_pdf": source_pdf,
                        "type": "heading"
                    })
                    chunk_idx += 1
                    # Reset contexts
                    current_crop = None
                    current_state = None
                    continue

                # Split paragraphs/list items into sentences to do micro-chunking
                sentences = self._split_into_sentences(text)
                
                temp_chunk_text = []
                for sentence in sentences:
                    crop, state = self._detect_entities(sentence)
                    
                    # Determine if context changed
                    crop_changed = crop is not None and crop != current_crop
                    state_changed = state is not None and state != current_state
                    is_advisory = any(word in sentence.lower() for word in ["advised", "advisory", "should", "recommend"])
                    
                    # Split if: crop changes, state changes, or is advisory
                    if (crop_changed or state_changed or is_advisory) and temp_chunk_text:
                        # Save current accumulated chunk
                        chunks.append({
                            "chunk_id": f"{source_pdf}_{chunk_idx}",
                            "text": " ".join(temp_chunk_text),
                            "heading": current_heading,
                            "page_number": page_no,
                            "source_pdf": source_pdf,
                            "type": "text_observation",
                            "crop_context": current_crop,
                            "state_context": current_state
                        })
                        chunk_idx += 1
                        temp_chunk_text = []

                    # Update context
                    if crop:
                        current_crop = crop
                    if state:
                        current_state = state
                        
                    temp_chunk_text.append(sentence)

                if temp_chunk_text:
                    chunks.append({
                        "chunk_id": f"{source_pdf}_{chunk_idx}",
                        "text": " ".join(temp_chunk_text),
                        "heading": current_heading,
                        "page_number": page_no,
                        "source_pdf": source_pdf,
                        "type": "text_observation",
                        "crop_context": current_crop,
                        "state_context": current_state
                    })
                    chunk_idx += 1

            elif item_type == "tables":
                # Convert table rows to descriptions
                rows = self._table_to_rows(item)
                for r in rows:
                    row_text = r["text"]
                    crop, state = self._detect_entities(row_text)
                    chunks.append({
                        "chunk_id": f"{source_pdf}_{chunk_idx}",
                        "text": f"Table under section '{current_heading}': {row_text}",
                        "heading": current_heading,
                        "page_number": page_no,
                        "source_pdf": source_pdf,
                        "type": "table_row",
                        "crop_context": crop or current_crop,
                        "state_context": state or current_state,
                        "structured_row": r["structured"]
                    })
                    chunk_idx += 1
                    
        return chunks

if __name__ == "__main__":
    # Test on a saved docling json
    json_files = list(config.DOCLING_JSON_DIR.glob("*.json"))
    if json_files:
        with open(json_files[0], "r", encoding="utf-8") as f:
            doc = json.load(f)
        chunker = SemanticChunker()
        chunks = chunker.chunk_document(doc, json_files[0].name)
        print(f"Generated {len(chunks)} chunks from {json_files[0].name}")
        if chunks:
            print("Sample chunk:", chunks[0])
    else:
        print("No Docling JSON found to test chunking.")
