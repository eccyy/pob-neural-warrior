"""
Use a real working build to create a valid connected tree
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Load one of your working builds
build_file = Path('../PathOfBuilding/src/Builds/blocker.xml')
tree = ET.parse(build_file)
spec = tree.getroot().find('.//Spec')
nodes_str = spec.get('nodes', '')
working_nodes = [int(n) for n in nodes_str.split(',') if n.strip()]

print(f"Using reference build: {build_file.name}")
print(f"Total nodes: {len(working_nodes)}")
print(f"First 20 nodes: {working_nodes[:20]}")

# This is a VALID connected tree from a real build
# Save it as a template
output = {
    'nodes': working_nodes,
    'class': 'Scion',
    'note': 'Valid connected tree from blocker.xml - use as template'
}

with open('pob_data/tree_data/reference_tree.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nSaved reference tree to pob_data/tree_data/reference_tree.json")
