/**
 * SemPKM Frontend Build Script
 *
 * Vendors all CDN dependencies, bundles them into logical groups,
 * minifies all app JS/CSS, content-hashes everything, and produces
 * a manifest.json mapping logical names to hashed filenames.
 *
 * Decisions: D267 (esbuild), D268 (npm vendor strategy),
 *            D269 (.gz pre-compression), D272 (chartjs lazy)
 *
 * Usage: cd frontend && npm ci && node build.js
 */

const esbuild = require('esbuild');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const DIST = path.join(__dirname, 'dist');
const STATIC = path.join(__dirname, 'static');
const NODE_MODULES = path.join(__dirname, 'node_modules');

/** Compute first 8 hex chars of SHA-256 of a buffer */
function contentHash(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex').slice(0, 8);
}

/** Write a file to dist/ with content hash in the name, return the filename */
function writeHashed(logicalBase, ext, content, suffix = '') {
  const buf = Buffer.isBuffer(content) ? content : Buffer.from(content);
  const hash = contentHash(buf);
  const filename = `${logicalBase}-${hash}${suffix}${ext}`;
  fs.writeFileSync(path.join(DIST, filename), buf);
  return filename;
}

/** Read a file from node_modules */
function readVendor(relPath) {
  return fs.readFileSync(path.join(NODE_MODULES, relPath), 'utf8');
}

async function build() {
  const startTime = Date.now();
  const manifest = {};

  // Clean dist/
  if (fs.existsSync(DIST)) {
    fs.rmSync(DIST, { recursive: true });
  }
  fs.mkdirSync(DIST, { recursive: true });

  console.log('Building SemPKM frontend assets...\n');

  // =========================================================================
  // 1. VENDOR JS BUNDLE — concatenated in dependency order
  // =========================================================================
  console.log('1. Building vendor JS bundle...');

  // These are all UMD/IIFE and can be concatenated directly
  const vendorJsSources = [
    // htmx (IIFE, registers window.htmx)
    'htmx.org/dist/htmx.min.js',
    // split.js (IIFE, registers window.Split)
    'split.js/dist/split.min.js',
    // cytoscape (UMD, registers window.cytoscape)
    'cytoscape/dist/cytoscape.min.js',
    // cytoscape layout plugins — must load after cytoscape
    'layout-base/layout-base.js',
    'cose-base/cose-base.js',
    'cytoscape-fcose/cytoscape-fcose.js',
    // dagre + cytoscape-dagre — must load after cytoscape
    'dagre/dist/dagre.min.js',
    'cytoscape-dagre/cytoscape-dagre.js',
    // marked UMD (registers window.marked)
    'marked/lib/marked.umd.js',
    // marked-highlight UMD
    'marked-highlight/lib/index.umd.js',
    // DOMPurify (UMD, registers window.DOMPurify)
    'dompurify/dist/purify.min.js',
    // lucide UMD (registers window.lucide)
    'lucide/dist/umd/lucide.min.js',
    // driver.js IIFE
    'driver.js/dist/driver.js.iife.js',
  ];

  // Concatenate UMD/IIFE sources with separators
  let vendorConcat = '';
  for (const src of vendorJsSources) {
    const code = readVendor(src);
    vendorConcat += `/* ${src} */\n${code}\n;\n`;
  }

  // highlight.js needs esbuild bundling (CJS module, not UMD)
  // Bundle it as IIFE that assigns to window.hljs
  const hljsEntryContent = `
    var hljs = require('highlight.js/lib/common');
    if (typeof window !== 'undefined') { window.hljs = hljs; }
  `;
  const hljsTmpEntry = path.join(DIST, '_hljs_entry.js');
  fs.writeFileSync(hljsTmpEntry, hljsEntryContent);

  const hljsResult = await esbuild.build({
    entryPoints: [hljsTmpEntry],
    bundle: true,
    format: 'iife',
    minify: true,
    write: false,
    platform: 'browser',
    target: 'es2020',
    nodePaths: [NODE_MODULES],
  });
  fs.unlinkSync(hljsTmpEntry);
  const hljsCode = hljsResult.outputFiles[0].text;

  // ninja-keys is ESM with decorators — needs esbuild bundling
  const ninjaEntryContent = `import 'ninja-keys';`;
  const ninjaTmpEntry = path.join(DIST, '_ninja_entry.js');
  fs.writeFileSync(ninjaTmpEntry, ninjaEntryContent);

  const ninjaResult = await esbuild.build({
    entryPoints: [ninjaTmpEntry],
    bundle: true,
    format: 'iife',
    minify: true,
    write: false,
    platform: 'browser',
    target: 'es2020',
    nodePaths: [NODE_MODULES],
  });
  fs.unlinkSync(ninjaTmpEntry);
  const ninjaCode = ninjaResult.outputFiles[0].text;

  // Assemble final vendor bundle: concat + hljs + ninja-keys
  const vendorFull = vendorConcat +
    `/* highlight.js (bundled) */\n${hljsCode}\n;\n` +
    `/* ninja-keys (bundled) */\n${ninjaCode}\n;\n`;

  // Minify the concatenated vendor bundle with keepNames for htmx compatibility
  const vendorMinified = await esbuild.transform(vendorFull, {
    minify: true,
    keepNames: true,
    target: 'es2020',
  });

  const vendorJsFile = writeHashed('vendor', '.min.js', vendorMinified.code);
  manifest['vendor.js'] = vendorJsFile;
  console.log(`   ${vendorJsFile} (${(Buffer.byteLength(vendorMinified.code) / 1024).toFixed(0)}KB)`);

  // =========================================================================
  // 2. VENDOR CSS BUNDLE — driver.js CSS
  // =========================================================================
  console.log('2. Building vendor CSS bundle...');

  const driverCss = readVendor('driver.js/dist/driver.css');
  const vendorCssMinified = await esbuild.transform(driverCss, {
    minify: true,
    loader: 'css',
  });
  const vendorCssFile = writeHashed('vendor', '.min.css', vendorCssMinified.code);
  manifest['vendor.css'] = vendorCssFile;
  console.log(`   ${vendorCssFile}`);

  // =========================================================================
  // 3. WORKSPACE-VENDOR JS — dockview-core
  // =========================================================================
  console.log('3. Building workspace-vendor bundles...');

  const dockviewJs = readVendor('dockview-core/dist/dockview-core.min.js');
  const wsVendorJsFile = writeHashed('workspace-vendor', '.min.js', dockviewJs);
  manifest['workspace-vendor.js'] = wsVendorJsFile;
  console.log(`   ${wsVendorJsFile}`);

  // =========================================================================
  // 4. WORKSPACE-VENDOR CSS — dockview CSS + bridge CSS
  // =========================================================================
  const dockviewCss = readVendor('dockview-core/dist/styles/dockview.css');
  const bridgeCss = fs.readFileSync(
    path.join(STATIC, 'css', 'dockview-sempkm-bridge.css'), 'utf8'
  );
  const wsVendorCssConcat = `${dockviewCss}\n${bridgeCss}`;
  const wsVendorCssMinified = await esbuild.transform(wsVendorCssConcat, {
    minify: true,
    loader: 'css',
  });
  const wsVendorCssFile = writeHashed('workspace-vendor', '.min.css', wsVendorCssMinified.code);
  manifest['workspace-vendor.css'] = wsVendorCssFile;
  console.log(`   ${wsVendorCssFile}`);

  // =========================================================================
  // 5a. GRIDSTACK BUNDLES — UMD JS + minified CSS
  // =========================================================================
  console.log('4a. Building gridstack bundles...');

  const gridstackJs = readVendor('gridstack/dist/gridstack-all.js');
  const gridstackJsMinified = await esbuild.transform(gridstackJs, {
    minify: true,
    target: 'es2020',
  });
  const gridstackJsFile = writeHashed('gridstack', '.min.js', gridstackJsMinified.code);
  manifest['gridstack.js'] = gridstackJsFile;
  console.log(`   ${gridstackJsFile}`);

  const gridstackCss = readVendor('gridstack/dist/gridstack.min.css');
  const gridstackCssMinified = await esbuild.transform(gridstackCss, {
    minify: true,
    loader: 'css',
  });
  const gridstackCssFile = writeHashed('gridstack', '.min.css', gridstackCssMinified.code);
  manifest['gridstack.css'] = gridstackCssFile;
  console.log(`   ${gridstackCssFile}`);

  // =========================================================================
  // 5b. FULLCALENDAR BUNDLE — pre-built global IIFE, just content-hash
  // =========================================================================
  console.log('4b. Building fullcalendar bundle...');

  const fullcalendarJs = fs.readFileSync(
    path.join(NODE_MODULES, 'fullcalendar/index.global.min.js')
  );
  const fullcalendarJsFile = writeHashed('fullcalendar', '.min.js', fullcalendarJs);
  manifest['fullcalendar.js'] = fullcalendarJsFile;
  console.log(`   ${fullcalendarJsFile} (${(fullcalendarJs.length / 1024).toFixed(0)}KB)`);

  // =========================================================================
  // 5c. LEAFLET + MARKERCLUSTER BUNDLES — UMD JS concat + CSS concat
  // =========================================================================
  console.log('4c. Building leaflet bundles...');

  const leafletJsSrc = readVendor('leaflet/dist/leaflet.js');
  const clusterJsSrc = readVendor('leaflet.markercluster/dist/leaflet.markercluster.js');
  const leafletJsConcat = `/* leaflet */\n${leafletJsSrc}\n;\n/* leaflet.markercluster */\n${clusterJsSrc}\n;\n`;
  const leafletJsMinified = await esbuild.transform(leafletJsConcat, {
    minify: true,
    target: 'es2020',
  });
  const leafletJsFile = writeHashed('leaflet', '.min.js', leafletJsMinified.code);
  manifest['leaflet.js'] = leafletJsFile;
  console.log(`   ${leafletJsFile}`);

  const leafletCssSrc = readVendor('leaflet/dist/leaflet.css');
  const clusterCssSrc = readVendor('leaflet.markercluster/dist/MarkerCluster.css');
  const clusterDefaultCssSrc = readVendor('leaflet.markercluster/dist/MarkerCluster.Default.css');
  const leafletCssConcat = `${leafletCssSrc}\n${clusterCssSrc}\n${clusterDefaultCssSrc}`;
  const leafletCssMinified = await esbuild.transform(leafletCssConcat, {
    minify: true,
    loader: 'css',
  });
  const leafletCssFile = writeHashed('leaflet', '.min.css', leafletCssMinified.code);
  manifest['leaflet.css'] = leafletCssFile;
  console.log(`   ${leafletCssFile}`);

  // =========================================================================
  // 5d. FRAPPE-GANTT BUNDLES — UMD JS + CSS
  // =========================================================================
  console.log('4d. Building frappe-gantt bundles...');

  const frappeGanttJs = readVendor('frappe-gantt/dist/frappe-gantt.umd.js');
  const frappeGanttJsMinified = await esbuild.transform(frappeGanttJs, {
    minify: true,
    target: 'es2020',
  });
  const frappeGanttJsFile = writeHashed('frappe-gantt', '.min.js', frappeGanttJsMinified.code);
  manifest['frappe-gantt.js'] = frappeGanttJsFile;
  console.log(`   ${frappeGanttJsFile}`);

  const frappeGanttCss = readVendor('frappe-gantt/dist/frappe-gantt.css');
  const frappeGanttCssMinified = await esbuild.transform(frappeGanttCss, {
    minify: true,
    loader: 'css',
  });
  const frappeGanttCssFile = writeHashed('frappe-gantt', '.min.css', frappeGanttCssMinified.code);
  manifest['frappe-gantt.css'] = frappeGanttCssFile;
  console.log(`   ${frappeGanttCssFile}`);

  // =========================================================================
  // 5e. CODEMIRROR BUNDLES — ESM, bundled via esbuild
  //     Two bundles: markdown (editor.js, vfs-browser.js) and sparql (sparql-console.js)
  // =========================================================================
  console.log('4e. Building CodeMirror bundles...');

  // CodeMirror Markdown bundle — IIFE, exposes window.CM_Markdown
  const cmMarkdownResult = await esbuild.build({
    entryPoints: [path.join(__dirname, 'src', 'codemirror-markdown-entry.js')],
    bundle: true,
    format: 'iife',
    globalName: 'CM_Markdown',
    minify: true,
    write: false,
    platform: 'browser',
    target: 'es2020',
    nodePaths: [NODE_MODULES],
  });
  const cmMarkdownCode = cmMarkdownResult.outputFiles[0].text;
  const cmMarkdownFile = writeHashed('codemirror-markdown', '.min.js', cmMarkdownCode);
  manifest['codemirror-markdown.js'] = cmMarkdownFile;
  console.log(`   ${cmMarkdownFile} (${(Buffer.byteLength(cmMarkdownCode) / 1024).toFixed(0)}KB)`);

  // CodeMirror SPARQL bundle — IIFE, exposes window.CM_Sparql
  const cmSparqlResult = await esbuild.build({
    entryPoints: [path.join(__dirname, 'src', 'codemirror-sparql-entry.js')],
    bundle: true,
    format: 'iife',
    globalName: 'CM_Sparql',
    minify: true,
    write: false,
    platform: 'browser',
    target: 'es2020',
    nodePaths: [NODE_MODULES],
  });
  const cmSparqlCode = cmSparqlResult.outputFiles[0].text;
  const cmSparqlFile = writeHashed('codemirror-sparql', '.min.js', cmSparqlCode);
  manifest['codemirror-sparql.js'] = cmSparqlFile;
  console.log(`   ${cmSparqlFile} (${(Buffer.byteLength(cmSparqlCode) / 1024).toFixed(0)}KB)`);

  // =========================================================================
  // 5. CHART.JS BUNDLE — UMD, just minify and hash
  // =========================================================================
  console.log('5. Building chart.js bundle...');

  const chartJs = readVendor('chart.js/dist/chart.umd.js');
  const chartJsMinified = await esbuild.transform(chartJs, {
    minify: true,
    target: 'es2020',
  });
  const chartJsFile = writeHashed('chartjs', '.min.js', chartJsMinified.code);
  manifest['chartjs.js'] = chartJsFile;
  console.log(`   ${chartJsFile}`);

  // =========================================================================
  // 7. HIGHLIGHT.JS THEME CSS — separate files, dynamically loaded by theme.js
  // =========================================================================
  console.log('6. Building highlight.js theme CSS...');

  const hljsGithubCss = fs.readFileSync(
    path.join(NODE_MODULES, 'highlight.js/styles/github.min.css')
  );
  const hljsGithubFile = writeHashed('hljs-github', '.css', hljsGithubCss);
  manifest['hljs-github.css'] = hljsGithubFile;
  console.log(`   ${hljsGithubFile}`);

  const hljsGithubDarkCss = fs.readFileSync(
    path.join(NODE_MODULES, 'highlight.js/styles/github-dark.min.css')
  );
  const hljsGithubDarkFile = writeHashed('hljs-github-dark', '.css', hljsGithubDarkCss);
  manifest['hljs-github-dark.css'] = hljsGithubDarkFile;
  console.log(`   ${hljsGithubDarkFile}`);

  // =========================================================================
  // 8. APP JS — each file individually minified with content hash
  // =========================================================================
  console.log('7. Building app JS files...');

  const jsDir = path.join(STATIC, 'js');
  const jsFiles = fs.readdirSync(jsDir).filter(f => f.endsWith('.js')).sort();

  for (const file of jsFiles) {
    const src = fs.readFileSync(path.join(jsDir, file), 'utf8');
    const result = await esbuild.transform(src, {
      minify: true,
      target: 'esnext',
      loader: 'js',
    });
    const baseName = file.replace('.js', '');
    const outFile = writeHashed(baseName, '.min.js', result.code);
    manifest[file] = outFile;
    console.log(`   ${file} → ${outFile}`);
  }

  // =========================================================================
  // 9. APP CSS — each file individually minified with content hash
  //    (except dockview-sempkm-bridge.css which is in workspace-vendor bundle)
  // =========================================================================
  console.log('8. Building app CSS files...');

  const cssDir = path.join(STATIC, 'css');
  const cssFiles = fs.readdirSync(cssDir)
    .filter(f => f.endsWith('.css') && f !== 'dockview-sempkm-bridge.css')
    .sort();

  for (const file of cssFiles) {
    const src = fs.readFileSync(path.join(cssDir, file), 'utf8');
    const result = await esbuild.transform(src, {
      minify: true,
      loader: 'css',
    });
    const baseName = file.replace('.css', '');
    const outFile = writeHashed(baseName, '.min.css', result.code);
    manifest[file] = outFile;
    console.log(`   ${file} → ${outFile}`);
  }

  // =========================================================================
  // 10. WRITE MANIFEST
  // =========================================================================
  console.log('\n9. Writing manifest.json...');

  const manifestJson = JSON.stringify(manifest, null, 2);
  fs.writeFileSync(path.join(DIST, 'manifest.json'), manifestJson);
  console.log(`   ${Object.keys(manifest).length} entries`);

  // =========================================================================
  // 10a. STABLE-NAMED COPIES — for static HTML files that can't use manifest
  // =========================================================================
  console.log('9a. Creating stable-named copies for static HTML...');

  // vendor.min.js — used by frontend/static/index.html (dev console)
  fs.copyFileSync(
    path.join(DIST, manifest['vendor.js']),
    path.join(DIST, 'vendor.min.js')
  );
  console.log('   vendor.min.js');

  // =========================================================================
  // 11. GENERATE .gz PRE-COMPRESSED SIBLINGS (D269)
  // =========================================================================
  console.log('10. Generating .gz pre-compressed files...');

  const distFiles = fs.readdirSync(DIST).filter(f =>
    f.endsWith('.js') || f.endsWith('.css') || f.endsWith('.json')
  );

  let gzCount = 0;
  for (const file of distFiles) {
    const filePath = path.join(DIST, file);
    execSync(`gzip -k -9 "${filePath}"`);
    gzCount++;
  }
  console.log(`   ${gzCount} .gz files created`);

  // =========================================================================
  // DONE
  // =========================================================================
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  const totalFiles = fs.readdirSync(DIST).length;
  console.log(`\n✓ Build complete in ${elapsed}s — ${totalFiles} files in dist/`);
  console.log(`  Manifest: ${Object.keys(manifest).length} entries`);
}

build().catch(err => {
  console.error('Build failed:', err);
  process.exit(1);
});
