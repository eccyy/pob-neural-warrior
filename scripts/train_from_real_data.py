"""
Train the model using real PoB builds
"""
import json
import sys
from pathlib import Path
import torch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.train import train_model


def load_training_data(data_file: str):
    """Load imported PoB builds"""
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} builds from {data_file}")
    return data


def prepare_training_data(builds_data):
    """
    Convert imported builds to training format
    
    Returns:
        List of tuples: (tree_vec, gear_vec, gem_vec, skill_vec, target_performance)
    """
    training_samples = []
    
    for build in builds_data:
        # Input features
        tree_vec = torch.tensor(build['tree'], dtype=torch.float32)
        gear_vec = torch.tensor(build['gear'], dtype=torch.float32)
        gem_vec = torch.tensor(build['gems'], dtype=torch.float32)
        skill_vec = torch.tensor(build['skill'], dtype=torch.float32)
        
        # Target: normalized performance
        # DPS / 100k, Life / 5k, ES / 5k (same normalization as training)
        dps_norm = build['dps'] / 100000.0
        life_norm = build['life'] / 5000.0
        es_norm = build['es'] / 5000.0
        
        target = torch.tensor([dps_norm, life_norm, es_norm], dtype=torch.float32)
        
        training_samples.append((tree_vec, gear_vec, gem_vec, skill_vec, target))
    
    return training_samples


def train_from_real_builds(
    data_file: str = "./training_data/imported_builds.json",
    epochs: int = 50,
    batch_size: int = 16
):
    """
    Train model on real PoB builds
    
    Args:
        data_file: Path to imported builds JSON
        epochs: Number of training epochs
        batch_size: Batch size for training
    """
    print("="*60)
    print("Training on Real PoB Builds")
    print("="*60)
    
    # Load data
    builds_data = load_training_data(data_file)
    
    if len(builds_data) < 5:
        print(f"\n⚠️  Warning: Only {len(builds_data)} builds available.")
        print("   For good results, import at least 10-20 diverse builds.")
        print("   You can download builds from pobb.in or poe.ninja")
        return
    
    # Prepare training data
    print("\nPreparing training data...")
    training_samples = prepare_training_data(builds_data)
    
    # Split into train/val (80/20)
    split_idx = int(len(training_samples) * 0.8)
    train_data = training_samples[:split_idx]
    val_data = training_samples[split_idx:]
    
    print(f"  Training samples: {len(train_data)}")
    print(f"  Validation samples: {len(val_data)}")
    
    # Train the model
    print(f"\nTraining for {epochs} epochs...")
    model, history = train_model(
        train_data=train_data,
        val_data=val_data,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=0.001
    )
    
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print("\nModel saved to: ./checkpoints/best_model.pt")
    print("You can now run optimization with the trained model:")
    print("  python main.py optimize")
    
    return model, history


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train model on real PoB builds")
    parser.add_argument(
        "--data",
        default="./training_data/imported_builds.json",
        help="Path to imported builds JSON"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size"
    )
    
    args = parser.parse_args()
    
    train_from_real_builds(
        data_file=args.data,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
