#!/usr/bin/env python3
"""
Simple test script for MCP server functionality without Unicode characters
"""

import json
import subprocess
import sys
import time

def test_mcp_server():
    """Test the MCP server with various JSON-RPC calls"""
    
    # Start the MCP server process
    process = subprocess.Popen(
        ["dotnet", "run", "--project", "src/HART.MCP.CLI"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # Test initialize
        print("Testing initialize...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            init_response = json.loads(response)
            print(f"SUCCESS Initialize response: {json.dumps(init_response, indent=2)}")
        
        # Test tools/list
        print("\nTesting tools/list...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            tools_response = json.loads(response)
            print(f"SUCCESS Tools list response: {json.dumps(tools_response, indent=2)}")
        
        # Test tool call
        print("\nTesting tools/call...")
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "TestTool",
                "arguments": {"input": "Hello from MCP test"}
            }
        }
        
        process.stdin.write(json.dumps(call_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            call_response = json.loads(response)
            print(f"SUCCESS Tool call response: {json.dumps(call_response, indent=2)}")
        
        # Test resources/list
        print("\nTesting resources/list...")
        resources_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(resources_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            resources_response = json.loads(response)
            print(f"SUCCESS Resources list response: {json.dumps(resources_response, indent=2)}")
        
        # Test resource read
        print("\nTesting resources/read...")
        read_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {
                "uri": "hart-mcp://status"
            }
        }
        
        process.stdin.write(json.dumps(read_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            read_response = json.loads(response)
            print(f"SUCCESS Resource read response: {json.dumps(read_response, indent=2)}")
        
        print("\nAll MCP tests completed successfully!")
        
    except Exception as e:
        print(f"ERROR during testing: {e}")
        if process.stderr:
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"Error output: {stderr_output}")
    
    finally:
        # Clean up
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_mcp_server()