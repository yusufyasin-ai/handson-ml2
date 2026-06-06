"use client";

import { useRef, useState, useCallback } from "react";

interface Props {
  onCapture: (file: File) => void;
  onClose: () => void;
}

export default function CameraCapture({ onCapture, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");

  const startCamera = useCallback(async (facing: "environment" | "user") => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
    }
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      setStream(s);
      setError(null);
      if (videoRef.current) {
        videoRef.current.srcObject = s;
      }
    } catch (e) {
      setError("Camera access denied or unavailable. Please upload a photo instead.");
    }
  }, [stream]);

  const handleStart = useCallback(() => startCamera(facingMode), [startCamera, facingMode]);

  const handleFlip = useCallback(() => {
    const next = facingMode === "environment" ? "user" : "environment";
    setFacingMode(next);
    startCamera(next);
  }, [facingMode, startCamera]);

  const handleCapture = useCallback(() => {
    if (!videoRef.current || !stream) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        stream.getTracks().forEach((t) => t.stop());
        setStream(null);
        onCapture(file);
      },
      "image/jpeg",
      0.92
    );
  }, [stream, onCapture]);

  const handleClose = useCallback(() => {
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);
    onClose();
  }, [stream, onClose]);

  return (
    <div className="fixed inset-0 z-50 bg-black/90 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-green-950 rounded-2xl overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-green-800">
          <span className="text-lg font-semibold text-green-300">Camera</span>
          <button onClick={handleClose} className="text-gray-400 hover:text-white text-2xl leading-none">&times;</button>
        </div>

        {error && (
          <div className="p-4 bg-red-900/50 text-red-300 text-sm m-4 rounded-lg">{error}</div>
        )}

        <div className="relative bg-black aspect-video">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
          {!stream && !error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="text-gray-400 text-sm">Camera not started</p>
            </div>
          )}
        </div>

        <div className="p-4 flex gap-3 justify-center flex-wrap">
          {!stream ? (
            <button
              onClick={handleStart}
              className="px-6 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-xl font-medium transition-colors"
            >
              Start Camera
            </button>
          ) : (
            <>
              <button
                onClick={handleFlip}
                className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition-colors"
              >
                Flip
              </button>
              <button
                onClick={handleCapture}
                className="px-8 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-xl font-semibold transition-colors shadow-lg"
              >
                Capture
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
