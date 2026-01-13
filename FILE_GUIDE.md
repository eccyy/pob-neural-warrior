# Neural Network Implementation - File Organization

This folder contains all neural network implementation files for the Path of Building optimizer.

## Directory Structure

```
neural_network/
├── README.md                    # Comprehensive overview of NN system
├── architecture.md              # Detailed neural network architecture design
├── reward_functions.md          # Complete reward function guide (3902 lines)
├── PROJECT_OVERVIEW.md          # Original ML implementation roadmap
├── __init__.py                  # Package initialization
│
├── models/                      # Neural network model implementations
│   ├── __init__.py
│   ├── multi_component.py       # Main MultiComponentBuilder model
│   ├── tree_optimizer.py        # PassiveTreeDecoder with clustering
│   ├── gear_optimizer.py        # SimpleGearDecoder (5 stats/slot)
│   └── gem_optimizer.py         # GemSelectionDecoder (multipliers)
│
├── training/                    # Training pipeline
│   ├── __init__.py
│   ├── data_collection.py       # Scrape poe.ninja builds
│   ├── train.py                 # Multi-objective training loop
│   └── validate.py              # Test on holdout set
│
├── utils/                       # Utility modules
│   ├── __init__.py
│   ├── poedb_scraper.py         # Scrape enemy data from poedb.tw
│   ├── build_parser.py          # Parse PoB build codes
│   └── feature_extraction.py    # Extract features (wraps ../features.py)
│
└── integration/                 # Integration with PoB Lua
    ├── __init__.py
    ├── export_suggestions.py    # Export to Lua format
    ├── import_build.py          # Import from PoB
    └── lua_bridge.py            # Python-Lua communication
```

## Related Files (Outside This Folder)

- **python/ml/features.py**: Existing feature extraction (242 lines)
  - Referenced by utils/feature_extraction.py
  
- **src/Classes/TreeTab.lua**: Working greedy optimizer (lines 815-1252)
  - Target for integration/export_suggestions.py
  
- **src/Classes/CalcsTab.lua**: Optimizer state storage
  - Used by integration/lua_bridge.py

## Quick Navigation

| Need to... | Start with... |
|-----------|--------------|
| Understand the system | [README.md](README.md) |
| See detailed architecture | [architecture.md](architecture.md) |
| Implement reward functions | [reward_functions.md](reward_functions.md) |
| Read original design | [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) |
| Build models | [models/](models/) |
| Train the network | [training/](training/) |
| Scrape game data | [utils/poedb_scraper.py](utils/poedb_scraper.py) |
| Integrate with Lua | [integration/](integration/) |

## Implementation Status

### ✅ Completed
- Comprehensive design documentation (3902 lines)
- Folder structure and package initialization
- Architecture specification
- Reward function design
- Game mechanics insights
- Simplification strategies

### 🚧 In Progress
- Model implementations (placeholders created)
- Training pipeline (structure defined)
- Utility modules (interfaces planned)
- Integration layer (approach documented)

### 📋 Planned
- Data collection from poe.ninja
- PoeDB enemy database scraper
- Multi-objective training loop
- Validation on holdout set
- Lua bridge implementation
- Production deployment

## Key Insights

1. **Complexity Reduction**: 10^300 → 10^6 through simplification
2. **Tree Clustering**: 8 clusters not 1500 random nodes
3. **Simplified Gear**: 5 stats per slot with average values
4. **Gem Multipliers**: 1.4x, 1.35x, 1.35x, 1.3x, 1.25x pattern
5. **Greedy Auras**: Enable all, remove lowest (no ML needed)
6. **No Local Maxima**: Discrete cluster decisions
7. **Skill Balance**: Within 2x, not 10x differences
8. **Time-to-Kill**: Primary offensive metric
9. **Offense = Defense**: Faster kills reduce incoming damage
10. **Environmental Damage**: Requires recovery, not just more damage

## Getting Started

1. Read [README.md](README.md) for system overview
2. Review [architecture.md](architecture.md) for model design
3. Study [reward_functions.md](reward_functions.md) for implementation details
4. Implement models in [models/](models/) directory
5. Build training pipeline in [training/](training/)
6. Create utility modules in [utils/](utils/)
7. Integrate with Lua in [integration/](integration/)

## Design Philosophy

- **Simplicity over complexity**: Use simple solutions where possible
- **Practical over theoretical**: Focus on what works in practice
- **Iterative improvement**: Start simple, add complexity only when needed
- **Data-driven decisions**: Let training data guide architecture choices
- **User-centric**: Optimize for the skill the user wants to play
