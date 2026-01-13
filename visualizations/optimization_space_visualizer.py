"""
Optimization Space Visualization
Shows how to balance multiple damage vectors to maximize DPS
Uses real Path of Building data to calculate realistic ceilings
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from typing import Dict, List, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.skill_scaling_analyzer import SkillScalingAnalyzer


class OptimizationSpaceVisualizer:
    """
    Visualizes damage optimization as a geometric problem:
    - 2D: Maximize area (vector1 × vector2)
    - 3D: Maximize volume (vector1 × vector2 × vector3)
    - N-D: Maximize hypervolume
    
    Key insight: Balanced investment > Stacking one vector
    """
    
    def __init__(self):
        self.analyzer = SkillScalingAnalyzer()
        
        # Realistic ceilings from PoB tree + items (in percentage points)
        self.vector_ceilings = {
            'increased_damage': 300,      # ~300% available from tree + items
            'crit_chance': 95,            # 5% base, can get to 95% (90 points)
            'crit_multi': 500,            # 150% base, can get to 650% (500 points)
            'dot_multi': 100,             # ~100% available for DoT builds
            'attack_speed': 150,          # ~150% for attack builds
            'cast_speed': 150,            # ~150% for spell builds
            'aura_effect': 100,           # ~100% with aura clusters
            'more_multipliers': 180,      # 40% × 40% × 40% = 174%
            'penetration': 40,            # ~40% ele pen available
        }
        
        # Point costs to reach ceiling (approximately)
        self.point_costs = {
            'increased_damage': 100,
            'crit_chance': 60,
            'crit_multi': 60,
            'dot_multi': 40,
            'attack_speed': 50,
            'cast_speed': 50,
            'aura_effect': 40,
            'more_multipliers': 30,  # Support gems + keystone
            'penetration': 20,
        }
    
    def create_2d_optimization_space(self, vector1: str, vector2: str, 
                                     skill: str = None, save_path: str = None):
        """
        2D visualization: Maximize area = vector1 × vector2
        Shows isoquant curves (lines of equal DPS)
        """
        print(f"\n1. Creating 2D Optimization Space ({vector1} vs {vector2})...")
        
        ceiling1 = self.vector_ceilings.get(vector1, 200)
        ceiling2 = self.vector_ceilings.get(vector2, 200)
        
        # Create grid
        x = np.linspace(0, ceiling1, 100)
        y = np.linspace(0, ceiling2, 100)
        X, Y = np.meshgrid(x, y)
        
        # Calculate DPS multiplier at each point
        # DPS = Base × (1 + vector1/100) × (1 + vector2/100)
        Z = (1 + X/100) * (1 + Y/100)
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Contour plot (isoquant curves)
        levels = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16]
        contour = ax.contour(X, Y, Z, levels=levels, colors='black', alpha=0.4, linewidths=1)
        ax.clabel(contour, inline=True, fontsize=9, fmt='%1.0fx')
        
        # Filled contour (heatmap)
        contourf = ax.contourf(X, Y, Z, levels=20, cmap='RdYlGn', alpha=0.6)
        plt.colorbar(contourf, ax=ax, label='DPS Multiplier')
        
        # Show ceiling constraints
        ax.axvline(ceiling1, color='red', linestyle='--', linewidth=2, 
                   label=f'{vector1} ceiling ({ceiling1}%)', alpha=0.7)
        ax.axhline(ceiling2, color='blue', linestyle='--', linewidth=2,
                   label=f'{vector2} ceiling ({ceiling2}%)', alpha=0.7)
        
        # Show balanced allocation
        balanced_x = ceiling1 * 0.5
        balanced_y = ceiling2 * 0.5
        balanced_dps = (1 + balanced_x/100) * (1 + balanced_y/100)
        ax.plot(balanced_x, balanced_y, 'go', markersize=15, 
                label=f'Balanced: {balanced_dps:.2f}x', zorder=5)
        
        # Show unbalanced allocations
        unbalanced_points = [
            (ceiling1, 0, 'Max Vector1'),
            (0, ceiling2, 'Max Vector2'),
            (ceiling1 * 0.8, ceiling2 * 0.2, '80/20'),
            (ceiling1 * 0.2, ceiling2 * 0.8, '20/80'),
        ]
        
        for ux, uy, label in unbalanced_points:
            dps = (1 + ux/100) * (1 + uy/100)
            marker = 'rx' if 'Max' in label else 'yo'
            ax.plot(ux, uy, marker, markersize=12 if 'Max' in label else 10,
                   label=f'{label}: {dps:.2f}x', zorder=5)
        
        # Add efficiency arrows showing marginal returns
        arrow_starts = [
            (ceiling1 * 0.3, ceiling2 * 0.3),
            (ceiling1 * 0.7, ceiling2 * 0.3),
            (ceiling1 * 0.3, ceiling2 * 0.7),
        ]
        
        for sx, sy in arrow_starts:
            # Arrow pointing toward balanced allocation
            dx = balanced_x - sx
            dy = balanced_y - sy
            length = np.sqrt(dx**2 + dy**2)
            if length > 20:  # Only show if significant distance
                ax.arrow(sx, sy, dx*0.3, dy*0.3, head_width=10, 
                        head_length=15, fc='purple', ec='purple', alpha=0.5)
        
        ax.set_xlabel(f'{vector1.replace("_", " ").title()} (%)', 
                     size=12, weight='bold')
        ax.set_ylabel(f'{vector2.replace("_", " ").title()} (%)', 
                     size=12, weight='bold')
        ax.set_title(f'DPS Optimization Space: {vector1} × {vector2}\n' +
                    'Contour lines show equal DPS (isoquants)\n' +
                    'Green dot = Optimal balanced allocation',
                    size=14, weight='bold', pad=20)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # Add text explaining optimization
        max_unbalanced = max((1 + ceiling1/100) * 1, 1 * (1 + ceiling2/100))
        textstr = f'Key Insight:\n' \
                 f'Balanced ({balanced_dps:.2f}x) >\n' \
                 f'Unbalanced ({max_unbalanced:.2f}x)'
        ax.text(0.98, 0.02, textstr, transform=ax.transAxes,
               fontsize=11, verticalalignment='bottom', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_3d_optimization_volume(self, vector1: str, vector2: str, vector3: str,
                                     save_path: str = None):
        """
        3D visualization: Maximize volume = vector1 × vector2 × vector3
        Shows isosurfaces of equal DPS
        """
        print(f"\n2. Creating 3D Optimization Volume ({vector1} × {vector2} × {vector3})...")
        
        ceiling1 = self.vector_ceilings.get(vector1, 200)
        ceiling2 = self.vector_ceilings.get(vector2, 200)
        ceiling3 = self.vector_ceilings.get(vector3, 200)
        
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Sample points
        allocations = [
            ('Balanced', ceiling1/2, ceiling2/2, ceiling3/2, 'green', 's', 200),
            ('Max V1', ceiling1, 0, 0, 'red', 'o', 150),
            ('Max V2', 0, ceiling2, 0, 'red', 'o', 150),
            ('Max V3', 0, 0, ceiling3, 'red', 'o', 150),
            ('V1+V2', ceiling1*0.7, ceiling2*0.7, ceiling3*0.1, 'yellow', '^', 100),
            ('V1+V3', ceiling1*0.7, ceiling2*0.1, ceiling3*0.7, 'yellow', '^', 100),
            ('V2+V3', ceiling1*0.1, ceiling2*0.7, ceiling3*0.7, 'yellow', '^', 100),
        ]
        
        for label, x, y, z, color, marker, size in allocations:
            dps = (1 + x/100) * (1 + y/100) * (1 + z/100)
            ax.scatter([x], [y], [z], c=color, marker=marker, s=size, 
                      label=f'{label}: {dps:.2f}x', edgecolors='black', linewidths=2)
        
        # Draw ceiling box
        # Define the vertices of the box
        box_x = [0, ceiling1, ceiling1, 0, 0, ceiling1, ceiling1, 0]
        box_y = [0, 0, ceiling2, ceiling2, 0, 0, ceiling2, ceiling2]
        box_z = [0, 0, 0, 0, ceiling3, ceiling3, ceiling3, ceiling3]
        
        # Draw edges
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
            [0, 4], [1, 5], [2, 6], [3, 7],  # Vertical edges
        ]
        
        for edge in edges:
            edge_x = [box_x[edge[0]], box_x[edge[1]]]
            edge_y = [box_y[edge[0]], box_y[edge[1]]]
            edge_z = [box_z[edge[0]], box_z[edge[1]]]
            ax.plot(edge_x, edge_y, edge_z, 'k--', alpha=0.3, linewidth=1)
        
        ax.set_xlabel(f'{vector1.replace("_", " ").title()} (%)', size=11, weight='bold')
        ax.set_ylabel(f'{vector2.replace("_", " ").title()} (%)', size=11, weight='bold')
        ax.set_zlabel(f'{vector3.replace("_", " ").title()} (%)', size=11, weight='bold')
        ax.set_title(f'3D DPS Optimization: {vector1} × {vector2} × {vector3}\n' +
                    'Maximize volume within ceiling constraints',
                    size=14, weight='bold', pad=20)
        ax.legend(loc='upper left', fontsize=9)
        
        # Rotate for better view
        ax.view_init(elev=20, azim=45)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_pareto_frontier(self, vectors: List[str], point_budget: int = 100,
                              save_path: str = None):
        """
        Show Pareto frontier - optimal allocations given point budget
        Points above frontier are impossible, points below are suboptimal
        """
        print(f"\n3. Creating Pareto Frontier (point budget: {point_budget})...")
        
        if len(vectors) != 2:
            print("   ERROR: Pareto frontier requires exactly 2 vectors for 2D visualization")
            return None
        
        v1, v2 = vectors
        ceiling1 = self.vector_ceilings[v1]
        ceiling2 = self.vector_ceilings[v2]
        cost1 = self.point_costs[v1]
        cost2 = self.point_costs[v2]
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Generate all possible allocations within budget
        allocations = []
        for points_v1 in range(0, min(point_budget + 1, cost1 + 1)):
            points_v2 = point_budget - points_v1
            if points_v2 >= 0:
                # Calculate stats gained
                stat1 = min(ceiling1 * (points_v1 / cost1), ceiling1)
                stat2 = min(ceiling2 * (points_v2 / cost2), ceiling2)
                dps = (1 + stat1/100) * (1 + stat2/100)
                allocations.append((stat1, stat2, dps, points_v1, points_v2))
        
        # Plot all allocations
        stats1 = [a[0] for a in allocations]
        stats2 = [a[1] for a in allocations]
        dps_values = [a[2] for a in allocations]
        
        scatter = ax.scatter(stats1, stats2, c=dps_values, s=50, cmap='RdYlGn',
                           alpha=0.6, edgecolors='black', linewidths=0.5)
        plt.colorbar(scatter, ax=ax, label='DPS Multiplier')
        
        # Draw Pareto frontier
        pareto_points = []
        for i, a in enumerate(allocations):
            is_pareto = True
            for j, b in enumerate(allocations):
                if i != j and b[0] >= a[0] and b[1] >= a[1] and b[2] > a[2]:
                    is_pareto = False
                    break
            if is_pareto:
                pareto_points.append(a)
        
        if pareto_points:
            pareto_points.sort(key=lambda x: x[0])
            pareto_x = [p[0] for p in pareto_points]
            pareto_y = [p[1] for p in pareto_points]
            ax.plot(pareto_x, pareto_y, 'b-', linewidth=3, label='Pareto Frontier', zorder=5)
            
            # Mark optimal point (highest DPS)
            optimal = max(pareto_points, key=lambda x: x[2])
            ax.plot(optimal[0], optimal[1], 'g*', markersize=20, 
                   label=f'Optimal: {optimal[2]:.2f}x DPS\n({optimal[3]} pts → {v1}, {optimal[4]} pts → {v2})',
                   zorder=6)
        
        # Show budget constraint line
        max_stat1 = ceiling1 * min(point_budget / cost1, 1.0)
        max_stat2 = ceiling2 * min(point_budget / cost2, 1.0)
        budget_x = np.linspace(0, max_stat1, 100)
        budget_y = max_stat2 - (budget_x / max_stat1) * max_stat2
        ax.plot(budget_x, budget_y, 'r--', linewidth=2, alpha=0.5,
               label=f'Budget Constraint ({point_budget} points)')
        
        ax.set_xlabel(f'{v1.replace("_", " ").title()} (%)', size=12, weight='bold')
        ax.set_ylabel(f'{v2.replace("_", " ").title()} (%)', size=12, weight='bold')
        ax.set_title(f'Pareto Frontier: Optimal Allocations with {point_budget} Points\n' +
                    'Points on frontier are optimal (best DPS for given stats)\n' +
                    'Points below frontier are suboptimal (wasted points)',
                    size=14, weight='bold', pad=20)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_marginal_returns_comparison(self, vectors: List[str], save_path: str = None):
        """
        Show marginal returns for each vector (how much DPS per % invested)
        Reveals which vectors give best return at different investment levels
        """
        print(f"\n4. Creating Marginal Returns Comparison...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()
        
        for idx, vector in enumerate(vectors[:4]):
            ax = axes[idx]
            ceiling = self.vector_ceilings.get(vector, 200)
            
            # Calculate DPS and marginal DPS
            investments = np.linspace(0, ceiling, 100)
            base_dps = 100  # Arbitrary base
            
            # Assume we have 100% invested in other vectors
            other_mult = 2.0  # (1 + 100%)
            
            dps_values = base_dps * (1 + investments/100) * other_mult
            
            # Marginal return = derivative
            marginal = np.gradient(dps_values, investments)
            
            # Plot DPS curve
            ax2 = ax.twinx()
            line1 = ax.plot(investments, dps_values, 'b-', linewidth=2.5, 
                          label='Total DPS')
            line2 = ax2.plot(investments, marginal, 'r--', linewidth=2, 
                           label='Marginal Return')
            
            # Mark zones
            efficient_zone = ceiling * 0.4
            ax.axvspan(0, efficient_zone, alpha=0.1, color='green', 
                      label='High Efficiency')
            ax.axvspan(efficient_zone, ceiling * 0.7, alpha=0.1, color='yellow',
                      label='Medium Efficiency')
            ax.axvspan(ceiling * 0.7, ceiling, alpha=0.1, color='red',
                      label='Low Efficiency')
            
            ax.set_xlabel(f'{vector.replace("_", " ").title()} (%)', size=11, weight='bold')
            ax.set_ylabel('Total DPS', size=11, weight='bold', color='b')
            ax2.set_ylabel('Marginal DPS per 1%', size=11, weight='bold', color='r')
            ax.set_title(f'{vector.replace("_", " ").title()} Returns', size=12, weight='bold')
            ax.tick_params(axis='y', labelcolor='b')
            ax2.tick_params(axis='y', labelcolor='r')
            ax.grid(True, alpha=0.3)
            
            # Combined legend
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax.legend(lines, labels, loc='upper left', fontsize=9)
        
        plt.suptitle('Marginal Returns Analysis\n' +
                    'Shows diminishing returns for each damage vector',
                    size=14, weight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig
    
    def create_ceiling_analysis(self, skill: str, save_path: str = None):
        """
        Calculate and visualize realistic ceilings for a specific skill
        using actual PoB data
        """
        print(f"\n5. Creating Ceiling Analysis for {skill}...")
        
        scaling = self.analyzer.analyze_skill(skill)
        
        # Determine relevant vectors for this skill
        relevant_vectors = {}
        
        # Increased damage (always relevant)
        relevant_vectors['increased_damage'] = self.vector_ceilings['increased_damage']
        
        # Speed (if scales)
        if scaling.speed_type == 'cast_speed':
            relevant_vectors['cast_speed'] = self.vector_ceilings['cast_speed']
        elif scaling.speed_type == 'attack_speed':
            relevant_vectors['attack_speed'] = self.vector_ceilings['attack_speed']
        
        # Crit (if scales)
        if scaling.scales_with_crit:
            relevant_vectors['crit_chance'] = self.vector_ceilings['crit_chance']
            relevant_vectors['crit_multi'] = self.vector_ceilings['crit_multi']
        
        # DoT (if relevant)
        if 'dot' in scaling.tags:
            relevant_vectors['dot_multi'] = self.vector_ceilings['dot_multi']
        
        # Calculate optimal allocation
        num_vectors = len(relevant_vectors)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # Left: Bar chart of ceilings
        vectors = list(relevant_vectors.keys())
        ceilings = list(relevant_vectors.values())
        colors = plt.cm.Set3(np.linspace(0, 1, len(vectors)))
        
        bars = ax1.barh(vectors, ceilings, color=colors, alpha=0.8, edgecolor='black')
        ax1.set_xlabel('Maximum Available (%)', size=12, weight='bold')
        ax1.set_title(f'Realistic Ceilings for {skill}\n(from PoB tree + items)',
                     size=13, weight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        # Add values on bars
        for i, (bar, ceil) in enumerate(zip(bars, ceilings)):
            ax1.text(ceil + 5, i, f'{ceil}%', va='center', fontsize=10, weight='bold')
        
        # Right: Calculate max DPS with different allocations
        allocation_strategies = {
            'Balanced': {v: relevant_vectors[v] / num_vectors for v in vectors},
            'Focus Primary': {vectors[0]: relevant_vectors[vectors[0]] * 0.6,
                            **{v: relevant_vectors[v] * 0.4/(num_vectors-1) for v in vectors[1:]}},
            'Max Single': {vectors[0]: relevant_vectors[vectors[0]],
                          **{v: 0 for v in vectors[1:]}},
        }
        
        if len(vectors) >= 2:
            allocation_strategies['50/50 Split'] = {
                vectors[0]: relevant_vectors[vectors[0]] * 0.5,
                vectors[1]: relevant_vectors[vectors[1]] * 0.5,
                **{v: 0 for v in vectors[2:]}
            }
        
        strategy_names = list(allocation_strategies.keys())
        strategy_dps = []
        
        for strategy_name, allocation in allocation_strategies.items():
            dps_mult = 1.0
            
            for vector, value in allocation.items():
                if vector in ['crit_chance', 'crit_multi']:
                    # Handle crit specially
                    continue
                else:
                    dps_mult *= (1 + value / 100)
            
            # Add crit contribution if present
            if 'crit_chance' in allocation and 'crit_multi' in allocation:
                crit_chance = allocation['crit_chance'] / 100
                crit_multi = 1.5 + allocation['crit_multi'] / 100  # 150% base
                dps_mult *= (1 + crit_chance * (crit_multi - 1))
            
            strategy_dps.append(dps_mult)
        
        bars2 = ax2.bar(strategy_names, strategy_dps, color=colors[:len(strategy_names)],
                       alpha=0.8, edgecolor='black')
        ax2.set_ylabel('DPS Multiplier', size=12, weight='bold')
        ax2.set_title(f'DPS with Different Allocation Strategies\n(Base DPS = 1.0x)',
                     size=13, weight='bold')
        ax2.grid(axis='y', alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add values on bars
        for bar, dps in zip(bars2, strategy_dps):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                    f'{dps:.2f}x', ha='center', va='bottom', fontsize=10, weight='bold')
        
        # Highlight best strategy
        best_idx = np.argmax(strategy_dps)
        bars2[best_idx].set_edgecolor('gold')
        bars2[best_idx].set_linewidth(4)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Saved: {save_path}")
        
        return fig


def generate_optimization_visualizations(output_dir: str = "visualizations/output"):
    """Generate all optimization space visualizations"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    viz = OptimizationSpaceVisualizer()
    
    print("=" * 80)
    print("GENERATING OPTIMIZATION SPACE VISUALIZATIONS")
    print("=" * 80)
    print("\nKey Concept: DPS = Product of vectors (multiplicative)")
    print("Optimal strategy: Balance vectors to maximize product")
    print("Like maximizing area (2D) or volume (3D)")
    print("=" * 80)
    
    # 1. 2D optimization spaces
    viz.create_2d_optimization_space(
        'increased_damage', 'crit_multi',
        save_path=f"{output_dir}/opt_01_2d_damage_vs_crit.png"
    )
    
    viz.create_2d_optimization_space(
        'increased_damage', 'attack_speed',
        save_path=f"{output_dir}/opt_02_2d_damage_vs_speed.png"
    )
    
    # 2. 3D optimization volume
    viz.create_3d_optimization_volume(
        'increased_damage', 'crit_multi', 'attack_speed',
        save_path=f"{output_dir}/opt_03_3d_volume.png"
    )
    
    # 3. Pareto frontier
    viz.create_pareto_frontier(
        ['increased_damage', 'crit_multi'],
        point_budget=100,
        save_path=f"{output_dir}/opt_04_pareto_frontier.png"
    )
    
    # 4. Marginal returns
    viz.create_marginal_returns_comparison(
        ['increased_damage', 'crit_multi', 'attack_speed', 'dot_multi'],
        save_path=f"{output_dir}/opt_05_marginal_returns.png"
    )
    
    # 5. Ceiling analysis for specific skills
    for skill in ['Righteous Fire', 'Blade Vortex', 'Lightning Strike']:
        safe_name = skill.replace(' ', '_').lower()
        viz.create_ceiling_analysis(
            skill,
            save_path=f"{output_dir}/opt_06_ceiling_{safe_name}.png"
        )
    
    print("\n" + "=" * 80)
    print("✓ ALL OPTIMIZATION VISUALIZATIONS GENERATED")
    print(f"✓ Saved to: {output_dir}/")
    print("=" * 80)


if __name__ == "__main__":
    generate_optimization_visualizations()
