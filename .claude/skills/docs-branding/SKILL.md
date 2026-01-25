---
name: neo4j-styleguide
description: Ensure consistency with Neo4j brand guidelines, Needle design system, and Cypher code style conventions. Use when creating Neo4j documentation, diagrams, presentations, Cypher queries, code examples, or any content that should align with Neo4j's visual identity and coding standards. Reference https://neo4j.design for the Needle design system.
---

# Neo4j Style Guide

Ensure consistency with Neo4j brand identity, the Needle design system, and Cypher coding conventions.

## Brand Colors

### Primary: Baltic (Blue-Green Teal)

The primary color is inspired by the Baltic Sea, combining calmness of blue with refreshing green qualities. It has both cool and warm undertones.

```
Primary Teal:    #018BFF (bright blue), #009999 (teal), #00C1B6 (cyan)
```

### Secondary Palette (Nature-Inspired)

```
Green:           #2F9E44 (forest), #B2F2BB (light green)
Orange:          #F79767 (warm orange), #FFEC99 (light yellow)
Red:             #E03131 (alert red), #FFC9C9 (light red)
Purple:          #C990C0 (node purple), #D0BFFF (light purple)
Pink:            #DA7194 (relationship pink)
```

### Neutral Colors

```
Dark:            #1E1E1E (text black)
Gray:            #A5ABB6 (default node/relationship)
Light:           #F3F3F0 (background)
White:           #FFFFFF
```

## Typography

### Font Families

| Use Case | Font | Notes |
|----------|------|-------|
| Display/Headings | **Syne Neo** | Modified Syne with circular dots (not squares) in periods, tittles. Rounded 'g' descender. |
| Body Text | **Public Sans** | Narrow structure, high legibility, good contrast to Syne |
| Code/Monospace | **Letter Gothic** | For code samples, Cypher queries, technical content |

### Typography Guidelines

- Use Syne Neo sparingly for headlines and display text
- Public Sans for all body copy and UI text
- Code blocks always use monospace font
- Ensure adequate contrast for accessibility

## Node Shape Language

Neo4j uses organic, fluid node shapes based on a hexagonal grid:

- **Circles/Ellipses** for entity nodes
- **Rounded rectangles** for containers/components
- Avoid rigid, angular shapes
- Shapes should feel interconnected and organic

## Cypher Code Style

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Keywords | UPPERCASE | `MATCH`, `RETURN`, `CREATE`, `WHERE` |
| Node Labels | UpperCamelCase | `:Person`, `:Movie`, `:Organization` |
| Relationship Types | UPPER_SNAKE_CASE | `:ACTED_IN`, `:WORKS_AT`, `:KNOWS` |
| Properties | lowerCamelCase | `firstName`, `dateCreated`, `isActive` |
| Variables | lowercase | `n`, `m`, `p`, `person`, `movie` |
| Null/Boolean | lowercase | `null`, `true`, `false` |

### Formatting Rules

```cypher
// Keywords uppercase, proper spacing
MATCH (p:Person {name: 'Alice'})-[:KNOWS]->(friend:Person)
WHERE friend.age > 30
RETURN friend.name AS name, friend.age AS age
ORDER BY friend.age DESC
```

**Key rules:**
- No space in label predicates: `(n:Label)` not `(n: Label)`
- Space after commas in lists
- No padding in function calls: `count(n)` not `count( n )`
- Break long patterns after arrows, not before
- Use anonymous nodes when variable not needed: `()-->(n:Movie)`
- Chain patterns to avoid repeating variables

### File Extension

Use `.cypher` for Cypher query files.

## Documentation Writing

### In Prose References

When referencing Cypher constructs in documentation:

- Labels with colon: `:Person`, `:Movie`
- Relationship types with colon: `:ACTED_IN`, `:KNOWS`
- Functions with parentheses: `count()`, `toString()`, `collect()`
- Use monospace/code font for all Cypher elements
- Use `cypherfmt` (Neo4j VS Code Extension) for formatting

### Code Examples

Always include:
- Proper syntax highlighting
- Realistic, meaningful sample data
- Comments explaining non-obvious patterns

## Graph Visualization Colors

Default node label colors for Neo4j Browser/Bloom:

```css
node {
  color: #A5ABB6;        /* default gray */
  border-color: #9AA1AC;
  text-color-internal: #FFFFFF;
}

node.Person {
  color: #DA7194;        /* pink */
  border-color: #CC3C6C;
}

node.Movie {
  color: #C990C0;        /* purple */
  border-color: #B261A5;
}

node.Organization {
  color: #F79767;        /* orange */
  border-color: #F36924;
}

relationship {
  color: #A5ABB6;
  shaft-width: 1px;
}
```

## Diagram Guidelines

When creating diagrams for Neo4j content:

1. **Use organic shapes** - circles for nodes, curved arrows for relationships
2. **Apply brand colors** - use the Baltic teal as primary accent
3. **Show relationships clearly** - arrows with type labels
4. **Include properties** - show key properties inside node shapes
5. **Maintain whitespace** - don't overcrowd diagrams

### Excalidraw Integration

When using the excalidraw skill for Neo4j diagrams:
- Use `#009999` (teal) for primary/highlighted nodes
- Use `#A5ABB6` (gray) for secondary nodes
- Use distinct colors for different node labels
- Label relationships in UPPER_SNAKE_CASE
- Use hand-drawn style (roughness: 1) for approachable feel

## AI-Generated Illustrations

Neo4j has specific guidelines for AI-generated artwork:
- Define a consistent illustration style
- Use the brand color palette in prompts
- Avoid generic AI aesthetics
- Maintain organic, nature-inspired themes
- Focus on connections and relationships

## Quick Reference

```
Primary:     #009999 (Baltic teal)
Accent:      #00C1B6 (cyan)
Text:        #1E1E1E (dark)
Background:  #F3F3F0 (light)

Display:     Syne Neo
Body:        Public Sans  
Code:        Letter Gothic

Labels:      UpperCamelCase (:Person)
Rel Types:   UPPER_SNAKE_CASE (:WORKS_AT)
Properties:  lowerCamelCase (firstName)
Keywords:    UPPERCASE (MATCH, RETURN)
```

## Resources

- **Needle Design System**: https://neo4j.design
- **Cypher Style Guide**: https://neo4j.com/docs/cypher-manual/current/styleguide/
- **Naming Conventions**: https://neo4j.com/docs/cypher-manual/current/syntax/naming/
- **Browser Styling**: https://neo4j.com/docs/browser-manual/current/operations/browser-styling/
