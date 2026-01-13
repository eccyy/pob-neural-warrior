"""
Interactive 3D Visualizations using Plotly
For exploring high-dimensional scaling vectors interactively
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path
from typing import List, Dict

sys.path.append(str(Path(__file__).parent.parent))

from utils.skill_scaling_analyzer import SkillScalingAnalyzer


class Interactive3DVisualizer:
    """
    Interactive visualizations for exploring scaling vectors
    Uses Plotly for web-based interactive charts
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
    
    def create_3d_scatter(self, skills: List[str]):
        """
        3D scatter plot with color and size as 4th/5th dimensions
        X: Damage scaling, Y: Speed scaling, Z: Defensive priority
        Color: Damage type, Size: Crit scaling
        """
        print("\n1. Creating Interactive 3D Scatter Plot...")
        
        data_points = []
        
        for skill in skills:
            scaling = self.analyzer.analyze_skill(skill)
            
            # Extract dimensions
            damage = len([x for x in scaling.increased_damage_types[:10] if 'damage' in x.lower()]) / 10
            speed = 0.8 if scaling.speed_type != 'none' else 0.0
            defense = scaling.defensive_priority.get('life', 0.5)
            
            # Determine damage type for color
            if 'fire' in scaling.tags:
                damage_type = 'Fire'
            elif 'cold' in scaling.tags:
                damage_type = 'Cold'
            elif 'lightning' in scaling.tags:
                damage_type = 'Lightning'
            elif 'physical' in scaling.tags:
                damage_type = 'Physical'
            elif 'chaos' in scaling.tags:
                damage_type = 'Chaos'
            else:
                damage_type = 'Generic'
            
            # Size based on crit scaling
            crit_size = 20 if scaling.scales_with_crit else 10
            
            data_points.append({
                'skill': skill,
                'damage': damage,
                'speed': speed,
                'defense': defense,
                'damage_type': damage_type,
                'crit_size': crit_size,
                'crit': 'Yes' if scaling.scales_with_crit else 'No'
            })
        
        # Create figure
        fig = go.Figure()
        
        for point in data_points:
            fig.add_trace(go.Scatter3d(
                x=[point['damage']],
                y=[point['speed']],
                z=[point['defense']],
                mode='markers+text',
                name=point['skill'],
                marker=dict(
                    size=point['crit_size'],
                    color=self.colors.get(point['skill'], '#888888'),
                    line=dict(width=2, color='white')
                ),
                text=point['skill'],
                textposition='top center',
                hovertemplate=f"<b>{point['skill']}</b><br>" +
                             f"Damage Focus: {point['damage']:.2f}<br>" +
                             f"Speed Focus: {point['speed']:.2f}<br>" +
                             f"Defense Priority: {point['defense']:.2f}<br>" +
                             f"Damage Type: {point['damage_type']}<br>" +
                             f"Crit Scaling: {point['crit']}<br>" +
                             "<extra></extra>"
            ))
        
        fig.update_layout(
            title='<b>3D Skill Scaling Analysis</b><br>' +
                  '<sub>Size = Crit Scaling, Color = Skill Type</sub>',
            scene=dict(
                xaxis_title='Damage Focus (0-1)',
                yaxis_title='Speed Focus (0-1)',
                zaxis_title='Defense Priority (0-1)',
                xaxis=dict(range=[0, 1]),
                yaxis=dict(range=[0, 1]),
                zaxis=dict(range=[0, 1])
            ),
            width=1200,
            height=800,
            showlegend=True
        )
        
        return fig
    
    def create_sunburst_chart(self, skill: str):
        """
        Hierarchical sunburst chart showing scaling breakdown
        Center -> Outer: Skill -> Category -> Specific Stats
        """
        print(f"\n2. Creating Sunburst Chart for {skill}...")
        
        scaling = self.analyzer.analyze_skill(skill)
        
        # Build hierarchical data
        labels = [skill]
        parents = ['']
        values = [100]
        colors = []
        
        # Level 1: Major categories
        categories = {
            'Damage': 40,
            'Defense': 30,
            'Speed': 15,
            'Crit': 10,
            'Utility': 5
        }
        
        # Adjust based on skill
        if scaling.speed_type == 'none':
            categories['Speed'] = 0
            categories['Damage'] += 15
        
        if not scaling.scales_with_crit:
            categories['Crit'] = 0
            categories['Damage'] += 10
        
        for cat, val in categories.items():
            if val > 0:
                labels.append(cat)
                parents.append(skill)
                values.append(val)
        
        # Level 2: Specific stats
        damage_stats = []
        for dt in scaling.increased_damage_types[:5]:
            clean_name = dt.replace('_', ' ').title()
            if clean_name not in damage_stats:
                damage_stats.append(clean_name)
                labels.append(clean_name)
                parents.append('Damage')
                values.append(categories.get('Damage', 0) / len(scaling.increased_damage_types[:5]))
        
        # Add defense stats
        for def_stat, priority in list(scaling.defensive_priority.items())[:3]:
            clean_name = def_stat.replace('_', ' ').title()
            labels.append(clean_name)
            parents.append('Defense')
            values.append(categories.get('Defense', 0) * priority)
        
        # Create figure
        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues='total',
            marker=dict(
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{label}</b><br>Value: %{value:.1f}<br><extra></extra>'
        ))
        
        fig.update_layout(
            title=f'<b>Scaling Breakdown: {skill}</b><br>' +
                  '<sub>Hierarchical view of stat priorities</sub>',
            width=900,
            height=900
        )
        
        return fig
    
    def create_stat_comparison_bars(self, skills: List[str]):
        """
        Interactive grouped bar chart comparing stat priorities
        """
        print("\n3. Creating Interactive Bar Chart...")
        
        stat_types = ['Life', 'Damage', 'Speed', 'Crit', 'DoT', 'Area']
        
        data = []
        for stat in stat_types:
            values = []
            for skill in skills:
                scaling = self.analyzer.analyze_skill(skill)
                value = self._get_stat_value(scaling, stat)
                values.append(value)
            
            data.append(go.Bar(
                name=stat,
                x=skills,
                y=values,
                text=[f'{v:.1%}' for v in values],
                textposition='auto',
                hovertemplate='<b>%{x}</b><br>' +
                             f'{stat}: %{{y:.1%}}<br>' +
                             '<extra></extra>'
            ))
        
        fig = go.Figure(data=data)
        
        fig.update_layout(
            title='<b>Stat Priority Comparison</b><br>' +
                  '<sub>Hover for details, click legend to toggle</sub>',
            xaxis_title='Skills',
            yaxis_title='Priority (0-100%)',
            barmode='group',
            width=1400,
            height=700,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        return fig
    
    def create_diminishing_returns_surface(self, skill: str):
        """
        3D surface plot showing diminishing returns
        X: Increased Damage, Y: DoT Multi, Z: Effective DPS
        """
        print(f"\n4. Creating 3D Diminishing Returns Surface for {skill}...")
        
        scaling = self.analyzer.analyze_skill(skill)
        
        # Create mesh grid
        inc_damage = np.linspace(0, 400, 50)
        dot_multi = np.linspace(0, 150, 50)
        X, Y = np.meshgrid(inc_damage, dot_multi)
        
        # Calculate effective DPS at each point
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                inc = X[i, j]
                dot = Y[i, j]
                
                # Base calculation
                base_dps = 100
                
                # Increased damage (additive)
                dps = base_dps * (1 + inc / 100)
                
                # DoT multi (additive with increased)
                if 'dot' in scaling.tags:
                    dps *= (1 + dot / 100)
                
                Z[i, j] = dps
        
        # Create surface
        fig = go.Figure(data=[go.Surface(
            x=X,
            y=Y,
            z=Z,
            colorscale='Viridis',
            hovertemplate='Inc Damage: %{x:.0f}%<br>' +
                         'DoT Multi: %{y:.0f}%<br>' +
                         'Effective DPS: %{z:.0f}<br>' +
                         '<extra></extra>'
        )])
        
        fig.update_layout(
            title=f'<b>Diminishing Returns Surface: {skill}</b><br>' +
                  '<sub>Shows how stat combinations affect DPS</sub>',
            scene=dict(
                xaxis_title='Increased Damage (%)',
                yaxis_title='DoT Multiplier (%)',
                zaxis_title='Effective DPS',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.3)
                )
            ),
            width=1200,
            height=800
        )
        
        return fig
    
    def _get_stat_value(self, scaling, stat: str) -> float:
        """Get normalized stat value for comparison"""
        stat_lower = stat.lower()
        increased_types = [x.lower() for x in scaling.increased_damage_types]
        
        if stat_lower == 'life':
            return 1.0 if any('life' in x for x in increased_types[:5]) else 0.4
        elif stat_lower == 'damage':
            return min(len([x for x in increased_types if 'damage' in x]) / 10, 1.0)
        elif stat_lower == 'speed':
            return 0.8 if scaling.speed_type != 'none' else 0.0
        elif stat_lower == 'crit':
            return 0.9 if scaling.scales_with_crit else 0.0
        elif stat_lower == 'dot':
            return 0.9 if 'dot' in scaling.tags else 0.0
        elif stat_lower == 'area':
            return 0.7 if scaling.area_scaling else 0.0
        
        return 0.0


def generate_interactive_visualizations(output_dir: str = "visualizations/output"):
    """Generate all interactive visualizations and save as HTML"""
    from typing import List
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    visualizer = Interactive3DVisualizer()
    
    skills = [
        'Righteous Fire',
        'Blade Vortex',
        'Lightning Strike',
        'Ice Spear',
        'Toxic Rain',
        'Cyclone'
    ]
    
    print("=" * 80)
    print("GENERATING INTERACTIVE VISUALIZATIONS")
    print("=" * 80)
    
    # 1. 3D Scatter
    fig1 = visualizer.create_3d_scatter(skills)
    fig1.write_html(f"{output_dir}/interactive_01_3d_scatter.html")
    print(f"   Saved: {output_dir}/interactive_01_3d_scatter.html")
    
    # 2. Sunburst for RF
    fig2 = visualizer.create_sunburst_chart('Righteous Fire')
    fig2.write_html(f"{output_dir}/interactive_02_sunburst_rf.html")
    print(f"   Saved: {output_dir}/interactive_02_sunburst_rf.html")
    
    # 3. Bar comparison
    fig3 = visualizer.create_stat_comparison_bars(skills)
    fig3.write_html(f"{output_dir}/interactive_03_bar_comparison.html")
    print(f"   Saved: {output_dir}/interactive_03_bar_comparison.html")
    
    # 4. 3D surface
    fig4 = visualizer.create_diminishing_returns_surface('Righteous Fire')
    fig4.write_html(f"{output_dir}/interactive_04_diminishing_surface.html")
    print(f"   Saved: {output_dir}/interactive_04_diminishing_surface.html")
    
    print("\n" + "=" * 80)
    print("✓ ALL INTERACTIVE VISUALIZATIONS GENERATED")
    print(f"✓ Open HTML files in browser from: {output_dir}/")
    print("=" * 80)
    
    # Show first one
    fig1.show()


if __name__ == "__main__":
    generate_interactive_visualizations()
