# Scaling Vector Visualization Guide

## Overview

This system provides **10 different visualization types** to explore high-dimensional skill scaling vectors, including techniques for visualizing data with **10+ dimensions** effectively.

## ✅ Generated Visualizations

### Static Visualizations (PNG)
Located in `visualizations/output/`:

1. **01_radar_chart.png** - Compare 10 dimensions across 6 skills simultaneously
2. **02_heatmap.png** - Matrix view of skill-stat relationships (6×18 = 108 data points)
3. **03_parallel_coordinates.png** - Multi-dimensional patterns across 8 dimensions
4. **04_diminishing_returns_rf.png** - 4 stat types showing value ceilings
5. **05_stat_ceilings.png** - Realistic investment limits per skill
6. **06_allocation_flow_rf.png** - Nested pie chart showing point distribution

### Interactive Visualizations (HTML)
Located in `visualizations/output/` - **Open in web browser!**

1. **interactive_01_3d_scatter.html** - 5D visualization (X, Y, Z, Color, Size)
2. **interactive_02_sunburst_rf.html** - Hierarchical scaling breakdown
3. **interactive_03_bar_comparison.html** - Grouped bar comparison with toggle
4. **interactive_04_diminishing_surface.html** - 3D surface showing stat interactions

## Techniques for Visualizing High-Dimensional Data

### Problem: Skill scaling vectors have 10+ dimensions

**Example dimensions for Righteous Fire:**
1. Life scaling (damage stat!)
2. ES scaling (damage stat!)
3. Fire damage
4. Burning damage
5. Elemental damage
6. Area damage
7. Spell damage
8. DoT multiplier
9. Fire DoT multiplier
10. Generic damage
11. Defensive priorities (7 sub-dimensions)
12. Speed type (cast/attack/none)
13. Crit scaling (yes/no + 5 sub-types)
14. Duration scaling
15. Area scaling
16. Projectile scaling

**Total: 20+ dimensions!** Cannot visualize in standard 2D/3D.

### Solutions Implemented

#### 1. **Radar Charts** - Circular Multi-Axis
**Handles:** 5-15 dimensions comfortably

Each axis radiates from center, skills form different shapes:
- **RF:** Large in Life/Fire, flat in Crit/Speed (spiky shape)
- **BV:** Round shape (benefits from many stats)
- **Lightning Strike:** Spiky in Attack/Lightning/Speed

**When to use:** Quick comparison of scaling patterns

---

#### 2. **Heatmaps** - Color-Encoded Matrix
**Handles:** 100+ data points (M skills × N stats)

Color intensity = relevance:
- 🟥 Red (1.0): Critical - must invest
- 🟨 Yellow (0.5): Good - moderate investment
- 🟩 Green (0.2): Minor - low priority
- ⬛ Dark (0.0): Useless - skip entirely

**When to use:** Comparing many skills × many stats at once

---

#### 3. **Parallel Coordinates** - Connected Dimensions
**Handles:** 5-10 dimensions with relationships

Each vertical line = dimension, horizontal lines = skills:
- **Parallel lines:** Similar scaling
- **Crossing lines:** Different priorities
- **Flat sections:** Dimension doesn't apply

**When to use:** Understanding multi-dimensional patterns

---

#### 4. **Dimensionality Reduction via Prioritization**
**Handles:** Reduce 20+ dimensions → Top 10

Only show dimensions with highest variance/importance:
- RF: Show Life, Fire, DoT (skip Crit, Attack, Cold, etc.)
- BV: Show Spell, Physical, Cast Speed, Crit (skip Life scaling)

**When to use:** Focusing on what matters per skill

---

#### 5. **3D Scatter + Extra Dimensions**
**Handles:** 5 dimensions (X, Y, Z, Color, Size)

Example mapping:
- X-axis: Damage focus (0-1)
- Y-axis: Speed focus (0-1)
- Z-axis: Defense priority (0-1)
- Color: Damage type (Fire=Red, Cold=Blue, etc.)
- Size: Crit scaling (Large=Yes, Small=No)

**When to use:** Exploring clustering and outliers

---

#### 6. **Hierarchical Visualization (Sunburst)**
**Handles:** 3-4 levels of nesting

```
Center: Righteous Fire
├─ Ring 1: Damage (40%)
│  ├─ Fire Damage (15%)
│  ├─ Burning Damage (15%)
│  └─ DoT Multi (10%)
├─ Ring 2: Defense (35%)
│  ├─ Life (25%)
│  └─ Resists (10%)
└─ Ring 3: Utility (25%)
```

**When to use:** Understanding stat hierarchies

---

#### 7. **Small Multiples** - Multiple Charts
**Handles:** Unlimited dimensions (1 chart per dimension group)

Create 4 separate charts for:
- Damage types (Fire, Cold, Lightning, Physical)
- Speed types (Cast, Attack, None)
- Defensive priorities (Life, ES, Armour, Evasion)
- Mechanics (Crit, Duration, Area, Projectile)

**When to use:** Deep analysis of specific dimension groups

---

#### 8. **3D Surfaces** - Interaction Effects
**Handles:** 3 dimensions showing relationships

Shows how 2 stats combine to affect output:
- X: Increased Damage (0-400%)
- Y: DoT Multiplier (0-150%)
- Z: Effective DPS

Reveals:
- **Linear regions:** Independent scaling
- **Curved regions:** Synergistic effects
- **Flat regions:** Diminishing returns

**When to use:** Understanding stat value ceilings and optimal ratios

---

#### 9. **Interactive Filtering**
**Handles:** Any number of dimensions via progressive disclosure

User controls which dimensions to show:
- Click skill → Hide non-relevant stats
- Click stat → Show only skills that use it
- Hover → See exact values
- Toggle → Compare specific skills

**When to use:** Exploratory analysis

---

#### 10. **Composite Metrics**
**Handles:** Reduce dimensions via weighted combinations

Create composite scores:
- **DPS Potential** = f(damage types, speed, crit)
- **Defense Rating** = f(life, ES, resists, mitigation)
- **Investment Efficiency** = f(stat ceiling, marginal returns)

Then visualize these 3 composites instead of 20+ raw dimensions.

**When to use:** High-level decision making

---

## Key Insights from Visualizations

### 1. Radar Chart Reveals
- **RF is an outlier:** Only skill where Life spike matches Damage spike
- **BV vs Ice Spear:** Both spells, but BV lacks Crit spike (lower priority)
- **Attack vs Spell:** Clear separation - no overlap in Attack/Spell dimensions

### 2. Heatmap Reveals
- **RF Life nodes:** 1.00 (unique!) vs 0.40 for all other skills
- **DoT Multi:** 1.00 for RF/Toxic Rain, 0.00 for others
- **Crit nodes:** Binary - either 0.90 or 0.00 (no medium values)

### 3. Parallel Coordinates Reveals
- **RF and Toxic Rain:** Parallel in DoT dimension but diverge on Life
- **All spells:** Converge at Cast Speed dimension
- **Crossing at Defense:** Different survivability strategies

### 4. Diminishing Returns Reveals
- **Increased Damage:** Linear until 200%, then steep curve
- **DoT Multi:** High efficiency up to 100%, wasteful beyond 150%
- **More Multipliers:** Exponential falloff - each layer weaker
- **Crit:** Threshold at 50% chance + 350% multi for break-even

### 5. Stat Ceilings Reveal
- **RF Life ceiling:** 250% (highest) because it's a damage stat
- **Generic Damage ceiling:** 300% across all skills (consistent)
- **Speed ceiling:** 150% for speed-scaling skills, 0% for DoT
- **Crit ceiling:** 600% (chance + multi) for crit skills, 0% for DoT

### 6. Allocation Flow Reveals
- **RF:** 35% Life → 40% Fire Damage → 20% Defense → 5% Utility
- **Crit spell:** 25% Life → 35% Damage → 25% Crit → 15% Speed
- **Attack:** 30% Life → 40% Attack Damage → 20% Speed → 10% Defense

### 7. 3D Scatter Reveals
- **Clustering:** Spells cluster (high Speed, low Defense)
- **RF isolation:** High Defense, zero Speed (unique position)
- **Crit dimension:** Clear separation (large vs small markers)

### 8. Sunburst Reveals
- **Top-level split:** All skills prioritize Damage > Defense > Speed
- **Sub-category variance:** RF Fire > Burning > DoT, BV Physical > Spell
- **Utility always small:** 5-10% regardless of skill

### 9. Interactive Bars Reveal
- **Life:** Uniform except RF (2.5× higher)
- **Speed:** Binary - 80% or 0%
- **Crit:** Binary - 90% or 0%
- **Damage:** Gradual variation (70-100%)

### 10. 3D Surface Reveals
- **Flat plateau:** Beyond 300% damage + 100% multi = no benefit
- **Steep slopes:** 0-150% damage = huge gains
- **Optimal ratio:** 2:1 increased damage to DoT multi

---

## Mathematical Explanation of Diminishing Returns

### Why Stats Have Ceilings

**Increased Damage (Additive):**
```
DPS = Base × (1 + IncreasedDamage/100)

0% → 100%: DPS doubles (100% gain)
100% → 200%: DPS goes 2× → 3× (50% gain)
200% → 300%: DPS goes 3× → 4× (33% gain)
300% → 400%: DPS goes 4× → 5× (25% gain)
```
**Each 100% gives progressively less benefit!**

**More Multipliers (Multiplicative):**
```
40% More × 40% More = 1.4 × 1.4 = 1.96× (not 1.8×!)

First 40%: +40% DPS
Second 40%: +40% of 1.4× = +56% total
Third 40%: +40% of 1.96× = +78% total
```
**Stack multiplicatively but opportunity cost increases!**

**Critical Strike (Conditional):**
```
EffectiveDPS = Base × (1 + CritChance × (CritMulti - 1))

5% chance × 150% multi: +2.5% DPS
50% chance × 350% multi: +125% DPS (break-even)
95% chance × 500% multi: +380% DPS (optimal)
```
**Requires heavy investment in BOTH chance AND multi!**

**DoT Multiplier (Additive with Increased):**
```
Total Multi = IncreasedDamage + DotMulti

100% Inc + 50% DoT = 150% total
150% Inc + 100% DoT = 250% total
```
**Competes with increased damage in same bucket!**

### Optimal Investment Strategy

Based on visualizations:

1. **First 100 points:**
   - 40% Life (defense + RF damage scaling)
   - 40% Main damage type (fire/cold/lightning/physical)
   - 20% Speed/Crit/DoT (whatever applies)

2. **Next 50 points:**
   - 60% Continue main damage type
   - 40% Defensive layers (resists, mitigation)

3. **Final 50 points:**
   - 50% Generic damage (running out of specific)
   - 30% Utility (area, duration, movement)
   - 20% More defense (life regen, recovery)

**Why this works:**
- Early points hit high-efficiency zones
- Diversification prevents diminishing returns
- Defensive investment prevents one-shots

---

## Usage Examples

### Compare Skills
```python
from visualizations.scaling_vector_visualizer import ScalingVectorVisualizer

viz = ScalingVectorVisualizer()

skills = ['Righteous Fire', 'Blade Vortex', 'Lightning Strike']

# Radar chart - overall comparison
viz.create_radar_chart(skills, save_path='comparison.png')

# Heatmap - detailed stat matrix
viz.create_heatmap(skills, save_path='heatmap.png')

# Parallel coordinates - pattern discovery
viz.create_parallel_coordinates(skills, save_path='patterns.png')
```

### Analyze One Skill
```python
# Diminishing returns
viz.create_diminishing_returns_curves('Righteous Fire', save_path='rf_returns.png')

# Ideal allocation
viz.create_node_allocation_flow('Righteous Fire', node_budget=100, save_path='rf_allocation.png')

# Stat ceilings
viz.create_stat_ceiling_chart(['Righteous Fire'], save_path='rf_ceilings.png')
```

### Interactive Exploration
```python
from visualizations.interactive_visualizer import Interactive3DVisualizer

viz = Interactive3DVisualizer()

# 3D scatter (opens in browser)
fig = viz.create_3d_scatter(skills)
fig.show()

# Sunburst drill-down
fig = viz.create_sunburst_chart('Righteous Fire')
fig.show()

# 3D surface
fig = viz.create_diminishing_returns_surface('Righteous Fire')
fig.show()
```

---

## Conclusion

We've implemented **10 visualization techniques** to handle **20+ dimensional** skill scaling vectors:

✅ Radar Charts (10 dimensions)
✅ Heatmaps (108 data points)
✅ Parallel Coordinates (8 dimensions)
✅ 3D Scatter + Color + Size (5 dimensions)
✅ Hierarchical Sunburst (3-4 levels)
✅ Diminishing Returns Curves (stat ceilings)
✅ Stat Ceiling Comparisons
✅ Node Allocation Flow
✅ Interactive Bars (filterable)
✅ 3D Surfaces (interaction effects)

**Key techniques for >3D visualization:**
1. **Encode extra dimensions:** Color, size, shape, opacity
2. **Hierarchical nesting:** Sunburst, treemaps
3. **Multiple views:** Small multiples, linked charts
4. **Dimensionality reduction:** Show top N, composite metrics
5. **Interactive filtering:** Progressive disclosure
6. **Animation:** Time as extra dimension
7. **Parallel coordinates:** N-dimensional line plots

All visualizations successfully generated and saved! Open the HTML files in your browser for interactive exploration.
