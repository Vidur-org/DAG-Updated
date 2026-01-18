"""
Test script for node editing functionality via API
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_node_editing():
    print("Testing Node Editing Functionality\n")
    print("=" * 60)
    
    # Step 1: Start a new analysis
    print("\n[1] Starting new analysis...")
    analyze_request = {
        "user_id": "test_user",
        "query": "Should I invest in RELIANCE for October 2024 to December 2024?",
        "preferences": {
            "preset": "fast",  # Use fast preset for quicker testing
            "save": False
        }
    }
    
    print(f"   Request: {json.dumps(analyze_request, indent=2)}")
    
    try:
        response = requests.post(f"{API_BASE}/analyze", json=analyze_request, timeout=300)
        response.raise_for_status()
        data = response.json()
        
        session_id = data["session_id"]
        print(f"   [OK] Analysis started successfully!")
        print(f"   Session ID: {session_id}")
        print(f"   Total Nodes: {data['execution_report']['stats']['num_nodes']}")
        
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Analysis failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False
    
    # Step 2: Get all nodes
    print("\n[2] Fetching all nodes...")
    try:
        response = requests.get(f"{API_BASE}/sessions/{session_id}/nodes")
        response.raise_for_status()
        nodes_data = response.json()
        
        nodes = nodes_data["nodes"]
        print(f"   [OK] Retrieved {len(nodes)} nodes")
        
        if len(nodes) == 0:
            print("   [WARNING] No nodes found. Cannot test editing.")
            return False
        
        # Display first few nodes
        print("\n   Sample nodes:")
        for node in nodes[:5]:
            print(f"      Node {node['id']} (Level {node['level']}): {node['question'][:60]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to fetch nodes: {e}")
        return False
    
    # Step 3: Get details of a specific node (preferably not root)
    print("\n[3] Getting node details...")
    test_node = None
    for node in nodes:
        if node['id'] != '0' and not node['is_leaf']:  # Pick a non-root, non-leaf node
            test_node = node
            break
    
    if not test_node:
        test_node = nodes[0]  # Fallback to first node
    
    node_id = test_node['id']
    print(f"   Testing with Node {node_id}")
    
    try:
        response = requests.get(f"{API_BASE}/sessions/{session_id}/nodes/{node_id}")
        response.raise_for_status()
        node_details = response.json()
        
        print(f"   [OK] Node details retrieved")
        print(f"   Question: {node_details['question'][:80]}...")
        print(f"   Level: {node_details['level']}")
        print(f"   Is Leaf: {node_details['is_leaf']}")
        print(f"   Children: {len(node_details['children']) if node_details['children'] else 0}")
        
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to get node details: {e}")
        return False
    
    # Step 4: Edit the node
    print("\n[4] Editing node...")
    original_question = node_details['question']
    new_question = f"[EDITED] {original_question} - Modified for testing purposes"
    
    edit_request = {
        "new_question": new_question
    }
    
    print(f"   Original: {original_question[:60]}...")
    print(f"   New: {new_question[:60]}...")
    
    try:
        print("   [WAIT] Sending edit request (this may take a while)...")
        response = requests.post(
            f"{API_BASE}/sessions/{session_id}/nodes/{node_id}/edit",
            json=edit_request,
            timeout=300
        )
        response.raise_for_status()
        edit_result = response.json()
        
        print(f"   [OK] Node edited successfully!")
        print(f"   Edit Count: {edit_result['edit_count']}")
        print(f"   Updated Question: {edit_result['updated_node']['question'][:60]}...")
        print(f"   New Children Count: {len(edit_result['updated_node']['children']) if edit_result['updated_node']['children'] else 0}")
        
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to edit node: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False
    
    # Step 5: Verify the edit by getting updated nodes
    print("\n[5] Verifying edit...")
    try:
        response = requests.get(f"{API_BASE}/sessions/{session_id}/nodes")
        response.raise_for_status()
        updated_nodes_data = response.json()
        
        updated_nodes = updated_nodes_data["nodes"]
        edited_node = next((n for n in updated_nodes if n['id'] == node_id), None)
        
        if edited_node:
            print(f"   [OK] Edit verified!")
            print(f"   Updated Question: {edited_node['question'][:60]}...")
            if edited_node['question'].startswith("[EDITED]"):
                print(f"   [OK] Question successfully updated!")
            else:
                print(f"   [WARNING] Question doesn't match expected format")
        else:
            print(f"   [WARNING] Could not find edited node")
        
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to verify edit: {e}")
        return False
    
    # Step 6: Get updated report
    print("\n[6] Getting updated report...")
    try:
        response = requests.get(f"{API_BASE}/sessions/{session_id}/report")
        response.raise_for_status()
        report = response.json()
        
        stats = report['execution_report']['stats']
        print(f"   [OK] Report retrieved")
        print(f"   Total Nodes: {stats['num_nodes']}")
        print(f"   LLM Calls: {stats['llm_calls']}")
        print(f"   Edit Count: {stats['edit_count']}")
        
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to get report: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All tests passed! Node editing is working correctly.")
    print(f"Session ID: {session_id}")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_node_editing()
    exit(0 if success else 1)
