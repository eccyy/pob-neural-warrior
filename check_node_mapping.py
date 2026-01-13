"""Check if common starting nodes are in our mapping"""
import json

m = json.load(open('pob_data/tree_data/node_mapping.json'))
n2i = {int(k): int(v) for k, v in m['node_to_index'].items()}

nodes = [44339, 39841, 7388, 52789, 367]
print('Checking common start nodes:')
for n in nodes:
    in_map = n in n2i
    idx = n2i.get(n, "N/A")
    print(f'Node {n}: in_mapping={in_map}, index={idx}')
