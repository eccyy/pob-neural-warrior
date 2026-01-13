"""Check if generated tree nodes form a connected path."""
import json
import sys
sys.path.insert(0, '../PathOfBuilding/src')
from lupa import LuaRuntime
from xml.etree import ElementTree as ET

# Load PoB tree data to get real edges
print("Loading PoB tree data...")
lua = LuaRuntime(unpack_returned_tuples=True)
with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
    tree_lua = f.read()

lua_globals = lua.eval('function(code) return load(code)() end')
tree_data = lua_globals(tree_lua)

# Build edge graph
edges = {}
for node_id, node_data in tree_data['nodes'].items():
    node_id = str(node_id)
    edges[node_id] = set()
    
    # Add outgoing connections
    if 'out' in node_data:
        for i, v in node_data['out'].items():
            edges[node_id].add(str(v))
    
    # Add incoming connections (make bidirectional)
    if 'in' in node_data:
        for i, v in node_data['in'].items():
            edges[node_id].add(str(v))

print(f"Built edge graph with {len(edges)} nodes")

# Load our generated tree
tree = ET.parse('test_graph_export.xml')
root = tree.getroot()
spec = root.find('.//Spec')
nodes_str = spec.get('nodes')
nodes = [str(n) for n in nodes_str.split(',')]

print(f"\nChecking connectivity of {len(nodes)} nodes...")

# Check if each node connects to at least one previous node
print("\n" + "=" * 60)
print("Node Connectivity Analysis")
print("=" * 60)

disconnected_nodes = []
for i, node in enumerate(nodes[1:], start=1):  # Skip first node (38129)
    # Check if this node connects to ANY previous node
    previous_nodes = set(nodes[:i])
    
    if node not in edges:
        print(f"  Node {i}: {node} - NOT IN TREE DATA!")
        disconnected_nodes.append((i, node, "not in tree"))
        continue
    
    connections_to_prev = edges[node].intersection(previous_nodes)
    
    if not connections_to_prev:
        print(f"  Node {i}: {node} - DISCONNECTED (no edge to previous nodes)")
        # Show what it DOES connect to
        if edges[node]:
            neighbors = list(edges[node])[:5]
            print(f"           Connects to: {neighbors}")
        disconnected_nodes.append((i, node, "no path"))
    elif i < 10:  # Show first few for verification
        print(f"  Node {i}: {node} ✓ connects to {list(connections_to_prev)[:3]}")

print(f"\n{'=' * 60}")
print(f"Summary:")
print(f"{'=' * 60}")
print(f"Total nodes: {len(nodes)}")
print(f"Disconnected nodes: {len(disconnected_nodes)}")
print(f"Connected nodes: {len(nodes) - len(disconnected_nodes)}")

if disconnected_nodes:
    print(f"\n{'=' * 60}")
    print(f"Disconnected Nodes (breaks in the path):")
    print(f"{'=' * 60}")
    for pos, node, reason in disconnected_nodes[:20]:  # Show first 20
        print(f"  Position {pos}: Node {node} ({reason})")
