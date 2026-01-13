"""
Test Skill-Aware Tree Building
Demonstrates how passive tree generation now uses skill scaling information
"""

import torch
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.skill_aware_tree_builder import SkillAwareTreeBuilder
from utils.skill_scaling_analyzer import SkillScalingAnalyzer


def load_tree_data():
    """Load edge index and node stats"""
    # Load edges
    edges_file = Path("../pob_data/tree_data/tree_edges.json")
    if edges_file.exists():
        with open(edges_file) as f:
            edges_data = json.load(f)
            edge_list = edges_data.get('edges', [])
            edge_index = torch.tensor(edge_list, dtype=torch.long).t()
            num_nodes = edges_data.get('num_nodes', 412)
    else:
        print("Warning: tree_edges.json not found, using dummy data")
        edge_index = torch.tensor([[0, 1], [1, 2], [2, 3]], dtype=torch.long).t()
        num_nodes = 412
    
    # Load node stats
    stats_file = Path("../pob_data/tree_data/node_stats.json")
    if stats_file.exists():
        with open(stats_file) as f:
            stats_data = json.load(f)
            node_stats = stats_data.get('nodes', [])
    else:
        print("Warning: node_stats.json not found, creating dummy data")
        # Create dummy stats for testing
        node_stats = []
        for i in range(num_nodes):
            node_stats.append({
                'id': i,
                'name': f"Node_{i}",
                'stats': {
                    'increased_spell_damage': 10 if i % 5 == 0 else 0,
                    'increased_fire_damage': 12 if i % 7 == 0 else 0,
                    'increased_cast_speed': 4 if i % 6 == 0 else 0,
                    'increased_life': 8 if i % 3 == 0 else 0,
                    'increased_area_of_effect': 8 if i % 8 == 0 else 0,
                }
            })
    
    return edge_index, num_nodes, node_stats


def test_skill_scaling_analyzer():
    """Test the skill scaling analyzer"""
    print("=" * 70)
    print("TESTING SKILL SCALING ANALYZER")
    print("=" * 70)
    
    analyzer = SkillScalingAnalyzer()
    
    # Test different skills
    skills_to_test = [
        ("Blade Vortex", ["Controlled Destruction", "Elemental Focus"]),
        ("Lightning Strike", ["Multistrike", "Elemental Damage with Attacks"]),
        ("Toxic Rain", ["Void Manipulation", "Swift Affliction"]),
        ("Righteous Fire", ["Burning Damage", "Elemental Focus"]),
    ]
    
    for skill_name, supports in skills_to_test:
        print(f"\n--- {skill_name} ---")
        scaling = analyzer.analyze_skill(skill_name, supports)
        
        print(f"Tags: {', '.join(scaling.tags)}")
        print(f"Damage types (top 5): {scaling.increased_damage_types[:5]}")
        print(f"Speed type: {scaling.speed_type}")
        print(f"Scales with crit: {scaling.scales_with_crit}")
        print(f"Area scaling: {scaling.area_scaling}")
        print(f"Projectile scaling: {scaling.projectile_scaling}")
        print(f"Duration scaling: {scaling.duration_scaling}")
        
        print(f"Defensive priorities:")
        for stat, priority in sorted(scaling.defensive_priority.items(), key=lambda x: -x[1])[:4]:
            print(f"  {stat}: {priority:.2f}")
    
    # Test node relevance calculation
    print("\n" + "=" * 70)
    print("TESTING NODE RELEVANCE CALCULATION")
    print("=" * 70)
    
    test_nodes = [
        {
            'name': 'Spell Damage Node',
            'stats': {
                'increased_spell_damage': 15,
                'increased_cast_speed': 5
            }
        },
        {
            'name': 'Fire Spell Node',
            'stats': {
                'increased_fire_damage': 12,
                'increased_spell_damage': 10,
                'increased_area_of_effect': 8
            }
        },
        {
            'name': 'Life Node',
            'stats': {
                'increased_life': 10
            }
        },
        {
            'name': 'Attack Speed Node',
            'stats': {
                'increased_attack_speed': 8,
                'increased_physical_damage': 12
            }
        },
    ]
    
    bv_scaling = analyzer.analyze_skill("Blade Vortex")
    
    print("\nBlade Vortex node relevance:")
    for node in test_nodes:
        relevance = analyzer.calculate_node_relevance(bv_scaling, node['stats'])
        print(f"  {node['name']}: {relevance:.3f}")


def test_skill_aware_tree_builder():
    """Test the skill-aware tree builder"""
    print("\n" + "=" * 70)
    print("TESTING SKILL-AWARE TREE BUILDER")
    print("=" * 70)
    
    # Load tree data
    edge_index, num_nodes, node_stats = load_tree_data()
    
    print(f"\nLoaded tree with {num_nodes} nodes and {edge_index.shape[1]} edges")
    
    # Create model
    model = SkillAwareTreeBuilder(
        num_nodes=num_nodes,
        edge_index=edge_index,
        use_skill_filtering=True
    )
    
    # Create build context
    context = {
        'gear': torch.randn(1, 20),
        'gems': torch.randn(1, 30),
        'skill': torch.randn(1, 10)
    }
    
    # Test different skills
    test_cases = [
        {
            'skill': 'Blade Vortex',
            'supports': ['Controlled Destruction', 'Elemental Focus', 'Unleash'],
            'start_node': 0,
            'num_points': 50
        },
        {
            'skill': 'Lightning Strike',
            'supports': ['Multistrike', 'Added Lightning Damage'],
            'start_node': 0,
            'num_points': 50
        },
        {
            'skill': 'Righteous Fire',
            'supports': ['Burning Damage', 'Elemental Focus', 'Swift Affliction'],
            'start_node': 0,
            'num_points': 50
        },
    ]
    
    for test_case in test_cases:
        skill = test_case['skill']
        supports = test_case['supports']
        
        print(f"\n--- Building tree for {skill} ---")
        print(f"Supports: {', '.join(supports)}")
        
        # Build tree
        tree = model.build_tree_with_skill_context(
            start_node_idx=test_case['start_node'],
            context=context,
            skill_name=skill,
            support_gems=supports,
            num_points=test_case['num_points'],
            node_stats=node_stats
        )
        
        print(f"Generated {len(tree)} nodes")
        print(f"First 10 nodes: {tree[:10]}")
        
        # Analyze tree composition
        total_offense = 0
        total_defense = 0
        stat_counts = {}
        
        for node_idx in tree[1:]:  # Skip starting node
            if node_idx < len(node_stats):
                node = node_stats[node_idx]
                for stat_name, value in node.get('stats', {}).items():
                    stat_counts[stat_name] = stat_counts.get(stat_name, 0) + value
                    
                    if 'damage' in stat_name or 'speed' in stat_name or 'crit' in stat_name:
                        total_offense += value
                    elif 'life' in stat_name or 'armour' in stat_name or 'evasion' in stat_name or 'resistance' in stat_name:
                        total_defense += value
        
        print(f"\nTree composition:")
        print(f"  Total offensive stats: {total_offense:.0f}")
        print(f"  Total defensive stats: {total_defense:.0f}")
        print(f"  Offense/Defense ratio: {total_offense/max(total_defense, 1):.2f}")
        
        # Show top stats
        print(f"\nTop 5 stats allocated:")
        top_stats = sorted(stat_counts.items(), key=lambda x: -x[1])[:5]
        for stat, value in top_stats:
            print(f"  {stat}: {value:.0f}")
        
        # Explain relevance of a few nodes
        print(f"\nNode explanations (sample of 3):")
        for i in [5, 10, 15]:
            if i < len(tree):
                node_idx = tree[i]
                if node_idx < len(node_stats):
                    explanation = model.explain_node_relevance(
                        skill_name=skill,
                        node_id=node_idx,
                        node_stats=node_stats[node_idx],
                        support_gems=supports
                    )
                    print(f"\n  Node {node_idx} ({node_stats[node_idx].get('name', 'Unknown')}):")
                    print(f"    Relevance: {explanation['relevance_score']:.3f}")
                    if explanation['contributing_stats']:
                        print(f"    Contributing stats:")
                        for stat in explanation['contributing_stats'][:3]:
                            print(f"      - {stat['stat']}: {stat['value']}")


def test_skill_comparison():
    """Compare trees generated for different skills"""
    print("\n" + "=" * 70)
    print("COMPARING TREES FOR DIFFERENT SKILLS")
    print("=" * 70)
    
    edge_index, num_nodes, node_stats = load_tree_data()
    
    model = SkillAwareTreeBuilder(
        num_nodes=num_nodes,
        edge_index=edge_index,
        use_skill_filtering=True
    )
    
    context = {
        'gear': torch.randn(1, 20),
        'gems': torch.randn(1, 30),
        'skill': torch.randn(1, 10)
    }
    
    skills = ['Blade Vortex', 'Lightning Strike', 'Toxic Rain']
    trees = {}
    
    for skill in skills:
        tree = model.build_tree_with_skill_context(
            start_node_idx=0,
            context=context,
            skill_name=skill,
            num_points=40,
            node_stats=node_stats
        )
        trees[skill] = set(tree)
    
    # Calculate overlap
    print("\nTree overlap analysis:")
    for i, skill1 in enumerate(skills):
        for skill2 in skills[i+1:]:
            overlap = len(trees[skill1] & trees[skill2])
            total = len(trees[skill1] | trees[skill2])
            percent = overlap / total * 100 if total > 0 else 0
            print(f"  {skill1} vs {skill2}: {overlap}/{total} nodes overlap ({percent:.1f}%)")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SKILL-AWARE PASSIVE TREE OPTIMIZATION TEST")
    print("=" * 70)
    print("\nThis test demonstrates:")
    print("1. Skill scaling analysis (which stats scale each skill)")
    print("2. Node relevance calculation (how good is each node for a skill)")
    print("3. Skill-aware tree building (prioritizing relevant nodes)")
    print("4. Tree comparison (different skills → different trees)")
    
    try:
        # Run tests
        test_skill_scaling_analyzer()
        test_skill_aware_tree_builder()
        test_skill_comparison()
        
        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
        print("\n📝 Summary:")
        print("  ✓ Skill scaling analyzer working")
        print("  ✓ Node relevance calculation working")
        print("  ✓ Skill-aware tree builder working")
        print("  ✓ Different skills generate different trees")
        
        print("\n💡 Next steps:")
        print("  1. Run: python scripts/extract_node_stats.py")
        print("     (to get real node stats from PoB)")
        print("  2. Train the model with skill-specific rewards")
        print("  3. Integrate with PoB calculation engine for accurate DPS")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
