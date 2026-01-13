# Righteous Fire DPS Calculation - PoB Analysis

## Overview
This document explains how Path of Building calculates Righteous Fire DPS and validates our skill-aware optimization implementation.

## How PoB Calculates RF Damage

### 1. Base Damage Calculation
**Source:** `PathOfBuilding/src/Data/Skills/act_int.lua` lines 15210-15216

```lua
preDamageFunc = function(activeSkill, output)
    if output.LifeUnreserved > 1 then
        activeSkill.skillData.FireDot = 
            output.Life * activeSkill.skillData.RFLifeMultiplier + 
            output.EnergyShield * activeSkill.skillData.RFESMultiplier
    end
end
```

**Constants from skill definition:**
```lua
{ "base_righteous_fire_%_of_max_life_to_deal_to_nearby_per_minute", 4200 }
{ "base_righteous_fire_%_of_max_energy_shield_to_deal_to_nearby_per_minute", 4200 }
```

**Calculation:**
- RFLifeMultiplier = 4200 / 6000 = 0.70 (70% of life)
- RFESMultiplier = 4200 / 6000 = 0.70 (70% of ES)
- **Base DPS = 0.70 × Life + 0.70 × Energy Shield**

This is RF's **unique mechanic** - base damage scales directly with life and ES pool size!

### 2. Damage Multipliers
**Source:** `PathOfBuilding/src/Modules/CalcOffence.lua` lines 5460-5470

```lua
-- Increased damage (additive)
local inc = skillModList:Sum("INC", dotTypeCfg, 
    "Damage",           -- Global damage
    "FireDamage",       -- Fire damage
    "ElementalDamage"   -- Elemental damage (fire/cold/lightning)
)

-- More multipliers (multiplicative)
local more = skillModList:More(dotTypeCfg, 
    "Damage", 
    "FireDamage", 
    "ElementalDamage"
)

-- DoT multiplier (additive with fire dot multi)
local mult = 
    skillModList:Sum("BASE", dotTypeCfg, "DotMultiplier") + 
    skillModList:Sum("BASE", dotTypeCfg, "FireDotMultiplier")

-- Final damage
local total = baseVal * (1 + inc/100) * more * (1 + mult/100) * effMult
```

### 3. Complete Scaling Formula

```
RF DPS = (0.70 × Life + 0.70 × ES) 
         × (1 + Increased Damage / 100) 
         × More Multipliers 
         × (1 + DoT Multi / 100)
         × Effectiveness Multiplier
```

**Where Increased Damage includes:**
- Increased Fire Damage
- Increased Burning Damage
- Increased Damage over Time
- Increased Elemental Damage
- Increased Area Damage
- Increased Spell Damage
- Increased Damage (global)

**Effectiveness Multiplier:**
- Enemy fire resistance
- Enemy fire damage taken
- Enemy damage over time taken
- Enemy elemental damage taken

### 4. What Does NOT Scale RF

❌ **Cast Speed** - RF is instant cast, DoT doesn't scale with cast speed  
❌ **Critical Strike** - Burning damage cannot crit  
❌ **Added Damage** - RF has 0% damage effectiveness for added damage  
❌ **Attack Damage** - RF is a spell, not an attack  
❌ **Poison/Bleed** - RF only deals fire DoT  

## Our Implementation

### Skill Database Entry
**File:** `pob_neural_network/utils/skill_scaling_analyzer.py`

```python
'Righteous Fire': {
    'tags': ['spell', 'fire', 'area', 'dot', 'aura'],
    'damage_type': 'dot',
    'added_damage_effectiveness': 0,  # No added damage
    'has_projectile': False,
    'can_crit': False  # DoT cannot crit
}
```

### Scaling Vector Extraction

**Priority-ordered damage types for RF:**

1. ✅ **increased_maximum_life** ← Increases base damage directly!
2. ✅ **increased_maximum_energy_shield** ← Increases base damage directly!
3. ✅ **maximum_life** (flat life)
4. ✅ **maximum_energy_shield** (flat ES)
5. ✅ **fire_spell_damage**
6. ✅ **spell_fire_damage**
7. ✅ **spell_damage**
8. ✅ **fire_damage**
9. ✅ **burning_damage** ← Very strong for RF
10. ✅ **elemental_damage**
11. ✅ **area_damage**
12. ✅ **damage_over_time** ← DoT Multi
13. ✅ **dot**
14. ✅ **damage** (global)

**Other mechanics:**
- Speed type: `none` (no cast speed scaling)
- Can crit: `False`
- Added damage: `[]` (empty - no flat damage)
- Duration scaling: `False`
- Area scaling: `True`
- Projectile scaling: `False`

### Special Enhancement for RF

Added RF-specific logic to prioritize Life/ES nodes:

```python
def _get_increased_damage_types(self, tags: Set[str], support_gems: List[str] = None, skill_name: str = None):
    damage_types = []
    
    # Special case: Righteous Fire scales with Life/ES
    if skill_name and 'righteous fire' in skill_name.lower():
        damage_types.extend([
            'increased_maximum_life',
            'increased_maximum_energy_shield',
            'maximum_life',
            'maximum_energy_shield',
        ])
    
    # ... rest of scaling vectors
```

## Validation Results

All checks passed ✓:

```
✓ PASS: Life/ES scaling
✓ PASS: Fire damage scaling
✓ PASS: Burning damage scaling
✓ PASS: DoT multiplier scaling
✓ PASS: Area damage scaling
✓ PASS: No cast speed scaling
✓ PASS: No crit scaling
✓ PASS: No added damage
✓ PASS: Has area tag
```

## Passive Tree Optimization Strategy

For Righteous Fire builds, the neural network will now prioritize:

### Tier 1 (Highest Priority)
- **Life nodes** - Directly increases base damage (70% of life)
- **Energy Shield nodes** - Directly increases base damage (70% of ES)
- **Fire DoT Multiplier** - Strongest damage multiplier
- **Maximum Fire Resistance** - To reduce self-degen from RF

### Tier 2 (High Priority)
- **Increased Burning Damage**
- **Increased Fire Damage**
- **Increased Damage over Time**
- **Life Regeneration** - To sustain RF self-degen
- **Fire Resistance** - To reduce self-degen

### Tier 3 (Medium Priority)
- **Increased Elemental Damage**
- **Increased Area Damage**
- **Increased Spell Damage**
- **Area of Effect** - Larger clear radius

### Tier 4 (Lower Priority)
- **Global Damage**
- **Generic Defenses** (armour, evasion)
- **Utility** (movement speed, flask effect)

### NOT Allocated (Skip)
- Cast Speed nodes
- Critical Strike nodes
- Attack Damage nodes
- Projectile nodes
- Added Damage nodes

## Testing

Run the validation test:
```bash
python test_rf_scaling.py
```

This will:
1. Extract RF scaling vector
2. Validate against PoB's calculation method
3. Confirm all checks pass
4. Display priority-ordered stat types

## Key Insights

1. **RF is unique** - base damage scales with Life/ES pool (70% of each per second)
2. **Life is a damage stat** - Every point of life increases RF damage by 0.7 DPS
3. **No speed scaling** - RF is instant cast, DoT doesn't scale with cast speed
4. **No crit scaling** - Burning damage cannot crit
5. **Fire DoT Multi is king** - Most efficient damage multiplier after life/ES
6. **Must sustain degen** - RF deals 90% of life + 70% of ES as self-degen per second

## Example Build Priorities

For a typical RF Chieftain:
- Target: 7000+ life
- Target: 1500+ ES (if hybrid)
- Target: 100+ Fire DoT Multi
- Target: 85%+ max fire resist (to reduce self-degen)
- Target: 5%+ life regen per second (to sustain RF)

**Expected RF DPS at these stats:**
```
Base = 0.70 × 7000 + 0.70 × 1500 = 4900 + 1050 = 5950
With 200% inc damage + 100% DoT Multi:
DPS = 5950 × (1 + 2.0) × (1 + 1.0) = 5950 × 3 × 2 = 35,700 DPS
```

## References

- PoB Skill Definition: `PathOfBuilding/src/Data/Skills/act_int.lua` line 15201
- PoB DoT Calculation: `PathOfBuilding/src/Modules/CalcOffence.lua` line 5400+
- Our Implementation: `pob_neural_network/utils/skill_scaling_analyzer.py`
- Test Script: `pob_neural_network/test_rf_scaling.py`
