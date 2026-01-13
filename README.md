# Neural Network Build Optimizer - Complete Implementation Guide

## 🎯 NEW: Skill-Aware Passive Tree Optimization

The neural network now properly selects passive tree nodes based on **skill scaling vectors** from Path of Building calculations!

**What this means:**
- ✅ Spell skills get spell damage, cast speed, spell crit
- ✅ Attack skills get attack damage, attack speed, weapon nodes
- ✅ DoT skills get DoT multi, duration (no crit/speed waste)
- ✅ Different skills → different trees (no more generic patterns)

**See:** [docs/SKILL_AWARE_OPTIMIZATION.md](docs/SKILL_AWARE_OPTIMIZATION.md) for complete documentation.

**Quick test:**
```bash
python test_skill_aware_tree.py
```

---

## Overview

This folder contains the complete implementation of a neural network-based build optimizer for Path of Building. The system uses machine learning to optimize passive tree allocation, gear selection, gem setup, and aura configuration.

## File Structure

```
python/ml/neural_network/
├── README.md                    # This file - overview and getting started
├── reward_functions.md          # Complete reward function design (3900+ lines)
├── architecture.md              # Neural network architecture details
├── training_pipeline.md         # Training procedures and data collection
├── models/                      # Neural network model implementations
│   ├── __init__.py
│   ├── multi_component.py       # Multi-component builder (tree+gear+gems)
│   ├── tree_optimizer.py        # Passive tree encoder/decoder
│   ├── gear_optimizer.py        # Simplified gear generation (5 stats/slot)
│   └── gem_optimizer.py         # Gem selection (damage multipliers)
├── training/                    # Training scripts
│   ├── __init__.py
│   ├── data_collection.py       # Scrape poe.ninja builds
│   ├── train.py                 # Main training loop
│   └── validate.py              # Validation and testing
├── utils/                       # Utility functions
│   ├── __init__.py
│   ├── poedb_scraper.py         # Scrape enemy data from poedb.tw
│   ├── build_parser.py          # Parse PoB build codes
│   └── feature_extraction.py   # Extract features from builds
└── integration/                 # Integration with PoB Lua
    ├── __init__.py
    ├── export_suggestions.py   # Export to Lua format
    └── import_build.py          # Import from PoB
```

## Key Features

### 1. Multi-Objective Optimization
- **Offensive metrics**: DPS, time-to-kill, clear speed
- **Defensive metrics**: Max hit taken, EHP, recovery rate
- **Environmental damage**: Ground degens, storms, unavoidable DoT
- **Scenario-based**: Mapper, Bosser, Balanced, Hardcore, Speed Farmer

### 2. Simplified Component Design
Each component is simplified to reduce complexity:

**Passive Tree** (~1500 nodes → 8 clusters)
- Cluster-level decisions (life, damage, crit, ES, evasion, block)
- Keystone selection (20 critical nodes)
- Notable prioritization within clusters
- Automatic pathing for travel nodes

**Gear** (10^20 combinations → 50 values)
- Just 5 key stats per slot (life, res, damage, speed, utility)
- Output average stat values (e.g., ring: 65 life, 95 res, 22 damage)
- Much simpler than complex item generation

**Gems** (400^24 combinations → 15 categories)
- Support gems grouped by function (damage, speed, AoE, defense)
- Follow standard multipliers: 1.4x, 1.35x, 1.35x, 1.3x, 1.25x
- Output multipliers directly instead of gem names

**Auras** (12 auras → greedy selection)
- Simple algorithm: enable all, remove lowest contributors
- No training needed - deterministic selection

### 3. Skill Balance Understanding
- Skills are balanced within 2x, not 10x differences
- Network learns scaling vector matching (skill stats → appropriate clusters)
- High crit skill → crit clusters, low crit → damage clusters
- Optimize FOR user's chosen skill, don't tell them to reroll

### 4. Passive Tree Structure Exploitation
**Clustering** reduces search space:
- 8 major clusters instead of 1500 random nodes
- Choose 2-3 clusters = 56 combinations (not 10^450)
- Within clusters, greedy selection works well

**Node hierarchy** simplifies decisions:
- Keystones: 20 binary decisions (build-defining)
- Notables: 280 power nodes (important)
- Small nodes: 1200 incremental/travel (auto-path)

**Dead nodes** are heavily penalized:
- Attack nodes for spell build = 0 value (10x penalty)
- Better to detour around dead regions
- Network learns archetype-specific relevance

**No local maxima** in PoE tree:
- Clusters are geographically separated
- Only ~8 relevant clusters per build type
- Simple greedy works - no complex exploration needed

### 5. Skill Scaling Vectors
Network understands skill-specific scaling:

**Crit scaling** (base crit matters):
- Ice Spear (7% base): crit nodes have 1.0 value
- Earthquake (5% base): crit nodes have 0.6 value
- Dynamic based on current investment (diminishing returns)

**Attack speed thresholds** (not linear):
- Overkilling (15k damage vs 10k HP): speed has reduced value
- Multi-hit required: speed has full linear value
- Near one-shot threshold: damage > speed

**Base damage** understanding:
- Attack skills scale from WEAPON damage (not skill base damage)
- "Low base damage" on attacks is normal, not a trap

## Implementation Status

### ✅ Completed
1. Comprehensive reward function design (reward_functions.md)
2. Offensive metrics (DPS, time-to-kill, clear speed, hit patterns)
3. Defensive metrics (max hit, EHP, recovery, environmental damage)
4. Simplified adversarial training (use poedb.tw enemy database)
5. Multi-component architecture design
6. Simplified gear generation (5 stats per slot)
7. Gem optimization (damage multipliers)
8. Aura optimization (greedy selection)
9. Passive tree clustering analysis
10. Skill scaling vector matching
11. Working greedy optimizer in Lua GUI (50% DPS improvement)

### 🚧 In Progress
1. Neural network model implementation
2. Training data collection from poe.ninja
3. PoeDB scraper for enemy data
4. Feature extraction pipeline

### 📋 Planned
1. Training loop with multi-objective loss
2. Integration with PoB Lua code
3. User interface for scenario selection
4. Content viability checker (which bosses can you do?)
5. Weakness analyzer (dies to X because Y)

## Quick Start

### Prerequisites
```bash
# Python 3.8+
pip install torch numpy pandas tqdm
pip install requests beautifulsoup4  # For poedb scraper
pip install PathOfBuildingAPI  # Optional, for build parsing
```

### Training Pipeline
```python
# 1. Collect training data
from training.data_collection import collect_poeninja_builds
builds = collect_poeninja_builds(limit=10000)

# 2. Scrape enemy database
from utils.poedb_scraper import PoeDBScraper
scraper = PoeDBScraper()
enemy_db = scraper.build_enemy_database()

# 3. Train model
from training.train import train_multi_objective
model = train_multi_objective(builds, enemy_db, epochs=1000)

# 4. Validate
from training.validate import test_on_holdout
results = test_on_holdout(model, test_builds)
```

### Integration with PoB
```python
# Export suggestions to Lua
from integration.export_suggestions import export_to_lua
suggestions = model.optimize_build(current_build, scenario='balanced')
export_to_lua(suggestions, output_path='optimizer_suggestions.lua')
```

## Design Philosophy

### Simplicity Over Complexity
- **Gear**: 5 stats per slot, not complex item generation
- **Gems**: Multiplier categories, not individual gem encoding
- **Auras**: Greedy selection, no training needed
- **Tree**: Cluster-level decisions, auto-path travel nodes

### Practical Over Theoretical
- Test against real enemies (poedb.tw), not synthetic
- Learn from existing builds (poe.ninja), not random exploration
- Supervised learning, not complex reinforcement learning
- User chooses skill, network optimizes for it

### User-Centric Design
- Let user pick scenario (mapper/bosser/balanced)
- Show which content they can/cannot do
- Explain weaknesses (dies to X because Y)
- Don't force meta builds, optimize their chosen skill

## Key Insights

1. **Offense IS Defense**: Fast kills = less incoming damage
2. **Time to Kill is Key**: Directly determines total damage taken
3. **Environmental Damage Matters**: Recovery is critical for degens
4. **Skills Are Balanced**: 10x difference is bad vs good builds, not skill A vs B
5. **Tree Has Structure**: 8 clusters, not 1500 random nodes
6. **No Local Maxima**: Discrete decisions, not smooth landscape
7. **Scaling Vectors Matter**: Match skill's strengths to tree clusters
8. **Dead Nodes Exist**: Some nodes are worse than travel nodes
9. **Simplify Components**: 50 values beats 10^20 combinations

## References

### Related Files (Outside This Folder)
- `python/ml/features.py` - Original feature extraction
- `python/ml/README.md` - Original ML roadmap
- `src/Classes/TreeTab.lua` (lines 185-210, 815-1252) - Working greedy optimizer
- `src/Classes/CalcsTab.lua` - Optimizer state storage

### External Resources
- poe.ninja - Top ladder builds
- poedb.tw - Enemy statistics and mechanics
- PoE Wiki - Game mechanics documentation

## Contributing

When adding new features:
1. Update relevant .md files with design rationale
2. Add examples showing why the approach works
3. Include concrete numbers (DPS, EHP, etc.) in examples
4. Test against real PoB builds
5. Document any simplifications made

## Contact

This is part of the Path of Building Optimizer project. See main README for more information.
