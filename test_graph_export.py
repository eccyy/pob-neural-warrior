"""
Quick test: Generate a tree with graph model and export to PoB XML
"""

import torch
import json
from pathlib import Path
from models.graph_tree_builder import GraphTreeBuilder, load_edge_index_from_builds
from integration.pob_bridge import PoBExporter
import sys
sys.path.insert(0, '../PathOfBuilding/src')
from lupa import LuaRuntime

def load_ascendancy_nodes():
    """Load set of ascendancy node IDs from PoB tree data."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
        tree_lua = f.read()
    
    lua_globals = lua.eval('function(code) return load(code)() end')
    tree_data = lua_globals(tree_lua)
    
    ascendancy_nodes = set()
    mastery_nodes = set()
    
    for node_id, node_data in tree_data['nodes'].items():
        if 'ascendancyName' in node_data or ('isAscendancyStart' in node_data and node_data['isAscendancyStart']):
            ascendancy_nodes.add(int(node_id))
        # Also filter mastery nodes - they require effect selection
        if 'isMastery' in node_data and node_data['isMastery']:
            mastery_nodes.add(int(node_id))
    
    return ascendancy_nodes, mastery_nodes

def test_graph_export():
    print("=" * 60)
    print("Testing Graph Model → PoB Export")
    print("=" * 60)
    
    # Load edge connectivity
    print("\n1. Loading tree structure...")
    edge_index = load_edge_index_from_builds(
        "./pob_data/tree_data",
        "./pob_data/tree_data/node_mapping.json"
    )
    print(f"   ✓ Loaded {edge_index.size(1)} edges")
    
    # Create model (untrained)
    print("\n2. Creating graph model...")
    model = GraphTreeBuilder(
        num_nodes=412,
        edge_index=edge_index
    )
    model.eval()
    print(f"   ✓ Model ready ({sum(p.numel() for p in model.parameters()):,} parameters)")
    
    # Load node mapping and filter out ascendancy nodes
    print("\n3. Loading node mapping...")
    ascendancy_nodes, mastery_nodes = load_ascendancy_nodes()
    print(f"   ✓ Identified {len(ascendancy_nodes)} ascendancy nodes to filter")
    print(f"   ✓ Identified {len(mastery_nodes)} mastery nodes to filter")
    
    with open("./pob_data/tree_data/node_mapping.json") as f:
        mapping = json.load(f)
        node_to_index = {int(k): int(v) for k, v in mapping['node_to_index'].items()}
        index_to_node = {int(v): int(k) for k, v in mapping['node_to_index'].items()}
    
    # Node 44683 (class start) connects TO: [45272, 58229, 55236, 18635]
    # But 18635 is ascendancy! Use 58229, 55236, or 63639 instead
    # Try nodes reachable from Shadow start that are NOT ascendancy
    candidate_bridges = [58229, 55236, 63639, 11334]  # Nodes connecting from Shadow start
    
    BRIDGE_NODE_ID = None
    for candidate in candidate_bridges:
        if candidate in node_to_index and candidate not in ascendancy_nodes and candidate not in mastery_nodes:
            BRIDGE_NODE_ID = candidate
            break
    
    if BRIDGE_NODE_ID is None:
        print(f"   ✗ Warning: No valid bridge node found!")
        # Use first non-ascendancy, non-mastery node in mapping
        for node_id, idx in node_to_index.items():
            if node_id not in ascendancy_nodes and node_id not in mastery_nodes:
                BRIDGE_NODE_ID = node_id
                break
    
    starting_node_idx = node_to_index[BRIDGE_NODE_ID]
    print(f"   ✓ Bridge node: {BRIDGE_NODE_ID} (index {starting_node_idx})")
    print(f"   ✓ This is a regular passive (not ascendancy)")
    COMMON_START_NODE_ID = BRIDGE_NODE_ID
    
    # Generate tree with random input
    print("\n4. Generating connected tree...")
    batch_size = 1
    gear = torch.randn(batch_size, 500)
    gems = torch.randn(batch_size, 100)
    skill = torch.randn(batch_size, 8)
    
    with torch.no_grad():
        allocated_tree = model.build_tree_greedy(
            gear, gems, skill, 
            num_points=100, 
            starting_node=starting_node_idx
        )
        
        # Predict performance
        node_embeddings = model.encode_tree()
        context = torch.cat([gear, gems, skill], dim=-1)
        tree_embedding = node_embeddings[allocated_tree].mean(dim=1)
        predicted_perf = model.performance_predictor(
            torch.cat([tree_embedding, context], dim=-1)
        )
    
    print(f"   ✓ Generated tree with {allocated_tree.size(1)} nodes")
    print(f"   ✓ Predicted DPS: {predicted_perf[0, 0].item():.0f}")
    print(f"   ✓ Predicted EHP: {predicted_perf[0, 1].item():.0f}")
    
    # Convert to build format
    print("\n5. Converting to build format...")
    build_data = {
        'gear': gear[0].numpy().tolist(),
        'gems': gems[0].numpy().tolist(),
        'skill': skill[0].numpy().tolist(),
        'tree': allocated_tree[0].numpy().tolist(),  # [100] array indices
        'dps': float(predicted_perf[0, 0].item()),
        'ehp': float(predicted_perf[0, 1].item())
    }
    
    # Save build
    output_json = "test_graph_build.json"
    with open(output_json, 'w') as f:
        json.dump(build_data, f, indent=2)
    print(f"   ✓ Saved to {output_json}")
    
    # Export to PoB XML
    print("\n6. Exporting to PoB XML...")
    output_xml = "test_graph_export.xml"
    
    # Convert tree array indices to PoB node IDs
    tree_node_ids = [index_to_node[int(idx)] for idx in allocated_tree[0].numpy()]
    
    # Shadow class starting nodes (correct connection order)
    # Based on tree edges: 38129 → 44683 → 45272
    # Node 44683 is the classStartIndex=6 node (class start)
    # Node 38129 connects TO 44683
    # Node 45272 connects FROM 44683
    SHADOW_START_NODES = [38129, 44683, 45272]
    
    # The generated tree starts from 39841, but we need to find nodes that
    # bridge from the starting sequence to our tree. Let's use nodes that
    # connect from 44683: [45272, 58229, 55236, 18635]
    # Node 18635 is in the INT/DEX area which connects toward 39841
    
    # Prepend the start sequence
    full_tree_with_dupes = SHADOW_START_NODES + tree_node_ids
    
    # Remove ascendancy nodes, mastery nodes, and duplicates while preserving order
    seen = set()
    full_tree = []
    ascendancy_removed = 0
    mastery_removed = 0
    
    for node_id in full_tree_with_dupes:
        # Skip ascendancy nodes
        if node_id in ascendancy_nodes:
            ascendancy_removed += 1
            continue
        # Skip mastery nodes (require manual effect selection)
        if node_id in mastery_nodes:
            mastery_removed += 1
            continue
        # Skip duplicates
        if node_id not in seen:
            seen.add(node_id)
            full_tree.append(node_id)
    
    num_duplicates = len(full_tree_with_dupes) - len(full_tree) - ascendancy_removed - mastery_removed
    if ascendancy_removed > 0:
        print(f"   ✓ Removed {ascendancy_removed} ascendancy nodes")
    if mastery_removed > 0:
        print(f"   ✓ Removed {mastery_removed} mastery nodes")
    if num_duplicates > 0:
        print(f"   ✓ Removed {num_duplicates} duplicate nodes")
    
    # Verify first actual node is start node
    if tree_node_ids[0] != COMMON_START_NODE_ID:
        print(f"   ⚠️  Warning: First tree node {tree_node_ids[0]} is not start node {COMMON_START_NODE_ID}")
    else:
        print(f"   ✓ First tree node is start node: {COMMON_START_NODE_ID}")
    
    print(f"   ✓ Prepended {len(SHADOW_START_NODES)} Shadow starting nodes")
    print(f"   ✓ Total unique nodes: {len(full_tree)}")
    
    # Create XML manually
    from xml.etree import ElementTree as ET
    root = ET.Element("PathOfBuilding")
    
    # Build element
    build = ET.SubElement(root, "Build")
    build.set("level", "90")
    build.set("targetVersion", "3_0")
    build.set("mainSocketGroup", "1")
    build.set("className", "Shadow")
    build.set("ascendClassName", "None")
    build.set("bandit", "None")
    
    # Tree element
    tree_elem = ET.SubElement(root, "Tree")
    tree_elem.set("activeSpec", "1")
    
    spec = ET.SubElement(tree_elem, "Spec")
    spec.set("treeVersion", "3_27")
    spec.set("classId", "6")  # Shadow (node 39841 start)
    spec.set("ascendClassId", "0")
    spec.set("nodes", ",".join(map(str, full_tree)))
    
    # Write XML
    tree_xml = ET.ElementTree(root)
    ET.indent(tree_xml, space="  ")
    tree_xml.write(output_xml, encoding="utf-8", xml_declaration=True)
    
    print(f"   ✓ Exported to {output_xml}")
    print(f"   ✓ Contains {len(full_tree)} unique nodes")
    
    # Verify XML
    print("\n7. Verifying XML structure...")
    from xml.etree import ElementTree as ET
    tree = ET.parse(output_xml)
    root = tree.getroot()
    
    spec_nodes = root.find('.//Tree/Spec')
    if spec_nodes is not None:
        nodes_attr = spec_nodes.get('nodes', '')
        node_list = [n for n in nodes_attr.split(',') if n]
        print(f"   ✓ XML contains {len(node_list)} nodes")
        print(f"   ✓ First 5 nodes: {','.join(node_list[:5])}")
        print(f"   ✓ Tree version: {spec_nodes.get('treeVersion', 'unknown')}")
    else:
        print("   ✗ No Tree/Spec found in XML!")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print(f"\n→ Import {output_xml} into Path of Building to verify")
    print("→ The tree should show connected nodes (even if untrained)")

if __name__ == "__main__":
    test_graph_export()
