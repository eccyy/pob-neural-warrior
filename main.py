"""
Main orchestration script for PoE Build Optimizer
Ties together data collection, training, and optimization
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import torch

# Add paths
sys.path.append(str(Path(__file__).parent))

from training.data_collection import PoeNinjaScraper, BuildDataProcessor
from training.train import Trainer, create_dataloaders
from training.genetic_optimizer import GeneticOptimizer, Build
from models.multi_component import MultiComponentBuilder
from integration.pob_importer import PoBImporter
from integration.pob_bridge import PoBExporter


def collect_data(league: str, num_builds: int = 10000):
    """Step 1: Collect training data from poe.ninja"""
    print("=" * 60)
    print("STEP 1: Data Collection")
    print("=" * 60)
    
    scraper = PoeNinjaScraper()
    builds = scraper.scrape_ladder(league, limit=num_builds)
    scraper.save_builds(builds, league)
    
    processor = BuildDataProcessor()
    processed = processor.process_builds(builds, validate=False)
    
    # Split into train/val
    split_idx = int(0.8 * len(processed))
    train_data = processed[:split_idx]
    val_data = processed[split_idx:]
    
    processor.save_dataset(train_data, f"../pob_data/processed/{league}_train.json")
    processor.save_dataset(val_data, f"../pob_data/processed/{league}_val.json")
    
    print(f"Collected {len(train_data)} training builds")
    print(f"Collected {len(val_data)} validation builds")


def train_model(
    train_file: str,
    val_file: str,
    epochs: int = 100,
    batch_size: int = 32
):
    """Step 2: Train the neural network"""
    print("\n" + "=" * 60)
    print("STEP 2: Model Training")
    print("=" * 60)
    
    model = MultiComponentBuilder()
    
    train_loader, val_loader = create_dataloaders(
        train_file=train_file,
        val_file=val_file,
        batch_size=batch_size
    )
    
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        learning_rate=1e-4,
        checkpoint_dir="./checkpoints"
    )
    
    trainer.train(num_epochs=epochs, early_stop_patience=10)
    
    print("Training complete!")


def optimize_build(
    model_path: str,
    base_build_path: Optional[str] = None,
    generations: int = 100
):
    """Step 3: Optimize a build using genetic algorithm"""
    print("\n" + "=" * 60)
    print("STEP 3: Build Optimization")
    print("=" * 60)
    
    # Load model
    model = MultiComponentBuilder()
    checkpoint = torch.load(model_path, weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    # Load base build if provided
    base_build = None
    if base_build_path:
        # Load from file
        pass
    
    # Run optimization
    optimizer = GeneticOptimizer(
        model=model,
        population_size=100,
        elite_size=10,
        mutation_rate=0.1
    )
    
    best_build, history = optimizer.optimize(
        base_build=base_build,
        num_generations=generations
    )
    
    print(f"\nOptimization Results:")
    print(f"Best fitness: {best_build.fitness:.2f}")
    print(f"Allocated tree points: {int(best_build.tree.sum())}")
    
    # Save optimized build
    output_path = Path("./optimized_builds/best_build.json")
    output_path.parent.mkdir(exist_ok=True)
    
    import json
    with open(output_path, 'w') as f:
        json.dump({
            'tree': best_build.tree.tolist(),
            'gear': best_build.gear.tolist(),
            'gems': best_build.gems.tolist(),
            'fitness': float(best_build.fitness)
        }, f, indent=2)
    
    print(f"Saved optimized build to {output_path}")


def import_pob_build(xml_path: str):
    """Import a PoB build and display its features"""
    print("=" * 60)
    print("Importing PoB Build")
    print("=" * 60)
    
    importer = PoBImporter()
    build = importer.import_from_file(xml_path)
    
    if build:
        print(f"\n✓ Successfully imported build from {xml_path}")
        print(f"\nBuild Info:")
        print(f"  Class: {build['metadata'].get('class', 'Unknown')}")
        print(f"  Level: {build['metadata'].get('level', '?')}")
        print(f"  Ascendancy: {build['metadata'].get('ascendancy', 'None')}")
        print(f"  Main Skill: {build['metadata'].get('main_skill', 'Unknown')}")
        print(f"  Allocated Nodes: {build['metadata'].get('allocated_nodes', 0)}")
        
        # Save processed build
        output_path = Path("./imported_builds/build.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        import numpy as np
        
        # Convert numpy arrays to lists for JSON
        serializable = {
            'metadata': build['metadata'],
            'features': {
                'tree': build['features']['tree'].tolist(),
                'gear': build['features']['gear'].tolist(),
                'gems': build['features']['gems'].tolist(),
                'skill': build['features']['skill'].tolist()
            },
            'targets': build['targets']
        }
        
        with open(output_path, 'w') as f:
            json.dump(serializable, f, indent=2)
        
        print(f"\n✓ Saved processed build to {output_path}")
    else:
        print("✗ Failed to import build")


def export_pob_build(build_json: str, output_xml: str):
    """Export optimized build to PoB XML format"""
    print("=" * 60)
    print("Exporting to PoB Format")
    print("=" * 60)
    
    import json
    with open(build_json, 'r') as f:
        build_data = json.load(f)
    
    exporter = PoBExporter()
    exporter.export_build(
        build_data,
        output_xml,
        build_name="NN Optimized Build"
    )
    
    print(f"\n✓ Exported build to {output_xml}")
    print("You can now import this file in Path of Building!")


def full_pipeline(league: str, num_builds: int = 1000):
    """Run the complete pipeline"""
    print("=" * 60)
    print("PoE Build Optimizer - Full Pipeline")
    print("=" * 60)
    
    # Step 1: Collect data
    collect_data(league, num_builds)
    
    # Step 2: Train model
    train_file = f"../pob_data/processed/{league}_train.json"
    val_file = f"../pob_data/processed/{league}_val.json"
    train_model(train_file, val_file, epochs=50, batch_size=32)
    
    # Step 3: Optimize build
    model_path = "./checkpoints/best_model.pt"
    optimize_build(model_path, generations=100)
    
    print("\n" + "=" * 60)
    print("Pipeline Complete!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PoE Build Optimizer")
    parser.add_argument(
        'command',
        choices=['collect', 'train', 'optimize', 'full', 'import-pob', 'export-pob', 'train-graph'],
        help='Command to run'
    )
    parser.add_argument(
        '--league',
        type=str,
        default='Keepers',
        help='League name for data collection'
    )
    parser.add_argument(
        '--num-builds',
        type=int,
        default=1000,
        help='Number of builds to collect'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='Number of training epochs'
    )
    parser.add_argument(
        '--generations',
        type=int,
        default=100,
        help='Number of GA generations'
    )
    parser.add_argument(
        '--model-path',
        type=str,
        default='./checkpoints/best_model.pt',
        help='Path to trained model'
    )
    parser.add_argument(
        '--train-file',
        type=str,
        help='Path to training data'
    )
    parser.add_argument(
        '--val-file',
        type=str,
        help='Path to validation data'
    )
    parser.add_argument(
        '--xml-path',
        type=str,
        help='Path to PoB XML file for import'
    )
    parser.add_argument(
        '--build-json',
        type=str,
        help='Path to build JSON file for export'
    )
    parser.add_argument(
        '--output-xml',
        type=str,
        default='./exported_build.xml',
        help='Output path for exported PoB XML'
    )
    
    args = parser.parse_args()
    
    if args.command == 'collect':
        collect_data(args.league, args.num_builds)
    
    elif args.command == 'train':
        if not args.train_file or not args.val_file:
            print("Error: --train-file and --val-file required for training")
            sys.exit(1)
        train_model(args.train_file, args.val_file, args.epochs)
    
    elif args.command == 'optimize':
        optimize_build(args.model_path, generations=args.generations)
    
    elif args.command == 'import-pob':
        if not args.xml_path:
            print("Error: --xml-path required for import")
            sys.exit(1)
        import_pob_build(args.xml_path)
    
    elif args.command == 'export-pob':
        if not args.build_json:
            print("Error: --build-json required for export")
            sys.exit(1)
        export_pob_build(args.build_json, args.output_xml)
    
    elif args.command == 'train-graph':
        """Train the graph-aware model using policy gradient"""
        from training.graph_tree_trainer import PolicyGradientTrainer, load_training_data
        from models.graph_tree_builder import GraphTreeBuilder, load_edge_index_from_builds
        import torch
        
        print("Graph Tree Training with Policy Gradient")
        print("=" * 50)
        
        # Load edge connectivity
        print("Loading tree structure...")
        edge_index = load_edge_index_from_builds(
            "./pob_data/tree_data",
            "./pob_data/tree_data/node_mapping.json"
        )
        print(f"✓ Loaded {edge_index.size(1)} edges")
        
        # Create model
        print("Creating model...")
        model = GraphTreeBuilder(
            num_nodes=412,
            edge_index=edge_index
        )
        print(f"✓ Model created with {sum(p.numel() for p in model.parameters()):,} parameters")
        
        # Load training data
        print("Loading training data...")
        train_data = load_training_data("./training_data/imported_builds_327.json")
        print(f"✓ Loaded {len(train_data)} builds")
        
        # Create trainer
        trainer = PolicyGradientTrainer(model, learning_rate=1e-4)
        
        # Train
        print("\nStarting training...")
        history = trainer.train(
            train_data,
            num_epochs=args.epochs,
            batch_size=args.batch_size
        )
        
        print("\n✓ Training complete!")
    
    elif args.command == 'full':
        full_pipeline(args.league, args.num_builds)
