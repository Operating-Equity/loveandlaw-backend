#!/usr/bin/env python3
"""Test WebSocket and API connections"""

import asyncio
import json
import aiohttp
import websockets
from datetime import datetime


async def test_api():
    """Test REST API health check"""
    print("Testing REST API...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/') as response:
                data = await response.json()
                print(f"✓ API Health Check: {data}")
                return True
    except Exception as e:
        print(f"✗ API Error: {e}")
        return False


async def test_websocket():
    """Test WebSocket connection and chat"""
    print("\nTesting WebSocket...")
    try:
        uri = "ws://localhost:8001"
        async with websockets.connect(uri) as websocket:
            print(f"✓ Connected to WebSocket")
            
            # Receive connection message
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"✓ Received: {data['type']} - {data.get('message', '')}")
            
            # Authenticate
            auth_msg = {
                "type": "auth",
                "user_id": "test-user-123"
            }
            await websocket.send(json.dumps(auth_msg))
            print(f"→ Sent authentication")
            
            # Receive auth response
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"✓ Auth response: {data['type']}")
            
            # Send test message
            test_msg = {
                "type": "user_msg",
                "cid": "test-msg-1",
                "text": "I'm feeling overwhelmed about my divorce proceedings. I don't know where to start."
            }
            await websocket.send(json.dumps(test_msg))
            print(f"→ Sent test message")
            
            # Receive responses
            chunks = []
            metrics = None
            suggestions = None
            
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(msg)
                    
                    if data['type'] == 'message_received':
                        print(f"✓ Message acknowledged")
                    elif data['type'] == 'ai_chunk':
                        chunks.append(data['text_fragment'])
                        print(".", end="", flush=True)
                    elif data['type'] == 'ai_complete':
                        print(f"\n✓ Response complete")
                        full_response = "".join(chunks)
                        print(f"\nAssistant: {full_response}")
                    elif data['type'] == 'metrics':
                        metrics = data['metrics']
                        print(f"\n✓ Metrics: {metrics}")
                    elif data['type'] == 'suggestions':
                        suggestions = data['suggestions']
                        print(f"✓ Suggestions: {suggestions}")
                        break  # Last expected message
                    
                except asyncio.TimeoutError:
                    print("\n✓ No more messages (timeout)")
                    break
            
            return True
            
    except Exception as e:
        print(f"✗ WebSocket Error: {e}")
        return False


async def main():
    """Run all tests"""
    print("Love & Law Backend Connection Test")
    print("==================================")
    print(f"Timestamp: {datetime.now()}")
    
    # Test both services
    api_ok = await test_api()
    ws_ok = await test_websocket()
    
    print("\n" + "="*50)
    if api_ok and ws_ok:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        if not api_ok:
            print("  - REST API is not accessible")
        if not ws_ok:
            print("  - WebSocket service is not accessible")
    
    print("\nMake sure to:")
    print("1. Set up your .env file with API keys")
    print("2. Run 'python main.py' to start the servers")
    print("3. Servers run on ports 8000 (API) and 8001 (WebSocket)")


if __name__ == "__main__":
    asyncio.run(main())