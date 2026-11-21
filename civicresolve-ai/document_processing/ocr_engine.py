"""
CivicResolve AI - OCR and Layout Extraction Engine
Powered by RapidOCR (PaddleOCR ONNX) and PyMuPDF text fusion.
Provides bounding box coordinates, per-line token clustering, and confidence scoring.
"""
import io
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Tuple, Optional

_RAPID_OCR_INSTANCE = None


def get_ocr_engine():
    """Lazy-loads and caches RapidOCR engine instance."""
    global _RAPID_OCR_INSTANCE
    if _RAPID_OCR_INSTANCE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_OCR_INSTANCE = RapidOCR()
        except Exception as e:
            print(f"[OCREngine] Warning: RapidOCR failed to initialize: {e}")
            _RAPID_OCR_INSTANCE = None
    return _RAPID_OCR_INSTANCE


def run_ocr_on_image(image_input: Any, page_number: int = 1) -> Dict[str, Any]:
    """
    Executes layout-aware OCR on a single image (numpy ndarray, PIL Image, or bytes).
    Returns extracted text, structured lines, token bounding boxes, and confidence statistics.
    """
    # Normalize input to numpy array
    if isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        np_img = np.array(pil_img)
    elif isinstance(image_input, Image.Image):
        np_img = np.array(image_input.convert("RGB"))
    elif isinstance(image_input, np.ndarray):
        np_img = image_input
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    img_h, img_w = np_img.shape[:2]
    engine = get_ocr_engine()

    tokens = []
    lines = []
    raw_text_parts = []
    total_conf = 0.0
    uncertain_tokens = []

    if engine is not None:
        try:
            results, elapse = engine(np_img)
            if results:
                for item in results:
                    # item format: [box_points, text, confidence]
                    # box_points is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    pts = item[0]
                    text = item[1].strip()
                    conf = float(item[2])

                    if not text:
                        continue

                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

                    token_dict = {
                        "text": text,
                        "bbox": [round(x0, 2), round(y0, 2), round(x1, y1, 2), round(y1, 2)],
                        "polygon": pts,
                        "confidence": round(conf, 3),
                        "page_number": page_number
                    }
                    tokens.append(token_dict)
                    raw_text_parts.append(text)
                    total_conf += conf

                    if conf < 0.70:
                        uncertain_tokens.append(token_dict)

        except Exception as e:
            print(f"[OCREngine] RapidOCR execution error: {e}")

    # Fallback to pytesseract if RapidOCR returned nothing or is unavailable
    if not tokens:
        tokens, raw_text_parts, total_conf, uncertain_tokens = _fallback_tesseract_ocr(np_img, page_number)

    avg_confidence = round(total_conf / max(1, len(tokens)), 3) if tokens else 0.0

    # Group tokens into lines based on vertical proximity
    clustered_lines = _cluster_tokens_into_lines(tokens)

    full_text = "\n".join([line["text"] for line in clustered_lines]) if clustered_lines else " ".join(raw_text_parts)

    return {
        "page_number": page_number,
        "width": img_w,
        "height": img_h,
        "full_text": full_text,
        "lines": clustered_lines,
        "tokens": tokens,
        "token_count": len(tokens),
        "mean_confidence": avg_confidence,
        "uncertain_tokens_count": len(uncertain_tokens),
        "uncertain_tokens": uncertain_tokens[:20]  # Cap preview
    }


def _cluster_tokens_into_lines(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups OCR tokens into reading order lines using bounding box Y-coordinates."""
    if not tokens:
        return []

    # Sort tokens top-to-bottom, then left-to-right
    sorted_tokens = sorted(tokens, key=lambda t: (t["bbox"][1], t["bbox"][0]))

    lines = []
    current_line = []
    current_y_center = None

    for t in sorted_tokens:
        box = t["bbox"]
        y_center = (box[1] + box[3]) / 2.0
        box_height = max(10, box[3] - box[1])

        if current_y_center is None:
            current_line.append(t)
            current_y_center = y_center
        else:
            # If vertical distance is within 60% of box height, group on same line
            if abs(y_center - current_y_center) < (box_height * 0.65):
                current_line.append(t)
            else:
                # Sort line tokens left-to-right
                current_line.sort(key=lambda tok: tok["bbox"][0])
                line_text = " ".join([tok["text"] for tok in current_line])
                lx0 = min(tok["bbox"][0] for tok in current_line)
                ly0 = min(tok["bbox"][1] for tok in current_line)
                lx1 = max(tok["bbox"][2] for tok in current_line)
                ly1 = max(tok["bbox"][3] for tok in current_line)
                lines.append({
                    "text": line_text,
                    "bbox": [round(lx0, 2), round(ly0, 2), round(lx1, 2), round(ly1, 2)],
                    "tokens": current_line
                })
                current_line = [t]
                current_y_center = y_center

    if current_line:
        current_line.sort(key=lambda tok: tok["bbox"][0])
        line_text = " ".join([tok["text"] for tok in current_line])
        lx0 = min(tok["bbox"][0] for tok in current_line)
        ly0 = min(tok["bbox"][1] for tok in current_line)
        lx1 = max(tok["bbox"][2] for tok in current_line)
        ly1 = max(tok["bbox"][3] for tok in current_line)
        lines.append({
            "text": line_text,
            "bbox": [round(lx0, 2), round(ly0, 2), round(lx1, 2), round(ly1, 2)],
            "tokens": current_line
        })

    return lines


def _fallback_tesseract_ocr(np_img: np.ndarray, page_number: int):
    """Fallback if RapidOCR is absent and pytesseract is available."""
    tokens = []
    raw_text = []
    total_conf = 0.0
    uncertain = []
    try:
        import pytesseract
        pil_img = Image.fromarray(np_img)
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            txt = data['text'][i].strip()
            conf = float(data['conf'][i])
            if txt and conf > 0:
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                t_dict = {
                    "text": txt,
                    "bbox": [float(x), float(y), float(x + w), float(y + h)],
                    "confidence": round(conf / 100.0, 3),
                    "page_number": page_number
                }
                tokens.append(t_dict)
                raw_text.append(txt)
                total_conf += conf / 100.0
                if conf < 65:
                    uncertain.append(t_dict)
    except Exception:
        pass
    return tokens, raw_text, total_conf, uncertain
