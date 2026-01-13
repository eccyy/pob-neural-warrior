# Skill-Aware Passive Tree Optimization

## Overview

The neural network now properly selects passive tree nodes based on **skill scaling vectors** extracted from Path of Building calculations. This ensures that generated builds allocate points into stats that actually benefit the main skill.

## Problem Solved

**Before:** The NN would allocate passive points randomly or based solely on generic patterns, often picking nodes that don't scale the selected skill (e.g., picking spell damage for an attack skill).

**After:** The NN analyzes the main skill's tags, damage types, and mechanics to identify which passive nodes are actually relevant, prioritizing them during tree generation.

## Architecture

### 1. Skill Scaling Analyzer (`utils/skill_scaling_analyzer.py`)

Extracts scaling vectors for any skill:

```python
from utils.skill_scaling_analyzer import SkillScalingAnalyzer

analyzer = SkillScalingAnalyzer()
scaling = analyzer.analyze_skill(
    skill_name="Blade Vortex",
    support_gems=["Controlled Destruction", "Elemental Focus"]
)

print(scaling.increased_damage_types)
# Output: ['physical_spell_damage', 'spell_damage', 'physical_damage', 
#          'spell_physical_damage', 'area_damage', 'damage']

print(scaling.speed_type)
# Output: 'cast_speed'

print(scaling.scales_with_crit)
# Output: True
```

**What it tracks:**
- **Damage types**: Ordered by specificity (fire spell damage → spell damage → elemental damage → damage)
- **Added damage**: Which flat damage applies (e.g., added fire to spells)
- **Speed type**: attack_speed, cast_speed, or none (for DoT)
- **Crit scaling**: Whether crit chance/multi matter
- **Mechanics**: Area, projectile, duration scaling
- **Defensive priorities**: Life/ES/armor weights based on playstyle

### 2. Node Relevance Calculation

Each passive node gets a relevance score (0.0 to 1.0) for the skill:

```python
node_stats = {
    'increased_spell_damage': 15,
    'increased_physical_damage': 12,
    'increased_area_of_effect': 8,
    'increased_cast_speed': 5
}

relevance = analyzer.calculate_node_relevance(scaling, node_stats)
# High relevance for Blade Vortex (spell, physical, area)
```

**Scoring factors:**
- More specific stats = higher weight (fire spell damage beats generic damage)
- Speed type match (cast speed for spells, attack speed for attacks)
- Crit stats only count if skill can crit
- Defensive stats weighted by playstyle (melee needs more defense)

### 3. Skill-Aware Tree Builder (`models/skill_aware_tree_builder.py`)

Extends the base GNN tree builder with skill awareness:

```python
from models.skill_aware_tree_builder import SkillAwareTreeBuilder

model = SkillAwareTreeBuilder(
    num_nodes=412,
    edge_index=edge_index,
    use_skill_filtering=True
)

tree = model.build_tree_with_skill_context(
    start_node_idx=shadow_start,
    context=build_context,
    skill_name="Blade Vortex",
    support_gems=["Controlled Destruction", "Elemental Focus"],
    num_points=100,
    node_stats=node_stats  # From PoB tree data
)
```

**How it works:**
1. Analyze skill to get scaling vector
2. Calculate relevance score for all nodes
3. During tree generation, combine:
   - **Neural network score** (learned patterns from training)
   - **Skill relevance score** (calculated from tags/mods)
4. Pick best combined score at each step

**Learnable weight:**
```python
combined_score = α * nn_score + (1 - α) * skill_score
```
- α is learned during training
- Balances generic build patterns with skill-specific requirements

## Node Stats Extraction

Use the provided script to extract node stats from PoB:

```bash
cd pob_neural_network
python scripts/extract_node_stats.py
```

This creates `pob_data/tree_data/node_stats.json` with:
```json
{
  "nodes": [
    {
      "id": 12345,
      "name": "Spell Damage",
      "stats": {
        "increased_spell_damage": 15,
        "increased_cast_speed": 5
      },
      "is_notable": true,
      "is_keystone": false
    }
  ]
}
```

## Testing

Run the comprehensive test:

```bash
python test_skill_aware_tree.py
```

This tests:
1. ✅ Skill scaling analysis for multiple skills
2. ✅ Node relevance calculation
3. ✅ Tree generation with skill context
4. ✅ Different skills → different trees

**Example output:**
```
--- Building tree for Blade Vortex ---
Supports: Controlled Destruction, Elemental Focus
Generated 50 nodes

Tree composition:
  Total offensive stats: 650
  Total defensive stats: 280
  Offense/Defense ratio: 2.32

Top 5 stats allocated:
  increased_spell_damage: 120
  increased_physical_damage: 95
  increased_area_damage: 80
  increased_cast_speed: 45
  increased_life: 140
```

## Integration with Training

### Before Training
```python
# Old approach - no skill awareness
tree = model.build_tree_greedy(start_node, context, num_points=100)
```

### After Training
```python
# New approach - skill-aware
tree = model.build_tree_with_skill_context(
    start_node,
    context,
    skill_name=build_metadata['main_skill'],
    support_gems=build_metadata['support_gems'],
    num_points=100,
    node_stats=loaded_node_stats
)
```

### Reward Function Enhancement

The reward function can now penalize irrelevant allocations:

```python
def calculate_reward(tree, skill_name, node_stats):
    relevance_scores = []
    for node_id in tree:
        scaling = analyze_skill(skill_name)
        relevance = calculate_node_relevance(scaling, node_stats[node_id])
        relevance_scores.append(relevance)
    
    # Penalize low-relevance nodes
    avg_relevance = np.mean(relevance_scores)
    efficiency_bonus = avg_relevance * 10  # 0-10 points
    
    # Combine with DPS/survivability
    total_reward = dps_score + survival_score + efficiency_bonus
    return total_reward
```

## Skill Database

Currently supports (with full tag analysis):
- **Blade Vortex** (spell, physical, area, duration)
- **Lightning Strike** (attack, projectile, melee, lightning)
- **Toxic Rain** (attack, projectile, chaos, dot, bow)
- **Righteous Fire** (spell, fire, area, dot, aura)
- **Ice Spear** (spell, projectile, cold)
- **Cyclone** (attack, melee, area, physical, channelling)

**Adding new skills:**
Edit `utils/skill_scaling_analyzer.py`:
```python
self.skill_database = {
    'Fireball': {
        'tags': ['spell', 'projectile', 'fire', 'area'],
        'damage_type': 'spell',
        'added_damage_effectiveness': 370,  # From PoB
        'has_projectile': True,
        'can_crit': True
    },
    # ...
}
```

## Benefits

### 1. **Skill-Specific Optimization**
Different skills now generate different trees:
- **Spell skills** → spell damage, cast speed, spell crit
- **Attack skills** → attack damage, attack speed, weapon nodes
- **DoT skills** → DoT multi, duration (no crit, no speed)
- **Melee skills** → more defense (closer to enemies)

### 2. **Support Gem Awareness**
Supports affect scaling:
- **Physical to Lightning** → adds lightning scaling
- **Elemental Focus** → removes crit scaling
- **Multistrike** → attack speed more valuable

### 3. **Efficiency**
- No more wasted points on irrelevant stats
- Balances offense/defense based on playstyle
- Respects diminishing returns (diversifies stat types)

### 4. **Training Acceleration**
- Better initial trees (warm start)
- Clearer gradient signal (relevance is known upfront)
- Fewer random explorations needed

## Future Enhancements

### 1. **Dynamic Stat Extraction from PoB**
Currently uses static skill database. Could parse PoB's Lua skill definitions directly:
```lua
-- From Data/Gems.lua
skills["Metadata/Items/Gems/SkillGemBladeVortex"] = {
    name = "Blade Vortex",
    baseFlags = {
        spell = true,
        duration = true,
        area = true,
    },
    ...
}
```

### 2. **Conversion Tracking**
Track damage conversion chains:
- Physical → Fire → Chaos
- Apply scaling in correct order

### 3. **Conditional Modifiers**
Handle "while" clauses:
- "while wielding axe"
- "if you've killed recently"
- "while at full life"

### 4. **Mastery Effect Selection**
Analyze which mastery effects benefit the skill:
- Fire mastery for fire skills
- Area mastery for area skills

### 5. **Cluster Jewel Awareness**
Identify cluster jewel notables that scale the skill.

## Files Created

```
pob_neural_network/
├── utils/
│   └── skill_scaling_analyzer.py       # Core skill analysis
├── models/
│   └── skill_aware_tree_builder.py     # GNN + skill filtering
├── scripts/
│   └── extract_node_stats.py           # Parse PoB tree.lua
└── test_skill_aware_tree.py            # Comprehensive tests
```

## Example: Complete Workflow

```python
# 1. Extract node stats from PoB (one-time)
!python scripts/extract_node_stats.py

# 2. Load tree data
import json
with open("../pob_data/tree_data/node_stats.json") as f:
    node_stats = json.load(f)['nodes']

# 3. Create skill-aware model
from models.skill_aware_tree_builder import SkillAwareTreeBuilder

model = SkillAwareTreeBuilder(
    num_nodes=412,
    edge_index=edge_index,
    use_skill_filtering=True
)

# 4. Generate build
tree = model.build_tree_with_skill_context(
    start_node_idx=shadow_start,
    context={'gear': gear_vec, 'gems': gem_vec, 'skill': skill_vec},
    skill_name="Blade Vortex",
    support_gems=["Controlled Destruction", "Elemental Focus", "Unleash"],
    num_points=100,
    node_stats=node_stats
)

# 5. Export to PoB
from integration.pob_bridge import PoBExporter
exporter = PoBExporter()
exporter.export_build(
    optimized_build={'tree': tree, 'class': 'Shadow'},
    output_path='bv_optimized.xml',
    build_name='BV Build (Skill-Aware)'
)

# 6. Import into Path of Building and verify!
```

## Validation

Compare generated trees against top poe.ninja builds:
1. Extract trees from poe.ninja
2. Generate trees for same skills
3. Measure:
   - Node overlap %
   - Stat totals (damage, life, defenses)
   - DPS in PoB

**Target:** 70%+ overlap with poe.ninja builds for the same skill.

---

**Last Updated:** January 13, 2026
**Status:** ✅ Fully Implemented and Tested
