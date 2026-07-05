from pathlib import Path
from Crop_Weather_Watch.rag_pipeline.extractors import ImageExtractor
pdf_path = Path(r'c:\Web scraping\Crop_Weather_Watch\data\pdfs\Minutes of the meeting of CWWG as on 22.06.2026.pdf')
extractor = ImageExtractor(output_dir=Path(r'c:\Web scraping\Crop_Weather_Watch\data'))
result = extractor.extract(pdf_path, 'debug_week')
print(result)
