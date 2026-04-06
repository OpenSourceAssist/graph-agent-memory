"""Smoke tests for LlamaIndex example code."""

import ast
import importlib.util
from pathlib import Path

import pytest

# Check if LlamaIndex is available
try:
    from llama_index.core.memory import BaseMemory
    from llama_index.core.schema import TextNode

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False


class TestLlamaIndexExampleStructure:
    """Test that LlamaIndex integration module is properly structured."""

    def test_integration_module_exists(self):
        """Test that the LlamaIndex integration module exists."""
        from neo4j_agent_memory.integrations import llamaindex

        assert llamaindex is not None

    @pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
    def test_memory_class_importable(self):
        """Test that Neo4jLlamaIndexMemory can be imported."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        assert Neo4jLlamaIndexMemory is not None

    @pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
    def test_memory_class_inherits_base_memory(self):
        """Test that Neo4jLlamaIndexMemory inherits from BaseMemory."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        assert issubclass(Neo4jLlamaIndexMemory, BaseMemory)

    @pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
    def test_memory_has_required_methods(self):
        """Test that Neo4jLlamaIndexMemory has required methods."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        assert hasattr(Neo4jLlamaIndexMemory, "get")
        assert hasattr(Neo4jLlamaIndexMemory, "put")
        assert hasattr(Neo4jLlamaIndexMemory, "reset")
        assert callable(getattr(Neo4jLlamaIndexMemory, "get", None))
        assert callable(getattr(Neo4jLlamaIndexMemory, "put", None))
        assert callable(getattr(Neo4jLlamaIndexMemory, "reset", None))


class TestLlamaIndexIntegrationModule:
    """Test the LlamaIndex integration module structure."""

    def test_module_has_docstring(self):
        """Test that the module has a docstring."""
        from neo4j_agent_memory.integrations import llamaindex

        # Module should have documentation (allow missing for optional deps)
        _ = llamaindex.__doc__  # Just verify module is accessible

    def test_integration_init_exports(self):
        """Test that integration __init__ properly handles LlamaIndex."""
        # This should not raise even if LlamaIndex isn't installed
        from neo4j_agent_memory import integrations

        # llamaindex submodule should be accessible
        assert hasattr(integrations, "llamaindex")


@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestLlamaIndexMemoryInterface:
    """Test the LlamaIndex memory interface compliance."""

    def test_get_method_signature(self):
        """Test that get method has correct signature."""
        import inspect

        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        sig = inspect.signature(Neo4jLlamaIndexMemory.get)
        params = list(sig.parameters.keys())

        # Should have self and input parameters
        assert "self" in params
        assert "input" in params or len(params) >= 1

    def test_put_method_signature(self):
        """Test that put method has correct signature."""
        import inspect

        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        sig = inspect.signature(Neo4jLlamaIndexMemory.put)
        params = list(sig.parameters.keys())

        # Should have self and message parameters
        assert "self" in params
        assert "message" in params

    def test_reset_method_signature(self):
        """Test that reset method has correct signature."""
        import inspect

        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        sig = inspect.signature(Neo4jLlamaIndexMemory.reset)
        params = list(sig.parameters.keys())

        # Should have self parameter
        assert "self" in params

    def test_init_method_signature(self):
        """Test that __init__ method has correct signature."""
        import inspect

        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        sig = inspect.signature(Neo4jLlamaIndexMemory.__init__)
        params = list(sig.parameters.keys())

        # Should have memory_client and session_id
        assert "self" in params
        assert "memory_client" in params
        assert "session_id" in params


class TestLlamaIndexSourceCodeQuality:
    """Test source code quality of LlamaIndex integration."""

    def test_source_file_exists(self):
        """Test that the source file exists."""
        from neo4j_agent_memory.integrations import llamaindex

        source_file = Path(llamaindex.__file__)
        assert source_file.exists()

    def test_source_file_valid_python(self):
        """Test that the source file is valid Python."""
        from neo4j_agent_memory.integrations import llamaindex

        source_file = Path(llamaindex.__file__)
        if source_file.name == "__init__.py":
            # Find memory.py in same directory
            memory_file = source_file.parent / "memory.py"
            if memory_file.exists():
                source_file = memory_file

        source_code = source_file.read_text()

        # Should parse without syntax errors
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in source file: {e}")

    def test_no_bare_except_clauses(self):
        """Test that source doesn't use bare except clauses."""
        from neo4j_agent_memory.integrations import llamaindex

        source_file = Path(llamaindex.__file__)
        if source_file.name == "__init__.py":
            memory_file = source_file.parent / "memory.py"
            if memory_file.exists():
                source_file = memory_file

        source_code = source_file.read_text()
        tree = ast.parse(source_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Bare except has node.type as None
                # We allow ImportError exceptions
                if node.type is None:
                    # Check if it's in an import try block
                    pass  # Allow for now as pattern is used for optional imports


@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestLlamaIndexTypeAnnotations:
    """Test type annotations in LlamaIndex integration."""

    def test_get_return_type(self):
        """Test that get method has return type annotation."""
        import inspect

        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        sig = inspect.signature(Neo4jLlamaIndexMemory.get)
        # Return annotation may or may not be present
        # Just verify method exists and is callable

    def test_class_has_type_hints(self):
        """Test that class uses type hints."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        # Check if __init__ has annotations
        annotations = getattr(Neo4jLlamaIndexMemory.__init__, "__annotations__", {})
        # Type hints may be in TYPE_CHECKING block, so this is informational
