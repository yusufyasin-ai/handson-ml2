"""
Golf Putting Gradient Analysis API
FastAPI backend — accepts an image, returns gradient vector field + Claude analysis.
"""

import io
import os
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from dotenv import load_dotenv

from gradient_detection import detect_green_mask, combine_gradient_signals
from claude_analysis import analyse_image_with_claude

load_dotenv()

app = FastAPI(title="Golf Putting Gradient API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_IMAGE_DIM = 1280  # Resize large images to keep processing fast
SUPPORTED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


def load_and_normalise(file_bytes: bytes, content_type: str) -> tuple[np.ndarray, str]:
    """Load image bytes → BGR numpy array, resize if needed, return normalised media type."""
    pil = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    w, h = pil.size
    if max(w, h) > MAX_IMAGE_DIM:
        scale = MAX_IMAGE_DIM / max(w, h)
        pil = pil.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    # Normalise media type for Claude
    if content_type in ("image/heic", "image/heif"):
        media_type = "image/jpeg"
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=92)
        file_bytes = buf.getvalue()
    else:
        media_type = content_type if content_type in {"image/jpeg", "image/png", "image/webp", "image/gif"} else "image/jpeg"
        buf = io.BytesIO()
        fmt = "JPEG" if media_type == "image/jpeg" else "PNG"
        pil.save(buf, format=fmt, quality=92)
        file_bytes = buf.getvalue()

    return bgr, media_type, file_bytes


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyse")
async def analyse(file: UploadFile = File(...)):
    if file.content_type not in SUPPORTED_TYPES and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail=f"Unsupported media type: {file.content_type}")

    raw_bytes = await file.read()
    if len(raw_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 20 MB)")

    try:
        bgr, media_type, normalised_bytes = load_and_normalise(raw_bytes, file.content_type or "image/jpeg")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not decode image: {exc}")

    # --- Computer vision gradient detection ---
    mask = detect_green_mask(bgr)
    cv_result = combine_gradient_signals(bgr, mask)

    # --- Claude Vision semantic analysis ---
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    claude_result = None
    if anthropic_key:
        try:
            claude_result = analyse_image_with_claude(normalised_bytes, media_type)
        except Exception as exc:
            claude_result = {"error": str(exc)}
    else:
        claude_result = {"error": "ANTHROPIC_API_KEY not set — Claude analysis disabled"}

    # --- Merge: overlay Claude zone data onto CV grid points ---
    image_h, image_w = bgr.shape[:2]
    if claude_result and "zones" in claude_result:
        zones = claude_result["zones"]
        zone_w = image_w / 4
        zone_h = image_h / 4
        for pt in cv_result["grid_points"]:
            col = min(int(pt["x"] / zone_w), 3)
            row = min(int(pt["y"] / zone_h), 3)
            zone = next((z for z in zones if z["row"] == row and z["col"] == col), None)
            if zone:
                pt["claude_direction_deg"] = zone["slope_direction_deg"]
                pt["claude_severity"] = zone["slope_severity"]
                pt["claude_confidence"] = zone["confidence"]

    return {
        "cv_analysis": cv_result,
        "claude_analysis": claude_result,
        "image_dimensions": {"width": image_w, "height": image_h},
    }
