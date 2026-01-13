"""
Path of Building Build Importer
Parses PoB XML files and build codes to extract features
"""

import json
import base64
import zlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import re


class PoBImporter:
    """Import and parse Path of Building builds"""
    
    def __init__(self, tree_dim: int = 1500, gear_dim: int = 500, gem_dim: int = 100):
        self.tree_dim = tree_dim
        self.gear_dim = gear_dim
        self.gem_dim = gem_dim
        
        # Load tree data if available
        self.tree_nodes = self._load_tree_nodes()
        
    def _load_tree_nodes(self) -> Dict:
        """Load passive tree node definitions and mapping"""
        # Load node mapping (node_id -> array_index)
        possible_paths = [
            Path("./pob_data/tree_data/node_mapping.json"),
            Path("../pob_data/tree_data/node_mapping.json"),
            Path("../../pob_data/tree_data/node_mapping.json")
        ]
        
        for mapping_file in possible_paths:
            if mapping_file.exists():
                with open(mapping_file) as f:
                    mapping_data = json.load(f)
                    # We want node_to_index mapping
                    return mapping_data.get('node_to_index', {})
        
        # Fallback: load parsed nodes
        tree_file = Path("../../pob_data/tree_data/parsed_nodes.json")
        if tree_file.exists():
            with open(tree_file) as f:
                return json.load(f)
        return {}
    
    def import_from_code(self, build_code: str) -> Dict:
        """
        Import build from PoB build code (base64 encoded)
        
        Args:
            build_code: Base64 encoded build string from PoB
            
        Returns:
            Dictionary with build data
        """
        try:
            # PoB uses base64 + zlib compression
            # Remove any whitespace
            build_code = build_code.strip().replace('\n', '').replace('\r', '')
            
            # Decode base64
            compressed = base64.b64decode(build_code)
            
            # Decompress
            xml_data = zlib.decompress(compressed)
            
            # Parse XML
            root = ET.fromstring(xml_data)
            
            return self.import_from_xml(root)
            
        except Exception as e:
            print(f"Error importing build code: {e}")
            return None
    
    def import_from_file(self, xml_path: str) -> Dict:
        """
        Import build from PoB XML file
        
        Args:
            xml_path: Path to .xml file
            
        Returns:
            Dictionary with build data
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            return self.import_from_xml(root)
        except Exception as e:
            print(f"Error importing build file: {e}")
            return None
    
    def import_from_xml(self, root: ET.Element) -> Dict:
        """
        Parse PoB XML structure
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary with extracted features
        """
        build_data = {
            'metadata': {},
            'features': {
                'tree': np.zeros(self.tree_dim, dtype=np.float32),
                'gear': np.zeros(self.gear_dim, dtype=np.float32),
                'gems': np.zeros(self.gem_dim, dtype=np.float32),
                'skill': np.zeros(8, dtype=np.float32)  # 8 skills in database
            },
            'targets': {
                'dps': 0.0,
                'life': 0.0,
                'es': 0.0
            }
        }
        
        # Parse Build section
        build_elem = root.find('Build')
        if build_elem is not None:
            build_data['metadata']['class'] = build_elem.get('className', 'Unknown')
            build_data['metadata']['level'] = int(build_elem.get('level', 1))
            build_data['metadata']['ascendancy'] = build_elem.get('ascendClassName', 'None')
        
        # Parse Tree section - MOST IMPORTANT
        tree_elem = root.find('Tree')
        if tree_elem is not None:
            spec_elem = tree_elem.find('Spec')
            if spec_elem is not None:
                nodes_str = spec_elem.get('nodes', '')
                if nodes_str:
                    # Parse comma-separated node IDs
                    node_ids = [int(n) for n in nodes_str.split(',') if n.strip()]
                    
                    # Convert node IDs to binary vector using mapping
                    nodes_mapped = 0
                    for node_id in node_ids:
                        node_id_str = str(node_id)
                        if node_id_str in self.tree_nodes:
                            # Use mapped index
                            array_idx = self.tree_nodes[node_id_str]
                            if array_idx < self.tree_dim:
                                build_data['features']['tree'][array_idx] = 1.0
                                nodes_mapped += 1
                    
                    build_data['metadata']['allocated_nodes'] = len(node_ids)
                    build_data['metadata']['mapped_nodes'] = nodes_mapped
                    print(f"[OK] Imported {len(node_ids)} passive tree nodes ({nodes_mapped} mapped)")
        
        # Parse Items section
        items_elem = root.find('Items')
        if items_elem is not None:
            build_data['features']['gear'] = self._parse_items(items_elem)
        
        # Parse Skills section
        skills_elem = root.find('Skills')
        if skills_elem is not None:
            gems_vec, main_skill = self._parse_skills(skills_elem)
            build_data['features']['gems'] = gems_vec
            build_data['metadata']['main_skill'] = main_skill
            
            # Set skill vector
            build_data['features']['skill'] = self._encode_skill(main_skill)
        
        # Parse Calcs section if available (performance data)
        calcs = root.find('.//Calcs')
        if calcs is not None:
            # Try to extract DPS, life, ES from calcs
            # This is complex - PoB stores computed stats here
            pass
        
        return build_data
    
    def _parse_items(self, items_elem: ET.Element) -> np.ndarray:
        """
        Parse gear items into feature vector
        
        For now, extract key stats from items:
        - Life, ES, Armour, Evasion
        - Elemental resistances
        - Damage stats
        """
        gear_vector = np.zeros(self.gear_dim, dtype=np.float32)
        
        # Simplified extraction - parse item text for stats
        for item in items_elem.findall('Item'):
            item_text = item.text or ''
            
            # Extract numeric stats using regex
            # Life: +X to maximum Life
            life_match = re.search(r'\+(\d+) to maximum Life', item_text)
            if life_match:
                gear_vector[0] += float(life_match.group(1))
            
            # ES: +X to maximum Energy Shield
            es_match = re.search(r'\+(\d+) to maximum Energy Shield', item_text)
            if es_match:
                gear_vector[1] += float(es_match.group(1))
            
            # Resistances
            fire_res = re.search(r'\+(\d+)% to Fire Resistance', item_text)
            if fire_res:
                gear_vector[10] += float(fire_res.group(1))
            
            cold_res = re.search(r'\+(\d+)% to Cold Resistance', item_text)
            if cold_res:
                gear_vector[11] += float(cold_res.group(1))
            
            lightning_res = re.search(r'\+(\d+)% to Lightning Resistance', item_text)
            if lightning_res:
                gear_vector[12] += float(lightning_res.group(1))
            
            # Weapon damage
            phys_dmg = re.search(r'Adds (\d+) to (\d+) Physical Damage', item_text)
            if phys_dmg:
                avg_dmg = (float(phys_dmg.group(1)) + float(phys_dmg.group(2))) / 2
                gear_vector[20] += avg_dmg
        
        # Normalize to 0-1 range
        gear_vector = np.clip(gear_vector / 1000.0, 0, 1)
        
        return gear_vector
    
    def _parse_skills(self, skills_elem: ET.Element) -> Tuple[np.ndarray, str]:
        """
        Parse skill gems into feature vector
        
        Returns:
            Tuple of (gem_vector, main_skill_name)
        """
        gem_vector = np.zeros(self.gem_dim, dtype=np.float32)
        main_skill = "Lightning Strike"  # Default
        
        # Find main skill group
        for skill_group in skills_elem.findall('Skill'):
            # Check if this is the main skill
            enabled = skill_group.get('enabled', 'true') == 'true'
            if not enabled:
                continue
            
            gems = []
            for gem in skill_group.findall('Gem'):
                gem_name = gem.get('nameSpec', '')
                gem_level = int(gem.get('level', 1))
                gem_quality = int(gem.get('quality', 0))
                
                gems.append({
                    'name': gem_name,
                    'level': gem_level,
                    'quality': gem_quality
                })
            
            # First gem is usually the active skill
            if gems:
                main_skill = gems[0]['name']
                
                # Encode support gems as features
                # For now, just count support types
                for i, gem in enumerate(gems[1:]):  # Skip main gem
                    if i < self.gem_dim:
                        # Simple encoding: gem level / 20
                        gem_vector[i] = gem['level'] / 20.0
                
                break  # Only process main skill group
        
        return gem_vector, main_skill
    
    def _encode_skill(self, skill_name: str) -> np.ndarray:
        """Encode skill name as one-hot vector"""
        from utils.skill_database import get_all_skills
        
        skills = get_all_skills()
        skill_vector = np.zeros(len(skills), dtype=np.float32)
        
        # Find matching skill (fuzzy match)
        skill_name_lower = skill_name.lower()
        for i, db_skill in enumerate(skills):
            if db_skill.lower() in skill_name_lower or skill_name_lower in db_skill.lower():
                skill_vector[i] = 1.0
                return skill_vector
        
        # Default to first skill if no match
        skill_vector[0] = 1.0
        return skill_vector
    
    def batch_import_from_directory(self, directory: str) -> List[Dict]:
        """
        Import all .xml builds from a directory
        
        Args:
            directory: Path to directory containing PoB XML files
            
        Returns:
            List of imported builds
        """
        builds = []
        xml_dir = Path(directory)
        
        if not xml_dir.exists():
            print(f"Directory not found: {directory}")
            return builds
        
        xml_files = list(xml_dir.glob("*.xml"))
        print(f"Found {len(xml_files)} XML files")
        
        for xml_file in xml_files:
            try:
                build = self.import_from_file(str(xml_file))
                if build:
                    build['metadata']['filename'] = xml_file.name
                    builds.append(build)
                    print(f"✓ Imported {xml_file.name}")
            except Exception as e:
                print(f"✗ Failed to import {xml_file.name}: {e}")
        
        return builds


if __name__ == "__main__":
    # Example usage
    importer = PoBImporter()
    
    # Test with an XML file
    test_file = "../../PathOfBuilding/src/Builds/~~temp~~.xml"
    if Path(test_file).exists():
        build = importer.import_from_file(test_file)
        if build:
            print("\nImported build:")
            print(f"Class: {build['metadata'].get('class')}")
            print(f"Level: {build['metadata'].get('level')}")
            print(f"Allocated nodes: {build['metadata'].get('allocated_nodes')}")
            print(f"Main skill: {build['metadata'].get('main_skill')}")
