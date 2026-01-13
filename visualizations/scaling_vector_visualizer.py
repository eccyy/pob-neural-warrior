"""
Scaling Vector Visualization System
Provides multiple visualization methods for high-dimensional skill scaling data
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.skill_scaling_analyzer import SkillScalingAnalyzer, ScalingVector


class ScalingVectorVisualizer:
    """
    Visualizes skill scaling vectors using multiple techniques:
    1. Radar charts - Compare overall scaling priorities
    2. Heatmaps - Show skill-stat relationships
    3. Parallel coordinates - Show multi-dimensional patterns
    4. Sankey diagrams - Show scaling flow from skill to stats
    5. Diminishing returns curves - Show stat value ceilings
    """
    
    def __init__(self):
        self.analyzer = SkillScalingAnalyzer()
        self.colors = {
            'Righteous Fire': '#FF4444',
            'Blade Vortex': '#8844FF',
            'Lightning Strike': '#4488FF',
            'Ice Spear': '#44CCFF',
            'Toxic Rain': '#44FF44',
            'Cyclone': '#FFAA44',
        }
    
    def create_radar_chart(self, skills: List[str], save_path: str = None):
        """
        Radar chart comparing scaling priorities across skills
        Good for: Comparing 5-10 dimensions at once
        """
        print("\n1. Creating Radar Chart...")
        
        # Define dimensions to compare
        categories = [
            'Life Scaling',
            'ES Scaling',
            'Speed Scaling',
            'Crit Scaling',
            'Fire Damage',
            'Cold Damage',
            'Lightning Damage',
            'Physical Damage',
            'Area Scaling',
            'Duration Scaling'
        ]
        
        fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection='polar'))
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        
        for skill in skills:
            scaling = self.analyzer.analyze_skill(skill)
            values = self._extract_radar_values(scaling)
            values += values[:1]  # Complete the circle
            
            color = self.colors.get(skill, '#888888')
            ax.plot(angles, values, 'o-', linewidth=2, label=skill, color=color)
            ax.fill(angles, values, alpha=0.15, color=color)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=10)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], size=8)
        ax.grid(True, linestyle='--', alpha=0.3)
        
        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
        plt.title('Skill Scaling Vector Comparison\n(Radar Chart)', 
                  size=14, weight='bold', pad=20)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_heatmap(self, skills: List[str], save_path: str = None):
        """
        Heatmap showing which stats scale which skills
        Good for: Showing many skills × many stats at once
        """
        print("\n2. Creating Heatmap...")
        
        # Define stat categories
        stat_types = [
            'Life', 'ES', 'Fire', 'Cold', 'Lightning', 'Physical', 'Chaos',
            'Cast Speed', 'Attack Speed', 'Crit Chance', 'Crit Multi',
            'Fire DoT Multi', 'Area', 'Duration', 'Projectile',
            'Spell Damage', 'Attack Damage', 'Elemental'
        ]
        
        # Build matrix
        matrix = np.zeros((len(skills), len(stat_types)))
        
        for i, skill in enumerate(skills):
            scaling = self.analyzer.analyze_skill(skill)
            for j, stat in enumerate(stat_types):
                matrix[i, j] = self._get_stat_relevance(scaling, stat)
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(14, 8))
        
        sns.heatmap(matrix, 
                    xticklabels=stat_types,
                    yticklabels=skills,
                    cmap='RdYlGn',
                    vmin=0, vmax=1,
                    annot=True,
                    fmt='.2f',
                    cbar_kws={'label': 'Scaling Relevance (0=None, 1=Critical)'},
                    linewidths=0.5,
                    ax=ax)
        
        plt.title('Skill-Stat Scaling Heatmap\n(Which stats scale which skills)', 
                  size=14, weight='bold', pad=20)
        plt.xlabel('Stat Types', size=12, weight='bold')
        plt.ylabel('Skills', size=12, weight='bold')
        plt.xticks(rotation=45, ha='right')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_parallel_coordinates(self, skills: List[str], save_path: str = None):
        """
        Parallel coordinates showing multi-dimensional patterns
        Good for: Seeing how multiple variables relate across skills
        """
        print("\n3. Creating Parallel Coordinates...")
        
        dimensions = [
            'Life Priority',
            'ES Priority',
            'Fire Damage',
            'Speed',
            'Crit',
            'DoT Focus',
            'Area',
            'Defense'
        ]
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Normalize x positions
        x = np.arange(len(dimensions))
        
        for skill in skills:
            scaling = self.analyzer.analyze_skill(skill)
            values = self._extract_parallel_values(scaling)
            
            color = self.colors.get(skill, '#888888')
            ax.plot(x, values, 'o-', linewidth=2.5, label=skill, 
                   color=color, alpha=0.8, markersize=8)
        
        ax.set_xticks(x)
        ax.set_xticklabels(dimensions, rotation=45, ha='right', size=11)
        ax.set_ylim(-0.05, 1.05)
        ax.set_ylabel('Scaling Priority (0=None, 1=Critical)', size=12, weight='bold')
        ax.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax.legend(loc='upper left', fontsize=11, framealpha=0.9)
        
        plt.title('Multi-Dimensional Scaling Patterns\n(Parallel Coordinates)', 
                  size=14, weight='bold', pad=20)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_diminishing_returns_curves(self, skill: str, save_path: str = None):
        """
        Show diminishing returns for different stat types
        Good for: Understanding stat value ceilings/caps
        """
        print(f"\n4. Creating Diminishing Returns Curves for {skill}...")
        
        scaling = self.analyzer.analyze_skill(skill)
        
        # Define stat ranges to test
        stat_ranges = {
            'Increased Damage': (0, 500),  # 0% to 500%
            'DoT Multiplier': (0, 200),    # 0% to 200%
            'More Multiplier': (0, 200),   # 0% to 200% (multiplicative stacks)
            'Critical Strike': (0, 100),   # 0% to 100%
        }
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        for idx, (stat_name, (min_val, max_val)) in enumerate(stat_ranges.items()):
            ax = axes[idx]
            
            # Calculate effective damage at each stat level
            stat_values = np.linspace(min_val, max_val, 100)
            damage_multipliers = []
            marginal_returns = []
            
            for stat in stat_values:
                mult = self._calculate_damage_multiplier(stat, stat_name, scaling)
                damage_multipliers.append(mult)
                
                # Marginal return: how much does +1% stat increase damage?
                if len(damage_multipliers) > 1:
                    marginal = damage_multipliers[-1] - damage_multipliers[-2]
                    marginal_returns.append(marginal)
                else:
                    marginal_returns.append(0)
            
            # Plot damage curve
            color = self.colors.get(skill, '#888888')
            ax.plot(stat_values, damage_multipliers, linewidth=2.5, color=color)
            ax.fill_between(stat_values, damage_multipliers, alpha=0.2, color=color)
            
            # Add reference lines
            ax.axhline(y=damage_multipliers[0] * 2, color='red', 
                      linestyle='--', alpha=0.5, linewidth=1.5, label='2x base damage')
            ax.axhline(y=damage_multipliers[0] * 3, color='orange', 
                      linestyle='--', alpha=0.5, linewidth=1.5, label='3x base damage')
            
            # Mark efficiency zones
            efficient_zone = max_val * 0.4
            ax.axvspan(0, efficient_zone, alpha=0.1, color='green', 
                      label='High efficiency')
            ax.axvspan(efficient_zone, max_val, alpha=0.1, color='yellow', 
                      label='Diminishing returns')
            
            ax.set_xlabel(f'{stat_name} (%)', size=11, weight='bold')
            ax.set_ylabel('Damage Multiplier', size=11, weight='bold')
            ax.set_title(f'{stat_name} Scaling', size=12, weight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, loc='best')
        
        plt.suptitle(f'Diminishing Returns Analysis: {skill}\n' + 
                    '(Shows how stat effectiveness decreases with investment)',
                    size=14, weight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_stat_ceiling_chart(self, skills: List[str], save_path: str = None):
        """
        Bar chart showing realistic stat ceilings for each skill
        Good for: Understanding practical limits of stat investment
        """
        print("\n5. Creating Stat Ceiling Chart...")
        
        stat_categories = ['Life', 'Damage', 'Speed', 'Crit', 'DoT Multi']
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(skills))
        width = 0.15
        
        for i, stat in enumerate(stat_categories):
            ceilings = []
            for skill in skills:
                scaling = self.analyzer.analyze_skill(skill)
                ceiling = self._estimate_stat_ceiling(scaling, stat)
                ceilings.append(ceiling)
            
            offset = (i - len(stat_categories)/2) * width
            ax.bar(x + offset, ceilings, width, label=stat, alpha=0.8)
        
        ax.set_xlabel('Skills', size=12, weight='bold')
        ax.set_ylabel('Realistic Stat Ceiling (%)', size=12, weight='bold')
        ax.set_title('Realistic Stat Investment Ceilings by Skill\n' + 
                    '(Maximum efficient investment before heavy diminishing returns)',
                    size=14, weight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(skills, rotation=45, ha='right')
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, axis='y', alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_node_allocation_flow(self, skill: str, node_budget: int = 100, 
                                   save_path: str = None):
        """
        Sankey-style diagram showing how points flow from budget to stat categories
        Good for: Understanding point distribution priorities
        """
        print(f"\n6. Creating Node Allocation Flow for {skill}...")
        
        scaling = self.analyzer.analyze_skill(skill)
        
        # Estimate ideal point distribution
        allocations = self._estimate_node_allocation(scaling, node_budget)
        
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Create nested pie charts (sunburst-style)
        # Inner circle: Major categories
        # Outer circle: Specific stats
        
        major_cats = list(allocations.keys())
        major_sizes = [sum(allocations[cat].values()) for cat in major_cats]
        major_colors = plt.cm.Set3(np.linspace(0, 1, len(major_cats)))
        
        # Inner pie
        wedges, texts, autotexts = ax.pie(major_sizes, 
                                          labels=major_cats,
                                          autopct='%1.1f%%',
                                          colors=major_colors,
                                          radius=0.7,
                                          wedgeprops=dict(width=0.3, edgecolor='white'),
                                          textprops={'size': 11, 'weight': 'bold'})
        
        # Outer pie (detailed stats)
        detailed_labels = []
        detailed_sizes = []
        detailed_colors = []
        
        for cat_idx, (cat, stats) in enumerate(allocations.items()):
            for stat_name, points in stats.items():
                detailed_labels.append(f"{stat_name}\n({points} pts)")
                detailed_sizes.append(points)
                # Use lighter shade of parent color
                color = np.array(major_colors[cat_idx])
                detailed_colors.append(color)
        
        wedges2, texts2 = ax.pie(detailed_sizes,
                                labels=detailed_labels,
                                colors=detailed_colors,
                                radius=1.0,
                                wedgeprops=dict(width=0.3, edgecolor='white'),
                                textprops={'size': 8})[:2]
        
        ax.set_title(f'Ideal Point Allocation: {skill}\n' + 
                    f'(Total: {node_budget} points)',
                    size=14, weight='bold', pad=20)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    # Helper methods for extracting values
    
    def _extract_radar_values(self, scaling: ScalingVector) -> List[float]:
        """Extract values for radar chart"""
        increased_types = [x.lower() for x in scaling.increased_damage_types]
        
        life_scaling = 1.0 if any('life' in x for x in increased_types[:5]) else 0.3
        es_scaling = 1.0 if any('energy_shield' in x or 'es' in x for x in increased_types[:5]) else 0.2
        speed_scaling = 0.8 if scaling.speed_type != 'none' else 0.0
        crit_scaling = 0.9 if scaling.scales_with_crit else 0.0
        fire_scaling = 0.9 if 'fire' in scaling.tags else 0.0
        cold_scaling = 0.9 if 'cold' in scaling.tags else 0.0
        lightning_scaling = 0.9 if 'lightning' in scaling.tags else 0.0
        physical_scaling = 0.9 if 'physical' in scaling.tags else 0.0
        area_scaling = 0.7 if scaling.area_scaling else 0.0
        duration_scaling = 0.7 if scaling.duration_scaling else 0.0
        
        return [life_scaling, es_scaling, speed_scaling, crit_scaling,
                fire_scaling, cold_scaling, lightning_scaling, physical_scaling,
                area_scaling, duration_scaling]
    
    def _get_stat_relevance(self, scaling: ScalingVector, stat: str) -> float:
        """Get relevance of a stat for a skill"""
        stat_lower = stat.lower()
        increased_types = [x.lower() for x in scaling.increased_damage_types]
        
        if stat_lower == 'life':
            return 1.0 if any('life' in x for x in increased_types[:5]) else 0.4
        elif stat_lower == 'es':
            return 1.0 if any('energy' in x for x in increased_types[:5]) else 0.3
        elif stat_lower in ['fire', 'cold', 'lightning', 'physical', 'chaos']:
            return 0.9 if stat_lower in scaling.tags else 0.0
        elif stat_lower == 'cast speed':
            return 0.8 if scaling.speed_type == 'cast_speed' else 0.0
        elif stat_lower == 'attack speed':
            return 0.8 if scaling.speed_type == 'attack_speed' else 0.0
        elif 'crit' in stat_lower:
            return 0.9 if scaling.scales_with_crit else 0.0
        elif 'dot multi' in stat_lower:
            return 1.0 if 'dot' in scaling.tags else 0.1
        elif stat_lower == 'area':
            return 0.7 if scaling.area_scaling else 0.0
        elif stat_lower == 'duration':
            return 0.7 if scaling.duration_scaling else 0.0
        elif stat_lower == 'projectile':
            return 0.7 if scaling.projectile_scaling else 0.0
        elif stat_lower == 'spell damage':
            return 0.7 if 'spell' in scaling.tags else 0.0
        elif stat_lower == 'attack damage':
            return 0.7 if 'attack' in scaling.tags else 0.0
        elif stat_lower == 'elemental':
            return 0.6 if any(e in scaling.tags for e in ['fire', 'cold', 'lightning']) else 0.0
        
        return 0.0
    
    def _extract_parallel_values(self, scaling: ScalingVector) -> List[float]:
        """Extract values for parallel coordinates"""
        increased_types = [x.lower() for x in scaling.increased_damage_types]
        
        life = 1.0 if any('life' in x for x in increased_types[:5]) else 0.4
        es = 1.0 if any('energy' in x for x in increased_types[:5]) else 0.3
        fire = 0.9 if 'fire' in scaling.tags else 0.0
        speed = 0.8 if scaling.speed_type != 'none' else 0.0
        crit = 0.9 if scaling.scales_with_crit else 0.0
        dot = 0.9 if 'dot' in scaling.tags else 0.0
        area = 0.7 if scaling.area_scaling else 0.0
        defense = scaling.defensive_priority.get('life', 0.5)
        
        return [life, es, fire, speed, crit, dot, area, defense]
    
    def _calculate_damage_multiplier(self, stat_value: float, stat_name: str, 
                                    scaling: ScalingVector) -> float:
        """Calculate effective damage multiplier for a given stat investment"""
        base = 100  # Base damage
        
        if stat_name == 'Increased Damage':
            return base * (1 + stat_value / 100)
        elif stat_name == 'DoT Multiplier':
            if 'dot' in scaling.tags:
                return base * (1 + stat_value / 100)
            else:
                return base  # No benefit if not DoT skill
        elif stat_name == 'More Multiplier':
            # More multipliers stack multiplicatively with diminishing returns
            layers = int(stat_value / 40)  # Assume 40% more per layer
            mult = 1.0
            for i in range(layers):
                mult *= 1.4
            return base * mult
        elif stat_name == 'Critical Strike':
            if scaling.scales_with_crit:
                # Assume 150% base crit multi, scaling to 500%
                crit_multi = 1.5 + (stat_value / 100) * 3.5
                return base * (1 + (stat_value / 100) * (crit_multi - 1))
            else:
                return base  # No benefit if can't crit
        
        return base
    
    def _estimate_stat_ceiling(self, scaling: ScalingVector, stat: str) -> float:
        """Estimate realistic ceiling for a stat type"""
        stat_lower = stat.lower()
        
        if stat_lower == 'life':
            # RF gets more, others get standard
            return 250 if any('life' in x.lower() for x in scaling.increased_damage_types[:5]) else 200
        elif stat_lower == 'damage':
            return 300  # Typical increased damage ceiling
        elif stat_lower == 'speed':
            return 150 if scaling.speed_type != 'none' else 0
        elif stat_lower == 'crit':
            return 600 if scaling.scales_with_crit else 0  # Crit chance + multi
        elif stat_lower == 'dot multi':
            return 100 if 'dot' in scaling.tags else 0
        
        return 0
    
    def _estimate_node_allocation(self, scaling: ScalingVector, budget: int) -> Dict:
        """Estimate ideal point distribution"""
        increased_types = [x.lower() for x in scaling.increased_damage_types[:10]]
        
        # Major categories
        allocations = {
            'Life/Defense': {},
            'Damage': {},
            'Speed': {},
            'Crit': {},
            'Utility': {}
        }
        
        # Calculate priorities
        life_priority = 1.0 if any('life' in x for x in increased_types[:5]) else 0.6
        damage_priority = 1.0
        speed_priority = 0.8 if scaling.speed_type != 'none' else 0.0
        crit_priority = 0.9 if scaling.scales_with_crit else 0.0
        utility_priority = 0.5
        
        total_priority = life_priority + damage_priority + speed_priority + crit_priority + utility_priority
        
        # Distribute points
        life_points = int(budget * life_priority / total_priority)
        damage_points = int(budget * damage_priority / total_priority)
        speed_points = int(budget * speed_priority / total_priority)
        crit_points = int(budget * crit_priority / total_priority)
        utility_points = budget - (life_points + damage_points + speed_points + crit_points)
        
        # Break down into specifics
        if life_points > 0:
            allocations['Life/Defense']['Life Nodes'] = int(life_points * 0.7)
            allocations['Life/Defense']['Resist Nodes'] = int(life_points * 0.2)
            allocations['Life/Defense']['Defense Nodes'] = life_points - int(life_points * 0.9)
        
        if damage_points > 0:
            element = next((tag for tag in ['fire', 'cold', 'lightning', 'physical'] if tag in scaling.tags), 'generic')
            allocations['Damage'][f'{element.title()} Damage'] = int(damage_points * 0.6)
            if 'dot' in scaling.tags:
                allocations['Damage']['DoT Multi'] = int(damage_points * 0.4)
            else:
                allocations['Damage']['Generic Damage'] = damage_points - int(damage_points * 0.6)
        
        if speed_points > 0:
            speed_type = 'Cast Speed' if scaling.speed_type == 'cast_speed' else 'Attack Speed'
            allocations['Speed'][speed_type] = speed_points
        
        if crit_points > 0:
            allocations['Crit']['Crit Chance'] = int(crit_points * 0.4)
            allocations['Crit']['Crit Multi'] = crit_points - int(crit_points * 0.4)
        
        if utility_points > 0:
            allocations['Utility']['Area/Duration/Proj'] = utility_points
        
        return allocations


def generate_all_visualizations(output_dir: str = "visualizations/output"):
    """Generate all visualization types"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    visualizer = ScalingVectorVisualizer()
    
    skills = [
        'Righteous Fire',
        'Blade Vortex',
        'Lightning Strike',
        'Ice Spear',
        'Toxic Rain',
        'Cyclone'
    ]
    
    print("=" * 80)
    print("GENERATING SCALING VECTOR VISUALIZATIONS")
    print("=" * 80)
    
    # 1. Radar chart
    visualizer.create_radar_chart(
        skills, 
        save_path=f"{output_dir}/01_radar_chart.png"
    )
    
    # 2. Heatmap
    visualizer.create_heatmap(
        skills,
        save_path=f"{output_dir}/02_heatmap.png"
    )
    
    # 3. Parallel coordinates
    visualizer.create_parallel_coordinates(
        skills,
        save_path=f"{output_dir}/03_parallel_coordinates.png"
    )
    
    # 4. Diminishing returns (for RF)
    visualizer.create_diminishing_returns_curves(
        'Righteous Fire',
        save_path=f"{output_dir}/04_diminishing_returns_rf.png"
    )
    
    # 5. Stat ceilings
    visualizer.create_stat_ceiling_chart(
        skills,
        save_path=f"{output_dir}/05_stat_ceilings.png"
    )
    
    # 6. Node allocation flow
    visualizer.create_node_allocation_flow(
        'Righteous Fire',
        node_budget=100,
        save_path=f"{output_dir}/06_allocation_flow_rf.png"
    )
    
    print("\n" + "=" * 80)
    print(f"✓ ALL VISUALIZATIONS GENERATED")
    print(f"✓ Saved to: {output_dir}/")
    print("=" * 80)
    
    plt.show()


if __name__ == "__main__":
    generate_all_visualizations()
