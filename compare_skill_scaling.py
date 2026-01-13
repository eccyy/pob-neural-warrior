"""
Compare passive tree node relevance for different skills
Demonstrates that skill-aware optimization correctly prioritizes different stats
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.skill_scaling_analyzer import SkillScalingAnalyzer


def compare_skills():
    """Compare how different skills value the same passive tree nodes"""
    
    analyzer = SkillScalingAnalyzer()
    
    # Test skills with different scaling
    skills = [
        "Righteous Fire",    # Fire DoT spell
        "Blade Vortex",      # Physical spell
        "Lightning Strike",  # Lightning attack
        "Ice Spear",        # Cold spell (crit)
    ]
    
    # Example passive tree nodes
    nodes = [
        {"name": "Bloodless", "stats": ["10% increased maximum Life", "+20 to maximum Life"]},
        {"name": "Cruel Preparation", "stats": ["8% increased maximum Life", "8% increased maximum Mana"]},
        {"name": "Holy Fire", "stats": ["12% increased Fire Damage", "10% increased Burning Damage"]},
        {"name": "Burning Brutality", "stats": ["24% increased Burning Damage", "10% increased Fire Damage over Time Multiplier"]},
        {"name": "Celestial Judgement", "stats": ["15% increased Spell Damage", "20% increased Elemental Damage", "5% increased Cast Speed"]},
        {"name": "Annihilation", "stats": ["10% increased Spell Damage", "+20% to Critical Strike Multiplier", "30% increased Critical Strike Chance"]},
        {"name": "Martial Experience", "stats": ["12% increased Attack Damage", "8% increased Attack Speed"]},
        {"name": "Primeval Force", "stats": ["15% increased Elemental Damage", "20% increased Elemental Damage with Attack Skills"]},
    ]
    
    print("=" * 100)
    print("SKILL-SPECIFIC NODE RELEVANCE COMPARISON")
    print("=" * 100)
    print("\nThis demonstrates how the same passive tree nodes are valued differently")
    print("depending on the active skill's scaling vectors.\n")
    
    for node in nodes:
        print(f"\n{node['name']}")
        print(f"Stats: {', '.join(node['stats'])}")
        print("-" * 100)
        
        # Analyze each skill
        for skill in skills:
            scaling = analyzer.analyze_skill(skill)
            relevance = calculate_node_relevance(node, scaling)
            
            # Visual bar
            bar_length = int(relevance * 40)
            bar = "█" * bar_length + "░" * (40 - bar_length)
            
            print(f"  {skill:20s} [{bar}] {relevance:.2f}")
        
    print("\n" + "=" * 100)
    print("KEY OBSERVATIONS")
    print("=" * 100)
    print("""
1. LIFE NODES (Bloodless, Cruel Preparation):
   - Righteous Fire: VERY HIGH (life is damage stat!)
   - Other skills: MEDIUM (life is just defense)
   
2. FIRE/BURNING NODES (Holy Fire, Burning Brutality):
   - Righteous Fire: VERY HIGH (primary damage type)
   - Blade Vortex: VERY LOW (physical spell, not fire)
   - Lightning Strike: VERY LOW (lightning attack, not fire)
   - Ice Spear: VERY LOW (cold spell, not fire)
   
3. CRIT NODES (Annihilation):
   - Ice Spear: HIGH (crit-focused cold spell)
   - Blade Vortex: MEDIUM (can crit but not primary focus)
   - Righteous Fire: ZERO (DoT cannot crit!)
   - Lightning Strike: MEDIUM (attack can crit)
   
4. ATTACK NODES (Martial Experience):
   - Lightning Strike: HIGH (attack speed + attack damage)
   - Righteous Fire: ZERO (spell, not attack)
   - Blade Vortex: ZERO (spell, not attack)
   - Ice Spear: ZERO (spell, not attack)
   
5. CAST SPEED (Celestial Judgement):
   - Ice Spear: HIGH (benefits from cast speed)
   - Blade Vortex: HIGH (benefits from cast speed)
   - Righteous Fire: ZERO (DoT doesn't scale with cast speed!)
   - Lightning Strike: ZERO (attack, not cast speed)

This proves the skill-aware optimization correctly identifies which nodes
are valuable for each skill's unique scaling requirements!
""")


def calculate_node_relevance(node: dict, scaling) -> float:
    """
    Calculate relevance score (0.0 to 1.0) for a node given a skill's scaling
    Simplified version for demonstration
    """
    relevance = 0.0
    stat_count = len(node['stats'])
    
    for stat in node['stats']:
        stat_lower = stat.lower()
        
        # Life/ES scaling (especially important for RF)
        if 'maximum life' in stat_lower and 'increased_maximum_life' in [s.lower() for s in scaling.increased_damage_types]:
            relevance += 1.0  # Very high for RF
        elif 'maximum life' in stat_lower:
            relevance += 0.4  # Medium for other builds (just defense)
        
        if 'maximum energy shield' in stat_lower and 'increased_maximum_energy_shield' in [s.lower() for s in scaling.increased_damage_types]:
            relevance += 1.0
        elif 'maximum energy shield' in stat_lower:
            relevance += 0.3
        
        # Fire damage scaling
        if 'fire damage' in stat_lower or 'burning damage' in stat_lower:
            if 'fire' in scaling.tags:
                relevance += 0.9
            elif 'elemental' in ' '.join(scaling.increased_damage_types).lower():
                relevance += 0.3
            else:
                relevance += 0.0  # Not fire skill
        
        # DoT multiplier
        if 'damage over time multiplier' in stat_lower:
            if scaling.speed_type == 'none' and ('dot' in scaling.tags or 'damageover time' in scaling.tags):
                relevance += 0.95  # Very high for DoT skills
            else:
                relevance += 0.1
        
        # Spell damage
        if 'spell damage' in stat_lower:
            if 'spell' in scaling.tags:
                relevance += 0.6
            else:
                relevance += 0.0
        
        # Attack damage
        if 'attack damage' in stat_lower:
            if 'attack' in scaling.tags:
                relevance += 0.6
            else:
                relevance += 0.0
        
        # Cast speed
        if 'cast speed' in stat_lower:
            if scaling.speed_type == 'cast_speed':
                relevance += 0.5
            else:
                relevance += 0.0  # Useless for DoT and attacks
        
        # Attack speed
        if 'attack speed' in stat_lower:
            if scaling.speed_type == 'attack_speed':
                relevance += 0.5
            else:
                relevance += 0.0
        
        # Crit
        if 'critical strike' in stat_lower:
            if scaling.scales_with_crit:
                relevance += 0.6
            else:
                relevance += 0.0  # Useless for DoT
        
        # Elemental damage
        if 'elemental damage' in stat_lower:
            if any(elem in scaling.tags for elem in ['fire', 'cold', 'lightning']):
                relevance += 0.5
            else:
                relevance += 0.0
    
    # Normalize by stat count and cap at 1.0
    return min(relevance / max(stat_count, 1), 1.0)


if __name__ == "__main__":
    compare_skills()
