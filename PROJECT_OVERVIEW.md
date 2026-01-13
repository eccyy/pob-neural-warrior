# Neural Network Build Optimizer - Implementation Plan

## Overview

This implementation uses a **surrogate model + genetic algorithm** approach:
1. Train a neural network to predict build performance (fast)
2. Use genetic algorithm to search the massive build space
3. Validate top candidates in real PoB

## Architecture

```
Build Code → Feature Extraction → NN Model → Performance Score
                                      ↓
                          Genetic Algorithm Search
                                      ↓
                          Top Candidates → PoB Validation
```

## Phase 1: Data Pipeline

### Install Dependencies
```bash
pip install PathOfBuildingAPI torch numpy pandas tqdm
```

### Extract Features from PoB Builds
- **Passive Tree**: One-hot vector (1 if allocated, 0 otherwise)
- **Gear Stats**: Aggregate stats from all items
- **Skills**: Active skill gems and support combinations
- **Ascendancy**: Class and ascendancy choice

### Target Variable
- Combined metric: `0.7 * DPS + 0.3 * EHP` (configurable weights)

## Phase 2: Training Data Collection

### Sources
1. **poe.ninja builds**: Top ladder builds
2. **User-generated**: Greedy optimizer results
3. **Synthetic**: Variations of good builds

### Dataset Structure
```python
{
    "build_code": "eNqV...",
    "allocated_nodes": [1234, 5678, ...],
    "gear_stats": {
        "life": 5000,
        "res_fire": 75,
        ...
    },
    "performance": {
        "dps": 1500000,
        "ehp": 250000,
        "score": 1125000
    }
}
```

## Phase 3: Model Architecture

### Surrogate Model (Fast Inference)
```python
import torch.nn as nn

class BuildSurrogate(nn.Module):
    def __init__(self, tree_dim=1500, gear_dim=50):
        super().__init__()
        # Tree branch (sparse, high-dim)
        self.tree_net = nn.Sequential(
            nn.Linear(tree_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU()
        )
        
        # Gear branch (dense, low-dim)
        self.gear_net = nn.Sequential(
            nn.Linear(gear_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU()
        )
        
        # Combined predictor
        self.predictor = nn.Sequential(
            nn.Linear(256 + 64, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()  # Output: normalized score 0-1
        )
    
    def forward(self, tree_vec, gear_vec):
        t = self.tree_net(tree_vec)
        g = self.gear_net(gear_vec)
        x = torch.cat([t, g], dim=1)
        return self.predictor(x) * 10_000_000  # Scale to typical DPS range
```

### Why This Architecture?
- **Separate branches**: Tree and gear have different properties
- **Dropout**: Prevents overfitting on specific builds
- **Skip connections**: Could add for deeper networks

## Phase 4: Genetic Algorithm Search

### Genome Representation
```python
class BuildGenome:
    def __init__(self):
        self.nodes = set()  # Allocated passive nodes
        self.budget = 100   # Point limit
        self.class_start = None  # Starting class
```

### Genetic Operators

#### Mutation
```python
def mutate(genome, mutation_rate=0.1):
    if random.random() < mutation_rate:
        # Add a random connected node
        candidates = get_adjacent_nodes(genome.nodes)
        if candidates and len(genome.nodes) < genome.budget:
            genome.nodes.add(random.choice(candidates))
    
    if random.random() < mutation_rate:
        # Remove a random non-critical node
        removable = [n for n in genome.nodes if not is_path_node(n)]
        if removable:
            genome.nodes.remove(random.choice(removable))
    
    return genome
```

#### Crossover
```python
def crossover(parent1, parent2):
    child = BuildGenome()
    child.class_start = parent1.class_start
    
    # Inherit nodes from both parents
    all_nodes = parent1.nodes | parent2.nodes
    
    # Select subset within budget
    while len(child.nodes) < child.budget and all_nodes:
        node = random.choice(list(all_nodes))
        if can_allocate(child, node):
            child.nodes.add(node)
        all_nodes.discard(node)
    
    return child
```

### GA Loop
```python
def genetic_algorithm(model, initial_build, generations=100, pop_size=50):
    # Initialize population with variations of greedy solution
    population = [mutate(initial_build.copy()) for _ in range(pop_size)]
    
    best_genome = None
    best_score = 0
    
    for gen in range(generations):
        # Evaluate all genomes using NN (fast!)
        scores = []
        for genome in population:
            tree_vec, gear_vec = encode_genome(genome)
            score = model(tree_vec, gear_vec).item()
            scores.append((score, genome))
        
        scores.sort(reverse=True)
        
        # Track best
        if scores[0][0] > best_score:
            best_score = scores[0][0]
            best_genome = scores[0][1]
        
        # Selection (top 20%)
        elite = [g for s, g in scores[:pop_size//5]]
        
        # Breed next generation
        population = elite.copy()  # Keep elite
        while len(population) < pop_size:
            p1, p2 = random.sample(elite, 2)
            child = crossover(p1, p2)
            child = mutate(child)
            population.append(child)
        
        if gen % 10 == 0:
            print(f"Gen {gen}: Best score = {best_score:.0f}")
    
    return best_genome
```

## Phase 5: Integration with PoB GUI

### Updated CLI Script
```python
# python/ml/optimize_cli.py

def optimize_build(build_code, node_budget=40):
    # 1. Parse current build
    build = parse_build(build_code)
    
    # 2. Load trained model
    model = load_model('trained_surrogate.pt')
    model.eval()
    
    # 3. Initialize with greedy baseline
    baseline = greedy_optimize(build, node_budget)
    
    # 4. Run GA to find better solution
    optimized = genetic_algorithm(
        model, 
        baseline, 
        generations=50,
        pop_size=30
    )
    
    # 5. Validate top 3 in real PoB
    candidates = get_top_candidates(optimized, n=3)
    validated = []
    
    for genome in candidates:
        build_code = encode_to_pob(genome)
        real_build = parse_build(build_code)
        real_score = calculate_score(real_build)
        validated.append((real_score, genome))
    
    validated.sort(reverse=True)
    
    # 6. Return best validated build
    return validated[0][1]
```

## Phase 6: File Structure

```
python/ml/
├── __init__.py
├── README.md                 # This file
├── features.py               # Feature extraction from PoB
├── model.py                  # Neural network architecture
├── genetic.py                # GA operators and loop
├── optimize_cli.py           # CLI interface for GUI
├── train.py                  # Training script
├── data/
│   ├── builds_dataset.json   # Training data
│   ├── trained_model.pt      # Model weights
│   └── scaler.pkl            # Feature normalization
└── notebooks/
    ├── 01_data_exploration.ipynb
    ├── 02_model_training.ipynb
    └── 03_ga_tuning.ipynb
```

## Quick Start

### 1. Collect Training Data
```bash
python -m ml.collect_data --source poe.ninja --league Affliction --limit 1000
```

### 2. Train Model
```bash
python -m ml.train --epochs 100 --batch-size 32 --lr 0.001
```

### 3. Test Optimization
```bash
python -m ml.optimize_cli --build-code "eNqV..." --nodes 40
```

### 4. Integrate with GUI
Update [src/Classes/TreeTab.lua](../../src/Classes/TreeTab.lua) `RunGPUOptimizerExternal()`:
```lua
local pythonScript = projectRoot .. "/python/ml/optimize_cli.py"
```

## Performance Expectations

### Greedy Algorithm (Current)
- Speed: ~100ms in Lua
- Quality: Good (50% better than manual)
- Limitation: Local optimum

### Neural Network + GA (Planned)
- Training: One-time, ~2 hours
- Inference: ~10ms per build
- GA search: 50 generations × 30 pop = 1500 evaluations × 10ms = **15 seconds**
- Quality: Better than greedy (finds global patterns)

## Next Steps

1. **Implement `features.py`**: Build the feature extraction pipeline
2. **Collect data**: 1000+ diverse builds
3. **Train baseline**: Simple MLP first
4. **Validate**: Compare to greedy on test set
5. **Optimize GA**: Tune mutation rate, population size
6. **Deploy**: Replace placeholder in GUI

## Advanced Features (Future)

- **Multi-objective optimization**: Pareto frontier for DPS vs EHP
- **Constraint handling**: Budget, attribute requirements
- **Online learning**: Update model with user feedback
- **Transfer learning**: Adapt to new leagues/patches
- **Ensemble models**: Combine multiple NNs for robustness
