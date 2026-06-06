"use client";

import { useEffect, useRef } from "react";

export interface GridPoint {
  x: number;
  y: number;
  vx: number;
  vy: number;
  magnitude: number;
  angle_deg: number;
  claude_direction_deg?: number;
  claude_severity?: number;
  claude_confidence?: number;
}

export interface AnalysisResult {
  cv_analysis: {
    grid_points: GridPoint[];
    overall_angle_deg: number;
    overall_magnitude: number;
    image_size: { width: number; height: number };
    green_bbox?: { x: number; y: number; width: number; height: number };
    step_size: number;
  };
  claude_analysis?: {
    overall?: {
      slope_direction_deg: number;
      slope_severity: number;
      confidence: number;
      dominant_cue: string;
      summary: string;
    };
    zones?: Array<{
      row: number;
      col: number;
      slope_direction_deg: number;
      slope_severity: number;
      confidence: number;
      notes: string;
    }>;
    putting_advice?: {
      break_direction: string;
      estimated_break_inches: number;
      pace_note: string;
      aim_tip: string;
    };
    lighting?: { direction_deg: number; quality: string };
    error?: string;
  };
  image_dimensions: { width: number; height: number };
}

interface Props {
  imageUrl: string;
  result: AnalysisResult;
  showCV: boolean;
  showClaude: boolean;
  showHeatmap: boolean;
}

const ARROW_SCALE = 48;

function slopeColor(magnitude: number): string {
  // Blue (flat) → Yellow → Red (steep)
  const t = Math.min(magnitude * 4, 1);
  const r = Math.round(255 * t);
  const g = Math.round(255 * (1 - Math.abs(t - 0.5) * 2));
  const b = Math.round(255 * (1 - t));
  return `rgb(${r},${g},${b})`;
}

function drawArrow(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  angle: number,
  magnitude: number,
  color: string,
  alpha: number = 0.85
) {
  const len = Math.min(magnitude * ARROW_SCALE, 32);
  if (len < 4) return;

  const rad = (angle * Math.PI) / 180;
  const ex = x + Math.cos(rad) * len;
  const ey = y + Math.sin(rad) * len;
  const headLen = len * 0.35;
  const headAngle = 0.45;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";

  // Shaft
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(ex, ey);
  ctx.stroke();

  // Arrowhead
  ctx.beginPath();
  ctx.moveTo(ex, ey);
  ctx.lineTo(
    ex - headLen * Math.cos(rad - headAngle),
    ey - headLen * Math.sin(rad - headAngle)
  );
  ctx.lineTo(
    ex - headLen * Math.cos(rad + headAngle),
    ey - headLen * Math.sin(rad + headAngle)
  );
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawHeatmapDot(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  magnitude: number,
  stepSize: number
) {
  const radius = stepSize * 0.45;
  const t = Math.min(magnitude * 5, 1);
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
  const alpha = 0.35 + t * 0.25;
  gradient.addColorStop(0, `rgba(255,${Math.round(200 * (1 - t))},0,${alpha})`);
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  ctx.save();
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

export default function GradientOverlay({ imageUrl, result, showCV, showClaude, showHeatmap }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const img = new Image();
    img.onload = () => {
      const { width: imgW, height: imgH } = result.image_dimensions;
      const displayW = container.clientWidth;
      const scale = displayW / imgW;
      const displayH = imgH * scale;

      canvas.width = displayW;
      canvas.height = displayH;

      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, displayW, displayH);
      ctx.drawImage(img, 0, 0, displayW, displayH);

      const pts = result.cv_analysis.grid_points;
      const step = result.cv_analysis.step_size * scale;

      // Heatmap layer
      if (showHeatmap) {
        pts.forEach((pt) => {
          drawHeatmapDot(ctx, pt.x * scale, pt.y * scale, pt.magnitude, step);
        });
      }

      // CV gradient arrows
      if (showCV) {
        pts.forEach((pt) => {
          const color = slopeColor(pt.magnitude);
          drawArrow(ctx, pt.x * scale, pt.y * scale, pt.angle_deg, pt.magnitude, color);
        });
      }

      // Claude semantic arrows
      if (showClaude) {
        pts.forEach((pt) => {
          if (pt.claude_direction_deg !== undefined && pt.claude_severity !== undefined) {
            const conf = pt.claude_confidence ?? 0.5;
            if (conf < 0.3) return;
            drawArrow(
              ctx,
              pt.x * scale,
              pt.y * scale,
              pt.claude_direction_deg,
              pt.claude_severity * 0.8,
              "#00ffff",
              0.7 * conf
            );
          }
        });
      }

      // Green bounding box
      const bbox = result.cv_analysis.green_bbox;
      if (bbox) {
        ctx.save();
        ctx.strokeStyle = "rgba(100,255,100,0.5)";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(bbox.x * scale, bbox.y * scale, bbox.width * scale, bbox.height * scale);
        ctx.restore();
      }
    };
    img.src = imageUrl;
  }, [imageUrl, result, showCV, showClaude, showHeatmap]);

  return (
    <div ref={containerRef} className="relative w-full">
      <img src={imageUrl} alt="Putting green" className="w-full rounded-xl opacity-0 absolute" />
      <canvas ref={canvasRef} className="w-full rounded-xl" />
    </div>
  );
}
