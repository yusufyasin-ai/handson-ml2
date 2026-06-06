"""
Grass gradient detection using multiple computer vision techniques.

Putting green grass gradient detection is non-trivial because:
- Grass is uniform in color with subtle texture variations
- Slopes manifest as lighting/shadow gradients, grain sheen, and visual undulations
- Standard edge detection finds grass blades, not terrain slope

Approach:
1. Gabor filter bank → grass grain direction (grain runs perpendicular to mowing direction,
   creates a sheen that's lighter when viewed "with the grain")
2. Illuminance gradient → shadow-based depth-from-shading signal
3. Color saturation gradient → subtle moisture/compaction variation correlates with slope
4. Combine signals into a smoothed vector field
"""

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import convolve2d


def detect_green_mask(image_bgr: np.ndarray) -> np.ndarray:
    """Segment the putting green from fringe, rough, sand, and sky."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    # Tight green hue range for closely mown putting surface
    lower = np.array([30, 30, 30])
    upper = np.array([95, 255, 220])
    mask = cv2.inRange(hsv, lower, upper)
    # Remove small noise, fill holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # Keep only the largest contiguous region (the main green surface)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        clean = np.zeros_like(mask)
        cv2.drawContours(clean, [largest], -1, 255, cv2.FILLED)
        return clean
    return mask


def gabor_grain_field(gray: np.ndarray, n_orientations: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply a Gabor filter bank to detect grass grain direction.
    Grass grain appears as periodic parallel lines at the mowing angle.
    The dominant orientation of strong Gabor responses indicates grain direction.
    Returns (angle_map, magnitude_map) in radians and normalised [0,1].
    """
    h, w = gray.shape
    responses = np.zeros((n_orientations, h, w), dtype=np.float32)
    angles = np.linspace(0, np.pi, n_orientations, endpoint=False)

    for i, theta in enumerate(angles):
        # Wavelength ~8-16px covers typical grass blade spacing in a green photo
        kernel = cv2.getGaborKernel(
            ksize=(31, 31), sigma=4.0, theta=theta,
            lambd=10.0, gamma=0.5, psi=0, ktype=cv2.CV_32F
        )
        filtered = cv2.filter2D(gray.astype(np.float32), cv2.CV_32F, kernel)
        responses[i] = np.abs(filtered)

    dominant_idx = np.argmax(responses, axis=0)
    magnitude = np.max(responses, axis=0)
    angle_map = angles[dominant_idx]
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    return angle_map, magnitude


def illuminance_gradient_field(image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute gradient of illuminance channel to detect shading-based slope signal.
    Depth-from-shading: brighter areas face the light source; gradient points uphill.
    Uses the L channel of LAB space which best separates luminance from colour.
    """
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32)
    # Smooth to suppress grass-blade texture noise before computing gradient
    L_smooth = gaussian_filter(L, sigma=8)
    gx = cv2.Sobel(L_smooth, cv2.CV_32F, 1, 0, ksize=7)
    gy = cv2.Sobel(L_smooth, cv2.CV_32F, 0, 1, ksize=7)
    magnitude = np.sqrt(gx**2 + gy**2)
    angle = np.arctan2(gy, gx)
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    return angle, magnitude


def saturation_gradient_field(image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Saturation gradient: wetter/lower areas tend to appear more saturated.
    Subtle but provides an independent signal complementary to luminance gradient.
    """
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    S = hsv[:, :, 1].astype(np.float32)
    S_smooth = gaussian_filter(S, sigma=12)
    gx = cv2.Sobel(S_smooth, cv2.CV_32F, 1, 0, ksize=7)
    gy = cv2.Sobel(S_smooth, cv2.CV_32F, 0, 1, ksize=7)
    magnitude = np.sqrt(gx**2 + gy**2)
    angle = np.arctan2(gy, gx)
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    return angle, magnitude


def vector_field_from_angles(
    angle: np.ndarray, magnitude: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Convert polar (angle, magnitude) to Cartesian (vx, vy) vector field."""
    vx = magnitude * np.cos(angle)
    vy = magnitude * np.sin(angle)
    return vx, vy


def combine_gradient_signals(
    image_bgr: np.ndarray,
    mask: np.ndarray
) -> dict:
    """
    Combine illuminance, saturation, and grain signals into a final gradient field.
    Returns dict with smoothed vector field and grid sample points for overlay.
    """
    h, w = image_bgr.shape[:2]

    # Per-channel signals
    illum_angle, illum_mag = illuminance_gradient_field(image_bgr)
    sat_angle, sat_mag = saturation_gradient_field(image_bgr)
    grain_angle, grain_mag = gabor_grain_field(
        cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    )

    # Weighted combination (illuminance gradient is strongest slope signal)
    illum_vx, illum_vy = vector_field_from_angles(illum_angle, illum_mag)
    sat_vx, sat_vy = vector_field_from_angles(sat_angle, sat_mag)
    # Grain direction → rotate 90° to get slope direction (grain ⊥ slope contour lines)
    grain_slope_angle = grain_angle + np.pi / 2
    grain_vx, grain_vy = vector_field_from_angles(grain_slope_angle, grain_mag * 0.4)

    combined_vx = 0.55 * illum_vx + 0.25 * sat_vx + 0.20 * grain_vx
    combined_vy = 0.55 * illum_vy + 0.25 * sat_vy + 0.20 * grain_vy

    # Apply green mask
    mask_f = (mask > 0).astype(np.float32)
    combined_vx *= mask_f
    combined_vy *= mask_f

    # Strongly smooth to get macro terrain features, not grass-blade micro-texture
    smooth_vx = gaussian_filter(combined_vx, sigma=20)
    smooth_vy = gaussian_filter(combined_vy, sigma=20)

    # Sample on a grid for the overlay arrows
    step = max(h, w) // 16
    grid_points = []
    xs = range(step // 2, w, step)
    ys = range(step // 2, h, step)

    for y in ys:
        for x in xs:
            if mask[min(y, h - 1), min(x, w - 1)] > 0:
                vx_val = float(smooth_vx[min(y, h - 1), min(x, w - 1)])
                vy_val = float(smooth_vy[min(y, h - 1), min(x, w - 1)])
                mag = float(np.sqrt(vx_val**2 + vy_val**2))
                angle_deg = float(np.degrees(np.arctan2(vy_val, vx_val)))
                grid_points.append({
                    "x": int(x), "y": int(y),
                    "vx": round(vx_val, 4), "vy": round(vy_val, 4),
                    "magnitude": round(mag, 4),
                    "angle_deg": round(angle_deg, 1)
                })

    # Overall dominant slope direction (mean vector over masked region)
    masked_vx = smooth_vx[mask > 0]
    masked_vy = smooth_vy[mask > 0]
    mean_vx = float(np.mean(masked_vx)) if masked_vx.size else 0.0
    mean_vy = float(np.mean(masked_vy)) if masked_vy.size else 0.0
    overall_angle = float(np.degrees(np.arctan2(mean_vy, mean_vx)))
    overall_mag = float(np.sqrt(mean_vx**2 + mean_vy**2))

    # Green bounding box (for frontend cropping hint)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    green_bbox = None
    if contours:
        x, y, bw, bh = cv2.boundingRect(max(contours, key=cv2.contourArea))
        green_bbox = {"x": int(x), "y": int(y), "width": int(bw), "height": int(bh)}

    return {
        "grid_points": grid_points,
        "overall_angle_deg": round(overall_angle, 1),
        "overall_magnitude": round(overall_mag, 4),
        "image_size": {"width": w, "height": h},
        "green_bbox": green_bbox,
        "step_size": step,
    }
