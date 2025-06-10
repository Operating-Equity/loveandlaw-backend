#!/usr/bin/env python3
"""
WebSocket health check script for CI/CD pipeline
"""
import asyncio
import sys
import json
import websockets
from websockets.exceptions import WebSocketException


async def test_websocket_connection(url: str, timeout: int = 30):
    """Test WebSocket connection and basic functionality"""
    try:
        async with websockets.connect(url, timeout=timeout) as websocket:
            print(f"Connected to {url}")
            
            # Send a test message
            test_message = {
                "type": "user_msg",
                "cid": "test-health-check",
                "text": "Health check test"
            }
            await websocket.send(json.dumps(test_message))
            print("Sent test message")
            
            # Wait for response
            response_received = False
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    print(f"Received: {data.get('type', 'unknown')}")
                    
                    if data.get('type') in ['ai_chunk', 'error', 'session_end']:
                        response_received = True
                        break
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    await websocket.send(json.dumps({"type": "heartbeat"}))
                except json.JSONDecodeError:
                    print(f"Received non-JSON message: {message}")
            
            if response_received:
                print("WebSocket health check passed")
                return 0
            else:
                print("No response received within timeout")
                return 1
                
    except WebSocketException as e:
        print(f"WebSocket connection failed: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test-websocket-health.py <websocket-url>")
        sys.exit(1)
    
    url = sys.argv[1]
    exit_code = asyncio.run(test_websocket_connection(url))
    sys.exit(exit_code)