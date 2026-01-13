# Documentation Index

This folder contains comprehensive documentation for the Path of Building Neural Network project.

## Quick Access

### 📘 [TRAINING_GUIDE.md](TRAINING_GUIDE.md)
Complete guide for training the model and generating PoB builds.

**Covers:**
- Quick start commands (generate builds NOW)
- Prerequisites and setup
- Training options (RL vs supervised)
- Generation pipeline walkthrough
- Class starting sequences
- Node filtering rules
- PoB XML export format
- Validation procedures
- Troubleshooting common issues
- Full training script pseudocode
- Performance metrics
- Next steps

**Use this when:** You want to generate builds, train the model, or troubleshoot export issues.

---

### 🎯 [SKILL_AWARE_OPTIMIZATION.md](SKILL_AWARE_OPTIMIZATION.md)
**NEW!** Skill-specific passive tree optimization using scaling vector analysis.

**Covers:**
- Skill scaling analyzer (damage types, speed, crit)
- Node relevance calculation
- Skill-aware tree builder (GNN + skill filtering)
- Node stats extraction from PoB
- Testing and validation
- Integration with training
- Support gem awareness

**Key features:**
- Different skills → different trees (spell vs attack vs DoT)
- Prioritizes relevant nodes (no wasted points)
- Combines learned patterns with skill requirements
- Supports 6+ skills out of the box

**Use this when:** You want builds that actually scale the selected skill properly.

---

### 🧠 [VARIABLE_ARCHITECTURE.md](VARIABLE_ARCHITECTURE.md)
Deep dive into the 7 categories of variables that drive the neural network workflow.

**Covers:**
- **Structural Variables** - Graph topology (edges, adjacency, node types)
- **Feature Variables** - Node stats (life, DPS, resists)
- **State Variables** - Build state during generation
- **Outcome Variables** - Reward signals (survival, TTK, EHP)
- **Adversarial Variables** - Encounter generation (boss fights)
- **Exploration Variables** - Diversity & novelty tracking
- **Fitting Variables** - Learned representations & embeddings

**Each section includes:**
- Current implementation status
- What needs building (with priority)
- Code examples and pseudocode
- Data flow diagrams
- Integration points

**Use this when:** You need to understand how the system works internally, what variables matter for training, or how to implement missing components.

---

## Status Overview

### ✅ What's Working
- GNN generates 97-node connected trees for Shadow class
- Real tree edges from PoB (431 edges, 412 nodes)
- PoB XML export (imports correctly)
- RL training framework (REINFORCE tested)
- Node filtering (ascendancy, mastery, duplicates)

### ⚠️ Critical Path (Blocks Real Training)
1. **BuildStatsDecoder** - Extract stats from passive tree
2. **FightSimulator** - Evaluate build performance
3. **ExplorationManager** - Prevent mode collapse

### 🔮 Future Enhancements
- Multi-class support (6 other classes)
- Mastery effect selection
- Cluster jewel optimization
- Ascendancy node allocation

---

## File Map

```
pob_neural_network/
├── docs/                          ← YOU ARE HERE
│   ├── README.md                  ← This file
│   ├── TRAINING_GUIDE.md          ← How to train & export
│   └── VARIABLE_ARCHITECTURE.md   ← System design & variables
│
├── models/
│   ├── graph_tree_builder.py     ← GNN architecture (1.66M params)
│   └── build_stats_decoder.py    ← TODO: Extract node stats
│
├── training/
│   ├── reward.py                  ← TODO: Reward function
│   ├── fight_simulator.py         ← TODO: Encounter simulation
│   └── exploration.py             ← TODO: Novelty tracking
│
├── test_graph_export.py           ← Generate & export build (WORKS)
├── test_rl_training.py            ← Test RL loop (WORKS)
├── check_tree_connectivity.py     ← Validate connections
│
└── pob_data/
    └── tree_data/
        ├── edge_index.json        ← Real tree edges
        └── node_mapping.json      ← Node ID mappings
```

---

## Quick Commands

```bash
# Generate a PoB build RIGHT NOW
cd c:\projects\pob\pob_neural_network
python test_graph_export.py

# Test RL training loop
python test_rl_training.py

# Validate tree connectivity
python check_tree_connectivity.py
```

---

## For LLMs / AI Assistants

When working on this project:

1. **Start here** - Read this README to understand the documentation structure
2. **Implementation questions** - Check TRAINING_GUIDE.md for step-by-step workflows
3. **Architecture questions** - Check VARIABLE_ARCHITECTURE.md for system design
4. **Critical path** - BuildStatsDecoder → FightSimulator → ExplorationManager
5. **Current state** - Tree generation works, rewards are placeholders

**Key insight:** The GNN can generate connected trees and export to PoB successfully. The bottleneck is evaluating build quality (need to extract stats from tree and simulate fights).

---

**Last Updated:** January 13, 2026
