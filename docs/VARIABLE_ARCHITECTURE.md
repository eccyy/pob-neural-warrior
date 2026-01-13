# Variable Architecture: PoE Build Neural Network

## Overview

This document maps the 7 categories of variables to the actual system architecture, showing how data flows through the GNN, where each variable type is used, and what's implemented vs what needs building.

---

## ðŸŽ¯ 1. Structural Variables

**Purpose:** Describe the geometry and topology of the passive skill tree

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| Edge index | `edge_index.json` | GNN message passing | âœ… Working |
| Node adjacency | Derived from edges | Valid candidate filtering | âœ… Working |
| Node mapping | `node_mapping.json` | Node ID â†” index | âœ… Working |
| Graph embeddings | `TreeGraphEncoder` | Node representations | âœ… Working |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Node type | PoB `tree.lua` â†’ `type` field | Weight keystone vs small node | HIGH |
| Distance from start | BFS from class start | Pathing cost optimization | MEDIUM |
| Cluster membership | Community detection on graph | Cluster jewel planning | LOW |
| Pathing cost | Shortest path algorithm | Minimize travel nodes | MEDIUM |
| Required travel nodes | Path analysis | Identify inefficient pathing | LOW |

**Current Code Mapping:**

```python
# models/graph_tree_builder.py
class TreeGraphEncoder(nn.Module):
    def forward(self, x, edge_index):
        # Uses edge_index for message passing
        x = self.conv1(x, edge_index)  # Structural variables flow here
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = self.conv3(x, edge_index)
        return x  # Output: learned structural embeddings
```

**Data Flow:**
```
edge_index.json â†’ torch.tensor([2, 431]) â†’ GCNConv layers â†’ node embeddings [412, 128]
                                                â†“
                                    Used in get_valid_candidates()
                                    (only pick adjacent nodes)
```

---

## âš¡ 2. Feature Variables

**Purpose:** Describe what each node does (stats, modifiers, effects)

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| Fixed node features | Random init | GNN input (placeholder) | âš ï¸ Dummy data |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Flat life/ES | PoB `tree.lua` â†’ `sd` field | Defense calculation | **CRITICAL** |
| % increased life/ES | PoB stat mods | EHP calculation | **CRITICAL** |
| % increased damage | PoB stat mods | DPS calculation | **CRITICAL** |
| Crit multi | PoB stat mods | Crit DPS builds | HIGH |
| Resistances | PoB stat mods | Survivability check | **CRITICAL** |
| Scaling tags | Parse from stat text | Build synergy detection | HIGH |
| Recovery (regen/leech) | PoB stat mods | Sustain evaluation | MEDIUM |
| Movement speed | PoB stat mods | Clear speed proxy | LOW |

**Required Implementation:**

```python
# TODO: training/build_stats_decoder.py
class BuildStatsDecoder:
    """Extract aggregated build stats from passive tree"""
    
    def __init__(self, tree_lua_path):
        # Parse PoB tree.lua to get node stats
        self.node_stats = self._parse_tree_lua(tree_lua_path)
        # Example: self.node_stats[26725] = {
        #     'life_flat': 30,
        #     'life_percent': 8,
        #     'es_percent': 0,
        #     'fire_res': 15,
        #     ...
        # }
    
    def decode(self, allocated_nodes, gear_vector, gems_vector):
        """
        Args:
            allocated_nodes: List[int] - Node IDs in tree
            gear_vector: torch.Tensor[500] - Gear embeddings
            gems_vector: torch.Tensor[100] - Gem embeddings
        
        Returns:
            build_stats: dict - Aggregated build statistics
        """
        # Aggregate passive tree stats
        total_life_flat = sum(self.node_stats[n].get('life_flat', 0) for n in allocated_nodes)
        total_life_pct = sum(self.node_stats[n].get('life_percent', 0) for n in allocated_nodes)
        
        # TODO: Decode gear/gems (from embeddings or directly)
        gear_life = self._extract_gear_life(gear_vector)
        
        # Calculate derived stats
        total_life = (base_life + gear_life + total_life_flat) * (1 + total_life_pct/100)
        
        return {
            'life': total_life,
            'es': total_es,
            'armor': total_armor,
            'evasion': total_evasion,
            'fire_res': total_fire_res,
            # ... all defenses
            'dps': estimated_dps,
            'crit_chance': crit_chance,
            'crit_multi': crit_multi,
            # ... all offensive stats
        }
```

**Data Flow:**
```
PoB tree.lua â†’ parse node stats â†’ node_stats dict
                                         â†“
                            allocated_nodes [N] â†’ aggregate stats â†’ build_stats dict
                                                                           â†“
                                                                    Used in reward()
```

---

## ðŸ§  3. State Variables

**Purpose:** Track current build state during greedy tree generation

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| Allocated nodes set | PathGenerator | Prevent re-allocation | âœ… Working |
| Current context | Concatenated tensor | Node selection scoring | âœ… Working |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Current total life | BuildStatsDecoder | Guide defensive choices | **CRITICAL** |
| Current DPS estimate | BuildStatsDecoder | Guide offensive choices | **CRITICAL** |
| Current resistances | BuildStatsDecoder | Prioritize capping | **CRITICAL** |
| Current pathing cost | Path length tracker | Minimize travel nodes | MEDIUM |
| Current synergy tags | Tag detector | Maintain build coherence | HIGH |
| Current weaknesses | Stat analyzer | Address gaps | MEDIUM |

**Required Implementation:**

```python
# models/graph_tree_builder.py - Enhanced PathGenerator
class PathGenerator(nn.Module):
    def build_tree_greedy(self, gear, gems, skill, num_points, starting_node):
        allocated = [starting_node]
        log_probs = []
        
        # STATE TRACKING (NEW)
        current_stats = {
            'life': base_life,
            'dps': 0,
            'fire_res': 0,
            'synergy_tags': set(),
            'weaknesses': []
        }
        
        for step in range(num_points):
            # Get valid candidates
            candidates = self.get_valid_candidates(allocated, self.edge_index)
            
            # UPDATE STATE (NEW)
            for node in candidates:
                # Project: what happens if we take this node?
                node_stats = self.get_node_stats(node)
                projected_life = current_stats['life'] + node_stats['life_contribution']
                projected_dps = current_stats['dps'] + node_stats['dps_contribution']
                # Use projections to inform selection scoring
            
            # Score candidates with state awareness
            context = torch.cat([
                gear, gems, skill,
                torch.tensor([current_stats['life']]),  # NEW
                torch.tensor([current_stats['dps']]),   # NEW
                torch.tensor([current_stats['fire_res']]),  # NEW
                # ... other state variables
            ])
            
            scores = self.score_nodes(embeddings[candidates], context)
            
            # Select and update state
            selected = candidates[scores.argmax()]
            allocated.append(selected)
            current_stats = self._update_state(current_stats, selected)  # NEW
        
        return allocated, log_probs
```

**Data Flow:**
```
Initial state (base_life, 0 DPS, 0 res)
        â†“
   [Select node 1] â†’ update_state() â†’ {life: 150, dps: 0, fire_res: 0}
        â†“
   [Select node 2] â†’ update_state() â†’ {life: 150, dps: 0, fire_res: 15}
        â†“
   [Select node 3] â†’ update_state() â†’ {life: 180, dps: 50, fire_res: 15}
        â†“
        ... continue until num_points reached
```

---

## ðŸ§© 4. Outcome Variables

**Purpose:** What we ultimately care about (reward signals)

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| Diversity score | Heuristic | Temporary reward | âš ï¸ Placeholder |
| Size score | Node count | Temporary reward | âš ï¸ Placeholder |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Time to kill | FightSimulator | DPS check | **CRITICAL** |
| Survival probability | FightSimulator | Defense check | **CRITICAL** |
| Time to death | FightSimulator | Tankiness metric | **CRITICAL** |
| Effective HP | BuildStatsDecoder | One-shot threshold | **CRITICAL** |
| DPS uptime | FightSimulator | Realistic DPS | HIGH |
| Build uniqueness | Distance from meta | Anti-collapse | MEDIUM |
| Build complexity | Pathing efficiency | Penalize inefficiency | LOW |

**Required Implementation:**

```python
# training/fight_simulator.py
class FightSimulator:
    """Rule-based or learned encounter simulation"""
    
    def run(self, build_stats, encounter):
        """
        Args:
            build_stats: dict - From BuildStatsDecoder
            encounter: dict - Boss/map characteristics
        
        Returns:
            result: dict - Outcome variables
        """
        # Calculate effective HP
        physical_ehp = build_stats['life'] * (1 + build_stats['armor'] / (build_stats['armor'] + 10*encounter['phys_dmg']))
        elemental_ehp = build_stats['life'] * (1 + build_stats['fire_res']/100)
        
        # Simulate encounter
        ttk = encounter['boss_hp'] / build_stats['dps']  # Time to kill
        
        # Can you survive boss hit?
        boss_hit_damage = encounter['hit_damage'] * (1 - min(build_stats['fire_res']/100, 0.75))
        survived = (boss_hit_damage < physical_ehp)
        
        # How long until you die?
        if survived:
            ttd = physical_ehp / encounter['dps']  # Time to death
        else:
            ttd = 0.1  # One-shot
        
        return {
            'survived': survived,
            'time_to_kill': ttk,
            'time_to_death': ttd,
            'effective_hp': min(physical_ehp, elemental_ehp),
            'dps_uptime': self._calculate_uptime(build_stats, encounter)
        }
```

**Data Flow:**
```
build_stats + encounter â†’ FightSimulator.run() â†’ outcome_vars
                                                        â†“
                                            compute_reward(outcome_vars)
                                                        â†“
                                            REINFORCE: -(log_probs Ã— reward).sum()
```

---

## âš”ï¸ 5. Adversarial Variables

**Purpose:** Describe the environment/opponent to create realistic pressure

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| None | N/A | N/A | âŒ Not implemented |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Boss damage profile | Encounter generator | Evaluate defense layers | **CRITICAL** |
| Attack speed | Encounter generator | Sustain pressure | HIGH |
| Damage type mix | Encounter generator | Test all resists | HIGH |
| Map mods | Encounter generator | Handle -max res, etc. | MEDIUM |
| Movement pressure | Encounter generator | DPS uptime penalty | LOW |
| Phase transitions | Encounter generator | Burst requirements | LOW |

**Required Implementation:**

```python
# training/encounter_generator.py
class EncounterGenerator:
    """Generate realistic boss/map encounters"""
    
    def __init__(self):
        # Define encounter templates
        self.encounters = {
            'T16_boss': {
                'boss_hp': 10_000_000,
                'hit_damage': 5000,
                'dps': 2000,
                'phys_dmg': 0.5,
                'fire_dmg': 0.3,
                'cold_dmg': 0.2,
                'attack_speed': 1.5,
            },
            'maven': {
                'boss_hp': 50_000_000,
                'hit_damage': 8000,
                'dps': 3500,
                'phys_dmg': 0.3,
                'fire_dmg': 0.4,
                'cold_dmg': 0.3,
                'attack_speed': 2.0,
                'phases': 3,
            },
            'uber_maven': {
                'boss_hp': 100_000_000,
                'hit_damage': 15000,
                'dps': 6000,
                # ... even harder
            }
        }
    
    def sample_encounter(self, difficulty='medium'):
        """Sample a realistic encounter with some randomness"""
        base = self.encounters['T16_boss']
        
        # Add randomness
        return {
            'boss_hp': base['boss_hp'] * random.uniform(0.8, 1.2),
            'hit_damage': base['hit_damage'] * random.uniform(0.9, 1.3),
            'dps': base['dps'] * random.uniform(0.85, 1.15),
            'phys_dmg': max(0, base['phys_dmg'] + random.gauss(0, 0.1)),
            # ... vary all parameters
        }
    
    def generate_adversarial_encounter(self, model, num_trials=10):
        """Find an encounter that exposes model weaknesses"""
        encounters = [self.sample_encounter() for _ in range(num_trials)]
        
        # Test model against all
        results = [self._test_model(model, enc) for enc in encounters]
        
        # Return the hardest one model can't beat
        hardest_idx = min(range(len(results)), key=lambda i: results[i]['reward'])
        return encounters[hardest_idx]
```

**Data Flow (Adversarial Training Loop):**
```
EncounterGenerator.sample_encounter() â†’ encounter_1
                                              â†“
                                    Model generates tree
                                              â†“
                                    FightSimulator.run(tree, encounter_1)
                                              â†“
                                    reward_1 (low if model fails)
                                              â†“
                                    REINFORCE update
                                              â†“
                                    Generate harder encounter_2
                                              â†“
                                    Repeat (co-evolution)
```

---

## ðŸ”¥ 6. Exploration Variables

**Purpose:** Help the model explore the space efficiently and avoid meta collapse

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| Temperature | Manual parameter | Softmax temperature in sampling | âœ… Working |
| Greedy selection | argmax() | Deterministic best choice | âœ… Working |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Entropy of selection | Distribution stats | Monitor exploration | HIGH |
| Novelty score | Distance from history | Reward unique builds | HIGH |
| Diversity penalty | Similarity metric | Prevent mode collapse | HIGH |
| Exploration bonus | Underused nodes | Encourage exploration | MEDIUM |
| Mutation rate | GA-style variation | Alternative search method | LOW |

**Required Implementation:**

```python
# training/exploration.py
class ExplorationManager:
    """Manage exploration vs exploitation balance"""
    
    def __init__(self):
        self.build_history = []  # Store generated trees
        self.node_visit_counts = defaultdict(int)
    
    def compute_novelty_score(self, new_tree):
        """Reward for being different from historical builds"""
        if len(self.build_history) == 0:
            return 1.0
        
        # Jaccard distance from all previous trees
        distances = []
        new_set = set(new_tree)
        for old_tree in self.build_history:
            old_set = set(old_tree)
            intersection = len(new_set & old_set)
            union = len(new_set | old_set)
            jaccard = intersection / union if union > 0 else 0
            distances.append(1 - jaccard)  # Convert similarity to distance
        
        # Average distance = novelty
        novelty = sum(distances) / len(distances)
        return novelty
    
    def compute_exploration_bonus(self, new_tree):
        """Bonus for visiting underused nodes"""
        bonus = 0
        for node in new_tree:
            # Nodes visited less get higher bonus
            visit_count = self.node_visit_counts[node]
            bonus += 1.0 / (visit_count + 1)
        
        # Update visit counts
        for node in new_tree:
            self.node_visit_counts[node] += 1
        
        return bonus / len(new_tree)
    
    def should_increase_temperature(self, iteration, reward_history):
        """Adaptive temperature: increase if stuck in local optimum"""
        if len(reward_history) < 100:
            return False
        
        # Check if rewards plateaued
        recent_rewards = reward_history[-50:]
        variance = np.var(recent_rewards)
        
        # Low variance = stuck, need more exploration
        return variance < 0.01
```

**Enhanced Reward Function:**

```python
# training/reward.py
def compute_reward(build_stats, sim_result, tree, exploration_manager):
    """Combined reward with exploration bonus"""
    
    # Core performance reward
    survived = sim_result['survived']
    ttk = sim_result['time_to_kill']
    ttd = sim_result['time_to_death']
    
    performance_reward = (
        10.0 * survived +
        max(0, 1.0 - ttk/60) +  # Prefer faster kills
        min(ttd/10, 5.0)  # Reward tanky builds
    )
    
    # Exploration bonuses
    novelty = exploration_manager.compute_novelty_score(tree)
    exploration_bonus = exploration_manager.compute_exploration_bonus(tree)
    
    # Combined (exploration bonus decays over time)
    exploration_weight = 0.3  # 30% weight on exploration
    total_reward = (
        (1 - exploration_weight) * performance_reward +
        exploration_weight * (novelty + exploration_bonus)
    )
    
    return total_reward
```

**Data Flow:**
```
Generate tree â†’ compute_novelty_score() â†’ novelty_reward
                                               â†“
                               Combined with performance_reward
                                               â†“
                                    Total reward with exploration
                                               â†“
                                    REINFORCE update (encourages diversity)
```

---

## ðŸ§ª 7. Fitting Variables

**Purpose:** Help the model learn patterns and generalize

### Currently Implemented

| Variable | Source | Usage | Status |
|----------|--------|-------|--------|
| Node embeddings | GCN layers | Learned representations | âœ… Working |
| Edge index | Real tree | Graph structure | âœ… Working |

### Need to Implement

| Variable | Source | Usage | Priority |
|----------|--------|-------|----------|
| Build embeddings | Encoder network | High-level build representation | MEDIUM |
| Encounter embeddings | Encoder network | Environment representation | MEDIUM |
| Synergy vectors | Learned from data | Detect stat interactions | HIGH |
| Latent variables | VAE-style | Capture build archetypes | LOW |
| Confidence estimates | Uncertainty quantification | Avoid overconfident bad builds | MEDIUM |

**Optional Enhancement:**

```python
# models/build_encoder.py
class BuildEncoder(nn.Module):
    """Encode entire build into a latent vector"""
    
    def __init__(self, num_nodes=412, hidden_dim=128, latent_dim=32):
        super().__init__()
        self.node_embedding = nn.Embedding(num_nodes, hidden_dim)
        self.set_encoder = nn.TransformerEncoder(...)  # Aggregate nodes
        self.fc = nn.Linear(hidden_dim, latent_dim)
    
    def forward(self, allocated_nodes):
        """
        Args:
            allocated_nodes: List[int] - Node IDs
        
        Returns:
            build_embedding: torch.Tensor[latent_dim]
        """
        # Embed each node
        node_embeds = self.node_embedding(torch.tensor(allocated_nodes))
        
        # Aggregate with attention (order-invariant)
        aggregated = self.set_encoder(node_embeds)
        
        # Project to latent space
        build_embedding = self.fc(aggregated.mean(0))
        
        return build_embedding  # [32] - captures build "archetype"
```

**Use Case:**

```python
# In training loop
build_embedding = build_encoder(tree)

# Use for diversity: Penalize builds with similar embeddings
similarity = cosine_similarity(build_embedding, historical_embeddings)
diversity_penalty = -similarity.max()  # Penalize if too similar

# Use for transfer learning: Cluster similar build types
cluster_id = kmeans.predict(build_embedding)
# -> Can train specialized models per archetype
```

---

## ðŸ”„ Complete Data Flow Diagram

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                         TRAINING ITERATION                          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

1. SETUP
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Structural Vars â”‚ edge_index.json â†’ GNN
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Feature Vars    â”‚ tree.lua â†’ node_stats dict
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Exploration Mgr â”‚ Initialize history, visit counts
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

2. GENERATE TREE
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Sample context   â”‚ â†’ gear, gems, skill, class
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Initialize state â”‚ â†’ {life: base, dps: 0, res: 0}
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Greedy Generation Loop (N nodes)       â”‚
   â”‚                                        â”‚
   â”‚ For each step:                         â”‚
   â”‚   1. Get valid candidates (adjacent)   â”‚  â† Structural Vars
   â”‚   2. Encode context + state            â”‚  â† State Vars
   â”‚   3. Score candidates with GNN         â”‚  â† Fitting Vars (embeddings)
   â”‚   4. Select node (greedy or sample)    â”‚  â† Exploration Vars (temperature)
   â”‚   5. Update state                      â”‚  â† Feature Vars (node stats)
   â”‚   6. Track log probability             â”‚  â† For REINFORCE
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   Generated tree: [node1, node2, ..., nodeN]

3. EVALUATE TREE
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ BuildStatsDecoder       â”‚
   â”‚ allocated_nodes â†’ stats â”‚  â† Feature Vars (aggregate)
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   build_stats = {life, dps, res, ...}
            â†“
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ EncounterGenerator      â”‚
   â”‚ Sample/generate boss    â”‚  â† Adversarial Vars
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   encounter = {boss_hp, hit_damage, ...}
            â†“
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ FightSimulator          â”‚
   â”‚ Simulate fight          â”‚  â† Outcome Vars (compute)
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   result = {survived, ttk, ttd, ...}

4. COMPUTE REWARD
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Performance reward      â”‚  â† Outcome Vars (from result)
   â”‚ + Novelty bonus         â”‚  â† Exploration Vars
   â”‚ + Exploration bonus     â”‚  â† Exploration Vars
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   total_reward = f(result, novelty, exploration)

5. UPDATE MODEL
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ REINFORCE               â”‚
   â”‚ loss = -(log_probs      â”‚  â† Tracked during generation
   â”‚         Ã— reward).sum() â”‚  â† From step 4
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
   loss.backward() â†’ optimizer.step()

6. TRACK EXPLORATION
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ Update build history    â”‚
   â”‚ Update visit counts     â”‚
   â”‚ Check for plateau       â”‚
   â”‚ Adjust temperature      â”‚  â† Exploration Vars (adaptive)
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

7. REPEAT (10k+ iterations)
```

---

## ðŸ“Š Variable Usage Summary

| Category | Current Status | Critical Path | Files Needed |
|----------|---------------|---------------|--------------|
| **Structural** | âœ… 80% done | Extract node types | `parse_node_types.py` |
| **Feature** | âŒ 10% done | **BuildStatsDecoder** | `training/build_stats_decoder.py` |
| **State** | âš ï¸ 40% done | **State tracking in PathGenerator** | `models/graph_tree_builder.py` (enhance) |
| **Outcome** | âŒ 0% done | **FightSimulator** | `training/fight_simulator.py` |
| **Adversarial** | âŒ 0% done | **EncounterGenerator** | `training/encounter_generator.py` |
| **Exploration** | âš ï¸ 30% done | **ExplorationManager** | `training/exploration.py` |
| **Fitting** | âœ… 60% done | Optional: BuildEncoder | `models/build_encoder.py` (optional) |

---

## ðŸŽ¯ Implementation Priority

### Phase 1: Core Evaluation (CRITICAL)
1. **BuildStatsDecoder** - Extract stats from tree
   - Parse PoB tree.lua
   - Aggregate node stats
   - Calculate derived stats (EHP, effective DPS)
   - **Blocks all real training**

2. **FightSimulator** - Evaluate build performance
   - Rule-based encounter simulation
   - Survival check (can tank boss hit?)
   - Time-to-kill calculation
   - **Provides real reward signal**

### Phase 2: Exploration & Diversity (HIGH)
3. **ExplorationManager** - Prevent mode collapse
   - Track build history
   - Compute novelty scores
   - Adaptive temperature
   - **Ensures diverse builds**

4. **Enhanced State Tracking** - Context-aware generation
   - Track life/dps/res during generation
   - Project impact of candidates
   - **Improves greedy selection quality**

### Phase 3: Adversarial Co-Evolution (MEDIUM)
5. **EncounterGenerator** - Realistic pressure
   - Encounter templates
   - Adaptive difficulty
   - **Tests builds thoroughly**

### Phase 4: Advanced Features (LOW)
6. **BuildEncoder** - Learn build archetypes (optional)
7. **Synergy detection** - Identify stat interactions (optional)
8. **Confidence estimates** - Uncertainty quantification (optional)

---

## ðŸ’¡ Key Insights

1. **Structural + Feature = Understanding**
   - Structural variables â†’ graph geometry
   - Feature variables â†’ what nodes do
   - Combined â†’ GNN learns meaningful patterns

2. **State = Context-Aware Decisions**
   - Without state: Greedy selection is blind
   - With state: Model knows what build needs next
   - Example: Low life â†’ prioritize +life nodes

3. **Outcome = Reward Signal**
   - Must be realistic (not just DPS)
   - Must be differentiable (for gradients)
   - Must balance multiple objectives

4. **Adversarial = Realistic Pressure**
   - Forces builds to be robust
   - Exposes weaknesses
   - Co-evolves with generator

5. **Exploration = Avoiding Meta Collapse**
   - Pure performance â†’ single meta build
   - Exploration bonus â†’ diverse builds
   - Balance is critical

6. **Fitting = Generalization**
   - Learned embeddings capture patterns
   - Prevents overfitting to specific builds
   - Enables transfer to new contexts

---

## ðŸš€ Next Steps

1. **Implement BuildStatsDecoder** (2-3 days)
   - Parse tree.lua with lupa
   - Extract all node stats
   - Test on existing builds

2. **Implement FightSimulator** (1-2 days)
   - Start simple: resist cap, EHP, DPS check
   - Test against known builds
   - Validate realistic

3. **Enhance PathGenerator** (1 day)
   - Add state tracking
   - Use BuildStatsDecoder for projections
   - Test improvement in tree quality

4. **Implement ExplorationManager** (1 day)
   - Track history
   - Compute novelty
   - Test diversity of generated builds

5. **Full training run** (ongoing)
   - 10k iterations
   - Monitor convergence
   - Validate build quality in PoB

---

**Current Status:** Tree generation works, but rewards are placeholders. Priority: Build real evaluation pipeline (Feature â†’ Outcome variables).
