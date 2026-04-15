/**
 * Applies patches/*.patch from the mobile/ directory using `patch -p1` (POSIX).
 *
 * Not `git apply`: git skips hunks for gitignored paths like node_modules, so patches never apply.
 *
 * Idempotent: if already applied, skips without prompting (reverse dry-run succeeds).
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const patchesDir = path.join(root, 'patches');

function patchArgs(patchPath, extra) {
  // Do not use --silent on --dry-run: on macOS it can make exit codes unreliable.
  return ['-p1', '-f', ...extra, '-i', patchPath];
}

function main() {
  if (!fs.existsSync(patchesDir)) {
    return;
  }

  const patches = fs
    .readdirSync(patchesDir)
    .filter((f) => f.endsWith('.patch'))
    .sort();

  for (const name of patches) {
    const patchPath = path.join(patchesDir, name);

    const already = spawnSync('patch', patchArgs(patchPath, ['--dry-run', '-R']), {
      cwd: root,
    });
    if (already.status === 0) {
      process.stdout.write(`Patch already applied: ${name}\n`);
      continue;
    }

    const canApply = spawnSync('patch', patchArgs(patchPath, ['--dry-run']), {
      cwd: root,
    });
    if (canApply.status !== 0) {
      process.stderr.write(
        `Could not apply ${name}: not applicable (wrong expo-modules-core version or corrupt files?).\n`
      );
      process.exit(1);
    }

    const apply = spawnSync('patch', patchArgs(patchPath, ['--no-backup-if-mismatch']), {
      cwd: root,
      stdio: 'inherit',
    });
    if (apply.status !== 0) {
      process.exit(apply.status || 1);
    }
  }
}

main();
