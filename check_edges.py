import json

edges = json.load(open('pob_data/tree_data/tree_edges.json'))
print('Total nodes with edges:', len(edges))
print('\nSample nodes:')
for node in list(edges.keys())[:5]:
    print(f'  Node {node}: {len(edges[node])} connections')

scion_start = '42178'
if scion_start in edges:
    print(f'\nScion start ({scion_start}): {len(edges[scion_start])} connections')
    print('  Connected to:', edges[scion_start][:10])
else:
    print(f'\nScion start ({scion_start}): NO EDGES FOUND')

# Check if any of the model's nodes have edges
model_nodes = ['869', '4270', '4492', '12250']
print('\nModel nodes in edge data:')
for node in model_nodes:
    if node in edges:
        print(f'  Node {node}: {len(edges[node])} connections')
    else:
        print(f'  Node {node}: NOT IN EDGES')
