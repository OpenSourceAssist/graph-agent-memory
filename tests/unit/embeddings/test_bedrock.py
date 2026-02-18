"""Unit tests for Amazon Bedrock embeddings."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBedrockEmbedder:
    """Tests for BedrockEmbedder class."""

    @pytest.fixture
    def mock_boto3(self):
        """Create a mock boto3 module."""
        with patch.dict("sys.modules", {"boto3": MagicMock()}):
            import boto3

            mock_client = MagicMock()
            mock_session = MagicMock()
            mock_session.client.return_value = mock_client
            boto3.Session.return_value = mock_session
            yield boto3, mock_client

    def test_embedder_initialization(self, mock_boto3):
        """Test embedder initializes with default values."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder()

        assert embedder._model == "amazon.titan-embed-text-v2:0"
        assert embedder._batch_size == 25
        assert embedder._normalize is True
        assert embedder._client is None  # Lazy initialization

    def test_embedder_initialization_with_custom_values(self, mock_boto3):
        """Test embedder initializes with custom values."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(
            model="amazon.titan-embed-text-v1",
            region_name="us-west-2",
            profile_name="my-profile",
            batch_size=10,
            normalize=False,
        )

        assert embedder._model == "amazon.titan-embed-text-v1"
        assert embedder._region_name == "us-west-2"
        assert embedder._profile_name == "my-profile"
        assert embedder._batch_size == 10
        assert embedder._normalize is False

    def test_dimensions_property_titan_v2(self, mock_boto3):
        """Test dimensions property for Titan V2 model."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="amazon.titan-embed-text-v2:0")
        assert embedder.dimensions == 1024

    def test_dimensions_property_titan_v1(self, mock_boto3):
        """Test dimensions property for Titan V1 model."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="amazon.titan-embed-text-v1")
        assert embedder.dimensions == 1536

    def test_dimensions_property_cohere(self, mock_boto3):
        """Test dimensions property for Cohere models."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="cohere.embed-english-v3")
        assert embedder.dimensions == 1024

        embedder = BedrockEmbedder(model="cohere.embed-multilingual-v3")
        assert embedder.dimensions == 1024

    def test_dimensions_property_unknown_model(self, mock_boto3):
        """Test dimensions property defaults to 1024 for unknown models."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="unknown-model")
        assert embedder.dimensions == 1024

    def test_ensure_client_initializes_boto3(self, mock_boto3):
        """Test _ensure_client initializes boto3 client."""
        boto3, mock_client = mock_boto3
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(
            region_name="us-west-2",
            profile_name="test-profile",
        )
        client = embedder._ensure_client()

        assert client is mock_client
        boto3.Session.assert_called_once_with(profile_name="test-profile")

    def test_ensure_client_caches_client(self, mock_boto3):
        """Test _ensure_client returns cached client on subsequent calls."""
        boto3, mock_client = mock_boto3
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder()
        client1 = embedder._ensure_client()
        client2 = embedder._ensure_client()

        assert client1 is client2
        # Session should only be called once
        assert boto3.Session.call_count == 1

    def test_build_request_body_titan(self, mock_boto3):
        """Test request body format for Titan models."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="amazon.titan-embed-text-v2:0", normalize=True)
        body = embedder._build_request_body("Hello world")
        parsed = json.loads(body)

        assert parsed["inputText"] == "Hello world"
        assert parsed["normalize"] is True

    def test_build_request_body_titan_no_normalize(self, mock_boto3):
        """Test request body format for Titan models without normalization."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="amazon.titan-embed-text-v2:0", normalize=False)
        body = embedder._build_request_body("Hello world")
        parsed = json.loads(body)

        assert parsed["inputText"] == "Hello world"
        assert "normalize" not in parsed

    def test_build_request_body_cohere(self, mock_boto3):
        """Test request body format for Cohere models."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="cohere.embed-english-v3")
        body = embedder._build_request_body("Hello world")
        parsed = json.loads(body)

        assert parsed["texts"] == ["Hello world"]
        assert parsed["input_type"] == "search_document"

    def test_parse_response_titan(self, mock_boto3):
        """Test response parsing for Titan models."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="amazon.titan-embed-text-v2:0")
        embedding = embedder._parse_response({"embedding": [0.1, 0.2, 0.3]})

        assert embedding == [0.1, 0.2, 0.3]

    def test_parse_response_cohere(self, mock_boto3):
        """Test response parsing for Cohere models."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(model="cohere.embed-english-v3")
        embedding = embedder._parse_response({"embeddings": [[0.1, 0.2, 0.3]]})

        assert embedding == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_single_text(self, mock_boto3):
        """Test embedding a single text."""
        boto3, mock_client = mock_boto3
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        # Set up mock response
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        mock_client.invoke_model.return_value = {"body": mock_response_body}

        embedder = BedrockEmbedder()
        embedding = await embedder.embed("Hello world")

        assert embedding == [0.1, 0.2, 0.3]
        mock_client.invoke_model.assert_called_once()
        call_kwargs = mock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "amazon.titan-embed-text-v2:0"

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self, mock_boto3):
        """Test batch embedding with empty list."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder()
        embeddings = await embedder.embed_batch([])

        assert embeddings == []

    @pytest.mark.asyncio
    async def test_embed_batch_multiple_texts(self, mock_boto3):
        """Test batch embedding with multiple texts."""
        boto3, mock_client = mock_boto3
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        # Set up mock responses
        responses = [
            {"embedding": [0.1, 0.2, 0.3]},
            {"embedding": [0.4, 0.5, 0.6]},
            {"embedding": [0.7, 0.8, 0.9]},
        ]
        call_count = [0]

        def mock_invoke(*args, **kwargs):
            mock_response_body = MagicMock()
            mock_response_body.read.return_value = json.dumps(responses[call_count[0]]).encode()
            call_count[0] += 1
            return {"body": mock_response_body}

        mock_client.invoke_model.side_effect = mock_invoke

        embedder = BedrockEmbedder()
        embeddings = await embedder.embed_batch(["text1", "text2", "text3"])

        assert len(embeddings) == 3
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        assert embeddings[2] == [0.7, 0.8, 0.9]

    def test_batch_size_capped_at_default(self, mock_boto3):
        """Test batch size is capped at default limit."""
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder(batch_size=100)
        assert embedder._batch_size == 25  # Capped at DEFAULT_BATCH_SIZE


class TestBedrockEmbedderErrors:
    """Tests for error handling in BedrockEmbedder."""

    def test_import_error_without_boto3(self):
        """Test EmbeddingError raised when boto3 not installed."""
        from neo4j_agent_memory.core.exceptions import EmbeddingError
        from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

        embedder = BedrockEmbedder()
        embedder._client = None
        embedder._boto3 = None

        # Mock import to simulate boto3 not being installed
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError("No module named 'boto3'")
            return real_import(name, *args, **kwargs)

        with (
            patch.object(builtins, "__import__", side_effect=mock_import),
            pytest.raises(EmbeddingError) as exc_info,
        ):
            embedder._ensure_client()

        assert "boto3 package not installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_error_handling(self):
        """Test embed raises EmbeddingError on failure."""
        with patch.dict("sys.modules", {"boto3": MagicMock()}):
            import boto3

            mock_client = MagicMock()
            mock_client.invoke_model.side_effect = Exception("API Error")
            mock_session = MagicMock()
            mock_session.client.return_value = mock_client
            boto3.Session.return_value = mock_session

            from neo4j_agent_memory.core.exceptions import EmbeddingError
            from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder

            embedder = BedrockEmbedder()

            with pytest.raises(EmbeddingError) as exc_info:
                await embedder.embed("test")

            assert "Failed to generate embedding" in str(exc_info.value)
