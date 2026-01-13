# GPU / Neural Network Optimizer - Implementation Guide

## Current Status

The **"Generate Best"** button uses a greedy algorithm implemented in Lua that:
- Selects nodes with highest power-per-point efficiency
- Considers path costs to each node
- Works within point budget constraints
- Already gives ~50% better DPS than manual allocation

The **"GPU Optimize"** button is a placeholder for future neural network implementation.

## Why Neural Networks?

Greedy algorithms make locally optimal choices but can't:
- Learn from thousands of successful builds
- Recognize complex synergies between nodes
- Optimize for multiple objectives (offense + defense)
- Adapt to different build archetypes

A neural network trained on build data can learn these patterns and provide better recommendations.

## Implementation Roadmap

### Phase 1: Data Collection (You are here)
1. Use "Generate Best" to create baseline optimized trees
2. Collect data: (build, allocated nodes, final DPS) tuples
3. Store in training dataset

### Phase 2: Feature Engineering
Extract features for each node:
- **Node features**: Stats, type, position, connections
- **Build context**: Class, level, gear, active skills
- **Path features**: Distance from allocated nodes, cost
- **Power features**: DPS increase, efficiency

### Phase 3: Model Architecture
```python
# Example: Graph Neural Network for tree optimization
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv

class PassiveTreeGNN(nn.Module):
    def __init__(self, node_features, hidden_dim=128):
        super().__init__()
        self.gcn1 = GCNConv(node_features, hidden_dim)
        self.gcn2 = GCNConv(hidden_dim, hidden_dim)
        self.gcn3 = GCNConv(hidden_dim, 64)
        self.output = nn.Linear(64, 1)  # Score for each node
        
    def forward(self, x, edge_index):
        # x: [num_nodes, node_features]
        # edge_index: [2, num_edges] (tree connections)
        x = self.gcn1(x, edge_index).relu()
        x = self.gcn2(x, edge_index).relu()
        x = self.gcn3(x, edge_index).relu()
        scores = self.output(x).sigmoid()
        return scores
```

### Phase 4: Training
```python
# Train model to predict node value given build context
def train_model(model, train_loader, optimizer, device):
    model.train()
    for batch in train_loader:
        # batch contains: node_features, edges, allocated_nodes, target_nodes
        optimizer.zero_grad()
        
        # Forward pass
        scores = model(batch.x.to(device), batch.edge_index.to(device))
        
        # Loss: nodes in optimal path should have high scores
        target = batch.target_mask.float().to(device)
        loss = nn.BCELoss()(scores.squeeze(), target)
        
        # Backprop
        loss.backward()
        optimizer.step()
```

### Phase 5: Integration

Replace `gpu_optimizer_cli_simple.py` with inference code:

```python
#!/usr/bin/env python3
import torch
from model import PassiveTreeGNN

def optimize_build(build_code, node_count=40):
    # 1. Parse build code
    build = parse_build_code(build_code)
    
    # 2. Extract features
    node_features = extract_node_features(build)
    edge_index = build_tree_graph(build.spec.tree)
    
    # 3. Load trained model
    model = PassiveTreeGNN.load('trained_model.pt')
    model.eval()
    
    # 4. Predict node scores
    with torch.no_grad():
        scores = model(node_features, edge_index)
    
    # 5. Select top nodes within budget
    selected = budget_constrained_selection(
        scores, 
        node_count, 
        build.allocated_nodes
    )
    
    return selected
```

## File Structure for ML Implementation

```
python/
├── gpu_optimizer_cli_simple.py     # Current placeholder
├── ml/
│   ├── __init__.py
│   ├── model.py                    # Neural network architecture
│   ├── features.py                 # Feature extraction from builds
│   ├── train.py                    # Training script
│   ├── inference.py                # Inference for optimization
│   └── data/
│       ├── builds_dataset.json     # Collected build data
│       └── trained_model.pt        # Trained model weights
└── data_collection/
    ├── collect_builds.py           # Scrape builds from poe.ninja
    └── annotate_optimal.py         # Use greedy to create labels
```

## Next Steps

1. **Collect Data**: Run greedy optimizer on diverse builds, save results
2. **Research**: Study graph neural networks for tree-structured data
3. **Prototype**: Implement simple model on small dataset
4. **Train**: Full training on large dataset
5. **Deploy**: Replace placeholder with inference code
6. **Iterate**: Collect user feedback, retrain model

## Resources

- **PyTorch Geometric**: Graph neural network library
- **DGL**: Deep Graph Library (alternative)
- **Path of Building Community**: Build data sources
- **Papers**: "Graph Attention Networks", "Neural Tree Search"

## Performance Considerations

- **Inference Speed**: Should be <1 second on GPU
- **Model Size**: Keep under 100MB for easy distribution  
- **Fallback**: Always keep Lua greedy as backup
- **Batch Processing**: Can optimize multiple builds in parallel

---

**Current workflow**: Enable "Show Node Power" → Click "Generate Best" → Click "Apply Nodes"

**Future workflow**: Click "GPU Optimize" → Neural network recommends optimal build → Apply
