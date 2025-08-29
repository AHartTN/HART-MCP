import argparse
import json
import sys

import requests


def main():
    parser = argparse.ArgumentParser(
        description="Hartonomous CLI client for MCP server."
    )
    parser.add_argument("prompt", type=str, help="The mission prompt for the agent.")
    parser.add_argument(
        "--host", type=str, default="http://127.0.0.1", help="The MCP server host."
    )
    parser.add_argument("--port", type=int, default=8000, help="The MCP server port.")
    parser.add_argument(
        "--agent_id", type=int, default=1, help="The agent ID to use for the mission."
    )

    args = parser.parse_args()

    server_url = f"{args.host}:{args.port}"
    mcp_url = f"{server_url}/mcp"

    print(f"Sending mission to {mcp_url}...")

    try:
        # Step 1: Send the mission prompt to /mcp endpoint
        response = requests.post(
            mcp_url,
            json={"query": args.prompt, "agent_id": args.agent_id},
            timeout=300,  # Increased timeout for potentially long-running missions
        )
        response.raise_for_status()
        mission_data = response.json()
        mission_id = mission_data.get("mission_id")

        if not mission_id:
            print("Error: No mission_id received from the server.")
            return

        print(f"Mission started with ID: {mission_id}")
        stream_url = f"{server_url}/stream/{mission_id}"
        print(f"Connecting to stream at {stream_url}...")

        # Step 2: Connect to the streaming endpoint
        with requests.get(stream_url, stream=True) as stream_response:
            stream_response.raise_for_status()
            for line in stream_response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data: "):
                        try:
                            message = json.loads(decoded_line[len("data: ") :])
                            # Basic color coding for different message types
                            if "status" in message and message["status"] == "completed":
                                print(
                                    f"\033[92m{json.dumps(message, indent=2)}\033[0m"
                                )  # Green for completion
                            elif "error" in message:
                                print(
                                    f"\033[91m{json.dumps(message, indent=2)}\033[0m"
                                )  # Red for errors
                            else:
                                print(json.dumps(message, indent=2))  # Default
                            sys.stdout.flush()
                        except json.JSONDecodeError:
                            print(f"Received non-JSON data: {decoded_line}")
                    else:
                        print(decoded_line)

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
