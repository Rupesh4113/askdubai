"""
CivicResolve AI - Advanced Image Preprocessing Engine
Implements EXIF orientation normalization, automatic deskewing,
perspective distortion correction, shadow removal, and contrast enhancement.
"""
import io
import math
import numpy as np
from PIL import Image, ImageOps
from typing import Tuple, Dict, Any, Optional

try:
    import cv2
except ImportError:
    cv2 = None


def preprocess_image_bytes(image_bytes: bytes) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Loads raw image bytes, applies complete preprocessing pipeline:
    1. EXIF orientation correction
    2. Boundary / perspective quadrilateral detection
    3. Deskew and rotation
    4. Illumination / shadow normalization
    5. Adaptive contrast enhancement (CLAHE)
    Returns (processed_bgr_image, metadata).
    """
    # 1. Load image with Pillow to handle EXIF orientation properly
    pil_img = Image.open(io.BytesIO(image_bytes))
    pil_img = ImageOps.exif_transpose(pil_img)
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    
    # Convert to OpenCV BGR format
    np_img = np.array(pil_img)
    if cv2 is not None:
        bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
    else:
        bgr = np_img[:, :, ::-1]

    meta = {
        "original_width": pil_img.width,
        "original_height": pil_img.height,
        "rotation_angle": 0.0,
        "perspective_corrected": False,
        "shadow_removal_applied": False,
        "clahe_applied": False,
        "document_bbox": [0, 0, pil_img.width, pil_img.height]
    }

    if cv2 is None:
        return bgr, meta

    # 2. Correct perspective distortion if a clear document quadrilateral is found
    warped, quad_detected, bbox = correct_perspective_distortion(bgr)
    if quad_detected:
        bgr = warped
        meta["perspective_corrected"] = True
        meta["document_bbox"] = bbox

    # 3. Deskew orientation
    deskewed, angle = deskew_image(bgr)
    if abs(angle) > 0.4:
        bgr = deskewed
        meta["rotation_angle"] = round(angle, 2)

    # 4. Remove shadows and normalize illumination
    enhanced, shadow_applied = remove_shadows_and_enhance(bgr)
    meta["shadow_removal_applied"] = shadow_applied
    meta["clahe_applied"] = True

    return enhanced, meta


def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """Detects text skew angle using Hough line transform and rotates accordingly."""
    if cv2 is None or image is None or image.size == 0:
        return image, 0.0

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=image.shape[1] // 5, maxLineGap=20)

    if lines is None or len(lines) == 0:
        return image, 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            continue
        rad = math.atan2(y2 - y1, x2 - x1)
        deg = math.degrees(rad)
        # Keep horizontal-ish lines within [-45, 45] degrees
        if -45 < deg < 45:
            angles.append(deg)

    if not angles:
        return image, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return image, median_angle

    # Rotate image around center
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, median_angle


def correct_perspective_distortion(image: np.ndarray) -> Tuple[np.ndarray, bool, list]:
    """
    Detects four corners of the largest document contour and applies a 4-point perspective warp.
    Falls back to original image if no confident 4-corner polygon is found.
    """
    h, w = image.shape[:2]
    default_bbox = [0, 0, w, h]

    if cv2 is None:
        return image, False, default_bbox

    # Downscale for fast contour detection
    max_dim = 1000
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        resized = cv2.resize(image, (int(w * scale), int(h * scale)))
    else:
        resized = image.copy()

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # Dilate edges to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edged, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    target_quad = None
    target_bbox = default_bbox
    img_area = (w * scale) * (h * scale)

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        area = cv2.contourArea(approx)

        # Require contour to cover at least 25% of image and have 4 points
        if len(approx) == 4 and area > (0.25 * img_area):
            target_quad = approx.reshape(4, 2) / scale
            bx, by, bw, bh = cv2.boundingRect(c)
            target_bbox = [int(bx / scale), int(by / scale), int(bw / scale), int(bh / scale)]
            break

    if target_quad is None:
        return image, False, default_bbox

    warped = four_point_transform(image, target_quad)
    return warped, True, target_bbox


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Applies four-point perspective warp to quadrilateral points."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]], dtype="float32")

    transform_matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, transform_matrix, (max_width, max_height))
    return warped


def order_points(pts: np.ndarray) -> np.ndarray:
    """Orders coordinates: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def remove_shadows_and_enhance(image: np.ndarray) -> Tuple[np.ndarray, bool]:
    """
    Removes uneven lighting and shadows using morphological background division,
    followed by CLAHE contrast equalization on luminance.
    """
    if cv2 is None:
        return image, False

    # Convert to LAB color space to process luminance channel independently
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Estimate background illumination with large morphological dilation
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    dilated = cv2.morphologyEx(l, cv2.MORPH_DILATE, kernel)
    bg = cv2.medianBlur(dilated, 21)

    # Divide luminance by background to normalize lighting
    diff = 255 - cv2.absdiff(l, bg)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)

    # Apply CLAHE to sharpen text contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(norm)

    merged = cv2.merge((enhanced_l, a, b))
    result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return result, True
