"""Extract class starting nodes from PoB tree data."""
import json
import sys
sys.path.insert(0, '../PathOfBuilding/src')

from lupa import LuaRuntime

# Load PoB tree data
lua = LuaRuntime(unpack_returned_tuples=True)
with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
    tree_lua = f.read()

# Execute and get tree data
lua.execute(tree_lua)
tree = lua.globals().tree

# Extract class starting nodes
print("=" * 60)
print("Class Starting Nodes from PoB Tree Data")
print("=" * 60)

classes = {}
for class_id, class_data in tree['classes'].items():
    class_name = class_data['name']
    base_str = class_data.get('base_str', 0)
    base_dex = class_data.get('base_dex', 0)
    base_int = class_data.get('base_int', 0)
    
    # Get starting nodes (they use 'base' field in some PoB versions)
    start_nodes = []
    
    # Try different potential fields
    if hasattr(class_data, 'start'):
        start_nodes.append(class_data.start)
    
    print(f"\nClass {class_id}: {class_name}")
    print(f"  Base Stats: {base_str} STR, {base_dex} DEX, {base_int} INT")
    print(f"  Available fields: {list(class_data.keys())}")
    
    classes[class_name] = {
        'classId': str(class_id),
        'base_str': base_str,
        'base_dex': base_dex,
        'base_int': base_int,
    }

print("\n" + "=" * 60)
print("Checking for 'classes' vs 'characterData'")
print("=" * 60)

# Check if there's character data with starting nodes
if hasattr(tree, 'characterData'):
    print("\nFound characterData!")
    for char_id, char_data in tree.characterData.items():
        print(f"Character {char_id}: {list(char_data.keys())}")

# Alternative: Look for nodes marked as "classStartNode" or similar
print("\n" + "=" * 60)
print("Searching for Class Start Node Patterns")
print("=" * 60)

class_start_nodes = {}
for node_id, node_data in tree['nodes'].items():
    # Check if this is a class start node
    is_start = node_data.get('isClassStart', False)
    is_ascendancy_start = node_data.get('isAscendancyStart', False)
    is_multiple = node_data.get('isMultipleChoice', False)
    is_mastery = node_data.get('isMastery', False)
    is_keystone = node_data.get('isKeystone', False)
    is_notable = node_data.get('isNotable', False)
    is_jewel = node_data.get('isJewelSocket', False)
    
    # Class start nodes might not have stats but connect to the tree
    if node_data.get('classStartIndex') is not None:
        class_idx = node_data.get('classStartIndex')
        if class_idx not in class_start_nodes:
            class_start_nodes[class_idx] = []
        class_start_nodes[class_idx].append(str(node_id))

print("\nNodes with 'classStartIndex' field:")
for class_idx in sorted(class_start_nodes.keys()):
    print(f"  Class Index {class_idx}: {class_start_nodes[class_idx]}")

# Save results
output = {
    'classes': classes,
    'class_start_nodes': class_start_nodes
}

with open('pob_data/tree_data/class_starts.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✓ Saved to pob_data/tree_data/class_starts.json")
