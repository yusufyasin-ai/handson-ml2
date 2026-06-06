"use client";

import type { AnalysisResult } from "./GradientOverlay";

interface Props {
  result: AnalysisResult;
}

function compassLabel(deg: number): string {
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"];
  return dirs[Math.round(((deg % 360) + 360) % 360 / 45)];
}

function severityLabel(s: number): { label: string; color: string } {
  if (s < 0.15) return { label: "Flat", color: "text-green-400" };
  if (s < 0.35) return { label: "Gentle", color: "text-yellow-300" };
  if (s < 0.6) return { label: "Moderate", color: "text-orange-400" };
  return { label: "Steep", color: "text-red-400" };
}

export default function AnalysisPanel({ result }: Props) {
  const ca = result.claude_analysis;
  const cv = result.cv_analysis;

  return (
    <div className="space-y-4">
      {/* CV Summary */}
      <div className="bg-green-950/60 rounded-xl p-4 border border-green-800">
        <h3 className="text-green-300 font-semibold text-sm uppercase tracking-wide mb-2">
          Computer Vision
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-400">Dominant direction</span>
            <p className="text-white font-medium">
              {compassLabel(cv.overall_angle_deg)} ({cv.overall_angle_deg.toFixed(0)}°)
            </p>
          </div>
          <div>
            <span className="text-gray-400">Signal strength</span>
            <p className={`font-medium ${severityLabel(cv.overall_magnitude).color}`}>
              {severityLabel(cv.overall_magnitude).label}
            </p>
          </div>
          <div>
            <span className="text-gray-400">Green points detected</span>
            <p className="text-white font-medium">{cv.grid_points.length}</p>
          </div>
          {cv.green_bbox && (
            <div>
              <span className="text-gray-400">Green coverage</span>
              <p className="text-white font-medium">
                {Math.round((cv.green_bbox.width * cv.green_bbox.height) /
                  (result.image_dimensions.width * result.image_dimensions.height) * 100)}%
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Claude Summary */}
      {ca && !ca.error && ca.overall && (
        <div className="bg-cyan-950/50 rounded-xl p-4 border border-cyan-800">
          <h3 className="text-cyan-300 font-semibold text-sm uppercase tracking-wide mb-2">
            AI Visual Analysis
          </h3>
          <p className="text-gray-200 text-sm mb-3 italic">&ldquo;{ca.overall.summary}&rdquo;</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-400">Slope direction</span>
              <p className="text-white font-medium">
                {compassLabel(ca.overall.slope_direction_deg)} ({ca.overall.slope_direction_deg}°)
              </p>
            </div>
            <div>
              <span className="text-gray-400">Severity</span>
              <p className={`font-medium ${severityLabel(ca.overall.slope_severity).color}`}>
                {severityLabel(ca.overall.slope_severity).label} ({(ca.overall.slope_severity * 100).toFixed(0)}%)
              </p>
            </div>
            <div>
              <span className="text-gray-400">Confidence</span>
              <p className="text-white font-medium">{(ca.overall.confidence * 100).toFixed(0)}%</p>
            </div>
            <div>
              <span className="text-gray-400">Key cue</span>
              <p className="text-white font-medium capitalize">{ca.overall.dominant_cue}</p>
            </div>
          </div>
        </div>
      )}

      {/* Putting Advice */}
      {ca && !ca.error && ca.putting_advice && (
        <div className="bg-yellow-950/50 rounded-xl p-4 border border-yellow-800">
          <h3 className="text-yellow-300 font-semibold text-sm uppercase tracking-wide mb-2">
            Putting Advice
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Break</span>
              <span className="text-white font-medium capitalize">
                {ca.putting_advice.break_direction} — ~{ca.putting_advice.estimated_break_inches}&quot;
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Pace</span>
              <span className="text-white font-medium capitalize">{ca.putting_advice.pace_note}</span>
            </div>
            <div className="mt-2 pt-2 border-t border-yellow-900">
              <p className="text-yellow-100 text-sm">{ca.putting_advice.aim_tip}</p>
            </div>
          </div>
        </div>
      )}

      {/* Lighting */}
      {ca && !ca.error && ca.lighting && (
        <div className="bg-gray-900/50 rounded-xl p-3 border border-gray-700 text-xs text-gray-400 flex gap-4">
          <span>Light from {compassLabel(ca.lighting.direction_deg)} ({ca.lighting.direction_deg}°)</span>
          <span className="capitalize">{ca.lighting.quality} light</span>
        </div>
      )}

      {/* Claude error */}
      {ca?.error && (
        <div className="bg-red-950/50 rounded-xl p-3 border border-red-800 text-sm text-red-300">
          AI analysis: {ca.error}
        </div>
      )}
    </div>
  );
}
