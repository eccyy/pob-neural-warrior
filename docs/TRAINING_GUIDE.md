# Path of Building Neural Network - Training & Export Guide

## Quick Start

### Generate a PoB Build (Works Now!)
```bash
python test_graph_export.py
```
- Generates a 97-node connected passive tree for Shadow
- Outputs: `test_graph_export.xml`
- Import into Path of Building to view

---

## Complete Workflow

### 1. Prerequisites

**Installed:**
- Python 3.9+
- PyTorch with CUDA (for GPU training)
- torch-geometric
- lupa (for Lua parsing)

**Data Files:**
- `../PathOfBuilding/src/TreeData/3_27/tree.lua` - PoB tree data
- `pob_data/tree_data/edge_index.json` - Real tree edges (431 edges)
- `pob_data/tree_data/node_mapping.json` - Node ID to index mapping (412 nodes)

### 2. Training Setup

#### Current Model Architecture

**File:** `models/graph_tree_builder.py`

**Components:**
- `TreeGraphEncoder` - GCN layers for node embeddings (3 layers, 128 dim)
- `PathGenerator` - Sequential node selection policy
- `GraphTreeBuilder` - Complete model (1.66M parameters)

**What it does:**
- Takes: Graph structure + gear/gems/skill context
- Outputs: Connected passive tree (greedy node-by-node generation)
- Respects tree connectivity (only picks adjacent nodes)

#### Training Options

**Option A: RL Training (Recommended for Real Builds)**

```bash
python test_rl_training.py
```

This runs adversarial RL training with:
- REINFORCE policy gradient algorithm
- Temperature-based exploration (1.0 = explore, 0.5 = exploit)
- Reward function (currently heuristic, needs real build stats)

**Training Loop:**
1. Sample context (class, gear, gems, skill)
2. Generate tree greedily with log probabilities
3. Compute reward (survival + DPS + uniqueness)
4. Update policy with gradient: -Σ log π(action) × reward
5. Repeat

**Key Parameters:**
- `num_nodes=50-100` - Tree size
- `temperature=1.0` - Exploration vs exploitation
- `learning_rate=1e-4` - Adam optimizer

**Option B: Supervised Pretraining (Not implemented yet)**

Train on existing PoB builds:
- Extract trees from `pob_data/processed/Keepers_train.json`
- Supervised learning: predict next node given partial tree
- Use as warm-start before RL fine-tuning

### 3. Generation Pipeline

#### Step-by-Step Tree Generation

**File:** `test_graph_export.py`

**Process:**
1. Load tree structure (edges, node mapping)
2. Filter out special nodes (ascendancy, mastery)
3. Select starting node for class
4. Generate tree greedily (100 nodes)
5. Prepend class starting sequence
6. Remove duplicates and special nodes
7. Export to PoB XML

**Class Starting Sequences:**

Each class requires specific starting nodes:

```python
CLASS_STARTS = {
    'Shadow': [38129, 44683, 45272],  # Must be first 3 nodes
    'Scion': [58833],                 # + 4 more (need to extract)
    'Marauder': [47175],              # + starting nodes
    'Ranger': [50459],                # + starting nodes
    'Witch': [54447],                 # + starting nodes
    'Duelist': [50986],               # + starting nodes
    'Templar': [61525],               # + starting nodes
}
```

**Bridge Nodes:**

After class start sequence, need a bridge to main tree:
- Shadow: Use node 11334 (connects from 38129)
- Other classes: Need to identify

#### Node Filtering

**Always filter out:**
1. **Ascendancy nodes** (479 nodes) - Separate system, max 8 allocated
2. **Mastery nodes** (349 nodes) - Require manual effect selection
3. **Duplicate nodes** - Can appear multiple times in generation

**Keep:**
- Regular passives (small nodes)
- Notable passives (larger stats)
- Keystone passives (build-defining mechanics)
- Jewel sockets (can slot jewels)

### 4. Export to Path of Building

#### XML Structure

```xml
<?xml version='1.0' encoding='utf-8'?>
<PathOfBuilding>
  <Build 
    level="90" 
    targetVersion="3_0" 
    mainSocketGroup="1" 
    className="Shadow" 
    ascendClassName="None" 
    bandit="None" />
  <Tree activeSpec="1">
    <Spec 
      treeVersion="3_27" 
      classId="6" 
      ascendClassId="0" 
      nodes="38129,44683,45272,11334,..." />
  </Tree>
</PathOfBuilding>
```

**Critical Requirements:**
- `className` must match `classId` (Shadow = 6)
- `nodes` must start with class starting sequence
- All nodes must form connected path
- No ascendancy nodes in `nodes` list
- Mastery nodes need `masteryEffects` attribute (skip for now)

#### Class IDs

```python
CLASS_IDS = {
    'Scion': 0,
    'Marauder': 1,
    'Ranger': 2,
    'Witch': 3,
    'Duelist': 4,
    'Templar': 5,
    'Shadow': 6
}
```

### 5. Validation

#### Check Tree Connectivity

```bash
python check_tree_connectivity.py
```

**Output:**
- Total nodes in XML
- Number of disconnected nodes (should be 0)
- First 10 connections verified

**Common Issues:**
- ❌ Node X disconnected: Missing edge or wrong order
- ❌ Class start not first: Must prepend class sequence
- ❌ Duplicate nodes: Filter before export

#### Verify in PoB

1. Open Path of Building
2. Click "Import/Export Build"
3. Load `test_graph_export.xml`
4. Check "Tree" tab
5. Verify nodes are allocated and connected

**Expected:**
- ~90-100 allocated nodes (exact count varies)
- All nodes highlighted in green
- Connected path from class start
- No red/disconnected nodes

### 6. Full Training Script (To Implement)

**Pseudocode:**

```python
# train_adversarial.py

from models.graph_tree_builder import GraphTreeBuilder, load_edge_index_from_builds
from training.build_stats_decoder import BuildStatsDecoder
from training.fight_simulator import FightSimulator
from training.reward import compute_reward

# Setup
model = GraphTreeBuilder(num_nodes=412, edge_index=edge_index)
decoder = BuildStatsDecoder()  # TODO: Implement
simulator = FightSimulator()   # TODO: Implement

optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

# Training loop
for iteration in range(10000):
    # Sample context
    class_name = random.choice(['Shadow', 'Witch', 'Ranger', ...])
    gear = sample_gear()
    gems = sample_gems()
    skill = sample_skill()
    
    # Generate tree with log probs
    tree, log_probs = model.build_tree_with_logprobs(
        start_node=get_class_start(class_name),
        gear=gear, gems=gems, skill=skill,
        temperature=1.0
    )
    
    # Decode to build stats
    build_stats = decoder.decode(tree, gear, gems, skill)
    # -> {life, es, armor, dps, resists, ...}
    
    # Simulate encounter
    encounter = sample_encounter()  # T16 boss, Maven, etc.
    result = simulator.run(build_stats, encounter)
    # -> {survived, time_to_kill, damage_taken}
    
    # Compute reward
    reward = compute_reward(build_stats, result)
    
    # REINFORCE update
    loss = -(log_probs * reward).sum()
    loss.backward()
    optimizer.step()
    
    # Log & save
    if iteration % 100 == 0:
        print(f"Iter {iteration}: Reward={reward:.3f}, Loss={loss:.3f}")
        torch.save(model.state_dict(), f'checkpoints/model_{iteration}.pt')
```

### 7. Export Trained Model

**After training:**

```python
# generate_build.py

import torch
from models.graph_tree_builder import GraphTreeBuilder
from integration.pob_bridge import export_to_pob_xml

# Load trained model
model = GraphTreeBuilder(num_nodes=412, edge_index=edge_index)
model.load_state_dict(torch.load('checkpoints/model_best.pt'))
model.eval()

# Generate tree
with torch.no_grad():
    tree = model.build_tree_greedy(
        gear=gear_vector,
        gems=gems_vector,
        skill=skill_vector,
        num_points=100,
        starting_node=shadow_start
    )

# Filter and export
tree_filtered = filter_special_nodes(tree)
export_to_pob_xml(
    tree_nodes=tree_filtered,
    class_name='Shadow',
    output_file='generated_build.xml'
)
```

---

## Current Limitations & TODOs

### ✓ Working Now
- Graph structure with real PoB edges
- Greedy tree generation (connected paths)
- PoB XML export (valid format)
- RL training loop (gradients flow)
- Node filtering (ascendancy, mastery, duplicates)
- Shadow class support

### ⚠️ Needs Implementation

**Priority 1: Build Stats Decoder**
- Extract passive stats from PoB tree data
- Aggregate: life%, ES%, armor%, resists, etc.
- Compute derived stats: total life, EHP, DPS
- Integration with PoB's Lua calculation engine

**Priority 2: Reward Function**
- Survival probability (can tank one-shots?)
- Time-to-kill (DPS check)
- Defensive layers (life + ES + armor + evasion + block)
- Resist capping (must hit 75% all res)
- Efficiency (don't over-invest in one area)

**Priority 3: Multi-Class Support**
- Extract starting sequences for all 7 classes
- Identify bridge nodes for each class
- Handle Scion's 5 starting nodes
- Class-specific tree generation

**Priority 4: Advanced Features**
- Mastery effect selection (requires heuristics or ML)
- Jewel socket optimization (which jewels to use?)
- Cluster jewel support (external tree connections)
- Ascendancy node allocation (separate from main tree)

---

## Troubleshooting

### "Only X nodes allocated in PoB" (X < expected)

**Causes:**
1. Ascendancy nodes in tree → Filter with `load_ascendancy_nodes()`
2. Mastery nodes without effects → Filter out masteries
3. Disconnected path → Run `check_tree_connectivity.py`
4. Wrong class start sequence → Verify order matches edges

**Fix:**
```python
# In test_graph_export.py, line 120-140
ascendancy_nodes, mastery_nodes = load_ascendancy_nodes()
filtered_tree = [n for n in tree if n not in ascendancy_nodes and n not in mastery_nodes]
```

### "Disconnected nodes" error

**Causes:**
1. Class start sequence in wrong order
2. Missing bridge node between class start and tree
3. Generated nodes don't connect to each other

**Fix:**
- Verify class start: `38129 → 44683 → 45272` for Shadow
- Check bridge node connects to class start
- Ensure GNN only picks adjacent neighbors

### "RuntimeError: dimension mismatch"

**Causes:**
1. Wrong input dimensions for gear/gems/skill
2. Edge index shape incorrect
3. Batch size issues

**Fix:**
```python
# Match model's expected dimensions
gear = torch.randn(500)   # gear_dim=500
gems = torch.randn(100)   # gem_dim=100
skill = torch.randn(8)    # skill_dim=8
```

---

## Example: Generate 5 Builds

```python
# batch_generate.py

from models.graph_tree_builder import GraphTreeBuilder
import torch

model = GraphTreeBuilder(num_nodes=412, edge_index=edge_index)
# model.load_state_dict(torch.load('trained_model.pt'))  # If trained
model.eval()

for i in range(5):
    # Random context
    gear = torch.randn(500)
    gems = torch.randn(100)
    skill = torch.randn(8)
    
    # Generate
    tree = model.build_tree_greedy(gear, gems, skill, num_points=100, starting_node=73)
    
    # Export
    export_to_pob_xml(
        tree_nodes=filter_special_nodes(tree),
        class_name='Shadow',
        output_file=f'build_{i+1}.xml'
    )
    
    print(f"Generated build_{i+1}.xml with {len(tree)} nodes")
```

---

## Performance Metrics

**Current Model:**
- Parameters: 1,663,747
- Generation time: ~0.1s per tree (CPU)
- Training iteration: ~0.5s (with gradient computation)
- Memory: ~500MB (model + graph data)

**Target Performance:**
- Training: 10,000 iterations × 0.5s = ~1.5 hours
- Inference: 100 builds/second
- Quality: 90%+ viable builds (survive T16)

---

## Next Steps

1. **Implement BuildStatsDecoder** (extract stats from tree)
2. **Create simple FightSimulator** (rule-based survival/DPS check)
3. **Train for 1000 iterations** (test convergence)
4. **Extract class starts for all classes** (multi-class support)
5. **Scale to full training run** (10k iterations)
6. **Add adversarial encounter generator** (hard scenario creation)

---

## File Reference

**Core Model:**
- `models/graph_tree_builder.py` - GNN architecture
- `models/build_stats_decoder.py` - TODO: Extract build stats
- `training/reward.py` - TODO: Reward function

**Testing:**
- `test_graph_export.py` - Generate & export single build
- `test_rl_training.py` - Test RL training loop
- `check_tree_connectivity.py` - Validate tree connections
- `check_ascendancy_nodes.py` - Find special nodes

**Data:**
- `pob_data/tree_data/edge_index.json` - Real tree edges
- `pob_data/tree_data/node_mapping.json` - Node ID mappings
- `../PathOfBuilding/src/TreeData/3_27/tree.lua` - PoB tree data

**Integration:**
- `integration/pob_bridge.py` - PoB XML export
- `extract_real_tree_edges.py` - Extract edges from PoB
- `extract_class_start_nodes.py` - Find class starting nodes

---

## Quick Commands

```bash
# Generate a build (works now)
python test_graph_export.py

# Test RL training
python test_rl_training.py

# Validate connectivity
python check_tree_connectivity.py

# Check for special nodes
python check_ascendancy_nodes.py

# Extract class starts
python extract_class_start_nodes.py
```

---

**Status:** Tree generation and export working. RL framework ready. Need build stats decoder for real training.
