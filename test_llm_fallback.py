#!/usr/bin/env python3
"""
Test script for LLM fallback and local model functionality
Demonstrates automatic fallback from cloud to local models
"""

import asyncio
import os
from llm_connector import LLMClient
from config import OLLAMA_MODELS


async def test_model_switching():
    """Test switching between different model configurations."""
    
    print("=" * 60)
    print("🤖 HART-MCP LLM FALLBACK & LOCAL MODEL TEST")
    print("=" * 60)
    
    # Test 1: Show available models
    print("\n📋 AVAILABLE MODELS:")
    print("  Cloud Models:")
    print("    - Gemini 2.0 Flash (primary)")
    print("    - Claude Opus (fallback)")
    print("    - Llama via HuggingFace (fallback)")
    
    print("\n  Local Models (Ollama):")
    for model_name, info in OLLAMA_MODELS.items():
        print(f"    - {model_name}: {info['description']}")
    
    # Test 2: Current configuration
    print(f"\n⚙️  CURRENT CONFIG:")
    print(f"   Primary Source: {os.getenv('LLM_SOURCE', 'gemini')}")
    print(f"   Fallback Enabled: {os.getenv('LLM_FALLBACK_ENABLED', 'true')}")
    print(f"   Fallback Order: {os.getenv('LLM_FALLBACK_ORDER', 'gemini,ollama,claude,llama')}")
    print(f"   Ollama Model: {os.getenv('OLLAMA_MODEL_NAME', 'llama3:8b')}")
    
    # Test 3: Initialize client and show status
    print(f"\n🔧 INITIALIZING LLM CLIENT...")
    client = LLMClient()
    
    models_status = client.get_available_models()
    print("   Client Status:")
    for provider, info in models_status.items():
        status_icon = "✅" if info['status'] else "❌"
        print(f"   {status_icon} {provider}: {info['model']} ({info['type']})")
    
    # Test 4: Try a simple query
    print(f"\n💬 TESTING LLM INVOCATION:")
    try:
        response = await client.invoke("What is AI? Answer in one sentence.")
        print(f"   Response: {response[:100]}{'...' if len(response) > 100 else ''}")
        
        if client.failed_clients:
            print(f"   ⚠️  Failed clients: {list(client.failed_clients)}")
        else:
            print(f"   ✅ All attempted clients successful")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Model switching examples
    print(f"\n🔄 MODEL SWITCHING EXAMPLES:")
    print("   To use Qwen Coder locally:")
    print("   export OLLAMA_MODEL_NAME=qwen2.5-coder:7b")
    print("   export LLM_SOURCE=ollama")
    
    print("\n   To use different fallback order:")
    print("   export LLM_FALLBACK_ORDER=ollama,gemini,claude")
    
    print("\n   To disable fallback:")
    print("   export LLM_FALLBACK_ENABLED=false")
    
    print(f"\n🎯 SYSTEM STATUS: READY FOR MULTI-AGENT AI!")
    print("=" * 60)


async def demonstrate_fallback():
    """Demonstrate fallback behavior."""
    print("\n🔀 FALLBACK DEMONSTRATION:")
    
    # Simulate rate limit scenario by showing the logic
    print("   Rate Limit Detection:")
    print("   - Detects: '429', 'quota', 'rate limit', 'too many requests'")
    print("   - Action: Automatically tries next model in fallback order")
    print("   - Recovery: Resets failed status on successful calls")
    
    print("\n   Fallback Sequence Example:")
    print("   1. Gemini (primary) → Rate limit detected")
    print("   2. Ollama (local) → Attempts local model")
    print("   3. Claude (cloud) → Tries alternative cloud provider")
    print("   4. Llama (HF) → Final fallback option")


if __name__ == "__main__":
    asyncio.run(test_model_switching())
    asyncio.run(demonstrate_fallback())