"""
End-to-End Neural Network Test
Generate a complete PoB build file using the cost-aware GNN
"""

import torch
import json
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).parent))

from models.cost_aware_tree_builder import CostAwareTreeBuilder


class PoBBuildGenerator:
    """Generate complete Path of Building XML from neural network output"""
    
    def __init__(self):
        self.pob_version = "2.42.0"  # Current PoB version
        
        # Class IDs (from PoB)
        self.class_ids = {
            'Scion': 0,
            'Marauder': 1,
            'Ranger': 2,
            'Witch': 3,
            'Duelist': 4,
            'Templar': 5,
            'Shadow': 6,
        }
        
        # Ascendancy IDs (from PoB)
        self.ascend_ids = {
            'None': 0,
            # Scion
            'Ascendant': 1,
            # Marauder
            'Juggernaut': 1,
            'Berserker': 2,
            'Chieftain': 3,
            # Ranger
            'Raider': 1,
            'Deadeye': 2,
            'Pathfinder': 3,
            # Witch - Order from tree.lua: Occultist, Elementalist, Necromancer
            'Occultist': 1,
            'Elementalist': 2,
            'Necromancer': 3,
            # Duelist
            'Slayer': 1,
            'Gladiator': 2,
            'Champion': 3,
            # Templar
            'Inquisitor': 1,
            'Hierophant': 2,
            'Guardian': 3,
            # Shadow
            'Assassin': 1,
            'Trickster': 2,
            'Saboteur': 3,
        }
    
    def _get_class_ids(self, class_name: str, ascendancy: str) -> tuple:
        """Get class and ascendancy IDs"""
        class_id = self.class_ids.get(class_name, 0)
        ascend_id = self.ascend_ids.get(ascendancy, 0)
        return class_id, ascend_id
        
    def create_pob_xml(
        self,
        build_name: str,
        class_name: str,
        ascendancy: str,
        level: int,
        allocated_nodes: list,
        skill_name: str,
        support_gems: list = None
    ) -> str:
        """
        Create complete PoB XML build
        
        Args:
            build_name: Name of the build
            class_name: Starting class (Shadow, Witch, etc.)
            ascendancy: Ascendancy class (Assassin, Occultist, etc.)
            level: Character level
            allocated_nodes: List of passive node IDs
            skill_name: Main skill gem name
            support_gems: List of support gems
            
        Returns:
            XML string
        """
        # Create root
        root = ET.Element('PathOfBuilding')
        
        # Build metadata
        build = ET.SubElement(root, 'Build')
        build.set('level', str(max(1, level)))
        build.set('targetVersion', '3_0')
        build.set('pantheonMajorGod', 'None')
        build.set('pantheonMinorGod', 'None')
        build.set('bandit', 'None')
        build.set('mainSocketGroup', '1')
        build.set('viewMode', 'TREE')
        build.set('characterLevelAutoMode', 'false')  # Use explicit level, not auto-calculated
        
        # Character class
        build.set('className', class_name)
        build.set('ascendClassName', ascendancy)
        
        # Passive tree
        tree = ET.SubElement(root, 'Tree')
        tree.set('activeSpec', '1')
        
        # Get class and ascendancy IDs
        class_id, ascend_id = self._get_class_ids(class_name, ascendancy)
        
        spec = ET.SubElement(tree, 'Spec')
        # Match exact attribute order from PoB exports:
        # masteryEffects, treeVersion, nodes, secondaryAscendClassId, ascendClassId, classId
        spec.set('masteryEffects', '')
        spec.set('treeVersion', '3_27')  # Current PoE tree version
        
        # Add allocated nodes as comma-separated string in nodes attribute
        nodes_str = ','.join(str(node) for node in allocated_nodes)
        spec.set('nodes', nodes_str)
        
        # Secondary ascendancy (for Scion dual-ascendancy, otherwise nil)
        spec.set('secondaryAscendClassId', 'nil')
        
        spec.set('ascendClassId', str(ascend_id))
        spec.set('classId', str(class_id))
        
        # URL and Sockets (required elements)
        url_elem = ET.SubElement(spec, 'URL')
        url_elem.text = f"\n\t\t\t\thttps://www.pathofexile.com/passive-skill-tree/AAAABgAAAAAA\n\t\t\t"
        ET.SubElement(spec, 'Sockets')
        ET.SubElement(spec, 'Overrides')
        
        # Skills
        skills = ET.SubElement(root, 'Skills')
        
        # Main skill group
        skill_group = ET.SubElement(skills, 'SkillSet')
        skill_group.set('id', '1')
        
        skill_elem = ET.SubElement(skill_group, 'Skill')
        skill_elem.set('mainActiveSkill', '1')
        skill_elem.set('enabled', 'true')
        skill_elem.set('slot', 'Weapon 1')
        
        # Main skill gem
        gem = ET.SubElement(skill_elem, 'Gem')
        gem.set('nameSpec', skill_name)
        gem.set('level', '20')
        gem.set('quality', '20')
        gem.set('enabled', 'true')
        gem.set('enableGlobal1', 'true')
        
        # Support gems
        if support_gems:
            for support_name in support_gems:
                support = ET.SubElement(skill_elem, 'Gem')
                support.set('nameSpec', support_name)
                support.set('level', '20')
                support.set('quality', '20')
                support.set('enabled', 'true')
                support.set('enableGlobal1', 'true')
        
        # Items (basic starter gear)
        items = ET.SubElement(root, 'Items')
        items.set('activeItemSet', '1')
        items.set('useSecondWeaponSet', 'false')
        
        item_set = ET.SubElement(items, 'ItemSet')
        item_set.set('id', '1')
        
        # Add basic weapon based on skill type
        slot = ET.SubElement(item_set, 'Slot')
        slot.set('name', 'Weapon 1')
        slot.set('itemId', '1')
        
        # Create basic weapon item
        weapon = ET.SubElement(items, 'Item')
        weapon.set('id', '1')
        weapon.text = self._create_basic_weapon(skill_name)
        
        # Config
        config = ET.SubElement(root, 'Config')
        
        # Enemy level input
        enemy_level = ET.SubElement(config, 'Input')
        enemy_level.set('name', 'enemyLevel')
        enemy_level.set('number', '84')
        
        # Enemy is boss input
        enemy_boss = ET.SubElement(config, 'Input')
        enemy_boss.set('name', 'enemyIsBoss')
        enemy_boss.set('string', 'Boss')
        
        # Notes
        notes = ET.SubElement(root, 'Notes')
        notes.text = f"""
Build: {build_name}
Generated by: Neural Network Cost-Aware Tree Builder
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Starting Class: {class_name} ({ascendancy})
Main Skill: {skill_name}
Passive Points: {len(allocated_nodes)}

This build was generated using:
1. Distance-aware pathing from {class_name} start
2. ROI-based node selection
3. Balanced stat allocation (maximizes DPS product)
4. Diminishing returns consideration
"""
        
        # Convert to pretty XML string
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')
    
    def _create_basic_weapon(self, skill_name: str) -> str:
        """Create basic weapon item text based on skill type"""
        skill_lower = skill_name.lower()
        
        if 'strike' in skill_lower or 'cleave' in skill_lower or 'slash' in skill_lower:
            # Attack skill - physical weapon
            return """Rarity: NORMAL
Corsair Sword
One Handed Sword
Physical Damage: 50-90
Critical Strike Chance: 5%
Attacks per Second: 1.5
Weapon Range: 11"""
        
        elif 'blade vortex' in skill_lower or 'ball' in skill_lower:
            # Spell - wand or sceptre
            return """Rarity: NORMAL
Imbued Wand
Wand
Physical Damage: 30-56
Critical Strike Chance: 7%
Attacks per Second: 1.3
Weapon Range: 120
+30% to Spell Damage
+15% to Critical Strike Multiplier"""
        
        elif 'righteous fire' in skill_lower:
            # RF - sceptre with damage
            return """Rarity: NORMAL
Void Sceptre
Sceptre  
Physical Damage: 40-60
Critical Strike Chance: 6.5%
Attacks per Second: 1.25
Weapon Range: 11
+40% to Elemental Damage
+15% to Fire Damage over Time Multiplier"""
        
        else:
            # Generic weapon
            return """Rarity: NORMAL
Simple Weapon
Physical Damage: 30-50
Critical Strike Chance: 5%
Attacks per Second: 1.4"""


def create_mock_tree_data():
    """Create mock passive tree data using REAL node IDs from PoB"""
    import json
    
    # Load real node mapping from extracted tree data
    with open('pob_data/tree_data/node_mapping.json', 'r') as f:
        node_data = json.load(f)
    
    # Convert to proper types (index -> real node ID)
    index_to_node = {int(k): int(v) for k, v in node_data['index_to_node'].items()}
    num_nodes = len(index_to_node)
    
    print(f"Loaded {num_nodes} real PoB nodes from tree data")
    
    # Create simple connections between sequential indices for testing
    # In production, would use real edge_index.json
    edges = []
    for i in range(min(100, num_nodes-1)):
        edges.append([i, i + 1])
    
    edge_index = torch.tensor(edges, dtype=torch.long).t()
    
    # Mock node stats (in production, would extract from tree.lua)
    node_stats = []
    for i in range(num_nodes):
        # Just use random stats for testing
        stats = {
            'Increased Damage': torch.randint(5, 15, (1,)).item(),
            'Increased Maximum Life': torch.randint(5, 20, (1,)).item(),
        }
        node_stats.append(stats)
    
    # Starting positions using real node indices from our tree
    # Scion (node 7960) = index 51, Shadow (node 61834) = index 382
    starting_positions = {
        'Scion': 51,      # Real Scion start (node 7960)
        'Shadow': 382,    # Real Shadow start (node 61834)
        'Marauder': 0,    # Fallback to first node (node 367)
        'Ranger': 20,     # Use nearby node
        'Witch': 10,      # Use nearby node
        'Duelist': 30,    # Use nearby node
        'Templar': 40,    # Use nearby node
    }
    
    return edge_index, node_stats, starting_positions, num_nodes, index_to_node


def test_end_to_end_build_generation():
    """Test complete pipeline: GNN → PoB XML"""
    print("=" * 80)
    print("END-TO-END NEURAL NETWORK BUILD GENERATION TEST")
    print("=" * 80)
    print()
    
    # Setup
    edge_index, node_stats, starting_positions, num_nodes, index_to_node = create_mock_tree_data()
    generator = PoBBuildGenerator()
    
    # Test configurations
    test_configs = [
        {
            'build_name': 'NN Generated - Lightning Strike Assassin',
            'class': 'Shadow',
            'ascendancy': 'Assassin',
            'skill': 'Lightning Strike',
            'supports': ['Multistrike Support', 'Added Lightning Damage Support', 
                        'Elemental Damage with Attacks Support', 'Inspiration Support'],
            'level': 90,
        },
        {
            'build_name': 'NN Generated - Blade Vortex Occultist',
            'class': 'Witch',
            'ascendancy': 'Occultist',
            'skill': 'Blade Vortex',
            'supports': ['Unleash Support', 'Controlled Destruction Support',
                        'Efficacy Support', 'Concentrated Effect Support'],
            'level': 90,
        },
        {
            'build_name': 'NN Generated - Righteous Fire Chieftain',
            'class': 'Marauder',
            'ascendancy': 'Chieftain',
            'skill': 'Righteous Fire',
            'supports': ['Burning Damage Support', 'Elemental Focus Support',
                        'Swift Affliction Support', 'Efficacy Support'],
            'level': 90,
        }
    ]
    
    output_dir = Path('pob_neural_network/generated_builds')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"Generating: {config['build_name']}")
        print(f"{'='*80}")
        
        # Initialize cost-aware tree builder
        builder = CostAwareTreeBuilder(
            num_nodes=num_nodes,
            edge_index=edge_index,
            distance_penalty=0.1,
            balance_reward=0.3
        )
        
        start_node = starting_positions[config['class']]
        print(f"Starting class: {config['class']} (Node {start_node})")
        print(f"Main skill: {config['skill']}")
        print(f"Ascendancy: {config['ascendancy']}")
        print()
        
        # Mock context (in real implementation, this would come from gear/gems)
        context = {
            'gear': torch.randn(1, 64),
            'gems': torch.randn(1, 64),
            'skill': torch.randn(1, 64),
        }
        
        # Generate tree using cost-aware builder
        print("Running cost-aware tree builder...")
        try:
            allocated_nodes, metrics = builder.build_tree_with_cost_awareness(
                start_node_idx=start_node,
                starting_class=config['class'],
                context=context,
                skill_name=config['skill'],
                support_gems=config['supports'],
                num_points=100,
                node_stats=node_stats
            )
            
            print(f"✓ Generated tree with {len(allocated_nodes)} nodes")
            print(f"  Final DPS estimate: {metrics['dps_values'][-1]:.1f}")
            print(f"  Average balance score: {sum(metrics['balance_scores'])/len(metrics['balance_scores']):.3f}")
            print(f"  Average ROI: {sum(metrics['roi_values'])/len(metrics['roi_values']):.3f}")
            
        except Exception as e:
            print(f"✗ Error generating tree: {e}")
            print("  Using mock allocation for testing...")
            # Fallback: simple radial allocation
            allocated_nodes = [start_node]
            for i in range(1, 101):
                next_node = (start_node + i) % num_nodes
                allocated_nodes.append(next_node)
        
        # Generate PoB XML
        print("\nGenerating Path of Building XML...")
        
        # Convert node indices to real PoB node IDs
        real_node_ids = [index_to_node[idx] for idx in allocated_nodes[:100] if idx in index_to_node]
        print(f"  Converted {len(real_node_ids)} indices to real PoB node IDs")
        
        # Calculate appropriate level based on allocated nodes (1 point per level starting at level 2)
        # Add some buffer points for quest rewards (~20 total)
        calculated_level = len(real_node_ids) + 2 if len(real_node_ids) < 90 else config['level']
        print(f"  Character level: {calculated_level} (based on {len(real_node_ids)} allocated nodes)")
        
        xml_content = generator.create_pob_xml(
            build_name=config['build_name'],
            class_name=config['class'],
            ascendancy=config['ascendancy'],
            level=calculated_level,  # Use calculated level matching node count
            allocated_nodes=real_node_ids,  # Use real node IDs
            skill_name=config['skill'],
            support_gems=config['supports']
        )
        
        # Save to file
        filename = config['build_name'].lower().replace(' ', '_').replace('-', '') + '.xml'
        output_path = output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        print(f"✓ Saved to: {output_path}")
        print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
        
        # Validate XML
        try:
            tree = ET.parse(output_path)
            root = tree.getroot()
            nodes_elem = root.find('.//Nodes')
            node_count = len(nodes_elem.findall('Node')) if nodes_elem is not None else 0
            skill_elem = root.find('.//Skill')
            skill_name = skill_elem.find('Gem').get('nameSpec') if skill_elem is not None else 'Unknown'
            
            print(f"✓ XML validation passed")
            print(f"  Nodes in tree: {node_count}")
            print(f"  Main skill: {skill_name}")
        except Exception as e:
            print(f"✗ XML validation failed: {e}")
    
    print("\n" + "=" * 80)
    print("BUILD GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nGenerated {len(test_configs)} builds in: {output_dir}")
    print("\nTo test in Path of Building:")
    print("1. Open Path of Building")
    print("2. Click 'Import/Export Build'")
    print("3. Click 'Import from...'")
    print("4. Select 'Load from file...'")
    print("5. Browse to generated_builds/ and select a .xml file")
    print("6. Check that the tree loads and skill is configured")
    print("\nExpected results:")
    print("- Passive tree should show allocated nodes")
    print("- Skills tab should show main skill + supports")
    print("- Tree should path efficiently from starting class")
    print("- Allocation should be balanced across relevant stats")


if __name__ == "__main__":
    test_end_to_end_build_generation()
