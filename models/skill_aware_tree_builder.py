"""
Skill-Aware Tree Builder
Extends GraphTreeBuilder to prioritize nodes based on main skill scaling
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.graph_tree_builder import GraphTreeBuilder
from utils.skill_scaling_analyzer import SkillScalingAnalyzer, ScalingVector


class SkillAwareTreeBuilder(GraphTreeBuilder):
    """
    Enhanced tree builder that uses skill scaling information
    to prioritize relevant passive nodes
    """
    
    def __init__(
        self,
        num_nodes: int,
        edge_index: torch.Tensor,
        node_feature_dim: int = 64,
        hidden_dim: int = 128,
        context_dim: int = 256,
        use_skill_filtering: bool = True
    ):
        super().__init__(num_nodes, edge_index, node_feature_dim, hidden_dim, context_dim)
        
        self.use_skill_filtering = use_skill_filtering
        self.skill_analyzer = SkillScalingAnalyzer()
        
        # Learnable weights for combining neural network scores with skill relevance
        self.skill_weight = nn.Parameter(torch.tensor(0.5))  # 0.5 = balanced
        
    def build_tree_with_skill_context(
        self,
        start_node_idx: int,
        context: Dict,
        skill_name: str,
        support_gems: List[str] = None,
        num_points: int = 100,
        node_stats: Optional[List[Dict]] = None
    ) -> List[int]:
        """
        Build a passive tree prioritizing nodes relevant to the main skill
        
        Args:
            start_node_idx: Starting node (class start)
            context: Dictionary with 'gear', 'gems', 'skill' tensors
            skill_name: Name of the main skill gem
            support_gems: List of support gems (optional)
            num_points: Number of passive points to allocate
            node_stats: List of node stat dictionaries (required for skill filtering)
            
        Returns:
            List of allocated node indices
        """
        if not self.use_skill_filtering or node_stats is None:
            # Fall back to standard tree building
            return self.build_tree_greedy(start_node_idx, context, num_points)
        
        # Analyze skill to get scaling requirements
        scaling_vector = self.skill_analyzer.analyze_skill(skill_name, support_gems)
        
        # Calculate relevance scores for all nodes
        node_relevance = self._calculate_node_relevance_batch(scaling_vector, node_stats)
        node_relevance_tensor = torch.tensor(node_relevance, dtype=torch.float32)
        
        # Build tree with skill-aware scoring
        return self._build_tree_skill_aware(
            start_node_idx,
            context,
            node_relevance_tensor,
            num_points
        )
    
    def _calculate_node_relevance_batch(
        self,
        scaling_vector: ScalingVector,
        node_stats: List[Dict]
    ) -> np.ndarray:
        """
        Calculate relevance scores for all nodes in batch
        
        Args:
            scaling_vector: Skill scaling requirements
            node_stats: List of stat dicts for each node
            
        Returns:
            Array of relevance scores [num_nodes]
        """
        relevance_scores = np.zeros(len(node_stats))
        
        for i, node in enumerate(node_stats):
            stats = node.get('stats', {})
            relevance_scores[i] = self.skill_analyzer.calculate_node_relevance(
                scaling_vector,
                stats
            )
        
        return relevance_scores
    
    def _build_tree_skill_aware(
        self,
        start_node_idx: int,
        context: Dict,
        node_relevance: torch.Tensor,
        num_points: int
    ) -> List[int]:
        """
        Build tree combining neural network policy with skill relevance scores
        
        Args:
            start_node_idx: Starting node index
            context: Build context (gear, gems, skill)
            node_relevance: Pre-computed skill relevance scores [num_nodes]
            num_points: Number of points to allocate
            
        Returns:
            List of allocated node indices
        """
        allocated = torch.zeros(self.num_nodes, dtype=torch.bool)
        allocated[start_node_idx] = True
        tree_sequence = [start_node_idx]
        
        # Build the full tree
        with torch.no_grad():
            # Get node embeddings from GNN
            node_indices = torch.arange(self.num_nodes)
            node_embeddings = self.tree_encoder(node_indices, self.edge_index)
            
            # Encode context
            context_tensor = torch.cat([
                context['gear'],
                context['gems'],
                context['skill']
            ], dim=-1)
            context_encoded = self.path_generator.context_encoder(context_tensor)
            
            # Initialize tree state
            tree_state = torch.zeros(self.hidden_dim)
            
            for step in range(num_points - 1):
                # Get neighboring nodes (only consider adjacent unallocated nodes)
                allocated_nodes = torch.where(allocated)[0]
                neighbor_mask = torch.zeros(self.num_nodes, dtype=torch.bool)
                
                for alloc_node in allocated_nodes:
                    # Find neighbors from edge_index
                    edges = self.edge_index[:, self.edge_index[0] == alloc_node]
                    neighbors = edges[1]
                    neighbor_mask[neighbors] = True
                
                # Remove already allocated nodes
                neighbor_mask = neighbor_mask & ~allocated
                
                if not neighbor_mask.any():
                    break  # No valid neighbors (shouldn't happen)
                
                candidate_indices = torch.where(neighbor_mask)[0]
                
                # Get neural network scores
                candidate_embeddings = node_embeddings[candidate_indices]
                context_repeated = context_encoded.unsqueeze(0).repeat(len(candidate_indices), 1)
                tree_state_repeated = tree_state.unsqueeze(0).repeat(len(candidate_indices), 1)
                
                combined_input = torch.cat([
                    candidate_embeddings,
                    context_repeated,
                    tree_state_repeated
                ], dim=-1)
                
                nn_scores = self.path_generator.node_selector(combined_input).squeeze(-1)
                nn_scores = torch.softmax(nn_scores, dim=0)
                
                # Get skill relevance scores for candidates
                skill_scores = node_relevance[candidate_indices]
                skill_scores = torch.softmax(skill_scores / 0.5, dim=0)  # Temperature scaling
                
                # Combine scores (weighted by learnable parameter)
                weight = torch.sigmoid(self.skill_weight)  # Clamp to [0, 1]
                combined_scores = weight * nn_scores + (1 - weight) * skill_scores
                
                # Select best node
                best_idx = torch.argmax(combined_scores)
                selected_node = candidate_indices[best_idx].item()
                
                # Allocate node
                allocated[selected_node] = True
                tree_sequence.append(selected_node)
                
                # Update tree state (simple running average)
                tree_state = tree_state * 0.9 + node_embeddings[selected_node] * 0.1
        
        return tree_sequence
    
    def get_skill_relevance_mask(
        self,
        skill_name: str,
        node_stats: List[Dict],
        support_gems: List[str] = None,
        threshold: float = 0.2
    ) -> torch.Tensor:
        """
        Get a binary mask of relevant nodes for a skill
        
        Args:
            skill_name: Main skill gem name
            node_stats: List of node stat dictionaries
            support_gems: Support gems (optional)
            threshold: Minimum relevance score
            
        Returns:
            Boolean tensor [num_nodes] where True = relevant
        """
        scaling_vector = self.skill_analyzer.analyze_skill(skill_name, support_gems)
        relevance_scores = self._calculate_node_relevance_batch(scaling_vector, node_stats)
        mask = torch.tensor(relevance_scores >= threshold, dtype=torch.bool)
        return mask
    
    def explain_node_relevance(
        self,
        skill_name: str,
        node_id: int,
        node_stats: Dict,
        support_gems: List[str] = None
    ) -> Dict:
        """
        Explain why a node is or isn't relevant for a skill
        
        Args:
            skill_name: Main skill gem name
            node_id: Node to explain
            node_stats: Stats for this node
            support_gems: Support gems (optional)
            
        Returns:
            Dictionary with explanation details
        """
        scaling_vector = self.skill_analyzer.analyze_skill(skill_name, support_gems)
        
        stats = node_stats.get('stats', {})
        relevance_score = self.skill_analyzer.calculate_node_relevance(scaling_vector, stats)
        
        # Find which stats contribute to relevance
        contributing_stats = []
        
        # Check damage types
        for damage_type in scaling_vector.increased_damage_types[:5]:  # Top 5
            stat_key = f"increased_{damage_type}"
            if stat_key in stats:
                contributing_stats.append({
                    'stat': stat_key,
                    'value': stats[stat_key],
                    'category': 'damage'
                })
        
        # Check speed
        if scaling_vector.speed_type != 'none':
            speed_key = f"increased_{scaling_vector.speed_type}"
            if speed_key in stats:
                contributing_stats.append({
                    'stat': speed_key,
                    'value': stats[speed_key],
                    'category': 'speed'
                })
        
        # Check crit
        if scaling_vector.scales_with_crit:
            for crit_type in scaling_vector.crit_types[:3]:  # Top 3
                if crit_type in stats:
                    contributing_stats.append({
                        'stat': crit_type,
                        'value': stats[crit_type],
                        'category': 'crit'
                    })
        
        return {
            'node_id': node_id,
            'skill_name': skill_name,
            'relevance_score': relevance_score,
            'is_relevant': relevance_score >= 0.3,
            'contributing_stats': contributing_stats,
            'skill_tags': list(scaling_vector.tags),
            'scales_with_crit': scaling_vector.scales_with_crit,
            'speed_type': scaling_vector.speed_type
        }


# Example usage
if __name__ == "__main__":
    # Load edge index (from tree_edges.json)
    import json
    
    edges_file = Path("../pob_data/tree_data/tree_edges.json")
    if edges_file.exists():
        with open(edges_file) as f:
            edges_data = json.load(f)
            edge_list = edges_data.get('edges', [])
            edge_index = torch.tensor(edge_list, dtype=torch.long).t()
    else:
        # Fallback: create simple chain
        edge_index = torch.tensor([[0, 1], [1, 2], [2, 3]], dtype=torch.long).t()
    
    # Create skill-aware model
    model = SkillAwareTreeBuilder(
        num_nodes=412,
        edge_index=edge_index,
        use_skill_filtering=True
    )
    
    # Example node stats (would normally come from PoB tree data)
    node_stats = [
        {
            'id': i,
            'stats': {
                'increased_spell_damage': 10 if i % 3 == 0 else 0,
                'increased_fire_damage': 12 if i % 5 == 0 else 0,
                'increased_cast_speed': 4 if i % 4 == 0 else 0,
                'increased_life': 8 if i % 2 == 0 else 0,
            }
        }
        for i in range(412)
    ]
    
    # Build context
    context = {
        'gear': torch.randn(1, 20),
        'gems': torch.randn(1, 30),
        'skill': torch.randn(1, 10)
    }
    
    # Build tree for Blade Vortex
    tree = model.build_tree_with_skill_context(
        start_node_idx=0,
        context=context,
        skill_name="Blade Vortex",
        support_gems=["Controlled Destruction", "Elemental Focus"],
        num_points=50,
        node_stats=node_stats
    )
    
    print(f"Built tree with {len(tree)} nodes for Blade Vortex")
    print(f"First 10 nodes: {tree[:10]}")
    
    # Explain a node
    explanation = model.explain_node_relevance(
        skill_name="Blade Vortex",
        node_id=tree[5],
        node_stats=node_stats[tree[5]]
    )
    print(f"\nNode {tree[5]} relevance: {explanation['relevance_score']:.2f}")
    print(f"Contributing stats: {explanation['contributing_stats']}")
