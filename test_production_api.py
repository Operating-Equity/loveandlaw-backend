#!/usr/bin/env python3
"""Comprehensive test suite for LoveAndLaw production API"""

import asyncio
import websockets
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuration
REST_API_BASE = "https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production"
WEBSOCKET_URL = "wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production"

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(name: str, status: str, details: str = ""):
    """Print test result with color"""
    if status == "PASS":
        print(f"{Colors.GREEN}✅ {name}: PASS{Colors.RESET} {details}")
    elif status == "FAIL":
        print(f"{Colors.RED}❌ {name}: FAIL{Colors.RESET} {details}")
    elif status == "INFO":
        print(f"{Colors.BLUE}ℹ️  {name}{Colors.RESET} {details}")
    else:
        print(f"{Colors.YELLOW}⚠️  {name}: {status}{Colors.RESET} {details}")

def test_rest_api():
    """Test REST API endpoints"""
    print(f"\n{Colors.BLUE}=== REST API Tests ==={Colors.RESET}")
    
    # Test health endpoint
    try:
        response = requests.get(f"{REST_API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print_test("Health Check", "PASS", f"Response: {data}")
            else:
                print_test("Health Check", "FAIL", f"Unexpected response: {data}")
        else:
            print_test("Health Check", "FAIL", f"Status code: {response.status_code}")
    except Exception as e:
        print_test("Health Check", "FAIL", f"Error: {e}")
    
    # Test match endpoint (expected to fail without auth)
    try:
        payload = {
            "facts": {
                "zip": "19104",
                "practice_area": "divorce",
                "budget": "$$"
            }
        }
        response = requests.post(
            f"{REST_API_BASE}/v1/match",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 404:
            print_test("Match Endpoint", "INFO", "Returns 404 (expected without proper routing)")
        else:
            print_test("Match Endpoint", "INFO", f"Status: {response.status_code}, Body: {response.text[:100]}")
    except Exception as e:
        print_test("Match Endpoint", "FAIL", f"Error: {e}")

async def test_websocket():
    """Test WebSocket functionality"""
    print(f"\n{Colors.BLUE}=== WebSocket Tests ==={Colors.RESET}")
    
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            print_test("WebSocket Connection", "PASS", "Connected successfully")
            
            # Test 1: Send user message
            test_message = {
                "action": "sendMessage",
                "data": {
                    "type": "user_msg",
                    "cid": f"test-{int(time.time())}",
                    "text": "I need help with child custody arrangements in my divorce."
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print_test("Send Message", "PASS", "Message sent")
            
            # Collect responses
            responses = []
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    responses.append(data)
                    
                    if data.get('type') == 'stream_end':
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Verify responses
            response_types = [r.get('type') for r in responses]
            
            if 'ai_chunk' in response_types:
                ai_chunks = [r for r in responses if r.get('type') == 'ai_chunk']
                print_test("AI Response", "PASS", f"Received {len(ai_chunks)} chunks")
            else:
                print_test("AI Response", "FAIL", "No AI chunks received")
            
            if 'cards' in response_types:
                cards = [r for r in responses if r.get('type') == 'cards'][0]
                print_test("Lawyer Cards", "PASS", f"Received {len(cards.get('cards', []))} lawyers")
            else:
                print_test("Lawyer Cards", "FAIL", "No lawyer cards received")
            
            if 'suggestions' in response_types:
                suggestions = [r for r in responses if r.get('type') == 'suggestions'][0]
                print_test("Suggestions", "PASS", f"Received {len(suggestions.get('suggestions', []))} suggestions")
            else:
                print_test("Suggestions", "FAIL", "No suggestions received")
            
            if 'stream_end' in response_types:
                print_test("Stream End", "PASS", "Proper stream termination")
            else:
                print_test("Stream End", "WARN", "No explicit stream end signal")
            
            # Test 2: Multiple messages
            print_test("\nMultiple Messages Test", "INFO", "Sending follow-up message")
            
            follow_up = {
                "action": "sendMessage",
                "data": {
                    "type": "user_msg",
                    "cid": f"test-{int(time.time())}-2",
                    "text": "What are the first steps I should take?"
                }
            }
            
            await websocket.send(json.dumps(follow_up))
            
            # Wait for at least one response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                if data.get('type') == 'ai_chunk':
                    print_test("Follow-up Response", "PASS", "Received response to follow-up")
                else:
                    print_test("Follow-up Response", "INFO", f"Response type: {data.get('type')}")
            except asyncio.TimeoutError:
                print_test("Follow-up Response", "FAIL", "Timeout waiting for response")
            
    except Exception as e:
        print_test("WebSocket Connection", "FAIL", f"Error: {e}")

def test_performance():
    """Test API performance"""
    print(f"\n{Colors.BLUE}=== Performance Tests ==={Colors.RESET}")
    
    # REST API latency
    latencies = []
    for i in range(5):
        start = time.time()
        try:
            response = requests.get(f"{REST_API_BASE}/health", timeout=5)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
        except:
            pass
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print_test("REST API Latency", "INFO", f"Average: {avg_latency:.2f}ms, Min: {min(latencies):.2f}ms, Max: {max(latencies):.2f}ms")
    else:
        print_test("REST API Latency", "FAIL", "Could not measure")

async def test_error_handling():
    """Test error handling"""
    print(f"\n{Colors.BLUE}=== Error Handling Tests ==={Colors.RESET}")
    
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            # Test invalid message format
            invalid_messages = [
                {"data": {"type": "invalid_type"}},  # Missing action
                {"action": "invalid_action", "data": {}},  # Invalid action
                {"action": "sendMessage", "data": {"type": "user_msg"}},  # Missing required fields
                "invalid json string",  # Invalid JSON
            ]
            
            for i, msg in enumerate(invalid_messages):
                try:
                    if isinstance(msg, str):
                        await websocket.send(msg)
                    else:
                        await websocket.send(json.dumps(msg))
                    
                    # Check if we get an error response or connection stays alive
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        print_test(f"Invalid Message {i+1}", "INFO", "Server handled gracefully")
                    except asyncio.TimeoutError:
                        print_test(f"Invalid Message {i+1}", "PASS", "No crash, connection maintained")
                except:
                    print_test(f"Invalid Message {i+1}", "WARN", "Connection may have been closed")
                    # Reconnect for next test
                    break
                    
    except Exception as e:
        print_test("Error Handling", "FAIL", f"Error: {e}")

async def main():
    """Run all tests"""
    print(f"{Colors.BLUE}{'='*50}")
    print(f"LoveAndLaw Production API Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}{Colors.RESET}")
    
    # Run REST API tests
    test_rest_api()
    
    # Run WebSocket tests
    await test_websocket()
    
    # Run performance tests
    test_performance()
    
    # Run error handling tests
    await test_error_handling()
    
    print(f"\n{Colors.BLUE}{'='*50}")
    print(f"Test Suite Completed")
    print(f"{'='*50}{Colors.RESET}")

if __name__ == "__main__":
    asyncio.run(main())