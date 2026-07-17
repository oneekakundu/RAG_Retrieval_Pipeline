import sys
from pathlib import Path
from gliner import GLiNER

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

class EntityExtractor:
    """Uses GLiNER to perform zero-shot named entity recognition on agricultural text chunks."""

    def __init__(self, model_name: str = None, threshold: float = None):
        self.model_name = model_name or config.GLINER_MODEL
        self.threshold = threshold or config.GLINER_THRESHOLD
        print(f"Loading GLiNER model: {self.model_name}...")
        self.model = GLiNER.from_pretrained(self.model_name)
        print("GLiNER model loaded successfully.")

    def extract_entities(self, text: str) -> dict:
        """
        Predict entities in the text using GLiNER labels.
        Returns a dict mapping label to list of extracted values and metadata.
        """
        if not text.strip():
            return {}

        try:
            predictions = self.model.predict_entities(text, config.GLINER_LABELS, threshold=self.threshold)
        except Exception as e:
            print(f"GLiNER prediction failed: {e}")
            predictions = []

        # Initialize structured results
        extracted = {label: [] for label in config.GLINER_LABELS}
        scores = []

        for pred in predictions:
            label = pred.get("label")
            val = pred.get("text", "").strip()
            score = pred.get("score", 0.0)
            
            if label in extracted and val:
                extracted[label].append({
                    "text": val,
                    "score": float(score),
                    "start": pred.get("start"),
                    "end": pred.get("end")
                })
                scores.append(score)

        # Calculate average confidence
        avg_confidence = sum(scores) / len(scores) if scores else 1.0

        return {
            "entities": extracted,
            "confidence": round(avg_confidence, 4),
            "raw_predictions": predictions
        }

if __name__ == "__main__":
    # Quick standalone test
    test_text = "Maize - vegetative stage - Downy mildew in Karnataka."
    extractor = EntityExtractor()
    result = extractor.extract_entities(test_text)
    print("Entities:", result["entities"])
    print("Confidence:", result["confidence"])
