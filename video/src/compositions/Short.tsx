import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type CaptionCue = {
  text: string;
  start_ms: number;
  end_ms: number;
};

export type Brand = {
  bg_top: string;
  bg_bottom: string;
  accent: string;
  text: string;
  muted: string;
};

export type ShortProps = {
  title: string;
  hook: string;
  captions: CaptionCue[];
  beats_on_screen: string[];
  brand: Brand;
  audio_file: string;
  duration_in_frames: number;
  fps: number;
  width: number;
  height: number;
};

export const shortSchema = undefined;

const FRAME_SAFE = { padding: "7% 8%" } as const;

function activeCaption(
  captions: CaptionCue[],
  frame: number,
  fps: number
): CaptionCue | null {
  const ms = (frame / fps) * 1000;
  for (const c of captions) {
    if (ms >= c.start_ms && ms < c.end_ms) return c;
  }
  return captions[captions.length - 1] || null;
}

const SoftOrbs: React.FC<{ brand: Brand }> = ({ brand }) => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 40) * 30;
  const drift2 = Math.cos(frame / 55) * 40;
  return (
    <>
      <div
        style={{
          position: "absolute",
          width: 520,
          height: 520,
          borderRadius: "50%",
          background: brand.accent,
          opacity: 0.12,
          filter: "blur(80px)",
          top: 180 + drift,
          left: -80 + drift2,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 420,
          height: 420,
          borderRadius: "50%",
          background: brand.muted,
          opacity: 0.1,
          filter: "blur(70px)",
          bottom: 220 - drift,
          right: -60 - drift2,
        }}
      />
    </>
  );
};

const AccentBar: React.FC<{ brand: Brand; progress: number }> = ({
  brand,
  progress,
}) => (
  <div
    style={{
      width: `${Math.max(8, progress * 100)}%`,
      height: 4,
      background: brand.accent,
      borderRadius: 2,
      marginTop: 28,
    }}
  />
);

export const Short: React.FC<ShortProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { brand, captions, title, audio_file } = props;

  const cue = activeCaption(captions, frame, fps);
  const enter = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 120 },
  });
  const scale = interpolate(enter, [0, 1], [0.94, 1]);
  const opacity = interpolate(enter, [0, 1], [0, 1]);
  const progress = frame / Math.max(durationInFrames - 1, 1);

  // subtle punch when caption changes
  const captionKey = cue?.text || "";
  const captionOpacity = interpolate(
    frame % Math.max(Math.floor(fps * 0.35), 1),
    [0, 4, 10],
    [0.85, 1, 1],
    { extrapolateRight: "clamp" }
  );

  let audioSrc: string | null = null;
  try {
    audioSrc = staticFile(audio_file);
  } catch {
    audioSrc = null;
  }

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(165deg, ${brand.bg_top} 0%, ${brand.bg_bottom} 55%, #0A1620 100%)`,
        fontFamily:
          '"DM Sans", "Avenir Next", "Segoe UI", system-ui, sans-serif',
        color: brand.text,
      }}
    >
      <SoftOrbs brand={brand} />

      {/* thin frame */}
      <div
        style={{
          position: "absolute",
          inset: 36,
          border: `1px solid ${brand.muted}33`,
          borderRadius: 8,
          pointerEvents: "none",
        }}
      />

      <AbsoluteFill
        style={{
          ...FRAME_SAFE,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          transform: `scale(${scale})`,
          opacity,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 22,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: brand.muted,
              fontWeight: 600,
            }}
          >
            Content Factory
          </div>
          <h1
            style={{
              margin: "18px 0 0",
              fontSize: 54,
              lineHeight: 1.15,
              fontWeight: 700,
              maxWidth: "92%",
            }}
          >
            {title}
          </h1>
          <AccentBar brand={brand} progress={progress} />
        </div>

        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "40px 0",
          }}
        >
          <div
            key={captionKey}
            style={{
              fontSize: 64,
              lineHeight: 1.2,
              fontWeight: 700,
              textAlign: "center",
              maxWidth: "95%",
              opacity: captionOpacity,
              textShadow: "0 8px 40px rgba(0,0,0,0.35)",
            }}
          >
            {cue?.text || props.hook}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            color: brand.muted,
            fontSize: 22,
            fontWeight: 500,
          }}
        >
          <span style={{ color: brand.accent }}>●</span>
          <span>Shorts · Reels</span>
        </div>
      </AbsoluteFill>

      {audioSrc ? <Audio src={audioSrc} /> : null}
    </AbsoluteFill>
  );
};
