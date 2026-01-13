"""
Create a mapping between array indices and PoB node IDs
This is needed to export optimized trees to PoB format
"""
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_node_mapping_from_builds(pob_builds_dir: str, output_file: str):
    """
    Create index -> node_id mapping by analyzing all builds
    
    Args:
        pob_builds_dir: Path to PoB Builds directory
        output_file: Where to save the node mapping
    """
    builds_dir = Path(pob_builds_dir)
    
    # Collect all unique node IDs from all builds
    all_node_ids = set()
    
    xml_files = list(builds_dir.glob("*.xml"))
    print(f"Scanning {len(xml_files)} builds to find all passive tree nodes...")
    
    for xml_file in xml_files:
        if xml_file.name.startswith("~~"):
            continue
            
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Find Tree/Spec/nodes attribute
            tree_elem = root.find('Tree')
            if tree_elem is not None:
                spec_elem = tree_elem.find('Spec')
                if spec_elem is not None:
                    nodes_str = spec_elem.get('nodes', '')
                    if nodes_str:
                        # Parse comma-separated node IDs
                        node_ids = [int(n) for n in nodes_str.split(',') if n.strip()]
                        all_node_ids.update(node_ids)
                        if len(all_node_ids) < 50:  # Only print for first few
                            print(f"  {xml_file.name}: {len(node_ids)} nodes")
        except Exception as e:
            pass  # Skip files that can't be parsed
    
    if not all_node_ids:
        print("\n[ERROR] No nodes found! Check that XML files have Tree/Spec/nodes data.")
        return None
    
    print(f"\nFound {len(all_node_ids)} unique passive tree nodes across all builds")
    
    # Sort node IDs and create index mapping
    sorted_nodes = sorted(all_node_ids)
    
    # Create bidirectional mapping
    # Convert node IDs to strings for JSON keys
    mapping = {
        'index_to_node': {str(i): node_id for i, node_id in enumerate(sorted_nodes)},
        'node_to_index': {str(node_id): i for i, node_id in enumerate(sorted_nodes)},
        'total_nodes': len(sorted_nodes)
    }
    
    # Save mapping
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"[OK] Created node mapping with {len(sorted_nodes)} unique nodes")
    print(f"  Saved to: {output_path}")
    print(f"\nSample node IDs: {sorted_nodes[:10]}")
    print(f"Max node ID: {sorted_nodes[-1]}")
    
    return mapping


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create node ID mapping")
    parser.add_argument(
        "--pob-dir",
        default="../PathOfBuilding/src/Builds",
        help="Path to PoB Builds directory"
    )
    parser.add_argument(
        "--output",
        default="./pob_data/tree_data/node_mapping.json",
        help="Output file for node mapping"
    )
    
    args = parser.parse_args()
    
    create_node_mapping_from_builds(args.pob_dir, args.output)
