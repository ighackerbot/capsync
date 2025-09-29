import { bundle } from '@remotion/bundler';
import { renderMedia } from '@remotion/renderer';
import path from 'path';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

const argv = yargs(hideBin(process.argv))
  .option('input', { type: 'string', demandOption: true, describe: 'Input video file (mp4)' })
  .option('captions', { type: 'string', describe: 'Captions JSON file with segments' })
  .option('style', { type: 'string', default: 'bottom-centered', choices: ['bottom-centered', 'top-bar', 'karaoke'] })
  .option('out', { type: 'string', demandOption: true, describe: 'Output mp4 path' })
  .parseSync();

type Segment = { id: string; start: number; end: number; text: string };

async function main() {
  const entry = path.join(process.cwd(), '..', 'app', 'src', 'video', 'remotion.js');
  const bundleLocation = await bundle({ entryPoint: entry });

  let segments: Segment[] = [];
  if (argv.captions) {
    const loaded = await import(path.isAbsolute(argv.captions) ? `file://${argv.captions}` : `file://${path.join(process.cwd(), argv.captions)}`);
    segments = (loaded.default || loaded.segments || []) as Segment[];
  }

  await renderMedia({
    composition: 'CaptionComposition',
    serveUrl: bundleLocation,
    codec: 'h264',
    outPath: argv.out,
    inputProps: {
      videoUrl: path.isAbsolute(argv.input) ? argv.input : path.join(process.cwd(), argv.input),
      segments,
      styleKey: argv.style,
    },
  });
  console.log('Rendered to', argv.out);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});


