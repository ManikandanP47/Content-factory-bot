import React from 'react';
import {Composition} from 'remotion';
import {Short, defaultShortProps, ShortProps} from './compositions/Short';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Short"
        component={Short}
        durationInFrames={defaultShortProps.duration_in_frames}
        fps={defaultShortProps.fps}
        width={defaultShortProps.width}
        height={defaultShortProps.height}
        defaultProps={defaultShortProps}
        calculateMetadata={async ({props}) => {
          const p = props as ShortProps;
          return {
            durationInFrames: Math.max(1, p.duration_in_frames || 1350),
            fps: p.fps || 30,
            width: p.width || 1080,
            height: p.height || 1920,
            props: p,
          };
        }}
      />
    </>
  );
};
