"""
Feature extraction from Path of Building builds
Converts PoB build codes into numeric vectors for ML
"""

import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path

# Try to import PathOfBuildingAPI (optional for now)
try:
    from pobapi import PoBImporter
    POBAPI_AVAILABLE = True
except ImportError:
    POBAPI_AVAILABLE = False
    print("PathOfBuildingAPI not installed. Install with: pip install PathOfBuildingAPI")


class BuildFeatureExtractor:
    """Extract numeric features from PoB builds for ML"""
    
    # Constants (update based on actual tree data)
    TOTAL_NODES = 1500  # Approximate number of passive nodes
    MAX_BUDGET = 123    # Max passive points (level 100 + quests)
    
    def __init__(self):
        self.node_id_map = {}  # Map node IDs to vector indices
        self._init_node_mapping()
    
    def _init_node_mapping(self):
        """Create mapping from node IDs to vector indices"""
        # This should be loaded from the actual passive tree data
        # For now, use a simple sequential mapping
        for i in range(self.TOTAL_NODES):
            self.node_id_map[i] = i
    
    def encode_tree(self, allocated_nodes: List[int]) -> np.ndarray:
        """
        Encode passive tree as one-hot vector
        
        Args:
            allocated_nodes: List of allocated node IDs
            
        Returns:
            Binary vector of length TOTAL_NODES
        """
        vec = np.zeros(self.TOTAL_NODES, dtype=np.float32)
        for node_id in allocated_nodes:
            if node_id in self.node_id_map:
                vec[self.node_id_map[node_id]] = 1
        return vec
    
    def encode_gear(self, items: List) -> np.ndarray:
        """
        Encode gear into stat vector
        
        Args:
            items: List of item objects from PoB
            
        Returns:
            Vector of aggregated gear stats
        """
        stats = {
            # Defense
            "life": 0,
            "energy_shield": 0,
            "armour": 0,
            "evasion": 0,
            "res_fire": 0,
            "res_cold": 0,
            "res_lightning": 0,
            "res_chaos": 0,
            
            # Offense
            "phys_dmg": 0,
            "fire_dmg": 0,
            "cold_dmg": 0,
            "lightning_dmg": 0,
            "chaos_dmg": 0,
            "crit_chance": 0,
            "crit_multi": 0,
            "attack_speed": 0,
            "cast_speed": 0,
            
            # Special
            "move_speed": 0,
        }
        
        # TODO: Parse item mods and update stats
        # This requires understanding PoB's mod format
        for item in items:
            # Placeholder - actual implementation needed
            pass
        
        return np.array(list(stats.values()), dtype=np.float32)
    
    def encode_skills(self, skills: List) -> np.ndarray:
        """
        Encode skill gems
        
        Args:
            skills: List of skill objects
            
        Returns:
            Vector encoding main skill and supports
        """
        # Simplified: One-hot for main skill type
        skill_types = [
            "attack", "spell", "minion", "totem", "trap", "mine",
            "warcry", "aura", "curse", "movement", "vaal"
        ]
        vec = np.zeros(len(skill_types), dtype=np.float32)
        
        # TODO: Parse skills and set appropriate flags
        
        return vec
    
    def encode_build(self, build) -> np.ndarray:
        """
        Encode complete build into feature vector
        
        Args:
            build: PoB build object
            
        Returns:
            Concatenated feature vector
        """
        tree_vec = self.encode_tree(build.tree.nodes if hasattr(build, 'tree') else [])
        gear_vec = self.encode_gear(build.items if hasattr(build, 'items') else [])
        skill_vec = self.encode_skills(build.skills if hasattr(build, 'skills') else [])
        
        # Combine all features
        return np.concatenate([tree_vec, gear_vec, skill_vec])
    
    def extract_target(self, build) -> float:
        """
        Extract target value (score) from build
        
        Args:
            build: PoB build with calculated stats
            
        Returns:
            Performance score (higher is better)
        """
        if not hasattr(build, 'stats'):
            return 0.0
        
        stats = build.stats
        
        # Get DPS (various sources)
        dps = 0.0
        if hasattr(stats, 'CombinedDPS'):
            dps = stats.CombinedDPS
        elif hasattr(stats, 'TotalDPS'):
            dps = stats.TotalDPS
        
        # Get EHP
        ehp = 0.0
        if hasattr(stats, 'TotalEHP'):
            ehp = stats.TotalEHP
        elif hasattr(stats, 'Life'):
            # Rough estimate if EHP not available
            ehp = stats.Life * (1 + stats.get('PhysicalDamageReduction', 0) / 100)
        
        # Combined score (configurable weights)
        score = dps * 0.7 + ehp * 0.3
        
        return score


def load_build_from_code(build_code: str):
    """
    Load build from PoB code
    
    Args:
        build_code: Base64 encoded PoB build string
        
    Returns:
        Build object or None if failed
    """
    if not POBAPI_AVAILABLE:
        print("PathOfBuildingAPI not available. Cannot parse build.")
        return None
    
    try:
        imp = PoBImporter()
        build = imp.import_code(build_code)
        return build
    except Exception as e:
        print(f"Error loading build: {e}")
        return None


def extract_features_from_code(build_code: str) -> Tuple[np.ndarray, float]:
    """
    Extract features and target from build code
    
    Args:
        build_code: PoB build code string
        
    Returns:
        (feature_vector, target_score)
    """
    build = load_build_from_code(build_code)
    if build is None:
        return None, None
    
    extractor = BuildFeatureExtractor()
    features = extractor.encode_build(build)
    target = extractor.extract_target(build)
    
    return features, target


if __name__ == "__main__":
    # Test feature extraction
    print("Feature Extractor Test")
    print("=" * 50)
    
    extractor = BuildFeatureExtractor()
    
    # Test with dummy data
    dummy_nodes = [1, 5, 10, 15, 20]
    tree_vec = extractor.encode_tree(dummy_nodes)
    print(f"Tree vector shape: {tree_vec.shape}")
    print(f"Allocated nodes: {tree_vec.sum()}")
    
    gear_vec = extractor.encode_gear([])
    print(f"Gear vector shape: {gear_vec.shape}")
    
    skill_vec = extractor.encode_skills([])
    print(f"Skill vector shape: {skill_vec.shape}")
    
    total_dim = len(tree_vec) + len(gear_vec) + len(skill_vec)
    print(f"\nTotal feature dimension: {total_dim}")
    
    if POBAPI_AVAILABLE:
        print("\nPathOfBuildingAPI is available - ready for real builds!")
    else:
        print("\nInstall PathOfBuildingAPI to parse real builds:")
        print("  pip install PathOfBuildingAPI")
