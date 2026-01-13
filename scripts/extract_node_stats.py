"""
Extract passive node stats from Path of Building tree data
Converts PoB's Lua tree format to Python-friendly JSON with stat dictionaries
"""

import json
import re
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def parse_lua_tree_to_node_stats(tree_lua_path: str, output_json_path: str):
    """
    Parse PoB's tree.lua file and extract node stats
    
    Args:
        tree_lua_path: Path to tree.lua file
        output_json_path: Where to save JSON output
    """
    with open(tree_lua_path, 'r', encoding='utf-8') as f:
        tree_lua = f.read()
    
    # Extract the tree table (it's a Lua table assignment)
    # Pattern: tree.nodes[<id>] = { ... }
    node_pattern = r'tree\.nodes\[(\d+)\]\s*=\s*{([^}]+(?:{[^}]+}[^}]+)*)}'
    
    nodes = []
    matches = re.finditer(node_pattern, tree_lua, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        node_id = int(match.group(1))
        node_content = match.group(2)
        
        # Extract sd (stat descriptions) - these contain the mod text
        sd_pattern = r'sd\s*=\s*{([^}]+)}'
        sd_match = re.search(sd_pattern, node_content)
        
        stat_descriptions = []
        if sd_match:
            sd_content = sd_match.group(1)
            # Extract quoted strings
            string_pattern = r'"([^"]+)"'
            stat_descriptions = re.findall(string_pattern, sd_content)
        
        # Parse stat descriptions into structured stats
        stats = parse_stat_descriptions(stat_descriptions)
        
        # Extract other useful properties
        name_match = re.search(r'dn\s*=\s*"([^"]+)"', node_content)
        name = name_match.group(1) if name_match else ""
        
        # Check if notable
        notable_match = re.search(r'not\s*=\s*true', node_content)
        is_notable = notable_match is not None
        
        # Check if keystone
        keystone_match = re.search(r'ks\s*=\s*true', node_content)
        is_keystone = keystone_match is not None
        
        # Check if mastery
        mastery_match = re.search(r'isMastery\s*=\s*true', node_content)
        is_mastery = mastery_match is not None
        
        # Check if ascendancy
        ascendancy_match = re.search(r'ascendancyName\s*=', node_content)
        is_ascendancy = ascendancy_match is not None
        
        nodes.append({
            'id': node_id,
            'name': name,
            'stats': stats,
            'stat_descriptions': stat_descriptions,
            'is_notable': is_notable,
            'is_keystone': is_keystone,
            'is_mastery': is_mastery,
            'is_ascendancy': is_ascendancy
        })
    
    # Save to JSON
    with open(output_json_path, 'w') as f:
        json.dump({
            'nodes': nodes,
            'total_nodes': len(nodes)
        }, f, indent=2)
    
    print(f"Extracted {len(nodes)} nodes to {output_json_path}")
    return nodes


def parse_stat_descriptions(stat_descriptions: List[str]) -> Dict[str, float]:
    """
    Parse stat description strings into structured stats
    
    Examples:
        "+10 to maximum Life" -> {'increased_life': 10}
        "10% increased Spell Damage" -> {'increased_spell_damage': 10}
        "5% increased Cast Speed" -> {'increased_cast_speed': 5}
    """
    stats = {}
    
    for desc in stat_descriptions:
        desc_lower = desc.lower()
        
        # Extract numeric value
        value_match = re.search(r'([\+\-]?\d+(?:\.\d+)?)', desc)
        if not value_match:
            continue
        
        value = float(value_match.group(1))
        
        # Parse different stat types
        
        # Life
        if 'maximum life' in desc_lower:
            stats['increased_life'] = stats.get('increased_life', 0) + value
        elif 'life' in desc_lower and 'increased' in desc_lower:
            stats['increased_life'] = stats.get('increased_life', 0) + value
        
        # Energy Shield
        if 'maximum energy shield' in desc_lower:
            stats['increased_energy_shield'] = stats.get('increased_energy_shield', 0) + value
        elif 'energy shield' in desc_lower and 'increased' in desc_lower:
            stats['increased_energy_shield'] = stats.get('increased_energy_shield', 0) + value
        
        # Armour
        if 'armour' in desc_lower and 'increased' in desc_lower:
            stats['increased_armour'] = stats.get('increased_armour', 0) + value
        
        # Evasion
        if 'evasion' in desc_lower and 'increased' in desc_lower:
            stats['increased_evasion'] = stats.get('increased_evasion', 0) + value
        
        # Damage types
        if 'spell damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_spell_damage'] = stats.get('increased_spell_damage', 0) + value
        
        if 'attack damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_attack_damage'] = stats.get('increased_attack_damage', 0) + value
        
        if 'physical damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_physical_damage'] = stats.get('increased_physical_damage', 0) + value
        
        if 'fire damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_fire_damage'] = stats.get('increased_fire_damage', 0) + value
        
        if 'cold damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_cold_damage'] = stats.get('increased_cold_damage', 0) + value
        
        if 'lightning damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_lightning_damage'] = stats.get('increased_lightning_damage', 0) + value
        
        if 'chaos damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_chaos_damage'] = stats.get('increased_chaos_damage', 0) + value
        
        if 'elemental damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_elemental_damage'] = stats.get('increased_elemental_damage', 0) + value
        
        # Specific combinations
        if 'spell fire damage' in desc_lower or 'fire spell damage' in desc_lower:
            stats['increased_fire_spell_damage'] = stats.get('increased_fire_spell_damage', 0) + value
        
        if 'spell cold damage' in desc_lower or 'cold spell damage' in desc_lower:
            stats['increased_cold_spell_damage'] = stats.get('increased_cold_spell_damage', 0) + value
        
        if 'spell lightning damage' in desc_lower or 'lightning spell damage' in desc_lower:
            stats['increased_lightning_spell_damage'] = stats.get('increased_lightning_spell_damage', 0) + value
        
        # Area/Projectile/Melee
        if 'area damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_area_damage'] = stats.get('increased_area_damage', 0) + value
        
        if 'projectile damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_projectile_damage'] = stats.get('increased_projectile_damage', 0) + value
        
        if 'melee damage' in desc_lower and 'increased' in desc_lower:
            stats['increased_melee_damage'] = stats.get('increased_melee_damage', 0) + value
        
        # Cast/Attack Speed
        if 'cast speed' in desc_lower and 'increased' in desc_lower:
            stats['increased_cast_speed'] = stats.get('increased_cast_speed', 0) + value
        
        if 'attack speed' in desc_lower and 'increased' in desc_lower:
            stats['increased_attack_speed'] = stats.get('increased_attack_speed', 0) + value
        
        # Critical Strike
        if 'critical strike chance' in desc_lower and 'increased' in desc_lower:
            stats['increased_critical_strike_chance'] = stats.get('increased_critical_strike_chance', 0) + value
        elif 'critical strike chance' in desc_lower and '+' in desc:
            stats['critical_strike_chance'] = stats.get('critical_strike_chance', 0) + value
        
        if 'critical strike multiplier' in desc_lower:
            stats['increased_critical_strike_multiplier'] = stats.get('increased_critical_strike_multiplier', 0) + value
        
        # Spell crit
        if 'spell critical strike chance' in desc_lower:
            stats['spell_critical_strike_chance'] = stats.get('spell_critical_strike_chance', 0) + value
        
        # Area of Effect
        if 'area of effect' in desc_lower and 'increased' in desc_lower:
            stats['increased_area_of_effect'] = stats.get('increased_area_of_effect', 0) + value
        
        # Duration
        if 'skill effect duration' in desc_lower and 'increased' in desc_lower:
            stats['increased_skill_effect_duration'] = stats.get('increased_skill_effect_duration', 0) + value
        
        # Projectiles
        if 'additional projectile' in desc_lower:
            stats['additional_projectiles'] = stats.get('additional_projectiles', 0) + abs(value)
        
        # Resistances
        if 'fire resistance' in desc_lower:
            stats['fire_resistance'] = stats.get('fire_resistance', 0) + value
        if 'cold resistance' in desc_lower:
            stats['cold_resistance'] = stats.get('cold_resistance', 0) + value
        if 'lightning resistance' in desc_lower:
            stats['lightning_resistance'] = stats.get('lightning_resistance', 0) + value
        if 'chaos resistance' in desc_lower:
            stats['chaos_resistance'] = stats.get('chaos_resistance', 0) + value
        if 'all elemental resistances' in desc_lower:
            stats['fire_resistance'] = stats.get('fire_resistance', 0) + value
            stats['cold_resistance'] = stats.get('cold_resistance', 0) + value
            stats['lightning_resistance'] = stats.get('lightning_resistance', 0) + value
    
    return stats


def create_simple_node_stats_for_testing():
    """Create a simple node stats file for testing when tree.lua isn't available"""
    nodes = []
    
    # Create 412 nodes with randomized stats
    import random
    random.seed(42)
    
    stat_templates = [
        {'increased_spell_damage': 10, 'increased_cast_speed': 3},
        {'increased_physical_damage': 12, 'increased_attack_speed': 4},
        {'increased_fire_damage': 10, 'increased_area_damage': 8},
        {'increased_cold_damage': 10, 'increased_projectile_damage': 8},
        {'increased_lightning_damage': 10, 'increased_cast_speed': 3},
        {'increased_life': 8, 'increased_armour': 10},
        {'increased_life': 6, 'increased_evasion': 10},
        {'increased_energy_shield': 8, 'increased_spell_damage': 6},
        {'increased_critical_strike_chance': 20, 'increased_critical_strike_multiplier': 10},
        {'increased_area_of_effect': 10, 'increased_area_damage': 12},
    ]
    
    for i in range(412):
        template = random.choice(stat_templates)
        nodes.append({
            'id': i,
            'name': f"Node_{i}",
            'stats': template.copy(),
            'is_notable': i % 20 == 0,
            'is_keystone': i % 100 == 0,
            'is_mastery': False,
            'is_ascendancy': False
        })
    
    return {'nodes': nodes, 'total_nodes': len(nodes)}


if __name__ == "__main__":
    # Try to find tree.lua
    possible_paths = [
        "../PathOfBuilding/src/TreeData/3_27/tree.lua",
        "../../PathOfBuilding/src/TreeData/3_27/tree.lua",
        "../pob_data/tree_data/tree.lua"
    ]
    
    tree_lua_path = None
    for path in possible_paths:
        if Path(path).exists():
            tree_lua_path = path
            break
    
    output_path = "../pob_data/tree_data/node_stats.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    if tree_lua_path:
        print(f"Found tree.lua at {tree_lua_path}")
        print("Parsing PoB tree data...")
        nodes = parse_lua_tree_to_node_stats(tree_lua_path, output_path)
        
        # Print some statistics
        print(f"\nStatistics:")
        print(f"  Total nodes: {len(nodes)}")
        print(f"  Notables: {sum(1 for n in nodes if n['is_notable'])}")
        print(f"  Keystones: {sum(1 for n in nodes if n['is_keystone'])}")
        print(f"  Masteries: {sum(1 for n in nodes if n['is_mastery'])}")
        
        # Show example node
        for node in nodes:
            if node['stats']:
                print(f"\nExample node: {node['name']} (ID: {node['id']})")
                print(f"  Stats: {node['stats']}")
                break
    else:
        print("Could not find tree.lua, creating simple test data...")
        test_data = create_simple_node_stats_for_testing()
        with open(output_path, 'w') as f:
            json.dump(test_data, f, indent=2)
        print(f"Created test data at {output_path}")
