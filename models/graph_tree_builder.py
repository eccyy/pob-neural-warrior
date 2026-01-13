"""
Graph Neural Network for Path of Building Passive Tree
Learns to build connected trees by understanding graph structure
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool
from torch_geometric.data import Data, Batch
from typing import Dict, List, Tuple, Optional
import numpy as np


class TreeGraphEncoder(nn.Module):
    """
    Encode the passive tree as a graph and learn node embeddings
    Uses Graph Convolutional Networks to understand tree structure
    """
    
    def __init__(
        self,
        num_nodes: int = 412,
        node_feature_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 3
    ):
        super().__init__()
        self.num_nodes = num_nodes
        self.node_feature_dim = node_feature_dim
        
        # Initial node embeddings (learnable)
        self.node_embeddings = nn.Embedding(num_nodes, node_feature_dim)
        
        # Graph convolution layers
        self.conv_layers = nn.ModuleList()
        self.conv_layers.append(GCNConv(node_feature_dim, hidden_dim))
        for _ in range(num_layers - 1):
            self.conv_layers.append(GCNConv(hidden_dim, hidden_dim))
        
        # Batch normalization
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(hidden_dim) for _ in range(num_layers)
        ])
        
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, node_indices: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Args:
            node_indices: [num_nodes] node IDs
            edge_index: [2, num_edges] edge connectivity
            
        Returns:
            Node embeddings [num_nodes, hidden_dim]
        """
        # Get initial embeddings
        x = self.node_embeddings(node_indices)
        
        # Apply graph convolutions
        for i, conv in enumerate(self.conv_layers):
            x = conv(x, edge_index)
            x = self.batch_norms[i](x)
            x = F.relu(x)
            x = self.dropout(x)
        
        return x


class PathGenerator(nn.Module):
    """
    Generate connected paths in the tree using sequential decision making
    Outputs one node at a time, ensuring connectivity
    """
    
    def __init__(
        self,
        node_embedding_dim: int = 128,
        context_dim: int = 256,
        hidden_dim: int = 256
    ):
        super().__init__()
        
        # Context encoder (gear, gems, skill requirements)
        self.context_encoder = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Node selector (decides which node to allocate next)
        # Input: node_embedding (128) + context (256) + tree_state (256) = 640
        self.node_selector = nn.Sequential(
            nn.Linear(node_embedding_dim + hidden_dim + hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)  # Score for each candidate node
        )
        
        # State aggregator (current tree state)
        self.state_aggregator = nn.LSTM(
            input_size=node_embedding_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True
        )
    
    def forward(
        self,
        node_embeddings: torch.Tensor,
        context: torch.Tensor,
        current_tree: torch.Tensor,
        candidate_mask: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            node_embeddings: [num_nodes, embed_dim] all node embeddings
            context: [batch, context_dim] build context (gear, gems, skill)
            current_tree: [batch, num_allocated, embed_dim] currently allocated nodes
            candidate_mask: [batch, num_nodes] which nodes are valid to allocate
            
        Returns:
            scores: [batch, num_nodes] allocation scores (masked)
        """
        batch_size = context.size(0)
        
        # Encode context
        context_emb = self.context_encoder(context)  # [batch, hidden_dim]
        
        # Aggregate current tree state
        if current_tree.size(1) > 0:
            _, (tree_state, _) = self.state_aggregator(current_tree)
            tree_state = tree_state[-1]  # [batch, hidden_dim]
        else:
            tree_state = torch.zeros(batch_size, self.state_aggregator.hidden_size, device=context.device)
        
        # Score each node
        num_nodes = node_embeddings.size(0)
        
        # Expand for batch processing
        node_emb_expanded = node_embeddings.unsqueeze(0).expand(batch_size, -1, -1)  # [batch, num_nodes, embed_dim]
        context_expanded = context_emb.unsqueeze(1).expand(-1, num_nodes, -1)  # [batch, num_nodes, hidden_dim]
        tree_state_expanded = tree_state.unsqueeze(1).expand(-1, num_nodes, -1)  # [batch, num_nodes, hidden_dim]
        
        # Concatenate features
        features = torch.cat([node_emb_expanded, context_expanded, tree_state_expanded], dim=-1)
        
        # Score nodes
        scores = self.node_selector(features).squeeze(-1)  # [batch, num_nodes]
        
        # Apply candidate mask (only adjacent nodes are valid)
        scores = scores.masked_fill(~candidate_mask, float('-inf'))
        
        return scores


class GraphTreeBuilder(nn.Module):
    """
    Complete model that builds optimal passive trees using graph structure
    """
    
    def __init__(
        self,
        num_nodes: int = 412,
        edge_index: torch.Tensor = None,
        gear_dim: int = 500,
        gem_dim: int = 100,
        skill_dim: int = 8,
        max_allocated: int = 120
    ):
        super().__init__()
        self.num_nodes = num_nodes
        self.max_allocated = max_allocated
        
        # Store edge connectivity
        self.register_buffer('edge_index', edge_index)
        
        # Graph encoder
        self.graph_encoder = TreeGraphEncoder(num_nodes=num_nodes)
        
        # Path generator
        context_dim = gear_dim + gem_dim + skill_dim
        self.path_generator = PathGenerator(
            node_embedding_dim=128,
            context_dim=context_dim
        )
        
        # Performance predictor (estimates DPS, EHP)
        self.performance_predictor = nn.Sequential(
            nn.Linear(128 + context_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 2)  # DPS, EHP
        )
    
    def encode_tree(self) -> torch.Tensor:
        """Encode all nodes in the tree"""
        device = next(self.parameters()).device
        node_indices = torch.arange(self.num_nodes, device=device)
        return self.graph_encoder(node_indices, self.edge_index)
    
    def get_valid_candidates(
        self,
        allocated: torch.Tensor,
        starting_node: int
    ) -> torch.Tensor:
        """
        Get mask of valid nodes that can be allocated next
        Only nodes adjacent to currently allocated nodes are valid
        
        Args:
            allocated: [num_allocated] currently allocated node indices
            starting_node: class starting position
            
        Returns:
            mask: [num_nodes] boolean mask of valid candidates
        """
        device = allocated.device
        mask = torch.zeros(self.num_nodes, dtype=torch.bool, device=device)
        
        if len(allocated) == 0:
            # Only starting node is valid
            mask[starting_node] = True
        else:
            # Find nodes adjacent to allocated nodes
            allocated_set = set(allocated.cpu().numpy())
            
            for i in range(self.edge_index.size(1)):
                src, dst = self.edge_index[:, i]
                src, dst = src.item(), dst.item()
                
                if src in allocated_set and dst not in allocated_set:
                    mask[dst] = True
                elif dst in allocated_set and src not in allocated_set:
                    mask[src] = True
        
        return mask
    
    def build_tree_greedy(
        self,
        gear: torch.Tensor,
        gems: torch.Tensor,
        skill: torch.Tensor,
        num_points: int = 100,
        starting_node: int = 0
    ) -> torch.Tensor:
        """
        Build tree greedily by selecting highest scoring adjacent nodes
        
        Returns:
            allocated: [num_allocated] sequence of allocated node indices
        """
        batch_size = gear.size(0)
        device = gear.device
        
        # Encode tree
        node_embeddings = self.encode_tree()
        
        # Build context
        context = torch.cat([gear, gems, skill], dim=-1)
        
        # Initialize with starting node
        allocated = [torch.full((batch_size,), starting_node, device=device)]
        
        for step in range(num_points - 1):
            # Get current tree state
            current_indices = torch.stack(allocated, dim=1)  # [batch, num_allocated]
            current_embeddings = node_embeddings[current_indices]  # [batch, num_allocated, embed_dim]
            
            # Get valid candidates
            candidate_mask = self.get_valid_candidates(current_indices[0], starting_node)
            candidate_mask = candidate_mask.unsqueeze(0).expand(batch_size, -1)
            
            # Score candidates
            scores = self.path_generator(
                node_embeddings,
                context,
                current_embeddings,
                candidate_mask
            )
            
            # Select highest scoring valid node
            next_node = scores.argmax(dim=-1)  # [batch]
            allocated.append(next_node)
        
        return torch.stack(allocated, dim=1)
    
    def forward(
        self,
        gear: torch.Tensor,
        gems: torch.Tensor,
        skill: torch.Tensor,
        target_tree: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass - either teacher forcing (training) or greedy (inference)
        """
        if self.training and target_tree is not None:
            # Teacher forcing during training
            node_embeddings = self.encode_tree()
            context = torch.cat([gear, gems, skill], dim=-1)
            
            # TODO: Implement teacher forcing with target tree
            # For now, return dummy predictions
            batch_size = gear.size(0)
            performance = self.performance_predictor(
                torch.cat([node_embeddings.mean(0).unsqueeze(0).expand(batch_size, -1), context], dim=-1)
            )
            
            return {
                'performance': performance,
                'tree': target_tree
            }
        else:
            # Greedy decoding during inference
            allocated = self.build_tree_greedy(gear, gems, skill)
            
            # Predict performance
            node_embeddings = self.encode_tree()
            context = torch.cat([gear, gems, skill], dim=-1)
            tree_embedding = node_embeddings[allocated].mean(dim=1)
            performance = self.performance_predictor(
                torch.cat([tree_embedding, context], dim=-1)
            )
            
            return {
                'performance': performance,
                'tree': allocated
            }


def load_edge_index_from_builds(builds_path: str, node_mapping_path: str) -> torch.Tensor:
    """
    Load edge connectivity from extracted edge data
    
    Returns:
        edge_index: [2, num_edges] tensor
    """
    import json
    from pathlib import Path
    
    # Try to load pre-computed edge index first
    edges_path = Path(builds_path).parent / "tree_data" / "edge_index.json"
    if edges_path.exists():
        print(f"Loading edge index from {edges_path}")
        with open(edges_path) as f:
            edge_list = json.load(f)
        edge_index = torch.tensor(edge_list, dtype=torch.long).t()
        return edge_index
    
    # Fallback to old method
    edges_path = Path(builds_path).parent / "tree_data" / "tree_edges.json"
    if not edges_path.exists():
        raise FileNotFoundError(f"Edge data not found at {edges_path}")
    
    # Load node mapping
    with open(node_mapping_path) as f:
        mapping = json.load(f)
        node_to_idx = {int(k): v for k, v in mapping['node_to_index'].items()}
    
    # Load edges
    with open(edges_path) as f:
        edges_dict = json.load(f)
    
    # Convert to edge_index format
    edge_list = []
    for src_str, neighbors in edges_dict.items():
        src_id = int(src_str)
        if src_id in node_to_idx:
            src_idx = node_to_idx[src_id]
            for dst_str in neighbors:
                dst_id = int(dst_str)
                if dst_id in node_to_idx:
                    dst_idx = node_to_idx[dst_id]
                    edge_list.append([src_idx, dst_idx])
    
    edge_index = torch.tensor(edge_list, dtype=torch.long).t()
    return edge_index


if __name__ == "__main__":
    # Test the model
    print("Testing Graph Tree Builder...")
    
    # Load edge connectivity
    edge_index = load_edge_index_from_builds(
        "./pob_data/tree_data",
        "./pob_data/tree_data/node_mapping.json"
    )
    
    print(f"Loaded {edge_index.size(1)} edges")
    
    # Create model
    model = GraphTreeBuilder(
        num_nodes=412,
        edge_index=edge_index
    )
    
    # Test forward pass
    batch_size = 4
    gear = torch.randn(batch_size, 500)
    gems = torch.randn(batch_size, 100)
    skill = torch.randn(batch_size, 8)
    
    with torch.no_grad():
        output = model(gear, gems, skill)
    
    print(f"Output tree shape: {output['tree'].shape}")
    print(f"Performance shape: {output['performance'].shape}")
    print("✓ Model test passed!")
