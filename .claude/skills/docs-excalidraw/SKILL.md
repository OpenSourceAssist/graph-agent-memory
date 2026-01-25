---
name: excalidraw
description: Generate Excalidraw JSON format diagrams for documentation, architecture diagrams, flowcharts, entity relationships, and visual explanations. Use when users request Excalidraw diagrams, .excalidraw files, visual diagrams for docs, architecture visualizations, flowcharts, or when converting ASCII art/placeholder diagrams to proper Excalidraw format.
---

# Excalidraw Diagram Generator

Generate valid Excalidraw JSON for diagrams that can be opened in Excalidraw, embedded in documentation, or used in Obsidian.

## JSON Schema Structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

## Element Types

### Base Properties (all elements)

```json
{
  "id": "unique-id",
  "type": "rectangle|ellipse|diamond|text|arrow|line",
  "x": 0,
  "y": 0,
  "width": 100,
  "height": 50,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "seed": 12345,
  "version": 1,
  "isDeleted": false,
  "groupIds": [],
  "frameId": null,
  "roundness": { "type": 3 },
  "boundElements": null
}
```

### Shape Elements: rectangle, ellipse, diamond

Use for boxes, containers, nodes. Diamond for decision points.

### Text Elements

```json
{
  "type": "text",
  "text": "Label",
  "fontSize": 20,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": null
}
```

`fontFamily`: 1=Virgil (hand-drawn), 2=Helvetica, 3=Cascadia (code)

### Linear Elements: arrow, line

```json
{
  "type": "arrow",
  "points": [[0, 0], [100, 0]],
  "startBinding": null,
  "endBinding": null,
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

`startArrowhead`/`endArrowhead`: null, "arrow", "bar", "dot", "triangle"

### Binding Arrows to Shapes

To connect arrows to shapes, use bindings:

```json
{
  "startBinding": {
    "elementId": "target-shape-id",
    "focus": 0,
    "gap": 5
  },
  "endBinding": {
    "elementId": "target-shape-id",
    "focus": 0,
    "gap": 5
  }
}
```

When binding, add `boundElements` to the target shape:
```json
{
  "boundElements": [
    { "id": "arrow-id", "type": "arrow" }
  ]
}
```

## Style Values

| Property | Values |
|----------|--------|
| fillStyle | "solid", "hachure", "cross-hatch" |
| strokeStyle | "solid", "dashed", "dotted" |
| roughness | 0 (architect), 1 (artist), 2 (cartoonist) |
| roundness.type | 2 (small radius), 3 (adaptive radius) |

## Color Palette

```
Stroke: #1e1e1e (black), #e03131 (red), #2f9e44 (green), #1971c2 (blue)
Background: transparent, #ffc9c9 (light red), #b2f2bb (light green), 
            #a5d8ff (light blue), #ffec99 (light yellow), #d0bfff (light purple)
```

## Generation Workflow

1. **Plan layout**: Sketch positions on a grid (increments of 50-100px)
2. **Create shapes first**: Generate all boxes/nodes with unique IDs
3. **Add text**: Create text elements, optionally bound to containers
4. **Add connections**: Create arrows with bindings to shape IDs
5. **Update boundElements**: Add arrow references to connected shapes

## ID Generation

Use descriptive IDs: `"memory-client-box"`, `"arrow-client-to-store"`, `"label-extraction"`

## Common Patterns

### Architecture Box with Label

```json
[
  {
    "id": "box-1",
    "type": "rectangle",
    "x": 100, "y": 100,
    "width": 200, "height": 80,
    "strokeColor": "#1e1e1e",
    "backgroundColor": "#a5d8ff",
    "fillStyle": "solid",
    "boundElements": [{ "id": "text-1", "type": "text" }]
  },
  {
    "id": "text-1",
    "type": "text",
    "x": 200, "y": 140,
    "text": "Component",
    "fontSize": 20,
    "textAlign": "center",
    "containerId": "box-1"
  }
]
```

### Connected Flowchart

See `references/examples.md` for complete flowchart and architecture examples.

## Output

Save as `.excalidraw` file (JSON with .excalidraw extension). Present to user for download.

## Replacing ASCII Placeholder Diagrams

When converting asciidoc placeholder diagrams like:
```
+------------------+
|   Component      |
+------------------+
```

Map to proper Excalidraw elements with appropriate sizing, colors, and connections.
