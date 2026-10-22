'use strict'

// Generates a sitemap.xml for the component's published pages so the docs
// can be submitted to search engines (Google Search Console, Bing).
//
// Pages are generated under /agent-memory/ but served publicly at
// https://neo4j.com/labs/agent-memory/, so the public base URL is
// configurable via the extension config key `base_url`:
//
//   antora:
//     extensions:
//       - require: ./extensions/sitemap.js
//         base_url: https://neo4j.com/labs
//
// The sitemap is published next to the component's pages
// (agent-memory/sitemap.xml), which the hosting layer maps to
// /labs/agent-memory/sitemap.xml.

const DEFAULT_BASE_URL = 'https://neo4j.com/labs'
const COMPONENT_NAME = 'agent-memory'

module.exports.register = function ({ config } = {}) {
  const baseUrl = ((config && config.base_url) || DEFAULT_BASE_URL).replace(/\/$/, '')
  this.on('beforePublish', ({ contentCatalog, siteCatalog }) => {
    const pages = contentCatalog.getPages(
      (page) => page.out && page.src.component === COMPONENT_NAME && page.src.family === 'page'
    )
    if (!pages.length) return
    const urls = pages.map((page) => baseUrl + page.pub.url).sort()
    const xml =
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      urls.map((loc) => `  <url><loc>${loc}</loc></url>`).join('\n') +
      '\n</urlset>\n'
    siteCatalog.addFile({
      contents: Buffer.from(xml),
      out: { path: `${COMPONENT_NAME}/sitemap.xml` },
      pub: { url: `/${COMPONENT_NAME}/sitemap.xml` },
    })
  })
}
