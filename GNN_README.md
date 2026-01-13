# Graph Neural Network for Path of Building

## Architecture Overview

This implementation uses **Graph Neural Networks (GNN)** to learn optimal passive tree allocation while respecting connectivity constraints. Unlike the previous approach that treated nodes as independent binary choices, this architecture understands the tree as a graph structure.

### Key Components

1. **TreeGraphEncoder** (`models/graph_tree_builder.py`)
   - Uses Graph Convolutional Networks (GCN) to learn node embeddings
   - Understands node relationships through edge connectivity
   - Each node learns from its neighbors in the passive tree

2. **PathGenerator** (`models/graph_tree_builder.py`)
   - Sequential decision making - outputs one node at a time
   - LSTM-based state tracking of currently allocated nodes
   - Ensures connectivity by only considering adjacent nodes

3. **PolicyGradientTrainer** (`training/graph_tree_trainer.py`)
   - Uses REINFORCE algorithm for reinforcement learning
   - Rewards: connectivity, efficiency, performance prediction
   - Adversarial-style training - model explores and learns from rewards

## Why This Works

### Problem with Previous Approach
- Treated passive tree as 412 independent binary choices
- No understanding of connectivity requirements
- Had to use similarity matching as workaround

### Graph-Aware Solution
- **Understands structure**: GCN learns which nodes connect to which
- **Sequential allocation**: Builds tree step-by-step, ensuring valid paths
- **Connectivity enforcement**: Only allows allocation of adjacent nodes
- **Adversarial training**: Policy gradient learns from trial and error

## Installation

```bash
# Install PyTorch Geometric
python scripts/setup_graph_dependencies.py

# Or manually:
pip install torch-geometric torch-scatter torch-sparse
```

## Training

```bash
# Train the graph-aware model
python training/graph_tree_trainer.py
```

The trainer will:
1. Load the passive tree graph structure (412 nodes, ~2000 edges)
2. Create the GNN model with graph convolution layers
3. Train using policy gradient (REINFORCE)
4. Save best model to `checkpoints/best_graph_model.pt`

### Training Process

**Policy Gradient Loop:**
1. Build a tree by sequentially selecting nodes
2. Start from class starting node
3. At each step, score all adjacent nodes
4. Sample action from probability distribution
5. Continue until 100 points allocated
6. Calculate reward based on:
   - Connectivity (is path valid?)
   - Performance (predicted DPS, EHP)
   - Efficiency (point usage)
7. Backpropagate reward through action sequence
8. Update model to increase probability of good actions

**Exploration vs Exploitation:**
- Entropy bonus encourages trying different paths
- Gradually converges to optimal strategies
- Learns which nodes lead to better builds

## Usage

```python
from models.graph_tree_builder import GraphTreeBuilder, load_edge_index_from_builds

# Load model
edge_index = load_edge_index_from_builds(
    "./pob_data/tree_data",
    "./pob_data/tree_data/node_mapping.json"
)

model = GraphTreeBuilder(num_nodes=412, edge_index=edge_index)
model.load_state_dict(torch.load("checkpoints/best_graph_model.pt")['model_state_dict'])
model.eval()

# Generate tree
with torch.no_grad():
    output = model(gear_tensor, gems_tensor, skill_tensor)
    allocated_tree = output['tree']  # Connected path!
    predicted_perf = output['performance']  # DPS, EHP
```

## Advantages Over Previous Approach

| Feature | Binary Choice (Old) | Graph-Aware (New) |
|---------|-------------------|-------------------|
| Connectivity | ❌ No understanding | ✅ Enforced by design |
| Tree Structure | ❌ Treats nodes independently | ✅ Understands graph relationships |
| Training | Supervised (MSE) | Reinforcement Learning (rewards) |
| Output | Scattered nodes | Connected valid path |
| Optimization | Not skill-specific | Learns optimal paths per skill |
| Workarounds | Needed similarity matching | None needed |

## Model Architecture Details

### Graph Convolution Layers
```
Input: Node IDs [num_nodes]
  ↓
Embedding: [num_nodes, 64]
  ↓
GCN Layer 1: [num_nodes, 128]
  ↓ (aggregates neighbor information)
GCN Layer 2: [num_nodes, 128]
  ↓ (multi-hop relationships)
GCN Layer 3: [num_nodes, 128]
  ↓
Output: Node embeddings [num_nodes, 128]
```

Each GCN layer:
- Aggregates information from connected neighbors
- Learns which node combinations are effective
- Multi-layer = understands longer paths

### Path Generation
```
State: [allocated_nodes] + [context: gear, gems, skill]
  ↓
LSTM State Aggregator
  ↓
For each candidate node:
  - Concatenate: [node_embedding, context, tree_state]
  - Score: Neural network → scalar
  ↓
Softmax → Probability distribution
  ↓
Sample action (with exploration)
  ↓
Add to allocated nodes
```

### Reward Function

```python
reward = (
    +10.0  if connected path
    -50.0  if disconnected (heavy penalty!)
    +5.0 * performance_accuracy
    +0.5 * efficiency (fewer points better)
)
```

## Performance Expectations

After training:
- **Connectivity**: 100% valid paths (enforced by architecture)
- **Skill-specific**: Learns different trees for different skills
- **Efficient**: Optimizes for point usage
- **Flexible**: Can target different performance goals

## Next Steps

1. **Train the model**: Run `python training/graph_tree_trainer.py`
2. **Integrate with export**: Update `pob_bridge.py` to use GraphTreeBuilder
3. **Fine-tune rewards**: Adjust reward weights for desired behavior
4. **Add multi-objective**: Consider defensive vs offensive builds
5. **Keystone detection**: Higher rewards for valuable keystones

## Comparison: Old vs New Export

**Old (Similarity Matching):**
```
NN predicts: 29 scattered nodes (not connected)
↓
Find similar build: 4.8% match
↓
Use similar build's tree: 113 connected nodes
↓
Not optimal for different skill!
```

**New (Graph-Aware):**
```
NN builds: 100 connected nodes (path-aware)
↓
All nodes are adjacent to previous
↓
Guaranteed connectivity
↓
Optimized for specific skill/gear
```

## Technical Notes

### Edge Data
- Extracted from 42 working 3.27 builds
- Heuristic: consecutive nodes in build likely connected
- Stored in `pob_data/tree_data/tree_edges.json`
- ~2000 edges between 412 nodes

### Starting Nodes (Class Positions)
```python
CLASS_STARTS = {
    'Scion': 42178,
    'Marauder': 54248,
    'Ranger': 36634,
    'Witch': 41263,
    'Duelist': 6230,
    'Templar': 26725,
    'Shadow': 33631
}
```

### Why Policy Gradient?
- Tree building is a sequential decision problem
- Each allocation affects future options (connectivity)
- Reward signal is sparse (only at end of tree)
- Policy gradient naturally handles this
- Exploration finds non-obvious strong paths

## Future Improvements

1. **Multi-step lookahead**: Consider future allocations
2. **Hierarchical planning**: Plan path to keystones, then fill
3. **Constraint optimization**: Hard limits on point budget
4. **Transfer learning**: Pre-train on all 207 builds, fine-tune on 3.27
5. **Graph attention**: Learn which edges are more important
