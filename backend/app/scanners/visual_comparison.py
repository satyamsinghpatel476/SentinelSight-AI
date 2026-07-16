from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import imagehash
from PIL import Image, ImageChops

from app.core.config import Settings
from app.scanners.screenshot_capture import screenshot_path_for_filename


@dataclass(frozen=True)
class VisualComparisonResult:
    visual_change_percent: float
    perceptual_hash_distance: int
    difference_image_filename: str
    difference_image_content_type: str
    visual_change_level: str


def compare_screenshots(
    baseline_filename: str,
    current_filename: str,
    settings: Settings,
) -> VisualComparisonResult:
    """Create a simple highlighted screenshot diff and change percentage."""

    baseline_path = screenshot_path_for_filename(settings, baseline_filename)
    current_path = screenshot_path_for_filename(settings, current_filename)
    output_dir = difference_storage_dir(settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.png"
    output_path = output_dir / filename

    with Image.open(baseline_path) as baseline_image:
        baseline = baseline_image.convert("RGB")
    with Image.open(current_path) as current_image:
        current = current_image.convert("RGB")

    width = max(baseline.width, current.width)
    height = max(baseline.height, current.height)
    baseline_padded = pad_to_size(baseline, width, height)
    current_padded = pad_to_size(current, width, height)

    hash_distance = imagehash.phash(baseline_padded) - imagehash.phash(current_padded)
    diff = ImageChops.difference(baseline_padded, current_padded).convert("L")
    threshold = 32
    changed_mask = diff.point(lambda value: 255 if value > threshold else 0)
    changed_pixels = sum(1 for value in changed_mask.getdata() if value)
    total_pixels = width * height
    change_percent = (
        round((changed_pixels / total_pixels) * 100, 2) if total_pixels else 0.0
    )

    overlay = current_padded.copy()
    highlight = Image.new("RGB", (width, height), (239, 68, 68))
    overlay.paste(highlight, mask=changed_mask)
    blended = Image.blend(current_padded, overlay, 0.45)
    blended.save(output_path, format="PNG")

    return VisualComparisonResult(
        visual_change_percent=change_percent,
        perceptual_hash_distance=int(hash_distance),
        difference_image_filename=filename,
        difference_image_content_type="image/png",
        visual_change_level=classify_visual_change(change_percent, settings),
    )


def pad_to_size(image: Image.Image, width: int, height: int) -> Image.Image:
    if image.width == width and image.height == height:
        return image
    padded = Image.new("RGB", (width, height), (255, 255, 255))
    padded.paste(image, (0, 0))
    return padded


def classify_visual_change(change_percent: float, settings: Settings) -> str:
    if change_percent >= settings.visual_major_threshold:
        return "major"
    if change_percent >= settings.visual_moderate_threshold:
        return "moderate"
    if change_percent >= settings.visual_minor_threshold:
        return "minor"
    return "none"


def difference_storage_dir(settings: Settings) -> Path:
    return Path(settings.evidence_storage_dir).resolve() / "differences"


def difference_path_for_filename(settings: Settings, filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("Invalid difference image filename")
    storage_root = difference_storage_dir(settings).resolve()
    resolved = (storage_root / filename).resolve()
    if storage_root not in resolved.parents and resolved != storage_root:
        raise ValueError("Invalid difference image path")
    return resolved
