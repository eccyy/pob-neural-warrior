"""
Convert poe.ninja ladder data to training format
Note: This data doesn't have passive trees, so it's limited for full training
"""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.skill_database import SKILL_DATABASE, get_skill_index


def convert_poeninja_to_training(
    poeninja_file: str = "../pob_data/poe_ninja/Keepers/ladder_1000_builds.json",
    output_file: str = "./training_data/poeninja_builds.json"
):
    """
    Convert poe.ninja ladder data to training format
    
    WARNING: poe.ninja data doesn't include passive trees or gear details,
    so this creates synthetic/random data for those features. 
    For best results, use actual PoB builds with import_training_data.py
    """
    print("="*60)
    print("Converting poe.ninja Data to Training Format")
    print("="*60)
    print("\n⚠️  WARNING: poe.ninja data doesn't include passive trees!")
    print("   This will generate random trees - not ideal for training.")
    print("   Consider using real PoB builds instead.\n")
    
    # Load poe.ninja data
    poeninja_path = Path(poeninja_file)
    if not poeninja_path.exists():
        print(f"❌ File not found: {poeninja_file}")
        return []
    
    with open(poeninja_path, 'r') as f:
        ninja_builds = json.load(f)
    
    print(f"Loaded {len(ninja_builds)} builds from poe.ninja")
    
    training_data = []
    
    for i, build in enumerate(ninja_builds[:100]):  # Limit to 100 for now
        # Generate random tree (since poe.ninja doesn't provide this)
        # In reality, you'd need the actual passive tree
        tree_vec = [0.0] * 1500
        num_nodes = np.random.randint(80, 120)  # Typical build uses 80-120 nodes
        random_nodes = np.random.choice(1500, num_nodes, replace=False)
        for node_idx in random_nodes:
            tree_vec[node_idx] = 1.0
        
        # Generate random gear vector (since poe.ninja doesn't provide gear)
        gear_vec = list(np.random.rand(500) * 0.5)  # Random gear stats
        
        # Generate random gem vector
        gem_vec = list(np.random.rand(100) * 0.5)
        
        # Encode skill
        skill_name = build.get('main_skill', 'Unknown')
        skill_idx = get_skill_index(skill_name)
        skill_vec = [0.0] * len(SKILL_DATABASE)
        if skill_idx is not None:
            skill_vec[skill_idx] = 1.0
        else:
            skill_vec[0] = 1.0  # Default to first skill
        
        # Create training sample
        training_sample = {
            'filename': f'poeninja_{i}.json',
            'tree': tree_vec,
            'gear': gear_vec,
            'gems': gem_vec,
            'skill': skill_vec,
            'allocated_nodes': [],  # Unknown
            'class': build.get('class', 'Unknown'),
            'level': build.get('level', 90),
            'main_skill': skill_name,
            # Target stats from poe.ninja
            'dps': build.get('dps', 0),
            'life': build.get('life', 0),
            'es': build.get('energy_shield', 0),
            'ehp': build.get('life', 0) + build.get('energy_shield', 0)
        }
        
        training_data.append(training_sample)
        
        if (i + 1) % 25 == 0:
            print(f"  Processed {i + 1} builds...")
    
    # Save
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(training_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ Converted {len(training_data)} builds")
    print(f"  Saved to: {output_path}")
    print(f"{'='*60}")
    
    # Statistics
    avg_dps = sum(b['dps'] for b in training_data) / len(training_data)
    avg_life = sum(b['life'] for b in training_data) / len(training_data)
    avg_es = sum(b['es'] for b in training_data) / len(training_data)
    
    print(f"\nDataset Statistics:")
    print(f"  Average DPS: {avg_dps:.0f}")
    print(f"  Average Life: {avg_life:.0f}")
    print(f"  Average ES: {avg_es:.0f}")
    
    print(f"\n⚠️  REMINDER: This data has random passive trees!")
    print(f"   For actual tree optimization, import real PoB builds:")
    print(f"   python scripts/import_training_data.py")
    
    return training_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert poe.ninja data to training format")
    parser.add_argument(
        "--input",
        default="../pob_data/poe_ninja/Keepers/ladder_1000_builds.json",
        help="Path to poe.ninja JSON file"
    )
    parser.add_argument(
        "--output",
        default="./training_data/poeninja_builds.json",
        help="Output file for training data"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of builds to process"
    )
    
    args = parser.parse_args()
    
    convert_poeninja_to_training(args.input, args.output)
