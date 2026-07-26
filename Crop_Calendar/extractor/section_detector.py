import re
from typing import List, Dict, Any

# Irrelevant section headings to drop
EXCLUDED_SECTION_HEADERS = [
    "GENERAL", "GENERAL SUMMARY", "SALIENT FEATURES", "EXECUTIVE SUMMARY",
    "WEATHER UPDATE", "WEATHER SUMMARY", "RAINFALL", "RAINFALL DISTRIBUTION",
    "RAINFALL FORECAST", "TEMPERATURE", "ADVANCE OF SOUTHWEST MONSOON",
    "WATER RESERVOIR STATUS", "RESERVOIR STORAGE", "GROUNDWATER LEVELS",
    "SOIL MOISTURE", "FERTILIZER POSITION", "FERTILIZERS", "INPUTS SITUATION",
    "MANDI WHOLESALE PRICES", "COMMODITIES BELOW MSP", "ADMINISTRATIVE NOTES",
    "ATTENDANCE", "KEY INSIGHTS", "PROGRESS OF AREA COVERAGE"
]

# Regex patterns for noisy header/footer text and docling watermark artifacts
NOISE_PATTERNS = [
    r"Government of India",
    r"Ministry of Agriculture",
    r"Department of Agriculture",
    r"Crop Weather Watch Group",
    r"Weekly report/\s*Minutes",
    r"Page\s+\d+\s+of\s+\d+",
    r"㄰⸲ㄮ㐰⸳",
    r"㌰ⵊ啎ⴲ〲㘠\S*",
    r"^<!-- image -->$",
    r"^\s*\|\s*Commodities\s*\|\s*MSP\s*" # Mandi price table header
]

class SectionDetector:
    """Detects and removes irrelevant sections, footers, headers, and noise from CWWG documents."""

    def __init__(self):
        self.noise_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in NOISE_PATTERNS]

    def _is_noise(self, text: str) -> bool:
        """Check if a line/paragraph is repeating header/footer/watermark noise."""
        if not text or len(text.strip()) < 3:
            return True
        for reg in self.noise_regexes:
            if reg.search(text):
                return True
        return False

    def _is_excluded_section(self, header_title: str) -> bool:
        """Check if heading belongs to an excluded non-crop section."""
        title_upper = header_title.upper()
        for excl in EXCLUDED_SECTION_HEADERS:
            if excl in title_upper:
                return True
        return False

    def filter_document(self, doc_dict: dict, markdown_content: str = "") -> List[Dict[str, Any]]:
        """
        Filters doc_dict / markdown into clean, relevant agricultural section blocks.
        Returns a list of dict objects: {'heading': str, 'text': str, 'page_number': int}
        """
        filtered_blocks = []
        current_heading = "General Observation"
        skip_current_section = False

        # If markdown_content is available, split into sections by headers (# or ##)
        if markdown_content:
            lines = markdown_content.splitlines()
            section_buffer = []
            section_page = 1

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                # Check for page numbers in docling markdown comments e.g. <!-- page 2 -->
                page_match = re.search(r"<!--\s*page\s*(\d+)\s*-->", stripped, re.IGNORECASE)
                if page_match:
                    section_page = int(page_match.group(1))
                    continue

                # Heading detection
                if stripped.startswith("#"):
                    # Save previous section if not skipped
                    if section_buffer and not skip_current_section:
                        full_text = "\n".join(section_buffer).strip()
                        if full_text and not self._is_noise(full_text):
                            filtered_blocks.append({
                                "heading": current_heading,
                                "text": full_text,
                                "page_number": section_page
                            })
                    
                    # Reset for new section
                    header_text = re.sub(r"^#+\s*", "", stripped).strip()
                    current_heading = header_text
                    skip_current_section = self._is_excluded_section(header_text)
                    section_buffer = []
                    continue

                # Filter noise lines
                if self._is_noise(stripped):
                    continue

                if not skip_current_section:
                    section_buffer.append(stripped)

            # Flush last section
            if section_buffer and not skip_current_section:
                full_text = "\n".join(section_buffer).strip()
                if full_text and not self._is_noise(full_text):
                    filtered_blocks.append({
                        "heading": current_heading,
                        "text": full_text,
                        "page_number": section_page
                    })

        return filtered_blocks

if __name__ == "__main__":
    detector = SectionDetector()
    sample_md = """
    ## 1. Weather Update:
    Maximum temperature is likely to be above normal in Madhya Maharashtra.
    ## 4. Pests & Diseases:
    Intensity of pests and diseases at some fields has been reported to be above Economic Threshold Level for Maize -vegetative stage (Downy mildew) in Karnataka.
    """
    blocks = detector.filter_document({}, sample_md)
    print("Filtered blocks:", blocks)
