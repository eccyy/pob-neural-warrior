# Scaling Vector Visualizations

This directory contains tools for visualizing high-dimensional skill scaling vectors and understanding how different stats interact.

## Visualization Types

### 1. Radar Charts (`scaling_vector_visualizer.py`)
**Best for:** Comparing 5-10 dimensions at once across multiple skills

Shows scaling priorities in a circular layout. Each axis represents a different stat type (Life, Fire Damage, Cast Speed, etc.). Different skills form different shapes.

**Example use:**
- Quickly see that RF prioritizes Life/Fire while BV prioritizes Spell/Physical
- Identify which skills have similar scaling patterns

### 2. Heatmaps (`scaling_vector_visualizer.py`)
**Best for:** Showing which skills scale with which stats

Matrix view with skills on Y-axis, stat types on X-axis, and color intensity showing relevance (0=irrelevant, 1=critical).

**Example use:**
- See at a glance that RF has 1.00 for Life and Fire DoT Multi
- Identify that Crit nodes are 0.00 for RF but 0.90 for Ice Spear

### 3. Parallel Coordinates (`scaling_vector_visualizer.py`)
**Best for:** Visualizing multi-dimensional patterns

Each vertical line is a dimension, horizontal lines connect a skill's values across all dimensions.

**Example use:**
- See how RF has high Life but zero Crit
- Trace a skill's journey from Life → Damage → Speed → Crit

### 4. Diminishing Returns Curves (`scaling_vector_visualizer.py`)
**Best for:** Understanding stat value ceilings

Shows how damage increases with stat investment and where diminishing returns kick in.

**Example use:**
- See that first 150% increased damage gives 2.5x DPS
- Beyond 300% damage, each 1% gives minimal benefit
- Identify efficient investment zones (highlighted in green)

### 5. Stat Ceiling Charts (`scaling_vector_visualizer.py`)
**Best for:** Understanding realistic investment limits

Bar chart showing practical maximum for each stat type per skill.

**Example use:**
- RF can invest 250% in Life (it's damage!), others only 200%
- DoT skills can get 100% DoT Multi, non-DoT gets 0%

### 6. Node Allocation Flow (`scaling_vector_visualizer.py`)
**Best for:** Understanding point distribution

Nested pie chart (sunburst style) showing how 100 passive points should be allocated.

**Example use:**
- RF should allocate 35 points to Life/Defense, 40 to Fire Damage
- Crit builds allocate 20 points to Crit, RF allocates 0

### 7. Interactive 3D Scatter (`interactive_visualizer.py`)
**Best for:** Exploring relationships between multiple dimensions

3D scatter plot where:
- X-axis = Damage focus
- Y-axis = Speed focus  
- Z-axis = Defense priority
- Color = Damage type
- Size = Crit scaling

**Example use:**
- Hover over skills to see all details
- Rotate view to see clustering patterns
- Identify outliers (RF with high defense focus)

### 8. Sunburst Charts (`interactive_visualizer.py`)
**Best for:** Hierarchical breakdown of scaling

Interactive circular chart with levels:
- Center: Skill name
- Ring 1: Major categories (Damage, Defense, Speed, etc.)
- Ring 2: Specific stats

**Example use:**
- Click to zoom into categories
- See exact percentage breakdown
- Understand stat hierarchy

### 9. Interactive Bar Charts (`interactive_visualizer.py`)
**Best for:** Direct stat comparison

Grouped bar chart comparing all skills across major stat types.

**Example use:**
- Click legend to hide/show stats
- Hover for exact percentages
- Export for presentations

### 10. 3D Diminishing Returns Surface (`interactive_visualizer.py`)
**Best for:** Understanding stat interaction effects

3D surface showing DPS as a function of two stats (e.g., Increased Damage × DoT Multi).

**Example use:**
- See how combining stats creates synergy
- Identify optimal stat ratios
- Understand why balanced investment beats stacking one stat

## Handling High-Dimensional Data

Since scaling vectors have 10+ dimensions, we use multiple techniques:

### Dimensionality Reduction
1. **Grouping:** Combine related stats (all fire damage types → Fire)
2. **Prioritization:** Show top 5-10 most important dimensions
3. **Filtering:** Skip zero-value dimensions (e.g., hide Crit for RF)

### Multiple Views
1. **Overview:** Radar chart shows all dimensions at once
2. **Detail:** Heatmap shows exact values
3. **Relationships:** Parallel coordinates show connections
4. **Deep Dive:** 3D plots explore specific dimension combinations

### Interactive Exploration
1. **Hover:** See exact values without cluttering display
2. **Click:** Drill down into categories
3. **Rotate:** Change perspective on 3D data
4. **Toggle:** Show/hide specific skills or stats

## Usage

### Generate Static Visualizations (PNG)
```bash
cd visualizations
python scaling_vector_visualizer.py
```

Output: 6 PNG files in `visualizations/output/`:
1. `01_radar_chart.png`
2. `02_heatmap.png`
3. `03_parallel_coordinates.png`
4. `04_diminishing_returns_rf.png`
5. `05_stat_ceilings.png`
6. `06_allocation_flow_rf.png`

### Generate Interactive Visualizations (HTML)
```bash
cd visualizations
python interactive_visualizer.py
```

Output: 4 HTML files in `visualizations/output/`:
1. `interactive_01_3d_scatter.html` - 3D scatter plot
2. `interactive_02_sunburst_rf.html` - Hierarchical breakdown
3. `interactive_03_bar_comparison.html` - Bar chart comparison
4. `interactive_04_diminishing_surface.html` - 3D surface plot

Open HTML files in any web browser for interactive exploration!

### Programmatic Use
```python
from visualizations.scaling_vector_visualizer import ScalingVectorVisualizer

visualizer = ScalingVectorVisualizer()

# Compare multiple skills
skills = ['Righteous Fire', 'Blade Vortex', 'Ice Spear']
fig = visualizer.create_radar_chart(skills)
plt.show()

# Analyze one skill in depth
fig = visualizer.create_diminishing_returns_curves('Righteous Fire')
plt.show()

# Show ideal point allocation
fig = visualizer.create_node_allocation_flow('Righteous Fire', node_budget=100)
plt.show()
```

### Interactive Exploration
```python
from visualizations.interactive_visualizer import Interactive3DVisualizer

visualizer = Interactive3DVisualizer()

# 3D scatter (X=Damage, Y=Speed, Z=Defense, Color=Type, Size=Crit)
fig = visualizer.create_3d_scatter(skills)
fig.show()  # Opens in browser

# Sunburst hierarchy
fig = visualizer.create_sunburst_chart('Righteous Fire')
fig.show()

# 3D diminishing returns surface
fig = visualizer.create_diminishing_returns_surface('Righteous Fire')
fig.show()
```

## Dependencies

### Required
```bash
pip install matplotlib seaborn numpy plotly
```

### For Jupyter Notebooks
```bash
pip install jupyter plotly-orca kaleido
```

## Key Insights from Visualizations

### Righteous Fire
- **Life nodes:** 1.00 relevance (unique - life is damage!)
- **Fire DoT Multi:** 1.00 relevance (strongest multiplier)
- **Crit nodes:** 0.00 relevance (DoT can't crit)
- **Cast Speed:** 0.00 relevance (instant cast, no speed scaling)
- **Optimal allocation:** 35% Life, 40% Fire Damage, 20% Defense, 5% Utility

### Blade Vortex
- **Spell/Physical:** 0.70 relevance
- **Cast Speed:** 0.80 relevance (scales DPS)
- **Crit:** 0.90 relevance (benefits from crit)
- **Life:** 0.40 relevance (just defense)
- **Optimal allocation:** 25% Life, 45% Damage, 20% Crit, 10% Speed

### Lightning Strike
- **Attack/Lightning:** 0.70 relevance
- **Attack Speed:** 0.80 relevance
- **Crit:** 0.60 relevance (can crit but not primary)
- **Fire:** 0.00 relevance (lightning skill)
- **Optimal allocation:** 30% Life, 40% Lightning Damage, 20% Speed, 10% Crit

## Interpretation Guide

### Radar Charts
- **Larger area:** More versatile scaling (benefits from more stats)
- **Spiky shape:** Specialized (only benefits from specific stats)
- **Round shape:** Generalist (benefits from many stats equally)

### Heatmaps
- **Red (1.0):** Critical stat - must invest heavily
- **Yellow (0.5):** Good stat - invest moderately
- **Green (0.2):** Minor stat - low priority
- **Dark (0.0):** Useless stat - skip completely

### Parallel Coordinates
- **Parallel lines:** Similar scaling patterns
- **Crossing lines:** Different priorities
- **Flat sections:** Dimension doesn't apply to that skill

### Diminishing Returns
- **Green zone (0-40%):** High efficiency, invest here first
- **Yellow zone (40-80%):** Medium efficiency, diminishing returns starting
- **Red zone (80%+):** Low efficiency, heavy diminishing returns

### Stat Ceilings
- **High bar:** Can invest heavily before diminishing returns
- **Low bar:** Hit ceiling quickly, diversify instead
- **Zero bar:** Don't invest at all (e.g., Crit for RF)

## Advanced: Creating Custom Visualizations

```python
# Custom radar chart with your own dimensions
def create_custom_radar(skill_name: str):
    visualizer = ScalingVectorVisualizer()
    scaling = visualizer.analyzer.analyze_skill(skill_name)
    
    # Define your own dimensions
    custom_dimensions = [
        ('Life', check_life_scaling(scaling)),
        ('Main Damage', check_main_damage(scaling)),
        ('Speed', check_speed_scaling(scaling)),
        # ... add more
    ]
    
    # Plot custom radar
    # ... implementation

# Custom heatmap with specific nodes
def create_node_heatmap(skill_names: List[str], node_names: List[str]):
    # Calculate relevance for each skill-node combination
    # Plot as heatmap
    # ... implementation
```

## Tips for Effective Visualization

1. **Choose the right tool:**
   - Comparing skills: Radar, Heatmap, Bar Chart
   - Understanding one skill: Sunburst, Allocation Flow
   - Finding limits: Diminishing Returns, Stat Ceilings
   - Exploring relationships: 3D Scatter, Parallel Coordinates

2. **Layer information:**
   - Start with overview (Radar/Heatmap)
   - Drill into specifics (Sunburst)
   - Validate with numbers (Interactive Bar Chart)

3. **Use interactivity:**
   - Static images for reports/documentation
   - Interactive HTML for exploration/analysis
   - Jupyter notebooks for iterative development

4. **Combine views:**
   - Show Radar + Heatmap side-by-side
   - Link 3D scatter with detailed sunburst
   - Animate transitions between states

## Future Enhancements

- [ ] t-SNE/UMAP dimensionality reduction to 2D
- [ ] Network graphs showing stat dependencies
- [ ] Animated transitions showing skill evolution
- [ ] Real-time updates as build changes
- [ ] Integration with PoB XML to show current build
- [ ] Sankey diagrams showing point flow
- [ ] Chord diagrams showing stat synergies
