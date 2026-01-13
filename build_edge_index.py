"""Build edge index for graph model using real tree edges"""
import json

# Load real edges
with open('pob_data/tree_data/real_tree_edges.json') as f:
    edges = json.load(f)

# Load node mapping
with open('pob_data/tree_data/node_mapping.json') as f:
    mapping = json.load(f)
    n2i = {int(k): int(v) for k, v in mapping['node_to_index'].items()}

# Build edge list
edge_list = []
skipped = 0

for src, dsts in edges.items():
    try:
        src_id = int(src)
        if src_id in n2i:
            src_idx = n2i[src_id]
            for dst in dsts:
                try:
                    dst_id = int(dst)
                    if dst_id in n2i:
                        dst_idx = n2i[dst_id]
                        edge_list.append([src_idx, dst_idx])
                except ValueError:
                    skipped += 1
    except ValueError:
        skipped += 1

print(f"Total edges between mapped nodes: {len(edge_list)}")
print(f"Skipped {skipped} invalid edges")

# Save
with open('pob_data/tree_data/edge_index.json', 'w') as f:
    json.dump(edge_list, f)

print("✓ Saved to pob_data/tree_data/edge_index.json")

# Verify bidirectional
bidirectional = []
edge_set = set()
for src, dst in edge_list:
    if (src, dst) not in edge_set:
        edge_set.add((src, dst))
        bidirectional.append([src, dst])
    if (dst, src) not in edge_set:
        edge_set.add((dst, src))
        bidirectional.append([dst, src])

print(f"Bidirectional edges: {len(bidirectional)}")
