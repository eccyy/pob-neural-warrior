"""
Extract actual tree edges from Path of Building tree data
"""
import json
from pathlib import Path
from lupa import LuaRuntime

def extract_real_edges():
    """Extract edge connectivity from PoB's actual tree data"""
    
    # Read the tree.lua file
    tree_file = Path('../PathOfBuilding/src/TreeData/3_27/tree.lua')
    
    if not tree_file.exists():
        print("Could not find tree data file!")
        return None
    
    print(f"Reading {tree_file}...")
    with open(tree_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Parsing Lua data...")
    lua = LuaRuntime(unpack_returned_tuples=True)
    
    # Execute the Lua code to get the tree table
    tree_data = lua.execute(content)
    
    print("Extracting node connections...")
    edges = {}
    
    if 'nodes' in tree_data:
        nodes = tree_data['nodes']
        total_nodes = 0
        total_edges = 0
        
        for node_id, node_data in nodes.items():
            total_nodes += 1
            if 'out' in node_data and node_data['out']:
                # Convert Lua table to list
                out_nodes = []
                for _, target_id in node_data['out'].items():
                    out_nodes.append(str(target_id))
                
                if out_nodes:
                    edges[str(node_id)] = out_nodes
                    total_edges += len(out_nodes)
            
            if total_nodes % 500 == 0:
                print(f"  Processed {total_nodes} nodes, {total_edges} edges...")
        
        print(f"\n✓ Extracted {total_nodes} nodes with {total_edges} edges")
    else:
        print("No 'nodes' key found in tree data!")
    
    return edges

if __name__ == "__main__":
    print("Extracting real tree edges from PoB tree data...")
    print("=" * 60)
    
    edges = extract_real_edges()
    
    if edges:
        # Save to JSON
        output_file = "pob_data/tree_data/real_tree_edges.json"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(edges, f, indent=2)
        
        print(f"\n✓ Saved to {output_file}")
        
        # Check if our mapped nodes are in the real tree
        print("\nChecking mapped nodes...")
        with open("pob_data/tree_data/node_mapping.json") as f:
            mapping = json.load(f)
            mapped_nodes = set(mapping['node_to_index'].keys())
        
        real_nodes = set(edges.keys())
        
        in_both = mapped_nodes & real_nodes
        print(f"  Mapped nodes: {len(mapped_nodes)}")
        print(f"  Real tree nodes: {len(real_nodes)}")
        print(f"  In both: {len(in_both)} ({100*len(in_both)/len(mapped_nodes):.1f}%)")
        
        # Check start node
        if '39841' in edges:
            print(f"\n✓ Shadow start node 39841 found")
            print(f"  Connects to: {edges['39841'][:10]}")
