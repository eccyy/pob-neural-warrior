"""
Verify that generated tree nodes are actually connected
"""

import json

def verify_connectivity(xml_path: str):
    """Check if nodes in XML are connected according to edge data"""
    from xml.etree import ElementTree as ET
    
    print("=" * 60)
    print("Verifying Tree Connectivity")
    print("=" * 60)
    
    # Load XML
    print(f"\n1. Loading {xml_path}...")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    spec = root.find('.//Tree/Spec')
    nodes_str = spec.get('nodes', '')
    node_ids = [int(n) for n in nodes_str.split(',') if n]
    print(f"   ✓ Found {len(node_ids)} nodes")
    
    # Load edge data
    print("\n2. Loading edge connectivity...")
    with open("./pob_data/tree_data/tree_edges.json") as f:
        edges = json.load(f)
    print(f"   ✓ Loaded edges for {len(edges)} nodes")
    
    # Check connectivity
    print("\n3. Checking connectivity...")
    disconnected = []
    
    for i, node_id in enumerate(node_ids):
        if i == 0:
            # First node is starting position
            continue
        
        prev_node = node_ids[i-1]
        
        # Check if current node connects to previous
        node_str = str(node_id)
        prev_str = str(prev_node)
        
        connected = False
        
        # Check if edge exists in either direction
        if node_str in edges:
            if prev_str in edges[node_str]:
                connected = True
        if prev_str in edges:
            if node_str in edges[prev_str]:
                connected = True
        
        if not connected:
            # Also check if connected to ANY previous node (not just immediate)
            for prev_node in node_ids[:i]:
                prev_str = str(prev_node)
                if node_str in edges:
                    if prev_str in edges[node_str]:
                        connected = True
                        break
                if prev_str in edges:
                    if node_str in edges[prev_str]:
                        connected = True
                        break
        
        if not connected:
            disconnected.append((i, node_id, prev_node))
    
    # Results
    print("\n" + "=" * 60)
    if disconnected:
        print(f"⚠️  Found {len(disconnected)} potentially disconnected nodes:")
        for i, node_id, prev in disconnected[:10]:  # Show first 10
            print(f"   Node {i}: {node_id} (not connected to any previous node)")
        if len(disconnected) > 10:
            print(f"   ... and {len(disconnected) - 10} more")
    else:
        print("✓ All nodes are connected!")
    
    print("=" * 60)
    
    # Additional check: are nodes in sequential order?
    print("\n4. Sequential connectivity check (adjacent pairs)...")
    adjacent_disconnected = 0
    for i in range(1, len(node_ids)):
        node_str = str(node_ids[i])
        prev_str = str(node_ids[i-1])
        
        connected = False
        if node_str in edges:
            if prev_str in edges[node_str]:
                connected = True
        if prev_str in edges:
            if node_str in edges[prev_str]:
                connected = True
        
        if not connected:
            adjacent_disconnected += 1
    
    print(f"   Adjacent pairs: {len(node_ids)-1}")
    print(f"   Connected: {len(node_ids)-1-adjacent_disconnected}")
    print(f"   Disconnected: {adjacent_disconnected}")
    
    if adjacent_disconnected == 0:
        print("   ✓ Perfect sequential path!")
    else:
        print(f"   ⚠️  {adjacent_disconnected} gaps in sequential path")
        print("   (Note: Still may be connected via earlier nodes)")

if __name__ == "__main__":
    verify_connectivity("test_graph_export.xml")
