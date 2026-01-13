# Getting Started with PoE Build Optimizer

This guide will walk you through setting up and using the neural network-based Path of Building optimizer.

## Overview

The optimizer uses a **three-phase approach**:

1. **Data Collection**: Scrape top builds from poe.ninja and poedb
2. **Training**: Train a neural network to predict build performance
3. **Optimization**: Use genetic algorithm + NN to find optimal builds

## Architecture

```
┌─────────────────────────────────────────────┐
│  Data Sources                               │
│  - poe.ninja ladder (10k+ builds)          │
│  - poedb.tw (enemy stats)                  │
│  - PoE API (passive tree)                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Neural Network (Surrogate Model)          │
│  - Encodes: Tree, Gear, Gems               │
│  - Learns: Cross-component synergies       │
│  - Predicts: DPS, EHP, Time-to-Kill        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Genetic Algorithm                          │
│  - Population: 100 builds                  │
│  - Fitness: NN prediction (fast!)          │
│  - Evolution: 100 generations              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Optimized Build                            │
│  - Best passive tree allocation            │
│  - Recommended gear stats                  │
│  - Optimal gem setup                       │
└─────────────────────────────────────────────┘
```

## Installation

### 1. Prerequisites

- Python 3.9 or higher
- CUDA (optional, for GPU training)
- 8GB+ RAM (16GB recommended)

### 2. Install Dependencies

```bash
cd pob_neural_network
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
python -c "import torch; print(torch.__version__)"
python -c "import requests; print('Requests OK')"
```

## Quick Start

### Option 1: Full Pipeline (Recommended for First Run)

Run the complete pipeline: data collection → training → optimization

```bash
python main.py full --league "Settlers" --num-builds 1000 --epochs 50
```

This will:
1. Scrape 1000 builds from poe.ninja
2. Train the neural network for 50 epochs
3. Optimize a build using genetic algorithm
4. Save results to `./optimized_builds/`

**Expected time**: 2-4 hours (depending on hardware)

### Option 2: Step-by-Step

#### Step 1: Collect Data

```bash
# Scrape current league ladder
python main.py collect --league "Settlers" --num-builds 10000

# This saves data to: ../pob_data/poe_ninja/Settlers/
```

#### Step 2: Train Model

```bash
python main.py train \
  --train-file "../pob_data/processed/Settlers_train.json" \
  --val-file "../pob_data/processed/Settlers_val.json" \
  --epochs 100
```

Training metrics will be saved to `./checkpoints/training_history.json`

#### Step 3: Optimize Build

```bash
python main.py optimize \
  --model-path "./checkpoints/best_model.pt" \
  --generations 100
```

## Advanced Usage

### Scrape Additional Data

#### Enemy Database (for realistic calculations)

```bash
cd ../pob_data/scrapers
python poedb_scraper.py
```

This scrapes enemy stats (life, resistances, damage) for:
- Major endgame bosses (Sirus, Maven, etc.)
- Map monsters at various tiers

#### Passive Tree Data

```bash
cd ../pob_data/scrapers
python poedb_scraper.py  # Also includes tree scraper
```

### Custom Training

If you want more control over training:

```python
from training.train import Trainer, create_dataloaders
from models.multi_component import MultiComponentBuilder

# Create model
model = MultiComponentBuilder(
    tree_dim=1500,
    gear_dim=500,
    gem_dim=100,
    hidden_dim=512
)

# Load data
train_loader, val_loader = create_dataloaders(
    train_file="path/to/train.json",
    val_file="path/to/val.json",
    batch_size=32
)

# Train
trainer = Trainer(
    model=model,
    train_loader=train_loader,
    val_loader=val_loader,
    learning_rate=1e-4
)

trainer.train(num_epochs=100)
```

### Custom Optimization

```python
from training.genetic_optimizer import GeneticOptimizer, Build
from models.multi_component import MultiComponentBuilder
import torch
import numpy as np

# Load trained model
model = MultiComponentBuilder()
checkpoint = torch.load("checkpoints/best_model.pt")
model.load_state_dict(checkpoint['model_state_dict'])

# Create optimizer
optimizer = GeneticOptimizer(
    model=model,
    population_size=200,  # Larger population
    elite_size=20,
    mutation_rate=0.15,   # Higher mutation
    crossover_rate=0.8
)

# Optional: Start from existing build
base_build = Build(
    tree=np.zeros(1500),  # Your current tree
    gear=np.zeros(500),   # Your current gear
    gems=np.zeros(100)    # Your current gems
)

# Optimize
best_build, history = optimizer.optimize(
    base_build=base_build,
    num_generations=200
)

print(f"Best fitness: {best_build.fitness}")
```

## Understanding the Results

### Optimized Build Output

The optimizer produces a JSON file with:

```json
{
  "tree": [0, 1, 1, 0, ...],  // 1500 values (1 = allocated)
  "gear": [0.8, 0.3, ...],     // 500 values (normalized 0-1)
  "gems": [0.9, 0.7, ...],     // 100 values (normalized 0-1)
  "fitness": 1250000.0         // Combined DPS + EHP score
}
```

### Interpreting Gear Stats

Gear vector contains aggregated stats:
- Indices 0-9: Life (total, %, flat, regen, etc.)
- Indices 10-19: Resistances (fire, cold, lightning, chaos)
- Indices 20-39: Damage stats
- Indices 40-59: Defense stats
- etc.

See `utils/features.py` for complete mapping.

### Training Metrics

Monitor training progress:

```python
import json
with open("checkpoints/training_history.json") as f:
    history = json.load(f)

# Plot losses
import matplotlib.pyplot as plt
plt.plot([h['total'] for h in history['train']], label='Train')
plt.plot([h['total'] for h in history['val']], label='Val')
plt.legend()
plt.show()
```

## Troubleshooting

### Out of Memory (OOM)

Reduce batch size:
```bash
python main.py train --batch-size 16  # Default is 32
```

### Slow Training

- Enable GPU: Install CUDA-enabled PyTorch
- Reduce model size: Edit `models/multi_component.py`
- Use fewer builds: `--num-builds 1000`

### Poor Optimization Results

- Train longer: `--epochs 200`
- Collect more data: `--num-builds 10000`
- Tune GA parameters: Edit `training/genetic_optimizer.py`

### poe.ninja API Rate Limits

The scraper includes rate limiting (0.5s delay). If you hit limits:
- Reduce batch size in `data_collection.py`
- Increase sleep time between requests

## Next Steps

1. **Validate Results**: Import optimized build into Path of Building
2. **Fine-tune**: Adjust fitness weights in `train.py`
3. **Expand Dataset**: Scrape multiple leagues
4. **Custom Objectives**: Modify loss function for specific build goals

## Project Structure

```
pob_neural_network/
├── main.py                    # Main orchestration script
├── requirements.txt           # Python dependencies
├── models/                    # Neural network architectures
│   └── multi_component.py    # Main model
├── training/                  # Training and optimization
│   ├── data_collection.py   # poe.ninja scraper
│   ├── train.py             # Training loop
│   └── genetic_optimizer.py # GA search
└── utils/                    # Utilities
    └── features.py          # Feature extraction

pob_data/
├── poe_ninja/               # Scraped builds
├── poedb/                   # Enemy data
├── tree_data/               # Passive tree
└── processed/               # Training datasets
```

## Contributing

This is an open research project. Contributions welcome:
- Better feature extraction
- Alternative model architectures
- Integration with Path of Building Lua
- Improved enemy data scraping

## References

- Path of Building: https://github.com/PathOfBuildingCommunity/PathOfBuilding
- poe.ninja: https://poe.ninja
- poedb.tw: https://poedb.tw
- PoE API: https://www.pathofexile.com/developer/docs

## Support

For issues and questions:
1. Check troubleshooting section
2. Review documentation in `*.md` files
3. Check existing GitHub issues
