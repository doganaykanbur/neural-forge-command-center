import asyncio
import json
from nexus_bridge import NexusBridge

async def test_bridge_logic():
    bridge = NexusBridge(ollama_url="http://mock-ollama:11434")
    
    print("--- Test 1: Model Switching Logic ---")
    # Initial state
    print(f"Initial Role: {bridge.active_role}")
    
    # Switch to Architect
    await bridge.switch_model("architect")
    print(f"Switched to Architect: {bridge.loaded_model}")
    assert bridge.loaded_model == "mistral-nemo:12b"
    
    # Switch to Builder
    await bridge.switch_model("builder")
    print(f"Switched to Builder: {bridge.loaded_model}")
    assert bridge.loaded_model == "qwen2.5-coder:7b"
    
    print("\n--- Test 2: Anthropic-to-Ollama Translation ---")
    anthropic_req = {
        "model": "claude-3-5-sonnet",
        "messages": [
            {"role": "user", "content": "Hello, build me a website."}
        ],
        "system": "You are a senior engineer."
    }
    
    payload = bridge.prepare_ollama_payload(anthropic_req)
    print("Ollama Payload:")
    print(json.dumps(payload, indent=2))
    
    assert payload["model"] == "qwen2.5-coder:7b"
    assert payload["messages"][0]["role"] == "system"
    assert "senior engineer" in payload["messages"][0]["content"]
    assert payload["messages"][1]["role"] == "user"
    assert "website" in payload["messages"][1]["content"]

    print("\n--- Logic Test Passed! ---")

if __name__ == "__main__":
    asyncio.run(test_bridge_logic())
