#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const rootDir = path.resolve(__dirname, '..');
const nextSwcPath = path.join(rootDir, 'node_modules', 'next', 'dist', 'build', 'swc', 'index.js');
const nextBundlePath = path.join(rootDir, 'node_modules', 'next', 'dist', 'compiled', 'webpack', 'bundle5.js');
const nextBinPath = require.resolve('next/dist/bin/next', { paths: [rootDir] });

function assertHealthyNextInstall() {
  if (!fs.existsSync(nextBundlePath)) {
    throw new Error(`Missing Next webpack bundle at ${nextBundlePath}`);
  }

  const bundle = fs.readFileSync(nextBundlePath, 'utf8');
  if (!bundle.includes('Compilation.PROCESS_ASSETS_STAGE_PRE_PROCESS')) {
    throw new Error(
      'The local Next.js install looks corrupted. Reinstall frontend dependencies before starting the admin console.'
    );
  }
}

function patchNextSwcRuntime() {
  if (!fs.existsSync(nextSwcPath)) {
    throw new Error(`Missing Next SWC runtime at ${nextSwcPath}`);
  }

  let source = fs.readFileSync(nextSwcPath, 'utf8');

  const replacements = [
    {
      needle:
        '        const isWebContainer = process.versions.webcontainer;\n' +
        '        const shouldLoadWasmFallbackFirst = !disableWasmFallback && unsupportedPlatform && useWasmBinary || isWebContainer;',
      replacement:
        '        const isWebContainer = process.versions.webcontainer;\n' +
        '        const forceWasmBinary = process.env.NEXT_FORCE_SWC_WASM === "1";\n' +
        '        const shouldLoadWasmFallbackFirst = !disableWasmFallback && unsupportedPlatform && useWasmBinary || isWebContainer;'
    },
    {
      needle:
        '        if (shouldLoadWasmFallbackFirst) {\n' +
        '            lastNativeBindingsLoadErrorCode = "unsupported_target";',
      replacement:
        '        if (forceWasmBinary) {\n' +
        '            const forcedWasmBindings = await tryLoadWasmWithFallback(attempts);\n' +
        '            if (forcedWasmBindings) {\n' +
        '                return resolve(forcedWasmBindings);\n' +
        '            }\n' +
        '        }\n' +
        '        if (shouldLoadWasmFallbackFirst) {\n' +
        '            lastNativeBindingsLoadErrorCode = "unsupported_target";'
    },
    {
      needle:
        'function loadBindingsSync() {\n' +
        '    let attempts = [];',
      replacement:
        'function loadBindingsSync() {\n' +
        '    if (process.env.NEXT_FORCE_SWC_WASM === "1") {\n' +
        '        if (wasmBindings) {\n' +
        '            return wasmBindings;\n' +
        '        }\n' +
        '        const bindings = require("@next/swc-wasm-nodejs");\n' +
        '        infoLog("next-swc build: wasm build @next/swc-wasm-nodejs (forced)");\n' +
        '        wasmBindings = {\n' +
        '            isWasm: true,\n' +
        '            transform(src, options) {\n' +
        '                if (typeof bindings.transform === "function") {\n' +
        '                    return bindings.transform(src.toString(), options);\n' +
        '                }\n' +
        '                return Promise.resolve(bindings.transformSync(src.toString(), options));\n' +
        '            },\n' +
        '            transformSync(src, options) {\n' +
        '                return bindings.transformSync(src.toString(), options);\n' +
        '            },\n' +
        '            minify(src, options) {\n' +
        '                if (typeof bindings.minify === "function") {\n' +
        '                    return bindings.minify(src.toString(), options);\n' +
        '                }\n' +
        '                return Promise.resolve(bindings.minifySync(src.toString(), options));\n' +
        '            },\n' +
        '            minifySync(src, options) {\n' +
        '                return bindings.minifySync(src.toString(), options);\n' +
        '            },\n' +
        '            parse(src, options) {\n' +
        '                if (typeof bindings.parse === "function") {\n' +
        '                    return bindings.parse(src.toString(), options);\n' +
        '                }\n' +
        '                return Promise.resolve(bindings.parseSync(src.toString(), options));\n' +
        '            },\n' +
        '            parseSync(src, options) {\n' +
        '                return bindings.parseSync(src.toString(), options);\n' +
        '            },\n' +
        '            getTargetTriple() {\n' +
        '                return undefined;\n' +
        '            },\n' +
        '            turbo: {\n' +
        '                startTrace: ()=>{\n' +
        '                    _log.error("Wasm binding does not support trace yet");\n' +
        '                },\n' +
        '                entrypoints: {\n' +
        '                    stream: (turboTasks, rootDir, applicationDir, pageExtensions, callbackFn)=>{\n' +
        '                        return bindings.streamEntrypoints(turboTasks, rootDir, applicationDir, pageExtensions, callbackFn);\n' +
        '                    },\n' +
        '                    get: (turboTasks, rootDir, applicationDir, pageExtensions)=>{\n' +
        '                        return bindings.getEntrypoints(turboTasks, rootDir, applicationDir, pageExtensions);\n' +
        '                    }\n' +
        '                }\n' +
        '            },\n' +
        '            mdx: {\n' +
        '                compile: (src, options)=>bindings.mdxCompile(src, getMdxOptions(options)),\n' +
        '                compileSync: (src, options)=>bindings.mdxCompileSync(src, getMdxOptions(options))\n' +
        '            }\n' +
        '        };\n' +
        '        return wasmBindings;\n' +
        '    }\n' +
        '    let attempts = [];'
    },
    {
      needle:
        '        try {\n' +
        '            let pkgPath = pkg;\n' +
        '            if (importPath) {\n' +
        '                // the import path must be exact when not in node_modules\n' +
        '                pkgPath = _path.default.join(importPath, pkg, "wasm.js");\n' +
        '            }\n' +
        '            let bindings = await import((0, _url.pathToFileURL)(pkgPath).toString());',
      replacement:
        '        try {\n' +
        '            let bindings;\n' +
        '            if (!importPath && pkg === "@next/swc-wasm-nodejs") {\n' +
        '                bindings = require(pkg);\n' +
        '            } else {\n' +
        '                let pkgPath = pkg;\n' +
        '                if (importPath) {\n' +
        '                    // the import path must be exact when not in node_modules\n' +
        '                    pkgPath = _path.default.join(importPath, pkg, "wasm.js");\n' +
        '                }\n' +
        '                bindings = await import((0, _url.pathToFileURL)(pkgPath).toString());\n' +
        '            }'
    },
    {
      needle:
        'function getBinaryMetadata() {\n' +
        '    var _bindings_getTargetTriple;',
      replacement:
        'function getBinaryMetadata() {\n' +
        '    if (process.env.NEXT_FORCE_SWC_WASM === "1") {\n' +
        '        return {\n' +
        '            target: undefined\n' +
        '        };\n' +
        '    }\n' +
        '    var _bindings_getTargetTriple;'
    },
    {
      needle:
        'const initCustomTraceSubscriber = (traceFileName)=>{\n' +
        '    if (!swcTraceFlushGuard) {',
      replacement:
        'const initCustomTraceSubscriber = (traceFileName)=>{\n' +
        '    if (process.env.NEXT_FORCE_SWC_WASM === "1") {\n' +
        '        return;\n' +
        '    }\n' +
        '    if (!swcTraceFlushGuard) {'
    },
    {
      needle:
        'const initHeapProfiler = ()=>{\n' +
        '    try {',
      replacement:
        'const initHeapProfiler = ()=>{\n' +
        '    if (process.env.NEXT_FORCE_SWC_WASM === "1") {\n' +
        '        return;\n' +
        '    }\n' +
        '    try {'
    },
    {
      needle:
        '    let flushed = false;\n' +
        '    return ()=>{\n' +
        '        if (!flushed) {',
      replacement:
        '    let flushed = false;\n' +
        '    return ()=>{\n' +
        '        if (process.env.NEXT_FORCE_SWC_WASM === "1") {\n' +
        '            return;\n' +
        '        }\n' +
        '        if (!flushed) {',
      count: 2
    }
  ];

  for (const replacement of replacements) {
    let applied = 0;
    while (source.includes(replacement.needle)) {
      source = source.replace(replacement.needle, replacement.replacement);
      applied += 1;
      if (!replacement.count || applied >= replacement.count) {
        break;
      }
    }

    if (applied === 0 && !source.includes(replacement.replacement.trim().slice(0, 80))) {
      throw new Error(`Failed to patch Next SWC runtime for pattern: ${replacement.needle.split('\n')[0]}`);
    }
  }

  fs.writeFileSync(nextSwcPath, source);
}

function startNext() {
  const args = process.argv.slice(2);
  const child = spawn(process.execPath, [nextBinPath, ...args], {
    cwd: rootDir,
    env: {
      ...process.env,
      NEXT_FORCE_SWC_WASM: '1'
    },
    stdio: 'inherit'
  });

  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

assertHealthyNextInstall();
patchNextSwcRuntime();
startNext();
