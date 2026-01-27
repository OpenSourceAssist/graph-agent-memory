# Smart Shopping Assistant

A full-stack example application demonstrating Neo4j Agent Memory integration with Microsoft Agent Framework. This retail shopping assistant showcases graph-native memory capabilities including preference learning, graph-based recommendations, and memory visualization.

## Features

- **Preference Learning**: Automatically extracts and stores shopping preferences from conversation
- **Graph-Based Recommendations**: "Customers who bought X also bought Y" via graph traversals
- **Product Relationship Discovery**: Find related products through shared attributes, categories, brands
- **Inventory-Aware Suggestions**: Filter recommendations by real-time availability
- **Memory Graph Visualization**: Interactive visualization of the context graph powering recommendations
- **GDS Algorithm Integration**: PageRank for popular products, community detection for product grouping

## Architecture

```
Frontend (Next.js 14 + Chakra UI)
         ↓ SSE/REST
Backend (FastAPI + Microsoft Agent Framework)
         ↓
Neo4j Agent Memory
         ↓
Neo4j Database
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Neo4j 5.x (local or AuraDB)
- OpenAI API key (or Azure OpenAI)

## Quick Start

### 1. Set Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# Neo4j connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# OpenAI (or Azure OpenAI)
OPENAI_API_KEY=sk-your-key

# Or for Azure OpenAI:
# AZURE_OPENAI_API_KEY=your-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Load Sample Product Data

```bash
cd backend
python -m data.load_products
```

### 4. Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 6. Start the Frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:3000 in your browser.

## Example Conversations

Try these conversations to see the memory features in action:

1. **Preference Learning**:
   - "I'm looking for running shoes"
   - "I prefer Nike brand"
   - "My budget is under $150"
   - Later: "What shoes would you recommend?" (uses learned preferences)

2. **Graph-Based Recommendations**:
   - "Show me the Nike Air Max 90"
   - "What products are similar to this?"
   - "How is this related to running shoes?"

3. **Memory Recall**:
   - "What do you know about my preferences?"
   - "What products have we discussed?"

## Project Structure

```
microsoft_agent_retail_assistant/
├── backend/
│   ├── main.py              # FastAPI server with SSE streaming
│   ├── agent.py             # Microsoft Agent Framework agent
│   ├── memory_config.py     # Neo4j memory configuration
│   ├── tools/
│   │   ├── product_search.py    # Product catalog search
│   │   ├── recommendations.py   # Graph-based recommendations
│   │   ├── inventory.py         # Stock/availability checks
│   │   └── cart.py              # Shopping cart operations
│   ├── data/
│   │   └── load_products.py     # Sample data loader
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js 14 app router
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── ProductGraph.tsx
│   │   │   ├── PreferencePanel.tsx
│   │   │   ├── RecommendationCards.tsx
│   │   │   └── MemoryExplorer.tsx
│   │   └── lib/
│   │       └── api.ts
│   └── package.json
├── data/
│   └── sample_products.json
└── README.md
```

## Key Neo4j Features Demonstrated

### 1. Three-Layer Memory Architecture

- **Short-term**: Conversation history with semantic search
- **Long-term**: Product entities, user preferences, purchase patterns
- **Reasoning**: Past shopping assistance traces for learning

### 2. Graph Traversals

```cypher
// Find products similar to what user viewed
MATCH (p:Product {id: $productId})-[:IN_CATEGORY]->(c)<-[:IN_CATEGORY]-(similar)
WHERE similar <> p
RETURN similar, count(c) AS shared_categories
ORDER BY shared_categories DESC
LIMIT 5
```

### 3. GDS Algorithms (with fallback)

- **PageRank**: Identify popular/influential products
- **Community Detection**: Group related products
- **Shortest Path**: Explain product relationships

### 4. Hybrid Vector + Graph Search

```cypher
CALL db.index.vector.queryNodes('product_embedding', 10, $embedding)
YIELD node as p, score
MATCH (p)-[:IN_CATEGORY]->(c)
WHERE c.name = $preferredCategory
RETURN p, score
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send message, get streamed response |
| `/memory/context` | GET | Get current memory context |
| `/memory/graph` | GET | Get memory graph for visualization |
| `/memory/preferences` | GET | Get learned user preferences |
| `/products/search` | GET | Search product catalog |
| `/products/{id}` | GET | Get product details |
| `/products/{id}/related` | GET | Get related products |

## Microsoft Agent Framework Integration

This example demonstrates:

1. **Neo4jContextProvider**: Injects relevant memory context before each agent response
2. **Neo4jChatMessageStore**: Persists conversation history in Neo4j graph
3. **Memory Tools**: Search memory, save preferences, find similar past interactions
4. **GDS Integration**: Graph algorithms for enhanced recommendations

## License

Apache 2.0
