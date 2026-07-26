import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"

def load_csv_mapping(filename: str, key_col: str = "synonym", val_col: str = "standard_name") -> dict:
    csv_path = RESOURCES_DIR / filename
    mapping = {}
    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    k = row.get(key_col, "").strip().lower()
                    v = row.get(val_col, "").strip()
                    if k and v:
                        mapping[k] = v
        except Exception:
            pass
    return mapping

STATE_MAPPING = {
    "orissa": "Odisha",
    "odisha": "Odisha",
    "karnataka": "Karnataka",
    "maharashtra": "Maharashtra",
    "andhra pradesh": "Andhra Pradesh",
    "ap": "Andhra Pradesh",
    "tamil nadu": "Tamil Nadu",
    "tn": "Tamil Nadu",
    "kerala": "Kerala",
    "gujarat": "Gujarat",
    "punjab": "Punjab",
    "haryana": "Haryana",
    "rajasthan": "Rajasthan",
    "west bengal": "West Bengal",
    "wb": "West Bengal",
    "bihar": "Bihar",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "chhattisgarh": "Chhattisgarh",
    "jharkhand": "Jharkhand",
    "himachal pradesh": "Himachal Pradesh",
    "hp": "Himachal Pradesh",
    "uttarakhand": "Uttarakhand",
    "assam": "Assam",
    "telangana": "Telangana",
    "jammu & kashmir": "Jammu & Kashmir",
    "j&k": "Jammu & Kashmir",
    "jammu and kashmir": "Jammu & Kashmir",
    "ladakh": "Ladakh",
    "all india": "All India",
    "india": "All India"
}

CROP_MAPPING = {
    "paddy": "Rice",
    "rice": "Rice",
    "wheat": "Wheat",
    "maize": "Maize",
    "corn": "Maize",
    "sugarcane": "Sugarcane",
    "cotton": "Cotton",
    "jute": "Jute",
    "mesta": "Jute",
    "soyabean": "Soybean",
    "soybean": "Soybean",
    "groundnut": "Groundnut",
    "peanut": "Groundnut",
    "mustard": "Mustard",
    "rapeseed": "Mustard",
    "arhar": "Pigeonpea (Arhar)",
    "tur": "Pigeonpea (Arhar)",
    "pigeonpea": "Pigeonpea (Arhar)",
    "urad": "Black Gram (Urad)",
    "uradbean": "Black Gram (Urad)",
    "black gram": "Black Gram (Urad)",
    "moong": "Green Gram (Moong)",
    "moongbean": "Green Gram (Moong)",
    "green gram": "Green Gram (Moong)",
    "gram": "Bengal Gram (Gram/Chickpea)",
    "chickpea": "Bengal Gram (Gram/Chickpea)",
    "bengal gram": "Bengal Gram (Gram/Chickpea)",
    "masur": "Lentil (Masur)",
    "lentil": "Lentil (Masur)",
    "bajra": "Pearl Millet (Bajra)",
    "pearl millet": "Pearl Millet (Bajra)",
    "jowar": "Sorghum (Jowar)",
    "sorghum": "Sorghum (Jowar)",
    "ragi": "Finger Millet (Ragi)",
    "finger millet": "Finger Millet (Ragi)",
    "sesamum": "Sesame (Sesamum)",
    "sesame": "Sesame (Sesamum)",
    "sunflower": "Sunflower",
    "castor": "Castor",
    "shri anna": "Coarse Cereals",
    "coarse cereals": "Coarse Cereals",
    "pulses": "Pulses",
    "oilseeds": "Oilseeds"
}

STAGE_MAPPING = {
    "sowing": "Sowing",
    "sown": "Sowing",
    "planting": "Sowing",
    "nursery": "Nursery",
    "germination": "Germination",
    "seedling": "Seedling",
    "vegetative": "Vegetative",
    "veg stage": "Vegetative",
    "tillering": "Tillering",
    "panicle": "Panicle Initiation",
    "panicle initiation": "Panicle Initiation",
    "flowering": "Flowering",
    "pod formation": "Pod Formation",
    "grain filling": "Grain Filling",
    "maturity": "Maturity",
    "harvesting": "Harvesting",
    "harvest": "Harvesting"
}

PEST_DISEASE_MAPPING = {
    "downy mildew": "Downy mildew",
    "powdery mildew": "Powdery mildew",
    "stem borer": "Stem borer",
    "blast": "Blast",
    "sheath blight": "Sheath blight",
    "bacterial leaf blight": "Bacterial leaf blight",
    "brown plant hopper": "Brown plant hopper",
    "leaf folder": "Leaf folder",
    "fall armyworm": "Fall armyworm",
    "pod borer": "Pod borer",
    "bollworm": "Bollworm",
    "aphid": "Aphids",
    "aphids": "Aphids",
    "whitefly": "Whitefly",
    "yellow mosaic virus": "Yellow mosaic virus",
    "red rot": "Red rot",
    "rust": "Rust"
}

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

# Merge external CSV resource dictionaries if available
STATE_MAPPING.update(load_csv_mapping("states.csv"))
CROP_MAPPING.update(load_csv_mapping("crops.csv"))
STAGE_MAPPING.update(load_csv_mapping("growth_stages.csv", val_col="standard_stage"))
PEST_DISEASE_MAPPING.update(load_csv_mapping("pests.csv"))
PEST_DISEASE_MAPPING.update(load_csv_mapping("diseases.csv"))

class Normalizer:
    """Utility class to normalize agricultural entities and parse report dates."""

    @staticmethod
    def normalize_state(state: Optional[str]) -> str:
        if not state or not isinstance(state, str):
            return "All India"
        s = state.lower().strip()
        if not s or s in ["null", "none", "n/a", "na", "-", "unknown"]:
            return "All India"
        
        # 1. Exact match in STATE_MAPPING
        if s in STATE_MAPPING:
            return STATE_MAPPING[s]

        # 2. Check if any valid state name is contained within the string (e.g. "Groundnut In Andhra Pradesh Has 20% Harvested")
        for key, val in STATE_MAPPING.items():
            if len(key) >= 4 and re.search(rf"\b{re.escape(key)}\b", s):
                return val

        # 3. Reject raw markdown tables, headers, and long sentence noise
        if "|" in state or "---" in state or len(state) > 30 or any(kw in s for kw in ["lakh ha", "sl. no", "area coverage", "harvested", "sown", "table", "annexure"]):
            return "All India"

        return state.title().strip()

    @staticmethod
    def normalize_crop(crop: Optional[str]) -> str:
        if not crop or len(crop.strip()) < 2:
            return "Unknown"
        c = crop.lower().strip()
        if c in CROP_MAPPING:
            return CROP_MAPPING[c]
        # Search word boundaries for mapped crop terms
        for k, v in CROP_MAPPING.items():
            if re.search(rf"\b{re.escape(k)}\b", c):
                return v
        return "Unknown"

    @staticmethod
    def normalize_stage(stage: Optional[str]) -> Optional[str]:
        if not stage or stage.strip() in ["null", "None", ""]:
            return None
        s = stage.lower().strip()
        if s in STAGE_MAPPING:
            return STAGE_MAPPING[s]
        for key, val in STAGE_MAPPING.items():
            if key in s:
                return val
        return stage.title().strip()

    @staticmethod
    def normalize_pest_disease(pest_or_disease: Optional[str]) -> Optional[str]:
        if not pest_or_disease or not isinstance(pest_or_disease, str):
            return None
        
        pd_str = pest_or_disease.strip()
        if not pd_str or pd_str.lower() in ["null", "none", "nil", "n/a", "na", "none reported", "absent", "normal", "unknown", "-", "--"]:
            return None

        # Reject raw markdown tables, headers, and report table columns
        pd_lower_raw = pd_str.lower()
        if "|" in pd_str or "---" in pd_str or any(kw in pd_lower_raw for kw in [
            "sowing progress", "area coverage", "lakh ha", "sl. no", "sl.no", "normal area",
            "target area", "coverage over", "difference in", "table 1", "table 2", "annexure", "section"
        ]):
            return None

        # Remove bullet prefixes e.g. "A. ", "B. ", "(a) ", "(1) ", "1. "
        pd_clean = re.sub(r"^(?:[a-zA-Z0-9][\.\)]|\([a-zA-Z0-9]+\))\s*", "", pd_str).strip()
        # Remove trailing/leading non-word characters
        pd_clean = re.sub(r"^[^\w]+|[^\w]+$", "", pd_clean).strip()
        pd_lower = pd_clean.lower()

        # Reject generic nonsense tokens like "A", "B", "C", "Pest A", "Pest B", "Pest", "Disease"
        if len(pd_clean) <= 2 and pd_lower not in ["bph", "blb", "ymv"]:
            return None
            
        if pd_lower in ["pest", "pests", "disease", "diseases", "pest a", "pest b", "pest c", "pest 1", "pest 2", "pest/disease"]:
            return None

        # Check in mapping dictionary
        if pd_lower in PEST_DISEASE_MAPPING:
            return PEST_DISEASE_MAPPING[pd_lower]
            
        for key, val in PEST_DISEASE_MAPPING.items():
            if key in pd_lower:
                return val
        
        # We trust the LLM to provide biological names if it survived the noise filters above.
        # But we must strictly reject full sentences, weather noise, and non-biological text.
        if len(pd_clean) > 40 or len(pd_clean.split()) > 5:
            return None
            
        reject_words = {"has", "is", "remained", "likely", "over", "above", "below", "except", "during", "till", "now", "are", "to", "be", "weather", "temperature", "probability", "intensity", "overall"}
        if any(w in pd_lower.split() for w in reject_words):
            return None

        # Ensure title case for display
        return pd_clean.title()

    @staticmethod
    def clean_display_text(text: Optional[str]) -> str:
        """
        Strip Docling/markdown artifacts that leak into evidence sentences and cause
        broken rendering downstream (e.g. Streamlit interpreting a leading '#' as a
        giant header, or stray table pipes breaking layout).
        This only removes formatting characters -- it never alters the wording of the
        evidence, so document-grounding (evidence == original sentence) is preserved.
        """
        if not text or not isinstance(text, str):
            return ""
        t = text.strip()
        # Strip leading markdown header hashes ('#', '##', '###', ...) on any line
        t = re.sub(r"(?m)^\s*#{1,6}\s*", "", t)
        # Collapse stray markdown table pipes that survive chunking into narrative text
        t = re.sub(r"\s*\|\s*", " ", t)
        # Docling sometimes emits multi-space padding from table-cell extraction
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    @staticmethod
    def parse_date_and_week(source_name: str, doc_text: Optional[str] = None) -> Tuple[str, int]:
        """
        Extract ISO report date (YYYY-MM-DD) and ISO week number.
        Checks filename pattern (e.g., 22.06.2026 or 22-06-2026 or 2026-06-22)
        and document header text.
        """
        # 1. Regex on filename DD.MM.YYYY or DD-MM-YYYY
        match = re.search(r"(\d{2})[.-](\d{2})[.-](\d{4})", source_name)
        if match:
            day, month, year = match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime("%Y-%m-%d"), dt.isocalendar()[1]
            except ValueError:
                pass

        # ISO format in filename YYYY-MM-DD
        iso_match = re.search(r"(\d{4})[.-](\d{2})[.-](\d{2})", source_name)
        if iso_match:
            year, month, day = iso_match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime("%Y-%m-%d"), dt.isocalendar()[1]
            except ValueError:
                pass

        # 2. Regex on doc text if provided e.g. "as on 22.06.2026" or "22 June 2026"
        if doc_text:
            text_match = re.search(r"(?:as on|held on|dated)\s+(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})", doc_text, re.IGNORECASE)
            if text_match:
                day, month, year = text_match.groups()
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime("%Y-%m-%d"), dt.isocalendar()[1]
                except ValueError:
                    pass

            text_word_match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", doc_text)
            if text_word_match:
                day, month_str, year = text_word_match.groups()
                m_int = MONTH_MAP.get(month_str.lower())
                if m_int:
                    try:
                        dt = datetime(int(year), m_int, int(day))
                        return dt.strftime("%Y-%m-%d"), dt.isocalendar()[1]
                    except ValueError:
                        pass

        # Default fallback
        dt = datetime.now()
        return dt.strftime("%Y-%m-%d"), dt.isocalendar()[1]

if __name__ == "__main__":
    print(Normalizer.normalize_state("karnataka"))
    print(Normalizer.normalize_crop("Maize"))
    print(Normalizer.normalize_stage("vegetative stage"))
    print(Normalizer.normalize_pest_disease("Downy mildew"))
    print(Normalizer.parse_date_and_week("Minutes of the meeting of CWWG as on 22.06.2026.pdf"))