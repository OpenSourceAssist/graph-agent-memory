#!/usr/bin/env node
/**
 * Documentation build script for neo4j-agent-memory
 *
 * Usage:
 *   node build.js          # Build docs once
 *   node build.js --watch  # Watch for changes and rebuild
 *   node build.js --serve  # Build, watch, and serve with live reload
 */

const Asciidoctor = require("asciidoctor")();
const fs = require("fs");
const path = require("path");

// Configuration
const CONFIG = {
  srcDir: __dirname,
  outDir: path.join(__dirname, "_site"),
  assetsDir: path.join(__dirname, "assets"),

  // Asciidoctor options
  asciidoctorOptions: {
    safe: "safe",
    backend: "html5",
    doctype: "article",
    standalone: true,
    attributes: {
      "source-highlighter": "highlight.js",
      "highlightjs-theme": "github-dark",
      icons: "font",
      toc: "left",
      toclevels: 3,
      sectanchors: true,
      sectlinks: true,
      experimental: true,
      nofooter: true,
      linkcss: true,
      stylesheet: "style.css",
      copycss: true,
      // Custom attributes
      "project-name": "Neo4j Agent Memory",
      "project-version": "0.1.0",
      "project-repo": "https://github.com/neo4j-labs/neo4j-agent-memory",
    },
  },
};

// Files to process (AsciiDoc files only)
const ADOC_FILES = [
  "index.adoc",
  "getting-started.adoc",
  "memory-types.adoc",
  "entity-extraction.adoc",
  "poleo-model.adoc",
  "configuration.adoc",
  "integrations.adoc",
  "faq.adoc",
  "product-improvements.adoc",
];

/**
 * Ensure output directory exists
 */
function ensureOutDir() {
  if (!fs.existsSync(CONFIG.outDir)) {
    fs.mkdirSync(CONFIG.outDir, { recursive: true });
  }
}

/**
 * Copy static assets
 */
function copyAssets() {
  const assetsOutDir = path.join(CONFIG.outDir);

  // Copy CSS
  const cssSource = path.join(CONFIG.assetsDir, "style.css");
  const cssDest = path.join(assetsOutDir, "style.css");
  if (fs.existsSync(cssSource)) {
    fs.copyFileSync(cssSource, cssDest);
    console.log(`  Copied: style.css`);
  }

  // Copy any images
  const imagesDir = path.join(CONFIG.assetsDir, "images");
  const imagesOutDir = path.join(assetsOutDir, "images");
  if (fs.existsSync(imagesDir)) {
    if (!fs.existsSync(imagesOutDir)) {
      fs.mkdirSync(imagesOutDir, { recursive: true });
    }
    fs.readdirSync(imagesDir).forEach((file) => {
      fs.copyFileSync(
        path.join(imagesDir, file),
        path.join(imagesOutDir, file),
      );
    });
    console.log(`  Copied: images/`);
  }
}

/**
 * Convert a single AsciiDoc file to HTML
 */
function convertFile(filename) {
  const inputPath = path.join(CONFIG.srcDir, filename);
  const outputFilename = filename.replace(".adoc", ".html");
  const outputPath = path.join(CONFIG.outDir, outputFilename);

  if (!fs.existsSync(inputPath)) {
    console.warn(`  Warning: ${filename} not found, skipping`);
    return;
  }

  try {
    const content = fs.readFileSync(inputPath, "utf8");
    const options = {
      ...CONFIG.asciidoctorOptions,
      standalone: false,
      to_file: false,
    };

    const doc = Asciidoctor.load(content, options);
    const html = doc.convert();
    const docTitle = doc.getDocumentTitle() || null;

    // Wrap in custom template with navigation
    const fullHtml = wrapInTemplate(html, filename, docTitle);

    fs.writeFileSync(outputPath, fullHtml);
    console.log(`  Built: ${outputFilename}`);
  } catch (error) {
    console.error(`  Error building ${filename}:`, error.message);
  }
}

/**
 * Wrap converted HTML in custom template with navigation
 */
function wrapInTemplate(content, sourceFile, docTitle) {
  const title = docTitle || extractTitle(content) || "Documentation";

  // Navigation items
  const navItems = [
    { file: "index.html", label: "Overview" },
    { file: "getting-started.html", label: "Getting Started" },
    { file: "memory-types.html", label: "Memory Types" },
    { file: "entity-extraction.html", label: "Entity Extraction" },
    { file: "poleo-model.html", label: "POLE+O Model" },
    { file: "configuration.html", label: "Configuration" },
    { file: "integrations.html", label: "Integrations" },
    { file: "faq.html", label: "FAQ" },
    { file: "product-improvements.html", label: "Roadmap" },
  ];

  const currentFile = sourceFile.replace(".adoc", ".html");

  const navHtml = navItems
    .map((item) => {
      const isActive = item.file === currentFile ? ' class="active"' : "";
      return `<a href="${item.file}"${isActive}>${item.label}</a>`;
    })
    .join("\n          ");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} | Neo4j Agent Memory</title>
  <link rel="stylesheet" href="style.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link id="hljs-theme" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/cypher.min.js"></script>
  <script>
    // Apply saved theme before paint to prevent flash
    (function() {
      var saved = localStorage.getItem('docs-theme');
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      var theme = saved || (prefersDark ? 'dark' : 'light');
      if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('hljs-theme').href =
          'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css';
      }
    })();
  </script>
  <script>hljs.highlightAll();</script>
</head>
<body>
  <!-- Mobile header (visible <= 1024px) -->
  <div class="mobile-header">
    <button class="menu-toggle" aria-label="Open navigation menu">
      <i class="fa-solid fa-bars"></i>
    </button>
    <a href="index.html" class="nav-logo">
      <span class="logo-icon">🧠</span>
      <span class="logo-text">Agent Memory</span>
    </a>
    <span class="version-badge">v0.1.0</span>
    <button class="theme-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
      <i class="icon-sun fa-solid fa-sun"></i>
      <i class="icon-moon fa-solid fa-moon"></i>
    </button>
  </div>

  <!-- Overlay backdrop for mobile nav -->
  <div class="nav-overlay" aria-hidden="true"></div>

  <div class="docs-wrapper">
    <nav class="docs-nav" aria-label="Main navigation">
      <div class="nav-header">
        <a href="index.html" class="nav-logo">
          <span class="logo-icon">🧠</span>
          <span class="logo-text">Agent Memory</span>
        </a>
        <span class="version-badge">v0.1.0</span>
        <button class="theme-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
          <i class="icon-sun fa-solid fa-sun"></i>
          <i class="icon-moon fa-solid fa-moon"></i>
        </button>
      </div>
      <div class="nav-links">
        <div class="nav-section">
          <span class="nav-section-title">Documentation</span>
          ${navHtml}
        </div>
        <div class="nav-section">
          <span class="nav-section-title">Resources</span>
          <a href="https://github.com/neo4j-labs/neo4j-agent-memory" target="_blank">
            <i class="fab fa-github"></i> GitHub
          </a>
          <a href="https://pypi.org/project/neo4j-agent-memory/" target="_blank">
            <i class="fab fa-python"></i> PyPI
          </a>
        </div>
      </div>
    </nav>
    <main class="docs-content">
      ${content}
    </main>
  </div>
  <script>
    (function() {
      // --- Theme toggle (all toggle buttons) ---
      var toggles = document.querySelectorAll('.theme-toggle');
      toggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
          var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
          var newTheme = isDark ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', newTheme);
          localStorage.setItem('docs-theme', newTheme);
          var hljsLink = document.getElementById('hljs-theme');
          if (hljsLink) {
            hljsLink.href = newTheme === 'dark'
              ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css'
              : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css';
          }
        });
      });

      // --- Mobile nav toggle ---
      var menuBtn = document.querySelector('.menu-toggle');
      var nav = document.querySelector('.docs-nav');
      var overlay = document.querySelector('.nav-overlay');

      function openNav() {
        nav.classList.add('open');
        overlay.classList.add('visible');
        document.body.classList.add('nav-open');
        menuBtn.setAttribute('aria-label', 'Close navigation menu');
        menuBtn.querySelector('i').className = 'fa-solid fa-xmark';
      }

      function closeNav() {
        nav.classList.remove('open');
        overlay.classList.remove('visible');
        document.body.classList.remove('nav-open');
        menuBtn.setAttribute('aria-label', 'Open navigation menu');
        menuBtn.querySelector('i').className = 'fa-solid fa-bars';
      }

      if (menuBtn && nav && overlay) {
        menuBtn.addEventListener('click', function() {
          if (nav.classList.contains('open')) {
            closeNav();
          } else {
            openNav();
          }
        });

        overlay.addEventListener('click', closeNav);

        // Close nav when a link is tapped
        nav.querySelectorAll('.nav-links a').forEach(function(link) {
          link.addEventListener('click', closeNav);
        });

        // Close nav on Escape key
        document.addEventListener('keydown', function(e) {
          if (e.key === 'Escape' && nav.classList.contains('open')) {
            closeNav();
          }
        });
      }

      // --- Wrap tables for horizontal scroll ---
      document.querySelectorAll('.docs-content table').forEach(function(table) {
        if (!table.closest('.tableblock-wrapper') && !table.closest('.admonitionblock')) {
          var wrapper = document.createElement('div');
          wrapper.className = 'tableblock-wrapper';
          table.parentNode.insertBefore(wrapper, table);
          wrapper.appendChild(table);
        }
      });
    })();
  </script>
</body>
</html>`;
}

/**
 * Extract title from HTML content
 */
function extractTitle(html) {
  const match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
  return match ? match[1].trim() : null;
}

/**
 * Build all documentation
 */
function buildAll() {
  console.log("Building documentation...");
  console.log(`  Source: ${CONFIG.srcDir}`);
  console.log(`  Output: ${CONFIG.outDir}`);
  console.log("");

  ensureOutDir();
  copyAssets();

  console.log("");
  console.log("Converting AsciiDoc files:");
  ADOC_FILES.forEach((file) => convertFile(file));

  console.log("");
  console.log("Documentation build complete!");
  console.log(
    `Open ${path.join(CONFIG.outDir, "index.html")} in your browser.`,
  );
}

/**
 * Watch for changes
 */
async function watch() {
  const chokidar = require("chokidar");

  console.log("Watching for changes...");

  const watcher = chokidar.watch(
    [path.join(CONFIG.srcDir, "*.adoc"), path.join(CONFIG.assetsDir, "**/*")],
    {
      ignoreInitial: true,
    },
  );

  watcher.on("change", (filePath) => {
    console.log(`\nFile changed: ${path.basename(filePath)}`);
    if (filePath.endsWith(".adoc")) {
      convertFile(path.basename(filePath));
    } else {
      copyAssets();
    }
  });

  watcher.on("add", (filePath) => {
    console.log(`\nFile added: ${path.basename(filePath)}`);
    buildAll();
  });
}

/**
 * Serve with live reload
 */
async function serve() {
  const liveServer = require("live-server");

  const params = {
    port: 8080,
    root: CONFIG.outDir,
    open: true,
    wait: 500,
    logLevel: 1,
  };

  console.log(`\nStarting live server at http://localhost:${params.port}`);
  liveServer.start(params);
}

// Main
const args = process.argv.slice(2);

buildAll();

if (args.includes("--watch") || args.includes("--serve")) {
  watch();
}

if (args.includes("--serve")) {
  serve();
}
