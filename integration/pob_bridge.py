"""
Integration Layer with Path of Building
Exports optimized builds in PoB-compatible format
"""

import json
import base64
import zlib
from typing import Dict, List, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom


class PoBExporter:
    """Export optimized builds to Path of Building XML format"""
    
    def __init__(self):
        self.tree_data = self._load_tree_data()
    
    def _load_tree_data(self) -> Dict:
        """Load passive tree node mapping (index -> node ID)"""
        # Try multiple locations for tree data
        possible_paths = [
            Path("./pob_data/tree_data/node_mapping.json"),
            Path("../pob_data/tree_data/node_mapping.json"),
            Path("../../pob_data/tree_data/node_mapping.json")
        ]
        
        for tree_file in possible_paths:
            if tree_file.exists():
                with open(tree_file) as f:
                    data = json.load(f)
                    # Return the index_to_node mapping
                    if 'index_to_node' in data:
                        # Convert string keys to int
                        return {int(k): v for k, v in data['index_to_node'].items()}
                    return data
        
        print("⚠️  Warning: Tree node mapping not found. Run: python scripts/create_node_mapping.py")
        print("   Using array indices - this will NOT work correctly in PoB!")
        return {}
    
    def export_build(
        self,
        optimized_build: Dict,
        output_path: str,
        build_name: str = "NN Optimized Build",
        class_name: str = "Scion"
    ) -> str:
        """
        Export optimized build to PoB XML format
        
        Args:
            optimized_build: Dictionary with tree, gear, gems arrays
            output_path: Where to save the .xml file
            build_name: Name of the build
            class_name: Character class
            
        Returns:
            Path to created XML file
        """
        # Create XML structure
        root = ET.Element("PathOfBuilding")
        
        # Build section
        build_elem = ET.SubElement(root, "Build")
        build_elem.set("level", "100")
        build_elem.set("targetVersion", "3_0")  # PoB application version
        build_elem.set("pantheonMajorGod", "None")
        build_elem.set("bandit", "None")
        build_elem.set("className", class_name)
        build_elem.set("ascendClassName", "None")
        build_elem.set("characterLevelAutoMode", "true")
        build_elem.set("mainSocketGroup", "1")
        build_elem.set("viewMode", "TREE")
        build_elem.set("pantheonMinorGod", "None")
        
        # Tree section
        tree_elem = ET.SubElement(root, "Tree")
        tree_elem.set("activeSpec", "1")
        
        spec_elem = ET.SubElement(tree_elem, "Spec")
        spec_elem.set("treeVersion", "3_27")
        spec_elem.set("classId", self._get_class_id(class_name))
        spec_elem.set("ascendClassId", "0")
        spec_elem.set("masteryEffects", "")
        spec_elem.set("secondaryAscendClassId", "nil")
        
        # Convert tree array to node IDs
        tree_array = optimized_build.get('tree', [])
        
        # Check if we have pre-computed PoB node IDs (for imported builds)
        if 'pob_nodes' in optimized_build and isinstance(optimized_build['pob_nodes'], str):
            nodes_text = optimized_build['pob_nodes']
        else:
            # Map array indices to actual PoB node IDs
            allocated_indices = [i for i, val in enumerate(tree_array) if val == 1]
            
            if self.tree_data:
                # Map indices to real node IDs
                allocated_node_ids = []
                for idx in allocated_indices:
                    if idx in self.tree_data:
                        allocated_node_ids.append(self.tree_data[idx])
                
                # Find most similar build from training data and use its tree
                if allocated_node_ids:
                    from utils.tree_connector import find_most_similar_build
                    similar_tree = find_most_similar_build(
                        allocated_node_ids,
                        class_name,
                        target_size=len(allocated_node_ids)
                    )
                    
                    if similar_tree:
                        nodes_text = ",".join(str(n) for n in similar_tree)
                        print(f"[Tree] Using similar build tree with {len(similar_tree)} connected nodes (target: {len(allocated_node_ids)})")
                    else:
                        # Fallback: use reference tree
                        ref_path = Path("./pob_data/tree_data/reference_tree.json")
                        if ref_path.exists():
                            import json
                            with open(ref_path) as f:
                                ref_data = json.load(f)
                                nodes_text = ",".join(str(n) for n in ref_data['nodes'][:len(allocated_node_ids)])
                                print(f"[Tree] Using reference tree (fallback)")
                        else:
                            nodes_text = ",".join(str(n) for n in allocated_node_ids)
                else:
                    nodes_text = ""
            else:
                # No mapping available - use indices (won't work in PoB)
                print("⚠️  Warning: Exporting with array indices instead of PoB node IDs")
                nodes_text = ",".join(str(idx) for idx in allocated_indices)
        
        spec_elem.set("nodes", nodes_text)
        
        # Add URL (required by PoB)
        url_elem = ET.SubElement(spec_elem, "URL")
        url_elem.text = "\n\t\t\t\thttps://www.pathofexile.com/passive-skill-tree/AAAABgAAAAAA\n\t\t\t"
        
        # Add empty Sockets and Overrides (required by PoB)
        sockets_elem = ET.SubElement(spec_elem, "Sockets")
        overrides_elem = ET.SubElement(spec_elem, "Overrides")
        
        # Items section (simplified - create placeholder items)
        items_elem = ET.SubElement(root, "Items")
        items_elem.set("activeItemSet", "1")
        items_elem.set("useSecondWeaponSet", "false")
        self._add_placeholder_items(items_elem, optimized_build)
        
        # Skills section
        skills_elem = ET.SubElement(root, "Skills")
        skills_elem.set("activeSkillSet", "1")
        skills_elem.set("defaultGemLevel", "20")
        skills_elem.set("defaultGemQuality", "20")
        self._add_placeholder_skills(skills_elem, optimized_build)
        
        # Config section
        config_elem = ET.SubElement(root, "Config")
        config_elem.set("activeConfigSet", "1")
        configset_elem = ET.SubElement(config_elem, "ConfigSet")
        configset_elem.set("title", "Default")
        configset_elem.set("id", "1")
        
        # Notes section
        notes_elem = ET.SubElement(root, "Notes")
        allocated_count = len(optimized_build.get('pob_nodes', '').split(',')) if 'pob_nodes' in optimized_build else len([i for i, v in enumerate(tree_array) if v == 1])
        notes_elem.text = f"\nBuild optimized by Neural Network\nFitness Score: {optimized_build.get('fitness', 0):.2f}\nAllocated Nodes: {allocated_count}\n"
        
        # TreeView section (optional but helps with display)
        treeview_elem = ET.SubElement(root, "TreeView")
        treeview_elem.set("searchStr", "")
        treeview_elem.set("zoomY", "0")
        treeview_elem.set("zoomLevel", "3")
        treeview_elem.set("showStatDifferences", "true")
        treeview_elem.set("zoomX", "0")
        notes_elem.text = f"Build optimized by Neural Network\nFitness Score: {optimized_build.get('fitness', 0):.2f}"
        
        # Pretty print and save
        xml_string = self._prettify_xml(root)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported build to {output_file}")
        return str(output_file)
    
    def _get_class_id(self, class_name: str) -> str:
        """Map class name to PoB class ID"""
        class_map = {
            "Scion": "0",
            "Marauder": "1",
            "Ranger": "2",
            "Witch": "3",
            "Duelist": "4",
            "Templar": "5",
            "Shadow": "6"
        }
        return class_map.get(class_name, "0")
    
    def _add_placeholder_items(self, items_elem: ET.Element, build: Dict):
        """Add placeholder items based on gear stats"""
        gear_array = build.get('gear', [])
        
        # Create realistic items with proper PoB formatting
        items_data = {
            1: {  # Weapon
                "rarity": "RARE",
                "name": "Neural Blade",
                "base": "Vaal Rapier",
                "quality": "20",
                "physical_dps": "Physical Damage: 45-85",
                "sockets": "G-G-G",
                "level_req": "68",
                "implicit": "+25% to Global Critical Strike Multiplier",
                "mods": [
                    "+50 to maximum Life",
                    "Adds 15 to 28 Physical Damage",
                    "25% increased Critical Strike Chance",
                    "30% increased Critical Strike Multiplier"
                ]
            },
            2: {  # Helmet
                "rarity": "RARE",
                "name": "Neural Circlet",
                "base": "Hubris Circlet",
                "quality": "20",
                "es": "Energy Shield: 180",
                "sockets": "B-B-B-B",
                "level_req": "69",
                "implicit": "",
                "mods": [
                    "+70 to maximum Life",
                    "+80 to maximum Energy Shield",
                    "+45% to Lightning Resistance"
                ]
            },
            3: {  # Body Armour
                "rarity": "RARE",
                "name": "Neural Regalia",
                "base": "Vaal Regalia",
                "quality": "20",
                "es": "Energy Shield: 380",
                "sockets": "B-B-B-B-B-B",
                "level_req": "68",
                "implicit": "",
                "mods": [
                    "+90 to maximum Life",
                    "+180 to maximum Energy Shield",
                    "+42% to Cold Resistance"
                ]
            },
            4: {  # Gloves
                "rarity": "RARE",
                "name": "Neural Gloves",
                "base": "Sorcerer Gloves",
                "quality": "20",
                "es": "Energy Shield: 80",
                "sockets": "B-B-B-B",
                "level_req": "69",
                "implicit": "",
                "mods": [
                    "+65 to maximum Life",
                    "+50 to maximum Energy Shield",
                    "+38% to Fire Resistance"
                ]
            },
            5: {  # Boots
                "rarity": "RARE",
                "name": "Neural Boots",
                "base": "Sorcerer Boots",
                "quality": "20",
                "es": "Energy Shield: 90",
                "sockets": "B-B-B-B",
                "level_req": "69",
                "implicit": "",
                "mods": [
                    "+70 to maximum Life",
                    "+55 to maximum Energy Shield",
                    "25% increased Movement Speed",
                    "+40% to Lightning Resistance"
                ]
            },
            6: {  # Amulet
                "rarity": "RARE",
                "name": "Neural Amulet",
                "base": "Agate Amulet",
                "quality": "",
                "sockets": "",
                "level_req": "60",
                "implicit": "+20 to Strength and Intelligence",
                "mods": [
                    "+60 to maximum Life",
                    "+35% to Lightning Resistance",
                    "25% increased Global Critical Strike Chance"
                ]
            },
            7: {  # Ring 1
                "rarity": "RARE",
                "name": "Neural Loop",
                "base": "Gold Ring",
                "quality": "",
                "sockets": "",
                "level_req": "60",
                "implicit": "+20 to maximum Life",
                "mods": [
                    "+45 to maximum Life",
                    "+40% to Fire Resistance",
                    "+38% to Cold Resistance"
                ]
            },
            8: {  # Ring 2
                "rarity": "RARE",
                "name": "Neural Band",
                "base": "Gold Ring",
                "quality": "",
                "sockets": "",
                "level_req": "60",
                "implicit": "+20 to maximum Life",
                "mods": [
                    "+50 to maximum Life",
                    "+42% to Lightning Resistance",
                    "+35% to Cold Resistance"
                ]
            },
            9: {  # Belt
                "rarity": "RARE",
                "name": "Neural Belt",
                "base": "Leather Belt",
                "quality": "",
                "sockets": "",
                "level_req": "60",
                "implicit": "+35 to maximum Life",
                "mods": [
                    "+70 to maximum Life",
                    "+40% to Fire Resistance",
                    "20% increased Flask Life Recovery rate"
                ]
            },
            10: {  # Shield
                "rarity": "RARE",
                "name": "Neural Shield",
                "base": "Titanium Spirit Shield",
                "quality": "20",
                "es": "Energy Shield: 150",
                "sockets": "B-B-B",
                "level_req": "68",
                "implicit": "+20 to maximum Mana",
                "mods": [
                    "+60 to maximum Life",
                    "+80 to maximum Energy Shield",
                    "+35% to Fire Resistance",
                    "18% increased Spell Damage"
                ]
            }
        }
        
        # Add items with proper formatting
        for item_id, item_data in items_data.items():
            item_elem = ET.SubElement(items_elem, "Item")
            item_elem.set("id", str(item_id))
            
            # Build item text in PoB format
            lines = [f"Rarity: {item_data['rarity']}"]
            lines.append(item_data['name'])
            lines.append(item_data['base'])
            
            if item_data.get('quality'):
                lines.append(f"Quality: {item_data['quality']}")
            if item_data.get('physical_dps'):
                lines.append(item_data['physical_dps'])
            if item_data.get('es'):
                lines.append(item_data['es'])
            if item_data.get('sockets'):
                lines.append(f"Sockets: {item_data['sockets']}")
            
            lines.append(f"LevelReq: {item_data['level_req']}")
            
            # Add implicit
            if item_data.get('implicit'):
                lines.append("Implicits: 1")
                lines.append(item_data['implicit'])
            else:
                lines.append("Implicits: 0")
            
            # Add mods
            lines.extend(item_data['mods'])
            
            item_elem.text = "\n".join(lines) + "\n"
        
        # Create ItemSet that references items
        itemset_elem = ET.SubElement(items_elem, "ItemSet")
        itemset_elem.set("id", "1")
        itemset_elem.set("useSecondWeaponSet", "false")
        
        # Map items to slots
        slot_mappings = {
            "Weapon 1": "1",
            "Weapon 2": "10",
            "Helmet": "2",
            "Body Armour": "3",
            "Gloves": "4",
            "Boots": "5",
            "Amulet": "6",
            "Ring 1": "7",
            "Ring 2": "8",
            "Belt": "9"
        }
        
        for slot_name, item_id in slot_mappings.items():
            slot_elem = ET.SubElement(itemset_elem, "Slot")
            slot_elem.set("name", slot_name)
            slot_elem.set("itemId", item_id)
    
    def _add_placeholder_skills(self, skills_elem: ET.Element, build: Dict):
        """Add placeholder skill setup"""
        gem_array = build.get('gems', [])
        
        # Get skill name if available
        skill_name = build.get('skill_name', 'Lightning Strike')
        
        # Create SkillSet
        skillset_elem = ET.SubElement(skills_elem, "SkillSet")
        skillset_elem.set("id", "1")
        
        # Create a 6-link
        skill_elem = ET.SubElement(skillset_elem, "Skill")
        skill_elem.set("slot", "Body Armour")
        skill_elem.set("enabled", "true")
        skill_elem.set("mainActiveSkill", "1")
        skill_elem.set("label", "")
        
        # Add gems (placeholder)
        gems = [
            {"name": skill_name, "skillId": skill_name.replace(" ", ""), "gemId": f"Metadata/Items/Gems/SkillGem{skill_name.replace(' ', '')}"},
            {"name": "Multistrike Support", "skillId": "SupportMultistrike", "gemId": "Metadata/Items/Gems/SupportGemMultistrike"},
            {"name": "Elemental Damage with Attacks Support", "skillId": "SupportWeaponElementalDamage", "gemId": "Metadata/Items/Gems/SupportGemWeaponElementalDamage"},
            {"name": "Added Lightning Damage Support", "skillId": "SupportAddedLightningDamage", "gemId": "Metadata/Items/Gems/SupportGemAddedLightningDamage"},
            {"name": "Inspiration Support", "skillId": "SupportInspiration", "gemId": "Metadata/Items/Gems/SupportGemInspiration"},
            {"name": "Lightning Penetration Support", "skillId": "SupportLightningPenetration", "gemId": "Metadata/Items/Gems/SupportGemLightningPenetration"}
        ]
        
        for i, gem in enumerate(gems):
            gem_elem = ET.SubElement(skill_elem, "Gem")
            gem_elem.set("level", "20")
            gem_elem.set("quality", "20")
            gem_elem.set("enabled", "true")
            gem_elem.set("enableGlobal1", "true")
            gem_elem.set("enableGlobal2", "true")
            gem_elem.set("skillId", gem["skillId"])
            gem_elem.set("gemId", gem["gemId"])
            gem_elem.set("nameSpec", gem["name"])
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def create_build_code(self, xml_path: str) -> str:
        """
        Create PoB build code from XML file
        (Base64 encoded, compressed)
        """
        with open(xml_path, 'rb') as f:
            xml_data = f.read()
        
        # Compress
        compressed = zlib.compress(xml_data)
        
        # Base64 encode
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        return encoded


class PoBImporter:
    """Import builds from Path of Building"""
    
    def decode_build_code(self, build_code: str) -> str:
        """
        Decode PoB build code to XML
        
        Args:
            build_code: Base64 encoded compressed XML
            
        Returns:
            Decompressed XML string
        """
        # Remove any whitespace
        build_code = build_code.strip()
        
        try:
            # Base64 decode
            compressed = base64.b64decode(build_code)
            
            # Decompress
            xml_data = zlib.decompress(compressed)
            
            return xml_data.decode('utf-8')
        except Exception as e:
            print(f"Error decoding build code: {e}")
            return ""
    
    def parse_build_xml(self, xml_string: str) -> Dict:
        """
        Parse PoB XML into structured format
        
        Returns:
            Dictionary with tree, items, skills
        """
        try:
            root = ET.fromstring(xml_string)
            
            build_data = {
                'class': None,
                'level': None,
                'tree': [],
                'items': [],
                'skills': []
            }
            
            # Parse build info
            build_elem = root.find('Build')
            if build_elem is not None:
                build_data['class'] = build_elem.get('className')
                build_data['level'] = int(build_elem.get('level', 100))
            
            # Parse tree
            tree_elem = root.find('Tree/Spec')
            if tree_elem is not None:
                nodes_str = tree_elem.get('nodes', '')
                if nodes_str:
                    build_data['tree'] = [int(n) for n in nodes_str.split(',')]
            
            # Parse items
            items_elem = root.find('Items')
            if items_elem is not None:
                for item in items_elem.findall('Item'):
                    build_data['items'].append(item.text)
            
            # Parse skills
            skills_elem = root.find('Skills')
            if skills_elem is not None:
                for skill in skills_elem.findall('Skill'):
                    gems = []
                    for gem in skill.findall('Gem'):
                        gems.append({
                            'name': gem.get('skillId'),
                            'level': gem.get('level'),
                            'quality': gem.get('quality')
                        })
                    build_data['skills'].append(gems)
            
            return build_data
            
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return {}
    
    def import_from_file(self, xml_path: str) -> Dict:
        """Import build from XML file"""
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_string = f.read()
        return self.parse_build_xml(xml_string)
    
    def import_from_code(self, build_code: str) -> Dict:
        """Import build from build code"""
        xml_string = self.decode_build_code(build_code)
        if xml_string:
            return self.parse_build_xml(xml_string)
        return {}


class LuaBridge:
    """
    Bridge between Python optimizer and Lua PoB
    Allows calling PoB calculations from Python
    """
    
    def __init__(self, pob_path: str = "../../PathOfBuilding"):
        self.pob_path = Path(pob_path)
    
    def validate_build(self, build_xml: str) -> Dict:
        """
        Validate build using actual PoB calculations
        
        This would require running PoB in headless mode
        For now, returns placeholder
        """
        # TODO: Implement actual PoB integration
        # Options:
        # 1. Use PathOfBuildingAPI library
        # 2. Call PoB Lua directly via lupa/lunatic
        # 3. Use HeadlessWrapper.lua
        
        return {
            'dps': 1000000,
            'life': 5000,
            'es': 0,
            'ehp': 5000,
            'valid': True
        }
    
    def export_to_pob(self, optimized_build: Dict, output_name: str):
        """
        Export optimized build directly to PoB Builds folder
        """
        builds_dir = self.pob_path / "src" / "Builds"
        
        exporter = PoBExporter()
        output_path = builds_dir / f"{output_name}.xml"
        
        exporter.export_build(
            optimized_build=optimized_build,
            output_path=str(output_path),
            build_name=output_name
        )
        
        print(f"Exported to PoB: {output_path}")


if __name__ == "__main__":
    # Example: Export optimized build
    print("=== Testing PoB Integration ===")
    
    # Load an optimized build
    import numpy as np
    optimized_build = {
        'tree': [1 if i < 100 else 0 for i in range(1500)],  # First 100 nodes
        'gear': np.random.rand(500).tolist(),
        'gems': np.random.rand(100).tolist(),
        'fitness': 1250000.0
    }
    
    # Export to XML
    exporter = PoBExporter()
    xml_path = exporter.export_build(
        optimized_build=optimized_build,
        output_path="./test_builds/optimized_build.xml",
        build_name="NN Optimized Test"
    )
    
    # Create build code
    build_code = exporter.create_build_code(xml_path)
    print(f"\nBuild code (first 100 chars): {build_code[:100]}...")
    
    # Test import
    importer = PoBImporter()
    imported = importer.import_from_file(xml_path)
    print(f"\nImported build:")
    print(f"  Class: {imported['class']}")
    print(f"  Level: {imported['level']}")
    print(f"  Allocated nodes: {len(imported['tree'])}")
    
    # Test Lua bridge
    bridge = LuaBridge()
    validation = bridge.validate_build(xml_path)
    print(f"\nValidation: {validation}")
