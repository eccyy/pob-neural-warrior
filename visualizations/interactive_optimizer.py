"""
Interactive Optimization Visualizer
Create an interactive HTML tool to visualize and optimize DPS by adjusting scaling vectors
"""

from pathlib import Path
import json


class InteractiveOptimizer:
    """Create interactive visualizations for DPS optimization"""
    
    def __init__(self, output_dir: str = "visualizations/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_skill_optimizer(self, skill_name: str, scaling_vectors: dict, 
                              ceilings: dict, total_points: int = 100,
                              base_dps: float = 100.0, global_multipliers: dict = None):
        """
        Create interactive optimizer for a single skill
        
        Args:
            skill_name: Name of the skill (e.g., "Blade Vortex")
            scaling_vectors: Dict of vector names to point efficiency (e.g., {"Increased Damage": 3.0})
            ceilings: Dict of vector names to maximum % (e.g., {"Increased Damage": 300})
            total_points: Total passive points to allocate
            base_dps: Base DPS before scaling
            global_multipliers: Dict of global multipliers with their properties
                               e.g., {"Frenzy Charges": {"more_per": 4, "max_count": 3, "cost": 15}}
        """
        
        if global_multipliers is None:
            global_multipliers = {}
        
        # Calculate optimal allocation (balanced)
        n_vectors = len(scaling_vectors)
        points_per_vector = total_points / n_vectors
        
        optimal_allocation = {}
        optimal_values = {}
        for vector, efficiency in scaling_vectors.items():
            ceiling = ceilings[vector]
            points = min(points_per_vector, ceiling / efficiency)
            optimal_allocation[vector] = points
            optimal_values[vector] = points * efficiency
        
        # Calculate initial (suboptimal) allocation - stack first vector
        vector_names = list(scaling_vectors.keys())
        initial_allocation = {v: 0.0 for v in vector_names}
        initial_allocation[vector_names[0]] = min(
            total_points, 
            ceilings[vector_names[0]] / scaling_vectors[vector_names[0]]
        )
        
        initial_values = {
            v: initial_allocation[v] * scaling_vectors[v] 
            for v in vector_names
        }
        
        # Create the interactive HTML
        html_content = self._generate_optimizer_html(
            skill_name, vector_names, scaling_vectors, ceilings, 
            total_points, base_dps, initial_values, optimal_values,
            initial_allocation, optimal_allocation, global_multipliers
        )
        
        output_file = self.output_dir / f"interactive_optimizer_{skill_name.lower().replace(' ', '_')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ Created interactive optimizer: {output_file}")
        return str(output_file)
    
    def _generate_optimizer_html(self, skill_name, vector_names, scaling_vectors, 
                                 ceilings, total_points, base_dps, initial_values,
                                 optimal_values, initial_allocation, optimal_allocation,
                                 global_multipliers):
        """Generate complete HTML with JavaScript for interactive optimization"""
        
        # Calculate optimal DPS
        optimal_dps = base_dps
        for vector, value in optimal_values.items():
            optimal_dps *= (1 + value / 100)
        
        # Create JavaScript data structures
        js_vectors = json.dumps(vector_names)
        js_ceilings = json.dumps(ceilings)
        js_efficiency = json.dumps(scaling_vectors)
        js_initial_values = json.dumps(initial_values)
        js_optimal_values = json.dumps(optimal_values)
        js_initial_alloc = json.dumps(initial_allocation)
        js_optimal_alloc = json.dumps(optimal_allocation)
        js_global_mults = json.dumps(global_multipliers)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{skill_name} - Interactive DPS Optimizer</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a1a;
            color: #e0e0e0;
        }}
        
        h1 {{
            text-align: center;
            color: #4CAF50;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}
        
        .controls-container {{
            background: #2a2a2a;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        .slider-group {{
            margin-bottom: 25px;
        }}
        
        .slider-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        
        .vector-name {{
            font-weight: 600;
            color: #4CAF50;
        }}
        
        .slider-value {{
            color: #FFA726;
            font-weight: 600;
        }}
        
        input[type="range"] {{
            width: 100%;
            height: 8px;
            border-radius: 5px;
            background: #404040;
            outline: none;
            -webkit-appearance: none;
        }}
        
        input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
        }}
        
        input[type="range"]::-moz-range-thumb {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            border: none;
        }}
        
        .stats-panel {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #4CAF50;
        }}
        
        .stat-subtext {{
            font-size: 14px;
            color: #FFA726;
            margin-top: 5px;
        }}
        
        .button-group {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 25px 0;
        }}
        
        button {{
            padding: 12px 30px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .btn-optimal {{
            background: #4CAF50;
            color: white;
        }}
        
        .btn-optimal:hover {{
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(76,175,80,0.4);
        }}
        
        .btn-reset {{
            background: #FF5722;
            color: white;
        }}
        
        .btn-reset:hover {{
            background: #f4511e;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(255,87,34,0.4);
        }}
        
        .btn-equal {{
            background: #2196F3;
            color: white;
        }}
        
        .btn-equal:hover {{
            background: #0b7dda;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(33,150,243,0.4);
        }}
        
        #chartDiv {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        .efficiency-indicator {{
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 18px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .efficiency-good {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
            border: 2px solid #4CAF50;
        }}
        
        .efficiency-medium {{
            background: rgba(255, 167, 38, 0.2);
            color: #FFA726;
            border: 2px solid #FFA726;
        }}
        
        .efficiency-poor {{
            background: rgba(244, 67, 54, 0.2);
            color: #F44336;
            border: 2px solid #F44336;
        }}
        
        .multipliers-section {{
            background: #2a2a2a;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        .multipliers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .multiplier-card {{
            background: #1a1a1a;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #404040;
            transition: all 0.3s;
        }}
        
        .multiplier-card:hover {{
            border-color: #4CAF50;
        }}
        
        .multiplier-card.active {{
            border-color: #4CAF50;
            background: rgba(76, 175, 80, 0.1);
        }}
        
        .multiplier-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }}
        
        .multiplier-checkbox {{
            width: 24px;
            height: 24px;
            cursor: pointer;
            accent-color: #4CAF50;
        }}
        
        .multiplier-name {{
            font-weight: 600;
            font-size: 15px;
            color: #e0e0e0;
            flex: 1;
        }}
        
        .multiplier-effect {{
            color: #4CAF50;
            font-weight: 700;
            font-size: 16px;
        }}
        
        .multiplier-details {{
            font-size: 13px;
            color: #888;
            margin-top: 8px;
            padding-left: 36px;
        }}
        
        .multiplier-cost {{
            color: #FFA726;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <h1>🎯 {skill_name} - DPS Optimizer</h1>
    <p class="subtitle">Adjust stat allocations to maximize DPS | {total_points} Passive Points Available</p>
    
    <div id="efficiencyIndicator" class="efficiency-indicator"></div>
    
    <div class="stats-panel">
        <div class="stat-card">
            <div class="stat-label">Current DPS</div>
            <div class="stat-value" id="currentDps">-</div>
            <div class="stat-subtext" id="dpsComparison">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Points Used</div>
            <div class="stat-value" id="pointsUsed">-</div>
            <div class="stat-subtext">of {total_points} available</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Optimization Score</div>
            <div class="stat-value" id="optimizationScore">-</div>
            <div class="stat-subtext" id="scoreDescription">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Optimal DPS</div>
            <div class="stat-value" style="color: #FFA726;">{optimal_dps:.1f}</div>
            <div class="stat-subtext">Balanced allocation target</div>
        </div>
    </div>
    
    <div class="button-group">
        <button class="btn-optimal" onclick="setOptimalAllocation()">📊 Show Optimal</button>
        <button class="btn-equal" onclick="setEqualAllocation()">⚖️ Equal Split</button>
        <button class="btn-reset" onclick="resetAllocation()">🔄 Reset</button>
    </div>
    
    <div class="multipliers-section" id="multipliers-section" style="display: none;">
        <h2 style="margin-top: 0; color: #4CAF50;">⚡ Global Multipliers Checklist</h2>
        <p style="color: #888; margin-bottom: 15px;">
            These are multiplicative "more" modifiers that work with any build. 
            Cost depends on skill, tree position, and gearing requirements.
        </p>
        <div class="multipliers-grid" id="multipliers-grid"></div>
    </div>
    
    <div class="controls-container">
        <h2 style="margin-top: 0; color: #4CAF50;">📈 Stat Allocation Controls</h2>
        <div id="sliders"></div>
    </div>
    
    <div id="chartDiv"></div>
    
    <script>
        // Configuration
        const SKILL_NAME = {json.dumps(skill_name)};
        const VECTORS = {js_vectors};
        const CEILINGS = {js_ceilings};
        const EFFICIENCY = {js_efficiency};
        const TOTAL_POINTS = {total_points};
        const BASE_DPS = {base_dps};
        const INITIAL_VALUES = {js_initial_values};
        const OPTIMAL_VALUES = {js_optimal_values};
        const INITIAL_ALLOCATION = {js_initial_alloc};
        const OPTIMAL_ALLOCATION = {js_optimal_alloc};
        const GLOBAL_MULTIPLIERS = {js_global_mults};
        
        // State
        let currentAllocation = {{}};
        let currentValues = {{}};
        let activeMultipliers = {{}};
        
        // Initialize
        function init() {{
            createSliders();
            createMultipliersSection();
            resetAllocation();
        }}
        
        function createSliders() {{
            const container = document.getElementById('sliders');
            VECTORS.forEach(vector => {{
                const maxPoints = Math.floor(CEILINGS[vector] / EFFICIENCY[vector]);
                const div = document.createElement('div');
                div.className = 'slider-group';
                div.innerHTML = `
                    <div class="slider-label">
                        <span class="vector-name">${{vector}}</span>
                        <span class="slider-value">
                            <span id="points-${{vector}}">0</span> pts → 
                            <span id="value-${{vector}}">0</span>%
                        </span>
                    </div>
                    <input type="range" 
                           id="slider-${{vector}}" 
                           min="0" 
                           max="${{maxPoints}}" 
                           step="1" 
                           value="0"
                           oninput="updateAllocation('${{vector}}', this.value)">
                `;
                container.appendChild(div);
            }});
        }}
        
        function createMultipliersSection() {{
            if (Object.keys(GLOBAL_MULTIPLIERS).length === 0) {{
                return; // No multipliers, hide section
            }}
            
            document.getElementById('multipliers-section').style.display = 'block';
            const container = document.getElementById('multipliers-grid');
            
            Object.keys(GLOBAL_MULTIPLIERS).forEach(name => {{
                const mult = GLOBAL_MULTIPLIERS[name];
                activeMultipliers[name] = false;
                
                let effectText = '';
                let detailsText = '';
                
                if (mult.type === 'charges') {{
                    const totalMore = mult.more_per * mult.max_count;
                    effectText = `+${{totalMore}}% MORE`;
                    detailsText = `${{mult.more_per}}% more per charge × ${{mult.max_count}} charges = ${{totalMore}}% more (additive with itself)`;
                }} else if (mult.type === 'penetration') {{
                    effectText = `+${{mult.value}}% MORE`;
                    detailsText = `${{mult.value}}% resistance penetration (multiplicative with damage)`;
                }} else if (mult.type === 'shock') {{
                    effectText = `+${{mult.value}}% MORE`;
                    detailsText = `${{mult.value}}% increased damage taken by enemies (multiplicative)`;
                }} else {{
                    effectText = `+${{mult.value}}% MORE`;
                    detailsText = mult.description || 'Multiplicative damage increase';
                }}
                
                const costText = mult.cost_varies ? 
                    `Cost: <span class="multiplier-cost">Varies</span> (depends on skill/tree/gear)` :
                    `Cost: <span class="multiplier-cost">${{mult.cost}} points</span>`;
                
                const div = document.createElement('div');
                div.className = 'multiplier-card';
                div.id = `mult-card-${{name.replace(/\\s+/g, '-')}}`;
                div.innerHTML = `
                    <div class="multiplier-header">
                        <input type="checkbox" 
                               class="multiplier-checkbox" 
                               id="mult-${{name.replace(/\\s+/g, '-')}}"
                               onchange="toggleMultiplier('${{name}}', this.checked)">
                        <label class="multiplier-name" for="mult-${{name.replace(/\\s+/g, '-')}}">${{name}}</label>
                        <span class="multiplier-effect">${{effectText}}</span>
                    </div>
                    <div class="multiplier-details">
                        ${{detailsText}}<br>
                        ${{costText}}
                    </div>
                `;
                container.appendChild(div);
            }});
        }}
        
        function toggleMultiplier(name, enabled) {{
            activeMultipliers[name] = enabled;
            const card = document.getElementById(`mult-card-${{name.replace(/\\s+/g, '-')}}`);
            if (enabled) {{
                card.classList.add('active');
            }} else {{
                card.classList.remove('active');
            }}
            updateStats();
            updateChart();
        }}
        
        function updateAllocation(vector, points) {{
            points = parseFloat(points);
            currentAllocation[vector] = points;
            currentValues[vector] = points * EFFICIENCY[vector];
            
            // Update display
            document.getElementById(`points-${{vector}}`).textContent = points.toFixed(0);
            document.getElementById(`value-${{vector}}`).textContent = currentValues[vector].toFixed(1);
            
            updateStats();
            updateChart();
        }}
        
        function calculateDPS() {{
            let dps = BASE_DPS;
            
            // Apply scaling vectors (multiplicative)
            VECTORS.forEach(vector => {{
                const value = currentValues[vector] || 0;
                dps *= (1 + value / 100);
            }});
            
            // Apply global multipliers (multiplicative)
            Object.keys(activeMultipliers).forEach(name => {{
                if (activeMultipliers[name]) {{
                    const mult = GLOBAL_MULTIPLIERS[name];
                    let moreValue = 0;
                    
                    if (mult.type === 'charges') {{
                        moreValue = mult.more_per * mult.max_count;
                    }} else {{
                        moreValue = mult.value;
                    }}
                    
                    dps *= (1 + moreValue / 100);
                }}
            }});
            
            return dps;
        }}
        
        function calculateOptimalDPS() {{
            let dps = BASE_DPS;
            VECTORS.forEach(vector => {{
                dps *= (1 + OPTIMAL_VALUES[vector] / 100);
            }});
            return dps;
        }}
        
        function getTotalPoints() {{
            return Object.values(currentAllocation).reduce((sum, pts) => sum + pts, 0);
        }}
        
        function getBalanceScore() {{
            // Calculate coefficient of variation (lower is more balanced)
            const values = Object.values(currentValues);
            if (values.every(v => v === 0)) return 0;
            
            const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
            const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
            const stdDev = Math.sqrt(variance);
            const cv = stdDev / mean;
            
            // Convert to 0-100 score (lower CV = higher score)
            return Math.max(0, 100 - cv * 100);
        }}
        
        function updateStats() {{
            const currentDps = calculateDPS();
            const optimalDps = calculateOptimalDPS();
            const totalPoints = getTotalPoints();
            const balanceScore = getBalanceScore();
            const efficiency = (currentDps / optimalDps) * 100;
            
            // Update DPS
            document.getElementById('currentDps').textContent = currentDps.toFixed(1);
            
            // Update comparison
            const comparison = document.getElementById('dpsComparison');
            const diff = ((currentDps / optimalDps - 1) * 100).toFixed(1);
            const diffSign = diff >= 0 ? '+' : '';
            comparison.textContent = `${{diffSign}}${{diff}}% vs optimal`;
            comparison.style.color = diff >= -5 ? '#4CAF50' : diff >= -15 ? '#FFA726' : '#F44336';
            
            // Update points
            document.getElementById('pointsUsed').textContent = totalPoints.toFixed(0);
            
            // Update optimization score
            document.getElementById('optimizationScore').textContent = balanceScore.toFixed(0) + '%';
            
            // Update score description
            const scoreDesc = document.getElementById('scoreDescription');
            if (balanceScore >= 80) {{
                scoreDesc.textContent = 'Excellent balance!';
                scoreDesc.style.color = '#4CAF50';
            }} else if (balanceScore >= 60) {{
                scoreDesc.textContent = 'Good balance';
                scoreDesc.style.color = '#FFA726';
            }} else {{
                scoreDesc.textContent = 'Unbalanced';
                scoreDesc.style.color = '#F44336';
            }}
            
            // Update efficiency indicator
            const indicator = document.getElementById('efficiencyIndicator');
            if (efficiency >= 95) {{
                indicator.className = 'efficiency-indicator efficiency-good';
                indicator.textContent = '🎯 Excellent! Near-optimal allocation';
            }} else if (efficiency >= 80) {{
                indicator.className = 'efficiency-indicator efficiency-medium';
                indicator.textContent = '⚠️ Good, but could be more balanced';
            }} else {{
                indicator.className = 'efficiency-indicator efficiency-poor';
                indicator.textContent = '❌ Unbalanced - try distributing points more evenly';
            }}
        }}
        
        function updateChart() {{
            const currentDps = calculateDPS();
            const optimalDps = calculateOptimalDPS();
            
            // Prepare data for radar chart
            const categories = VECTORS.map(v => v.replace('Increased ', '').replace(' Multiplier', ' Multi'));
            
            const currentData = VECTORS.map(v => currentValues[v] || 0);
            const optimalData = VECTORS.map(v => OPTIMAL_VALUES[v]);
            const ceilingData = VECTORS.map(v => CEILINGS[v]);
            
            const trace1 = {{
                type: 'scatterpolar',
                r: currentData,
                theta: categories,
                fill: 'toself',
                name: 'Current',
                line: {{color: '#4CAF50', width: 3}},
                fillcolor: 'rgba(76, 175, 80, 0.3)'
            }};
            
            const trace2 = {{
                type: 'scatterpolar',
                r: optimalData,
                theta: categories,
                fill: 'toself',
                name: 'Optimal (Balanced)',
                line: {{color: '#FFA726', width: 2, dash: 'dash'}},
                fillcolor: 'rgba(255, 167, 38, 0.1)'
            }};
            
            const trace3 = {{
                type: 'scatterpolar',
                r: ceilingData,
                theta: categories,
                fill: 'toself',
                name: 'Maximum Ceiling',
                line: {{color: '#666', width: 1, dash: 'dot'}},
                fillcolor: 'rgba(100, 100, 100, 0.05)'
            }};
            
            const layout = {{
                polar: {{
                    radialaxis: {{
                        visible: true,
                        range: [0, Math.max(...ceilingData) * 1.1],
                        tickfont: {{color: '#aaa'}},
                        gridcolor: '#444'
                    }},
                    angularaxis: {{
                        tickfont: {{color: '#e0e0e0', size: 12}}
                    }},
                    bgcolor: '#1a1a1a'
                }},
                showlegend: true,
                legend: {{
                    font: {{color: '#e0e0e0'}},
                    bgcolor: 'rgba(42, 42, 42, 0.8)',
                    bordercolor: '#666',
                    borderwidth: 1
                }},
                paper_bgcolor: '#2a2a2a',
                plot_bgcolor: '#1a1a1a',
                font: {{color: '#e0e0e0'}},
                title: {{
                    text: `DPS Comparison: ${{currentDps.toFixed(1)}} vs ${{optimalDps.toFixed(1)}} (Optimal)`,
                    font: {{size: 18, color: '#4CAF50'}}
                }},
                height: 600
            }};
            
            Plotly.newPlot('chartDiv', [trace3, trace2, trace1], layout, {{responsive: true}});
        }}
        
        function setOptimalAllocation() {{
            VECTORS.forEach(vector => {{
                const points = OPTIMAL_ALLOCATION[vector];
                currentAllocation[vector] = points;
                currentValues[vector] = OPTIMAL_VALUES[vector];
                document.getElementById(`slider-${{vector}}`).value = points;
                document.getElementById(`points-${{vector}}`).textContent = points.toFixed(0);
                document.getElementById(`value-${{vector}}`).textContent = OPTIMAL_VALUES[vector].toFixed(1);
            }});
            updateStats();
            updateChart();
        }}
        
        function setEqualAllocation() {{
            const pointsPerVector = TOTAL_POINTS / VECTORS.length;
            VECTORS.forEach(vector => {{
                const maxPoints = Math.floor(CEILINGS[vector] / EFFICIENCY[vector]);
                const points = Math.min(pointsPerVector, maxPoints);
                currentAllocation[vector] = points;
                currentValues[vector] = points * EFFICIENCY[vector];
                document.getElementById(`slider-${{vector}}`).value = points;
                document.getElementById(`points-${{vector}}`).textContent = points.toFixed(0);
                document.getElementById(`value-${{vector}}`).textContent = currentValues[vector].toFixed(1);
            }});
            updateStats();
            updateChart();
        }}
        
        function resetAllocation() {{
            VECTORS.forEach(vector => {{
                const points = INITIAL_ALLOCATION[vector];
                currentAllocation[vector] = points;
                currentValues[vector] = INITIAL_VALUES[vector];
                document.getElementById(`slider-${{vector}}`).value = points;
                document.getElementById(`points-${{vector}}`).textContent = points.toFixed(0);
                document.getElementById(`value-${{vector}}`).textContent = INITIAL_VALUES[vector].toFixed(1);
            }});
            updateStats();
            updateChart();
        }}
        
        // Initialize on load
        init();
    </script>
</body>
</html>"""
        
        return html


def main():
    """Generate interactive optimizer for a crit skill"""
    visualizer = InteractiveOptimizer()
    
    # Example: Blade Vortex (spell crit skill)
    print("=" * 80)
    print("GENERATING INTERACTIVE DPS OPTIMIZER WITH GLOBAL MULTIPLIERS")
    print("=" * 80)
    print()
    
    # Define global multipliers (mostly work with all skills)
    global_multipliers = {
        'Frenzy Charges': {
            'type': 'charges',
            'more_per': 4,
            'max_count': 3,
            'cost': 15,
            'cost_varies': False
        },
        'Power Charges': {
            'type': 'charges',
            'more_per': 4,
            'max_count': 3,
            'cost': 10,
            'cost_varies': False
        },
        'Lightning Penetration': {
            'type': 'penetration',
            'value': 37,  # Typical achievable
            'cost': 20,
            'cost_varies': True,
            'description': '37% lightning penetration (multiplicative vs resistances)'
        },
        'Fire Penetration': {
            'type': 'penetration',
            'value': 37,
            'cost': 20,
            'cost_varies': True,
            'description': '37% fire penetration (multiplicative vs resistances)'
        },
        'Cold Penetration': {
            'type': 'penetration',
            'value': 37,
            'cost': 20,
            'cost_varies': True,
            'description': '37% cold penetration (multiplicative vs resistances)'
        },
        'Shock (20%)': {
            'type': 'shock',
            'value': 20,
            'cost': 25,
            'cost_varies': True,
            'description': '20% shock = 20% increased damage taken (multiplicative)'
        },
        'Intimidate': {
            'type': 'debuff',
            'value': 10,
            'cost': 15,
            'cost_varies': True,
            'description': '10% increased damage taken (multiplicative)'
        },
        'Tailwind': {
            'type': 'buff',
            'value': 8,
            'cost': 20,
            'cost_varies': True,
            'description': '8% more action speed (multiplicative with cast/attack speed)'
        }
    }
    
    skills = [
        {
            'name': 'Blade Vortex',
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
            'points': 100,
            'base_dps': 100.0,
            'multipliers': {
                'Frenzy Charges': global_multipliers['Frenzy Charges'],
                'Power Charges': global_multipliers['Power Charges'],
                'Lightning Penetration': global_multipliers['Lightning Penetration'],
                'Shock (20%)': global_multipliers['Shock (20%)'],
                'Tailwind': global_multipliers['Tailwind'],
            }
        },
        {
            'name': 'Lightning Strike',
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
            'points': 100,
            'base_dps': 100.0,
            'multipliers': {
                'Frenzy Charges': global_multipliers['Frenzy Charges'],
                'Lightning Penetration': global_multipliers['Lightning Penetration'],
                'Shock (20%)': global_multipliers['Shock (20%)'],
                'Intimidate': global_multipliers['Intimidate'],
                'Tailwind': global_multipliers['Tailwind'],
            }
        },
        {
            'name': 'Righteous Fire',
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
            'points': 100,
            'base_dps': 100.0,
            'multipliers': {
                'Fire Penetration': global_multipliers['Fire Penetration'],
            }
        }
    ]
    
    for skill_config in skills:
        print(f"\nCreating optimizer for: {skill_config['name']}")
        output_file = visualizer.create_skill_optimizer(
            skill_name=skill_config['name'],
            scaling_vectors=skill_config['vectors'],
            ceilings=skill_config['ceilings'],
            total_points=skill_config['points'],
            base_dps=skill_config['base_dps'],
            global_multipliers=skill_config.get('multipliers', {})
        )
        print(f"  → Open in browser: {output_file}")
    
    print("\n" + "=" * 80)
    print("✓ ALL INTERACTIVE OPTIMIZERS GENERATED")
    print("=" * 80)
    print("\nINSTRUCTIONS:")
    print("1. Open any HTML file in your web browser")
    print("2. Use sliders to allocate passive points")
    print("3. Check/uncheck global multipliers to add them")
    print("4. Watch DPS change in real-time")
    print("5. Compare your allocation to optimal (balanced)")
    print("\nGLOBAL MULTIPLIERS:")
    print("- Frenzy Charges: 4% more per charge (3 charges = 12% more)")
    print("- Power Charges: 4% more per charge (3 charges = 12% more)")
    print("- Penetration: ~37% multiplicative with damage")
    print("- Shock/Intimidate: Increased damage taken (multiplicative)")
    print("- Tailwind: 8% more action speed")
    print("\nCost varies by:")
    print("  • Skill type (melee vs ranged vs spell)")
    print("  • Starting tree position")
    print("  • Gearing requirements")
    print("  • Build archetype")
    print("\nKEY INSIGHT:")
    print("1. Balance stat allocation FIRST (maximize the product)")
    print("2. Add global multipliers as CHECKLIST items")
    print("3. Each multiplier is independent cost/benefit analysis")


if __name__ == "__main__":
    main()
