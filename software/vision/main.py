"""
Vision service — MJPEG video stream and snapshot via OpenCV.

Endpoints
---------
GET /stream/video  — multipart/x-mixed-replace MJPEG stream
GET /snapshot      — single JPEG frame
GET /              — health check

Environment variables
---------------------
CAMERA_INDEX : int  — OpenCV device index (default 0)
JPEG_QUALITY : int  — JPEG compression quality 1-100 (default 80)
"""

import asyncio
import io
import logging
import os
import time
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("hexapod.vision")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s — %(message)s")

_CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
_JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))

# ── Try to import OpenCV ───────────────────────────────────────────────────────
try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    logger.warning("opencv-python not available — vision service in simulation mode.")

app = FastAPI(title="Hexapod Vision", version="0.1.0")

# Shared camera handle
_cap = None


def _get_camera():
    global _cap
    if _cap is None and _CV2_AVAILABLE:
        _cap = cv2.VideoCapture(_CAMERA_INDEX)
        if not _cap.isOpened():
            logger.error("Failed to open camera index %d", _CAMERA_INDEX)
            _cap = None
    return _cap


def _read_jpeg_frame() -> bytes:
    """Capture one frame and encode as JPEG bytes."""
    cap = _get_camera()
    if cap is None or not _CV2_AVAILABLE:
        # Return a minimal 1×1 grey JPEG placeholder
        try:
            import numpy as np
            frame = np.full((240, 320, 3), 128, dtype="uint8")
            cv2.putText(frame, "No camera", (80, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
            return buf.tobytes()
        except Exception:
            return b""

    ret, frame = cap.read()
    if not ret:
        return b""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
    return buf.tobytes()


async def _mjpeg_generator() -> AsyncGenerator[bytes, None]:
    """Async generator yielding MJPEG multipart frames."""
    boundary = b"--frame"
    while True:
        frame_bytes = await asyncio.get_event_loop().run_in_executor(None, _read_jpeg_frame)
        if frame_bytes:
            yield (
                boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes + b"\r\n"
            )
        await asyncio.sleep(1 / 30)  # ~30 fps


@app.get("/")
async def health():
    return {"status": "ok", "service": "hexapod-vision", "camera": _CV2_AVAILABLE}


@app.get("/stream/video")
async def video_stream():
    """MJPEG streaming endpoint."""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/snapshot")
async def snapshot():
    """Return a single JPEG snapshot."""
    frame_bytes = await asyncio.get_event_loop().run_in_executor(None, _read_jpeg_frame)
    if not frame_bytes:
        return JSONResponse(status_code=503, content={"error": "No frame available"})
    return StreamingResponse(io.BytesIO(frame_bytes), media_type="image/jpeg")
