import { build, context } from 'esbuild';

const options = {
  entryPoints: ['frontend/main.jsx'],
  bundle: true,
  minify: !process.argv.includes('--watch'),
  outfile: 'public/static/app.js',
  jsx: 'automatic',
  target: ['es2020'],
  loader: { '.woff2': 'file', '.woff': 'file' },
  assetNames: 'fonts/[name]-[hash]',
  publicPath: '/static',
  define: { 'process.env.NODE_ENV': '"production"' },
  legalComments: 'linked',
  logLevel: 'info',
};

if (process.argv.includes('--watch')) {
  const watcher = await context(options);
  await watcher.watch();
  console.log('Watching React and CSS sources. Run python app.py in another terminal.');
} else {
  await build(options);
}
