"""
Screen Capture Engine
Captures the screen at configurable FPS, detects changes via perceptual hashing,
compresses frames to JPEG, and queues them for consumption.
"""

import asyncio
import base64
import io
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import imagehash
import mss
import mss.tools
from PIL import Image, ImageFilter

from config import agent_config as config

logger = logging.getLogger(__name__)


@dataclass
class Frame:
    """A single captured frame with metadata."""
    image_b64: str          # base64-encoded JPEG
    timestamp: float        # capture time
    width: int
    height: int
    frame_number: int
    changed: bool = True    # whether this frame differs from the previous


class ScreenCapture:
    """
    Continuous screen capture with intelligent change detection.

    Usage:
        capture = ScreenCapture()
        await capture.start()

        # Get latest frame
        frame = capture.latest_frame

        # Get frame as base64 for Claude API
        b64 = capture.get_frame_b64()

        await capture.stop()
    """

    def __init__(self):
        self._running = False
        self._paused = False
        self._frame_number = 0
        self._last_hash: Optional[imagehash.ImageHash] = None
        self._latest_frame: Optional[Frame] = None
        self._frame_queue: asyncio.Queue = asyncio.Queue(maxsize=30)
        self._task: Optional[asyncio.Task] = None
        self._subscribers: list[asyncio.Queue] = []

        # Stats
        self._frames_captured = 0
        self._frames_skipped = 0
        self._capture_times: list[float] = []

    @property
    def latest_frame(self) -> Optional[Frame]:
        return self._latest_frame

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def stats(self) -> dict:
        avg_capture = (
            sum(self._capture_times[-100:]) / len(self._capture_times[-100:])
            if self._capture_times else 0
        )
        return {
            "frames_captured": self._frames_captured,
            "frames_skipped": self._frames_skipped,
            "avg_capture_ms": round(avg_capture * 1000, 1),
            "running": self._running,
            "paused": self._paused,
            "fps": config.capture_fps,
        }

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to receive new frames. Returns a queue that gets new frames pushed to it."""
        q: asyncio.Queue = asyncio.Queue(maxsize=5)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a frame subscriber."""
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def start(self):
        """Start the capture loop."""
        if self._running:
            logger.warning("Capture already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._capture_loop())
        logger.info(
            f"Screen capture started: {config.capture_fps} FPS, "
            f"quality={config.capture_quality}, scale={config.capture_scale}"
        )

    async def stop(self):
        """Stop the capture loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Screen capture stopped")

    def pause(self):
        """Pause capture (still running but not grabbing frames)."""
        self._paused = True
        logger.info("Capture paused")

    def resume(self):
        """Resume capture after pause."""
        self._paused = False
        logger.info("Capture resumed")

    def get_frame_b64(self) -> Optional[str]:
        """Get the latest frame as a base64 JPEG string (for Claude API)."""
        if self._latest_frame:
            return self._latest_frame.image_b64
        return None

    def get_frame_bytes(self) -> Optional[bytes]:
        """Get the latest frame as raw JPEG bytes (for WebSocket streaming)."""
        if self._latest_frame:
            return base64.b64decode(self._latest_frame.image_b64)
        return None

    async def capture_single(self) -> Optional[Frame]:
        """Capture a single frame on demand (bypasses change detection)."""
        return await asyncio.to_thread(self._grab_frame, force=True)

    # ── Internal ───────────────────────────────────────────────────────

    async def _capture_loop(self):
        """Main capture loop running at configured FPS."""
        interval = 1.0 / config.capture_fps

        while self._running:
            try:
                if self._paused:
                    await asyncio.sleep(0.1)
                    continue

                start = time.monotonic()
                frame = await asyncio.to_thread(self._grab_frame)
                elapsed = time.monotonic() - start
                self._capture_times.append(elapsed)

                if frame and frame.changed:
                    self._latest_frame = frame
                    self._frames_captured += 1

                    # Push to all subscribers (non-blocking)
                    for sub in self._subscribers:
                        try:
                            sub.put_nowait(frame)
                        except asyncio.QueueFull:
                            # Drop oldest frame for slow consumers
                            try:
                                sub.get_nowait()
                                sub.put_nowait(frame)
                            except (asyncio.QueueEmpty, asyncio.QueueFull):
                                pass
                else:
                    self._frames_skipped += 1

                # Sleep for remaining interval time
                sleep_time = max(0, interval - elapsed)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Capture error: {e}", exc_info=True)
                await asyncio.sleep(1)

    def _grab_frame(self, force: bool = False) -> Optional[Frame]:
        """Grab a screenshot, detect changes, and return a Frame."""
        try:
            # Create a fresh mss instance each call. This is required on Windows
            # because mss uses thread-local GDI handles, and this method runs
            # in a thread pool via asyncio.to_thread(). The 'with' statement
            # ensures handles are properly released after each grab.
            with mss.mss() as sct:
                # Grab the primary monitor
                monitor = sct.monitors[1]  # [0] is "all monitors combined"
                sct_img = sct.grab(monitor)

                # Convert to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Scale down
            if config.capture_scale < 1.0:
                new_w = int(img.width * config.capture_scale)
                new_h = int(img.height * config.capture_scale)
                # Clamp to max dimensions
                new_w = min(new_w, config.max_frame_width)
                new_h = min(new_h, config.max_frame_height)
                img = img.resize((new_w, new_h), Image.LANCZOS)

            # Apply blur regions for privacy
            img = self._apply_blur_regions(img)

            # Change detection via perceptual hash
            current_hash = imagehash.phash(img, hash_size=16)
            changed = force

            if self._last_hash is not None:
                # Hash difference: 0 = identical, higher = more different
                diff = self._last_hash - current_hash
                # Threshold: hash_size=16 means 256 bits, so diff of ~5+ is meaningful
                changed = changed or (diff > 5)
            else:
                changed = True  # First frame is always "changed"

            if not changed and not force:
                return Frame(
                    image_b64="",
                    timestamp=time.time(),
                    width=img.width,
                    height=img.height,
                    frame_number=self._frame_number,
                    changed=False,
                )

            self._last_hash = current_hash

            # Compress to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=config.capture_quality, optimize=True)
            jpeg_bytes = buffer.getvalue()
            b64_str = base64.b64encode(jpeg_bytes).decode("utf-8")

            self._frame_number += 1

            return Frame(
                image_b64=b64_str,
                timestamp=time.time(),
                width=img.width,
                height=img.height,
                frame_number=self._frame_number,
                changed=True,
            )

        except Exception as e:
            logger.error(f"Frame grab error: {e}", exc_info=True)
            return None

    def _apply_blur_regions(self, img: Image.Image) -> Image.Image:
        """Apply gaussian blur to configured privacy regions."""
        if not config.blur_regions:
            return img

        for region in config.blur_regions:
            x, y, w, h = region
            # Scale coordinates
            sx = int(x * config.capture_scale)
            sy = int(y * config.capture_scale)
            sw = int(w * config.capture_scale)
            sh = int(h * config.capture_scale)

            # Crop, blur, paste back
            box = (sx, sy, sx + sw, sy + sh)
            cropped = img.crop(box)
            blurred = cropped.filter(ImageFilter.GaussianBlur(radius=20))
            img.paste(blurred, box)

        return img
