"""
Cost-Benefit Hill Climb Visualizer
Shows the optimization landscape with costs varying by starting position
"""

from pathlib import Path
import json
import math


class CostBenefitVisualizer:
    """Create interactive cost-benefit visualizations for stat optimization"""
    
    def __init__(self, output_dir: str = "visualizations/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_hillclimb_optimizer(self, skill_name: str, starting_class: str,
                                  scaling_vectors: dict, ceilings: dict,
                                  node_distances: dict, total_points: int = 100,
                                  base_dps: float = 100.0):
        """
        Create interactive hill climb visualization
        
        Args:
            skill_name: Name of the skill
            starting_class: Starting class (Shadow, Witch, Marauder, etc.)
            scaling_vectors: Dict of vector names to efficiency (% per point)
            ceilings: Dict of vector names to maximum %
            node_distances: Dict of vector names to distance from starting class
            total_points: Total passive points available
            base_dps: Base DPS before scaling
        """
        
        # Calculate cost-benefit metrics for each vector
        metrics = {}
        for vector in scaling_vectors:
            efficiency = scaling_vectors[vector]
            ceiling = ceilings[vector]
            distance = node_distances[vector]
            
            # Max points that can be invested
            max_investment = min(total_points, ceiling / efficiency)
            
            # Cost per point includes distance (pathing cost)
            effective_cost = 1 + (distance / 10)  # Distance penalty
            
            # Benefit per effective point
            roi = efficiency / effective_cost
            
            metrics[vector] = {
                'efficiency': efficiency,
                'ceiling': ceiling,
                'distance': distance,
                'max_investment': max_investment,
                'effective_cost': effective_cost,
                'roi': roi
            }
        
        html_content = self._generate_hillclimb_html(
            skill_name, starting_class, scaling_vectors, ceilings,
            node_distances, metrics, total_points, base_dps
        )
        
        output_file = self.output_dir / f"hillclimb_{skill_name.lower().replace(' ', '_')}_{starting_class.lower()}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ Created hill climb optimizer: {output_file}")
        return str(output_file)
    
    def _generate_hillclimb_html(self, skill_name, starting_class, scaling_vectors,
                                 ceilings, node_distances, metrics, total_points, base_dps):
        """Generate HTML with 3D hill climb visualization"""
        
        js_vectors = json.dumps(list(scaling_vectors.keys()))
        js_efficiency = json.dumps(scaling_vectors)
        js_ceilings = json.dumps(ceilings)
        js_distances = json.dumps(node_distances)
        js_metrics = json.dumps(metrics)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{skill_name} - Hill Climb Optimizer ({starting_class})</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a1a;
            color: #e0e0e0;
        }}
        
        h1 {{
            text-align: center;
            color: #4CAF50;
            margin-bottom: 5px;
        }}
        
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 16px;
        }}
        
        .main-grid {{
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .controls-panel {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            height: fit-content;
        }}
        
        .chart-container {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: #1a1a1a;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #4CAF50;
        }}
        
        .vector-card {{
            background: #1a1a1a;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
            transition: all 0.3s;
        }}
        
        .vector-card:hover {{
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(76,175,80,0.3);
        }}
        
        .vector-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .vector-name {{
            font-weight: 600;
            font-size: 14px;
            color: #e0e0e0;
        }}
        
        .vector-value {{
            font-weight: 700;
            font-size: 16px;
            color: #4CAF50;
        }}
        
        .vector-metrics {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 12px;
            color: #888;
        }}
        
        .metric {{
            display: flex;
            justify-content: space-between;
        }}
        
        .metric-label {{
            color: #666;
        }}
        
        .metric-value {{
            color: #FFA726;
            font-weight: 600;
        }}
        
        .distance-indicator {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 8px;
        }}
        
        .distance-near {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }}
        
        .distance-medium {{
            background: rgba(255, 167, 38, 0.2);
            color: #FFA726;
        }}
        
        .distance-far {{
            background: rgba(244, 67, 54, 0.2);
            color: #F44336;
        }}
        
        input[type="range"] {{
            width: 100%;
            margin: 10px 0;
        }}
        
        .slider-label {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            margin-bottom: 5px;
        }}
        
        button {{
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            font-size: 14px;
            font-weight: 600;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .btn-greedy {{
            background: #4CAF50;
            color: white;
        }}
        
        .btn-greedy:hover {{
            background: #45a049;
            transform: translateY(-2px);
        }}
        
        .btn-balanced {{
            background: #2196F3;
            color: white;
        }}
        
        .btn-balanced:hover {{
            background: #0b7dda;
            transform: translateY(-2px);
        }}
        
        .btn-reset {{
            background: #666;
            color: white;
        }}
        
        .btn-reset:hover {{
            background: #555;
            transform: translateY(-2px);
        }}
        
        .info-box {{
            background: #1a1a1a;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            border-left: 4px solid #FFA726;
        }}
        
        .info-title {{
            font-weight: 600;
            color: #FFA726;
            margin-bottom: 8px;
        }}
        
        .info-text {{
            font-size: 13px;
            color: #aaa;
            line-height: 1.6;
        }}
        
        .legend {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }}
        
        .legend-color {{
            width: 30px;
            height: 15px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <h1>⛰️ {skill_name} - Hill Climb Optimizer</h1>
    <p class="subtitle">
        Starting Class: <strong style="color: #4CAF50;">{starting_class}</strong> | 
        {total_points} Passive Points | 
        Color = Distance Cost
    </p>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Current DPS</div>
            <div class="stat-value" id="currentDps">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Points Used</div>
            <div class="stat-value" id="pointsUsed">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Efficiency Score</div>
            <div class="stat-value" id="efficiencyScore">-</div>
        </div>
    </div>
    
    <div class="main-grid">
        <div class="controls-panel">
            <h3 style="margin-top: 0; color: #4CAF50;">📊 Stat Allocation</h3>
            
            <div id="vectorControls"></div>
            
            <div style="margin-top: 20px;">
                <button class="btn-greedy" onclick="greedyClimb()">🎯 Greedy Climb (Best ROI)</button>
                <button class="btn-balanced" onclick="balancedAllocation()">⚖️ Balanced Allocation</button>
                <button class="btn-reset" onclick="reset()">🔄 Reset</button>
            </div>
            
            <div class="info-box">
                <div class="info-title">💡 Hill Climbing Strategy</div>
                <div class="info-text">
                    <strong>Greedy:</strong> Always picks attribute with best ROI (efficiency ÷ distance cost)<br><br>
                    <strong>Balanced:</strong> Distributes points evenly across all vectors<br><br>
                    <strong>Color coding:</strong><br>
                    🟢 Near (0-20 nodes)<br>
                    🟠 Medium (20-40 nodes)<br>
                    🔴 Far (40+ nodes)
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <div id="surfaceChart"></div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: linear-gradient(to right, #4CAF50, #FFA726, #F44336);"></div>
                    <span>Distance from {starting_class} (Green=Near, Red=Far)</span>
                </div>
            </div>
            <div id="roiChart" style="margin-top: 20px;"></div>
        </div>
    </div>
    
    <div id="vectorMetrics" style="margin-top: 20px;"></div>
    
    <script>
        // Configuration
        const SKILL_NAME = {json.dumps(skill_name)};
        const STARTING_CLASS = {json.dumps(starting_class)};
        const VECTORS = {js_vectors};
        const EFFICIENCY = {js_efficiency};
        const CEILINGS = {js_ceilings};
        const DISTANCES = {js_distances};
        const METRICS = {js_metrics};
        const TOTAL_POINTS = {total_points};
        const BASE_DPS = {base_dps};
        
        // State
        let allocation = {{}};
        let values = {{}};
        
        function init() {{
            createControls();
            createMetricsDisplay();
            reset();
        }}
        
        function createControls() {{
            const container = document.getElementById('vectorControls');
            
            VECTORS.forEach(vector => {{
                const metric = METRICS[vector];
                const maxPoints = Math.floor(metric.max_investment);
                
                const div = document.createElement('div');
                div.innerHTML = `
                    <div class="slider-label">
                        <span style="font-weight: 600;">${{vector}}</span>
                        <span id="value-${{vector}}" style="color: #4CAF50;">0 pts</span>
                    </div>
                    <input type="range" 
                           id="slider-${{vector}}"
                           min="0" 
                           max="${{maxPoints}}" 
                           value="0"
                           step="1"
                           oninput="updateAllocation('${{vector}}', this.value)">
                `;
                container.appendChild(div);
            }});
        }}
        
        function createMetricsDisplay() {{
            const container = document.getElementById('vectorMetrics');
            
            // Sort by ROI
            const sortedVectors = VECTORS.slice().sort((a, b) => 
                METRICS[b].roi - METRICS[a].roi
            );
            
            let html = '<div style="background: #2a2a2a; padding: 20px; border-radius: 10px;">';
            html += '<h3 style="color: #4CAF50; margin-top: 0;">📈 Vector Analysis (Sorted by ROI)</h3>';
            html += '<div style="display: grid; gap: 12px;">';
            
            sortedVectors.forEach((vector, index) => {{
                const metric = METRICS[vector];
                const distance = metric.distance;
                
                let distanceClass = 'distance-near';
                let distanceLabel = 'Near';
                if (distance > 40) {{
                    distanceClass = 'distance-far';
                    distanceLabel = 'Far';
                }} else if (distance > 20) {{
                    distanceClass = 'distance-medium';
                    distanceLabel = 'Medium';
                }}
                
                const rankEmoji = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${{index + 1}}`;
                
                html += `
                    <div class="vector-card">
                        <div class="vector-header">
                            <div>
                                <span class="vector-name">${{rankEmoji}} ${{vector}}</span>
                                <span class="distance-indicator ${{distanceClass}}">${{distance}} nodes</span>
                            </div>
                            <span class="vector-value" id="allocation-${{vector}}">0%</span>
                        </div>
                        <div class="vector-metrics">
                            <div class="metric">
                                <span class="metric-label">Efficiency:</span>
                                <span class="metric-value">${{metric.efficiency.toFixed(2)}}% / pt</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">ROI:</span>
                                <span class="metric-value">${{metric.roi.toFixed(2)}}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Distance Cost:</span>
                                <span class="metric-value">${{metric.effective_cost.toFixed(2)}}×</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Max Investment:</span>
                                <span class="metric-value">${{Math.floor(metric.max_investment)}} pts</span>
                            </div>
                        </div>
                    </div>
                `;
            }});
            
            html += '</div></div>';
            container.innerHTML = html;
        }}
        
        function updateAllocation(vector, points) {{
            allocation[vector] = parseFloat(points);
            values[vector] = allocation[vector] * EFFICIENCY[vector];
            updateDisplay();
        }}
        
        function updateDisplay() {{
            // Update sliders and labels
            VECTORS.forEach(vector => {{
                const pts = allocation[vector] || 0;
                const val = values[vector] || 0;
                document.getElementById(`slider-${{vector}}`).value = pts;
                document.getElementById(`value-${{vector}}`).textContent = `${{pts}} pts`;
                document.getElementById(`allocation-${{vector}}`).textContent = `${{val.toFixed(1)}}%`;
            }});
            
            // Calculate stats
            const totalPoints = Object.values(allocation).reduce((sum, v) => sum + v, 0);
            const dps = calculateDPS();
            
            // Calculate efficiency score (DPS per point spent)
            const efficiency = totalPoints > 0 ? (dps / totalPoints).toFixed(1) : 0;
            
            document.getElementById('currentDps').textContent = dps.toFixed(1);
            document.getElementById('pointsUsed').textContent = totalPoints.toFixed(0);
            document.getElementById('efficiencyScore').textContent = efficiency;
            
            updateCharts();
        }}
        
        function calculateDPS() {{
            let dps = BASE_DPS;
            VECTORS.forEach(vector => {{
                const value = values[vector] || 0;
                dps *= (1 + value / 100);
            }});
            return dps;
        }}
        
        function greedyClimb() {{
            // Reset
            VECTORS.forEach(v => {{
                allocation[v] = 0;
                values[v] = 0;
            }});
            
            // Greedy algorithm: always pick best ROI
            let pointsRemaining = TOTAL_POINTS;
            
            while (pointsRemaining > 0) {{
                let bestVector = null;
                let bestROI = -1;
                
                // Find vector with best ROI that can still accept points
                VECTORS.forEach(vector => {{
                    const metric = METRICS[vector];
                    const currentAllocation = allocation[vector] || 0;
                    
                    if (currentAllocation < metric.max_investment) {{
                        // Calculate marginal ROI (diminishing returns for high allocations)
                        const currentValue = values[vector] || 0;
                        const marginalEfficiency = metric.efficiency * (1 / (1 + currentValue / 100));
                        const marginalROI = marginalEfficiency / metric.effective_cost;
                        
                        if (marginalROI > bestROI) {{
                            bestROI = marginalROI;
                            bestVector = vector;
                        }}
                    }}
                }});
                
                if (!bestVector) break;
                
                // Allocate 1 point to best vector
                allocation[bestVector] = (allocation[bestVector] || 0) + 1;
                values[bestVector] = allocation[bestVector] * EFFICIENCY[bestVector];
                pointsRemaining--;
            }}
            
            updateDisplay();
        }}
        
        function balancedAllocation() {{
            // Reset
            VECTORS.forEach(v => {{
                allocation[v] = 0;
                values[v] = 0;
            }});
            
            // Distribute evenly
            const pointsPerVector = TOTAL_POINTS / VECTORS.length;
            
            VECTORS.forEach(vector => {{
                const metric = METRICS[vector];
                const points = Math.min(pointsPerVector, metric.max_investment);
                allocation[vector] = points;
                values[vector] = points * EFFICIENCY[vector];
            }});
            
            updateDisplay();
        }}
        
        function reset() {{
            VECTORS.forEach(v => {{
                allocation[v] = 0;
                values[v] = 0;
            }});
            updateDisplay();
        }}
        
        function updateCharts() {{
            // Create 3D surface showing cost landscape
            const resolution = 20;
            const vectors = VECTORS.slice(0, 2); // Use first 2 vectors for 3D
            
            if (vectors.length < 2) return;
            
            const v1 = vectors[0];
            const v2 = vectors[1];
            
            const max1 = Math.floor(METRICS[v1].max_investment);
            const max2 = Math.floor(METRICS[v2].max_investment);
            
            // Generate grid
            const x = [];
            const y = [];
            const z = [];
            const colors = [];
            
            for (let i = 0; i <= resolution; i++) {{
                const xRow = [];
                const yRow = [];
                const zRow = [];
                const colorRow = [];
                
                for (let j = 0; j <= resolution; j++) {{
                    const p1 = (i / resolution) * max1;
                    const p2 = (j / resolution) * max2;
                    
                    const val1 = p1 * EFFICIENCY[v1];
                    const val2 = p2 * EFFICIENCY[v2];
                    
                    const dps = BASE_DPS * (1 + val1 / 100) * (1 + val2 / 100);
                    
                    // Cost calculation (includes distance)
                    const cost = p1 * METRICS[v1].effective_cost + p2 * METRICS[v2].effective_cost;
                    
                    xRow.push(p1);
                    yRow.push(p2);
                    zRow.push(dps);
                    colorRow.push(cost);
                }}
                
                x.push(xRow);
                y.push(yRow);
                z.push(zRow);
                colors.push(colorRow);
            }}
            
            const surface = {{
                type: 'surface',
                x: x,
                y: y,
                z: z,
                surfacecolor: colors,
                colorscale: [
                    [0, '#4CAF50'],
                    [0.5, '#FFA726'],
                    [1, '#F44336']
                ],
                colorbar: {{
                    title: 'Effective<br>Cost',
                    titlefont: {{color: '#e0e0e0'}},
                    tickfont: {{color: '#e0e0e0'}}
                }},
                showscale: true
            }};
            
            // Add current allocation point
            const current = {{
                type: 'scatter3d',
                x: [allocation[v1] || 0],
                y: [allocation[v2] || 0],
                z: [calculateDPS()],
                mode: 'markers',
                marker: {{
                    size: 10,
                    color: '#00ff00',
                    symbol: 'diamond',
                    line: {{
                        color: '#ffffff',
                        width: 2
                    }}
                }},
                name: 'Current'
            }};
            
            const layout = {{
                title: {{
                    text: `DPS Landscape: ${{v1}} vs ${{v2}}<br><sub>Color = Effective Cost (Distance Penalty)</sub>`,
                    font: {{color: '#e0e0e0', size: 16}}
                }},
                scene: {{
                    xaxis: {{
                        title: v1.replace('Increased ', '').replace(' Multiplier', ' Multi'),
                        titlefont: {{color: '#e0e0e0'}},
                        tickfont: {{color: '#aaa'}},
                        gridcolor: '#444',
                        backgroundcolor: '#1a1a1a'
                    }},
                    yaxis: {{
                        title: v2.replace('Increased ', '').replace(' Multiplier', ' Multi'),
                        titlefont: {{color: '#e0e0e0'}},
                        tickfont: {{color: '#aaa'}},
                        gridcolor: '#444',
                        backgroundcolor: '#1a1a1a'
                    }},
                    zaxis: {{
                        title: 'DPS',
                        titlefont: {{color: '#4CAF50'}},
                        tickfont: {{color: '#aaa'}},
                        gridcolor: '#444',
                        backgroundcolor: '#1a1a1a'
                    }},
                    bgcolor: '#1a1a1a'
                }},
                paper_bgcolor: '#2a2a2a',
                plot_bgcolor: '#1a1a1a',
                height: 500
            }};
            
            Plotly.newPlot('surfaceChart', [surface, current], layout, {{responsive: true}});
            
            // Create ROI bar chart
            createROIChart();
        }}
        
        function createROIChart() {{
            const sortedVectors = VECTORS.slice().sort((a, b) => 
                METRICS[b].roi - METRICS[a].roi
            );
            
            const rois = sortedVectors.map(v => METRICS[v].roi);
            const distances = sortedVectors.map(v => METRICS[v].distance);
            
            const trace = {{
                type: 'bar',
                x: sortedVectors.map(v => v.replace('Increased ', '').replace(' Multiplier', ' Multi')),
                y: rois,
                marker: {{
                    color: distances,
                    colorscale: [
                        [0, '#4CAF50'],
                        [0.5, '#FFA726'],
                        [1, '#F44336']
                    ],
                    colorbar: {{
                        title: 'Distance',
                        titlefont: {{color: '#e0e0e0'}},
                        tickfont: {{color: '#e0e0e0'}}
                    }}
                }},
                text: rois.map(r => r.toFixed(2)),
                textposition: 'outside',
                textfont: {{color: '#e0e0e0'}}
            }};
            
            const layout = {{
                title: {{
                    text: 'Return on Investment (ROI) by Vector<br><sub>Efficiency ÷ Effective Cost (higher is better)</sub>',
                    font: {{color: '#e0e0e0', size: 16}}
                }},
                xaxis: {{
                    tickfont: {{color: '#e0e0e0'}},
                    gridcolor: '#444'
                }},
                yaxis: {{
                    title: 'ROI',
                    titlefont: {{color: '#4CAF50'}},
                    tickfont: {{color: '#aaa'}},
                    gridcolor: '#444'
                }},
                paper_bgcolor: '#2a2a2a',
                plot_bgcolor: '#1a1a1a',
                height: 400
            }};
            
            Plotly.newPlot('roiChart', [trace], layout, {{responsive: true}});
        }}
        
        init();
    </script>
</body>
</html>"""
        
        return html


def main():
    """Generate hill climb visualizations for different classes"""
    visualizer = CostBenefitVisualizer()
    
    print("=" * 80)
    print("GENERATING HILL CLIMB COST-BENEFIT VISUALIZATIONS")
    print("=" * 80)
    print()
    
    # Shadow - Crit/Dex class (good for Lightning Strike, Blade Vortex)
    configs = [
        {
            'skill': 'Lightning Strike',
            'class': 'Shadow',
            'vectors': {
                'Increased Physical Damage': 3.0,
                'Attack Speed': 3.0,
                'Critical Strike Chance': 1.58,
                'Critical Strike Multiplier': 8.33,
            },
            'ceilings': {
                'Increased Physical Damage': 300,
                'Attack Speed': 150,
                'Critical Strike Chance': 95,
                'Critical Strike Multiplier': 500,
            },
            'distances': {
                'Increased Physical Damage': 25,  # Medium distance
                'Attack Speed': 15,  # Close
                'Critical Strike Chance': 10,  # Very close (shadow specialty)
                'Critical Strike Multiplier': 12,  # Very close
            }
        },
        {
            'skill': 'Lightning Strike',
            'class': 'Marauder',
            'vectors': {
                'Increased Physical Damage': 3.0,
                'Attack Speed': 3.0,
                'Critical Strike Chance': 1.58,
                'Critical Strike Multiplier': 8.33,
            },
            'ceilings': {
                'Increased Physical Damage': 300,
                'Attack Speed': 150,
                'Critical Strike Chance': 95,
                'Critical Strike Multiplier': 500,
            },
            'distances': {
                'Increased Physical Damage': 12,  # Very close (marauder specialty)
                'Attack Speed': 20,  # Medium
                'Critical Strike Chance': 55,  # Very far
                'Critical Strike Multiplier': 60,  # Very far
            }
        },
        {
            'skill': 'Righteous Fire',
            'class': 'Marauder',
            'vectors': {
                'Increased Maximum Life': 3.12,
                'Damage over Time Multiplier': 2.5,
                'Burning Damage': 3.0,
            },
            'ceilings': {
                'Increased Maximum Life': 250,
                'Damage over Time Multiplier': 100,
                'Burning Damage': 300,
            },
            'distances': {
                'Increased Maximum Life': 8,  # Very close (str area)
                'Damage over Time Multiplier': 30,  # Medium
                'Burning Damage': 25,  # Medium
            }
        },
        {
            'skill': 'Blade Vortex',
            'class': 'Witch',
            'vectors': {
                'Increased Spell Damage': 3.0,
                'Cast Speed': 3.0,
                'Critical Strike Chance': 1.58,
                'Critical Strike Multiplier': 8.33,
            },
            'ceilings': {
                'Increased Spell Damage': 300,
                'Cast Speed': 150,
                'Critical Strike Chance': 95,
                'Critical Strike Multiplier': 500,
            },
            'distances': {
                'Increased Spell Damage': 10,  # Very close (witch specialty)
                'Cast Speed': 15,  # Close
                'Critical Strike Chance': 25,  # Medium
                'Critical Strike Multiplier': 28,  # Medium
            }
        }
    ]
    
    for config in configs:
        print(f"\nCreating hill climb for: {config['skill']} ({config['class']})")
        output_file = visualizer.create_hillclimb_optimizer(
            skill_name=config['skill'],
            starting_class=config['class'],
            scaling_vectors=config['vectors'],
            ceilings=config['ceilings'],
            node_distances=config['distances'],
            total_points=100,
            base_dps=100.0
        )
        print(f"  → {output_file}")
    
    print("\n" + "=" * 80)
    print("✓ ALL HILL CLIMB VISUALIZATIONS GENERATED")
    print("=" * 80)
    print("\nKEY FEATURES:")
    print("1. 3D Surface Plot - Shows DPS landscape colored by cost")
    print("2. ROI Bar Chart - Vectors sorted by efficiency ÷ distance cost")
    print("3. Vector Cards - Detailed metrics including distance from start")
    print("4. Greedy Algorithm - Picks best ROI at each step")
    print("5. Balanced Strategy - Distributes points evenly")
    print("\nCOLOR CODING:")
    print("  🟢 Green = Near (0-20 nodes from starting class)")
    print("  🟠 Orange = Medium (20-40 nodes)")
    print("  🔴 Red = Far (40+ nodes)")
    print("\nINSIGHT:")
    print("- Shadow excels at crit (10-12 nodes away)")
    print("- Marauder excels at life/phys damage (8-12 nodes)")
    print("- Witch excels at spell damage/cast speed (10-15 nodes)")
    print("- Greedy climber considers BOTH efficiency AND distance")
    print("- Far nodes need higher efficiency to be worth the path cost!")


if __name__ == "__main__":
    main()
