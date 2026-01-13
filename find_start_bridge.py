"""Find which nodes from Shadow starting sequence are in our mapping."""
import json

# Load builds to get node mapping
print("Loading builds...")
with open('../pob_data/processed/Keepers_train.json', 'r') as f:
    builds = json.load(f)

# Extract all unique node IDs
all_nodes = set()
for build in builds:
    if 'tree' in build and 'allocated_nodes' in build['tree']:
        all_nodes.update(build['tree']['allocated_nodes'])

print(f"Found {len(all_nodes)} unique nodes in training data")

# Create mapping
node_ids = sorted(all_nodes)
node_to_index = {str(node_id): idx for idx, node_id in enumerate(node_ids)}

# Nodes reachable from Shadow starting sequence
reachable_nodes = ['11334', '18635', '55236', '58229', '63639']

# Also check Shadow start sequence itself
shadow_start_nodes = ['38129', '45272', '44683']

print("\n" + "=" * 60)
print("Shadow Start Sequence Nodes")
print("=" * 60)

for node_id in shadow_start_nodes:
    if node_id in node_to_index:
        index = node_to_index[node_id]
        print(f"  ✓ Node {node_id} is in mapping (index {index})")
    else:
        print(f"  ✗ Node {node_id} NOT in mapping")

print("\n" + "=" * 60)
print("Nodes Reachable FROM Start Sequence")
print("=" * 60)

found_nodes = []
for node_id in reachable_nodes:
    if node_id in node_to_index:
        index = node_to_index[node_id]
        found_nodes.append((node_id, index))
        print(f"  ✓ Node {node_id} is in mapping (index {index})")
    else:
        print(f"  ✗ Node {node_id} NOT in mapping")

# Check our current start node
our_start = '39841'
print(f"\n{'=' * 60}")
print(f"Our Current Start Node")
print(f"{'=' * 60}")
if our_start in node_to_index:
    print(f"  ✓ Node {our_start} is in mapping (index {node_to_index[our_start]})")
else:
    print(f"  ✗ Node {our_start} NOT in mapping")

if found_nodes:
    print(f"\n{'=' * 60}")
    print(f"SOLUTION: Start generation from one of these nodes!")
    print(f"{'=' * 60}")
    print(f"\nRecommendation: Use node {found_nodes[0][0]} (index {found_nodes[0][1]})")
    print(f"This connects directly from the Shadow starting sequence.")
else:
    print(f"\n{'=' * 60}")
    print(f"PROBLEM: None of the directly reachable nodes are in mapping!")
    print(f"Need to find a path through the tree to node 39841")
    print(f"{'=' * 60}")
