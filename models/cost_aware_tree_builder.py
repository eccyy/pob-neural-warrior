"""
Cost-Aware Tree Builder with Distance-based ROI
Incorporates pathing costs and starting position into passive tree optimization
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
import numpy as np
import sys
from pathlib import Path
from collections import deque

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.skill_aware_tree_builder import SkillAwareTreeBuilder
from utils.skill_scaling_analyzer import ScalingVector


class CostAwareTreeBuilder(SkillAwareTreeBuilder):
    """
    Enhanced tree builder that considers:
    1. Distance from starting position (pathing cost)
    2. ROI (efficiency / effective cost)
    3. Diminishing returns on repeated stat types
    4. Balanced allocation across scaling vectors
    """
    
    def __init__(
        self,
        num_nodes: int,
        edge_index: torch.Tensor,
        node_feature_dim: int = 64,
        hidden_dim: int = 128,
        context_dim: int = 256,
        distance_penalty: float = 0.1,  # Penalty per node distance
        balance_reward: float = 0.3,     # Reward for balanced allocation
    ):
        super().__init__(num_nodes, edge_index, node_feature_dim, hidden_dim, context_dim)
        
        self.distance_penalty = distance_penalty
        self.balance_reward = balance_reward
        
        # Learnable parameters for cost-aware scoring
        self.distance_weight = nn.Parameter(torch.tensor(0.15))  # How much distance matters
        self.roi_weight = nn.Parameter(torch.tensor(0.35))       # How much ROI matters
        self.balance_weight = nn.Parameter(torch.tensor(0.30))   # How much balance matters
        self.gnn_weight = nn.Parameter(torch.tensor(0.20))       # How much GNN score matters
        
        # Cache for distance calculations
        self._distance_cache = {}
        
    def calculate_distances_from_start(
        self,
        start_node_idx: int,
        edge_index: torch.Tensor,
        max_distance: int = 100
    ) -> torch.Tensor:
        """
        Calculate shortest path distance from start node to all other nodes using BFS
        
        Args:
            start_node_idx: Starting node index
            edge_index: Edge connectivity [2, num_edges]
            max_distance: Maximum distance to compute (nodes beyond are set to max_distance)
            
        Returns:
            Tensor of distances [num_nodes]
        """
        cache_key = (start_node_idx, max_distance)
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]
        
        # Build adjacency list
        adj_list = [[] for _ in range(self.num_nodes)]
        edges = edge_index.cpu().numpy()
        for i in range(edges.shape[1]):
            src, dst = edges[0, i], edges[1, i]
            adj_list[src].append(dst)
            adj_list[dst].append(src)  # Undirected
        
        # BFS
        distances = np.full(self.num_nodes, max_distance, dtype=np.float32)
        distances[start_node_idx] = 0
        
        queue = deque([start_node_idx])
        
        while queue:
            node = queue.popleft()
            current_dist = distances[node]
            
            if current_dist >= max_distance:
                continue
            
            for neighbor in adj_list[node]:
                if distances[neighbor] > current_dist + 1:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)
        
        distances_tensor = torch.tensor(distances, dtype=torch.float32)
        self._distance_cache[cache_key] = distances_tensor
        return distances_tensor
    
    def calculate_effective_cost(
        self,
        distances: torch.Tensor,
        base_cost: float = 1.0
    ) -> torch.Tensor:
        """
        Calculate effective cost including distance penalty
        
        Effective Cost = base_cost * (1 + distance_penalty * distance)
        
        Args:
            distances: Distance from start for each node [num_nodes]
            base_cost: Base cost per point (default 1.0)
            
        Returns:
            Effective cost tensor [num_nodes]
        """
        return base_cost * (1.0 + self.distance_penalty * distances)
    
    def calculate_roi_scores(
        self,
        node_relevance: torch.Tensor,
        effective_costs: torch.Tensor,
        current_allocation: Dict[str, float],
        scaling_vector: ScalingVector,
        node_stats: List[Dict]
    ) -> torch.Tensor:
        """
        Calculate ROI considering:
        1. Base efficiency (node_relevance)
        2. Effective cost (including distance)
        3. Diminishing returns (based on current allocation)
        
        Args:
            node_relevance: Base relevance scores [num_nodes]
            effective_costs: Effective costs including distance [num_nodes]
            current_allocation: Current stat allocation dict
            scaling_vector: Skill scaling requirements
            node_stats: List of node stat dicts
            
        Returns:
            ROI scores [num_nodes]
        """
        roi_scores = torch.zeros(self.num_nodes)
        
        for node_idx, stats in enumerate(node_stats):
            if stats is None:
                continue
            
            base_efficiency = node_relevance[node_idx].item()
            effective_cost = effective_costs[node_idx].item()
            
            if effective_cost <= 0:
                continue
            
            # Calculate diminishing returns multiplier
            # As we allocate more to a stat type, additional points give less value
            diminishing_mult = self._calculate_diminishing_returns(
                stats, current_allocation, scaling_vector
            )
            
            # ROI = (efficiency * diminishing_returns) / effective_cost
            roi = (base_efficiency * diminishing_mult) / effective_cost
            roi_scores[node_idx] = roi
        
        return roi_scores
    
    def _calculate_diminishing_returns(
        self,
        node_stats: Dict,
        current_allocation: Dict[str, float],
        scaling_vector: ScalingVector
    ) -> float:
        """
        Calculate diminishing returns multiplier based on current allocation
        
        The more we've invested in a stat type, the less valuable additional points become
        This encourages balanced allocation across different vectors
        
        Args:
            node_stats: Stats provided by this node
            current_allocation: Current total % in each stat category
            scaling_vector: Skill scaling requirements
            
        Returns:
            Multiplier in range [0.3, 1.0] (heavily diminishing at high allocation)
        """
        # For each stat this node provides, check current allocation
        diminishing_factors = []
        
        for stat_name, stat_value in node_stats.items():
            if stat_value <= 0:
                continue
            
            # Map stat to category (e.g., "increased_damage", "crit_chance", etc.)
            category = self._map_stat_to_category(stat_name)
            
            if category in current_allocation:
                current_value = current_allocation[category]
                
                # Get ceiling for this category
                ceiling = self._get_category_ceiling(category)
                
                if ceiling > 0:
                    # Diminishing returns: 1.0 at 0%, 0.5 at 50%, 0.3 at 100%
                    allocation_ratio = current_value / ceiling
                    # Use exponential decay: e^(-2 * ratio)
                    factor = np.exp(-2.0 * allocation_ratio)
                    # Clamp to [0.3, 1.0]
                    factor = max(0.3, min(1.0, factor))
                    diminishing_factors.append(factor)
        
        # Return average diminishing factor (or 1.0 if no relevant stats)
        if len(diminishing_factors) == 0:
            return 1.0
        return np.mean(diminishing_factors)
    
    def _map_stat_to_category(self, stat_name: str) -> str:
        """Map specific stat names to general categories"""
        stat_lower = stat_name.lower()
        
        # Damage categories
        if any(word in stat_lower for word in ['damage', 'spell', 'attack', 'physical', 'elemental']):
            if 'multiplier' in stat_lower or 'multi' in stat_lower:
                return 'damage_over_time_multiplier'
            return 'increased_damage'
        
        # Speed categories
        if 'attack speed' in stat_lower:
            return 'attack_speed'
        if 'cast speed' in stat_lower:
            return 'cast_speed'
        
        # Crit categories
        if 'critical' in stat_lower or 'crit' in stat_lower:
            if 'multiplier' in stat_lower or 'multi' in stat_lower:
                return 'critical_strike_multiplier'
            return 'critical_strike_chance'
        
        # Defensive categories
        if 'life' in stat_lower or 'maximum life' in stat_lower:
            return 'maximum_life'
        if 'energy shield' in stat_lower:
            return 'energy_shield'
        
        # Default
        return stat_name.lower().replace(' ', '_')
    
    def _get_category_ceiling(self, category: str) -> float:
        """Get realistic ceiling for a stat category"""
        ceilings = {
            'increased_damage': 300.0,
            'attack_speed': 150.0,
            'cast_speed': 150.0,
            'critical_strike_chance': 95.0,
            'critical_strike_multiplier': 500.0,
            'damage_over_time_multiplier': 100.0,
            'maximum_life': 250.0,
            'energy_shield': 250.0,
        }
        return ceilings.get(category, 200.0)  # Default ceiling
    
    def calculate_balance_score(
        self,
        current_allocation: Dict[str, float],
        scaling_vector: ScalingVector
    ) -> float:
        """
        Calculate how balanced the current allocation is
        Balanced allocation (similar % in each vector) maximizes product
        
        Uses coefficient of variation: lower = more balanced
        
        Args:
            current_allocation: Current % allocated to each category
            scaling_vector: Relevant categories for this skill
            
        Returns:
            Balance score in [0, 1] where 1 = perfectly balanced
        """
        # Get values for relevant categories only
        relevant_values = []
        
        for category in ['increased_damage', 'attack_speed', 'cast_speed', 
                        'critical_strike_chance', 'critical_strike_multiplier',
                        'damage_over_time_multiplier', 'maximum_life']:
            if category in current_allocation:
                relevant_values.append(current_allocation[category])
        
        if len(relevant_values) < 2:
            return 1.0  # Can't judge balance with < 2 vectors
        
        # Coefficient of variation: std / mean
        values = np.array(relevant_values)
        mean = np.mean(values)
        
        if mean < 1e-6:
            return 1.0  # No allocation yet
        
        std = np.std(values)
        cv = std / mean
        
        # Convert to score: 0 CV = 1.0 score, high CV = 0.0 score
        # Use exponential decay
        balance_score = np.exp(-cv)
        
        return balance_score
    
    def build_tree_with_cost_awareness(
        self,
        start_node_idx: int,
        starting_class: str,
        context: Dict,
        skill_name: str,
        support_gems: List[str] = None,
        num_points: int = 100,
        node_stats: Optional[List[Dict]] = None
    ) -> Tuple[List[int], Dict]:
        """
        Build passive tree with cost-awareness and ROI optimization
        
        Args:
            start_node_idx: Starting node index
            starting_class: Starting class name (Shadow, Witch, Marauder, etc.)
            context: Build context tensors
            skill_name: Main skill gem name
            support_gems: Support gems list
            num_points: Passive points budget
            node_stats: Node statistics
            
        Returns:
            Tuple of (allocated_nodes, metrics_dict)
        """
        if node_stats is None:
            raise ValueError("node_stats required for cost-aware building")
        
        # Analyze skill scaling
        scaling_vector = self.skill_analyzer.analyze_skill(skill_name, support_gems)
        
        # Calculate distances from start
        distances = self.calculate_distances_from_start(start_node_idx, self.edge_index)
        effective_costs = self.calculate_effective_cost(distances)
        
        # Calculate base relevance scores
        node_relevance = self._calculate_node_relevance_batch(scaling_vector, node_stats)
        node_relevance_tensor = torch.tensor(node_relevance, dtype=torch.float32)
        
        # Initialize allocation tracking
        current_allocation = {}
        allocated_nodes = [start_node_idx]
        available_nodes = set()
        
        # Add neighbors of start node
        self._update_available_nodes(start_node_idx, allocated_nodes, available_nodes)
        
        # Track metrics
        metrics = {
            'dps_values': [100.0],  # Start with base DPS
            'balance_scores': [1.0],
            'total_costs': [0.0],
            'roi_values': [1.0]
        }
        
        # Greedy allocation with cost-awareness
        for step in range(num_points):
            if len(available_nodes) == 0:
                print(f"  Warning: No available nodes at step {step}")
                break
            
            # Calculate ROI for all available nodes
            roi_scores = self.calculate_roi_scores(
                node_relevance_tensor,
                effective_costs,
                current_allocation,
                scaling_vector,
                node_stats
            )
            
            # Calculate balance score
            balance_score = self.calculate_balance_score(current_allocation, scaling_vector)
            
            # Get GNN scores (from parent class)
            gnn_scores = self._get_gnn_scores(context)
            
            # Combined scoring with learnable weights
            combined_scores = (
                self.roi_weight * roi_scores +
                self.balance_weight * balance_score +
                self.gnn_weight * gnn_scores
            )
            
            # Mask unavailable nodes
            mask = torch.ones(self.num_nodes) * float('-inf')
            for node_idx in available_nodes:
                mask[node_idx] = 0.0
            combined_scores = combined_scores + mask
            
            # Select best node
            best_node = torch.argmax(combined_scores).item()
            
            if best_node in allocated_nodes:
                break
            
            # Allocate node
            allocated_nodes.append(best_node)
            
            # Update allocation tracking
            stats = node_stats[best_node]
            if stats:
                for stat_name, stat_value in stats.items():
                    category = self._map_stat_to_category(stat_name)
                    current_allocation[category] = current_allocation.get(category, 0.0) + stat_value
            
            # Update available nodes (add neighbors)
            self._update_available_nodes(best_node, allocated_nodes, available_nodes)
            
            # Track metrics
            dps = self._estimate_dps(current_allocation, scaling_vector)
            metrics['dps_values'].append(dps)
            metrics['balance_scores'].append(balance_score)
            metrics['total_costs'].append(effective_costs[best_node].item())
            metrics['roi_values'].append(roi_scores[best_node].item())
        
        return allocated_nodes, metrics
    
    def _get_gnn_scores(self, context: Dict) -> torch.Tensor:
        """Get scores from GNN embeddings"""
        # Simplified - in practice would use actual GNN forward pass
        return torch.randn(self.num_nodes) * 0.1  # Small random component
    
    def _update_available_nodes(
        self,
        new_node: int,
        allocated_nodes: List[int],
        available_nodes: set
    ):
        """Update set of nodes available for allocation"""
        # Add neighbors of newly allocated node
        edges = self.edge_index.cpu().numpy()
        for i in range(edges.shape[1]):
            src, dst = edges[0, i], edges[1, i]
            if src == new_node and dst not in allocated_nodes:
                available_nodes.add(dst)
            elif dst == new_node and src not in allocated_nodes:
                available_nodes.add(src)
    
    def _estimate_dps(
        self,
        allocation: Dict[str, float],
        scaling_vector: ScalingVector
    ) -> float:
        """
        Estimate DPS based on current allocation
        DPS = base * product of (1 + value/100) for each category
        """
        base_dps = 100.0
        multiplier = 1.0
        
        for category in ['increased_damage', 'attack_speed', 'cast_speed',
                        'critical_strike_chance', 'critical_strike_multiplier',
                        'damage_over_time_multiplier', 'maximum_life']:
            if category in allocation:
                value = allocation[category]
                
                # Special handling for crit (needs both chance and multi)
                if category == 'critical_strike_chance':
                    crit_chance = value / 100.0
                    crit_multi = allocation.get('critical_strike_multiplier', 0) / 100.0
                    base_multi = 1.5  # Base crit multi
                    crit_mult = 1.0 + crit_chance * (base_multi + crit_multi - 1.0)
                    multiplier *= crit_mult
                elif category != 'critical_strike_multiplier':
                    # Skip multi since it's handled with chance
                    multiplier *= (1.0 + value / 100.0)
        
        return base_dps * multiplier


def demonstrate_cost_aware_building():
    """Demonstrate cost-aware tree building"""
    print("=" * 80)
    print("COST-AWARE TREE BUILDER DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Create simple graph (5x5 grid for demo)
    size = 5
    num_nodes = size * size
    edges = []
    
    # Connect grid nodes
    for i in range(size):
        for j in range(size):
            node = i * size + j
            # Right neighbor
            if j < size - 1:
                edges.append([node, node + 1])
            # Bottom neighbor
            if i < size - 1:
                edges.append([node, node + size])
    
    edge_index = torch.tensor(edges, dtype=torch.long).t()
    
    # Create builder
    builder = CostAwareTreeBuilder(
        num_nodes=num_nodes,
        edge_index=edge_index,
        distance_penalty=0.1
    )
    
    # Mock node stats
    node_stats = []
    for i in range(num_nodes):
        # Nodes far from start have better stats but higher cost
        distance_from_start = abs(i // size - 0) + abs(i % size - 0)
        stats = {
            'increased_damage': 5 + distance_from_start * 2,
            'attack_speed': 3 + distance_from_start * 1,
        }
        node_stats.append(stats)
    
    print("Demo: 5x5 grid, start at (0,0)")
    print("Far nodes have better stats but higher distance cost")
    print()
    
    # Calculate distances
    distances = builder.calculate_distances_from_start(0, edge_index)
    print(f"Sample distances: {distances[:10].numpy()}")
    
    effective_costs = builder.calculate_effective_cost(distances)
    print(f"Sample effective costs: {effective_costs[:10].numpy()}")
    print()
    
    print("KEY CONCEPTS:")
    print("1. Distance Penalty: Far nodes cost more (1 + 0.1 × distance)")
    print("2. ROI: (efficiency × diminishing_returns) / effective_cost")
    print("3. Balance Reward: Encourages spreading points across vectors")
    print("4. GNN scores add learned component on top of analytical ROI")
    print()
    print("This enables the neural network to learn optimal pathing strategies!")
    

if __name__ == "__main__":
    demonstrate_cost_aware_building()
