"""
Multi-Component Build Optimizer
Learns to optimize passive tree, gear, gems, and auras simultaneously
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple


class MultiComponentBuilder(nn.Module):
    """
    Main neural network that handles all build components:
    - Passive tree allocation
    - Gear stat recommendations
    - Gem selection
    - Cross-component synergies
    """
    
    def __init__(
        self,
        tree_dim: int = 1500,
        gear_dim: int = 500,
        gem_dim: int = 100,
        skill_dim: int = 8,  # Number of skills in database
        hidden_dim: int = 512,
        num_gear_slots: int = 10,
        stats_per_slot: int = 5
    ):
        super().__init__()
        
        self.tree_dim = tree_dim
        self.gear_dim = gear_dim
        self.gem_dim = gem_dim
        self.skill_dim = skill_dim
        self.num_gear_slots = num_gear_slots
        self.stats_per_slot = stats_per_slot
        
        # Component encoders
        self.tree_encoder = nn.Sequential(
            nn.Linear(tree_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU()
        )
        
        self.gear_encoder = nn.Sequential(
            nn.Linear(gear_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 256),
            nn.ReLU()
        )
        
        self.gem_encoder = nn.Sequential(
            nn.Linear(gem_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 128),
            nn.ReLU()
        )
        
        # Skill encoder (one-hot to embedding)
        self.skill_encoder = nn.Sequential(
            nn.Linear(skill_dim, 32),
            nn.ReLU()
        )
        
        # Shared interaction layer learns cross-component synergies
        # e.g., tree +% phys damage makes flat phys on gear more valuable
        self.interaction_layer = nn.Sequential(
            nn.Linear(256 + 256 + 128 + 32, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU()
        )
        
        # Component decoders
        # Tree decoder: outputs probability for each node
        self.tree_decoder = nn.Sequential(
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Linear(512, tree_dim),
            nn.Sigmoid()  # Probability of allocating each node
        )
        
        # Gear decoder: outputs 5 stats per slot
        self.gear_decoder = nn.Sequential(
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, num_gear_slots * stats_per_slot),
            nn.Sigmoid()  # Normalized 0-1, will be scaled to actual ranges
        )
        
        # Gem decoder: outputs support category multipliers
        self.gem_decoder = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 15),  # 15 support categories
            nn.Sigmoid()  # 0-1, will be scaled to 1.0-1.4x range
        )
        
        # Performance predictor
        self.performance_predictor = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 3)  # [dps, ehp, time_to_kill]
        )
    
    def forward(
        self,
        tree_vec: torch.Tensor,
        gear_vec: torch.Tensor,
        gem_vec: torch.Tensor,
        skill_vec: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass through the network
        
        Args:
            tree_vec: Binary vector of allocated nodes (batch, tree_dim)
            gear_vec: Aggregated gear stats (batch, gear_dim)
            gem_vec: Current gem setup (batch, gem_dim)
            skill_vec: One-hot encoded skill (batch, skill_dim)
            
        Returns:
            Dictionary containing:
            - tree_suggestions: Probability for each node
            - gear_suggestions: 5 stats per slot (num_slots * 5)
            - gem_multipliers: Support category multipliers
            - predicted_performance: [dps, ehp, ttk]
        """
        # Encode components
        tree_encoded = self.tree_encoder(tree_vec)
        gear_encoded = self.gear_encoder(gear_vec)
        gem_encoded = self.gem_encoder(gem_vec)
        skill_encoded = self.skill_encoder(skill_vec)
        
        # Learn interactions
        combined = torch.cat([tree_encoded, gear_encoded, gem_encoded, skill_encoded], dim=1)
        interaction = self.interaction_layer(combined)
        
        # Decode to component suggestions
        tree_probs = self.tree_decoder(interaction)
        gear_stats = self.gear_decoder(interaction)
        gem_mults = self.gem_decoder(interaction)
        
        # Predict performance
        performance = self.performance_predictor(interaction)
        
        return {
            'tree_suggestions': tree_probs,
            'gear_suggestions': gear_stats.view(-1, self.num_gear_slots, self.stats_per_slot),
            'gem_multipliers': gem_mults * 0.4 + 1.0,  # Scale to 1.0-1.4x range
            'predicted_performance': performance
        }
    
    def encode_build(
        self,
        tree_vec: torch.Tensor,
        gear_vec: torch.Tensor,
        gem_vec: torch.Tensor,
        skill_vec: torch.Tensor
    ) -> torch.Tensor:
        """
        Encode a build into a latent representation
        Useful for similarity search and clustering
        """
        tree_encoded = self.tree_encoder(tree_vec)
        gear_encoded = self.gear_encoder(gear_vec)
        gem_encoded = self.gem_encoder(gem_vec)
        skill_encoded = self.skill_encoder(skill_vec)
        
        combined = torch.cat([tree_encoded, gear_encoded, gem_encoded, skill_encoded], dim=1)
        return self.interaction_layer(combined)
    
    def predict_performance(
        self,
        tree_vec: torch.Tensor,
        gear_vec: torch.Tensor,
        gem_vec: torch.Tensor,
        skill_vec: torch.Tensor
    ) -> torch.Tensor:
        """
        Fast performance prediction without generating suggestions
        Used during genetic algorithm search
        """
        latent = self.encode_build(tree_vec, gear_vec, gem_vec, skill_vec)
        return self.performance_predictor(latent)


class ClusterAwareTreeOptimizer(nn.Module):
    """
    Tree optimizer that understands cluster structure
    Makes decisions at cluster level, not individual nodes
    """
    
    # 8 major clusters in PoE tree
    CLUSTERS = {
        'life': list(range(0, 200)),
        'damage': list(range(200, 400)),
        'crit': list(range(400, 600)),
        'es': list(range(600, 800)),
        'evasion': list(range(800, 1000)),
        'block': list(range(1000, 1200)),
        'speed': list(range(1200, 1400)),
        'utility': list(range(1400, 1500))
    }
    
    def __init__(self, tree_dim: int = 1500):
        super().__init__()
        
        # Cluster selector
        self.cluster_scorer = nn.Sequential(
            nn.Linear(tree_dim + 100, 256),  # +100 for skill context
            nn.ReLU(),
            nn.Linear(256, 8),  # Score for each cluster
            nn.Softmax(dim=1)
        )
        
        # Node selector within cluster
        self.node_selector = nn.Sequential(
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Linear(512, tree_dim),
            nn.Sigmoid()
        )
    
    def forward(
        self,
        current_tree: torch.Tensor,
        skill_context: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            cluster_weights: Importance of each cluster
            node_probabilities: Probability for each node
        """
        combined = torch.cat([current_tree, skill_context], dim=1)
        cluster_weights = self.cluster_scorer(combined)
        
        # This would be more complex in practice
        # Need to weight nodes by their cluster
        node_probs = self.node_selector(combined)
        
        return cluster_weights, node_probs


if __name__ == "__main__":
    # Test the model
    batch_size = 4
    model = MultiComponentBuilder()
    
    # Create dummy inputs
    tree = torch.rand(batch_size, 1500)
    gear = torch.rand(batch_size, 500)
    gems = torch.rand(batch_size, 100)
    
    # Forward pass
    output = model(tree, gear, gems)
    
    print("Tree suggestions shape:", output['tree_suggestions'].shape)
    print("Gear suggestions shape:", output['gear_suggestions'].shape)
    print("Gem multipliers shape:", output['gem_multipliers'].shape)
    print("Predicted performance shape:", output['predicted_performance'].shape)
    
    # Test performance prediction
    perf = model.predict_performance(tree, gear, gems)
    print("Performance prediction:", perf.shape)
