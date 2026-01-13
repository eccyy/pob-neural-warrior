"""Check for mastery nodes in generated tree."""
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

# Identify mastery nodes and other special node types
print("Identifying special node types...")
mastery_nodes = set()
jewel_sockets = set()
keystones = set()
notables = set()

for node_id, node_data in tree_data['nodes'].items():
    node_id_str = str(node_id)
    
    if 'isMastery' in node_data and node_data['isMastery']:
        mastery_nodes.add(node_id_str)
    if 'isJewelSocket' in node_data and node_data['isJewelSocket']:
        jewel_sockets.add(node_id_str)
    if 'isKeystone' in node_data and node_data['isKeystone']:
        keystones.add(node_id_str)
    if 'isNotable' in node_data and node_data['isNotable']:
        notables.add(node_id_str)

print(f"Found {len(mastery_nodes)} mastery nodes")
print(f"Found {len(jewel_sockets)} jewel socket nodes")
print(f"Found {len(keystones)} keystone nodes")
print(f"Found {len(notables)} notable nodes")

# Load our generated tree
tree = ET.parse('test_graph_export.xml')
root = tree.getroot()
spec = root.find('.//Spec')
nodes_str = spec.get('nodes')
nodes = nodes_str.split(',')

print(f"\nAnalyzing generated tree with {len(nodes)} nodes...")

# Find special nodes in our tree
masteries_in_tree = []
jewels_in_tree = []
keystones_in_tree = []
notables_in_tree = []

for i, node in enumerate(nodes):
    if node in mastery_nodes:
        masteries_in_tree.append((i, node))
    if node in jewel_sockets:
        jewels_in_tree.append((i, node))
    if node in keystones:
        keystones_in_tree.append((i, node))
    if node in notables:
        notables_in_tree.append((i, node))

print(f"\n{'=' * 60}")
print(f"Special Nodes in Generated Tree:")
print(f"{'=' * 60}")

if masteries_in_tree:
    print(f"\n✓ Found {len(masteries_in_tree)} mastery nodes:")
    for pos, node in masteries_in_tree[:10]:
        node_data = tree_data['nodes'][int(node)]
        name = node_data['name'] if 'name' in node_data else 'Unknown'
        print(f"  Position {pos}: Node {node} - {name}")
    print(f"\nNOTE: Mastery nodes need masteryEffects selected!")
    print(f"Current masteryEffects: {spec.get('masteryEffects', 'EMPTY')}")

if jewels_in_tree:
    print(f"\n✓ Found {len(jewels_in_tree)} jewel socket nodes:")
    for pos, node in jewels_in_tree[:5]:
        print(f"  Position {pos}: Node {node}")

if keystones_in_tree:
    print(f"\n✓ Found {len(keystones_in_tree)} keystone nodes:")
    for pos, node in keystones_in_tree[:10]:
        node_data = tree_data['nodes'][int(node)]
        name = node_data['name'] if 'name' in node_data else 'Unknown'
        print(f"  Position {pos}: Node {node} - {name}")

if notables_in_tree:
    print(f"\n✓ Found {len(notables_in_tree)} notable nodes")

if not masteries_in_tree and not jewels_in_tree and not keystones_in_tree:
    print("\n✓ No special nodes (masteries, jewels, keystones) found")

# Check the difference
print(f"\n{'=' * 60}")
print(f"Summary:")
print(f"{'=' * 60}")
print(f"Nodes in XML: {len(nodes)}")
print(f"Nodes showing in PoB: 89")
print(f"Missing: {len(nodes) - 89}")
print(f"\nPossible causes:")
print(f"  - Mastery nodes without effects: {len(masteries_in_tree)}")
print(f"  - Jewel sockets (usually counted): {len(jewels_in_tree)}")
print(f"  - Other special node types")
