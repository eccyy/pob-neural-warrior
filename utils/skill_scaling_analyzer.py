"""
Skill Scaling Analyzer
Extracts relevant scaling vectors from Path of Building calculations
for skill-specific passive tree optimization.
"""

import numpy as np
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class ScalingVector:
    """Represents which stats scale a given skill"""
    # Damage scaling
    increased_damage_types: List[str]  # e.g., ['spell', 'fire', 'elemental', 'area']
    added_damage_types: List[str]  # e.g., ['fire_to_spells', 'lightning_to_spells']
    
    # Attack/cast speed
    speed_type: str  # 'attack_speed', 'cast_speed', or 'none' (for DoT)
    
    # Crit scaling
    scales_with_crit: bool
    crit_types: List[str]  # e.g., ['spell_crit', 'fire_crit', 'global_crit']
    
    # Other multipliers
    duration_scaling: bool
    area_scaling: bool
    projectile_scaling: bool
    
    # Defensive priorities (based on skill playstyle)
    defensive_priority: Dict[str, float]  # {'life': 0.8, 'es': 0.2, 'evasion': 0.5}
    
    # Skill tags (from PoB)
    tags: Set[str]


class SkillScalingAnalyzer:
    """
    Analyzes skills to determine which passive tree nodes are relevant
    Uses PoB's skill tags and damage calculations
    """
    
    def __init__(self):
        self.skill_database = self._load_skill_database()
        self.stat_weights = {}
    
    def _load_skill_database(self) -> Dict:
        """Load skill properties from PoB data"""
        # Try to load from pob_data
        skill_db_path = Path("../pob_data/gems/skill_database.json")
        if skill_db_path.exists():
            with open(skill_db_path) as f:
                return json.load(f)
        
        # Fallback to embedded database
        return {
            'Lightning Strike': {
                'tags': ['attack', 'projectile', 'melee', 'lightning', 'strike'],
                'damage_type': 'attack',
                'added_damage_effectiveness': 100,
                'has_projectile': True,
                'can_crit': True
            },
            'Blade Vortex': {
                'tags': ['spell', 'physical', 'area', 'duration'],
                'damage_type': 'spell',
                'added_damage_effectiveness': 100,
                'has_projectile': False,
                'can_crit': True
            },
            'Righteous Fire': {
                'tags': ['spell', 'fire', 'area', 'dot', 'aura'],
                'damage_type': 'dot',
                'added_damage_effectiveness': 0,
                'has_projectile': False,
                'can_crit': False
            },
            'Toxic Rain': {
                'tags': ['attack', 'projectile', 'chaos', 'dot', 'bow', 'area'],
                'damage_type': 'dot',
                'added_damage_effectiveness': 40,
                'has_projectile': True,
                'can_crit': False  # DoT doesn't crit
            },
            'Ice Spear': {
                'tags': ['spell', 'projectile', 'cold'],
                'damage_type': 'spell',
                'added_damage_effectiveness': 100,
                'has_projectile': True,
                'can_crit': True
            },
            'Cyclone': {
                'tags': ['attack', 'melee', 'area', 'physical', 'channelling'],
                'damage_type': 'attack',
                'added_damage_effectiveness': 50,
                'has_projectile': False,
                'can_crit': True
            },
        }
    
    def analyze_skill(self, skill_name: str, support_gems: List[str] = None) -> ScalingVector:
        """
        Analyze a skill to determine its scaling vectors
        
        Args:
            skill_name: Name of the main skill gem
            support_gems: List of support gems (optional, affects scaling)
            
        Returns:
            ScalingVector with all relevant scaling stats
        """
        if skill_name not in self.skill_database:
            # Return generic scaling for unknown skills
            return self._get_generic_scaling()
        
        skill_data = self.skill_database[skill_name]
        tags = set(skill_data.get('tags', []))
        
        # Determine damage type scaling
        increased_damage_types = self._get_increased_damage_types(tags, support_gems, skill_name)
        added_damage_types = self._get_added_damage_types(tags, skill_data)
        
        # Speed scaling
        speed_type = self._determine_speed_type(skill_data, tags)
        
        # Crit scaling
        scales_with_crit = skill_data.get('can_crit', False)
        crit_types = self._get_crit_types(tags) if scales_with_crit else []
        
        # Other mechanics
        duration_scaling = 'duration' in tags
        area_scaling = 'area' in tags
        projectile_scaling = 'projectile' in tags or skill_data.get('has_projectile', False)
        
        # Defensive priorities (based on skill playstyle)
        defensive_priority = self._determine_defensive_priorities(tags)
        
        return ScalingVector(
            increased_damage_types=increased_damage_types,
            added_damage_types=added_damage_types,
            speed_type=speed_type,
            scales_with_crit=scales_with_crit,
            crit_types=crit_types,
            duration_scaling=duration_scaling,
            area_scaling=area_scaling,
            projectile_scaling=projectile_scaling,
            defensive_priority=defensive_priority,
            tags=tags
        )
    
    def _get_increased_damage_types(self, tags: Set[str], support_gems: List[str] = None, skill_name: str = None) -> List[str]:
        """
        Determine which "increased damage" modifiers apply
        Returns in order of specificity (most specific first)
        """
        damage_types = []
        
        # Special case: Righteous Fire scales with Life/ES (base damage = 70% of Life + 70% of ES)
        if skill_name and 'righteous fire' in skill_name.lower():
            damage_types.extend([
                'increased_maximum_life',
                'increased_maximum_energy_shield',
                'maximum_life',
                'maximum_energy_shield',
            ])
        
        # Most specific: skill type + element
        if 'spell' in tags:
            if 'fire' in tags:
                damage_types.extend(['fire_spell_damage', 'spell_fire_damage'])
            if 'cold' in tags:
                damage_types.extend(['cold_spell_damage', 'spell_cold_damage'])
            if 'lightning' in tags:
                damage_types.extend(['lightning_spell_damage', 'spell_lightning_damage'])
            if 'physical' in tags:
                damage_types.extend(['physical_spell_damage', 'spell_physical_damage'])
            if 'chaos' in tags:
                damage_types.extend(['chaos_spell_damage', 'spell_chaos_damage'])
        
        if 'attack' in tags:
            if 'fire' in tags:
                damage_types.extend(['fire_attack_damage', 'attack_fire_damage'])
            if 'cold' in tags:
                damage_types.extend(['cold_attack_damage', 'attack_cold_damage'])
            if 'lightning' in tags:
                damage_types.extend(['lightning_attack_damage', 'attack_lightning_damage'])
            if 'physical' in tags:
                damage_types.extend(['physical_attack_damage', 'attack_physical_damage'])
            if 'chaos' in tags:
                damage_types.extend(['chaos_attack_damage', 'attack_chaos_damage'])
        
        # Medium specificity: skill type or element
        if 'spell' in tags:
            damage_types.append('spell_damage')
        if 'attack' in tags:
            damage_types.append('attack_damage')
        
        if 'fire' in tags:
            damage_types.extend(['fire_damage', 'burning_damage'])
        if 'cold' in tags:
            damage_types.append('cold_damage')
        if 'lightning' in tags:
            damage_types.append('lightning_damage')
        if 'physical' in tags:
            damage_types.append('physical_damage')
        if 'chaos' in tags:
            damage_types.append('chaos_damage')
        
        # Elemental (fire/cold/lightning)
        if any(tag in tags for tag in ['fire', 'cold', 'lightning']):
            damage_types.append('elemental_damage')
        
        # Archetype modifiers
        if 'projectile' in tags:
            damage_types.append('projectile_damage')
        if 'area' in tags:
            damage_types.append('area_damage')
        if 'melee' in tags:
            damage_types.append('melee_damage')
        if 'bow' in tags:
            damage_types.append('bow_damage')
        if 'wand' in tags:
            damage_types.append('wand_damage')
        if 'dot' in tags:
            damage_types.extend(['damage_over_time', 'dot'])
        if 'minion' in tags:
            damage_types.append('minion_damage')
        if 'totem' in tags:
            damage_types.append('totem_damage')
        if 'trap' in tags:
            damage_types.append('trap_damage')
        if 'mine' in tags:
            damage_types.append('mine_damage')
        
        # Global (least specific)
        damage_types.append('damage')
        
        # Check support gems for conversion
        if support_gems:
            if any('to fire' in gem.lower() for gem in support_gems):
                damage_types.extend(['fire_damage', 'elemental_damage'])
            if any('to cold' in gem.lower() for gem in support_gems):
                damage_types.extend(['cold_damage', 'elemental_damage'])
            if any('to lightning' in gem.lower() for gem in support_gems):
                damage_types.extend(['lightning_damage', 'elemental_damage'])
        
        return damage_types
    
    def _get_added_damage_types(self, tags: Set[str], skill_data: Dict) -> List[str]:
        """Determine which flat added damage applies"""
        added_types = []
        
        effectiveness = skill_data.get('added_damage_effectiveness', 100)
        if effectiveness == 0:
            return []  # DoT skills don't benefit from added damage
        
        if 'spell' in tags:
            added_types.extend([
                'added_fire_damage_to_spells',
                'added_cold_damage_to_spells',
                'added_lightning_damage_to_spells',
                'added_chaos_damage_to_spells',
                'added_physical_damage_to_spells'
            ])
        
        if 'attack' in tags:
            if 'bow' in tags:
                added_types.append('added_damage_to_bow_attacks')
            if 'wand' in tags:
                added_types.append('added_damage_to_wand_attacks')
            
            added_types.extend([
                'added_fire_damage_to_attacks',
                'added_cold_damage_to_attacks',
                'added_lightning_damage_to_attacks',
                'added_chaos_damage_to_attacks',
                'added_physical_damage'
            ])
        
        return added_types
    
    def _determine_speed_type(self, skill_data: Dict, tags: Set[str]) -> str:
        """Determine if skill scales with attack speed or cast speed"""
        if 'dot' in tags and 'attack' not in tags:
            return 'none'  # Pure DoT skills don't scale with speed
        
        if 'spell' in tags:
            return 'cast_speed'
        if 'attack' in tags:
            return 'attack_speed'
        
        return 'none'
    
    def _get_crit_types(self, tags: Set[str]) -> List[str]:
        """Determine which crit modifiers apply"""
        crit_types = []
        
        if 'spell' in tags:
            crit_types.extend(['spell_critical_strike_chance', 'spell_critical_strike_multiplier'])
        if 'attack' in tags:
            crit_types.extend(['attack_critical_strike_chance', 'attack_critical_strike_multiplier'])
        
        # Element-specific crit
        if 'fire' in tags:
            crit_types.extend(['fire_critical_strike_chance', 'fire_critical_strike_multiplier'])
        if 'cold' in tags:
            crit_types.extend(['cold_critical_strike_chance', 'cold_critical_strike_multiplier'])
        if 'lightning' in tags:
            crit_types.extend(['lightning_critical_strike_chance', 'lightning_critical_strike_multiplier'])
        
        # Global
        crit_types.extend(['critical_strike_chance', 'critical_strike_multiplier'])
        
        return crit_types
    
    def _determine_defensive_priorities(self, tags: Set[str]) -> Dict[str, float]:
        """
        Determine defensive stat priorities based on skill playstyle
        Returns weights (0.0 to 1.0) for each defensive layer
        """
        priorities = {
            'life': 1.0,  # Everyone needs life
            'energy_shield': 0.3,
            'armour': 0.5,
            'evasion': 0.5,
            'block': 0.4,
            'suppression': 0.4,
            'max_resist': 0.6,
        }
        
        # Melee builds need more defense (closer to enemies)
        if 'melee' in tags:
            priorities['armour'] = 0.8
            priorities['life'] = 1.0
            priorities['block'] = 0.7
        
        # Ranged builds can invest less in defense
        if 'projectile' in tags or 'bow' in tags:
            priorities['evasion'] = 0.8
            priorities['suppression'] = 0.8
            priorities['life'] = 0.9
        
        # Channelling skills are stationary (need more defense)
        if 'channelling' in tags:
            priorities['life'] = 1.0
            priorities['max_resist'] = 0.9
        
        # DoT builds can be more mobile
        if 'dot' in tags:
            priorities['life'] = 0.9
            priorities['evasion'] = 0.7
        
        # Spell builds often go ES
        if 'spell' in tags and 'attack' not in tags:
            priorities['energy_shield'] = 0.7
            priorities['life'] = 0.8
        
        return priorities
    
    def _get_generic_scaling(self) -> ScalingVector:
        """Return generic scaling for unknown skills"""
        return ScalingVector(
            increased_damage_types=['damage', 'elemental_damage'],
            added_damage_types=[],
            speed_type='none',
            scales_with_crit=True,
            crit_types=['critical_strike_chance', 'critical_strike_multiplier'],
            duration_scaling=False,
            area_scaling=False,
            projectile_scaling=False,
            defensive_priority={'life': 1.0, 'armour': 0.5, 'evasion': 0.5},
            tags=set()
        )
    
    def calculate_node_relevance(
        self,
        scaling_vector: ScalingVector,
        node_stats: Dict[str, float]
    ) -> float:
        """
        Calculate how relevant a passive node is for a given skill
        
        Args:
            scaling_vector: Skill's scaling requirements
            node_stats: Stats provided by the passive node
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        relevance = 0.0
        total_weight = 0.0
        
        # Check offensive stats
        for damage_type in scaling_vector.increased_damage_types:
            stat_key = f"increased_{damage_type}"
            if stat_key in node_stats:
                # Weight by specificity (earlier in list = more specific = higher weight)
                specificity = 1.0 / (scaling_vector.increased_damage_types.index(damage_type) + 1)
                relevance += node_stats[stat_key] * specificity * 1.0
                total_weight += specificity * 1.0
        
        # Attack/cast speed
        if scaling_vector.speed_type != 'none':
            speed_key = f"increased_{scaling_vector.speed_type}"
            if speed_key in node_stats:
                relevance += node_stats[speed_key] * 0.8
                total_weight += 0.8
        
        # Crit scaling
        if scaling_vector.scales_with_crit:
            for crit_type in scaling_vector.crit_types:
                if crit_type in node_stats:
                    relevance += node_stats[crit_type] * 0.9
                    total_weight += 0.9
        
        # Duration/area/projectile
        if scaling_vector.duration_scaling and 'increased_skill_effect_duration' in node_stats:
            relevance += node_stats['increased_skill_effect_duration'] * 0.6
            total_weight += 0.6
        
        if scaling_vector.area_scaling and 'increased_area_of_effect' in node_stats:
            relevance += node_stats['increased_area_of_effect'] * 0.7
            total_weight += 0.7
        
        if scaling_vector.projectile_scaling:
            if 'increased_projectile_damage' in node_stats:
                relevance += node_stats['increased_projectile_damage'] * 0.8
                total_weight += 0.8
            if 'additional_projectiles' in node_stats:
                relevance += node_stats['additional_projectiles'] * 2.0  # Very valuable
                total_weight += 2.0
        
        # Defensive stats (weighted by priority)
        for def_stat, priority in scaling_vector.defensive_priority.items():
            stat_key = f"increased_{def_stat}"
            if stat_key in node_stats:
                relevance += node_stats[stat_key] * priority * 0.5
                total_weight += priority * 0.5
        
        # Normalize
        if total_weight > 0:
            return min(relevance / total_weight, 1.0)
        return 0.0
    
    def filter_relevant_nodes(
        self,
        skill_name: str,
        all_nodes: List[Dict],
        support_gems: List[str] = None,
        threshold: float = 0.3
    ) -> List[int]:
        """
        Filter passive tree nodes to only those relevant for a skill
        
        Args:
            skill_name: Main skill gem name
            all_nodes: List of all passive nodes with their stats
            support_gems: Support gems (affects conversion/tags)
            threshold: Minimum relevance score to include node
            
        Returns:
            List of relevant node IDs
        """
        scaling = self.analyze_skill(skill_name, support_gems)
        relevant_nodes = []
        
        for node in all_nodes:
            node_id = node.get('id')
            node_stats = node.get('stats', {})
            
            relevance = self.calculate_node_relevance(scaling, node_stats)
            
            if relevance >= threshold:
                relevant_nodes.append(node_id)
        
        return relevant_nodes


# Example usage
if __name__ == "__main__":
    analyzer = SkillScalingAnalyzer()
    
    # Analyze Blade Vortex
    bv_scaling = analyzer.analyze_skill("Blade Vortex", support_gems=["Controlled Destruction", "Elemental Focus"])
    print(f"Blade Vortex Scaling:")
    print(f"  Damage types: {bv_scaling.increased_damage_types[:5]}")
    print(f"  Speed: {bv_scaling.speed_type}")
    print(f"  Crit: {bv_scaling.scales_with_crit}")
    print(f"  Area: {bv_scaling.area_scaling}")
    
    # Test node relevance
    test_node = {
        'id': 12345,
        'stats': {
            'increased_spell_damage': 10,
            'increased_physical_damage': 12,
            'increased_area_of_effect': 8,
            'increased_cast_speed': 5
        }
    }
    
    relevance = analyzer.calculate_node_relevance(bv_scaling, test_node['stats'])
    print(f"\nNode relevance for Blade Vortex: {relevance:.2f}")
