"""Extract class starting nodes from PoB tree by looking for 'spc' field."""
import json
import sys
sys.path.insert(0, '../PathOfBuilding/src')

from lupa import LuaRuntime

# Load PoB tree data
lua = LuaRuntime(unpack_returned_tuples=True)
with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
    tree_lua = f.read()

# Execute and get tree - it returns a table directly
lua_globals = lua.eval('function(code) return load(code)() end')
tree_data = lua_globals(tree_lua)

print("=" * 60)
print("Extracting Class Starting Nodes (3_27)")
print("=" * 60)

# Find nodes with 'classStartIndex' field - these are class start nodes
class_starts = {}
for node_id, node_data in tree_data['nodes'].items():
    if 'classStartIndex' in node_data:
        class_id = node_data['classStartIndex']
        if class_id not in class_starts:
            class_starts[class_id] = []
        class_starts[class_id].append(str(node_id))

print("\nClass Starting Nodes (by classId):")
class_names = {
    0: "Scion",
    1: "Marauder", 
    2: "Ranger",
    3: "Witch",
    4: "Duelist",
    5: "Templar",
    6: "Shadow"
}

for class_id in sorted(class_starts.keys()):
    class_name = class_names.get(class_id, f"Unknown-{class_id}")
    nodes = class_starts[class_id]
    print(f"\n  Class {class_id} ({class_name}): {len(nodes)} nodes")
    print(f"    Nodes: {nodes}")

# Save to JSON
output = {
    'class_names': class_names,
    'class_start_nodes': {str(k): v for k, v in class_starts.items()}
}

with open('pob_data/tree_data/class_start_nodes.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✓ Saved to pob_data/tree_data/class_start_nodes.json")
