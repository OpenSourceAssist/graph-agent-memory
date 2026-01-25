#!/usr/bin/env node
/**
 * Documentation build script for neo4j-agent-memory
 *
 * Usage:
 *   node build.js          # Build docs once
 *   node build.js --watch  # Watch for changes and rebuild
 *   node build.js --serve  # Build, watch, and serve with live reload
 *   node build.js --validate  # Check for broken links
 */

const Asciidoctor = require("asciidoctor")();
const fs = require("fs");
const path = require("path");

// Configuration
const CONFIG = {
  srcDir: __dirname,
  outDir: path.join(__dirname, "_site"),
  assetsDir: path.join(__dirname, "assets"),

  // Diataxis documentation quadrants
  quadrants: ["explanation", "tutorials", "how-to", "reference"],

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

// Build statistics
const stats = {
  filesProcessed: 0,
  errors: [],
  startTime: null,
};

/**
 * Recursively find all .adoc files in a directory
 */
function findAdocFiles(dir, basePath = "") {
  const files = [];
  if (!fs.existsSync(dir)) return files;

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = path.join(basePath, entry.name);

    if (entry.isDirectory()) {
      // Skip _site, node_modules, and hidden directories
      if (
        !entry.name.startsWith("_") &&
        !entry.name.startsWith(".") &&
        entry.name !== "node_modules"
      ) {
        files.push(...findAdocFiles(fullPath, relativePath));
      }
    } else if (entry.name.endsWith(".adoc")) {
      files.push(relativePath);
    }
  }
  return files;
}

/**
 * Ensure output directory exists
 */
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * Copy static assets recursively
 */
function copyAssets() {
  const assetsOutDir = CONFIG.outDir;

  // Copy CSS
  const cssSource = path.join(CONFIG.assetsDir, "style.css");
  const cssDest = path.join(assetsOutDir, "style.css");
  if (fs.existsSync(cssSource)) {
    fs.copyFileSync(cssSource, cssDest);
    console.log(`  Copied: style.css`);
  }

  // Copy favicon
  const faviconSource = path.join(CONFIG.assetsDir, "favicon.svg");
  const faviconDest = path.join(assetsOutDir, "favicon.svg");
  if (fs.existsSync(faviconSource)) {
    fs.copyFileSync(faviconSource, faviconDest);
    console.log(`  Copied: favicon.svg`);
  }

  // Copy images directory recursively
  copyDirRecursive(
    path.join(CONFIG.assetsDir, "images"),
    path.join(assetsOutDir, "images"),
  );
}

/**
 * Recursively copy a directory
 */
function copyDirRecursive(src, dest) {
  if (!fs.existsSync(src)) return;

  ensureDir(dest);
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
  console.log(`  Copied: ${path.relative(CONFIG.assetsDir, src)}/`);
}

/**
 * Get quadrant from file path
 */
function getQuadrant(filePath) {
  const parts = filePath.split(path.sep);
  if (parts.length > 0 && CONFIG.quadrants.includes(parts[0])) {
    return parts[0];
  }
  return null;
}

/**
 * Generate navigation structure from file system
 */
function generateNavigation(adocFiles) {
  const nav = {
    root: [],
    quickstart: [],
    tutorials: [],
    "how-to": [],
    reference: [],
    explanation: [],
  };

  // Files that belong in the Quickstart section
  const quickstartFiles = [
    "configuration.html",
    "enrichment.html",
    "entity-extraction.html",
    "getting-started.html",
    "integrations.html",
    "memory-types.html",
    "poleo-model.html",
  ];

  // Labels for quadrant sections
  const quadrantLabels = {
    tutorials: "Tutorials",
    "how-to": "How-To Guides",
    reference: "Reference",
    explanation: "Concepts",
  };

  // Process all files
  for (const file of adocFiles) {
    const quadrant = getQuadrant(file);
    const htmlFile = file.replace(".adoc", ".html");
    const label = getNavLabel(file);

    if (quadrant) {
      nav[quadrant].push({ file: htmlFile, label });
    } else if (quickstartFiles.includes(htmlFile)) {
      nav.quickstart.push({ file: htmlFile, label });
    } else {
      nav.root.push({ file: htmlFile, label });
    }
  }

  // Sort each section (index files first, then alphabetically)
  for (const key of Object.keys(nav)) {
    nav[key].sort((a, b) => {
      if (a.file.endsWith("index.html")) return -1;
      if (b.file.endsWith("index.html")) return 1;
      return a.label.localeCompare(b.label);
    });
  }

  return { nav, quadrantLabels };
}

/**
 * Get navigation label from file path
 */
function getNavLabel(filePath) {
  const fileName = path.basename(filePath, ".adoc");

  // Special cases
  const specialLabels = {
    index: "Overview",
    "getting-started": "Getting Started",
    "memory-types": "Memory Types",
    "entity-extraction": "Entity Extraction",
    "poleo-model": "POLE+O Model",
    configuration: "Configuration",
    integrations: "Integrations",
    faq: "FAQ",
    "product-improvements": "Roadmap",
    "first-agent-memory": "First Agent Memory",
    "conversation-memory": "Conversation Memory",
    "knowledge-graph": "Knowledge Graph",
    messages: "Messages",
    entities: "Entities",
    preferences: "Preferences",
    "reasoning-traces": "Reasoning Traces",
    "batch-processing": "Batch Processing",
    geocoding: "Geocoding",
    enrichment: "Enrichment",
    deduplication: "Deduplication",
    "pydantic-ai": "PydanticAI",
    langchain: "LangChain",
    llamaindex: "LlamaIndex",
    crewai: "CrewAI",
    "environment-variables": "Environment Variables",
    extractors: "Extractors",
    schemas: "Schemas",
    cli: "CLI",
    deployment: "Deployment",
    "memory-client": "MemoryClient",
    "short-term": "Short-Term Memory",
    "long-term": "Long-Term Memory",
    reasoning: "Reasoning Memory",
    "extraction-pipeline": "Extraction Pipeline",
    "graph-architecture": "Graph Architecture",
    "resolution-deduplication": "Resolution & Deduplication",
  };

  if (specialLabels[fileName]) {
    return specialLabels[fileName];
  }

  // Convert kebab-case to Title Case
  return fileName
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Convert a single AsciiDoc file to HTML
 */
function convertFile(filePath, navigation) {
  const inputPath = path.join(CONFIG.srcDir, filePath);
  const outputPath = path.join(
    CONFIG.outDir,
    filePath.replace(".adoc", ".html"),
  );

  // Ensure output directory exists
  ensureDir(path.dirname(outputPath));

  if (!fs.existsSync(inputPath)) {
    console.warn(`  Warning: ${filePath} not found, skipping`);
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

    // Calculate relative path to root for stylesheet
    const depth = filePath.split(path.sep).length - 1;
    const rootPath = depth > 0 ? "../".repeat(depth) : "";

    // Wrap in custom template with navigation
    const fullHtml = wrapInTemplate(
      html,
      filePath,
      docTitle,
      navigation,
      rootPath,
    );

    fs.writeFileSync(outputPath, fullHtml);
    stats.filesProcessed++;
    console.log(`  Built: ${filePath.replace(".adoc", ".html")}`);
  } catch (error) {
    stats.errors.push({ file: filePath, error: error.message });
    console.error(`  Error building ${filePath}:`, error.message);
  }
}

/**
 * Generate breadcrumb HTML
 */
function generateBreadcrumb(filePath, rootPath) {
  const parts = filePath.split(path.sep);
  const crumbs = [{ href: `${rootPath}index.html`, label: "Home" }];

  // Add quadrant if present
  if (parts.length > 1) {
    const quadrant = parts[0];
    const quadrantLabels = {
      tutorials: "Tutorials",
      "how-to": "How-To Guides",
      reference: "Reference",
      explanation: "Concepts",
    };
    if (quadrantLabels[quadrant]) {
      crumbs.push({
        href: `${rootPath}${quadrant}/index.html`,
        label: quadrantLabels[quadrant],
      });
    }

    // Add subdirectory if present (e.g., integrations, api)
    if (parts.length > 2) {
      const subdir = parts[1];
      const subdirLabel = subdir.charAt(0).toUpperCase() + subdir.slice(1);
      crumbs.push({
        href: `${rootPath}${quadrant}/${subdir}/index.html`,
        label: subdirLabel,
      });
    }
  }

  return crumbs
    .map((crumb, i) =>
      i === crumbs.length - 1
        ? `<span class="breadcrumb-current">${crumb.label}</span>`
        : `<a href="${crumb.href}" class="breadcrumb-link">${crumb.label}</a>`,
    )
    .join('<span class="breadcrumb-separator">/</span>');
}

/**
 * Wrap converted HTML in custom template with navigation
 */
function wrapInTemplate(content, sourceFile, docTitle, navigation, rootPath) {
  const title = docTitle || extractTitle(content) || "Documentation";
  const quadrant = getQuadrant(sourceFile);
  const currentFile = sourceFile.replace(".adoc", ".html");
  const breadcrumbHtml = generateBreadcrumb(sourceFile, rootPath);

  // Build navigation HTML
  const { nav, quadrantLabels } = navigation;

  // Root navigation items (just Overview)
  const rootNavHtml = nav.root
    .filter(
      (item) => !["product-improvements.html", "faq.html"].includes(item.file),
    )
    .map((item) => {
      const isActive = item.file === currentFile ? ' class="active"' : "";
      return `<a href="${rootPath}${item.file}"${isActive}>${item.label}</a>`;
    })
    .join("\n          ");

  // Quickstart navigation items
  const quickstartNavHtml = nav.quickstart
    .map((item) => {
      const isActive = item.file === currentFile ? ' class="active"' : "";
      return `<a href="${rootPath}${item.file}"${isActive}>${item.label}</a>`;
    })
    .join("\n            ");

  // Quadrant navigation sections
  const quadrantNavHtml = CONFIG.quadrants
    .map((q) => {
      if (nav[q].length === 0) return "";
      const isCurrentQuadrant = quadrant === q;
      const items = nav[q]
        .map((item) => {
          const isActive = item.file === currentFile ? ' class="active"' : "";
          return `<a href="${rootPath}${item.file}"${isActive}>${item.label}</a>`;
        })
        .join("\n            ");
      return `
        <div class="nav-section nav-section-quadrant" data-quadrant="${q}">
          <span class="nav-section-title${isCurrentQuadrant ? " current" : ""}">${quadrantLabels[q]}</span>
          ${items}
        </div>`;
    })
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} | Neo4j Agent Memory</title>
  <link rel="icon" type="image/svg+xml" href="${rootPath}favicon.svg">
  <link rel="stylesheet" href="${rootPath}style.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link id="hljs-theme" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
  <link href="${rootPath}pagefind/pagefind-ui.css" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/cypher.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/yaml.min.js"></script>
  <script src="${rootPath}pagefind/pagefind-ui.js"></script>
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
<body${quadrant ? ` data-quadrant="${quadrant}"` : ""}>
  <!-- Search modal -->
  <div id="search-modal" class="search-modal" role="dialog" aria-modal="true" aria-labelledby="search-title">
    <div class="search-modal-backdrop"></div>
    <div class="search-modal-content">
      <div class="search-modal-header">
        <h2 id="search-title" class="search-modal-title">Search Documentation</h2>
        <button class="search-modal-close" aria-label="Close search">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div id="search-container"></div>
      <div class="search-modal-footer">
        <kbd>↵</kbd> to select &nbsp; <kbd>↑</kbd><kbd>↓</kbd> to navigate &nbsp; <kbd>Esc</kbd> to close
      </div>
    </div>
  </div>

  <!-- Mobile header (visible <= 1024px) -->
  <div class="mobile-header">
    <button class="menu-toggle" aria-label="Open navigation menu">
      <i class="fa-solid fa-bars"></i>
    </button>
    <a href="${rootPath}index.html" class="nav-logo">
      <span class="logo-icon">🧠</span>
      <span class="logo-text">Agent Memory</span>
    </a>
    <button class="search-trigger" aria-label="Search documentation" title="Search (Ctrl+K)">
      <i class="fa-solid fa-magnifying-glass"></i>
    </button>
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
        <a href="${rootPath}index.html" class="nav-logo">
          <span class="logo-icon">🧠</span>
          <span class="logo-text">Agent Memory</span>
        </a>
        <span class="version-badge">v0.1.0</span>
        <button class="search-trigger" aria-label="Search documentation" title="Search (Ctrl+K)">
          <i class="fa-solid fa-magnifying-glass"></i>
          <span class="search-shortcut"><kbd>⌘</kbd><kbd>K</kbd></span>
        </button>
        <button class="theme-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
          <i class="icon-sun fa-solid fa-sun"></i>
          <i class="icon-moon fa-solid fa-moon"></i>
        </button>
      </div>
      <div class="nav-links">
        <div class="nav-section">
          <span class="nav-section-title">Documentation</span>
          ${rootNavHtml}
        </div>
        <div class="nav-section">
          <span class="nav-section-title">Quickstart</span>
          ${quickstartNavHtml}
        </div>
        ${quadrantNavHtml}
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
      <nav class="breadcrumb" aria-label="Breadcrumb">
        ${breadcrumbHtml}
      </nav>
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

      // --- Code block copy buttons ---
      document.querySelectorAll('.listingblock pre').forEach(function(pre) {
        var button = document.createElement('button');
        button.className = 'code-copy-btn';
        button.innerHTML = '<i class="fa-regular fa-copy"></i>';
        button.title = 'Copy to clipboard';
        button.addEventListener('click', function() {
          var code = pre.querySelector('code');
          var text = code ? code.textContent : pre.textContent;
          navigator.clipboard.writeText(text).then(function() {
            button.innerHTML = '<i class="fa-solid fa-check"></i>';
            setTimeout(function() {
              button.innerHTML = '<i class="fa-regular fa-copy"></i>';
            }, 2000);
          });
        });
        pre.style.position = 'relative';
        pre.appendChild(button);
      });

      // --- Search modal ---
      var searchModal = document.getElementById('search-modal');
      var searchContainer = document.getElementById('search-container');
      var searchInitialized = false;

      function openSearch() {
        if (!searchInitialized && typeof PagefindUI !== 'undefined') {
          new PagefindUI({
            element: '#search-container',
            showSubResults: true,
            showImages: false,
            resetStyles: false
          });
          searchInitialized = true;
        }
        searchModal.classList.add('open');
        document.body.classList.add('search-open');
        setTimeout(function() {
          var input = searchContainer.querySelector('input');
          if (input) input.focus();
        }, 100);
      }

      function closeSearch() {
        searchModal.classList.remove('open');
        document.body.classList.remove('search-open');
      }

      // Search trigger buttons
      document.querySelectorAll('.search-trigger').forEach(function(btn) {
        btn.addEventListener('click', openSearch);
      });

      // Close button and backdrop
      var closeBtn = searchModal.querySelector('.search-modal-close');
      var backdrop = searchModal.querySelector('.search-modal-backdrop');
      if (closeBtn) closeBtn.addEventListener('click', closeSearch);
      if (backdrop) backdrop.addEventListener('click', closeSearch);

      // Keyboard shortcut (Cmd+K / Ctrl+K)
      document.addEventListener('keydown', function(e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          if (searchModal.classList.contains('open')) {
            closeSearch();
          } else {
            openSearch();
          }
        }
        if (e.key === 'Escape' && searchModal.classList.contains('open')) {
          closeSearch();
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
  stats.startTime = Date.now();
  stats.filesProcessed = 0;
  stats.errors = [];

  console.log("Building documentation...");
  console.log(`  Source: ${CONFIG.srcDir}`);
  console.log(`  Output: ${CONFIG.outDir}`);
  console.log("");

  ensureDir(CONFIG.outDir);
  copyAssets();

  // Find all AsciiDoc files
  const adocFiles = findAdocFiles(CONFIG.srcDir);
  console.log(`\nFound ${adocFiles.length} AsciiDoc files`);

  // Generate navigation
  const navigation = generateNavigation(adocFiles);

  // Convert all files
  console.log("\nConverting AsciiDoc files:");
  adocFiles.forEach((file) => convertFile(file, navigation));

  // Print build stats
  const elapsed = ((Date.now() - stats.startTime) / 1000).toFixed(2);
  console.log("\n" + "=".repeat(50));
  console.log(`Build complete in ${elapsed}s`);
  console.log(`  Files processed: ${stats.filesProcessed}`);
  if (stats.errors.length > 0) {
    console.log(`  Errors: ${stats.errors.length}`);
    stats.errors.forEach((e) => console.log(`    - ${e.file}: ${e.error}`));
  }
  console.log("=".repeat(50));
  console.log(
    `Open ${path.join(CONFIG.outDir, "index.html")} in your browser.`,
  );
}

/**
 * Validate internal links
 */
function validateLinks() {
  console.log("\nValidating internal links...");
  const errors = [];

  // Find all HTML files in output
  const htmlFiles = [];
  function findHtmlFiles(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        findHtmlFiles(fullPath);
      } else if (entry.name.endsWith(".html")) {
        htmlFiles.push(fullPath);
      }
    }
  }
  findHtmlFiles(CONFIG.outDir);

  // Check each file for broken links
  for (const htmlFile of htmlFiles) {
    const content = fs.readFileSync(htmlFile, "utf8");
    const linkRegex = /href="([^"#]+)"/g;
    let match;

    while ((match = linkRegex.exec(content)) !== null) {
      const href = match[1];

      // Skip external links
      if (href.startsWith("http") || href.startsWith("//")) continue;

      // Skip pagefind assets (generated separately by pagefind)
      if (href.includes("pagefind/")) continue;

      // Skip links to examples directory (outside docs)
      if (href.includes("/examples/")) continue;

      // Resolve relative path
      const linkTarget = path.resolve(path.dirname(htmlFile), href);

      if (!fs.existsSync(linkTarget)) {
        const relativePath = path.relative(CONFIG.outDir, htmlFile);
        errors.push({ file: relativePath, brokenLink: href });
      }
    }
  }

  if (errors.length > 0) {
    console.log(`\nFound ${errors.length} broken links:`);
    errors.forEach((e) => console.log(`  ${e.file}: ${e.brokenLink}`));
    process.exit(1);
  } else {
    console.log("All internal links valid!");
  }
}

/**
 * Watch for changes
 */
async function watch() {
  const chokidar = require("chokidar");

  console.log("\nWatching for changes...");

  const watcher = chokidar.watch(
    [
      path.join(CONFIG.srcDir, "**/*.adoc"),
      path.join(CONFIG.assetsDir, "**/*"),
    ],
    {
      ignoreInitial: true,
      ignored: [
        path.join(CONFIG.srcDir, "_site/**"),
        path.join(CONFIG.srcDir, "node_modules/**"),
      ],
    },
  );

  watcher.on("change", (filePath) => {
    console.log(`\nFile changed: ${path.relative(CONFIG.srcDir, filePath)}`);
    buildAll();
  });

  watcher.on("add", (filePath) => {
    console.log(`\nFile added: ${path.relative(CONFIG.srcDir, filePath)}`);
    buildAll();
  });

  watcher.on("unlink", (filePath) => {
    console.log(`\nFile removed: ${path.relative(CONFIG.srcDir, filePath)}`);
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

if (args.includes("--validate")) {
  buildAll();
  validateLinks();
} else {
  buildAll();

  if (args.includes("--watch") || args.includes("--serve")) {
    watch();
  }

  if (args.includes("--serve")) {
    serve();
  }
}
