#!/usr/bin/env node
/**
 * OpenCode Acode Plugin — Build/Packaging Script
 *
 * Packages the plugin into a ZIP file that can be installed
 * in Acode via Settings → Plugins → Install from ZIP.
 *
 * Usage:
 *   node scripts/zip.js              # Build the plugin ZIP
 *   node scripts/zip.js --watch      # Watch for changes and rebuild
 */

const fs = require('fs');
const path = require('path');

const PLUGIN_DIR = path.resolve(__dirname, '..');
const OUTPUT_DIR = path.resolve(PLUGIN_DIR, 'dist');
const PLUGIN_ZIP = path.join(OUTPUT_DIR, 'acode-oc.zip');

// Files to include in the plugin ZIP
// Must match the "files" array in plugin.json exactly
const FILES = [
  'plugin.json',
  'main.js',
  'icon.png',
  'README.md',
  'scripts/cors-proxy.js',
];

async function build() {
  // Ensure output directory exists
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  // Load archiver (install if missing)
  let archiverMod;
  try {
    archiverMod = require('archiver');
  } catch (e) {
    console.log('[OpenCode] archiver not found. Installing...');
    require('child_process').execSync(
      'npm install archiver --no-save',
      { cwd: PLUGIN_DIR, stdio: 'inherit' }
    );
    archiverMod = require('archiver');
  }

  const archive = new archiverMod.ZipArchive();
  const output = fs.createWriteStream(PLUGIN_ZIP);

  archive.on('error', (err) => { throw err; });
  archive.pipe(output);

  // Add each file
  for (const file of FILES) {
    const filePath = path.join(PLUGIN_DIR, file);
    if (fs.existsSync(filePath)) {
      archive.file(filePath, { name: file });
      console.log(`  + ${file}`);
    } else {
      console.warn(`  ! WARNING: ${file} not found, skipping`);
    }
  }

  await archive.finalize();

  // Wait for the output stream to finish
  await new Promise((resolve, reject) => {
    output.on('close', resolve);
    output.on('error', reject);
  });

  const size = (archive.pointer() / 1024).toFixed(1);
  console.log(`\n  ✓ Plugin packaged: ${PLUGIN_ZIP}`);
  console.log(`  Size: ${size} KB`);
  console.log(`  Files: ${FILES.length}`);
  console.log(`\n  Install in Acode:`);
  console.log(`    Settings → Plugins → Install from ZIP`);
  console.log(`    Select: ${PLUGIN_ZIP}\n`);
}

// ─── Watch mode ──────────────────────────────────

function watch() {
  console.log('[OpenCode] Watching for changes...');
  const watched = FILES.map((f) => path.join(PLUGIN_DIR, f));
  watched.forEach((f) => {
    fs.watch(f, () => {
      console.log(`\n[OpenCode] Change detected: ${path.basename(f)}`);
      build().catch((err) => console.error(err));
    });
  });
}

// ─── Main ────────────────────────────────────────

const args = process.argv.slice(2);
if (args.includes('--watch')) {
  build()
    .then(() => watch())
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
} else {
  build().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
