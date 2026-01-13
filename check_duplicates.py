"""Check for duplicate nodes in generated tree."""
import json
from xml.etree import ElementTree as ET

# Read the generated XML
tree = ET.parse('test_graph_export.xml')
root = tree.getroot()

# Get the nodes list
spec = root.find('.//Spec')
nodes_str = spec.get('nodes')
nodes = [int(n) for n in nodes_str.split(',')]

print("=" * 60)
print("Checking for Duplicate Nodes")
print("=" * 60)

print(f"\nTotal nodes in XML: {len(nodes)}")
print(f"Unique nodes: {len(set(nodes))}")
print(f"Duplicates: {len(nodes) - len(set(nodes))}")

# Find which nodes are duplicated
from collections import Counter
node_counts = Counter(nodes)
duplicates = {node: count for node, count in node_counts.items() if count > 1}

if duplicates:
    print(f"\n{'=' * 60}")
    print(f"Duplicated Nodes (appears multiple times):")
    print(f"{'=' * 60}")
    for node, count in sorted(duplicates.items()):
        print(f"  Node {node}: appears {count} times")
        # Show positions
        positions = [i for i, n in enumerate(nodes) if n == node]
        print(f"    Positions: {positions}")
else:
    print("\n✓ No duplicates found!")

# Check first few nodes
print(f"\n{'=' * 60}")
print(f"First 10 nodes:")
print(f"{'=' * 60}")
for i, node in enumerate(nodes[:10]):
    print(f"  {i}: {node}")

# Also check the JSON build data
print(f"\n{'=' * 60}")
print(f"Checking build JSON data:")
print(f"{'=' * 60}")

with open('test_graph_build.json', 'r') as f:
    build = json.load(f)

tree_indices = build['tree']
print(f"\nTree array length: {len(tree_indices)}")
print(f"Unique indices: {len(set(tree_indices))}")
print(f"First 10 indices: {tree_indices[:10]}")
