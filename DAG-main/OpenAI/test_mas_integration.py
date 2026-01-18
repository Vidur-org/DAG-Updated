"""
Test script to verify MAS-Tree integration

This script tests if the Tree system can successfully:
1. Call MAS for data gathering
2. Load and parse output.json
3. Build tree structure with MAS data
"""

import asyncio
import sys
from pathlib import Path

# Add paths
openai_path = Path(__file__).parent
mas_path = openai_path.parent / "MAS-main"
sys.path.insert(0, str(openai_path))
sys.path.insert(0, str(mas_path))

async def test_integration():
    print("🧪 Testing MAS-Tree Integration\n")
    
    # Test 1: Import Tree Orchestrator
    print("Test 1: Importing Tree Orchestrator...")
    try:
        from tree_orchestrator_main import TreeOrchestrator
        print("✅ Import successful\n")
    except Exception as e:
        print(f"❌ Import failed: {e}\n")
        return
    
    # Test 2: Initialize orchestrator
    print("Test 2: Initializing orchestrator...")
    try:
        orchestrator = TreeOrchestrator(max_levels=3, max_children=2)
        print(f"✅ Orchestrator initialized")
        print(f"   Stock: {orchestrator.stock}")
        print(f"   Investment Window: {orchestrator.investment_window}")
        print(f"   MAS Output Path: {orchestrator.mas_output_path}\n")
    except Exception as e:
        print(f"❌ Initialization failed: {e}\n")
        return
    
    # Test 3: Test MAS data fetching
    print("Test 3: Testing MAS data fetch...")
    try:
        query = f"Should I invest in {orchestrator.stock} for {orchestrator.investment_window}?"
        print(f"   Query: {query}")
        print(f"   Calling MAS system...\n")
        
        mas_data = await orchestrator.fetch_mas_data(query)
        
        print(f"✅ MAS data fetched successfully")
        print(f"   Timestamp: {mas_data.get('timestamp')}")
        print(f"   Results: {len(mas_data.get('results', {}))} tasks")
        print(f"   Report length: {len(mas_data.get('final_report', ''))} chars")
        print(f"   Output saved: {orchestrator.mas_output_path.exists()}\n")
    except Exception as e:
        print(f"❌ MAS fetch failed: {e}\n")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Build root node
    print("Test 4: Building root node with MAS data...")
    try:
        root_node = await orchestrator.buil_first_node()
        print(f"✅ Root node created")
        print(f"   Node ID: {root_node.id}")
        print(f"   Context length: {len(root_node.context)} chars")
        print(f"   Child questions: {len(root_node.child_questions)}")
        print(f"   BM25 indexed docs: {len(orchestrator.context)}\n")
    except Exception as e:
        print(f"❌ Root node creation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\n✅ Integration is working correctly")
    print("   - MAS system callable from Tree")
    print("   - output.json generated and loaded")
    print("   - Tree can build nodes with MAS data")
    print("   - BM25 cache populated with MAS results")
    print("\n📝 To run full analysis:")
    print("   python tree_orchestrator_main.py")

if __name__ == "__main__":
    asyncio.run(test_integration())
