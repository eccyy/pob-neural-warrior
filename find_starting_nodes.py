import json

# Load node mapping
with open('pob_data/tree_data/node_mapping.json', 'r') as f:
    data = json.load(f)

# Known starting node IDs from PoB (from tree.lua analysis)
known_starting_nodes = {
    'Scion': 7960,      # classId 0
    'Marauder': 26725,  # classId 1
    'Ranger': 36634,    # classId 2
    'Witch': 41714,     # classId 3
    'Duelist': 34883,   # classId 4
    'Templar': 54142,   # classId 5
    'Shadow': 61834     # classId 6
}

print("Checking which starting nodes are in our tree data:\n")
node_to_index = data.get('node_to_index', {})
index_to_node = data.get('index_to_node', {})

for class_name, node_id in known_starting_nodes.items():
    if str(node_id) in node_to_index:
        idx = node_to_index[str(node_id)]
        print(f"✓ {class_name:12} node {node_id:5} -> index {idx:3}")
    else:
        print(f"✗ {class_name:12} node {node_id:5} -> NOT IN TREE")

print(f"\nTotal nodes in tree: {len(index_to_node)}")
print(f"\nFirst 10 indices and their node IDs:")
for i in range(min(10, len(index_to_node))):
    print(f"  Index {i}: Node {index_to_node[str(i)]}")
