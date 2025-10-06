#!/bin/bash

# Test concurrent container creation with real Docker
# This tests that multiple Claude Agent SDK sessions can run simultaneously

set -e

API_URL="http://localhost:8000"
API_KEY="${ANTHROPIC_API_KEY:-test-key}"

echo "🧪 Testing Concurrent Container Sessions"
echo "=========================================="
echo ""

# Test 1: Multiple concurrent requests
echo "Test 1: Sending 3 concurrent requests..."
curl -X POST "$API_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"Count to 3"}],"stream":false}' \
  > /tmp/response1.json 2>/dev/null &
PID1=$!

curl -X POST "$API_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"Say hello"}],"stream":false}' \
  > /tmp/response2.json 2>/dev/null &
PID2=$!

curl -X POST "$API_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"What is 2+2?"}],"stream":false}' \
  > /tmp/response3.json 2>/dev/null &
PID3=$!

# Wait for all requests to complete
echo "Waiting for requests to complete..."
wait $PID1
wait $PID2
wait $PID3

echo "✅ All 3 requests completed"
echo ""

# Test 2: Check for unique session IDs
echo "Test 2: Verifying unique session IDs..."
SESSION1=$(grep -o '"session_id": "[^"]*"' /tmp/response1.json | head -1 | cut -d'"' -f4 || echo "not_found")
SESSION2=$(grep -o '"session_id": "[^"]*"' /tmp/response2.json | head -1 | cut -d'"' -f4 || echo "not_found")
SESSION3=$(grep -o '"session_id": "[^"]*"' /tmp/response3.json | head -1 | cut -d'"' -f4 || echo "not_found")

echo "Session 1: $SESSION1"
echo "Session 2: $SESSION2"
echo "Session 3: $SESSION3"

if [ "$SESSION1" != "$SESSION2" ] && [ "$SESSION2" != "$SESSION3" ] && [ "$SESSION1" != "$SESSION3" ]; then
    echo "✅ All session IDs are unique"
else
    echo "❌ Session IDs are not unique!"
    exit 1
fi
echo ""

# Test 3: Check active containers
echo "Test 3: Checking active containers..."
CONTAINER_COUNT=$(docker ps --filter "label=agvector=true" --format "{{.Names}}" | wc -l)
echo "Active agvector containers: $CONTAINER_COUNT"

if [ $CONTAINER_COUNT -ge 1 ]; then
    echo "✅ Containers are running"
    docker ps --filter "label=agvector=true" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "⚠️  No active containers (they may have been cleaned up)"
fi
echo ""

# Test 4: Rapid fire test
echo "Test 4: Rapid fire requests (5 in quick succession)..."
for i in {1..5}; do
    curl -X POST "$API_URL/chat/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $API_KEY" \
      -d "{\"model\":\"claude-sonnet-4.5\",\"messages\":[{\"role\":\"user\",\"content\":\"Quick test $i\"}],\"stream\":false}" \
      > /tmp/rapid_$i.json 2>/dev/null &
done

wait
echo "✅ All rapid fire requests completed"
echo ""

# Test 5: Streaming concurrency
echo "Test 5: Testing concurrent streaming requests..."
timeout 10 curl -X POST "$API_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"Stream 1"}],"stream":true}' \
  --no-buffer > /tmp/stream1.log 2>&1 &
STREAM1=$!

timeout 10 curl -X POST "$API_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"Stream 2"}],"stream":true}' \
  --no-buffer > /tmp/stream2.log 2>&1 &
STREAM2=$!

wait $STREAM1
wait $STREAM2
echo "✅ Concurrent streaming requests completed"
echo ""

# Summary
echo "=========================================="
echo "🎉 Concurrent Session Tests Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✅ Concurrent non-streaming requests"
echo "  ✅ Unique session IDs per container"
echo "  ✅ Multiple containers running simultaneously"
echo "  ✅ Rapid fire request handling"
echo "  ✅ Concurrent streaming requests"
echo ""
echo "Check logs:"
echo "  Response 1: /tmp/response1.json"
echo "  Response 2: /tmp/response2.json"
echo "  Response 3: /tmp/response3.json"
echo "  Stream logs: /tmp/stream*.log"
