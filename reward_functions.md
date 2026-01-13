# Reward Function Design for PoE Build Optimizer

## The Challenge

Path of Exile has multiple competing objectives that interact in complex ways:
- **Offense**: Kill speed, clear speed, single target DPS
- **Defense**: Survive different damage patterns (many small hits vs few big hits)
- **Recovery**: Life/ES regen, leech, sustain
- **Utility**: Movement speed, quality of life

**Critical Insight**: **Offense IS defense**. Enemies can't hurt you if they're dead.

A simple `DPS × EHP` metric misses critical nuances:
- High DPS but slow kills (low hit rate) = more damage taken
- High DPS with fast kills (high hit rate) = less damage taken
- Time to kill directly impacts total incoming damage

## Key Offensive Metrics

### 1. Time to Kill (Most Important Offensive Metric)

Time to kill is the KEY metric because it directly determines how much damage you take. Faster kills = less time exposed = less damage taken.

```python
def time_to_kill(build, enemy_type='normal'):
    """
    How long it takes to kill different enemy types
    
    Enemy types:
    - trash: Regular pack monsters (50k HP)
    - rare: Rare/magic monsters (500k HP)  
    - boss: Map bosses (5M HP)
    - endgame_boss: Pinnacle bosses (50M HP)
    """
    enemy_hp = {
        'trash': 50_000,
        'rare': 500_000,
        'boss': 5_000_000,
        'endgame_boss': 50_000_000
    }
    
    dps = build.stats.TotalDPS
    if dps <= 0:
        return float('inf')
    
    hp = enemy_hp.get(enemy_type, enemy_hp['trash'])
    ttk = hp / dps
    
    return ttk

def damage_taken_while_killing(build, enemy_type='trash', enemy_dps=5000):
    """
    Calculate total damage taken while killing an enemy
    THIS is why DPS matters for defense!
    
    Example:
    - Build A: 5M DPS, kills trash in 0.01 sec → takes 50 damage
    - Build B: 1M DPS, kills trash in 0.05 sec → takes 250 damage
    
    Build A is 5x safer despite same defenses!
    """
    ttk = time_to_kill(build, enemy_type)
    
    # Total raw damage taken
    total_incoming = enemy_dps * ttk
    
    # Apply mitigation
    mitigation = build.stats.PhysicalDamageReduction / 100
    total_incoming *= (1 - mitigation)
    
    return total_incoming
```

### 2. Hit Rate vs Hit Damage

Builds with the same DPS can have very different "feel" and effectiveness:

```python
def analyze_hit_pattern(build):
    """
    Different hit patterns have different effectiveness
    
    Pattern A: 10 hits/sec × 100k damage = 1M DPS
    Pattern B: 2 hits/sec × 500k damage = 1M DPS
    
    Pattern A:
    - Kills trash instantly (< 1 hit needed)
    - Better for leech (more frequent hits)
    - Better for life on hit recovery
    
    Pattern B:
    - Overkills trash (wastes damage)
    - Slower leech ramp-up
    - Less recovery from life on hit
    """
    dps = build.stats.TotalDPS
    hit_rate = build.stats.HitRate  # Attacks or casts per second
    damage_per_hit = dps / hit_rate if hit_rate > 0 else 0
    
    return {
        'dps': dps,
        'hit_rate': hit_rate,
        'damage_per_hit': damage_per_hit,
        'pattern': 'rapid' if hit_rate > 5 else 'slow'
    }
```

### 3. Clear Speed (For Mapping)

```python
def clear_speed_score(build):
    """
    How fast can you clear packs of enemies
    
    Factors:
    - AoE radius (how many enemies you hit at once)
    - Hit rate (how many times you attack)
    - Movement speed (how fast you get to next pack)
    - DPS (how fast each pack dies)
    """
    aoe_radius = build.stats.AreaOfEffectRadius
    hit_rate = build.stats.HitRate
    move_speed = build.stats.MovementSpeed / 100
    
    # Time to kill a pack
    pack_ttk = time_to_kill(build, 'trash')
    
    # Time between packs (depends on screen distance and move speed)
    time_between_packs = 20 / move_speed  # ~20 units between packs
    
    # Packs per minute
    packs_per_minute = 60 / (pack_ttk + time_between_packs)
    
    # More AoE = hit more enemies per attack = fewer attacks needed
    clear_score = packs_per_minute * (1 + aoe_radius / 10)
    
    return clear_score
```

## Key Defensive Metrics

### 1. Maximum Hit Taken (One-Shot Protection)
```python
def max_hit_taken(build):
    """
    Maximum physical/elemental/chaos hit that can be survived
    Critical for boss encounters with big slams
    """
    life = build.stats.Life
    es = build.stats.EnergyShield
    
    # Physical max hit
    phys_reduction = build.stats.PhysicalDamageReduction / 100
    armour_effectiveness = calculate_armour_vs_hit(build.stats.Armour)
    phys_max_hit = (life + es) / (1 - phys_reduction * armour_effectiveness)
    
    # Elemental max hit (per element)
    fire_res = min(build.stats.FireResist, 90) / 100
    fire_max_hit = (life + es) / (1 - fire_res)
    
    # Combined score (weakest link matters)
    return min(phys_max_hit, fire_max_hit, cold_max_hit, lightning_max_hit)
```

### 2. Effective Hit Points (EHP) - Sustained Damage
```python
def effective_hp(build):
    """
    How much damage needed to kill you against sustained hits
    Good for mapping, DoT ground effects
    """
    life = build.stats.Life
    es = build.stats.EnergyShield
    
    # Layer 1: Avoidance/Evasion
    evade_chance = build.stats.EvadeChance / 100
    dodge_chance = build.stats.DodgeChance / 100
    block_chance = build.stats.BlockChance / 100
    avoidance = 1 - (1 - evade_chance) * (1 - dodge_chance) * (1 - block_chance)
    
    # Layer 2: Mitigation
    phys_reduction = build.stats.PhysicalDamageReduction / 100
    
    # Combined EHP
    base_hp = life + es
    ehp = base_hp / (1 - avoidance) / (1 - phys_reduction)
    
    return ehp
```

### 3. Recovery Rate (Sustain)
```python
def recovery_per_second(build):
    """
    How fast can you recover from damage
    Critical for extended fights and recovery windows
    """
    # Regeneration
    life_regen = build.stats.LifeRegen
    es_regen = build.stats.ESRecharge
    
    # Leech (capped)
    max_leech_rate = build.stats.MaxLifeLeechRate / 100
    leech_per_hit = build.stats.LifeLeechPerHit
    hits_per_second = build.stats.HitRate
    actual_leech = min(leech_per_hit * hits_per_second, max_leech_rate * build.stats.Life)
    
    # Life/ES on hit
    life_on_hit = build.stats.LifeGainedOnHit * hits_per_second
    
    total_recovery = life_regen + actual_leech + life_on_hit + es_regen
    
    return total_recovery
```

### 4. Time to Kill (TTK) vs Different Damage Patterns
```python
def time_to_kill(build, damage_pattern):
    """
    How long can you survive a specific damage pattern
    
    damage_pattern examples:
    - "small_rapid": 1000 dmg × 10 hits/sec (mapping)
    - "medium_steady": 5000 dmg × 2 hits/sec (bosses)
    - "large_slam": 50000 dmg × 0.2 hits/sec (one-shots)
    """
    hits_per_sec = damage_pattern.frequency
    damage_per_hit = damage_pattern.damage
    
    # Effective HP after mitigation
    ehp = effective_hp(build)
    
    # Recovery reduces effective incoming damage
    recovery = recovery_per_second(build)
    net_dps = (damage_per_hit * hits_per_sec) - recovery
    
    if net_dps <= 0:
        return float('inf')  # Immortal against this pattern
    
    ttk = ehp / net_dps
    return ttk
```

### 5. Environmental/Unavoidable Damage (DoT, Ground Effects)

**Critical Insight**: Some damage cannot be avoided by killing enemies faster. Ground degens, DoT effects, and environmental damage are UNAVOIDABLE and test your recovery/sustain.

```python
def can_survive_degen(build, degen_type='burning_ground'):
    """
    Can you survive standing in environmental damage?
    
    Examples:
    - Burning ground: ~5000 fire DPS
    - Caustic ground: ~8000 chaos DPS
    - Sirus storms: ~15000 DPS
    - Shaper beam: ~20000 DPS (while moving through)
    - Maven memory game: ~10000 DPS
    
    Key insight: Even though these can be "several life pools per second",
    they are CAPPED by game balance. You can't face-tank 1M DPS degens.
    
    What matters:
    1. Resistance (mitigation)
    2. Recovery rate (can you outheal it?)
    3. Life/ES pool (how long can you tank it?)
    """
    
    degen_patterns = {
        'burning_ground': {
            'base_dps': 5000,
            'damage_type': 'fire',
            'duration': 'sustained'  # Can last entire fight
        },
        'caustic_ground': {
            'base_dps': 8000,
            'damage_type': 'chaos',
            'duration': 'sustained'
        },
        'sirus_storm': {
            'base_dps': 15000,
            'damage_type': 'physical',
            'duration': 'sustained'
        },
        'maven_degen': {
            'base_dps': 10000,
            'damage_type': 'mixed',  # All damage types
            'duration': 'burst'  # 5-10 seconds
        },
        'shaper_beam': {
            'base_dps': 20000,
            'damage_type': 'cold',
            'duration': 'burst'  # 1-2 seconds while moving
        }
    }
    
    degen = degen_patterns.get(degen_type, degen_patterns['burning_ground'])
    base_dps = degen['base_dps']
    
    # Apply resistances (mitigation)
    if degen['damage_type'] == 'fire':
        resist = min(build.stats.FireResist, 90) / 100
        mitigated_dps = base_dps * (1 - resist)
    elif degen['damage_type'] == 'chaos':
        resist = min(build.stats.ChaosResist, 90) / 100
        mitigated_dps = base_dps * (1 - resist)
    elif degen['damage_type'] == 'physical':
        reduction = build.stats.PhysicalDamageReduction / 100
        mitigated_dps = base_dps * (1 - reduction)
    else:  # mixed
        avg_resist = (build.stats.FireResist + build.stats.ColdResist + 
                     build.stats.LightningResist) / 3 / 100
        mitigated_dps = base_dps * (1 - avg_resist)
    
    # Calculate net damage after recovery
    recovery = recovery_per_second(build)
    net_dps = mitigated_dps - recovery
    
    # Can we outheal it?
    if net_dps <= 0:
        return {
            'survivable': True,
            'indefinite': True,
            'time_to_death': float('inf'),
            'net_dps': net_dps
        }
    
    # How long can we survive?
    life = build.stats.Life
    es = build.stats.EnergyShield
    total_pool = life + es
    
    time_to_death = total_pool / net_dps
    
    # For sustained degens, need to survive indefinitely
    # For burst degens, need to survive the duration
    if degen['duration'] == 'sustained':
        survivable = time_to_death > 60  # Need to tank for 1+ minute
    else:  # burst
        survivable = time_to_death > 10  # Need to tank for 10+ seconds
    
    return {
        'survivable': survivable,
        'indefinite': False,
        'time_to_death': time_to_death,
        'net_dps': net_dps,
        'mitigated_dps': mitigated_dps,
        'recovery': recovery
    }

def environmental_damage_score(build):
    """
    Score build's ability to handle unavoidable environmental damage
    
    This is where recovery and resistances matter MOST.
    Offense doesn't help - you can't kill the ground!
    """
    # Test against common degens
    burning = can_survive_degen(build, 'burning_ground')
    caustic = can_survive_degen(build, 'caustic_ground')
    sirus = can_survive_degen(build, 'sirus_storm')
    
    # Recovery ratio (how much of degen can we outheal?)
    recovery = recovery_per_second(build)
    
    # Score based on what we can survive
    score = 0
    
    if burning['survivable']:
        score += 0.2  # Basic requirement
    if caustic['survivable']:
        score += 0.3  # Chaos res is hard to cap
    if sirus['survivable']:
        score += 0.5  # Endgame content
    
    # Bonus for high recovery (can outheal more damage)
    recovery_score = normalize(recovery, 10000)  # 10k/sec is excellent
    score += 0.3 * recovery_score
    
    return score
```

## Multi-Objective Reward Function

### Approach 1: Weighted Sum (Simple)
```python
def reward_weighted(build):
    """
    Simple weighted combination
    Good starting point, but assumes linear tradeoffs
    """
    # Normalize each metric to [0, 1] range
    dps_score = normalize(build.stats.TotalDPS, max_dps=10_000_000)
    max_hit_score = normalize(max_hit_taken(build), max_hit=100_000)
    ehp_score = normalize(effective_hp(build), max_ehp=1_000_000)
    recovery_score = normalize(recovery_per_second(build), max_recovery=10_000)
    
    # Weights (tunable)
    w_offense = 0.4
    w_max_hit = 0.2  # Boss slams
    w_ehp = 0.2      # Sustained damage
    w_recovery = 0.2  # Sustain
    
    score = (
        w_offense * dps_score +
        w_max_hit * max_hit_score +
        w_ehp * ehp_score +
        w_recovery * recovery_score
    )
    
    return score
```

### Approach 2: Pareto Optimization (Better)
```python
def reward_pareto(build):
    """
    Multi-objective: Find builds that aren't dominated
    A build dominates B if it's better in all metrics
    
    Returns a vector of objectives (not single score)
    """
    objectives = {
        'dps': build.stats.TotalDPS,
        'max_hit_phys': max_hit_taken(build, damage_type='physical'),
        'max_hit_ele': max_hit_taken(build, damage_type='elemental'),
        'ehp': effective_hp(build),
        'recovery': recovery_per_second(build),
        'ttk_mapping': time_to_kill(build, pattern='small_rapid'),
        'ttk_boss': time_to_kill(build, pattern='medium_steady'),
    }
    
    return objectives
```

### Approach 3: Scenario-Based (Most Realistic)
```python
def reward_scenario(build, scenario='mapper'):
    """
    Different reward functions for different playstyles
    
    KEY PRINCIPLE: Offense and defense are interconnected!
    Fast kills = less time taking damage = effective defense
    Slow kills = more time taking damage = need more defense
    
    Scenarios:
    - 'mapper': Fast clear, movement, kill trash instantly
    - 'bosser': High single target, survive slams, sustain long fights
    - 'balanced': Mix of both
    - 'hardcore': Safety first, acceptable damage
    - 'speed_farmer': Glass cannon, absolute maximum clear speed
    """
    
    # Calculate all metrics
    dps = build.stats.TotalDPS
    ttk_trash = time_to_kill(build, 'trash')
    ttk_boss = time_to_kill(build, 'endgame_boss')
    clear_speed = clear_speed_score(build)
    max_hit = max_hit_taken(build)
    ehp = effective_hp(build)
    recovery = recovery_per_second(build)
    
    # Calculate damage taken while killing (offense as defense!)
    incoming_trash = damage_taken_while_killing(build, 'trash', enemy_dps=5000)
    incoming_boss = damage_taken_while_killing(build, 'endgame_boss', enemy_dps=15000)
    
    # Calculate environmental damage survival
    env_score = environmental_damage_score(build)
    
    if scenario == 'mapper':
        # Prioritize clear speed and movement
        # Kill trash SO FAST they can't hurt you
        score = (
            0.30 * normalize(clear_speed, 100) +          # Clear speed is king
            0.20 * normalize(dps, 5_000_000) +            # Raw DPS
            0.20 * (1 - normalize(ttk_trash, 1.0)) +      # Kill trash in <1 sec (INVERTED)
            0.15 * normalize(max_hit, 20_000) +           # Survive occasional hits
            0.10 * env_score +                            # Handle ground effects
            0.05 * normalize(build.stats.MovementSpeed, 200)  # Zoom zoom
        )
        
        # Penalty if you take too much damage while killing packs
        if incoming_trash > ehp * 0.5:
            score *= 0.5  # Bad! Taking too much damage
    
    elif scenario == 'bosser':
        # Prioritize single target DPS and survivability for long fights
        # Environmental damage is CRITICAL for bosses (degens, storms, etc.)
        score = (
            0.25 * normalize(dps, 10_000_000) +           # High single target
            0.20 * normalize(max_hit, 50_000) +           # Survive boss slams
            0.20 * normalize(recovery, 5000) +            # Sustain long fights
            0.15 * env_score +                            # CRITICAL: Sirus storms, Maven degen, etc.
            0.12 * (1 - normalize(ttk_boss, 30)) +        # Kill endgame bosses reasonably fast (INVERTED)
            0.08 * normalize(ehp, 150_000)                # General tankiness
        )
        
        # Penalty if boss fight takes too long (net damage > EHP)
        net_boss_damage = incoming_boss - (recovery * ttk_boss)
        if net_boss_damage > ehp:
            score *= 0.3  # Can't survive the fight!
    
    elif scenario == 'speed_farmer':
        # Glass cannon - absolute maximum clear speed
        # Kill everything before it can react
        score = (
            0.50 * normalize(clear_speed, 150) +          # ZOOM ZOOM
            0.30 * normalize(dps, 10_000_000) +           # Overkill DPS
            0.15 * (1 - normalize(ttk_trash, 0.5)) +      # Kill trash instantly (INVERTED)
            0.05 * normalize(max_hit, 10_000)             # Just enough to not get one-shot
        )
    
    elif# MUST handle all environmental damage (one mistake = RIP character)
        score = (
            0.25 * normalize(max_hit, 80_000) +           # NEVER get one-shot
            0.20 * normalize(ehp, 200_000) +              # Very tanky
            0.20 * normalize(recovery, 5000) +            # Sustain forever
            0.20 * env_score +                            # MUST survive all degens (hardcore = permadeath!)
            0.10 * normalize(dps, 3_000_000) +            # Still need acceptable damage
            0.05 * (1 - normalize(ttk_boss, 60))          # Don't timeout on bosses (INVERTED)
        )
        
        # Hard requirement: must be able to kill bosses without dying
        net_boss_damage = incoming_boss - (recovery * ttk_boss)
        if net_boss_damage > ehp * 0.8:
            score *= 0.1  # Too risky for hardcore!
        
        # Hard requirement: must handle common degens
        if not can_survive_degen(build, 'burning_ground')['survivable']:
            score *= 0.2  # Too dangerousy * ttk_boss)
        if net_boss_damage > ehp * 0.8:
            score *= 0.1  # Too risky for hardcore!
    
    else:  # balanced
        # Even distribution of offense and defense
        score = (
            0.25 * normalize(dps, 5_000_000) +
            0.20 * normalize(clear_speed, 80) +
            0.20 * normalize(max_hit, 30_000) +
            0.20 * normalize(ehp, 100_000) +
            0.15 * normalize(recovery, 3000)
        )
    
    return score
```

## Implementation in Neural Network Training

### Data Collection with Multiple Objectives
```python
def collect_training_data(build_codes, scenarios=['mapper', 'bosser', 'balanced']):
    """
    Collect features and multiple target values
    Include BOTH offensive and defensive metrics
    """
    dataset = []
    
    for code in build_codes:
        build = parse_build(code)
        
        # Extract features (passive tree + gear)
        features = extract_features(build)
        
        # Calculate all objectives (OFFENSIVE + DEFENSIVE)
        targets = {
            # Offensive metrics
            'dps': build.stats.TotalDPS,
            'ttk_trash': time_to_kill(build, 'trash'),
            'ttk_boss': time_to_kill(build, 'endgame_boss'),
            'clear_speed': clear_speed_score(build),
            
            # Defensive metrics
            'max_hit': max_hit_taken(build),
            'ehp': effective_hp(build),
            'recovery': recovery_per_second(build),
            
            # Environmental damage (unavoidable)
            'env_damage_score': environmental_damage_score(build),
            'burning_ground_survive': can_survive_degen(build, 'burning_ground')['survivable'],
            'sirus_storm_survive': can_survive_degen(build, 'sirus_storm')['survivable'],
            
            # Offensive-as-defense metrics
            'damage_taken_vs_trash': damage_taken_while_killing(build, 'trash'),
            'damage_taken_vs_boss': damage_taken_while_killing(build, 'endgame_boss'),
            'net_boss_damage': damage_taken_while_killing(build, 'endgame_boss') - 
                             (recovery_per_second(build) * time_to_kill(build, 'endgame_boss')),
        }
        
        # Scenario scores
        for scenario in scenarios:
            targets[f'score_{scenario}'] = reward_scenario(build, scenario)
        
        dataset.append({
            'features': features,
            'targets': targets,
            'build_code': code
        })
    
    return dataset
```

### Multi-Task Neural Network
```python
class MultiObjectiveBuildNet(nn.Module):
    """
    Predict multiple objectives simultaneously
    Shares features between tasks
    Learns that offense and defense are interconnected
    """
    def __init__(self, feature_dim):
        super().__init__()
        
        # Shared feature extraction
        self.shared = nn.Sequential(
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU()
        )
        
        # Offensive task heads
        self.head_dps = nn.Linear(256, 1)
        self.head_ttk_trash = nn.Linear(256, 1)
        self.head_ttk_boss = nn.Linear(256, 1)
        self.head_clear_speed = nn.Linear(256,
        self.head_env_damage = nn.Linear(256, 1)  # Environmental damage survival 1)
        
        # Defensive task heads
        self.head_max_hit = nn.Linear(256, 1)
        self.head_ehp = nn.Linear(256, 1)
        self.head_recovery = nn.Linear(256, 1)
        
        # Scenario heads (learned tradeoffs)
        self.head_mapper = nn.Linear(256, 1)
        self.head_bosser = nn.Linear(256, 1)
        self.head_balanced = nn.Linear(256, 1)
        self.head_hardcore = nn.Linear(256, 1)
        self.head_speed_farmer = nn.Linear(256, 1)
    
    def forward(self, x):
        shared_features = self.shared(x)
        
        return {
            # Offensive predictions
            'dps': self.head_dps(shared_features),
            'ttk_trash': self.head_ttk_trash(shared_features),
            'ttk_boss': self.head_ttk_boss(shared_features),
            'clear_speed': self.head_clear_speed(shared_features),
            
            # Defensive predictions
            'max_hit': self.head_max_hit(shared_features),
            'ehp': self.head_ehp(shared_features),
            'env_damage': self.head_env_damage(shared_features),
            'recovery': self.head_recovery(shared_features),
            
            # Scenario predictions
            'mapper': self.head_mapper(shared_features),
            'bosser': self.head_bosser(shared_features),
            'balanced': self.head_balanced(shared_features),
            'hardcore': self.head_hardcore(shared_features),
            'speed_farmer': self.head_speed_farmer(shared_features),
        }
```

### Training with Multiple Losses
```python
def train_multi_objective(model, data_loader, optimizer):
    """
    Train to predict all objectives simultaneously
    Weight losses by importance - offense matters for defense!
    """
    model.train()
    
    for batch in data_loader:
        features = batch['features']
        targets = batch['targets']
        
        # Forward pass
        predictions = model(features)
        
        # Offensive losses
        loss_dps = F.mse_loss(predictions['dps'], targets['dps'])
        loss_ttk_trash = F.mse_loss(predictions['ttk_trash'], targets['ttk_trash'])
        loss_ttk_boss = F.mse_loss(predictions['ttk_boss'], targets['ttk_boss'])
        loss_clear = F.mse_loss(predictions['clear_speed'], targets['clear_speed'])
        
        # Defensive losses
        loss_max_hit = F.mse_loss(predictions['max_hit'], targets['max_hit'])
        loss_ehp = F.mse_loss(predictions['ehp'], targets['ehp'])
        loss_recovery = F.mse_loss(predictions['recovery'], targets['recovery'])
        
        # Scenario losses
        loss_mapper = F.mse_loss(predictions['mapper'], targets['score_mapper'])
        loss_bosser = F.mse_loss(predictions['bosser'], targets['score_bosser'])
        loss_balanced = F.mse_loss(predictions['balanced'], targets['score_balanced'])
        
        # Combined loss (adjust weights based on importance)
        # Higher weights on what matters most
        total_loss = (
            # Offensive (critical for survival via fast kills)
            1.5 * loss_dps +              # High DPS = fast kills = less incoming damage
            2.0 * loss_ttk_trash +        # TTK is THE key metric
            1.5 * loss_ttk_boss +
            1.0 * loss_closses
            loss_max_hit = F.mse_loss(predictions['max_hit'], batch['target_max_hit'])
            loss_ehp = F.mse_loss(predictions['ehp'], batch['target_ehp'])
            loss_recovery = F.mse_loss(predictions['recovery'], batch['target_recovery'])
            loss_env = F.mse_loss(predictions['env_damage'], batch['target_env_damage_score'])
            
            # Defensive (critical for not dying)
            2.5 * loss_max_hit +          # One-shots are #1 killer
            1.5 * loss_ehp +
            1.5 * loss_recovery +         # Recovery is CRITICAL for degens
            1.8 * loss_env +              # Environmental damage kills many builds         # One-shots are #1 killer
            1.5 * loss_ehp +
            1.2 * loss_recovery +
            
            # Scenarios (user-facing predictions)
            1.0 * loss_mapper +
            1.0 * loss_bosser +
            1.0 * loss_balanced
        )
        
        # Backprop
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()
```

## Genetic Algorithm with User-Selected Objective

```python
def genetic_algorithm(model, initial_build, objective='balanced', generations=100):
    """
    Optimize for specific objective chosen by user
    """
    population = initialize_population(initial_build)
    
    for gen in range(generations):
        scores = []
        for genome in population:
            # Predict all objectives
            features = encode_genome(genome)
            predictions = model(features)
            
            # Use selected objective for fitness
            fitness = predictions[objective].item()
            scores.append((fitness, genome))
        
        # Evolution continues...
        population = evolve(scores)
    
    return best_genome
```

## UI Integration: Let User Choose

```lua
-- In GenerateBestNodesPopup, add objective selection
local objectives = {
    "Balanced (General)",
    "Mapper (Clear Speed)",
    "Bosser (Single Target)",
    "Hardcore (Survival)",
    "Custom..."
}

controls.objectiveSelect = new("DropDownControl", {...}, objectives, function(index, value)
    self.optimizerObjective = value
end)
```

## Key Insights

1. **No single "best" reward**: Different content requires different builds
2. **Scenario-based is most practical**: Let users pick their playstyle
3. **Multi-task learning**: Train one model for all objectives, switch at inference
4. **Defensive complexity**: PoE's layered defenses require multiple metrics
5. **Recovery matters**: High EHP is worthless without sustain
6. **OFFENSE IS DEFENSE**: Fast kills = less time taking damage = fewer deaths
7. **Time to kill is the key offensive metric**: Directly determines incoming damage
8. **Hit pattern matters**: Same DPS with different hit rates = different effectiveness
9. **Environmental damage tests recovery**: Some damage is unavoidable - you must outheal it
10. **Degens are capped**: Even "several life pools per second" is limited by game balance (~5-20k DPS)

## Types of Damage and Counter-Strategies

```python
def damage_type_analysis():
    """
    PoE has three fundamentally different damage types requiring different defenses
    """
    
    damage_types = {
        'avoidable_by_killing': {
            'examples': ['Enemy attacks', 'Enemy spells', 'Boss abilities'],
            'counter': 'High DPS - kill them before they hurt you',
            'metrics': ['DPS', 'Time to Kill', 'Clear Speed'],
            'importance': 0.40
        },
        
        'avoidable_by_tanking': {
            'examples': ['Boss slams', 'One-shot mechanics', 'Big hits'],
            'counter': 'High EHP + Max Hit - survive the hit',
            'metrics': ['Max Hit Taken', 'EHP', 'Mitigation'],
            'importance': 0.35
        },
        
        'unavoidable_environmental': {
            'examples': [
                'Burning ground (5k DPS)',
                'Caustic ground (8k DPS)',
                'Sirus storms (15k DPS)',
                'Maven memory game (10k DPS)',
                'Shaper degen (20k DPS burst)'
            ],
            'counter': 'High recovery - outheal the degen',
            'metrics': ['Recovery per Second', 'Resistances', 'Life/ES Pool'],
            'importance': 0.25,
            'note': 'Even though degens SEEM like "several pools per second", they are capped by game design. A 6k life build facing 10k DPS degen looks like "1.67 pools per second" but the actual DPS is limited to ~10k, not infinite.'
        }
    }
    
    return damage_types
```

## Offense as Defense: Concrete Examples

```python
def compare_builds_example():
    """
    Demonstrate why offense matters for defense
    """
    # Build A: Glass cannon
    build_a = {
        'dps': 10_000_000,
        'max_hit': 15_000,
        'ehp': 50_000,
        'recovery': 1000
    }
    
    # Build B: Tank
    build_b = {
        'dps': 2_000_000,
        'max_hit': 50_000,
        'ehp': 200_000,
        'recovery': 5000
    }
    
    # Scenario 1: Mapping (trash mobs, 50k HP each, 5k DPS)
    print("=== MAPPING ===")
    ttk_a_trash = 50_000 / build_a['dps']  # 0.005 sec
    ttk_b_trash = 50_000 / build_b['dps']  # 0.025 sec
    
    damage_a_trash = 5000 * ttk_a_trash  # 25 damage taken
    damage_b_trash = 5000 * ttk_b_trash  # 125 damage taken
    
    print(f"Build A: Kills in {ttk_a_trash:.3f}s, takes {damage_a_trash:.0f} damage → SURVIVES EASILY")
    print(f"Build B: Kills in {ttk_b_trash:.3f}s, takes {damage_b_trash:.0f} damage → SURVIVES EASILY")
    print("Winner: Build A (5x faster, less risk exposure)")
    
    # Scenario 2: Boss fight (50M HP, 15k DPS)
    print("\n=== BOSS FIGHT ===")
    ttk_a_boss = 50_000_000 / build_a['dps']  # 5 seconds
    ttk_b_boss = 50_000_000 / build_b['dps']  # 25 seconds
    
    damage_a_boss = 15000 * ttk_a_boss - (build_a['recovery'] * ttk_a_boss)  # 70k net damage
    damage_b_boss = 15000 * ttk_b_boss - (build_b['recovery'] * ttk_b_boss)  # 250k net damage
    
    print(f"Build A: Kills in {ttk_a_boss:.0f}s, net damage {damage_a_boss:.0f} → DEAD (exceeds EHP)")
    print(f"Build B: Kills in {ttk_b_boss:.0f}s, net damage {damage_b_boss:.0f} → SURVIVES (within EHP)")
    print("Winner: Build B (can sustain the fight)")
    
    # Scenario 3: Environmental degen (Sirus storm, 15k DPS, can't avoid)
    print("\n=== SIRUS STORM (15k DPS degen) ===")
    net_degen_a = 15000 - build_a['recovery']  # 14k net DPS
    net_degen_b = 15000 - build_b['recovery']  # 10k net DPS
    
    survive_time_a = build_a['ehp'] / net_degen_a  # ~3.5 seconds
    survive_time_b = build_b['ehp'] / net_degen_b  # ~20 seconds
    
    print(f"Build A: Net degen {net_degen_a:.0f} DPS, dies in {survive_time_a:.1f}s → DEAD")
    print(f"Build B: Net degen {net_degen_b:.0f} DPS, survives {survive_time_b:.1f}s → CAN SURVIVE")
    print("Winner: Build B (recovery + EHP lets you tank degens)")
    print("Note: Offense doesn't help here - you can't kill the ground!")
    
    # Conclusion
    print("\n=== CONCLUSION ===")
    print("Build A: Best for mapping (kills so fast you barely take damage)")
    print("Build B: Best for bossing (can sustain long fights + environmental damage)")
    print("Environmental damage: Recovery is CRITICAL - even 5k recovery matters vs 15k degen")
    print("NO SINGLE 'BEST' BUILD - depends on content!")

# Output:
# === MAPPING ===
# Build A: Kills in 0.005s, takes 25 damage → SURVIVES EASILY
# Build B: Kills in 0.025s, takes 125 damage → SURVIVES EASILY  
# Winner: Build A (5x faster, less risk exposure)
#
# === BOSS FIGHT ===
# Build A: Kills in 5s, net damage 70000 → DEAD (exceeds EHP)
# Build B: Kills in 25s, net damage 250000 → SURVIVES (within EHP)
# Winner: Build B (can sustain the fight)
#
# === SIRUS STORM (15k DPS degen) ===
# Build A: Net degen 14000 DPS, dies in 3.5s → DEAD
# Build B: Net degen 10000 DPS, survives 20.0s → CAN SURVIVE
# Winner: Build B (recovery + EHP lets you tank degens)
# Note: Offense doesn't help here - you can't kill the ground!
#
# === CONCLUSION ===
# Build A: Best for mapping (kills so fast you barely take damage)
# Build B: Best for bossing (can sustain long fights + environmental damage)
# Environmental damage: Recovery is CRITICAL - even 5k recovery matters vs 15k degen
# NO SINGLE 'BEST' BUILD - depends on content!
```

This approach lets the NN learn the complex tradeoffs between offense and defense, then users select their priority at optimization time!

## Advanced: Adversarial/Competitive Training

### Two-Network Competition Approach

Instead of training a single network, use **two competing networks** that push each other to improve:

```python
class AdversarialBuildOptimizer:
    """
    Two networks compete against each other:
    
    Network 1 (Builder): Generates optimized builds
    Network 2 (Killer): Generates enemy/boss strategies to counter those builds
    
    They train in alternating cycles, forcing each other to improve.
    """
    
    def __init__(self):
        # Network 1: Build optimizer (tries to create strong builds)
        self.builder_net = MultiObjectiveBuildNet(feature_dim=1500)
        
        # Network 2: Enemy generator (tries to create scenarios that kill builds)
        self.killer_net = EnemyStrategyNet(input_dim=1500)
    
    def train_adversarial(self, initial_builds, epochs=1000):
        """
        Adversarial training loop:
        1. Builder creates optimized builds
        2. Killer creates enemy strategies to defeat those builds
        3. Builder adapts to survive killer's strategies
        4. Repeat until convergence
        """
        
        for epoch in range(epochs):
            # Phase 1: Builder generates builds
            builds = self.builder_net.generate_builds(initial_builds)
            
            # Phase 2: Killer analyzes builds and creates counter-strategies
            enemy_strategies = self.killer_net.generate_counters(builds)
            
            # Phase 3: Evaluate builds against enemy strategies
            survival_scores = []
            for build, strategy in zip(builds, enemy_strategies):
                score = evaluate_survival(build, strategy)
                survival_scores.append(score)
            
            # Phase 4: Update networks
            # Builder is rewarded for surviving killer's strategies
            builder_loss = -torch.mean(survival_scores)  # Maximize survival
            builder_loss.backward()
            self.builder_optimizer.step()
            
            # Killer is rewarded for defeating builder's builds
            killer_loss = torch.mean(survival_scores)  # Minimize builder survival
            killer_loss.backward()
            self.killer_optimizer.step()
            
            if epoch % 100 == 0:
                print(f"Epoch {epoch}: Avg Survival = {torch.mean(survival_scores):.3f}")


class PoeDBEnemyDatabase:
    """
    SIMPLIFIED: Use real PoE data instead of generating synthetic enemies
    
    Scrape/download enemy data from poedb.tw or wiki:
    - Enemy names, HP, damage types
    - Boss mechanics, hit patterns
    - Environmental hazards from maps
    
    This is MUCH simpler than training a killer network!
    """
    
    def __init__(self):
        # Load real enemy data (scraped from poedb.tw)
        self.enemy_database = self.load_poedb_data()
    
    def load_poedb_data(self):
        """
        Download enemy data from poedb.tw/us/
        
        Example enemy entries:
        {
            'Hillock': {'hp': 1200, 'damage': 500, 'type': 'physical', 'attacks_per_sec': 1.2},
            'Sirus': {'hp': 70M, 'damage': 25000, 'type': 'mixed', 'attacks_per_sec': 0.8},
            'Maven': {'hp': 100M, 'damage': 30000, 'type': 'mixed', 'degen': 10000},
        }
        """
        return {
            # Act bosses (easy)
            'brutus': {'hp': 5000, 'phys_damage': 800, 'attacks_per_sec': 1.0, 'slam_damage': 3000},
            'merveil': {'hp': 8000, 'cold_damage': 1200, 'attacks_per_sec': 2.0},
            
            # Map bosses (medium)
            'hydra': {'hp': 15_000_000, 'phys_damage': 8000, 'attacks_per_sec': 1.5, 'fork_damage': 12000},
            'minotaur': {'hp': 18_000_000, 'phys_damage': 15000, 'attacks_per_sec': 0.8, 'burrow_damage': 25000},
            
            # Endgame bosses (hard)
            'sirus': {
                'hp': 70_000_000,
                'phys_damage': 12000,
                'attacks_per_sec': 0.8,
                'die_beam': 40000,  # One-shot mechanic
                'degen_storm': 15000  # Per second
            },
            'maven': {
                'hp': 100_000_000,
                'mixed_damage': 18000,
                'attacks_per_sec': 1.0,
                'memory_game_degen': 10000,
                'orb_cascade': 50000  # One-shot if you get hit by all
            },
            'uber_elder': {
                'hp': 80_000_000,
                'cold_damage': 10000,
                'attacks_per_sec': 1.2,
                'expanding_nova': 30000,
                'degen_pool': 8000
            },
            
            # Map environments
            'burning_ground': {'fire_dps': 5000, 'duration': 'sustained'},
            'shocked_ground': {'lightning_dps': 6000, 'duration': 'sustained'},
            'caustic_ground': {'chaos_dps': 8000, 'duration': 'sustained'},
            
            # Common packs
            'white_mob': {'hp': 50000, 'damage': 1000, 'attacks_per_sec': 1.5, 'pack_size': 10},
            'blue_mob': {'hp': 200000, 'damage': 3000, 'attacks_per_sec': 1.5, 'pack_size': 3},
            'rare_mob': {'hp': 500000, 'damage': 5000, 'attacks_per_sec': 1.2, 'pack_size': 1},
        }
    
    def get_challenging_encounters(self, build, num_tests=10):
        """
        SIMPLIFIED: Just test build against ALL real enemies
        No need to "learn" - use actual game data!
        
        Return the hardest encounters for this build
        """
        results = []
        
        for enemy_name, enemy_data in self.enemy_database.items():
            survival = self.test_encounter(build, enemy_name, enemy_data)
            results.append({
                'enemy': enemy_name,
                'survival_score': survival,
                'data': enemy_data
            })
        
        # Sort by difficulty (lowest survival = hardest)
        results.sort(key=lambda x: x['survival_score'])
        
        return results[:num_tests]  # Return hardest encounters
    
    def test_encounter(self, build, enemy_name, enemy_data):
        """
        Simulate build vs specific enemy from poedb
        """
        # One-shot check
        if 'slam_damage' in enemy_data:
            max_hit = max_hit_taken(build, 'physical')
            if enemy_data['slam_damage'] > max_hit:
                return 0.0  # One-shot = dead
        
        if 'die_beam' in enemy_data:
            max_hit = max_hit_taken(build, 'physical')
            if enemy_data['die_beam'] > max_hit:
                return 0.0
        
        # Sustained damage check
        if 'hp' in enemy_data:
            ttk = enemy_data['hp'] / build.stats.TotalDPS
            
            # Calculate incoming damage during fight
            dps = enemy_data.get('phys_damage', enemy_data.get('cold_damage', enemy_data.get('mixed_damage', 0)))
            aps = enemy_data.get('attacks_per_sec', 1.0)
            incoming = dps * aps * ttk
            
            # Add degen if present
            if 'degen_storm' in enemy_data:
                incoming += enemy_data['degen_storm'] * ttk
            
            # Can we survive?
            net_damage = incoming - (recovery_per_second(build) * ttk)
            ehp = effective_hp(build)
            
            survival = 1.0 - min(net_damage / ehp, 1.0)
            return max(survival, 0.0)
        
        # Degen-only encounters
        if enemy_name.endswith('_ground'):
            dps = enemy_data.get('fire_dps', enemy_data.get('chaos_dps', enemy_data.get('lightning_dps', 0)))
            recovery = recovery_per_second(build)
            
            if recovery >= dps:
                return 1.0  # Can outheal
            else:
                ehp = effective_hp(build)
                survive_time = ehp / (dps - recovery)
                return min(survive_time / 60, 1.0)  # Normalize to 60 seconds
        
        return 0.5  # Default


# SIMPLIFIED training loop
class SimplifiedAdversarialTraining:
    """
    STREAMLINED: No killer network needed!
    Just test against real enemies from poedb
    """
    
    def __init__(self):
        self.builder = MultiObjectiveBuildNet(1500)
        self.enemy_db = PoeDBEnemyDatabase()
    
    def train(self, initial_builds, epochs=1000):
        """
        Much simpler training loop:
        1. Builder generates builds
        2. Test against ALL real enemies from poedb
        3. Penalize builds that fail against common enemies
        4. Update builder
        """
        
        for epoch in range(epochs):
            # Generate builds
            builds = self.builder.generate_builds(initial_builds)
            
            # Test against real enemies (no neural network needed!)
            for build in builds:
                encounters = self.enemy_db.get_challenging_encounters(build)
                
                # Calculate loss
                survival_scores = [enc['survival_score'] for enc in encounters]
                avg_survival = np.mean(survival_scores)
                
                # Penalize builds that die to common enemies
                critical_fails = sum(1 for s in survival_scores if s < 0.1)
                
                loss = -avg_survival + critical_fails * 0.5
            
            # Update builder
            loss.backward()
            optimizer.step()
            
            if epoch % 100 == 0:
                print(f"Epoch {epoch}: Avg survival = {avg_survival:.3f}, Fails = {critical_fails}")
    
    def analyze_build_weaknesses(self, build):
        """
        User-facing: Show which enemies kill this build
        """
        encounters = self.enemy_db.get_challenging_encounters(build, num_tests=20)
        
        print("Build Weakness Analysis:")
        print("=" * 50)
        
        for enc in encounters[:5]:  # Show top 5 threats
            if enc['survival_score'] < 0.5:
                print(f"⚠️  {enc['enemy']}: {enc['survival_score']*100:.0f}% survival")
                
                # Suggest fixes
                if 'slam_damage' in enc['data'] or 'die_beam' in enc['data']:
                    print(f"   → Need {enc['data'].get('slam_damage', enc['data'].get('die_beam', 0))} max hit (currently {max_hit_taken(build):.0f})")
                
                if 'degen_storm' in enc['data'] or enc['enemy'].endswith('_ground'):
                    degen = enc['data'].get('degen_storm', enc['data'].get('fire_dps', enc['data'].get('chaos_dps', 0)))
                    recovery = recovery_per_second(build)
                    print(f"   → Need {degen} recovery/sec to outheal (currently {recovery:.0f})")
        
        return encounters


def evaluate_survival(build, enemy_strategy):
    """
    Simulate build vs enemy strategy
    Returns survival score (0 = dead, 1 = perfect survival)
    """
    
    # Apply enemy damage
    damage_type = enemy_strategy['damage_type']
    damage_amount = enemy_strategy['amount']
    damage_pattern = enemy_strategy['pattern']
    
    # Calculate build's defense against this specific strategy
    if damage_pattern == 'burst':
        # Can build survive a one-shot?
        max_hit = max_hit_taken(build, damage_type)
        survival_score = min(max_hit / damage_amount, 1.0)
        
    elif damage_pattern == 'sustained':
        # Can build outheal sustained damage?
        recovery = recovery_per_second(build)
        net_damage = damage_amount - recovery
        
        if net_damage <= 0:
            survival_score = 1.0  # Can outheal indefinitely
        else:
            ehp = effective_hp(build)
            time_to_death = ehp / net_damage
            survival_score = min(time_to_death / 60, 1.0)  # Normalize to 60 seconds
    
    elif damage_pattern == 'environmental':
        # Can build survive environmental effects?
        env_result = can_survive_degen(build, enemy_strategy['environmental'])
        survival_score = 1.0 if env_result['survivable'] else 0.0
    
    return survival_score
```

### Why Adversarial Training Works

```python
def adversarial_benefits():
    """
    Benefits of testing against real enemy data:
    
    1. REALISTIC: Test against actual game enemies, not synthetic data
    2. SIMPLE: No need to train a killer network - just use poedb
    3. COMPREHENSIVE: Test against ALL bosses, mobs, environments
    4. ACTIONABLE: Can tell users "you die to Sirus" not "you die to abstract scenario X"
    5. MAINTAINABLE: Update enemy data when game patches, no retraining needed
    """
    
    examples = {
        'scenario_1': {
            'builder_attempt': 'High DPS glass cannon (50k EHP, 10M DPS)',
            'poedb_test': 'Dies to Sirus die beam (40k damage)',
            'builder_adapts': 'Increase max hit to 45k',
            'outcome': 'Can now survive Sirus one-shots'
        },
        
        'scenario_2': {
            'builder_attempt': 'Super tank (200k EHP, -60% chaos res, 1M DPS)',
            'poedb_test': 'Dies to caustic ground (8k chaos DPS)',
            'builder_adapts': 'Cap chaos res at 75%',
            'outcome': 'Can now do caustic ground maps'
        },
        
        'scenario_3': {
            'builder_attempt': 'Balanced build (5M DPS, 100k EHP, 2k recovery)',
            'poedb_test': 'Takes 3 minutes to kill Maven, dies to memory game degen',
            'builder_adapts': 'Increase DPS to kill faster OR increase recovery',
            'outcome': 'Kills Maven before running out of HP'
        }
    }
    
    return examples
```

### Scraping poedb.tw Data

```python
import requests
from bs4 import BeautifulSoup
import json

class PoeDBScraper:
    """
    Scrape real enemy data from poedb.tw
    
    Example URLs:
    - https://poedb.tw/us/Sirus,_Awakener_of_Worlds
    - https://poedb.tw/us/The_Maven
    - https://poedb.tw/us/Kitava,_the_Destroyer
    """
    
    def scrape_boss_data(self, boss_name):
        """
        Get real stats from poedb
        """
        url = f"https://poedb.tw/us/{boss_name.replace(' ', '_')}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Parse boss stats (this will vary based on poedb structure)
        boss_data = {
            'name': boss_name,
            'hp': self.parse_hp(soup),
            'damage': self.parse_damage(soup),
            'mechanics': self.parse_mechanics(soup)
        }
        
        return boss_data
    
    def build_enemy_database(self):
        """
        Build comprehensive enemy database
        """
        bosses = [
            'Sirus, Awakener of Worlds',
            'The Maven',
            'The Shaper',
            'The Elder',
            'Uber Elder',
            'Hydra',
            'Minotaur',
            'Phoenix',
            'Chimera',
            'Kitava, the Destroyer'
        ]
        
        database = {}
        for boss in bosses:
            database[boss] = self.scrape_boss_data(boss)
        
        # Save to JSON
        with open('poedb_enemies.json', 'w') as f:
            json.dump(database, f, indent=2)
        
        return database
```

### Competitive Co-Evolution Strategy

```python
class CompetitiveBuildOptimizer:
    """
    Alternative approach: Multiple builder networks compete
    
    Instead of Builder vs Killer, have multiple builders compete
    for the "best" build according to different strategies.
    
    This creates diversity and prevents local optima.
    """
    
    def __init__(self, num_competitors=4):
        self.competitors = [
            MultiObjectiveBuildNet(feature_dim=1500) 
            for _ in range(num_competitors)
        ]
        
        self.strategies = ['mapper', 'bosser', 'balanced', 'hardcore']
    
    def train_competitive(self, initial_builds, epochs=1000):
        """
        Each network specializes in a different strategy
        They compete on shared benchmarks
        """
        
        for epoch in range(epochs):
            all_builds = []
            
            # Each competitor generates builds for their specialty
            for i, (net, strategy) in enumerate(zip(self.competitors, self.strategies)):
                builds = net.generate_builds(initial_builds, scenario=strategy)
                all_builds.extend(builds)
            
            # Evaluate ALL builds on ALL scenarios
            scores = self.evaluate_all_scenarios(all_builds)
            
            # Update networks based on relative performance
            for i, net in enumerate(self.competitors):
                strategy = self.strategies[i]
                
                # This network's builds
                my_builds = all_builds[i * len(initial_builds):(i+1) * len(initial_builds)]
                
                # Compare to other networks' builds on MY specialty
                my_scores = [scores[strategy][build] for build in my_builds]
                other_scores = [scores[strategy][build] for build in all_builds if build not in my_builds]
                
                # Reward for beating competitors
                loss = -torch.mean(torch.tensor(my_scores)) + torch.mean(torch.tensor(other_scores))
                
                # Train to improve
                loss.backward()
                self.optimizers[i].step()
            
            if epoch % 100 == 0:
                print(f"Epoch {epoch}: Competition scores:")
                for strategy in self.strategies:
                    avg_score = np.mean([scores[strategy][b] for b in all_builds])
                    print(f"  {strategy}: {avg_score:.3f}")
```

### Implementation Guide (Simplified)

```python
def implement_poedb_training():
    """
    SIMPLIFIED Step-by-step:
    
    1. Scrape/download enemy data from poedb.tw (one-time)
    2. Train base builder network on existing builds (warmup)
    3. Run training loop:
       - Builder generates builds
       - Test against ALL real enemies from database
       - Penalize builds that die to common content
       - Update builder
    4. Validate on hold-out encounters
    5. Save builder network
    
    Result:
    - Builder that creates builds viable for ALL content
    - No killer network needed - just real game data
    - Can show users exactly which bosses they'll struggle with
    """
    
    # Step 1: Build enemy database (once)
    scraper = PoeDBScraper()
    enemy_db = scraper.build_enemy_database()
    # Save to JSON for reuse
    
    # Step 2: Initialize builder
    builder = MultiObjectiveBuildNet(1500)
    
    # Step 3: Warmup training
    warmup_data = load_existing_builds()  # From poe.ninja
    pretrain(builder, warmup_data, epochs=200)
    
    # Step 4: Adversarial training (simplified)
    trainer = SimplifiedAdversarialTraining()
    trainer.train(warmup_data, epochs=1000)
    
    # Step 5: Validate
    test_build = create_test_build()
    weaknesses = trainer.analyze_build_weaknesses(test_build)
    print(f"Build fails against: {[w['enemy'] for w in weaknesses if w['survival_score'] < 0.3]}")
    
    return builder


def user_interface_example():
    """
    Show user which content their build can/cannot do
    """
    # User's current build
    user_build = load_user_build()
    
    # Test against real enemies
    db = PoeDBEnemyDatabase()
    encounters = db.get_challenging_encounters(user_build, num_tests=30)
    
    print("Content Viability:")
    print("=" * 60)
    
    # Group by difficulty tier
    can_do = [e for e in encounters if e['survival_score'] > 0.7]
    sketchy = [e for e in encounters if 0.3 < e['survival_score'] <= 0.7]
    cannot_do = [e for e in encounters if e['survival_score'] <= 0.3]
    
    print(f"✅ Can comfortably do ({len(can_do)}):")
    for e in can_do[:5]:
        print(f"   {e['enemy']}: {e['survival_score']*100:.0f}%")
    
    print(f"\n⚠️  Risky content ({len(sketchy)}):")
    for e in sketchy:
        print(f"   {e['enemy']}: {e['survival_score']*100:.0f}%")
    
    print(f"\n❌ Cannot do ({len(cannot_do)}):")
    for e in cannot_do:
        print(f"   {e['enemy']}: {e['survival_score']*100:.0f}%")
        # Show why they fail
        if 'slam_damage' in e['data']:
            print(f"      → One-shot by {e['data']['slam_damage']} damage slam")
        elif 'degen_storm' in e['data']:
            print(f"      → Cannot outheal {e['data']['degen_storm']} DPS degen")
```

### Key Advantages (Simplified Approach)

1. **Real Data**: Test against actual game enemies, not synthetic scenarios
2. **No Extra Network**: Don't need to train a killer network - just use poedb
3. **Actionable Feedback**: "Dies to Sirus" is clearer than "dies to abstract scenario 42"
4. **Easy Updates**: When game patches, just update the JSON file
5. **Comprehensive**: Test against 50+ real encounters automatically
6. **User-Friendly**: Show exactly which content they can/can't do

This is like having a test suite of ALL PoE bosses - much simpler than training a competitor!

## Multi-Component Resource Allocation Problem

### The Exponential Complexity Challenge

You're absolutely right - the builder side is EXPONENTIALLY harder than the killer side:

```python
class BuildComplexityAnalysis:
    """
    Why building is exponentially harder than testing:
    
    KILLER/TESTER (Simple):
    - Fixed enemy stats from poedb
    - ~50 different enemies to test against
    - No combinations needed
    - Complexity: O(n) where n = 50
    
    BUILDER (Extremely Complex):
    - Passive Tree: ~1500 nodes, ~100 point budget
    - Gear: 10 slots × hundreds of mods each
    - Gems: 24 sockets × 400+ gem choices
    - ALL THREE INTERACT MULTIPLICATIVELY:
      * Tree gives +100% increased phys → gear flat phys matters more
      * Gem converts phys to fire → need fire damage on tree/gear
      * Gear has +2 to gems → gem levels scale exponentially
      * Crit on tree → crit multi on gear → crit gems synergy
      
    Total search space: C(1500,100) × 10^20 × 400^24 ≈ 10^300
    """
    
    def estimate_search_space(self):
        from scipy.special import comb
        
        # Passive tree combinations
        tree_space = comb(1500, 100, exact=False)  # Choose 100 from 1500
        
        # Gear combinations (conservative estimate)
        gear_slots = 10
        meaningful_items_per_slot = 100  # After filtering by archetype
        gear_space = meaningful_items_per_slot ** gear_slots
        
        # Gem combinations
        num_sockets = 24  # Full set of gear
        gems_available = 400
        gem_space = gems_available ** num_sockets
        
        total = tree_space * gear_space * gem_space
        
        print(f"Passive tree alone: ~10^{int(np.log10(tree_space))}")
        print(f"Gear combinations: ~10^{int(np.log10(gear_space))}")
        print(f"Gem combinations: ~10^{int(np.log10(gem_space))}")
        print(f"TOTAL search space: ~10^{int(np.log10(total))}")
        print(f"\nFor reference:")
        print(f"Atoms in universe: ~10^80")
        print(f"CONCLUSION: Must use intelligent search, cannot brute force!")
```

### Solution: Multi-Component Neural Network

```python
class MultiComponentBuilder(nn.Module):
    """
    Handle tree + gear + gems with separate encoders/decoders
    Key: SHARED representation learns interactions between components
    """
    
    def __init__(self):
        super().__init__()
        
        # Component-specific encoders (capture component structure)
        self.tree_encoder = nn.Sequential(
            nn.Linear(1500, 256),  # Encode which nodes allocated
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.gear_encoder = nn.Sequential(
            nn.Linear(500, 256),  # Encode gear stats (aggregated)
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.gem_encoder = nn.Sequential(
            nn.Linear(100, 128),  # Encode gem configuration
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # SHARED encoder: learns interactions between components
        self.interaction_encoder = nn.Sequential(
            nn.Linear(256 + 256 + 128, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU()
        )
        
        # Component-specific decoders (generate improvements)
        self.tree_decoder = PassiveTreeDecoder(256, num_nodes=1500)
        self.gear_decoder = SimpleGearDecoder(256)  # Just 5 stats per slot!
        self.gem_decoder = GemSelectionDecoder(256, num_gems=400)
    
    def forward(self, current_build):
        """
        Given current build, suggest improvements to ALL components
        """
        # Encode each component
        tree_enc = self.tree_encoder(current_build['tree'])
        gear_enc = self.gear_encoder(current_build['gear'])
        gem_enc = self.gem_encoder(current_build['gems'])
        
        # Learn interactions in shared space
        combined = torch.cat([tree_enc, gear_enc, gem_enc], dim=-1)
        shared = self.interaction_encoder(combined)
        
        # Generate component-specific improvements
        tree_improvements = self.tree_decoder(shared, current_build['tree'])
        gear_values = self.gear_decoder(shared)  # Average stat values per slot
        gem_suggestions = self.gem_decoder(shared, current_build['gems'])
        
        return {
            'tree': tree_improvements,
            'gear': gear_priorities,
            'gems': gem_suggestions
        }


class PassiveTreeDecoder(nn.Module):
    """Suggest which passive nodes to allocate/deallocate"""
    
    def __init__(self, input_dim, num_nodes=1500):
        super().__init__()
        self.decoder = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, num_nodes),
            nn.Sigmoid()  # Probability of allocating each node
        )
    
    def forward(self, shared_features, current_tree):
        """Return probability distribution over nodes"""
        node_probs = self.decoder(shared_features)
        
        # Mask already-allocated nodes (encourage exploration)
        node_probs = node_probs * (1 - current_tree)
        
        return node_probs


class SimpleGearDecoder(nn.Module):
    """
    SIMPLIFIED: Each slot has only ~5 key stats
    Just output average values for those stats
    
    Much simpler than complex item generation!
    """
    
    def __init__(self, input_dim):
        super().__init__()
        
        # Define key stats per slot (only 5 per slot)
        self.slot_stats = {
            'weapon': ['added_phys_damage', 'crit_chance', 'attack_speed', 'elemental_damage', 'accuracy'],
            'body_armour': ['life', 'armour', 'evasion', 'energy_shield', 'resistances'],
            'helmet': ['life', 'resistances', 'accuracy', 'attributes', 'armour'],
            'gloves': ['life', 'resistances', 'attack_speed', 'accuracy', 'damage'],
            'boots': ['life', 'resistances', 'movement_speed', 'armour', 'evasion'],
            'amulet': ['life', 'damage', 'crit_multi', 'attributes', 'resistances'],
            'ring_1': ['life', 'resistances', 'damage', 'accuracy', 'attributes'],
            'ring_2': ['life', 'resistances', 'damage', 'accuracy', 'attributes'],
            'belt': ['life', 'resistances', 'armour', 'flask_charges', 'attributes'],
            'jewels': ['life', 'damage', 'crit_multi', 'attack_speed', 'resistances']
        }
        
        # Simple decoder per slot: output 5 values
        self.slot_decoders = nn.ModuleDict({
            slot: nn.Sequential(
                nn.Linear(input_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 5),  # Just 5 stats per slot!
                nn.Sigmoid()       # Normalize to 0-1, then scale to typical ranges
            )
            for slot in self.slot_stats.keys()
        })
    
    def forward(self, shared_features):
        """
        For each slot, output average stat values
        """
        gear_stats = {}
        
        for slot, decoder in self.slot_decoders.items():
            # Output 5 normalized values (0-1)
            normalized = decoder(shared_features)
            
            # Scale to typical ranges for each stat
            scaled = self.scale_to_typical_ranges(slot, normalized)
            
            gear_stats[slot] = scaled
        
        return gear_stats
    
    def scale_to_typical_ranges(self, slot, normalized):
        """
        Scale 0-1 outputs to typical stat ranges
        
        Example for ring:
        - life: 0-1 → 40-80 life
        - resistances: 0-1 → 30-48% per resist (total 90-144)
        - damage: 0-1 → 10-30 added damage
        """
        typical_ranges = {
            'weapon': [
                (20, 150),   # added_phys_damage (weapon dependent)
                (5, 8),      # crit_chance %
                (10, 20),    # attack_speed %
                (30, 60),    # elemental_damage %
                (300, 500)   # accuracy
            ],
            'body_armour': [
                (80, 120),   # life
                (800, 1500), # armour/evasion/ES (base dependent)
                (800, 1500), # secondary defense
                (0, 300),    # tertiary defense
                (40, 80)     # total resistances
            ],
            'helmet': [
                (60, 90),    # life
                (60, 90),    # total resistances
                (200, 400),  # accuracy
                (30, 50),    # attributes
                (200, 400)   # armour
            ],
            'gloves': [
                (50, 80),    # life
                (60, 90),    # total resistances
                (10, 16),    # attack_speed %
                (200, 400),  # accuracy
                (20, 40)     # added damage
            ],
            'boots': [
                (60, 90),    # life
                (60, 90),    # total resistances
                (25, 30),    # movement_speed %
                (100, 300),  # armour
                (100, 300)   # evasion
            ],
            'amulet': [
                (40, 70),    # life
                (30, 60),    # % increased damage
                (25, 40),    # crit_multi %
                (30, 50),    # attributes
                (30, 60)     # resistances
            ],
            'ring_1': [
                (40, 70),    # life
                (70, 105),   # total resistances (3 resists)
                (15, 30),    # added damage
                (200, 400),  # accuracy
                (30, 50)     # attributes
            ],
            'ring_2': [
                (40, 70),    # life
                (70, 105),   # total resistances
                (15, 30),    # added damage
                (200, 400),  # accuracy
                (30, 50)     # attributes
            ],
            'belt': [
                (60, 90),    # life
                (60, 90),    # total resistances
                (100, 300),  # armour
                (20, 30),    # flask charges gained %
                (30, 50)     # attributes
            ],
            'jewels': [
                (5, 7),      # % life
                (12, 16),    # % damage
                (15, 20),    # crit_multi %
                (6, 8),      # attack_speed %
                (0, 15)      # resistances
            ]
        }
        
        ranges = typical_ranges[slot]
        scaled = []
        
        for i, (min_val, max_val) in enumerate(ranges):
            # Scale normalized[i] from 0-1 to min_val-max_val
            value = min_val + normalized[i] * (max_val - min_val)
            scaled.append(value)
        
        return torch.stack(scaled)


class GemSelectionDecoder(nn.Module):
    """
    SIMPLIFIED: Gems follow predictable patterns
    
    Support gems are primarily about:
    1. Damage multipliers: 1.4x, 1.35x, 1.35x, 1.3x, 1.25x (per gem added)
    2. Simple attribute modifications: speed, AoE, defensive layers
    
    Much simpler than item generation!
    """
    
    def __init__(self, input_dim, num_sockets=6):
        super().__init__()
        
        # Most builds use 1 main skill + 5 supports (6-link)
        self.num_sockets = num_sockets
        
        # Support gem categories (not 400 individual gems!)
        self.support_categories = {
            # Damage multipliers (typical: 1.4x for first, 1.35x, 1.35x, 1.3x, 1.25x)
            'added_damage': {'multiplier': 1.40, 'priority': 1},      # Added Fire, Added Cold, etc.
            'more_damage': {'multiplier': 1.35, 'priority': 2},       # Elemental Focus, Controlled Destruction
            'crit_support': {'multiplier': 1.35, 'priority': 3},      # Increased Critical Strikes, Strikes
            'damage_conversion': {'multiplier': 1.30, 'priority': 4}, # Physical to Lightning, Cold to Fire
            'utility_damage': {'multiplier': 1.25, 'priority': 5},    # Concentrated Effect, Hypothermia
            
            # Speed/cast modifications
            'faster_attacks': {'speed_mult': 1.30, 'damage_mult': 0.95},
            'faster_casting': {'speed_mult': 1.30, 'damage_mult': 0.95},
            'multistrike': {'speed_mult': 1.60, 'damage_mult': 0.80, 'repeat': 3},
            'spell_echo': {'speed_mult': 1.50, 'damage_mult': 0.85, 'repeat': 2},
            
            # Area/range modifications
            'increased_aoe': {'aoe_mult': 1.40, 'damage_mult': 0.95},
            'awakened_aoe': {'aoe_mult': 1.50, 'damage_mult': 0.98},
            'concentrated_effect': {'aoe_mult': 0.70, 'damage_mult': 1.30},
            
            # Defensive modifications
            'fortify': {'defense': 'fortify', 'damage_mult': 1.15},
            'life_leech': {'defense': 'leech', 'damage_mult': 1.20},
            'blind': {'defense': 'blind', 'damage_mult': 1.10},
        }
        
        # Simple decoder: select support category for each socket (after main skill)
        self.decoder = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, (num_sockets - 1) * len(self.support_categories)),
            # -1 because first socket is main skill (user chooses)
        )
    
    def forward(self, shared_features):
        """
        For each support socket (5 in a 6-link), select which support category
        """
        logits = self.decoder(shared_features)
        logits = logits.view(self.num_sockets - 1, len(self.support_categories))
        
        # Softmax over support categories for each socket
        support_probs = torch.softmax(logits, dim=-1)
        
        return support_probs
    
    def calculate_final_multipliers(self, support_selection):
        """
        Calculate final damage/speed/AoE multipliers from selected supports
        
        Example:
        Socket 1 (main skill): Blade Vortex
        Socket 2: Added Fire (1.4x damage)
        Socket 3: Controlled Destruction (1.35x damage)
        Socket 4: Increased Critical Strikes (1.35x damage)
        Socket 5: Hypothermia (1.25x damage)
        Socket 6: Increased AoE (1.4x AoE, 0.95x damage)
        
        Total damage: 1.0 × 1.4 × 1.35 × 1.35 × 1.25 × 0.95 = 3.01x
        Total AoE: 1.4x
        """
        total_damage_mult = 1.0
        total_speed_mult = 1.0
        total_aoe_mult = 1.0
        
        for socket_probs in support_selection:
            # Get most likely support for this socket
            best_support_idx = torch.argmax(socket_probs)
            support_name = list(self.support_categories.keys())[best_support_idx]
            support = self.support_categories[support_name]
            
            # Apply multipliers
            if 'multiplier' in support:
                total_damage_mult *= support['multiplier']
            if 'damage_mult' in support:
                total_damage_mult *= support['damage_mult']
            if 'speed_mult' in support:
                total_speed_mult *= support['speed_mult']
            if 'aoe_mult' in support:
                total_aoe_mult *= support['aoe_mult']
        
        return {
            'damage_multiplier': total_damage_mult,
            'speed_multiplier': total_speed_mult,
            'aoe_multiplier': total_aoe_mult
        }


def example_gem_optimization():
    """
    Example: Neural network learns optimal support combination
    
    For a Blade Vortex build:
    """
    
    # Network learns to select supports based on build needs
    scenarios = {
        'mapper_build': {
            # Prioritize clear speed
            'supports': ['increased_aoe', 'faster_casting', 'added_damage', 'more_damage', 'utility_damage'],
            'total_damage': 1.0 * 1.40 * 1.30 * 1.35 * 0.95 = 2.32,
            'total_aoe': 1.40,
            'total_speed': 1.30,
            'reason': 'Large AoE + fast cast = clear packs quickly'
        },
        
        'bosser_build': {
            # Prioritize single target damage
            'supports': ['added_damage', 'more_damage', 'crit_support', 'damage_conversion', 'concentrated_effect'],
            'total_damage': 1.0 * 1.40 * 1.35 * 1.35 * 1.30 * 1.30 = 4.43,
            'total_aoe': 0.70,  # Smaller but doesn't matter for single target
            'total_speed': 1.0,
            'reason': 'Maximum damage multiplier for boss DPS'
        },
        
        'defensive_build': {
            # Balance damage with survivability
            'supports': ['added_damage', 'more_damage', 'fortify', 'life_leech', 'faster_casting'],
            'total_damage': 1.0 * 1.40 * 1.35 * 1.15 * 1.20 * 0.95 = 2.46,
            'total_speed': 1.30,
            'defenses': ['fortify', 'leech'],
            'reason': 'Good damage + defensive layers'
        }
    }
    
    return scenarios


def gem_encoding_simplified():
    """
    How to encode gems: Just track multipliers!
    
    Old approach (complex):
    - Encode each of 400 gems individually
    - Learn all their interactions
    - Try to predict optimal combinations
    
    New approach (simple):
    - Group gems by function (damage, speed, AoE, defense)
    - Output multipliers directly
    - Just follow the standard pattern: 1.4x, 1.35x, 1.35x, 1.3x, 1.25x
    
    Why this works:
    1. Most 6-links follow predictable patterns
    2. Damage supports follow diminishing returns (1.4 → 1.35 → 1.3 → 1.25)
    3. Utility supports trade damage for other benefits (speed, AoE, defense)
    4. Only ~10-15 support categories matter (not 400 individual gems)
    """
    
    # Instead of encoding 400 gems
    old_approach = torch.zeros(400)  # 0 or 1 for each gem
    
    # Just encode multipliers
    new_approach = {
        'damage_multiplier': 3.5,   # Product of all damage multipliers
        'speed_multiplier': 1.3,    # Speed increase
        'aoe_multiplier': 1.4,      # AoE increase
        'defensive_layers': ['fortify', 'leech']  # Which defenses active
    }
    
    # Much simpler: 3 floats + list instead of 400 dimensions!
    return new_approach


class AuraOptimizer:
    """
    SIMPLEST APPROACH: Enable all auras, remove ones that contribute least
    
    Auras are limited by mana reservation:
    - Most auras reserve 50% mana
    - Some reserve 25% or 35%
    - Reservation efficiency can lower these
    
    Typical builds run 3-4 auras
    """
    
    def __init__(self):
        self.aura_list = {
            # Offensive auras (50% reservation)
            'hatred': {'reservation': 0.50, 'damage_mult': 1.35, 'type': 'offensive'},
            'wrath': {'reservation': 0.50, 'damage_mult': 1.35, 'type': 'offensive'},
            'anger': {'reservation': 0.50, 'damage_mult': 1.35, 'type': 'offensive'},
            'zealotry': {'reservation': 0.50, 'damage_mult': 1.30, 'crit': 1.20, 'type': 'offensive'},
            'pride': {'reservation': 0.50, 'damage_mult': 1.40, 'type': 'offensive'},
            
            # Defensive auras (50% reservation)
            'determination': {'reservation': 0.50, 'armour_mult': 2.0, 'phys_reduction': 0.15, 'type': 'defensive'},
            'grace': {'reservation': 0.50, 'evasion_mult': 2.0, 'type': 'defensive'},
            'discipline': {'reservation': 0.35, 'es_flat': 300, 'es_regen': 1.5, 'type': 'defensive'},
            
            # Utility auras (25-35% reservation)
            'vitality': {'reservation': 0.35, 'life_regen': 2.0, 'type': 'utility'},
            'clarity': {'reservation': 0.35, 'mana_regen': 3.0, 'type': 'utility'},
            'precision': {'reservation': 0.35, 'accuracy': 2000, 'crit': 1.10, 'type': 'utility'},
            
            # Defensive utility (25% reservation)
            'defiance_banner': {'reservation': 0.10, 'armour': 1500, 'evasion': 1500, 'type': 'utility'},
            'dread_banner': {'reservation': 0.10, 'accuracy_mult': 1.15, 'impale': 0.20, 'type': 'utility'},
        }
    
    def optimize_auras(self, build_stats, max_reservation=1.0):
        """
        Simple greedy algorithm:
        1. Enable ALL auras
        2. Calculate contribution of each
        3. Remove lowest contributors until reservation fits
        
        Args:
            build_stats: Current build stats (damage, defense, etc.)
            max_reservation: Max reservation (1.0 = 100%, can be >1 with Prism Guardian)
        """
        
        # Step 1: Enable all auras and score each
        aura_scores = {}
        
        for aura_name, aura in self.aura_list.items():
            # Calculate combined offense + defense contribution
            offense_score = self._calculate_offense_contribution(aura, build_stats)
            defense_score = self._calculate_defense_contribution(aura, build_stats)
            
            # Combined score (weighted by user preference)
            total_score = offense_score + defense_score
            
            aura_scores[aura_name] = {
                'score': total_score,
                'offense': offense_score,
                'defense': defense_score,
                'reservation': aura['reservation']
            }
        
        # Step 2: Sort by score (highest first)
        sorted_auras = sorted(aura_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Step 3: Greedily add auras until reservation limit
        selected_auras = []
        total_reservation = 0.0
        
        for aura_name, aura_info in sorted_auras:
            new_reservation = total_reservation + aura_info['reservation']
            
            if new_reservation <= max_reservation:
                selected_auras.append(aura_name)
                total_reservation = new_reservation
        
        return {
            'selected_auras': selected_auras,
            'total_reservation': total_reservation,
            'scores': aura_scores
        }
    
    def _calculate_offense_contribution(self, aura, build_stats):
        """How much does this aura increase damage?"""
        score = 0.0
        
        # Direct damage multiplier
        if 'damage_mult' in aura:
            score += (aura['damage_mult'] - 1.0) * 1000  # e.g., 1.35x = 350 points
        
        # Crit multiplier
        if 'crit' in aura:
            crit_weight = build_stats.get('crit_chance', 0.0) / 100.0
            score += (aura['crit'] - 1.0) * 1000 * crit_weight
        
        # Accuracy (if attack build)
        if 'accuracy' in aura and build_stats.get('is_attack_build', False):
            score += aura['accuracy'] / 10  # 2000 accuracy = 200 points
        
        return score
    
    def _calculate_defense_contribution(self, aura, build_stats):
        """How much does this aura increase survivability?"""
        score = 0.0
        
        # Armour contribution
        if 'armour_mult' in aura:
            current_armour = build_stats.get('armour', 10000)
            added_armour = current_armour * (aura['armour_mult'] - 1.0)
            score += added_armour / 100  # 10k armour = 100 points
        
        if 'armour' in aura:
            score += aura['armour'] / 100
        
        # Evasion contribution
        if 'evasion_mult' in aura:
            current_evasion = build_stats.get('evasion', 10000)
            added_evasion = current_evasion * (aura['evasion_mult'] - 1.0)
            score += added_evasion / 100
        
        # Energy shield
        if 'es_flat' in aura:
            score += aura['es_flat'] / 10  # 300 ES = 30 points
        
        # Regen
        if 'life_regen' in aura:
            score += aura['life_regen'] * 50  # 2% regen = 100 points
        
        # Physical reduction
        if 'phys_reduction' in aura:
            score += aura['phys_reduction'] * 1000  # 15% = 150 points
        
        return score


def example_aura_optimization():
    """
    Example: Optimize auras for different build types
    """
    
    optimizer = AuraOptimizer()
    
    # Physical attack build
    phys_build = {
        'damage_type': 'physical',
        'is_attack_build': True,
        'armour': 20000,
        'evasion': 5000,
        'crit_chance': 60.0
    }
    
    result = optimizer.optimize_auras(phys_build, max_reservation=1.0)
    
    """
    Output example:
    {
        'selected_auras': ['pride', 'determination', 'precision', 'defiance_banner'],
        'total_reservation': 0.95,  # 50% + 50% + 35% + 10% = 145% (with efficiency: 95%)
        'scores': {
            'pride': {'score': 400, 'offense': 400, 'defense': 0, 'reservation': 0.50},
            'determination': {'score': 350, 'offense': 0, 'defense': 350, 'reservation': 0.50},
            'precision': {'score': 300, 'offense': 300, 'defense': 0, 'reservation': 0.35},
            'hatred': {'score': 200, 'offense': 200, 'defense': 0, 'reservation': 0.50},  # Not selected
            # ...
        }
    }
    
    Why these auras?
    1. Pride: 40% more damage (best for physical)
    2. Determination: Doubles armour (huge for phys mitigation)
    3. Precision: 2000 accuracy + crit (attack build needs accuracy)
    4. Defiance Banner: Cheap 10% reservation, adds armour/evasion
    
    Why NOT Hatred?
    - Only 35% more damage (worse than Pride's 40%)
    - Would push reservation over 100%
    - Precision + Banner give more combined value
    """
    
    return result


def integrate_auras_with_neural_network():
    """
    How to integrate aura optimization into ML model:
    
    APPROACH: Just run greedy algorithm after tree/gear/gems
    
    Why not train aura selection?
    1. Only ~12 auras to choose from (tiny search space)
    2. Greedy algorithm is near-optimal (O(n log n))
    3. Choice depends on build stats (dynamic based on tree/gear)
    4. Training would be overkill for such simple problem
    
    Implementation:
    """
    
    def optimize_full_build(tree_allocation, gear_stats, gem_setup):
        # 1. Apply tree, gear, gems
        build_stats = calculate_build_stats(tree_allocation, gear_stats, gem_setup)
        
        # 2. Run aura optimizer on final build
        aura_optimizer = AuraOptimizer()
        aura_result = aura_optimizer.optimize_auras(build_stats)
        
        # 3. Recalculate with auras enabled
        final_stats = apply_auras(build_stats, aura_result['selected_auras'])
        
        return {
            'tree': tree_allocation,
            'gear': gear_stats,
            'gems': gem_setup,
            'auras': aura_result['selected_auras'],
            'final_dps': final_stats['dps'],
            'final_ehp': final_stats['ehp']
        }
    
    """
    Neural network only needs to optimize tree + gear + gems
    Auras are deterministically solved afterwards
    
    Much simpler than trying to train aura selection!
    """


# ============================================================================
# PASSIVE TREE STRUCTURE & CLUSTERING
# ============================================================================

class PassiveTreeStructure:
    """
    CRITICAL INSIGHT: The passive tree is NOT random!
    
    Key observations that reduce complexity:
    1. Similar stats cluster together (damage near damage, life near life)
    2. Travel nodes provide minimal stats (just pathing)
    3. Notable nodes (named) have high impact
    4. Keystones are critical binary decisions
    5. Effective search space << 1500 nodes
    
    This structure can be exploited by the neural network!
    """
    
    def __init__(self):
        self.node_types = {
            'small': {
                'count': ~1200,
                'stats': 'Low (10 str, 3% damage, etc.)',
                'purpose': 'Pathing and small increments'
            },
            'notable': {
                'count': ~280,
                'stats': 'Medium-High (25% damage, 30 life, etc.)',
                'purpose': 'Main power nodes'
            },
            'keystone': {
                'count': ~20,
                'stats': 'Build-defining (enable/disable mechanics)',
                'purpose': 'Binary decisions (yes/no)'
            }
        }
        
        self.clusters = {
            'life': {
                'location': 'Marauder/Templar area (left side)',
                'nodes': ~150,
                'typical_path': 'Life wheel → Scion life rectangle',
                'stats': '+% life, +flat life, +life regen'
            },
            'damage_physical': {
                'location': 'Duelist/Marauder area (bottom-left)',
                'nodes': ~100,
                'stats': '+% physical damage, +% attack speed, impale'
            },
            'damage_elemental': {
                'location': 'Witch/Templar area (top)',
                'nodes': ~120,
                'stats': '+% elemental damage, +% penetration, +% cast speed'
            },
            'crit': {
                'location': 'Assassin/Shadow area (right)',
                'nodes': ~80,
                'stats': '+% crit chance, +% crit multi, power charges'
            },
            'energy_shield': {
                'location': 'Witch area (top-right)',
                'nodes': ~100,
                'stats': '+% ES, +flat ES, +ES recharge'
            },
            'evasion': {
                'location': 'Ranger area (bottom-right)',
                'nodes': ~80,
                'stats': '+% evasion, +% attack speed, +% movement speed'
            },
            'block': {
                'location': 'Duelist area (bottom)',
                'nodes': ~40,
                'stats': '+% block chance, +% attack damage'
            },
            'minion': {
                'location': 'Witch area (top-right)',
                'nodes': ~70,
                'stats': '+% minion damage, +% minion life, +minion count'
            }
        }
    
    def analyze_effective_search_space(self):
        """
        Why search space is smaller than it appears:
        
        APPARENT: 1500 nodes = 10^450 combinations
        ACTUAL: Much smaller due to clustering!
        """
        
        analysis = {
            'keystones': {
                'count': 20,
                'decision': 'Binary (allocate or not)',
                'combinations': 2**20,  # ~1 million
                'examples': ['Resolute Technique', 'Elemental Overload', 'Chaos Inoculation']
            },
            
            'notables': {
                'count': 280,
                'decision': 'Which clusters to path to',
                'effective_choices': 50,  # Most builds use 30-50 notables
                'combinations': 'C(280, 50) but clustered!'
            },
            
            'small_nodes': {
                'count': 1200,
                'decision': 'Mostly determined by notable pathing',
                'effective_choices': 'Auto-selected for efficient pathing',
                'combinations': 'Not independent! Follows shortest path'
            },
            
            'clusters': {
                'count': 8,  # Life, damage, crit, ES, evasion, block, minion, etc.
                'decision': 'Which 2-3 clusters to focus on',
                'combinations': 'C(8, 3) = 56',
                'examples': ['Life + Damage', 'ES + Crit', 'Life + Block']
            }
        }
        
        """
        REAL SEARCH SPACE:
        1. Choose 2-3 clusters (56 combinations)
        2. Choose 3-5 keystones (C(20, 4) = 4,845)
        3. Choose ~40 notables within clusters (mostly determined by step 1)
        4. Small nodes auto-path between notables
        
        Total: ~56 × 5k × path_variants ≈ 10^6 to 10^9
        
        Much more tractable than 10^450!
        """
        
        return analysis
    
    def exploit_clustering_in_neural_network(self):
        """
        How to design network to exploit tree structure:
        """
        
        approach = {
            'hierarchical_encoding': {
                'description': 'Encode tree at multiple levels',
                'level_1': 'Cluster selection (life/damage/crit/ES/evasion)',
                'level_2': 'Keystone selection (binary decisions)',
                'level_3': 'Notable selection within clusters',
                'level_4': 'Auto-compute efficient pathing'
            },
            
            'graph_neural_network': {
                'description': 'Treat tree as graph, nodes have neighbors',
                'benefit_1': 'Learns that nearby nodes have similar stats',
                'benefit_2': 'Learns efficient pathing automatically',
                'benefit_3': 'Understands cluster boundaries'
            },
            
            'attention_mechanism': {
                'description': 'Focus on high-impact nodes (notables/keystones)',
                'benefit': 'Small nodes get low attention (mostly auto-path)'
            },
            
            'cluster_embeddings': {
                'description': 'Pre-encode each cluster as a unit',
                'life_cluster': 'Embed "life wheel" as single concept',
                'damage_cluster': 'Embed "crit cluster" as single concept',
                'benefit': 'Network learns "allocate life cluster" not "allocate 50 individual nodes"'
            }
        }
        
        return approach


def example_tree_clustering():
    """
    Example: How clustering reduces complexity
    
    Typical build decision process:
    """
    
    # Instead of: "Which 100 of 1500 nodes?"
    complex_decision = {
        'nodes_to_allocate': [...],  # 100 node IDs
        'combinations': '10^450'
    }
    
    # Actually: "Which 2-3 clusters + which keystones?"
    simple_decision = {
        'step_1_clusters': ['life', 'crit'],  # 2 of 8 clusters
        'step_2_keystones': ['Pain Attunement'],  # 1 of 20
        'step_3_notables': [
            'Heart of the Warrior',  # Notable in life cluster
            'Constitution',           # Notable in life cluster
            'Assassination',          # Notable in crit cluster
            'Disemboweling',         # Notable in crit cluster
            # ... ~30-40 notables total
        ],
        'step_4_pathing': 'Auto-computed (shortest path through small nodes)',
        'combinations': 'C(8,2) × C(20,1) × path_options ≈ 10^6'
    }
    
    """
    Why this works:
    1. Clusters are geographically separated
    2. Can't efficiently allocate from 5+ different clusters (too much pathing)
    3. Most builds focus on 2-3 clusters (e.g., life + damage, or ES + crit)
    4. Within a cluster, take the best notables (greedy works well)
    5. Small nodes automatically follow shortest path
    
    Neural network can learn this hierarchy!
    """
    
    return simple_decision


def travel_node_penalty():
    """
    Travel nodes (small nodes with minimal stats) should be penalized
    
    Problem: If network treats all nodes equally, might waste points on travel
    
    Solution: Weighted node allocation
    """
    
    def calculate_node_priority(node, build_archetype):
        """
        Assign priority weight to each node type
        
        CRITICAL: Some nodes are WORSE than travel nodes!
        - Attack speed node for spell build = 0 value
        - Energy shield node for life build = 0 value  
        - Elemental damage node for physical build = 0 value
        - Crit nodes for non-crit build = 0 value
        
        These "dead" nodes should be weighted BELOW travel nodes!
        """
        
        # First check if node is completely useless for this build
        if is_dead_node(node, build_archetype):
            return 0.0  # ZERO value (worse than travel!)
        
        # Then check node type
        if node['type'] == 'keystone':
            if is_beneficial_keystone(node, build_archetype):
                return 10.0  # High priority (build-defining)
            else:
                return 0.0   # Some keystones ruin builds (e.g., Resolute Technique for crit)
        
        elif node['type'] == 'notable':
            relevance = calculate_stat_relevance(node, build_archetype)
            return 3.0 * relevance  # 0.0 to 3.0 based on relevance
        
        elif node['type'] == 'small' and is_high_stat_node(node):
            relevance = calculate_stat_relevance(node, build_archetype)
            return 1.5 * relevance  # 0.0 to 1.5
        
        elif node['type'] == 'small':
            # Pure travel nodes (10 str, 10 int, etc.)
            return 0.5   # Low but non-zero (at least gives attributes)
        
        else:
            return 0.1   # Very low (pure travel nodes)
    
    def is_dead_node(node, build_archetype):
        """
        Check if node provides NO benefit to this build
        
        Examples of dead nodes:
        """
        stats = node['stats']
        
        # Spell build: attack stats are worthless
        if build_archetype['damage_type'] == 'spell':
            if any(stat in stats for stat in ['attack_speed', 'attack_damage', 'weapon_damage']):
                if not has_spell_stats(stats):  # Pure attack node
                    return True
        
        # Attack build: spell stats are worthless
        if build_archetype['damage_type'] == 'attack':
            if any(stat in stats for stat in ['spell_damage', 'cast_speed', 'spell_crit']):
                if not has_attack_stats(stats):  # Pure spell node
                    return True
        
        # Life build: pure ES nodes are worthless
        if build_archetype['defense_type'] == 'life':
            if 'energy_shield' in stats and not any(k in stats for k in ['life', 'armour', 'evasion']):
                return True
        
        # ES build: pure life nodes are worthless (usually)
        if build_archetype['defense_type'] == 'energy_shield':
            if 'life' in stats and not any(k in stats for k in ['energy_shield', 'mana']):
                return True
        
        # Non-crit build: pure crit nodes are worthless
        if not build_archetype['uses_crit']:
            if any(stat in stats for stat in ['crit_chance', 'crit_multi']) and 'damage' not in stats:
                return True
        
        # Physical build: pure elemental nodes are worthless (if no conversion)
        if build_archetype['damage_element'] == 'physical' and not build_archetype['converts_damage']:
            if any(stat in stats for stat in ['fire_damage', 'cold_damage', 'lightning_damage']):
                if 'physical_damage' not in stats:
                    return True
        
        # Minion build: non-minion damage is worthless
        if build_archetype['is_minion_build']:
            if any(stat in stats for stat in ['damage', 'attack_speed', 'cast_speed']):
                if 'minion' not in str(stats):  # Doesn't affect minions
                    return True
        
        return False
    
    def calculate_stat_relevance(node, build_archetype):
        """
        Calculate 0.0 to 1.0 relevance score for node
        
        1.0 = Perfect match (life for life build, damage for your type)
        0.5 = Partially useful (generic damage, attributes)
        0.0 = Completely useless (dead stat)
        """
        stats = node['stats']
        relevance = 0.0
        stat_count = len(stats)
        
        for stat_name, stat_value in stats.items():
            stat_relevance = calculate_single_stat_relevance(
                stat_name, stat_value, build_archetype
            )
            relevance += stat_relevance
        
        # Average relevance across all stats
        return relevance / max(stat_count, 1)
    
    def calculate_single_stat_relevance(stat_name, stat_value, build):
        """
        Score individual stat 0.0 to 1.0
        
        CRITICAL: Must consider skill's base values and scaling vectors!
        
        Example: "+50% critical strike chance" node
        - Skill with 7% base crit: 7% → 10.5% = +50% effectiveness → score 1.0
        - Skill with 5% base crit: 5% → 7.5% = +50% effectiveness → score 0.7
        - Skill with 0% base crit: Can't crit at all → score 0.0
        
        The SAME NODE has different value depending on skill!
        """
        
        skill_scaling = build.get('skill_scaling_vectors', {})
        
        # Life/Defense stats
        if stat_name == 'life_percent':
            return 1.0 if build['defense_type'] == 'life' else 0.2
        
        if stat_name == 'energy_shield_percent':
            return 1.0 if build['defense_type'] == 'energy_shield' else 0.0
        
        if stat_name == 'armour_percent':
            return 1.0 if build['defense_layers'].get('armour') else 0.3
        
        if stat_name == 'evasion_percent':
            return 1.0 if build['defense_layers'].get('evasion') else 0.3
        
        # Damage stats - depends on damage type
        if stat_name == 'spell_damage':
            return 1.0 if build['damage_type'] == 'spell' else 0.0
        
        if stat_name == 'attack_damage':
            return 1.0 if build['damage_type'] == 'attack' else 0.0
        
        if stat_name == 'minion_damage':
            return 1.0 if build['is_minion_build'] else 0.0
        
        # Generic damage (usually useful)
        if stat_name in ['damage', 'elemental_damage', 'physical_damage']:
            return 0.8
        
        # Speed stats - SCALING DEPENDENT
        if stat_name == 'cast_speed':
            if build['damage_type'] != 'spell':
                return 0.0
            # Cast speed value depends on skill's base cast time
            base_cast_time = skill_scaling.get('base_cast_time', 0.8)
            if base_cast_time > 1.0:  # Slow skill (e.g., Flameblast 2.0s)
                return 1.0  # High value - speed helps a lot
            elif base_cast_time < 0.5:  # Fast skill (e.g., Blade Vortex 0.25s)
                return 0.6  # Lower value - already fast, diminishing returns
            else:
                return 0.8  # Medium speed skill
        
        if stat_name == 'attack_speed':
            if build['damage_type'] != 'attack':
                return 0.0
            base_attack_speed = skill_scaling.get('base_attack_speed', 1.2)
            # Similar logic to cast speed
            if base_attack_speed < 1.0:  # Slow weapon
                return 1.0
            elif base_attack_speed > 1.5:  # Fast weapon
                return 0.6
            else:
                return 0.8
        
        # Crit stats - HEAVILY SCALING DEPENDENT
        if stat_name == 'crit_chance':
            if not build['uses_crit']:
                return 0.0
            
            # Base crit chance determines scaling efficiency
            base_crit = skill_scaling.get('base_crit_chance', 5.0)
            
            if base_crit >= 6.5:  # High base crit (e.g., assassin skills, Ice Spear)
                return 1.0  # Excellent scaling
            elif base_crit >= 5.5:  # Medium crit (most spells)
                return 0.8  # Good scaling
            elif base_crit >= 5.0:  # Low-medium crit
                return 0.6  # OK scaling
            else:  # Very low crit (< 5%)
                return 0.3  # Poor scaling, hard to get high crit
        
        if stat_name == 'crit_multi':
            if not build['uses_crit']:
                return 0.0
            
            # Crit multi scales with crit chance (multiplicative)
            base_crit = skill_scaling.get('base_crit_chance', 5.0)
            current_crit_chance = build.get('current_crit_chance', base_crit)
            
            # Crit multi only valuable if you crit often
            if current_crit_chance >= 50:  # High crit
                return 1.0  # Excellent (critting often)
            elif current_crit_chance >= 30:  # Medium crit
                return 0.7  # Good
            elif current_crit_chance >= 15:  # Low crit
                return 0.4  # Mediocre
            else:  # Very low crit
                return 0.1  # Poor (rarely critting)
        
        # Area of Effect - depends on skill type
        if stat_name == 'area_of_effect':
            if build['skill_type'] not in ['area', 'aoe']:
                return 0.0  # Single target skill, AoE does nothing
            
            base_aoe = skill_scaling.get('base_aoe_radius', 20)
            if base_aoe < 15:  # Small AoE skill
                return 1.0  # High value - needs AoE badly
            elif base_aoe > 30:  # Large AoE skill
                return 0.5  # Lower value - already covers screen
            else:
                return 0.8
        
        # Projectile stats
        if stat_name == 'projectile_speed':
            if 'projectile' not in build.get('skill_tags', []):
                return 0.0
            return 0.6  # Usually useful for QoL
        
        if stat_name == 'additional_projectiles':
            if 'projectile' not in build.get('skill_tags', []):
                return 0.0
            
            # More projectiles = more hits (if they can hit same target)
            if build.get('projectiles_can_overlap', False):
                return 1.0  # Excellent (each proj = more damage)
            else:
                return 0.7  # Good for clear, not single target
        
        # Duration - depends on skill
        if stat_name == 'skill_duration':
            if 'duration' not in build.get('skill_tags', []):
                return 0.0  # Instant skill
            
            base_duration = skill_scaling.get('base_duration', 4.0)
            if base_duration < 3.0:  # Short duration
                return 1.0  # High value - needs duration
            elif base_duration > 8.0:  # Long duration
                return 0.3  # Low value - already long enough
            else:
                return 0.6
        
        # Attributes (always somewhat useful)
        if stat_name in ['strength', 'dexterity', 'intelligence']:
            return 0.4  # Needed for gear/gems
        
        return 0.5  # Default for unknown stats


def skill_scaling_vectors_explained():
    """
    Why skill base values matter for node selection
    
    CONCEPT: Same passive node has different value for different skills
    
    CRITICAL CLARIFICATIONS:
    1. "Low base damage" is NOT a trap for attack skills!
       - Attack skills scale from WEAPON damage, not skill base damage
       - "Low base damage" just means "scales with weapon" (normal for attacks)
       - Explosive Arrow example was wrong - it's weapon-based, needs weapon damage nodes
    
    2. Attack speed has THRESHOLD effects, not linear scaling!
       - If mob dies in 1 hit: speed doesn't matter (already instant)
       - If mob dies in 1 second with 1.0 APS: 2.0 APS still takes 1 attack (no benefit!)
       - Need 2-3x speed to actually get second hit before mob dies
       - Speed value depends on time-to-kill breakpoints
    """
    
    examples = {
        'crit_scaling': {
            'ice_spear': {
                'base_crit': 7.0,
                'with_300_increased_crit': '7.0 * 4.0 = 28%',  # Excellent!
                'node_value': 1.0,
                'reasoning': 'High base crit scales efficiently with increased crit'
            },
            'earthquake': {
                'base_crit': 5.0,
                'with_300_increased_crit': '5.0 * 4.0 = 20%',  # OK
                'node_value': 0.6,
                'reasoning': 'Lower base crit, same investment gives less final crit'
            },
            'non_crit_skill_with_RT': {
                'base_crit': 5.0,
                'with_resolute_technique': '0% (cannot crit)',
                'node_value': 0.0,
                'reasoning': 'Resolute Technique keystone disables crits entirely'
            }
        },
        
        'attack_speed_scaling_THRESHOLD_EFFECTS': {
            'scenario_1_overkill': {
                'mob_hp': 10000,
                'hit_damage': 15000,
                'base_aps': 1.0,
                'attacks_needed': 1,
                'time_to_kill': '1.0 seconds (1 attack)',
                
                'with_50_increased_speed': {
                    'new_aps': 1.5,
                    'attacks_needed': 1,  # Still only need 1 hit!
                    'time_to_kill': '0.67 seconds (1 attack)',
                    'actual_benefit': 0.33,  # Only 33% faster (not 50%)
                    'node_value': 0.7,  # Less than expected
                    'reasoning': 'Overkilling - speed helps but not full value'
                },
                
                'with_100_increased_speed': {
                    'new_aps': 2.0,
                    'attacks_needed': 1,
                    'time_to_kill': '0.5 seconds (1 attack)',
                    'actual_benefit': 0.5,  # Only 50% faster (not 100%)
                    'node_value': 0.5,  # Diminished value
                    'reasoning': 'Still overkilling - need more damage, not speed'
                }
            },
            
            'scenario_2_threshold': {
                'mob_hp': 10000,
                'hit_damage': 6000,
                'base_aps': 1.0,
                'attacks_needed': 2,
                'time_to_kill': '2.0 seconds (2 attacks)',
                
                'with_50_increased_speed': {
                    'new_aps': 1.5,
                    'attacks_needed': 2,
                    'time_to_kill': '1.33 seconds (2 attacks)',
                    'actual_benefit': 0.50,  # Full 50% benefit
                    'node_value': 1.0,  # Full value!
                    'reasoning': 'Need multiple hits - speed scales linearly'
                },
                
                'with_100_increased_speed': {
                    'new_aps': 2.0,
                    'attacks_needed': 2,
                    'time_to_kill': '1.0 seconds (2 attacks)',
                    'actual_benefit': 1.0,  # Full 100% benefit
                    'node_value': 1.0,
                    'reasoning': 'Multiple hits needed - full linear scaling'
                }
            },
            
            'scenario_3_breakpoint': {
                'mob_hp': 10000,
                'hit_damage': 8000,
                'base_aps': 1.0,
                'attacks_needed': 2,
                'time_to_kill': '2.0 seconds (2 attacks)',
                
                'with_25_increased_damage': {
                    'new_hit_damage': 10000,
                    'attacks_needed': 1,  # Crossed threshold!
                    'time_to_kill': '1.0 seconds (1 attack)',
                    'actual_benefit': 1.0,  # 100% faster!
                    'node_value': 2.0,  # HUGE value
                    'reasoning': 'Crossed one-shot threshold - massive speedup'
                },
                
                'with_100_increased_speed': {
                    'new_aps': 2.0,
                    'attacks_needed': 2,  # Still need 2 hits
                    'time_to_kill': '1.0 seconds (2 attacks)',
                    'actual_benefit': 1.0,  # 100% faster
                    'node_value': 1.0,
                    'reasoning': 'Linear scaling, but damage would have been better'
                }
            }
        },
        
        'base_damage_WEAPON_SCALING': {
            'spell_skill': {
                'skill': 'Fireball',
                'base_damage': '100-150 fire damage at gem level 20',
                'scaling': 'Scales from gem level + spell damage % + added damage',
                'weapon_matters': False,
                'reasoning': 'Spell damage is independent of weapon'
            },
            
            'attack_skill_NOT_A_TRAP': {
                'skill': 'Heavy Strike',
                'base_damage': '10% more damage (at gem level 1)',  # The SKILL adds multiplier
                'actual_damage': 'Weapon base damage × (1.10) × all multipliers',
                'scaling': 'Scales from WEAPON damage + attack damage % + added damage',
                'weapon_matters': True,
                'reasoning': '''
                    LOW SKILL BASE DAMAGE IS NORMAL FOR ATTACKS!
                    
                    Attack skills don't have their own base damage like spells.
                    They use weapon damage as the base.
                    
                    Example with 500 DPS weapon:
                    - Heavy Strike: 500 × 1.10 = 550 DPS
                    - Cleave: 500 × 0.80 = 400 DPS (wider AoE trades damage)
                    
                    "Low base damage" just means "uses weapon damage"
                    NOT a trap! Just need good weapon + weapon damage nodes.
                ''',
                'node_priority': {
                    'weapon_damage': 1.0,  # Scales the base (weapon)
                    'attack_damage': 1.0,   # Also scales weapon damage
                    'added_damage': 0.8,    # Flat added (good with fast attacks)
                    'attack_speed': 1.0     # If multi-hit (see threshold effects above)
                }
            }
        },
        
        'aoe_scaling': {
            'small_aoe': {
                'skill': 'Glacial Cascade',
                'base_radius': 10,
                'with_100_increased_aoe': '20 radius',
                'node_value': 1.0,
                'reasoning': 'Small AoE desperately needs increases'
            },
            'large_aoe': {
                'skill': 'Righteous Fire',
                'base_radius': 35,
                'with_100_increased_aoe': '70 radius',
                'node_value': 0.3,
                'reasoning': 'Already covers entire screen, more is overkill'
            }
        },
        
        'duration_scaling': {
            'short_duration': {
                'skill': 'Vaal Righteous Fire',
                'base_duration': 4.0,
                'with_100_increased_duration': '8.0 seconds',
                'node_value': 1.0,
                'reasoning': 'Short buff, duration extends powerful effect'
            },
            'long_duration': {
                'skill': 'Blade Vortex',
                'base_duration': 5.0,
                'with_100_increased_duration': '10.0 seconds',
                'node_value': 0.4,
                'reasoning': 'Already lasts long enough for mapping'
            }
        }
    }
    
    """
    KEY INSIGHTS FOR NEURAL NETWORK:
    
    1. ATTACK SPEED HAS THRESHOLD EFFECTS
       - Not linear scaling like we thought!
       - Value depends on hits-to-kill
       - If overkilling: speed has reduced value (get damage instead)
       - If multi-hit: speed has full value
       - Need to encode: current_damage / enemy_hp ratio
    
    2. BASE DAMAGE CONFUSION RESOLVED
       - Spell skills: Have their own base damage (gem level)
       - Attack skills: Use weapon base damage (skill adds multiplier)
       - "Low base damage" on attack skills is NORMAL, not a trap
       - Attack skills need weapon damage nodes, not "skill base damage"
    
    3. DAMAGE VS SPEED TRADEOFF
       - Near one-shot threshold: Damage > Speed (cross threshold!)
       - Far from threshold: Speed = Damage (linear scaling)
       - Overkilling: Damage < Speed (wasting damage)
    
    4. SKILL BALANCE - NO 10X DIFFERENCES
       - CRITICAL: Most skills are balanced within 2x of each other!
       - No "god tier" skills that are 10x better
       - Differences are in scaling vectors, not raw power
       - Some skills prefer crit, others prefer non-crit
       - Some skills prefer speed, others prefer hit damage
       - Some skills prefer AoE, others single target
       
       Why this matters:
       - Network doesn't need to learn "skill X is best"
       - Just needs to match: skill's vectors → appropriate clusters
       - Ice Spear (7% base crit) → crit clusters = good
       - Earthquake (5% base crit) → non-crit clusters = equally good
       - BOTH end up with similar final DPS if built correctly!
       
       Implication:
       - Don't train network to pick skills
       - Train network to optimize GIVEN skill
       - User picks skill, network finds best tree/gear/gems for it
       - Much simpler and more useful!
    
    5. NETWORK NEEDS TO LEARN
       - Current DPS / Enemy HP ratio
       - Attacks needed to kill (1, 2, 3+)
       - Whether at threshold (8000 damage vs 10k HP = near threshold)
       - Prioritize damage nodes if near threshold
       - Prioritize speed nodes if multi-hit
       - Match skill's scaling vectors to available passive clusters
       - Don't fight the skill's natural strengths
    """
    
    return examples


def skill_balance_and_scaling_vector_matching():
    """
    CRITICAL INSIGHT: Skills are balanced, just have different scaling vectors
    
    Common misconception:
    - "Skill A is 10x better than Skill B"
    
    Reality:
    - Skills are within 2x of each other when built correctly
    - Differences are in HOW they scale, not POTENTIAL power
    - A skill that seems weak just needs different build approach
    """
    
    examples = {
        'spell_comparison_SIMILAR_POWER': {
            'ice_spear_crit_build': {
                'skill': 'Ice Spear',
                'base_crit': 7.0,
                'optimal_scaling': 'Crit chance + crit multi',
                'tree_allocation': 'Shadow crit cluster + Witch spell cluster',
                'final_dps': 10_000_000,  # 10M DPS
                'investment': '100 passive points'
            },
            
            'blade_vortex_noncrit_build': {
                'skill': 'Blade Vortex',
                'base_crit': 5.0,
                'optimal_scaling': 'Spell damage + cast speed + duration',
                'tree_allocation': 'Witch spell cluster + duration nodes',
                'final_dps': 9_500_000,  # 9.5M DPS
                'investment': '100 passive points',
                'note': 'Only 5% less DPS than Ice Spear! Different vectors, same result'
            },
            
            'fireball_conversion_build': {
                'skill': 'Fireball',
                'base_crit': 6.0,
                'optimal_scaling': 'Fire damage + elemental damage + penetration',
                'tree_allocation': 'Templar elemental cluster + Witch spell cluster',
                'final_dps': 10_200_000,  # 10.2M DPS
                'investment': '100 passive points',
                'note': 'Slightly higher! Different element, same power level'
            }
        },
        
        'attack_comparison_SIMILAR_POWER': {
            'cyclone_fast_hits': {
                'skill': 'Cyclone',
                'hit_rate': 8.0,  # 8 hits per second
                'hit_damage': 100_000,
                'optimal_scaling': 'Attack speed + generic damage',
                'tree_allocation': 'Duelist attack cluster + life wheel',
                'final_dps': 800_000,
                'investment': '100 passive points'
            },
            
            'earthquake_slow_hits': {
                'skill': 'Earthquake',
                'hit_rate': 2.0,  # 2 hits per second
                'hit_damage': 380_000,
                'optimal_scaling': 'Damage + area + slow but powerful',
                'tree_allocation': 'Marauder damage cluster + life wheel',
                'final_dps': 760_000,
                'investment': '100 passive points',
                'note': 'Only 5% less DPS! Slow hits but bigger damage'
            },
            
            'spectral_throw_projectile': {
                'skill': 'Spectral Throw',
                'hit_rate': 10.0,  # 10 hits per second (multiple projectiles)
                'hit_damage': 75_000,
                'optimal_scaling': 'Projectile damage + attack speed + pierce',
                'tree_allocation': 'Ranger projectile cluster + life wheel',
                'final_dps': 750_000,
                'investment': '100 passive points',
                'note': 'Similar DPS! Different mechanics, same power'
            }
        },
        
        'why_skills_seem_unbalanced': {
            'perception': 'Some skills seem 10x better',
            
            'reality': {
                'bad_build': {
                    'skill': 'Ice Spear',
                    'tree': 'Took generic damage nodes, no crit',
                    'dps': 2_000_000,  # 2M DPS
                    'reason': 'Fighting the skill! Ignored 7% base crit (its strength)',
                    'verdict': 'Skill seems weak, but build is wrong'
                },
                
                'good_build': {
                    'skill': 'Ice Spear',
                    'tree': 'Crit cluster + crit multi nodes',
                    'dps': 10_000_000,  # 10M DPS
                    'reason': 'Leveraged 7% base crit (the skill\'s natural strength)',
                    'verdict': '5x better by matching scaling vectors!'
                },
                
                'lesson': '''
                    The 10x difference isn't Ice Spear vs other skills.
                    It's GOOD BUILD vs BAD BUILD of same skill.
                    
                    Any skill can be weak if built wrong.
                    Any skill can be strong if built right.
                    
                    The difference is matching skill's vectors to tree clusters!
                '''
            }
        }
    }
    
    """
    IMPLICATIONS FOR NEURAL NETWORK:
    
    1. DON'T TRAIN SKILL SELECTION
       - User chooses skill (based on playstyle preference)
       - Network optimizes tree/gear/gems FOR THAT SKILL
       - Much simpler problem!
    
    2. LEARN SCALING VECTOR MATCHING
       - High base crit skill → prioritize crit clusters
       - Low base crit skill → prioritize damage/speed clusters
       - AoE skill → prioritize AoE + clear speed
       - Single target skill → prioritize boss damage
    
    3. NO "OPTIMAL" SKILL EXISTS
       - Ice Spear isn't "better" than Blade Vortex
       - They're equal power, different builds
       - Network learns: "For Ice Spear, use crit. For BV, use spell damage"
       - Not: "Ice Spear is best, always recommend it"
    
    4. SIMPLIFIES TRAINING
       - Train on many different skills (variety)
       - Learn pattern: skill stats → appropriate clusters
       - Generalizes to new skills automatically
       - Don't need to discover "meta" skills
    
    5. USER EXPERIENCE
       - User: "Optimize my Blade Vortex build"
       - Network: "Your skill has 5% base crit → skip crit, take spell damage + cast speed + duration"
       - Result: 9.5M DPS (near optimal)
       
       vs
       
       - Bad network: "Ice Spear is better, reroll your character"
       - User: "WTF I like Blade Vortex"
       - Result: Unhappy user
    
    TAKEAWAY:
    Skills are balanced. Network's job is to find the right scaling vectors
    for each skill, not to pick "best" skill. This is way more useful and
    way simpler to train!
    """
    
    return examples


def dynamic_node_valuation():
    """
    Calculate node value based on current build state and skill scaling
    
    Traditional approach (WRONG):
    - Crit node always has value X for crit builds
    
    Correct approach:
    - Crit node value depends on:
      1. Skill base crit (higher = better scaling)
      2. Current crit chance (diminishing returns at high values)
      3. Investment in crit multi (synergy)
      4. Skill hit rate (fast hitting = less crit needed)
    """
    
    def calculate_marginal_value(stat_type, current_stats, skill_data):
        """
        Calculate marginal value of adding +X% to a stat
        
        Returns: Expected DPS increase per 10% increase in stat
        """
        
        # Example: Crit chance
        if stat_type == 'crit_chance':
            base_crit = skill_data['base_crit_chance']
            current_increased_crit = current_stats['increased_crit_chance']
            current_crit_multi = current_stats['crit_multi']
            
            # Calculate current effective crit
            current_crit = base_crit * (1 + current_increased_crit / 100)
            current_crit = min(current_crit, 95)  # Cap at 95%
            
            # Calculate with +10% increased crit
            new_increased_crit = current_increased_crit + 10
            new_crit = base_crit * (1 + new_increased_crit / 100)
            new_crit = min(new_crit, 95)
            
            # DPS increase formula
            crit_dps_mult = 1 + (current_crit / 100) * (current_crit_multi / 100)
            new_crit_dps_mult = 1 + (new_crit / 100) * (current_crit_multi / 100)
            
            marginal_increase = (new_crit_dps_mult / crit_dps_mult) - 1
            
            return marginal_increase
        
        # Example: Attack speed
        if stat_type == 'attack_speed':
            # Linear scaling (usually)
            return 0.10  # 10% increase = 10% more DPS
        
        # Example: Damage
        if stat_type == 'increased_damage':
            current_increased = current_stats['total_increased_damage']
            # Diminishing returns with high investment
            marginal = 10 / (100 + current_increased)
            return marginal
        
        return 0.05  # Default
    
    """
    Use marginal value to prioritize nodes:
    
    At 0% increased crit:
    - Crit node: 0.15 marginal value (15% DPS increase)
    - Damage node: 0.10 marginal value (10% DPS increase)
    → Take crit node
    
    At 300% increased crit (near cap):
    - Crit node: 0.02 marginal value (2% DPS increase)
    - Damage node: 0.06 marginal value (6% DPS increase)
    → Take damage node
    
    This is dynamic optimization based on current state!
    Neural network can learn this by encoding current stats.
    """
    
    return calculate_marginal_value
    
    """
    Use in reward function:
    
    reward = (
        damage_increase * 10 +
        defense_increase * 5 -
        num_travel_nodes * 2 -          ← Travel node penalty
        num_dead_nodes * 10 -            ← DEAD NODE PENALTY (5x worse!)
        total_points_used * 0.5          ← Efficiency penalty
    )
    
    This encourages network to:
    1. AVOID dead nodes at all costs (massive penalty)
    2. Minimize travel nodes (smaller penalty)
    3. Only allocate nodes that actually help the build
    4. Path efficiently to avoid crossing useless regions
    
    Example:
    - Spell build pathing through Duelist (attack nodes): BAD, dead nodes everywhere
    - Spell build staying in Witch/Templar area: GOOD, all nodes useful
    """
    
    return calculate_node_priority


def example_dead_nodes():
    """
    Real examples of dead nodes for different builds:
    
    SPELL BUILD (Blade Vortex):
    ✓ Spell damage, cast speed, elemental damage = GOOD (1.0 relevance)
    ✗ Attack speed, weapon damage, accuracy = DEAD (0.0 relevance)
    ~ Generic damage, life, attributes = OK (0.5-0.8 relevance)
    
    LIFE-BASED BUILD:
    ✓ % life, flat life, life regen = GOOD (1.0 relevance)
    ✗ % energy shield, ES recharge = DEAD (0.0 relevance)
    ~ Armour, evasion = OK (0.3-1.0 depending on build)
    
    PHYSICAL ATTACK BUILD (No conversion):
    ✓ Physical damage, attack speed = GOOD (1.0 relevance)
    ✗ Fire/cold/lightning damage = DEAD (0.0 relevance)
    ✗ Spell damage, cast speed = DEAD (0.0 relevance)
    
    NON-CRIT BUILD (Resolute Technique):
    ✓ Damage, attack speed, life = GOOD (1.0 relevance)
    ✗ Crit chance, crit multi = DEAD (0.0 relevance, RT prevents crits)
    
    MINION BUILD:
    ✓ Minion damage, minion life = GOOD (1.0 relevance)
    ✗ Player damage, player attack/cast speed = DEAD (0.0, doesn't affect minions)
    ~ Life, defense = OK (0.8 relevance, player still needs to survive)
    
    WHY THIS MATTERS:
    - A spell build pathing through Duelist area wastes 20+ points on dead nodes
    - Better to path around (even if longer) to avoid dead regions
    - Neural network MUST learn which nodes are dead for each archetype
    - Dead nodes are worse than empty space!
    """
    
    examples = {
        'spell_build_in_duelist': {
            'path_length': 15,
            'dead_nodes': 12,  # Attack speed, weapon damage, accuracy
            'useful_nodes': 3,  # Just life/attributes
            'penalty': -120,    # 12 × 10 penalty
            'verdict': 'TERRIBLE PATH'
        },
        
        'spell_build_in_witch': {
            'path_length': 15,
            'dead_nodes': 0,
            'useful_nodes': 15,  # Spell damage, cast speed, ES, life
            'penalty': 0,
            'verdict': 'EFFICIENT PATH'
        },
        
        'life_build_through_CI_nodes': {
            'path_length': 10,
            'dead_nodes': 8,   # Pure ES nodes
            'useful_nodes': 2,
            'penalty': -80,    # 8 × 10 penalty
            'verdict': 'BAD PATH - avoid ES clusters'
        }
    }
    
    return examples


def spatial_encoding_for_tree():
    """
    Encode tree position to help network learn clustering
    
    Problem: Node IDs are arbitrary (node 1234 vs 5678 don't encode proximity)
    
    Solution: Add spatial coordinates
    """
    
    def encode_node_with_position(node):
        """
        Include X, Y coordinates in node encoding
        """
        encoding = {
            'node_id': node['id'],
            'stats': node['stats'],  # Damage, life, etc.
            
            # ADD SPATIAL INFO
            'x_position': node['x'] / 10000,  # Normalize to [-1, 1]
            'y_position': node['y'] / 10000,
            'cluster_id': get_cluster_id(node['x'], node['y']),  # Which cluster?
            'distance_from_start': euclidean_distance(node, starting_node),
            
            # Node type
            'is_keystone': node['type'] == 'keystone',
            'is_notable': node['type'] == 'notable',
            'is_small': node['type'] == 'small'
        }
        
        return encoding
    
    """
    Benefits:
    1. Network learns that nearby nodes (similar X,Y) have similar stats
    2. Can learn to allocate entire regions (clusters)
    3. Understands distance cost (far nodes require more travel)
    4. Discovers cluster boundaries automatically
    
    This is how Graph Neural Networks work!
    """
    
    return encode_node_with_position


# ============================================================================
# SUMMARY: Exploiting Tree Structure
# ============================================================================

"""
KEY INSIGHTS FOR NEURAL NETWORK:

1. CLUSTERING REDUCES SEARCH SPACE
   - 8 major clusters instead of 1500 random nodes
   - Choose 2-3 clusters = 56 combinations
   - Within clusters, greedy notable selection works well
   - Effective search space: 10^6 not 10^450

2. NODE HIERARCHY
   - Keystones: 20 binary decisions (critical)
   - Notables: ~280 power nodes (important)
   - Small nodes: ~1200 incremental/travel (auto-path)
   
3. TRAVEL NODE PENALTY
   - Penalize inefficient pathing in reward function
   - Encourages nearby cluster selection
   - Forces efficient shortest paths

4. DEAD NODE PENALTY (WORSE THAN TRAVEL!)
   - Attack nodes for spell build = 0 value
   - ES nodes for life build = 0 value
   - Crit nodes for non-crit build = 0 value
   - Penalty: 5x worse than travel nodes
   
5. SPATIAL ENCODING
   - Add X,Y coordinates to node encoding
   - Network learns geographic clustering
   - Can use Graph Neural Network architecture

6. LOCAL MAXIMA IS NOT A PROBLEM
   - Traditional ML concern: Getting stuck in local maxima
   - In PoE: NOT AN ISSUE due to clustering!
   
   Why local maxima doesn't matter:
   a) Only ~8 clusters relevant for any damage type
      - Spell damage: Witch/Templar clusters
      - Attack damage: Duelist/Ranger clusters
      - Minion damage: Witch cluster
      
   b) Clusters are far apart geographically
      - Can't accidentally "get stuck" between them
      - Either you commit to a cluster or you don't
      
   c) Within a cluster, nodes are similar
      - All nodes in "spell damage cluster" increase spell damage
      - No local maxima within cluster (all options ~equally good)
      - Greedy selection works fine!
      
   d) The decision is binary at cluster level
      - Take life cluster: YES or NO
      - Take crit cluster: YES or NO
      - Not a smooth gradient where you can get stuck
      
   e) Cross-cluster synergies are rare
      - Life + Damage = obvious combo (not a "discovery")
      - ES + Damage = obvious combo
      - No hidden synergies between distant clusters
   
   Example:
   - Traditional optimization: Smooth fitness landscape with many local peaks
   - PoE tree: Discrete clusters, binary decisions, obvious combos
   
   This means:
   - Simple greedy algorithms work well (as we've seen!)
   - Neural network doesn't need complex exploration strategies
   - No need for simulated annealing, genetic algorithms, etc.
   - Just need to learn: "Which 2-3 clusters?" then greedy within them
   
   PRACTICAL IMPLICATION:
   - Can use simple supervised learning (not reinforcement learning)
   - Train on good builds from poe.ninja
   - Network learns: "Blade Vortex → Witch + Templar clusters"
   - No need to explore random combinations
   
7. PRACTICAL APPROACH
   - Train on cluster selection (high-level decisions)
   - Use A* pathfinding for efficient routing
   - Only train notable selection within chosen clusters
   - Much faster and more effective!

IMPLEMENTATION PRIORITY:
1. Start with cluster-level decisions (which 2-3 areas?)
2. Add keystone selection (which build-defining nodes?)
3. Notable selection within clusters (greedy works)
4. Auto-path small nodes (A* algorithm)

This hierarchical approach is how experienced players think:
"I need life and crit, so I'll path through the life wheel and 
grab the crit nodes near Shadow"

NOT: "I'll allocate nodes 12, 47, 193, 284, ..."
"""


def why_no_local_maxima():
    """
    Detailed explanation: Why PoE tree doesn't suffer from local maxima
    
    COMPARISON WITH TYPICAL OPTIMIZATION PROBLEMS:
    """
    
    typical_problem = {
        'landscape': 'Smooth continuous function',
        'example': 'f(x,y) = sin(x) * cos(y) with many peaks',
        'issue': 'Can get stuck on small peak, miss global maximum',
        'solution': 'Need exploration: simulated annealing, genetic algorithms',
        'visualization': '''
            Height
              ^
              |     *  Peak3
              |  *     /\
              | /\    /  \  *  Peak1 (global max)
              |/  \  /    \ /\
              |    \/Peak2 \/
              +-------------------> Position
        '''
    }
    
    poe_tree_reality = {
        'landscape': 'Discrete clusters, far apart',
        'example': '8 distinct clusters in different tree regions',
        'issue': 'No issue! Clusters are obvious and separated',
        'solution': 'Simple greedy: pick best 2-3 clusters, then best nodes within',
        'visualization': '''
            Power
              ^
              |
              |  [Life]              [Damage]         [Crit]
              |   ████                 ████            ████
              |   ████                 ████            ████
              |
              |          [ES]    [Block]    [Eva]
              |          ███      ███        ███
              |          ███      ███        ███
              |
              +-----------------------------------------------------> Tree Position
              
            Notice:
            1. Clusters are separated (not overlapping)
            2. Within cluster, all nodes ~similar value
            3. No "valleys" between clusters (just empty space)
            4. Binary decision: allocate from cluster or not
        '''
    }
    
    """
    WHY THIS MATTERS FOR NEURAL NETWORK:
    
    1. Don't need exploration strategies
       - No need for epsilon-greedy (random exploration)
       - No need for temperature/annealing
       - Just learn which clusters are good for which build
    
    2. Supervised learning is sufficient
       - Train on poe.ninja builds (already optimal)
       - Learn pattern: "Spell build → Witch clusters"
       - Don't need to discover this through trial/error
    
    3. Greedy is near-optimal within clusters
       - Once you choose a cluster, take best nodes
       - No complex optimization needed
       - Current greedy algorithm already achieves this!
    
    4. Simplifies training
       - Fewer hyperparameters to tune
       - Faster convergence
       - More predictable behavior
       - Easier to debug
    """
    
    return poe_tree_reality


def cluster_based_optimization():
    """
    Leverage cluster structure for efficient optimization
    
    HIERARCHICAL DECISION MAKING:
    """
    
    def optimize_tree_hierarchical(build_archetype, point_budget):
        """
        Two-stage optimization exploiting cluster structure
        """
        
        # STAGE 1: Cluster selection (high-level)
        # This is where the "optimization" happens
        available_clusters = identify_relevant_clusters(build_archetype)
        
        # For spell build, only ~3-4 clusters matter:
        relevant_clusters = {
            'life_wheel': {'priority': 10, 'nodes': 40},
            'witch_spell': {'priority': 10, 'nodes': 50},
            'templar_elemental': {'priority': 8, 'nodes': 45},
            'shadow_crit': {'priority': 6, 'nodes': 35},  # If crit build
        }
        
        # Choose top 2-3 clusters (only 56 combinations!)
        selected_clusters = greedy_cluster_selection(
            relevant_clusters,
            point_budget
        )
        
        # STAGE 2: Node selection within clusters (greedy)
        # No local maxima here - all nodes in cluster are similar!
        allocated_nodes = []
        
        for cluster in selected_clusters:
            # Greedy: take highest value nodes until budget exhausted
            cluster_nodes = get_cluster_nodes(cluster)
            sorted_nodes = sort_by_value(cluster_nodes)
            
            for node in sorted_nodes:
                if points_remaining >= path_cost(node):
                    allocated_nodes.append(node)
                    points_remaining -= path_cost(node)
        
        return allocated_nodes
    
    """
    Why this works without local maxima:
    
    1. Stage 1 is discrete (choose cluster A or B, not smooth)
    2. Stage 2 is monotonic (more nodes in good cluster = better)
    3. No "wrong turns" that trap you
    4. No hidden synergies between distant clusters
    5. Decisions are independent (life cluster doesn't affect damage cluster choice)
    
    Result: Simple greedy gives near-optimal solution!
    """
    
    return optimize_tree_hierarchical


def compare_to_complex_optimizations():
    """
    Why PoE doesn't need complex optimization algorithms
    """
    
    comparison = {
        'genetic_algorithms': {
            'when_needed': 'Complex fitness landscapes with many local maxima',
            'poe_needs_it': False,
            'reason': 'PoE tree has discrete clusters, no hidden local maxima',
            'overkill': 'Would work but adds complexity for no benefit'
        },
        
        'simulated_annealing': {
            'when_needed': 'Escaping local maxima in continuous spaces',
            'poe_needs_it': False,
            'reason': 'No local maxima to escape from!',
            'overkill': 'Temperature schedule unnecessary'
        },
        
        'reinforcement_learning': {
            'when_needed': 'Unknown reward function, need to explore',
            'poe_needs_it': False,
            'reason': 'Reward is known (DPS/EHP), builds exist on poe.ninja',
            'better_approach': 'Supervised learning on good builds'
        },
        
        'greedy_algorithm': {
            'when_needed': 'When greedy gives optimal/near-optimal',
            'poe_needs_it': True,
            'reason': 'Cluster structure makes greedy work!',
            'current_status': 'Already implemented and working (50% DPS increase)'
        },
        
        'neural_network': {
            'when_needed': 'Learn patterns from data (which clusters for which builds)',
            'poe_needs_it': True,
            'reason': 'Better than greedy, learns build archetypes',
            'approach': 'Supervised learning on poe.ninja builds',
            'benefit': 'Learns: Blade Vortex → Witch + life clusters automatically'
        }
    }
    
    """
    CONCLUSION:
    
    PoE build optimization is easier than typical ML problems because:
    1. Discrete cluster structure (not continuous)
    2. Only ~8 relevant clusters per build
    3. No local maxima between clusters
    4. Greedy works within clusters
    5. Optimal builds already exist (poe.ninja)
    
    Best approach:
    1. Neural network learns cluster selection (supervised)
    2. Greedy algorithm within clusters
    3. No need for complex exploration
    4. Fast training, predictable results
    """
    
    return comparison
```

### Staged Training Strategy (Practical Approach)

```python
class StagedMultiComponentTraining:
    """
    Don't optimize everything at once - use staged training!
    
    Stage 1: Tree only (current greedy optimizer)
    Stage 2: Tree + gear priorities
    Stage 3: Tree + gear + gems
    Stage 4: Joint fine-tuning
    """
    
    def train_stage_1_tree_only(self, builds, epochs=500):
        """
        STAGE 1: Optimize passive tree with FIXED gear/gems
        
        This is what we have working NOW!
        - User provides gear and gems
        - Model optimizes tree allocation
        - Already gives 50%+ improvement
        """
        print("=== STAGE 1: Tree Optimization ===")
        
        # Freeze gear and gem decoders
        for param in self.model.gear_decoder.parameters():
            param.requires_grad = False
        for param in self.model.gem_decoder.parameters():
            param.requires_grad = False
        
        for epoch in range(epochs):
            for build in builds:
                # Only optimize tree
                suggestions = self.model(build)
                tree_improvements = suggestions['tree']
                
                # Apply tree changes, keep gear/gems fixed
                new_build = build.copy()
                new_build.tree = self.apply_tree_changes(build.tree, tree_improvements)
                
                # Test against poedb enemies
                survival = self.test_against_all_enemies(new_build)
                
                # Loss: negative survival (want to maximize)
                loss = -survival.mean()
                
                loss.backward()
                optimizer.step()
        
        print(f"Stage 1 complete: Tree optimizer trained")
    
    def train_stage_2_gear_stats(self, builds, epochs=300):
        """
        STAGE 2: Add simple gear stat generation
        
        Just output average values for 5 key stats per slot
        Much simpler than complex item search!
        """
        print("=== STAGE 2: Simple Gear Stat Generation ===")
        
        # Unfreeze gear decoder, keep tree decoder trainable
        for param in self.model.gear_decoder.parameters():
            param.requires_grad = True
        
        for epoch in range(epochs):
            for build in builds:
                # Get tree + gear suggestions
                suggestions = self.model(build)
                
                # Apply changes
                new_build = build.copy()
                new_build.tree = self.apply_tree_changes(build.tree, suggestions['tree'])
                
                # Apply gear: just use the averaged stat values directly
                new_build.gear = self.create_simple_gear(suggestions['gear'])
                
                # Evaluate
                survival = self.test_against_all_enemies(new_build)
                loss = -survival.mean()
                
                loss.backward()
                optimizer.step()
        
        print(f"Stage 2 complete: Simple gear generator trained")
    
    def create_simple_gear(self, gear_stats):
        """
        Convert predicted stat values to simple gear items
        
        No complex item database needed - just create items with average stats
        """
        gear_items = []
        
        for slot, stats in gear_stats.items():
            # Create simple item with these stats
            item = {
                'slot': slot,
                'stats': {}
            }
            
            # Map to actual stat names
            stat_names = self.model.gear_decoder.slot_stats[slot]
            for i, stat_name in enumerate(stat_names):
                item['stats'][stat_name] = stats[i].item()
            
            gear_items.append(item)create_simple_gear(suggestions['gear']
        
        return gear_items
    
    def train_stage_3_gems(self, builds, epochs=300):
        """
        STAGE 3: Add gem recommendations
        """
        print("=== STAGE 3: Gem Optimization ===")
        
        # Unfreeze everything
        for param in self.model.parameters():
            param.requires_grad = True
        
        for epoch in range(epochs):
            for build in builds:
                # Get ALL suggestions
                suggestions = self.model(build)
                
                # Apply ALL changes
                new_build = build.copy()
                new_build.tree = self.apply_tree_changes(build.tree, suggestions['tree'])
                new_build.gear = self.search_gear_matching_priorities(suggestions['gear'], build.budget)
                new_build.gems = self.apply_gem_suggestions(build.gems, suggestions['gems'])
                
                # Evaluate complete build
                survival = self.test_against_all_enemies(new_build)
                loss = -survival.mean()
                
                loss.backward()
                optimizer.step()
        
        print(f"Stage 3 complete: Full build optimizer trained")


def example_simple_gear_output():
    """
    Example of simplified gear generation
    
    Instead of:
    "Find Titanium Spirit Shield with +78 life, +42% fire res, +38% cold res..."
    
    Just output:
    Ring 1: {life: 65, resistances: 95, added_damage: 22, accuracy: 350, attributes: 42}
    Ring 2: {life: 58, resistances: 88, added_damage: 18, accuracy: 310, attributes: 38}
    
    These are AVERAGE values that make the build viable
    No complex item search needed!
    """
    
    model = MultiComponentBuilder()
    build = load_user_build()
    
    suggestions = model(build)
    
    print("Recommended Gear Stats:")
    print("=" * 60)
    
    for slot, stats in suggestions['gear'].items():
        stat_names = model.gear_decoder.slot_stats[slot]
        print(f"\n{slot.upper()}:")
        for i, stat_name in enumerate(stat_names):
            value = stats[i].item()
            print(f"  {stat_name}: {value:.1f}")
    
    # Output example:
    # WEAPON:
    #   added_phys_damage: 85.0
    #   crit_chance: 6.5%
    #   attack_speed: 15.0%
    #   elemental_damage: 45.0%
    #   accuracy: 400.0
    #
    # RING_1:
    #   life: 65.0
    #   resistances: 95.0 (total across fire/cold/lightning)
    #   added_damage: 22.0
    #   accuracy: 350.0
    #   attributes: 42.0


def why_simple_gear_works():
    """
    Why averaging gear stats is sufficient:
    
    1. PoB calculations are LINEAR for most stats:
       - 100 life on ring = same as 100 life on belt
       - Just sum them up, doesn't matter which slot
    
    2. Only ~5 stats really matter per slot:
       - Life/ES (defense)
       - Resistances (defense)
       - Damage (offense)
       - Attack/cast speed (offense)
       - Utility (movement, attributes)
    
    3. Average values represent "achievable gear":
       - Ring with 65 life, 95 res is realistic for medium budget
       - User can find approximations easily
    
    4. Neural network learns RELATIVE importance:
       - If build is weak to chaos damage → ring gets high chaos res value
       - If build needs more crit → weapon gets high crit chance value
       - It learns WHAT to prioritize, average HOW MUCH
    
    5. Dramatically simpler than item generation:
       - No need for item database
       - No need for trade API integration
       - No need to handle rare item mod combinations
       - Just output 5 numbers per slot!
    
    Result: 10 slots × 5 stats = 50 total numbers to predict
    Much simpler than 10^20 item combinations!
    """
    pass
```

### Simplified Approach: Tree Only (Recommended for V1)

```python
class TreeOnlyOptimizer:
    """
    SIMPLEST viable product: Just optimize tree
    
    Why this is still HUGE value:
    - Tree has biggest search space (2^1500)
    - Tree optimization gives 50%+ improvement (we proved this!)
    - User maintains control over build concept
    - Much simpler to implement and train
    
    Gear/gems can be added later as V2/V3 features
    """
    
    def optimize(self, user_build):
        """
        User provides:
        - Their main skill (Blade Vortex, Cyclone, etc.)
        - Their gear (weapons, armor, accessories)
        - Their support gems
        - Their current tree
        
        We provide:
        - Optimized passive tree allocation
        - 50-100% DPS improvement
        - Better defenses
        - Viability analysis against all content
        """
        
        # Encode user's fixed components
        gear_stats = aggregate_gear_stats(user_build.items)
        gem_stats = aggregate_gem_stats(user_build.gem_links)
        
        # Optimize tree for THIS specific gear/gem setup
        tree_features = torch.cat([
            encode_current_tree(user_build.tree),
            gear_stats,
            gem_stats
        ])
        
        # Neural network predicts optimal tree
        optimal_tree = self.tree_net(tree_features)
        
        return optimal_tree


# This is what we have NOW and it already works great!
```

### Why Stage 1 (Tree Only) is the Right Start

```python
def why_tree_first():
    """
    Reasons to start with tree optimization:
    
    1. BIGGEST SEARCH SPACE: C(1500,100) ≈ 10^135 combinations
       Even just tree is intractable without ML
    
    2. ALREADY PROVEN: Greedy optimizer gives 50%+ improvement
       Neural network will do even better
    
    3. USER CONTROL: Players want to choose their skill/archetype
       Tree optimization respects their vision
    
    4. GEAR DEPENDS ON BUDGET: Optimizing gear requires knowing player's currency
       Tree is "free" (just respec points)
    
    5. GEMS ARE SIMPLER: Only ~20-30 viable support combinations per skill
       Can be added as lookup table or simple rules
    
    6. INTERACTIONS FLOW FROM TREE: Tree determines:
       - Damage type (phys/fire/cold/etc)
       - Attack vs spell vs minion
       - Crit vs non-crit
       - Life vs ES vs hybrid
       Then gear/gems follow naturally
    """
    pass
```

**Conclusion**: Start with tree optimization (what we have now), add gear/gem recommendations in future versions!
