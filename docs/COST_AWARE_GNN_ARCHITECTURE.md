# Cost-Aware GNN Architecture

## Overview

The enhanced GNN architecture incorporates distance-based costs, ROI calculations, and balanced allocation principles to generate realistic passive tree builds.

## Key Components

### 1. **Distance Calculation (BFS)**
```python
distances = calculate_distances_from_start(start_node_idx, edge_index)
# Shadow: [0, 1, 1, 2, 3, ...]  # Distance to each node
# Marauder: [50, 49, 48, ...]    # Different starting position
```

**Purpose**: Measures pathing cost from starting class to each node cluster.

### 2. **Effective Cost**
```python
effective_cost = 1.0 + (distance_penalty × distance)
```

**Examples**:
- Near node (10 distance): Cost = 1.0 + 0.1×10 = **2.0×**
- Far node (60 distance): Cost = 1.0 + 0.1×60 = **7.0×**

**Impact**: Far nodes need **3.5× the efficiency** to match near nodes' ROI!

### 3. **ROI Calculation**
```python
ROI = (efficiency × diminishing_returns_mult) / effective_cost
```

**Components**:
- **Efficiency**: Base stat value (e.g., 3% increased damage per point)
- **Diminishing Returns**: `exp(-2 × allocation_ratio)` 
  - At 0% allocated: 1.0× (full value)
  - At 50% allocated: 0.37× (heavy penalty)
  - At 100% allocated: 0.14× (very heavy penalty)
- **Effective Cost**: Includes distance penalty

**Example**:
```
Shadow allocating to Crit nodes (10 distance, 1.58% efficiency):
  Initial: ROI = (1.58 × 1.0) / 2.0 = 0.79
  At 50%:  ROI = (1.58 × 0.37) / 2.0 = 0.29

Shadow allocating to Life nodes (60 distance, 3.12% efficiency):
  Initial: ROI = (3.12 × 1.0) / 7.0 = 0.45  (worse than crit!)
  At 50%:  ROI = (3.12 × 0.37) / 7.0 = 0.16
```

### 4. **Balance Score**
```python
balance_score = exp(-coefficient_of_variation)
```

**Encourages balanced allocation**:
- All stats at 150%: CV = 0.0 → Score = 1.0 ✅
- Stats at [300%, 0%, 0%]: CV = 1.73 → Score = 0.18 ❌

**Why**: Balanced allocation maximizes product (DPS = ∏ vectors)

### 5. **Combined Scoring**
```python
final_score = (
    roi_weight × roi_score +
    balance_weight × balance_score +
    gnn_weight × learned_score +
    distance_weight × distance_penalty
)
```

**Learnable Weights** (trained via RL):
- `roi_weight = 0.35` - Analytical ROI component
- `balance_weight = 0.30` - Balance reward
- `gnn_weight = 0.20` - Neural network learned patterns
- `distance_weight = 0.15` - Distance penalty

## Training Strategy

### Phase 1: Supervised Pre-training
Train on expert builds from PoB to learn:
- Which starting classes work for which skills
- Common pathing strategies (Highway nodes, jewel sockets)
- Typical allocation patterns

### Phase 2: Reinforcement Learning
Optimize via PPO with reward function:

```python
reward = (
    0.4 × normalized_dps +          # Higher DPS is better
    0.3 × balance_score +            # Balanced allocation wins
    0.2 × (1 / avg_effective_cost) + # Minimize pathing cost
    0.1 × diversity_bonus            # Explore different strategies
)
```

**Key Insight**: The RL agent learns to balance:
1. High DPS (optimization goal)
2. Low cost (efficiency goal)
3. Balanced allocation (multiplicative product maximization)

### Phase 3: Fine-tuning per Skill
Fine-tune on specific skill archetypes:
- Crit builds (Shadow/Assassin start)
- DoT builds (Trickster/Occultist start)
- Life builds (Marauder/Juggernaut start)

## Implementation Details

### Distance-Aware Node Selection
```python
# During tree building
for step in range(num_points):
    # 1. Calculate ROI for all reachable nodes
    roi_scores = calculate_roi(node_relevance, effective_costs, 
                               current_allocation, scaling_vector)
    
    # 2. Calculate balance score
    balance_score = calculate_balance(current_allocation)
    
    # 3. Get GNN learned scores
    gnn_scores = gnn_forward_pass(context)
    
    # 4. Combine with learnable weights
    combined = (roi_weight * roi_scores + 
                balance_weight * balance_score +
                gnn_weight * gnn_scores)
    
    # 5. Select best node
    best_node = argmax(combined)
    
    # 6. Update allocation tracking
    allocate(best_node)
```

### Diminishing Returns Tracking
```python
current_allocation = {
    'increased_damage': 180,      # 60% of 300 ceiling
    'attack_speed': 90,           # 60% of 150 ceiling
    'critical_strike_chance': 57, # 60% of 95 ceiling
    'critical_strike_multiplier': 300  # 60% of 500 ceiling
}

# Next damage node gets penalty
damage_node_value = 10  # +10% increased damage
diminishing = exp(-2 × (180/300)) = exp(-1.2) = 0.30

# Effective value = 10 × 0.30 = 3.0 (reduced from 10!)
```

This **automatically** encourages the GNN to:
- Stop investing in saturated stats
- Spread points across multiple vectors
- Find the optimal balance point

## Visualization Integration

The cost-benefit visualizations directly inform GNN training:

### Hill Climb Landscape → GNN Loss Function
```python
# The 3D surface plot shows optimal paths
# GNN learns to follow these paths via imitation learning

def compute_landscape_loss(predicted_path, optimal_path):
    # Penalize deviation from high-ROI trajectory
    loss = 0
    for node in predicted_path:
        roi = calculate_roi(node)
        optimal_roi = max_roi_at_step()
        loss += (optimal_roi - roi) ** 2
    return loss
```

### Distance Coloring → Cost Function
```python
# Green nodes (near) should be prioritized early
# Red nodes (far) should only be taken if high efficiency

def compute_distance_efficiency_loss(path):
    loss = 0
    for step, node in enumerate(path):
        distance = distances[node]
        efficiency = node_efficiency[node]
        
        # Early steps should favor near nodes
        expected_distance = min(step * 2, 40)
        if distance > expected_distance and efficiency < threshold:
            loss += (distance - expected_distance) * penalty
    
    return loss
```

## Expected Behavior

### Shadow Building Lightning Strike (Crit)
```
Step 1-20:   Crit nodes (10-15 distance, ROI 0.7-0.8)
Step 21-40:  Attack speed (15-20 distance, ROI 0.6-0.7)
Step 41-60:  Phys damage (20-30 distance, ROI 0.5-0.6)
Step 61-80:  Crit multi (12-18 distance, ROI 0.4-0.5)
Step 81-100: Life/defenses (30-40 distance, ROI 0.3-0.4)

Final Allocation (balanced):
  Increased Damage: 180% (60% of ceiling)
  Attack Speed: 90% (60% of ceiling)
  Crit Chance: 57% (60% of ceiling)
  Crit Multi: 300% (60% of ceiling)

Total DPS: ~1,200 (balanced)
vs
Crit-only: ~800 (unbalanced, worse!)
```

### Marauder Building Lightning Strike (Non-Crit)
```
Step 1-30:   Phys damage (10-15 distance, ROI 0.8-0.9)
Step 31-60:  Life (8-12 distance, ROI 0.7-0.8)
Step 61-80:  Attack speed (25-30 distance, ROI 0.5-0.6)
Step 81-100: More damage (20-25 distance, ROI 0.4-0.5)

Note: Crit nodes avoided (55-60 distance, ROI 0.15 - terrible!)

Final Allocation:
  Increased Damage: 240% (80% of ceiling)
  Attack Speed: 120% (80% of ceiling)
  Life: 200% (80% of ceiling)
  Crit: 0% (skipped - too far!)

Total DPS: ~900 (non-crit viable)
```

## Key Advantages

1. **Realistic Pathing**: Considers actual tree distances, not just node values
2. **Class-Specific**: Learns different strategies for different starting positions
3. **Balanced Allocation**: Automatically maximizes multiplicative product
4. **Efficient**: Avoids expensive paths unless justified by high efficiency
5. **Interpretable**: ROI calculations can be visualized and debugged

## Training Data Requirements

For effective training, need:
1. **Passive tree graph** with edge connectivity
2. **Node statistics** (what stats each node provides)
3. **Starting positions** for each class
4. **Expert builds** (optional, for supervised pre-training)
5. **Skill scaling data** (from PoB calculations)

All of this can be extracted from PoB's Lua files!

## Next Steps

1. ✅ **Implement distance calculation** (BFS from starting class)
2. ✅ **Add ROI-based scoring** (efficiency / effective_cost)
3. ✅ **Track allocation for diminishing returns**
4. ✅ **Calculate balance rewards**
5. ⏳ **Train GNN with cost-aware loss function**
6. ⏳ **Validate on real builds from PoB**
7. ⏳ **Fine-tune per skill archetype**

## Summary

The cost-aware GNN transforms passive tree optimization from a simple "pick high-value nodes" problem into a realistic **constrained optimization** problem that mirrors how human players build:

- **Start near home**: Prioritize nearby clusters
- **Path efficiently**: Avoid long detours unless necessary
- **Balance investments**: Spread points across vectors
- **Diminishing returns**: Don't over-invest in one stat
- **Skill-specific**: Different skills need different strategies

This approach should produce builds that look and feel like real PoE builds, not just mathematically optimal but unrealistic allocations!
