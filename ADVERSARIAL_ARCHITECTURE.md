# Current GNN + Adversarial Training Architecture

## Current Setup (What We Have)

### 1. Build Policy Network (GNN)
**File:** `models/graph_tree_builder.py`

**Architecture:**
- **GraphTreeBuilder** - Graph Neural Network for passive tree generation
- Uses GCNConv layers (3 layers) for node embeddings
- Input: 
  - Graph structure (412 nodes, 431 edges from real PoB tree)
  - Starting node index
  - Context: gear (20 dims), gems (30 dims), skill (10 dims)
- Output: Greedy node selection (builds tree one node at a time)
- Parameters: 1.66M parameters

**Current Generation Process:**
```python
def build_tree_greedy(self, start_node_idx, context, num_nodes=100):
    allocated = torch.zeros(num_nodes, dtype=torch.bool)
    allocated[start_node_idx] = True
    tree_sequence = [start_node_idx]
    
    for _ in range(num_nodes - 1):
        # Get neighbor nodes
        neighbors = get_unallocated_neighbors(allocated)
        if len(neighbors) == 0:
            break
        
        # Score neighbors with GNN
        scores = self.forward(allocated, context)
        
        # Pick best unallocated neighbor
        best_neighbor = neighbors[scores[neighbors].argmax()]
        allocated[best_neighbor] = True
        tree_sequence.append(best_neighbor)
    
    return tree_sequence
```

**Key Features:**
- ✓ Greedy path generation (one node at a time)
- ✓ Respects graph connectivity (only picks reachable neighbors)
- ✓ Context-aware (gear, gems, skill influence choices)
- ✓ Generates connected trees
- ✓ Exports to PoB XML format

### 2. Node Mapping & Edges
**Files:**
- `pob_data/tree_data/edge_index.json` - Real tree edges (431 edges)
- `pob_data/tree_data/node_mapping.json` - 412 unique nodes from training data

**Filtered Node Types:**
- ✓ Ascendancy nodes removed (479 nodes filtered)
- ✓ Mastery nodes removed (349 nodes filtered)
- ✓ Only regular passive nodes (small, notable, keystone, jewel sockets)

### 3. Export Pipeline
**Files:**
- `integration/pob_bridge.py` - PoB XML export
- `test_graph_export.py` - Testing script

**Current Export:**
- Prepends class starting nodes (e.g., Shadow: 38129 → 44683 → 45272)
- Filters duplicates
- Validates connectivity
- Generates valid PoB XML with ~97 connected nodes

---

## What We Need to Add (Adversarial Training)

### Phase 1: Environment Model (Fight Simulator)

**Option A: Neural Predictor** (Recommended to start)
```python
class BuildEvaluator(nn.Module):
    """
    Predicts build performance from build stats.
    """
    def __init__(self):
        # Input: build stats (life, ES, armor, evasion, resists, DPS, etc.)
        # Output: survival_prob, time_to_kill, expected_damage_taken
        
    def forward(self, build_stats, encounter_context):
        # Returns reward components
        return {
            'survival': 0.0-1.0,
            'dps_uptime': 0.0-1.0,
            'ttk': seconds,
            'damage_taken': float
        }
```

**Option B: Rule-Based Simulator**
```python
def simulate_encounter(build_stats, boss_type, map_mods):
    """
    Hand-crafted combat rules:
    - Check if resists capped
    - Compute EHP vs one-shots
    - Calculate DPS vs boss HP
    - Check recovery rate vs DoT
    """
    pass
```

**Data Needed:**
- Build stats extraction from passive tree
- PoB's calculation engine (or approximation)
- Boss/map statistics (HP, damage, mechanics)

### Phase 2: Build Stats Decoder

**File to create:** `models/build_stats_decoder.py`

```python
class BuildStatsDecoder:
    """
    Converts passive tree + gear + gems → build stats.
    Uses PoB's calculation engine or neural approximation.
    """
    def decode(self, tree_nodes, gear, gems, skill):
        # Extract passive stats
        passive_stats = self.get_passive_stats(tree_nodes)
        
        # Combine with gear/gems
        total_stats = self.combine_stats(passive_stats, gear, gems)
        
        # Calculate derived stats (EHP, DPS, etc.)
        derived = self.calculate_derived_stats(total_stats, skill)
        
        return {
            'life': int,
            'es': int,
            'armor': int,
            'evasion': int,
            'resists': [fire, cold, lightning, chaos],
            'block': float,
            'dps': float,
            'crit_chance': float,
            'leech': float,
            'regen': float,
            # ... more stats
        }
```

**Integration with PoB:**
- Use PoB's Lua calculation engine directly
- Or train neural approximator on PoB output

### Phase 3: Reward Function

**File to create:** `training/reward.py`

```python
def compute_reward(build_stats, encounter_result, uniqueness_score):
    """
    Multi-objective reward function.
    """
    # Survival component
    survival = encounter_result['survival']
    
    # Kill speed component
    ttk_score = 1.0 / (1.0 + encounter_result['ttk'] / 10.0)
    
    # Efficiency (don't over-invest)
    efficiency = 1.0 - (overkill_penalty + overdefense_penalty)
    
    # Uniqueness (avoid meta-copying)
    diversity = uniqueness_score  # Distance from common builds
    
    # Weighted combination
    reward = (
        0.4 * survival +
        0.3 * ttk_score +
        0.2 * efficiency +
        0.1 * diversity
    )
    
    return reward
```

### Phase 4: RL Training Loop

**File to create:** `training/adversarial_trainer.py`

```python
class AdversarialTrainer:
    def __init__(self, policy_network, evaluator):
        self.policy = policy_network  # Our GNN
        self.evaluator = evaluator    # Environment model
        self.optimizer = torch.optim.Adam(policy.parameters())
        
    def train_step(self):
        # 1. Sample context
        context = self.sample_context()  # class, gear, gems, skill
        
        # 2. Generate build with GNN (save log probs)
        tree, log_probs = self.policy.build_tree_with_logprobs(
            context['start_node'],
            context['gear'],
            context['gems'],
            context['skill']
        )
        
        # 3. Decode to build stats
        build_stats = self.decoder.decode(tree, context)
        
        # 4. Evaluate in environment
        encounter = self.sample_encounter()  # boss/map
        result = self.evaluator(build_stats, encounter)
        
        # 5. Compute reward
        reward = compute_reward(build_stats, result, self.uniqueness(tree))
        
        # 6. Update policy (REINFORCE)
        loss = -sum(log_prob * reward for log_prob in log_probs)
        loss.backward()
        self.optimizer.step()
        
        return reward, build_stats
        
    def train(self, num_iterations):
        for i in range(num_iterations):
            reward, stats = self.train_step()
            # Log metrics, save checkpoints, etc.
```

### Phase 5: Adversarial Environment (Optional Advanced)

**File to create:** `models/adversarial_encounter_generator.py`

```python
class AdversarialEncounterGenerator(nn.Module):
    """
    Learns to generate challenging encounters.
    Tries to find weaknesses in builds.
    """
    def generate_encounter(self, build_stats):
        # Analyze build weaknesses
        weaknesses = self.identify_weaknesses(build_stats)
        
        # Generate encounter that exploits them
        encounter = self.create_challenging_scenario(weaknesses)
        
        return encounter
    
    def train_step(self, policy_network):
        # Generate encounter
        # Run policy against it
        # If policy succeeds: increase difficulty
        # If policy fails: adjust difficulty curve
        pass
```

---

## Implementation Roadmap

### Milestone 1: Build Stats Extraction ⚠️ CRITICAL PATH
**Priority: HIGH**
- [ ] Create `BuildStatsDecoder` class
- [ ] Extract passive stats from PoB tree data
- [ ] Integrate PoB calculation engine (Lua interop or neural approximation)
- [ ] Test: Generate tree → get accurate DPS/EHP

**Why first:** Can't train without knowing what builds actually do!

### Milestone 2: Simple Evaluator
**Priority: HIGH**
- [ ] Create simple rule-based evaluator
- [ ] Define encounters (T16 boss, Maven, Uber Pinnacle)
- [ ] Implement basic survival/TTK calculation
- [ ] Test: Can it rank builds sensibly?

### Milestone 3: Policy with Log Probs
**Priority: MEDIUM**
- [ ] Modify `build_tree_greedy` to return log probabilities
- [ ] Store action sequence for RL updates
- [ ] Implement softmax temperature for exploration
- [ ] Test: Can we compute gradients through tree generation?

### Milestone 4: Training Loop
**Priority: MEDIUM**
- [ ] Implement REINFORCE algorithm
- [ ] Create reward function
- [ ] Set up training loop
- [ ] Log metrics (reward, DPS, EHP over time)

### Milestone 5: Neural Evaluator (Advanced)
**Priority: LOW**
- [ ] Collect dataset of (build_stats, encounter, result)
- [ ] Train neural predictor
- [ ] Replace rule-based evaluator
- [ ] Fine-tune together with policy

### Milestone 6: Adversarial Encounters (Research)
**Priority: LOW**
- [ ] Implement encounter generator
- [ ] Set up adversarial training loop
- [ ] Balance difficulty curve
- [ ] Test: Does it find real weaknesses?

---

## Key Design Decisions

### ✓ Keep What Works
- Greedy GNN tree generation (it's actually perfect for RL!)
- Graph structure (respects tree topology)
- Context encoding (gear/gems/skill)

### → Modify Slightly
- Add `sample_with_logprobs()` method (for RL gradients)
- Add temperature parameter (for exploration)
- Return action sequence (for credit assignment)

### + Add New Components
- BuildStatsDecoder (PoB integration)
- Evaluator/Environment (fight simulator)
- Reward function (multi-objective)
- RL trainer (REINFORCE/PPO)

---

## Why This Works

1. **Greedy = Sequential Policy**
   - Each node choice is a discrete action
   - Natural for credit assignment
   - Can analyze decision paths

2. **GNN = Structure Awareness**
   - Respects tree connectivity
   - Learns cluster synergies
   - Generalizes across tree regions

3. **Adversarial = Real Builds**
   - Stops "PoB warrior" builds
   - Forces defensive investment
   - Discovers creative solutions

4. **Modular = Iterative Development**
   - Can improve each component independently
   - Start simple (rule-based eval)
   - Upgrade later (neural eval, adversarial encounters)

---

## Next Immediate Steps

1. **Extract build stats from passive tree**
   - Use PoB's tree data to get stat modifiers
   - Implement stat aggregation
   - Calculate life/ES/armor/DPS

2. **Create simple fight simulator**
   - Define 3-5 boss archetypes
   - Rule-based damage/survival calculation
   - Test with hand-crafted builds

3. **Modify GNN for RL**
   - Add `sample_node()` method with log probs
   - Implement action sequence tracking
   - Test gradient flow

Would you like me to start implementing any of these components?
