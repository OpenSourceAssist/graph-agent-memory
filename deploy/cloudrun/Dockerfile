# Neo4j Agent Memory MCP Server
# Cloud Run deployment image
#
# Build:
#   docker build -t neo4j-memory-mcp .
#
# Run locally:
#   docker run -p 8080:8080 \
#     -e NEO4J_URI=bolt://host.docker.internal:7687 \
#     -e NEO4J_USER=neo4j \
#     -e NEO4J_PASSWORD=password \
#     neo4j-memory-mcp

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package with MCP and Google dependencies
RUN pip install --no-cache-dir -e ".[mcp,google]"

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the MCP server via the installed CLI entry point
CMD ["neo4j-memory", "mcp", "serve", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]
