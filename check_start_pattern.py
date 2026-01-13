import json

mapping = json.load(open('pob_data/tree_data/node_mapping.json'))
edges = json.load(open('pob_data/tree_data/real_tree_edges.json'))

# Check nodes from working build
test_nodes = [25511, 32117, 39841]

print("Checking first 3 nodes from working Shadow build:")
for n in test_nodes:
    in_map = str(n) in mapping['node_to_index']
    connects_to = edges.get(str(n), [])[:5]
    print(f"  Node {n}: in_mapping={in_map}, connects_to={connects_to}")

# Check what these special nodes are
print("\nLooking for class start pattern...")
print("Nodes 25511 and 32117 appear to be jewel sockets or class starts")
print("\nChecking if they're in the full tree:")
print(f"  25511 in tree: {str(25511) in edges}")
print(f"  32117 in tree: {str(32117) in edges}")
