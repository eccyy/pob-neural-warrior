"""
Skill Database
Contains base properties for Path of Exile skills
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class SkillProperties:
    """Base properties for a skill"""
    name: str
    damage_type: str
    base_damage_min: float
    base_damage_max: float
    base_speed: float
    damage_effectiveness: float
    tags: List[str]
    crit_chance: float


SKILL_DATABASE: Dict[str, SkillProperties] = {
    'Lightning Strike': SkillProperties('Lightning Strike', 'attack', 5, 12, 1.2, 1.0, ['attack', 'projectile', 'melee', 'lightning'], 5.0),
    'Ice Spear': SkillProperties('Ice Spear', 'spell', 27, 40, 0.65, 1.0, ['spell', 'projectile', 'cold'], 7.0),
    'Earthquake': SkillProperties('Earthquake', 'attack', 180, 220, 1.0, 2.2, ['attack', 'melee', 'area', 'physical', 'slam'], 5.0),
    'Toxic Rain': SkillProperties('Toxic Rain', 'dot', 100, 150, 0.8, 0.4, ['attack', 'projectile', 'area', 'chaos', 'dot', 'bow'], 5.0),
    'Righteous Fire': SkillProperties('Righteous Fire', 'dot', 1500, 1500, 1.0, 0.0, ['spell', 'area', 'fire', 'dot', 'aura'], 0.0),
    'Cyclone': SkillProperties('Cyclone', 'attack', 50, 75, 0.3, 0.5, ['attack', 'melee', 'area', 'physical', 'channelling'], 5.0),
    'Blade Vortex': SkillProperties('Blade Vortex', 'spell', 35, 52, 0.6, 1.0, ['spell', 'area', 'physical', 'duration'], 6.0),
    'Spark': SkillProperties('Spark', 'spell', 18, 54, 0.65, 1.0, ['spell', 'projectile', 'lightning', 'duration'], 6.0),
}


def get_skill_index(skill_name: str):
    """Get the index of a skill in the database"""
    skill_list = list(SKILL_DATABASE.keys())
    try:
        return skill_list.index(skill_name)
    except ValueError:
        return None


def get_all_skills() -> List[str]:
    """Get list of all skill names"""
    return list(SKILL_DATABASE.keys())


def get_skill(skill_name: str) -> SkillProperties:
    """Get skill properties by name"""
    return SKILL_DATABASE.get(skill_name)


def calculate_base_dps(skill: SkillProperties, added_flat_damage: float = 0) -> float:
    """Calculate base DPS from skill properties"""
    if skill.damage_type == 'dot':
        return (skill.base_damage_min + skill.base_damage_max) / 2
    else:
        avg_base = (skill.base_damage_min + skill.base_damage_max) / 2
        avg_added = added_flat_damage * skill.damage_effectiveness
        total_damage = avg_base + avg_added
        hits_per_second = 1.0 / skill.base_speed
        return total_damage * hits_per_second
