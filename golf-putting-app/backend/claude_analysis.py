"""
Claude Vision analysis for putting green slope interpretation.

Computer vision alone cannot reliably determine absolute slope direction from
a flat grass surface. Claude Vision provides:
  - High-level scene understanding (lighting direction, shadows, undulations)
  - Grass grain / sheen direction interpretation
  - Slope confidence assessment
  - Putting break recommendation
  - Correction overlay grid (angle + magnitude at key zones)
"""

import base64
import json
import re
from pathlib import Path

import anthropic


SYSTEM_PROMPT = """You are an expert golf course analyst and caddie with deep knowledge of
reading putting greens. You can interpret subtle visual cues in photographs of putting greens:
shadow patterns, grass grain (sheen direction), colour saturation differences, visible
undulations, and surrounding terrain context."""

ANALYSIS_PROMPT = """Analyse this putting green photograph and return a detailed slope/gradient
analysis as a JSON object. Focus on:

1. Identifying slope direction by reading:
   - Shadow casting direction and length (long shadows = significant slope)
   - Grass grain sheen (lighter = viewing with the grain; darker = against the grain)
   - Colour / brightness gradients across the surface
   - Visible surface undulations or ridges
   - Surrounding context (hills, water runoff paths)

2. Divide the visible green into a 4×4 grid of zones (row 0-3 top-bottom,
   col 0-3 left-right). For each zone present in the image return:
   - slope_direction: compass bearing the ball would roll toward (0=North/up, 90=East/right)
   - slope_severity: 0.0 (flat) to 1.0 (severe)
   - confidence: 0.0-1.0 how confident you are for this zone
   - notes: one-line visual cue explanation

3. Identify the dominant overall slope direction and severity.

4. Describe the suggested putting adjustments (aim point offset, pace notes).

Return ONLY valid JSON in this exact schema, no markdown fences:
{
  "overall": {
    "slope_direction_deg": <number 0-359>,
    "slope_severity": <0.0-1.0>,
    "confidence": <0.0-1.0>,
    "dominant_cue": "<shadow|grain|colour|undulation|context>",
    "summary": "<one sentence>"
  },
  "zones": [
    {
      "row": <0-3>, "col": <0-3>,
      "slope_direction_deg": <number>,
      "slope_severity": <0.0-1.0>,
      "confidence": <0.0-1.0>,
      "notes": "<string>"
    }
  ],
  "putting_advice": {
    "break_direction": "<left|right|straight>",
    "estimated_break_inches": <number>,
    "pace_note": "<fast|medium|slow>",
    "aim_tip": "<string>"
  },
  "lighting": {
    "direction_deg": <0-359 where light appears to come from>,
    "quality": "<harsh|soft|overcast>"
  }
}"""


def analyse_image_with_claude(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Send image to Claude Vision and parse the structured gradient analysis."""
    client = anthropic.Anthropic()

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": ANALYSIS_PROMPT},
                ],
            }
        ],
    )

    raw_text = message.content[0].text.strip()

    # Strip any accidental markdown code fences
    raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
    raw_text = re.sub(r"\n?```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Attempt to extract a JSON object from mixed response
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Claude returned non-JSON response", "raw": raw_text}
