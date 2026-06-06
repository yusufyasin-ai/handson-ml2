"use client";

import { useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import CameraCapture from "@/components/CameraCapture";
import AnalysisPanel from "@/components/AnalysisPanel";
import type { AnalysisResult } from "@/components/GradientOverlay";

const GradientOverlay = dynamic(() => import("@/components/GradientOverlay"), { ssr: false });

type Status = "idle" | "loading" | "done" | "error";

export default function Home() {
  const [showCamera, setShowCamera] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [showCV, setShowCV] = useState(true);
  const [showClaude, setShowClaude] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const analyseFile = useCallback(async (file: File) => {
    setStatus("loading");
    setResult(null);
    setErrorMsg("");

    const url = URL.createObjectURL(file);
    setImageUrl(url);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/api/analyse", { method: "POST", body: form });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(detail.detail ?? res.statusText);
      }
      const data: AnalysisResult = await res.json();
      setResult(data);
      setStatus("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Unknown error");
      setStatus("error");
    }
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) analyseFile(file);
    },
    [analyseFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) analyseFile(file);
    },
    [analyseFile]
  );

  return (
    <main className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <div className="max-w-5xl mx-auto mb-8">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-3xl">⛳</span>
          <h1 className="text-2xl font-bold text-white tracking-tight">GreenReader</h1>
        </div>
        <p className="text-green-400 text-sm ml-11">
          AI-powered putting green slope &amp; gradient analyser
        </p>
      </div>

      <div className="max-w-5xl mx-auto grid md:grid-cols-[1fr_320px] gap-6">
        {/* Left — image / upload */}
        <div className="space-y-4">
          {/* Upload / drop zone */}
          {status === "idle" && (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className="border-2 border-dashed border-green-700 rounded-2xl p-10 flex flex-col items-center gap-4 bg-green-950/30 hover:bg-green-950/50 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="text-5xl">📸</div>
              <div className="text-center">
                <p className="text-white font-medium">Drop a putting green photo here</p>
                <p className="text-gray-400 text-sm mt-1">or click to browse · JPEG, PNG, WEBP</p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  className="px-5 py-2 bg-green-700 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Upload photo
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowCamera(true); }}
                  className="px-5 py-2 bg-green-900 hover:bg-green-800 text-white rounded-lg text-sm font-medium transition-colors border border-green-700"
                >
                  Use camera
                </button>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>
          )}

          {/* Loading */}
          {status === "loading" && imageUrl && (
            <div className="relative rounded-2xl overflow-hidden">
              <img src={imageUrl} alt="Analysing..." className="w-full rounded-2xl opacity-60" />
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40">
                <div className="w-12 h-12 border-4 border-green-400 border-t-transparent rounded-full animate-spin mb-3" />
                <p className="text-white font-medium">Analysing gradients…</p>
                <p className="text-gray-300 text-sm mt-1">Running CV + AI vision</p>
              </div>
            </div>
          )}

          {/* Error */}
          {status === "error" && (
            <div className="bg-red-950/60 border border-red-700 rounded-2xl p-6 text-center">
              <p className="text-red-300 font-medium mb-2">Analysis failed</p>
              <p className="text-red-400 text-sm mb-4">{errorMsg}</p>
              <button
                onClick={() => { setStatus("idle"); setImageUrl(null); }}
                className="px-5 py-2 bg-red-800 hover:bg-red-700 text-white rounded-lg text-sm"
              >
                Try again
              </button>
            </div>
          )}

          {/* Result overlay */}
          {status === "done" && imageUrl && result && (
            <>
              {/* Layer toggles */}
              <div className="flex gap-3 flex-wrap">
                <button
                  onClick={() => setShowHeatmap((v) => !v)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    showHeatmap ? "bg-orange-700 text-white" : "bg-gray-800 text-gray-400"
                  }`}
                >
                  Heatmap
                </button>
                <button
                  onClick={() => setShowCV((v) => !v)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    showCV ? "bg-green-700 text-white" : "bg-gray-800 text-gray-400"
                  }`}
                >
                  CV Gradients
                </button>
                <button
                  onClick={() => setShowClaude((v) => !v)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    showClaude ? "bg-cyan-700 text-white" : "bg-gray-800 text-gray-400"
                  }`}
                >
                  AI Arrows
                </button>
                <button
                  onClick={() => { setStatus("idle"); setImageUrl(null); setResult(null); }}
                  className="ml-auto px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
                >
                  New photo
                </button>
              </div>

              <GradientOverlay
                imageUrl={imageUrl}
                result={result}
                showCV={showCV}
                showClaude={showClaude}
                showHeatmap={showHeatmap}
              />

              {/* Legend */}
              <div className="flex gap-4 text-xs text-gray-400 flex-wrap">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-gradient-to-r from-blue-400 to-red-400 inline-block rounded" />
                  CV gradient (blue=flat, red=steep)
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-cyan-400 inline-block rounded" />
                  AI directional arrows
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-orange-500/60 inline-block" />
                  Slope intensity heatmap
                </span>
              </div>
            </>
          )}
        </div>

        {/* Right — analysis panel */}
        <div>
          {result ? (
            <AnalysisPanel result={result} />
          ) : (
            <div className="bg-green-950/30 rounded-2xl p-6 border border-green-900 text-center">
              <div className="text-4xl mb-3">🏌️</div>
              <p className="text-green-400 font-medium text-sm">
                Upload or capture a photo of the green to see the gradient analysis
              </p>
              <ul className="mt-4 text-left text-xs text-gray-400 space-y-1.5">
                <li>✓ Shadow &amp; lighting gradient (depth-from-shading)</li>
                <li>✓ Grass grain / texture direction (Gabor filters)</li>
                <li>✓ Colour saturation gradient</li>
                <li>✓ Claude AI semantic scene analysis</li>
                <li>✓ Putting break &amp; pace advice</li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {showCamera && (
        <CameraCapture
          onCapture={(file) => { setShowCamera(false); analyseFile(file); }}
          onClose={() => setShowCamera(false)}
        />
      )}
    </main>
  );
}
