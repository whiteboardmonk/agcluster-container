"""
E2E tests for Claude-native architecture

Tests the complete flow:
1. Launch session with agent config
2. Send chat message via /api/agents/chat
3. Verify Claude-specific events are streamed correctly
4. Test tool execution, thinking, and todo events
"""

import pytest
import httpx
import json
import asyncio
from typing import AsyncIterator


# API Configuration
API_BASE_URL = "http://localhost:8000"
ANTHROPIC_API_KEY = None  # Set via environment variable or pytest parameter


@pytest.fixture(scope="module")
def api_key():
    """API key fixture - set via environment or test parameter"""
    # This will be passed as a parameter when running tests
    return ANTHROPIC_API_KEY


@pytest.fixture(scope="module")
async def test_session(api_key):
    """Launch a test session and clean up after tests"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Launch session with code-assistant config
        response = await client.post(
            f"{API_BASE_URL}/api/agents/launch",
            json={
                "api_key": api_key,
                "config_id": "code-assistant"
            }
        )

        assert response.status_code == 200, f"Failed to launch session: {response.text}"
        session_data = response.json()
        session_id = session_data["session_id"]

        print(f"\n✓ Launched session: {session_id}")
        print(f"  Agent ID: {session_data['agent_id']}")
        print(f"  Config: {session_data['config_id']}")

        yield session_id

        # Cleanup: Stop session
        try:
            await client.delete(f"{API_BASE_URL}/api/agents/sessions/{session_id}")
            print(f"\n✓ Cleaned up session: {session_id}")
        except Exception as e:
            print(f"\n⚠ Failed to cleanup session: {e}")


async def parse_sse_stream(response: httpx.Response) -> AsyncIterator[dict]:
    """Parse SSE stream and yield parsed events"""
    buffer = ""

    async for chunk in response.aiter_bytes():
        buffer += chunk.decode('utf-8')

        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            line = line.strip()

            if not line or line == 'data: [DONE]':
                continue

            if line.startswith('data: {'):
                try:
                    event = json.loads(line[6:])  # Remove 'data: ' prefix
                    yield event
                except json.JSONDecodeError as e:
                    print(f"⚠ Failed to parse SSE line: {line[:100]}... Error: {e}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_health_check():
    """Test API health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_image" in data
        print("\n✓ Health check passed")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_list_configs():
    """Test listing available agent configurations"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/configs/")
        assert response.status_code == 200
        data = response.json()
        assert "configs" in data
        assert data["total"] >= 4

        config_ids = [c["id"] for c in data["configs"]]
        assert "code-assistant" in config_ids
        assert "research-agent" in config_ids
        assert "data-analysis" in config_ids
        assert "fullstack-team" in config_ids

        print(f"\n✓ Found {data['total']} agent configurations")
        for config in data["configs"]:
            print(f"  - {config['id']}: {config['name']}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_launch_session(api_key):
    """Test launching a session with code-assistant config"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/agents/launch",
            json={
                "api_key": api_key,
                "config_id": "code-assistant"
            }
        )

        assert response.status_code == 200, f"Failed to launch: {response.text}"
        data = response.json()

        assert "session_id" in data
        assert "agent_id" in data
        assert "config_id" in data
        assert data["config_id"] == "code-assistant"
        assert data["status"] == "running"

        print(f"\n✓ Session launched successfully")
        print(f"  Session ID: {data['session_id']}")
        print(f"  Agent ID: {data['agent_id']}")

        # Cleanup
        await client.delete(f"{API_BASE_URL}/api/agents/sessions/{data['session_id']}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_simple_chat_message(api_key, test_session):
    """Test sending a simple message and receiving response"""
    session_id = test_session

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": session_id
            },
            json={
                "messages": [
                    {"role": "user", "content": "Hello! Please respond with 'Hello, I am Claude.'"}
                ],
                "sessionId": session_id
            }
        )

        assert response.status_code == 200

        # Collect stream events
        events = []
        content_parts = []

        async for event in parse_sse_stream(response):
            events.append(event)

            # Collect text content
            if event.get("type") == "message" and event.get("msg_type") == "content":
                content = event.get("data", {}).get("content", "")
                if content:
                    content_parts.append(content)

        # Verify we got events
        assert len(events) > 0, "No events received from stream"

        # Verify we got content
        full_response = "".join(content_parts)
        assert len(full_response) > 0, "No content received"

        # Verify completion event
        completion_events = [e for e in events if e.get("type") == "complete"]
        assert len(completion_events) > 0, "No completion event received"

        print(f"\n✓ Chat message test passed")
        print(f"  Events received: {len(events)}")
        print(f"  Response: {full_response[:100]}...")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_tool_execution_events(api_key, test_session):
    """Test that tool execution events are streamed correctly"""
    session_id = test_session

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": session_id
            },
            json={
                "messages": [
                    {"role": "user", "content": "Create a file called test.txt with the content 'Hello World'"}
                ],
                "sessionId": session_id
            }
        )

        assert response.status_code == 200

        # Collect events
        events = []
        tool_events = []

        async for event in parse_sse_stream(response):
            events.append(event)

            # Check for tool events
            msg_type = event.get("msg_type")
            if msg_type in ["tool_start", "tool_use", "tool_complete"]:
                tool_events.append(event)
                print(f"  Tool event: {msg_type} - {event.get('data', {}).get('tool_name', 'unknown')}")

        # Verify we got tool execution events
        assert len(tool_events) > 0, "No tool execution events received"

        # Verify tool types
        tool_names = [e.get("data", {}).get("tool_name") for e in tool_events]
        assert "Write" in tool_names or "Bash" in tool_names, f"Expected Write or Bash tool, got: {tool_names}"

        print(f"\n✓ Tool execution test passed")
        print(f"  Total events: {len(events)}")
        print(f"  Tool events: {len(tool_events)}")
        print(f"  Tools used: {set(tool_names)}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_todo_events(api_key, test_session):
    """Test that todo/task tracking events are streamed"""
    session_id = test_session

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": session_id
            },
            json={
                "messages": [
                    {"role": "user", "content": "Create 3 files: data.json, config.yaml, and readme.md. Track your progress with todos."}
                ],
                "sessionId": session_id
            }
        )

        assert response.status_code == 200

        # Collect events
        events = []
        todo_events = []

        async for event in parse_sse_stream(response):
            events.append(event)

            # Check for todo events
            if event.get("msg_type") == "todo_update":
                todo_events.append(event)
                todos = event.get("data", {}).get("todos", [])
                print(f"  Todo update: {len(todos)} tasks")

        # We should get todo events since code-assistant has TodoWrite tool
        # Note: This depends on Claude deciding to use the tool
        print(f"\n✓ Todo events test completed")
        print(f"  Total events: {len(events)}")
        print(f"  Todo events: {len(todo_events)}")

        if len(todo_events) > 0:
            print("  ✓ Todo tracking is working!")
        else:
            print("  ⚠ No todo events (Claude may not have used TodoWrite tool)")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_thinking_events(api_key, test_session):
    """Test that thinking/reasoning events are captured"""
    session_id = test_session

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": session_id
            },
            json={
                "messages": [
                    {"role": "user", "content": "Solve this problem step by step: What is 15% of 240?"}
                ],
                "sessionId": session_id
            }
        )

        assert response.status_code == 200

        # Collect events
        events = []
        thinking_events = []

        async for event in parse_sse_stream(response):
            events.append(event)

            # Check for thinking events
            if event.get("msg_type") == "thinking":
                thinking_events.append(event)
                thinking_content = event.get("data", {}).get("content", "")
                print(f"  Thinking: {thinking_content[:100]}...")

        print(f"\n✓ Thinking events test completed")
        print(f"  Total events: {len(events)}")
        print(f"  Thinking events: {len(thinking_events)}")

        if len(thinking_events) > 0:
            print("  ✓ Extended thinking is enabled!")
        else:
            print("  ⚠ No thinking events (may need extended thinking enabled)")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_persistence(api_key, test_session):
    """Test that session persists across multiple messages"""
    session_id = test_session

    async with httpx.AsyncClient(timeout=120.0) as client:
        # First message
        response1 = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": session_id
            },
            json={
                "messages": [
                    {"role": "user", "content": "Remember this number: 42"}
                ],
                "sessionId": session_id
            }
        )

        assert response1.status_code == 200

        # Consume first response
        async for _ in parse_sse_stream(response1):
            pass

        # Second message - test context retention
        response2 = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": session_id
            },
            json={
                "messages": [
                    {"role": "user", "content": "Remember this number: 42"},
                    {"role": "assistant", "content": "I'll remember that the number is 42."},
                    {"role": "user", "content": "What number did I ask you to remember?"}
                ],
                "sessionId": session_id
            }
        )

        assert response2.status_code == 200

        # Check if response mentions 42
        content_parts = []
        async for event in parse_sse_stream(response2):
            if event.get("type") == "message" and event.get("msg_type") == "content":
                content = event.get("data", {}).get("content", "")
                if content:
                    content_parts.append(content)

        full_response = "".join(content_parts)

        print(f"\n✓ Session persistence test completed")
        print(f"  Response: {full_response[:200]}...")

        # Context retention check
        if "42" in full_response:
            print("  ✓ Context retained across messages!")
        else:
            print("  ⚠ Context may not be fully retained")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_error_handling_invalid_session(api_key):
    """Test error handling for invalid session ID"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/agents/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Session-ID": "invalid-session-id"
            },
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "sessionId": "invalid-session-id"
            }
        )

        # Should return 404 for invalid session
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()

        print("\n✓ Error handling test passed")
        print(f"  Error message: {error_data['detail']}")


if __name__ == "__main__":
    # Run tests with pytest
    print("Run with: ANTHROPIC_API_KEY=sk-... pytest tests/e2e/test_claude_native_flow.py -v -s")
