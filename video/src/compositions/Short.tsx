import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

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

export type BrollClip = {
  src: string;
  ken: string;
  start_ms: number;
  end_ms: number;
};

export type ShortProps = {
  title: string;
  hook: string;
  captions: CaptionCue[];
  beats_on_screen: string[];
  brand: Brand;
  audio_file: string;
  audio_public_name: string;
  broll: BrollClip[];
  duration_in_frames: number;
  fps: number;
  width: number;
  height: number;
};

export const defaultShortProps: ShortProps = {
  title: 'Protect deep work',
  hook: 'Most people get focus completely wrong.',
  captions: [
    {text: 'Focus is under attack', start_ms: 0, end_ms: 4000},
    {text: 'Clarity beats hustle', start_ms: 4000, end_ms: 9000},
    {text: 'One system. Two blocks.', start_ms: 9000, end_ms: 14000},
    {text: 'Save this. Try it tomorrow.', start_ms: 14000, end_ms: 18000},
  ],
  beats_on_screen: [],
  brand: {
    bg_top: '#07141C',
    bg_bottom: '#16384A',
    accent: '#F0B429',
    text: '#F7F4EC',
    muted: '#9EB6C2',
  },
  audio_file: '',
  audio_public_name: '',
  broll: [],
  duration_in_frames: 540,
  fps: 30,
  width: 1080,
  height: 1920,
};

export const shortSchema = undefined;

/** Soft crossfade between photo beats — feels editorial, not slideshow. */
const CROSSFADE_MS = 620;

function kenTransform(
  ken: string,
  progress: number,
): {scale: number; x: number; y: number} {
  const p = Math.min(1, Math.max(0, progress));
  // Ease-in-out for smoother camera moves
  const e = p * p * (3 - 2 * p);
  switch (ken) {
    case 'zoom_out':
      return {scale: interpolate(e, [0, 1], [1.32, 1.06]), x: 0, y: interpolate(e, [0, 1], [-18, 12])};
    case 'pan_left':
      return {
        scale: 1.28,
        x: interpolate(e, [0, 1], [72, -72]),
        y: interpolate(e, [0, 1], [-22, 18]),
      };
    case 'pan_right':
      return {
        scale: 1.28,
        x: interpolate(e, [0, 1], [-72, 72]),
        y: interpolate(e, [0, 1], [18, -22]),
      };
    case 'drift_up':
      return {
        scale: interpolate(e, [0, 1], [1.18, 1.3]),
        x: interpolate(e, [0, 1], [-8, 14]),
        y: interpolate(e, [0, 1], [36, -48]),
      };
    case 'zoom_in':
    default:
      return {
        scale: interpolate(e, [0, 1], [1.08, 1.36]),
        x: interpolate(e, [0, 1], [-20, 24]),
        y: interpolate(e, [0, 1], [14, -28]),
      };
  }
}

const KenBurnsShot: React.FC<{
  clip: BrollClip;
  accent: string;
}> = ({clip, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ms = (frame / fps) * 1000;

  const from = clip.start_ms - CROSSFADE_MS;
  const to = clip.end_ms + CROSSFADE_MS;
  if (ms < from || ms > to) return null;

  const fadeIn = interpolate(
    ms,
    [clip.start_ms - CROSSFADE_MS, clip.start_ms + 40],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const fadeOut = interpolate(
    ms,
    [clip.end_ms - 40, clip.end_ms + CROSSFADE_MS],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const progress = interpolate(ms, [clip.start_ms, clip.end_ms], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const {scale, x, y} = kenTransform(clip.ken || 'zoom_in', progress);

  return (
    <AbsoluteFill style={{opacity}}>
      <AbsoluteFill
        style={{
          transform: `translate(${x}px, ${y}px) scale(${scale})`,
          willChange: 'transform',
        }}
      >
        <Img
          src={staticFile(clip.src)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </AbsoluteFill>
      {/* Cinematic grade — readable center for captions + deep edges */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(4,10,18,0.5) 0%, rgba(4,10,18,0.22) 38%, rgba(4,10,18,0.28) 55%, rgba(4,10,18,0.62) 100%)',
        }}
      />
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse at 50% 48%, rgba(0,0,0,0.35) 0%, transparent 58%)',
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 48% 28%, ${accent}28 0%, transparent 52%)`,
          mixBlendMode: 'soft-light',
        }}
      />
      {/* Warm light leak */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 88% 12%, ${accent}33 0%, transparent 42%)`,
          mixBlendMode: 'screen',
          opacity: 0.55,
        }}
      />
      {/* Cool edge leak */}
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse at 8% 78%, rgba(70,140,180,0.28) 0%, transparent 45%)',
          mixBlendMode: 'screen',
          opacity: 0.4,
        }}
      />
    </AbsoluteFill>
  );
};

/** Soft vignette + film grain overlay for premium Shorts look. */
const CinematicOverlay: React.FC<{accent: string; frame: number}> = ({
  accent,
  frame,
}) => {
  // Subtle grain flicker so stills feel like footage
  const grainOp = 0.085 + 0.025 * Math.sin(frame * 0.73);
  return (
    <>
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.55) 100%)',
          pointerEvents: 'none',
          zIndex: 8,
        }}
      />
      <AbsoluteFill
        style={{
          opacity: grainOp,
          backgroundImage:
            'radial-gradient(rgba(255,255,255,0.95) 0.55px, transparent 0.65px)',
          backgroundSize: '2.8px 2.8px',
          backgroundPosition: `${(frame * 1.7) % 7}px ${(frame * 2.3) % 5}px`,
          pointerEvents: 'none',
          zIndex: 9,
          mixBlendMode: 'overlay',
        }}
      />
      {/* Thin accent rim light */}
      <AbsoluteFill
        style={{
          boxShadow: `inset 0 0 120px ${accent}14`,
          pointerEvents: 'none',
          zIndex: 9,
        }}
      />
    </>
  );
};

export const Short: React.FC<ShortProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const brand = {...defaultShortProps.brand, ...props.brand};
  const captions = props.captions?.length
    ? props.captions
    : defaultShortProps.captions;
  const ms = (frame / fps) * 1000;

  let idx = captions.findIndex((c) => ms >= c.start_ms && ms < c.end_ms);
  if (idx < 0) idx = Math.max(0, captions.length - 1);
  const cue = captions[idx];
  const local = Math.max(0, frame - Math.floor((cue.start_ms / 1000) * fps));
  const enter = spring({
    frame: local,
    fps,
    config: {damping: 16, stiffness: 140, mass: 0.85},
  });
  const y = interpolate(enter, [0, 1], [48, 0]);
  const pop = interpolate(enter, [0, 1], [0.94, 1]);
  const progress = frame / Math.max(durationInFrames - 1, 1);

  // Caption exit soften near beat end
  const cueOut = interpolate(
    ms,
    [cue.end_ms - 280, cue.end_ms],
    [1, 0.15],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const captionOpacity = Math.min(enter, cueOut);

  const titleOpacity = interpolate(frame, [0, 10, 48, 78], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const broll =
    props.broll?.length > 0
      ? props.broll
      : captions.map((c, i) => ({
          src: '',
          ken: (
            ['zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'drift_up'] as const
          )[i % 5],
          start_ms: c.start_ms,
          end_ms: c.end_ms,
        }));

  const publicName = props.audio_public_name || props.audio_file;
  let audioSrc: string | null = null;
  if (publicName) {
    try {
      audioSrc = staticFile(publicName);
    } catch {
      audioSrc = null;
    }
  }

  const hasPhotos = broll.some((b) => Boolean(b.src));
  const displaySize =
    cue.text.length > 42 ? 52 : cue.text.length > 28 ? 64 : cue.text.length > 18 ? 74 : 86;

  return (
    <AbsoluteFill
      style={{
        background: brand.bg_top,
        fontFamily: '"Helvetica Neue", "Avenir Next", system-ui, sans-serif',
        color: brand.text,
        overflow: 'hidden',
      }}
    >
      {hasPhotos ? (
        broll.map((clip, i) =>
          clip.src ? (
            <KenBurnsShot
              key={`${clip.src}-${i}`}
              clip={clip}
              accent={brand.accent}
            />
          ) : null,
        )
      ) : (
        <AbsoluteFill
          style={{
            background: `linear-gradient(165deg, ${brand.bg_top}, ${brand.bg_bottom})`,
          }}
        />
      )}

      <CinematicOverlay accent={brand.accent} frame={frame} />

      {/* Top chrome — minimal, not dashboard */}
      <div
        style={{
          position: 'absolute',
          top: 64,
          left: 52,
          right: 52,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 14,
          opacity: interpolate(frame, [0, 18], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
        }}
      >
        <div
          style={{
            fontSize: 18,
            letterSpacing: 4.5,
            textTransform: 'uppercase',
            fontWeight: 700,
            color: brand.accent,
            textShadow: '0 2px 18px rgba(0,0,0,0.75)',
          }}
        >
          Content Factory
        </div>
        <div
          style={{
            fontSize: 16,
            letterSpacing: 2,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.72)',
            textShadow: '0 2px 12px rgba(0,0,0,0.7)',
          }}
        >
          {String(idx + 1).padStart(2, '0')} / {String(captions.length).padStart(2, '0')}
        </div>
      </div>

      {/* Brief title sting */}
      <div
        style={{
          position: 'absolute',
          top: 150,
          left: 52,
          right: 52,
          opacity: titleOpacity,
          zIndex: 14,
          textShadow: '0 6px 28px rgba(0,0,0,0.8)',
        }}
      >
        <div
          style={{
            fontSize: 17,
            letterSpacing: 3.5,
            textTransform: 'uppercase',
            color: brand.accent,
            marginBottom: 12,
            fontWeight: 700,
          }}
        >
          Watch this
        </div>
        <div
          style={{
            fontFamily: 'Georgia, "Iowan Old Style", "Times New Roman", serif',
            fontSize: 38,
            fontWeight: 700,
            lineHeight: 1.12,
            letterSpacing: -0.4,
            color: '#FFFFFF',
          }}
        >
          {props.title}
        </div>
      </div>

      {/* Centered kinetic caption — premium serif over footage */}
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          padding: '0 56px',
          zIndex: 15,
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            transform: `translateY(${y}px) scale(${pop})`,
            opacity: captionOpacity,
            width: '100%',
            maxWidth: 940,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: 64,
              height: 4,
              background: brand.accent,
              margin: '0 auto 28px',
              borderRadius: 2,
              transform: `scaleX(${enter})`,
              boxShadow: `0 0 28px ${brand.accent}cc`,
            }}
          />
          <div
            style={{
              fontFamily:
                'Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", serif',
              fontSize: displaySize,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: -0.8,
              color: '#FFFFFF',
              textShadow:
                '0 1px 0 rgba(0,0,0,0.45), 0 12px 36px rgba(0,0,0,0.85), 0 0 1px rgba(0,0,0,1)',
            }}
          >
            {cue.text}
          </div>
          <div
            style={{
              marginTop: 26,
              fontSize: 15,
              letterSpacing: 4,
              textTransform: 'uppercase',
              fontWeight: 700,
              color: brand.accent,
              textShadow: '0 2px 16px rgba(0,0,0,0.8)',
              opacity: 0.92,
            }}
          >
            Beat {idx + 1}
          </div>
        </div>
      </AbsoluteFill>

      {/* Slim progress rail */}
      <div
        style={{
          position: 'absolute',
          left: 48,
          right: 48,
          bottom: 64,
          zIndex: 16,
        }}
      >
        <div
          style={{
            height: 3,
            borderRadius: 999,
            background: 'rgba(255,255,255,0.18)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${progress * 100}%`,
              height: '100%',
              background: brand.accent,
              boxShadow: `0 0 18px ${brand.accent}`,
            }}
          />
        </div>
      </div>

      {audioSrc ? <Audio src={audioSrc} /> : null}
    </AbsoluteFill>
  );
};
