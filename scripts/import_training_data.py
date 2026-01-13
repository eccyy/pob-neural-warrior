"""
Import multiple PoB builds to create training dataset
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration.pob_importer import PoBImporter


def import_builds_from_directory(pob_builds_dir: str, output_file: str):
    """
    Import all .xml builds from PoB Builds directory
    
    Args:
        pob_builds_dir: Path to PathOfBuilding/src/Builds/
        output_file: Where to save the training dataset
    """
    importer = PoBImporter()
    builds_dir = Path(pob_builds_dir)
    
    training_data = []
    
    # Find all XML files
    xml_files = list(builds_dir.glob("*.xml"))
    print(f"Found {len(xml_files)} XML files in {builds_dir}")
    
    for xml_file in xml_files:
        if xml_file.name.startswith("~~"):
            # Skip temp files
            continue
        
        # Check tree version first
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_file)
            spec = tree.getroot().find('.//Spec')
            if spec is not None:
                tree_version = spec.get('treeVersion', '')
                if tree_version != '3_27':
                    continue  # Skip non-3.27 builds
            else:
                continue  # Skip builds without Spec
        except:
            continue  # Skip unparseable files
            
        print(f"\nImporting: {xml_file.name}")
        try:
            result = importer.import_from_file(str(xml_file))
            
            if result and 'features' in result:
                # Extract data from the correct structure
                metadata = result.get('metadata', {})
                features = result.get('features', {})
                targets = result.get('targets', {})
                
                # Convert numpy arrays to lists for JSON serialization
                tree_list = features.get('tree', []).tolist() if hasattr(features.get('tree', []), 'tolist') else list(features.get('tree', []))
                gear_list = features.get('gear', []).tolist() if hasattr(features.get('gear', []), 'tolist') else list(features.get('gear', []))
                gems_list = features.get('gems', []).tolist() if hasattr(features.get('gems', []), 'tolist') else list(features.get('gems', []))
                skill_list = features.get('skill', []).tolist() if hasattr(features.get('skill', []), 'tolist') else list(features.get('skill', []))
                
                # Count allocated nodes from the tree
                allocated_count = int(sum(tree_list)) if tree_list else 0
                
                build_data = {
                    'filename': xml_file.name,
                    'tree': tree_list,
                    'gear': gear_list,
                    'gems': gems_list,
                    'skill': skill_list,
                    'allocated_nodes': allocated_count,  # Use actual count from tree
                    'class': metadata.get('class', 'Unknown'),
                    'level': metadata.get('level', 100),
                    # Target stats (what we want to optimize for)
                    'dps': targets.get('dps', 0),
                    'life': targets.get('life', 0),
                    'es': targets.get('es', 0),
                    'ehp': targets.get('life', 0) + targets.get('es', 0)  # Simplified EHP
                }
                
                training_data.append(build_data)
                print(f"  [OK] Imported successfully: {allocated_count} nodes, "
                      f"DPS: {build_data['dps']:.0f}, Life: {build_data['life']}, ES: {build_data['es']}")
            else:
                print(f"  [FAIL] Failed to import (no data returned)")
                
        except Exception as e:
            print(f"  [ERROR] Error: {e}")
    
    # Save training data
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(training_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Imported {len(training_data)} builds successfully")
    print(f"Saved to: {output_path}")
    print(f"{'='*60}")
    
    # Print statistics
    if training_data:
        avg_nodes = sum(b['allocated_nodes'] for b in training_data) / len(training_data)
        avg_dps = sum(b['dps'] for b in training_data) / len(training_data)
        avg_life = sum(b['life'] for b in training_data) / len(training_data)
        
        print(f"\nDataset Statistics:")
        print(f"  Average nodes allocated: {avg_nodes:.0f}")
        print(f"  Average DPS: {avg_dps:.0f}")
        print(f"  Average Life: {avg_life:.0f}")
    
    return training_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import PoB builds for training")
    parser.add_argument(
        "--pob-dir",
        default="../PathOfBuilding/src/Builds",
        help="Path to PoB Builds directory"
    )
    parser.add_argument(
        "--output",
        default="./training_data/imported_builds.json",
        help="Output file for training dataset"
    )
    
    args = parser.parse_args()
    
    import_builds_from_directory(args.pob_dir, args.output)
