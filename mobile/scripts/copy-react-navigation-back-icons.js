/**
 * Workaround for Metro dev asset resolution (facebook/metro#1667, react-navigation#13023):
 * Metro requests back-icon@Nx.png but @react-navigation/elements only ships
 * back-icon@Nx.ios.png / back-icon@Nx.android.png. Copying iOS variants to the generic
 * names unblocks the dev server; platform-specific assets still resolve at runtime.
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const assetsDir = path.join(
  root,
  'node_modules',
  '@react-navigation',
  'elements',
  'lib',
  'module',
  'assets'
);

function main() {
  if (!fs.existsSync(assetsDir)) {
    process.stdout.write(
      'copy-react-navigation-back-icons: skip (no @react-navigation/elements assets dir)\n'
    );
    return;
  }

  const scales = [1, 2, 3, 4];
  for (const n of scales) {
    const from = path.join(assetsDir, `back-icon@${n}x.ios.png`);
    const to = path.join(assetsDir, `back-icon@${n}x.png`);
    if (!fs.existsSync(from)) {
      process.stderr.write(`copy-react-navigation-back-icons: missing ${from}\n`);
      process.exitCode = 1;
      continue;
    }
    fs.copyFileSync(from, to);
  }
  if (process.exitCode === 1) {
    process.exit(1);
  }
  process.stdout.write('copy-react-navigation-back-icons: ok\n');
}

main();
