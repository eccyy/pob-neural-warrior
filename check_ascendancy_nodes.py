"""Identify and filter out ascendancy nodes from generated tree."""
import sys
sys.path.insert(0, '../PathOfBuilding/src')
from lupa import LuaRuntime
from xml.etree import ElementTree as ET

# Load PoB tree data
print("Loading PoB tree data...")
lua = LuaRuntime(unpack_returned_tuples=True)
with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
    tree_lua = f.read()

lua_globals = lua.eval('function(code) return load(code)() end')
tree_data = lua_globals(tree_lua)

# Identify ascendancy nodes
print("Identifying ascendancy nodes...")
ascendancy_nodes = set()
regular_nodes = set()

for node_id, node_data in tree_data['nodes'].items():
    node_id_str = str(node_id)
    
    # Check if this is an ascendancy node
    is_ascendancy = False
    
    if 'ascendancyName' in node_data:
        is_ascendancy = True
    elif 'isAscendancyStart' in node_data and node_data['isAscendancyStart']:
        is_ascendancy = True
    
    if is_ascendancy:
        ascendancy_nodes.add(node_id_str)
    else:
        regular_nodes.add(node_id_str)

print(f"Found {len(ascendancy_nodes)} ascendancy nodes")
print(f"Found {len(regular_nodes)} regular passive nodes")

# Load our generated tree
tree = ET.parse('test_graph_export.xml')
root = tree.getroot()
spec = root.find('.//Spec')
nodes_str = spec.get('nodes')
nodes = [str(n) for n in nodes_str.split(',')]

print(f"\nAnalyzing generated tree with {len(nodes)} nodes...")

# Find ascendancy nodes in our tree
ascendancy_in_tree = []
for i, node in enumerate(nodes):
    if node in ascendancy_nodes:
        ascendancy_in_tree.append((i, node))

print(f"\n{'=' * 60}")
print(f"Ascendancy Nodes in Generated Tree:")
print(f"{'=' * 60}")

if ascendancy_in_tree:
    print(f"Found {len(ascendancy_in_tree)} ascendancy nodes:")
    for pos, node in ascendancy_in_tree:
        node_data = tree_data['nodes'][int(node)]
        name = node_data['name'] if 'name' in node_data else 'Unknown'
        ascendancy_class = node_data['ascendancyName'] if 'ascendancyName' in node_data else 'Unknown'
        print(f"  Position {pos}: Node {node} - {name} ({ascendancy_class})")
    
    # Filter them out
    filtered_nodes = [n for n in nodes if n not in ascendancy_nodes]
    print(f"\n{'=' * 60}")
    print(f"After filtering:")
    print(f"{'=' * 60}")
    print(f"Original: {len(nodes)} nodes")
    print(f"Filtered: {len(filtered_nodes)} nodes")
    print(f"Removed: {len(nodes) - len(filtered_nodes)} ascendancy nodes")
else:
    print("✓ No ascendancy nodes found in generated tree")

# Show which of our mapped nodes are ascendancy
print(f"\n{'=' * 60}")
print(f"Checking Training Data Mapping:")
print(f"{'=' * 60}")

import json
with open('pob_data/tree_data/node_mapping.json', 'r') as f:
    mapping = json.load(f)

mapped_ascendancy = []
for node_str in mapping['node_to_index'].keys():
    if node_str in ascendancy_nodes:
        mapped_ascendancy.append(node_str)

if mapped_ascendancy:
    print(f"WARNING: {len(mapped_ascendancy)} ascendancy nodes in our training mapping!")
    print(f"We should filter these out before training.")
    if len(mapped_ascendancy) <= 20:
        print(f"Ascendancy nodes: {mapped_ascendancy}")
else:
    print("✓ No ascendancy nodes in training mapping")
