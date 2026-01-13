"""
Visualization utilities for the PoE Build Optimizer
Creates diagrams and plots for understanding the system
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import json
from pathlib import Path


def plot_training_history(history_file: str, output_file: str = "training_curves.png"):
    """Plot training and validation loss curves"""
    with open(history_file) as f:
        history = json.load(f)
    
    train_losses = [h['total'] for h in history['train']]
    val_losses = [h['total'] for h in history['val']]
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Training Metrics', fontsize=16)
    
    # Total loss
    axes[0, 0].plot(train_losses, label='Train', alpha=0.8)
    axes[0, 0].plot(val_losses, label='Val', alpha=0.8)
    axes[0, 0].set_title('Total Loss')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # DPS loss
    dps_train = [h['dps'] for h in history['train']]
    dps_val = [h['dps'] for h in history['val']]
    axes[0, 1].plot(dps_train, label='Train', alpha=0.8)
    axes[0, 1].plot(dps_val, label='Val', alpha=0.8)
    axes[0, 1].set_title('DPS Loss')
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # EHP loss
    ehp_train = [h['ehp'] for h in history['train']]
    ehp_val = [h['ehp'] for h in history['val']]
    axes[0, 2].plot(ehp_train, label='Train', alpha=0.8)
    axes[0, 2].plot(ehp_val, label='Val', alpha=0.8)
    axes[0, 2].set_title('EHP Loss')
    axes[0, 2].set_xlabel('Epoch')
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)
    
    # Tree loss
    tree_train = [h['tree'] for h in history['train']]
    tree_val = [h['tree'] for h in history['val']]
    axes[1, 0].plot(tree_train, label='Train', alpha=0.8)
    axes[1, 0].plot(tree_val, label='Val', alpha=0.8)
    axes[1, 0].set_title('Tree Reconstruction Loss')
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Gear loss
    gear_train = [h['gear'] for h in history['train']]
    gear_val = [h['gear'] for h in history['val']]
    axes[1, 1].plot(gear_train, label='Train', alpha=0.8)
    axes[1, 1].plot(gear_val, label='Val', alpha=0.8)
    axes[1, 1].set_title('Gear Loss')
    axes[1, 1].set_xlabel('Epoch')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    # Gem loss
    gem_train = [h['gem'] for h in history['train']]
    gem_val = [h['gem'] for h in history['val']]
    axes[1, 2].plot(gem_train, label='Train', alpha=0.8)
    axes[1, 2].plot(gem_val, label='Val', alpha=0.8)
    axes[1, 2].set_title('Gem Loss')
    axes[1, 2].set_xlabel('Epoch')
    axes[1, 2].legend()
    axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved training curves to {output_file}")


def plot_optimization_progress(history: list, output_file: str = "optimization_progress.png"):
    """Plot genetic algorithm optimization progress"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Best fitness over generations
    axes[0].plot(history, linewidth=2, color='#2ecc71')
    axes[0].set_title('Best Fitness Over Generations', fontsize=14)
    axes[0].set_xlabel('Generation', fontsize=12)
    axes[0].set_ylabel('Fitness', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(y=max(history), color='r', linestyle='--', alpha=0.5, label='Best')
    axes[0].legend()
    
    # Fitness improvement rate
    improvements = np.diff(history)
    axes[1].bar(range(len(improvements)), improvements, alpha=0.7, color='#3498db')
    axes[1].set_title('Fitness Improvement Per Generation', fontsize=14)
    axes[1].set_xlabel('Generation', fontsize=12)
    axes[1].set_ylabel('Improvement', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved optimization progress to {output_file}")


def create_architecture_diagram(output_file: str = "architecture_diagram.png"):
    """Create a visual diagram of the neural network architecture"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Define colors
    color_input = '#3498db'
    color_encoder = '#9b59b6'
    color_interaction = '#e74c3c'
    color_decoder = '#f39c12'
    color_output = '#2ecc71'
    
    # Helper function to draw box
    def draw_box(x, y, width, height, text, color):
        box = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.1",
            edgecolor='black',
            facecolor=color,
            alpha=0.7,
            linewidth=2
        )
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text,
                ha='center', va='center',
                fontsize=10, fontweight='bold',
                color='white')
    
    # Input layer
    draw_box(0.5, 8, 1.5, 0.8, "Tree\n(1500)", color_input)
    draw_box(0.5, 6.5, 1.5, 0.8, "Gear\n(500)", color_input)
    draw_box(0.5, 5, 1.5, 0.8, "Gems\n(100)", color_input)
    
    # Encoders
    draw_box(3, 8, 1.5, 0.8, "Tree Enc\n(256)", color_encoder)
    draw_box(3, 6.5, 1.5, 0.8, "Gear Enc\n(256)", color_encoder)
    draw_box(3, 5, 1.5, 0.8, "Gem Enc\n(128)", color_encoder)
    
    # Interaction layer
    draw_box(5.5, 6.5, 2, 1.5, "Interaction\nLayer\n(640→512→256)", color_interaction)
    
    # Decoders
    draw_box(8, 8.5, 1.5, 0.8, "Tree Dec\n(1500)", color_decoder)
    draw_box(8, 7, 1.5, 0.8, "Gear Dec\n(50)", color_decoder)
    draw_box(8, 5.5, 1.5, 0.8, "Gem Dec\n(15)", color_decoder)
    draw_box(8, 4, 1.5, 0.8, "Perf Pred\n(3)", color_decoder)
    
    # Arrows
    arrow_props = dict(arrowstyle='->', lw=2, color='black')
    
    # Input to encoder
    for y in [8.4, 6.9, 5.4]:
        ax.annotate('', xy=(3, y), xytext=(2, y),
                   arrowprops=arrow_props)
    
    # Encoder to interaction
    for y in [8.4, 6.9, 5.4]:
        ax.annotate('', xy=(5.5, 7.25), xytext=(4.5, y),
                   arrowprops=arrow_props)
    
    # Interaction to decoders
    for y in [8.9, 7.4, 5.9, 4.4]:
        ax.annotate('', xy=(8, y), xytext=(7.5, 7.25),
                   arrowprops=arrow_props)
    
    # Title
    ax.text(5, 9.5, "Multi-Component Neural Network Architecture",
            ha='center', fontsize=16, fontweight='bold')
    
    # Legend
    legend_elements = [
        mpatches.Patch(color=color_input, label='Input'),
        mpatches.Patch(color=color_encoder, label='Encoder'),
        mpatches.Patch(color=color_interaction, label='Interaction'),
        mpatches.Patch(color=color_decoder, label='Decoder')
    ]
    ax.legend(handles=legend_elements, loc='lower center',
             ncol=4, fontsize=10, frameon=False)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved architecture diagram to {output_file}")


def create_pipeline_flowchart(output_file: str = "pipeline_flowchart.png"):
    """Create a flowchart of the complete pipeline"""
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    def draw_box(x, y, width, height, text, color):
        box = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.1",
            edgecolor='black',
            facecolor=color,
            alpha=0.8,
            linewidth=2
        )
        ax.add_patch(box)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            ax.text(x + width/2, y + height/2 - i*0.2 + (len(lines)-1)*0.1,
                   line, ha='center', va='center',
                   fontsize=9, fontweight='bold')
    
    # Pipeline stages
    stages = [
        (11, "Data Collection\npoe.ninja + poedb", '#3498db'),
        (9.5, "Feature Extraction\n1500 + 500 + 100 dims", '#9b59b6'),
        (8, "Neural Network Training\n100 epochs", '#e74c3c'),
        (6.5, "Model Validation\nR² > 0.85", '#f39c12'),
        (5, "Genetic Algorithm\n100 generations", '#1abc9c'),
        (3.5, "Top-10 Validation\nActual PoB", '#34495e'),
        (2, "Export to XML\nPoB format", '#2ecc71'),
        (0.5, "Optimized Build\nReady to use!", '#27ae60')
    ]
    
    for y, text, color in stages:
        draw_box(2, y, 6, 1, text, color)
    
    # Arrows
    arrow_props = dict(arrowstyle='->', lw=3, color='black')
    for i in range(len(stages) - 1):
        ax.annotate('', xy=(5, stages[i+1][0] + 1),
                   xytext=(5, stages[i][0]),
                   arrowprops=arrow_props)
    
    # Title
    ax.text(5, 11.7, "Complete Optimization Pipeline",
           ha='center', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved pipeline flowchart to {output_file}")


if __name__ == "__main__":
    print("Generating visualizations...")
    
    # Create diagrams
    create_architecture_diagram()
    create_pipeline_flowchart()
    
    # Example: Plot training history (if exists)
    history_file = Path("../checkpoints/training_history.json")
    if history_file.exists():
        plot_training_history(str(history_file))
    
    # Example: Plot optimization progress
    example_history = [100000 + i*5000 + np.random.randint(-1000, 1000)
                      for i in range(100)]
    plot_optimization_progress(example_history)
    
    print("All visualizations generated!")
