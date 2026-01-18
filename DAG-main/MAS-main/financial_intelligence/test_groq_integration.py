#!/usr/bin/env python3
"""
Test script for Groq fallback integration
"""
import asyncio
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    get_fallback_system_type,
    should_enable_fallback,
    should_enable_groq_fallback,
    should_enable_openai_fallback,
    validate_config,
    print_config_summary
)
from groq_fallback import get_groq_fallback_handler, get_hybrid_fallback_handler
from openai_fallback import get_fallback_handler as get_openai_fallback_handler


async def test_groq_fallback():
    """Test Groq fallback functionality"""
    print("=" * 60)
    print("TESTING GROQ FALLBACK INTEGRATION")
    print("=" * 60)
    
    # Print configuration summary
    print_config_summary()
    
    print(f"\n🔧 Fallback System Type: {get_fallback_system_type()}")
    print(f"✅ Any Fallback Enabled: {should_enable_fallback()}")
    print(f"🚀 Groq Fallback Enabled: {should_enable_groq_fallback()}")
    print(f"🤖 OpenAI Fallback Enabled: {should_enable_openai_fallback()}")
    
    # Test Groq fallback handler
    print(f"\n🧪 Testing Groq fallback handler...")
    groq_handler = get_groq_fallback_handler()
    print(f"   Available: {groq_handler.is_available()}")
    
    if groq_handler.is_available():
        # Test with a simple query
        test_query = "What is the current repo rate in India?"
        print(f"   Testing query: {test_query}")
        
        try:
            result = await groq_handler.get_fallback_response(test_query)
            print(f"   Status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"   Response length: {len(result.get('response', ''))}")
                print(f"   Sources: {len(result.get('references', []))}")
                print(f"   Model: {result.get('model')}")
            else:
                print(f"   Error: {result.get('message')}")
        except Exception as e:
            print(f"   Exception: {e}")
    
    # Test hybrid fallback handler
    print(f"\n🧪 Testing Hybrid fallback handler...")
    hybrid_handler = get_hybrid_fallback_handler()
    print(f"   Available: {hybrid_handler.is_available()}")
    
    if hybrid_handler.is_available():
        try:
            result = await hybrid_handler.get_fallback_response(test_query)
            print(f"   Status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"   Response length: {len(result.get('response', ''))}")
                print(f"   Sources: {len(result.get('references', []))}")
                print(f"   Fallback System: {result.get('fallback_system')}")
            else:
                print(f"   Error: {result.get('message')}")
        except Exception as e:
            print(f"   Exception: {e}")
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 60)


async def main():
    """Main test function"""
    try:
        # Validate configuration first
        validate_config()
        
        # Run tests
        await test_groq_fallback()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
