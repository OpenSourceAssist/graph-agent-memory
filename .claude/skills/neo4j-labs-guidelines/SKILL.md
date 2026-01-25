---
name: neo4j-labs-brand
description: Brand identity guidelines for Neo4j Labs projects. Use when creating documentation, README files, presentations, diagrams, or marketing materials for Neo4j Labs projects. Defines visual identity, tone, messaging, and lifecycle badges that differentiate Labs from official Neo4j products while maintaining brand connection.
---

# Neo4j Labs Brand Identity

Brand guidelines for Neo4j Labs projects—the experimental incubator for next-generation graph developer tooling.

## What is Neo4j Labs?

Neo4j Labs is a collection of the latest innovations in graph technology. Projects are:
- Designed and developed by Neo4j engineers
- Actively maintained but without SLAs or backwards compatibility guarantees
- Supported via the online community (not enterprise support)
- Either graduate to official products or get deprecated with source available

**Key distinction**: Labs projects are experimental and community-supported, unlike official Neo4j products.

## Brand Positioning

### Tagline
> Incubating the Next Generation of Graph Developer Tooling

### Voice & Tone

| Attribute | Labs Tone | vs. Official Neo4j |
|-----------|-----------|-------------------|
| Experimental | "Try it out, help us shape it" | "Production-ready" |
| Transparent | "APIs may change" | "Stable interfaces" |
| Community-first | "Join the discussion" | "Contact support" |
| Approachable | "Rough around the edges" | "Enterprise-grade" |
| Collaborative | "PRs welcome!" | "Licensed product" |

### Messaging Guidelines

**DO say:**
- "Labs project" or "Neo4j Labs project"
- "Community-supported"
- "Actively maintained"
- "May graduate to official support"
- "APIs may change"
- "Experimental functionality"

**DON'T say:**
- "Production-ready" (unless graduated)
- "Officially supported"
- "Enterprise support available"
- "SLA guaranteed"

## Visual Identity

### Primary Color: Innovation Purple

Labs uses purple as its primary accent to differentiate from Neo4j's Baltic teal while suggesting innovation and experimentation.

```
Labs Purple:     #6366F1 (primary accent)
Labs Purple Dark: #4F46E5 (hover/active states)
Labs Purple Light: #A5B4FC (backgrounds)
```

### Secondary Colors (Neo4j Palette)

Maintain connection to Neo4j brand:

```
Neo4j Teal:      #009999 (links, secondary accent)
Text Dark:       #1E1E1E
Text Gray:       #6B7280
Background:      #F9FAFB (light gray)
White:           #FFFFFF
```

### Status Colors

```
Experimental:    #F59E0B (amber/orange)
Beta:            #6366F1 (purple)
Stable:          #10B981 (green)
Deprecated:      #EF4444 (red)
Graduated:       #009999 (neo4j teal)
```

## Project Lifecycle Badges

Every Labs project should display its status clearly.

### Badge Styles

```markdown
![Labs Project](https://img.shields.io/badge/Neo4j-Labs-6366F1?logo=neo4j)
![Status: Experimental](https://img.shields.io/badge/Status-Experimental-F59E0B)
![Status: Beta](https://img.shields.io/badge/Status-Beta-6366F1)
![Status: Stable](https://img.shields.io/badge/Status-Stable-10B981)
![Status: Deprecated](https://img.shields.io/badge/Status-Deprecated-EF4444)
![Community Supported](https://img.shields.io/badge/Support-Community-6B7280)
```

### Status Definitions

| Status | Description | Badge Color |
|--------|-------------|-------------|
| **Experimental** | Early development, APIs will change | Amber `#F59E0B` |
| **Beta** | Feature complete, gathering feedback | Purple `#6366F1` |
| **Stable** | Ready for production use (with Labs caveats) | Green `#10B981` |
| **Deprecated** | No longer maintained, source available | Red `#EF4444` |
| **Graduated** | Moved to official Neo4j product | Teal `#009999` |

## Documentation Template

### README Structure

```markdown
# Project Name

![Neo4j Labs](badge) ![Status](badge) ![Community Supported](badge)

> One-line description of what this project does.

⚠️ **This is a Neo4j Labs project.** It is actively maintained but not officially 
supported. APIs may change. Community support available via 
[Neo4j Community](https://community.neo4j.com).

## Features

- Feature 1
- Feature 2

## Quick Start

[Installation and basic usage]

## Documentation

[Link to full docs]

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## Support

- 💬 [Neo4j Community Forum](https://community.neo4j.com)
- 🐛 [GitHub Issues](link)
- 📖 [Documentation](link)

## License

[License info]
```

### Required Disclaimer

Every Labs project must include this disclaimer prominently:

> ⚠️ **Neo4j Labs Project**
> 
> This project is part of Neo4j Labs and is actively maintained, but not officially 
> supported. There are no SLAs or guarantees around backwards compatibility and 
> deprecation. For questions and support, please use the 
> [Neo4j Community Forum](https://community.neo4j.com).

## Typography

### Font Stack

```css
/* Headings - use Syne Neo where available, fallback to system */
font-family: 'Syne', system-ui, -apple-system, sans-serif;

/* Body - Public Sans or system fallback */
font-family: 'Public Sans', system-ui, -apple-system, sans-serif;

/* Code - monospace */
font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
```

### Heading Styles

- **H1**: Project name only, large and bold
- **H2**: Section headers with emoji icons encouraged
- **H3**: Subsections
- Use sentence case for headings (not Title Case)

## Iconography

### Recommended Emoji Usage

```
🧪 Experimental features
🚀 Getting started / Quick start
📖 Documentation
💬 Community / Discussion
🐛 Bug reports / Issues
🤝 Contributing
⚠️ Warnings / Caveats
✨ New features
🔧 Configuration
📦 Installation
```

### Logo Usage

Labs projects should NOT create custom logos. Use:
1. The Neo4j logo with "Labs" badge
2. Text-only project name
3. GitHub repository social preview with Labs branding

## Diagram Style

When creating diagrams for Labs projects:

### Colors
```
Primary shapes:    #6366F1 (Labs purple)
Secondary shapes:  #009999 (Neo4j teal)
Neutral shapes:    #E5E7EB (light gray)
Text:              #1E1E1E (dark)
Arrows/lines:      #6B7280 (gray)
```

### Style Guidelines
- Use hand-drawn/sketch style (roughness: 1-2) for approachable feel
- Rounded corners on rectangles
- Clear labels on all components
- Include "Labs" badge in architecture diagrams

## GitHub Repository Standards

### Repository Settings

- **Description**: Start with "Neo4j Labs:" prefix
- **Topics**: Include `neo4j`, `neo4j-labs`, relevant tech tags
- **About section**: Link to neo4j.com/labs/[project]

### Social Preview

Create a social preview image (1280x640px) with:
- Labs purple gradient background
- Project name in white
- "Neo4j Labs" badge
- Simple icon or diagram representing functionality

### Issue/PR Templates

Include Labs-specific templates that:
- Remind contributors this is a Labs project
- Link to community forum for support questions
- Thank contributors for helping improve the project

## Presentation Slides

### Slide Template

- **Background**: White or very light gray (#F9FAFB)
- **Accent color**: Labs purple (#6366F1)
- **Header**: Include "Neo4j Labs" identifier
- **Footer**: Project name, GitHub URL, community link

### Required Slides

1. **Title slide**: Project name + "A Neo4j Labs Project"
2. **Disclaimer slide**: Labs support model explanation
3. **Community slide**: How to get help, contribute

## Current Labs Projects Reference

Active projects (as of 2025):
- GenAI Ecosystem (LangChain, LlamaIndex, Haystack integrations)
- LLM Knowledge Graph Builder
- MCP Servers
- arrows.app
- APOC Extended
- NeoDash
- Neosemantics (RDF/Linked Data)
- Neo4j Migrations
- Needle Starter Kit
- Cypher Workbench
- neomodel (Python OGM)

Graduated to official:
- Graph Data Science Library
- Neo4j Connector for Apache Kafka
- Neo4j Connector for Apache Spark
- Neo4j Docker Container
- GraphQL Library
- Aura CLI

## Quick Reference Card

```
COLORS
──────────────────────────────
Labs Purple:      #6366F1
Labs Purple Dark: #4F46E5
Neo4j Teal:       #009999
Status Amber:     #F59E0B
Status Green:     #10B981
Status Red:       #EF4444
Text Dark:        #1E1E1E
Text Gray:        #6B7280

TONE
──────────────────────────────
✓ Experimental, transparent
✓ Community-first, collaborative
✓ Approachable, helpful
✗ Not "production-ready"
✗ Not "officially supported"

REQUIRED ELEMENTS
──────────────────────────────
☐ Labs badge in README
☐ Status badge (experimental/beta/stable)
☐ Community support badge
☐ Disclaimer paragraph
☐ Link to community forum
☐ Contributing guidelines
```

## Resources

- **Neo4j Labs Homepage**: https://neo4j.com/labs/
- **Community Forum**: https://community.neo4j.com
- **GitHub Organization**: https://github.com/neo4j-labs
- **Needle Design System**: https://neo4j.design
- **Neo4j Brand Guidelines**: Reference `neo4j-styleguide` skill
