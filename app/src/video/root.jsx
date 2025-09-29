import React from 'react';
import { Composition } from 'remotion';
import { CaptionComposition } from './CaptionComposition.jsx';

const Root = () => {
  return (
    <>
      <Composition
        id="CaptionComposition"
        component={CaptionComposition}
        durationInFrames={30 * 10}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{ videoUrl: '', segments: [], styleKey: 'bottom-centered' }}
      />
    </>
  );
};

export default Root;


