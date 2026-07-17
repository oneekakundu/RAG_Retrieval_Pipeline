import re
from datetime import datetime
from pathlib import Path

# Mapping dictionaries for normalization
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
    "ladakh": "Ladakh"
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
    "soyabean": "Soybean",
    "soybean": "Soybean",
    "groundnut": "Groundnut",
    "mustard": "Mustard",
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
    "sunflower": "Sunflower"
}

STAGE_MAPPING = {
    "sowing": "Sowing",
    "planting": "Sowing",
    "germination": "Germination",
    "seedling": "Seedling",
    "vegetative": "Vegetative",
    "tillering": "Tillering",
    "panicle": "Panicle Initiation",
    "flowering": "Flowering",
    "pod formation": "Pod Formation",
    "grain filling": "Grain Filling",
    "maturity": "Maturity",
    "harvesting": "Harvesting",
    "harvest": "Harvesting"
}

class Normalizer:
    """Utility class to normalize and clean extracted agricultural entities."""

    @staticmethod
    def normalize_state(state: str) -> str:
        """Standardize Indian state names."""
        if not state:
            return "All India"
        s = state.lower().strip()
        return STATE_MAPPING.get(s, state.title().strip())

    @staticmethod
    def normalize_crop(crop: str) -> str:
        """Standardize crop names."""
        if not crop:
            return "Unknown"
        c = crop.lower().strip()
        return CROP_MAPPING.get(c, crop.title().strip())

    @staticmethod
    def normalize_stage(stage: str) -> str:
        """Standardize crop growth stages."""
        if not stage:
            return "Active Growth"
        
        s = stage.lower().strip()
        # Direct lookup
        if s in STAGE_MAPPING:
            return STAGE_MAPPING[s]
            
        # Substring matching
        for key, val in STAGE_MAPPING.items():
            if key in s:
                return val
        return stage.title().strip()

    @staticmethod
    def normalize_pest_disease(pest_or_disease: str) -> str:
        """Clean pest and disease names by removing noise."""
        if not pest_or_disease:
            return "None Reported"
        name = pest_or_disease.strip()
        # Remove trailing/leading punctuation
        name = re.sub(r"^[^\w]+|[^\w]+$", "", name)
        # Standardize capitalization
        return name.title()

    @staticmethod
    def parse_date_and_week(source_name: str) -> tuple[str, int]:
        """
        Parse standard YYYY-MM-DD date and week number from filenames.
        Example: 'Minutes of the meeting of CWWG as on 08.06.2026.pdf' -> ('2026-06-08', 24)
        """
        # Search for date pattern in filename: DD.MM.YYYY or DD-MM-YYYY
        match = re.search(r"(\d{2})[.-](\d{2})[.-](\d{4})", source_name)
        if match:
            day, month, year = match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                date_str = dt.strftime("%Y-%m-%d")
                week_num = dt.isocalendar()[1]
                return date_str, week_num
            except Exception:
                pass
                
        # Default fallback
        dt = datetime.now()
        return dt.strftime("%Y-%m-%d"), dt.isocalendar()[1]

if __name__ == "__main__":
    print(Normalizer.normalize_state("Orissa"))
    print(Normalizer.normalize_crop("tur"))
    print(Normalizer.normalize_stage("early tillering stage"))
    print(Normalizer.parse_date_and_week("Minutes of the meeting of CWWG as on 08.06.2026.pdf"))
