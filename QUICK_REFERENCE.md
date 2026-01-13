# Quick Reference Guide - PoE Build Optimizer

## One-Line Commands

```bash
# Complete pipeline (start to finish)
python main.py full --league "Settlers" --num-builds 1000

# Just collect data
python main.py collect --league "Settlers" --num-builds 10000

# Just train model
python main.py train --train-file train.json --val-file val.json --epochs 100

# Just optimize
python main.py optimize --model-path checkpoints/best_model.pt --generations 100
```

## File Structure Quick Reference

```
pob_neural_network/
├── main.py                         # Run this!
├── requirements.txt                # pip install -r requirements.txt
├── GETTING_STARTED.md             # Read this first
├── COMPLETE_DOCUMENTATION.md      # Comprehensive guide
│
├── models/
│   ├── multi_component.py         # Main neural network
│   └── __init__.py
│
├── training/
│   ├── data_collection.py         # Scrape poe.ninja
│   ├── train.py                   # Train the model
│   ├── genetic_optimizer.py       # Optimize builds
│   └── __init__.py
│
├── integration/
│   ├── pob_bridge.py              # Export to PoB
│   └── __init__.py
│
└── utils/
    ├── features.py                # Feature extraction
    └── __init__.py

pob_data/
├── poe_ninja/                     # Scraped builds
├── poedb/                         # Enemy data
├── tree_data/                     # Passive tree
├── processed/                     # Training data
└── scrapers/
    └── poedb_scraper.py          # Data scrapers
```

## Python API Quick Reference

### Training

```python
from training.train import Trainer, create_dataloaders
from models.multi_component import MultiComponentBuilder

# Create model
model = MultiComponentBuilder()

# Load data
train_loader, val_loader = create_dataloaders(
    train_file="train.json",
    val_file="val.json"
)

# Train
trainer = Trainer(model, train_loader, val_loader)
trainer.train(num_epochs=100)
```

### Optimization

```python
from training.genetic_optimizer import GeneticOptimizer, Build
import torch

# Load model
model = MultiComponentBuilder()
model.load_state_dict(torch.load("best_model.pt")['model_state_dict'])

# Optimize
optimizer = GeneticOptimizer(model)
best_build, history = optimizer.optimize(num_generations=100)

print(f"Fitness: {best_build.fitness}")
```

### Integration

```python
from integration.pob_bridge import PoBExporter, PoBImporter

# Export to PoB
exporter = PoBExporter()
exporter.export_build(
    optimized_build=build_dict,
    output_path="my_build.xml",
    build_name="NN Optimized"
)

# Import from PoB
importer = PoBImporter()
build = importer.import_from_file("existing_build.xml")
```

## Configuration Quick Reference

### Model Hyperparameters

```python
MultiComponentBuilder(
    tree_dim=1500,        # Number of tree nodes
    gear_dim=500,         # Gear stat dimensions
    gem_dim=100,          # Gem dimensions
    hidden_dim=512,       # Hidden layer size
    num_gear_slots=10,    # Number of gear slots
    stats_per_slot=5      # Stats per gear slot
)
```

### Training Hyperparameters

```python
Trainer(
    model=model,
    train_loader=train_loader,
    val_loader=val_loader,
    learning_rate=1e-4,          # Adam learning rate
    checkpoint_dir='./checkpoints'
)

trainer.train(
    num_epochs=100,              # Max epochs
    early_stop_patience=10       # Stop if no improvement
)
```

### Genetic Algorithm Parameters

```python
GeneticOptimizer(
    model=model,
    population_size=100,         # Population per generation
    elite_size=10,               # Top builds to keep
    mutation_rate=0.1,           # Probability of mutation
    crossover_rate=0.7           # Probability of crossover
)

optimizer.optimize(
    base_build=None,             # Starting build (optional)
    num_generations=100,         # Max generations
    convergence_threshold=1e-4   # Stop if converged
)
```

## Data Format Reference

### Optimized Build JSON

```json
{
  "tree": [0, 1, 1, 0, ...],     // 1500 binary values
  "gear": [0.8, 0.3, ...],        // 500 float values (0-1)
  "gems": [0.9, 0.7, ...],        // 100 float values (0-1)
  "fitness": 1250000.0            // Combined score
}
```

### Training Data Format

```json
{
  "metadata": {
    "character": "CharName",
    "class": "Ranger",
    "level": 95
  },
  "features": {
    "tree": [...],               // 1500 binary
    "gear": [...],               // 500 floats
    "gems": [...]                // 100 floats
  },
  "targets": {
    "dps": 1500000,
    "life": 5000,
    "es": 0
  }
}
```

## Common Modifications

### Change Fitness Function

Edit `training/train.py`:
```python
class MultiObjectiveLoss(nn.Module):
    def __init__(self):
        self.dps_weight = 0.4      # ← Modify these
        self.ehp_weight = 0.3
        self.tree_weight = 0.15
        self.gear_weight = 0.1
        self.gem_weight = 0.05
```

### Change Population Size

Edit `training/genetic_optimizer.py`:
```python
optimizer = GeneticOptimizer(
    population_size=200,    # ← Increase for better search
    elite_size=20           # ← 10% of population
)
```

### Change Tree Complexity

Edit `models/multi_component.py`:
```python
self.tree_encoder = nn.Sequential(
    nn.Linear(tree_dim, 512),     # ← Increase for more capacity
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(512, 256),          # ← Increase hidden dim
    nn.ReLU()
)
```

## Performance Benchmarks

| Task | CPU (16-core) | GPU (RTX 3080) |
|------|---------------|----------------|
| Data collection | 30 min | N/A |
| Training (100 epochs) | 8 hours | 2 hours |
| Optimization (100 gen) | 4 min | 1 min |
| **Total Pipeline** | **~9 hours** | **~2.5 hours** |

## Memory Requirements

| Component | RAM | VRAM |
|-----------|-----|------|
| Data loading | 2GB | - |
| Training | 4GB | 6GB |
| Optimization | 1GB | 2GB |
| **Total** | **8GB** | **8GB** |

## Troubleshooting Checklist

- [ ] Python 3.9+ installed?
- [ ] Dependencies installed? (`pip install -r requirements.txt`)
- [ ] CUDA available? (`torch.cuda.is_available()`)
- [ ] Enough disk space? (20GB recommended)
- [ ] Data collected? (Check `pob_data/poe_ninja/`)
- [ ] Model trained? (Check `checkpoints/best_model.pt`)

## Key Metrics to Monitor

### During Training
- **Total Loss**: Should decrease steadily
- **DPS Loss**: Should be < 0.1 by epoch 50
- **EHP Loss**: Should be < 0.1 by epoch 50
- **Val Loss**: Should track train loss (not diverge)

### During Optimization
- **Best Fitness**: Should increase over generations
- **Population Diversity**: Should remain > 0.3
- **Convergence**: Usually happens around generation 50-70

## Directory After Full Run

```
pob_neural_network/
├── checkpoints/
│   ├── best_model.pt              # Best model weights
│   ├── training_history.json      # Loss curves
│   └── checkpoint_epoch_*.pt      # Regular checkpoints
│
├── optimized_builds/
│   ├── best_build.json            # Optimized build
│   └── best_build.xml             # PoB format
│
└── logs/
    └── training.log               # Detailed logs

pob_data/
├── poe_ninja/
│   └── Settlers/
│       └── ladder_10000_builds.json
│
├── processed/
│   ├── Settlers_train.json
│   └── Settlers_val.json
│
└── poedb/
    └── enemy_database.json
```

## Next Steps After First Run

1. **Validate Results**
   - Import `optimized_builds/best_build.xml` into Path of Building
   - Check if DPS/EHP match predictions
   - Adjust fitness weights if needed

2. **Improve Model**
   - Collect more data: `--num-builds 20000`
   - Train longer: `--epochs 200`
   - Tune hyperparameters

3. **Customize**
   - Add build-specific constraints
   - Implement custom reward functions
   - Create scenario-specific optimizers

## Resources

- **Documentation**: `GETTING_STARTED.md`, `COMPLETE_DOCUMENTATION.md`
- **Architecture**: `architecture.md`, `PROJECT_OVERVIEW.md`
- **Rewards**: `reward_functions.md`
- **Code**: All `.py` files have docstrings

## Support

Check these in order:
1. This quick reference
2. `GETTING_STARTED.md`
3. `COMPLETE_DOCUMENTATION.md`
4. Code docstrings
5. GitHub issues

---

**TIP**: Bookmark this file for quick command lookup!
