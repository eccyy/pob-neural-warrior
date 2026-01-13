# Neural Network Architecture Design

## Overview

The Path of Building optimizer uses a multi-component neural network that handles passive tree, gear, gems, and auras simultaneously. The key innovation is a shared interaction layer that learns how these components synergize.

## Architecture Diagram

```
Current Build State
        ↓
┌───────────────────────────────────────────────────┐
│  Component Encoders (Learn Component Structure)   │
├───────────────────────────────────────────────────┤
│  Tree Encoder (1500 → 256)                        │
│  Gear Encoder (500 → 256)                         │
│  Gem Encoder (100 → 128)                          │
└───────────────────────────────────────────────────┘
        ↓ concat
┌───────────────────────────────────────────────────┐
│  Shared Interaction Layer (640 → 512 → 256)       │
│  Learns cross-component synergies:                │
│  - Tree +% phys → gear flat phys valuable         │
│  - Crit on tree → crit multi on gear             │
│  - Fire conversion → fire damage nodes            │
└───────────────────────────────────────────────────┘
        ↓ split
┌───────────────────────────────────────────────────┐
│  Component Decoders (Generate Improvements)       │
├───────────────────────────────────────────────────┤
│  Tree Decoder → Node allocation probabilities     │
│  Gear Decoder → 5 stats per slot (simplified)     │
│  Gem Decoder → Support categories & multipliers   │
└───────────────────────────────────────────────────┘
        ↓
Optimized Build Suggestions
```

## Component Details

### 1. Passive Tree Encoder/Decoder

**Input**: Binary vector (1500 nodes, 1 = allocated, 0 = not)

**Encoder**:
- Linear(1500 → 512) + ReLU + Dropout(0.2)
- Linear(512 → 256) + ReLU

**Decoder**:
- Linear(256 → 512) + ReLU
- Linear(512 → 1500) + Sigmoid
- Output: Probability for each node (0-1)

**Post-processing**:
- Mask already-allocated nodes
- Apply cluster constraints (prefer nearby nodes)
- Use A* pathfinding for travel nodes
- Enforce point budget

### 2. Gear Encoder/Decoder (Simplified)

**Input**: Aggregated stats vector (500 dimensions)
- Life: total, %increased, flat
- Resistances: fire, cold, lightning, chaos
- Damage: phys, ele, chaos, added
- Defenses: armour, evasion, ES
- Utility: move speed, attributes, accuracy

**Encoder**:
- Linear(500 → 256) + ReLU + Dropout(0.2)

**Decoder** (Per Slot):
- Linear(256 → 64) + ReLU
- Linear(64 → 5) + Sigmoid
- Output: 5 normalized values per slot
- Scale to typical ranges (e.g., ring: 40-70 life, 70-105 res)

**10 Gear Slots**:
- Weapon: [added_damage, crit_chance, attack_speed, ele_damage, accuracy]
- Body Armour: [life, armour/eva/ES, secondary_defense, tertiary, res]
- Helmet: [life, res, accuracy, attributes, armour]
- Gloves: [life, res, attack_speed, accuracy, damage]
- Boots: [life, res, move_speed, armour, evasion]
- Amulet: [life, damage%, crit_multi, attributes, res]
- Ring 1: [life, res, damage, accuracy, attributes]
- Ring 2: [life, res, damage, accuracy, attributes]
- Belt: [life, res, armour, flask_charges, attributes]
- Jewels: [life%, damage%, crit_multi, attack_speed, res]

### 3. Gem Encoder/Decoder (Multiplier-Based)

**Input**: Current gem setup (100 dimensions)
- Main skill gem (24 total sockets, 1-hot encoding)
- Support gem categories (15 categories)
- Gem levels (normalized 1-21)

**Encoder**:
- Linear(100 → 128) + ReLU + Dropout(0.2)

**Decoder** (Per 6-Link):
- Linear(256 → 128) + ReLU
- Linear(128 → 5 × 15) # 5 support sockets × 15 categories
- Reshape to (5, 15) + Softmax per socket

**Support Categories** (15 total):
1. Added Damage (1.40x dmg)
2. More Damage (1.35x dmg)
3. Crit Support (1.35x dmg)
4. Damage Conversion (1.30x dmg)
5. Utility Damage (1.25x dmg)
6. Faster Attacks (1.30x speed, 0.95x dmg)
7. Faster Casting (1.30x speed, 0.95x dmg)
8. Multistrike (1.60x speed, 0.80x dmg, repeat 3)
9. Spell Echo (1.50x speed, 0.85x dmg, repeat 2)
10. Increased AoE (1.40x aoe, 0.95x dmg)
11. Awakened AoE (1.50x aoe, 0.98x dmg)
12. Concentrated Effect (0.70x aoe, 1.30x dmg)
13. Fortify (fortify buff, 1.15x dmg)
14. Life Leech (leech, 1.20x dmg)
15. Blind (blind enemies, 1.10x dmg)

### 4. Aura Optimization (Non-Neural)

Auras use a deterministic greedy algorithm (no training needed):

```python
def optimize_auras(build_stats, max_reservation=1.0):
    # 1. Score all auras by offense + defense contribution
    # 2. Sort by score (highest first)
    # 3. Greedily add auras until reservation limit
    # 4. Return selected auras
```

12 total auras → choose 3-4 based on build stats

## Shared Interaction Layer

**Purpose**: Learn how components synergize

**Architecture**:
- Concat encoders: (256 + 256 + 128) = 640 dims
- Linear(640 → 512) + ReLU + Dropout(0.3)
- Linear(512 → 256) + ReLU

**What it learns**:
1. **Tree-Gear interactions**:
   - Tree has +200% increased physical damage
   - → Gear with flat physical damage becomes more valuable
   
2. **Tree-Gem interactions**:
   - Tree has high crit chance + crit multi
   - → Crit support gems more valuable
   
3. **Gear-Gem interactions**:
   - Gear converts physical → fire
   - → Fire damage support gems more valuable
   
4. **Threshold effects**:
   - Current damage near one-shot threshold
   - → Prioritize damage nodes over speed nodes

## Training Objectives

### Multi-Task Learning (11 heads)

**Offensive predictions** (4 heads):
1. Total DPS (MSE loss)
2. Time to kill trash (MSE loss)
3. Time to kill bosses (MSE loss)
4. Clear speed score (MSE loss)

**Defensive predictions** (4 heads):
5. Max hit taken (MSE loss)
6. Effective HP (MSE loss)
7. Recovery per second (MSE loss)
8. Environmental damage score (MSE loss)

**Scenario predictions** (5 heads):
9. Mapper score (MSE loss)
10. Bosser score (MSE loss)
11. Balanced score (MSE loss)
12. Hardcore score (MSE loss)
13. Speed farmer score (MSE loss)

### Loss Weighting

```python
total_loss = (
    # Offensive (critical for survival via fast kills)
    1.5 * loss_dps +
    2.0 * loss_ttk_trash +        # TTK is THE key metric
    1.5 * loss_ttk_boss +
    1.0 * loss_clear_speed +
    
    # Defensive (critical for not dying)
    2.5 * loss_max_hit +           # One-shots are #1 killer
    1.5 * loss_ehp +
    1.5 * loss_recovery +
    1.8 * loss_env_damage +        # Degens kill many builds
    
    # Scenarios (user-facing predictions)
    1.0 * loss_mapper +
    1.0 * loss_bosser +
    1.0 * loss_balanced +
    1.0 * loss_hardcore +
    1.0 * loss_speed_farmer
)
```

Higher weights on what matters most for survival.

## Training Data

### Sources
1. **poe.ninja**: Top 10,000 builds from ladder
2. **Synthetic variations**: Modify good builds slightly
3. **Greedy optimizer results**: Bootstrap from working optimizer

### Features per Build
- Allocated passive nodes (1500-dim binary vector)
- Gear stats (500-dim aggregated stats)
- Gem setup (100-dim categorical + levels)
- Build metadata (class, ascendancy, level)
- Skill info (name, tags, base stats)

### Targets per Build
- All 13 objectives calculated via PoB
- Tested against 30+ enemies from poedb.tw
- Environmental damage survival scores
- Scenario-specific composite scores

## Inference Pipeline

```python
def optimize_build(current_build, scenario='balanced', iterations=5):
    """
    Iteratively improve build
    """
    build = current_build
    
    for i in range(iterations):
        # 1. Encode current build
        features = extract_features(build)
        
        # 2. Predict improvements
        predictions = model(features)
        
        # 3. Select scenario objective
        target_score = predictions[scenario]
        
        # 4. Apply top suggestions
        # Tree: allocate top 5 nodes
        top_nodes = torch.topk(predictions['tree'], k=5)
        build = allocate_nodes(build, top_nodes)
        
        # Gear: target these stat values per slot
        gear_targets = predictions['gear']
        build = update_gear_targets(build, gear_targets)
        
        # Gems: use these support categories
        gem_setup = predictions['gems']
        build = update_gems(build, gem_setup)
        
        # 5. Re-calculate with PoB
        build = recalculate_pob(build)
        
        # 6. Check improvement
        new_score = calculate_scenario_score(build, scenario)
        if new_score <= target_score:
            break  # Converged
    
    # 7. Optimize auras (deterministic)
    auras = optimize_auras(build.stats)
    build = apply_auras(build, auras)
    
    return build
```

## Model Size

**Parameters**:
- Tree encoder: (1500×512 + 512×256) = 899k params
- Gear encoder: (500×256) = 128k params
- Gem encoder: (100×128) = 13k params
- Shared layer: (640×512 + 512×256) = 459k params
- Tree decoder: (256×512 + 512×1500) = 899k params
- Gear decoders: 10×(256×64 + 64×5) = 167k params
- Gem decoder: (256×128 + 128×75) = 42k params
- Task heads: 13×(256×1) = 3k params

**Total**: ~2.6M parameters (small by modern standards)

**Memory**: ~10MB for model weights

**Training time**: ~8 hours on GPU (10k builds, 1000 epochs)

**Inference time**: ~50ms per build optimization iteration

## Advantages Over Greedy

1. **Learns synergies**: Understands cross-component interactions
2. **Global view**: Considers all components simultaneously
3. **Skill-aware**: Matches scaling vectors to skill base stats
4. **Fast**: 50ms per iteration vs 30s for full PoB calculation
5. **Improves over time**: Gets better with more training data

## Limitations

1. **Requires training data**: Need 10k+ builds to train well
2. **PoB dependency**: Still needs PoB for final validation
3. **Simplified gear**: Only outputs stat targets, not actual items
4. **User skill choice**: Doesn't recommend which skill to use

## Future Improvements

1. **Unique item handling**: Currently ignores unique-specific mechanics
2. **Cluster jewel support**: Add cluster jewel allocation
3. **Advanced interactions**: Reservation efficiency, curse limits
4. **Build diversity**: Ensure multiple viable solutions
5. **Incremental learning**: Update model with user feedback

## References

- reward_functions.md - Complete reward function design
- README.md - Project overview and quick start
- ../features.py - Feature extraction utilities
