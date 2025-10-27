"""Unit tests for OpenAI <-> Claude SDK translation layer."""

import pytest
import json
import re
from agcluster.container.core.translator import (
    generate_completion_id,
    claude_message_to_openai_text,
    stream_to_openai_sse,
    create_openai_completion_response,
)


@pytest.mark.unit
class TestGenerateCompletionId:
    """Test completion ID generation."""

    def test_id_format(self):
        """Test that completion ID follows OpenAI format."""
        completion_id = generate_completion_id()
        assert completion_id.startswith("chatcmpl-")
        assert len(completion_id) == 21  # chatcmpl- (9) + 12 hex chars

    def test_id_uniqueness(self):
        """Test that generated IDs are unique."""
        ids = {generate_completion_id() for _ in range(100)}
        assert len(ids) == 100  # All unique

    def test_id_hex_characters(self):
        """Test that ID suffix contains only hex characters."""
        completion_id = generate_completion_id()
        suffix = completion_id[9:]  # Remove "chatcmpl-"
        assert re.match(r"^[0-9a-f]{12}$", suffix)


@pytest.mark.unit
class TestClaudeMessageToOpenAIText:
    """Test extraction of text from Claude SDK messages."""

    def test_extract_message_content(self):
        """Test extracting content from normal message."""
        message = {"type": "message", "data": {"content": "Hello, world!"}}
        result = claude_message_to_openai_text(message)
        assert result == "Hello, world!"

    def test_extract_empty_content(self):
        """Test extracting empty content."""
        message = {"type": "message", "data": {"content": ""}}
        result = claude_message_to_openai_text(message)
        assert result == ""

    def test_extract_missing_content_field(self):
        """Test handling message with missing content field."""
        message = {"type": "message", "data": {}}
        result = claude_message_to_openai_text(message)
        assert result == ""

    def test_extract_missing_data_field(self):
        """Test handling message with missing data field."""
        message = {"type": "message"}
        result = claude_message_to_openai_text(message)
        assert result == ""

    def test_extract_error_message(self):
        """Test extracting error message."""
        message = {"type": "error", "message": "Something went wrong"}
        result = claude_message_to_openai_text(message)
        assert result == "[Error: Something went wrong]"

    def test_extract_error_without_message(self):
        """Test error without message field."""
        message = {"type": "error"}
        result = claude_message_to_openai_text(message)
        assert result == "[Error: Unknown error]"

    def test_unknown_message_type(self):
        """Test handling unknown message type."""
        message = {"type": "unknown", "data": {"content": "test"}}
        result = claude_message_to_openai_text(message)
        assert result == ""

    def test_empty_message(self):
        """Test handling empty message dict."""
        result = claude_message_to_openai_text({})
        assert result == ""


@pytest.mark.unit
class TestStreamToOpenAISSE:
    """Test streaming conversion to OpenAI SSE format."""

    async def test_single_message_stream(self):
        """Test converting single message to SSE."""

        async def mock_stream():
            yield {"type": "message", "data": {"type": "content", "content": "Hello"}}
            yield {"type": "complete", "status": "success"}

        chunks = []
        async for chunk in stream_to_openai_sse(mock_stream(), "claude-sonnet-4.5"):
            chunks.append(chunk)

        # Should have 3 chunks: message, finish, [DONE]
        assert len(chunks) == 3
        assert chunks[0].startswith("data: ")
        assert chunks[2] == "data: [DONE]\n\n"

        # Parse first chunk
        first_data = json.loads(chunks[0][6:-2])  # Remove "data: " and "\n\n"
        assert first_data["object"] == "chat.completion.chunk"
        assert first_data["model"] == "claude-sonnet-4.5"
        assert first_data["choices"][0]["delta"]["content"] == "Hello"
        assert first_data["choices"][0]["finish_reason"] is None

        # Parse finish chunk
        finish_data = json.loads(chunks[1][6:-2])
        assert finish_data["choices"][0]["finish_reason"] == "stop"
        assert finish_data["choices"][0]["delta"] == {}

    async def test_multiple_messages_stream(self):
        """Test streaming multiple messages."""

        async def mock_stream():
            yield {"type": "message", "data": {"type": "content", "content": "Hello"}}
            yield {"type": "message", "data": {"type": "content", "content": " world"}}
            yield {"type": "message", "data": {"type": "content", "content": "!"}}
            yield {"type": "complete", "status": "success"}

        chunks = []
        async for chunk in stream_to_openai_sse(mock_stream(), "claude-sonnet-4.5"):
            chunks.append(chunk)

        # Should have 5 chunks: 3 messages + finish + [DONE]
        assert len(chunks) == 5

        # All chunks should use same completion_id
        ids = set()
        for chunk in chunks[:-1]:  # Exclude [DONE]
            data = json.loads(chunk[6:-2])
            ids.add(data["id"])
        assert len(ids) == 1  # All same ID

    async def test_empty_content_messages_skipped(self):
        """Test that messages with empty content are skipped."""

        async def mock_stream():
            yield {"type": "message", "data": {"type": "content", "content": ""}}
            yield {"type": "message", "data": {"type": "content", "content": "Hello"}}
            yield {"type": "message", "data": {"type": "content"}}
            yield {"type": "complete", "status": "success"}

        chunks = []
        async for chunk in stream_to_openai_sse(mock_stream(), "claude-sonnet-4.5"):
            chunks.append(chunk)

        # Should have 3 chunks: 1 message (not 3) + finish + [DONE]
        assert len(chunks) == 3

    async def test_error_in_stream(self):
        """Test handling error message in stream."""

        async def mock_stream():
            yield {"type": "message", "data": {"type": "content", "content": "Starting..."}}
            yield {"type": "error", "message": "Connection lost"}

        chunks = []
        async for chunk in stream_to_openai_sse(mock_stream(), "claude-sonnet-4.5"):
            chunks.append(chunk)

        # Should have 3 chunks: message + error + [DONE]
        assert len(chunks) == 3

        # Parse error chunk
        error_data = json.loads(chunks[1][6:-2])
        assert error_data["choices"][0]["finish_reason"] == "error"
        assert "[Error: Connection lost]" in error_data["choices"][0]["delta"]["content"]

    async def test_sse_format_compliance(self):
        """Test that SSE format matches OpenAI spec."""

        async def mock_stream():
            yield {"type": "message", "data": {"type": "content", "content": "Test"}}
            yield {"type": "complete", "status": "success"}

        chunks = []
        async for chunk in stream_to_openai_sse(mock_stream(), "claude-sonnet-4.5"):
            chunks.append(chunk)

        # All chunks except [DONE] should be valid JSON with "data: " prefix
        for chunk in chunks[:-1]:
            assert chunk.startswith("data: ")
            assert chunk.endswith("\n\n")
            json_str = chunk[6:-2]  # Remove "data: " and "\n\n"
            data = json.loads(json_str)
            assert "id" in data
            assert "object" in data
            assert "created" in data
            assert "model" in data
            assert "choices" in data


@pytest.mark.unit
class TestCreateOpenAICompletionResponse:
    """Test non-streaming OpenAI response creation."""

    def test_basic_response_structure(self):
        """Test basic response structure."""
        response = create_openai_completion_response("Hello, world!", "claude-sonnet-4.5")

        assert response["object"] == "chat.completion"
        assert response["model"] == "claude-sonnet-4.5"
        assert "id" in response
        assert response["id"].startswith("chatcmpl-")
        assert "created" in response
        assert isinstance(response["created"], int)

    def test_response_choices(self):
        """Test choices array in response."""
        response = create_openai_completion_response("Test content", "claude-sonnet-4.5")

        assert len(response["choices"]) == 1
        choice = response["choices"][0]
        assert choice["index"] == 0
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] == "Test content"
        assert choice["finish_reason"] == "stop"

    def test_response_usage(self):
        """Test usage field (should be zeros for MVP)."""
        response = create_openai_completion_response("Test", "claude-sonnet-4.5")

        assert "usage" in response
        assert response["usage"]["prompt_tokens"] == 0
        assert response["usage"]["completion_tokens"] == 0
        assert response["usage"]["total_tokens"] == 0

    def test_empty_content(self):
        """Test response with empty content."""
        response = create_openai_completion_response("", "claude-sonnet-4.5")

        assert response["choices"][0]["message"]["content"] == ""
        assert response["choices"][0]["finish_reason"] == "stop"

    def test_multiline_content(self):
        """Test response with multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        response = create_openai_completion_response(content, "claude-sonnet-4.5")

        assert response["choices"][0]["message"]["content"] == content
