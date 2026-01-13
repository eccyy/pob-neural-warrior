"""Check which nodes connect the Shadow starting sequence to our generated tree."""
import json
import sys
sys.path.insert(0, '../PathOfBuilding/src')

from lupa import LuaRuntime

# Load PoB tree data
lua = LuaRuntime(unpack_returned_tuples=True)
with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
    tree_lua = f.read()

lua_globals = lua.eval('function(code) return load(code)() end')
tree_data = lua_globals(tree_lua)

# Shadow starting nodes
shadow_starts = [38129, 45272, 44683]
our_start_node = 39841

print("=" * 60)
print("Shadow Starting Sequence Connections")
print("=" * 60)

# Check what each starting node connects to
for node_id in shadow_starts:
    node_data = tree_data['nodes'][node_id]
    
    # Convert Lua table to Python list
    out_nodes = []
    if 'out' in node_data:
        for i, v in node_data['out'].items():
            out_nodes.append(str(v))
    
    in_nodes = []
    if 'in' in node_data:
        for i, v in node_data['in'].items():
            in_nodes.append(str(v))
    
    print(f"\nNode {node_id} ({node_data['name']}):")
    print(f"  Connects TO: {out_nodes}")
    print(f"  Connects FROM: {in_nodes}")
    
    # Check if any connect to our start node
    if str(our_start_node) in out_nodes:
        print(f"  ✓ CONNECTS TO OUR START NODE {our_start_node}!")

# Check what our start node connects from
print(f"\n{'=' * 60}")
print(f"Our Generated Tree Start Node")
print(f"{'=' * 60}")

our_node_data = tree_data['nodes'][our_start_node]

out_nodes = []
if 'out' in our_node_data:
    for i, v in our_node_data['out'].items():
        out_nodes.append(str(v))

in_nodes = []
if 'in' in our_node_data:
    for i, v in our_node_data['in'].items():
        in_nodes.append(str(v))

print(f"\nNode {our_start_node} ({our_node_data['name']}):")
print(f"  Connects TO: {out_nodes}")
print(f"  Connects FROM: {in_nodes}")

# Check if it connects from any starting nodes
for node_id in shadow_starts:
    if str(node_id) in in_nodes:
        print(f"  ✓ CONNECTS FROM STARTING NODE {node_id}!")

# Find ALL nodes that connect TO the starting sequence (outward paths)
print(f"\n{'=' * 60}")
print(f"All Nodes Connecting FROM Starting Sequence")
print(f"{'=' * 60}")

all_out_nodes = set()
for node_id in shadow_starts:
    node_data = tree_data['nodes'][node_id]
    if 'out' in node_data:
        for i, v in node_data['out'].items():
            all_out_nodes.add(str(v))

print(f"\nNodes directly reachable from starting sequence:")
for node in sorted(all_out_nodes, key=int):
    print(f"  {node}")
