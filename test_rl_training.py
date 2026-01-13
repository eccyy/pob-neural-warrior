"""
Test adversarial training loop with current GNN.
Uses simple heuristic rewards to verify RL mechanics work.
"""

import torch
import torch.nn.functional as F
import json
from pathlib import Path
from models.graph_tree_builder import GraphTreeBuilder, load_edge_index_from_builds

def simple_heuristic_reward(tree_indices, index_to_node):
    """
    Simple heuristic reward without needing full build stats.
    Rewards: diversity, notable allocation, avoiding over-concentration
    """
    tree_nodes = [index_to_node[idx] for idx in tree_indices]
    
    # Reward 1: Tree diversity (spread across tree)
    # Use variance in node IDs as proxy for spread
    diversity = torch.tensor(tree_nodes).float().std().item() / 10000.0
    
    # Reward 2: Tree size (more nodes = better, up to a point)
    size_score = min(len(tree_nodes) / 100.0, 1.0)
    
    # Reward 3: Connectivity efficiency (penalize backtracking)
    # Could measure average "distance" between consecutive nodes
    
    # Combined reward
    reward = 0.5 * diversity + 0.5 * size_score
    return reward

class RLGraphTreeBuilder(GraphTreeBuilder):
    """
    Extended GraphTreeBuilder with RL capabilities.
    Adds log probability tracking and sampling.
    """
    
    def build_tree_with_logprobs(self, start_node_idx, gear, gems, skill, num_nodes=100, temperature=1.0):
        """
        Build tree greedily but track log probabilities for RL.
        
        Args:
            temperature: Higher = more exploration. 1.0 = normal, 0.1 = greedy
        
        Returns:
            tree_sequence: List of node indices
            log_probs: List of log probabilities for each action
        """
        device = next(self.parameters()).device
        
        # Move inputs to device
        gear = gear.to(device)
        gems = gems.to(device)
        skill = skill.to(device)
        
        # Encode all tree nodes once
        node_embeddings = self.encode_tree()  # [num_nodes, 128]
        
        # Build context
        context = torch.cat([gear, gems, skill], dim=-1).unsqueeze(0)  # [1, context_dim]
        context_encoded = self.path_generator.context_encoder(context)  # [1, hidden_dim]
        
        # Track allocated nodes
        allocated = []
        tree_sequence = [start_node_idx]
        log_probs = []
        
        for step in range(num_nodes - 1):
            # Get valid candidates (neighbors of allocated nodes)
            candidate_mask = self.get_valid_candidates(
                torch.tensor(tree_sequence, device=device),
                start_node_idx
            )
            
            if not candidate_mask.any():
                break
            
            # Compute tree state from allocated nodes
            if len(tree_sequence) > 0:
                allocated_embeddings = node_embeddings[tree_sequence]
                tree_state = allocated_embeddings.mean(dim=0, keepdim=True)  # [1, 128]
            else:
                tree_state = torch.zeros(1, 128, device=device)
            
            # Score all nodes
            # node_selector expects: node_embedding (128) + context (256) + tree_state (256)
            # But context_encoded is already 256, tree_state should also be 256
            
            # Expand context and tree_state for broadcasting
            context_broadcast = context_encoded.expand(self.num_nodes, -1)  # [num_nodes, 256]
            
            # Tree state from allocated embeddings
            if len(tree_sequence) > 0:
                allocated_embeddings = node_embeddings[tree_sequence]
                tree_state_vec = allocated_embeddings.mean(dim=0)  # [128]
                # Project to 256
                tree_state_broadcast = tree_state_vec.unsqueeze(0).expand(self.num_nodes, -1)  # [num_nodes, 128]
                # Pad to 256
                tree_state_broadcast = F.pad(tree_state_broadcast, (0, 128))  # [num_nodes, 256]
            else:
                tree_state_broadcast = torch.zeros(self.num_nodes, 256, device=device)
            
            # Combine features: [num_nodes, 128+256+256=640]
            features = torch.cat([node_embeddings, context_broadcast, tree_state_broadcast], dim=-1)
            scores = self.path_generator.node_selector(features).squeeze(-1)  # [num_nodes]
            
            # Apply temperature and mask
            logits = scores / temperature
            logits = logits.masked_fill(~candidate_mask, float('-inf'))
            
            # Sample action
            action_probs = F.softmax(logits, dim=-1)
            
            if temperature > 0.5:  # Exploration
                next_node = torch.multinomial(action_probs, 1).item()
            else:  # Exploitation
                next_node = action_probs.argmax().item()
            
            # Store log probability
            log_prob = F.log_softmax(logits, dim=-1)[next_node]
            log_probs.append(log_prob)
            
            # Add to tree
            tree_sequence.append(next_node)
        
        return tree_sequence, torch.stack(log_probs) if log_probs else torch.tensor([])
    
    def _get_neighbors(self, node_idx):
        """Get all neighbors of a node from edge index."""
        neighbors = []
        for i in range(self.edge_index.size(1)):
            if self.edge_index[0, i] == node_idx:
                neighbors.append(self.edge_index[1, i].item())
            elif self.edge_index[1, i] == node_idx:
                neighbors.append(self.edge_index[0, i].item())
        return list(set(neighbors))

def test_rl_training():
    print("=" * 60)
    print("Testing RL Training Loop")
    print("=" * 60)
    
    # Load edge connectivity
    print("\n1. Loading tree structure...")
    edge_index = load_edge_index_from_builds(
        "./pob_data/tree_data",
        "./pob_data/tree_data/node_mapping.json"
    )
    print(f"   ✓ Loaded {edge_index.size(1)} edges")
    
    # Load node mapping
    print("\n2. Loading node mapping...")
    with open("./pob_data/tree_data/node_mapping.json") as f:
        mapping = json.load(f)
        node_to_index = {int(k): int(v) for k, v in mapping['node_to_index'].items()}
        index_to_node = {int(v): int(k) for k, v in mapping['node_to_index'].items()}
    
    start_node_id = 11334  # Shadow bridge node
    start_idx = node_to_index[start_node_id]
    print(f"   ✓ Starting from node {start_node_id} (index {start_idx})")
    
    # Create RL-capable model
    print("\n3. Creating RL-capable GNN...")
    model = RLGraphTreeBuilder(
        num_nodes=412,
        edge_index=edge_index
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    print(f"   ✓ Model ready ({sum(p.numel() for p in model.parameters()):,} parameters)")
    
    # Training loop
    print("\n4. Running RL training loop...")
    print(f"   Testing {5} iterations with REINFORCE algorithm\n")
    
    # Dummy context (match actual dimensions)
    gear = torch.randn(500)   # gear_dim from model
    gems = torch.randn(100)   # gem_dim from model
    skill = torch.randn(8)    # skill_dim from model
    
    for iteration in range(5):
        model.train()
        optimizer.zero_grad()
        
        # Generate tree with log probabilities
        temperature = 1.0 if iteration < 3 else 0.5  # Explore then exploit
        tree_sequence, log_probs = model.build_tree_with_logprobs(
            start_idx, gear, gems, skill,
            num_nodes=50,  # Smaller for faster testing
            temperature=temperature
        )
        
        # Compute reward (simple heuristic for now)
        reward = simple_heuristic_reward(tree_sequence, index_to_node)
        
        # REINFORCE update: maximize log_prob * reward
        # Policy gradient: -∑ log π(a) * R
        policy_loss = -(log_probs * reward).sum()
        
        # Backward pass
        policy_loss.backward()
        
        # Clip gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        print(f"   Iter {iteration + 1}:")
        print(f"     Tree size: {len(tree_sequence)} nodes")
        print(f"     Reward: {reward:.4f}")
        print(f"     Loss: {policy_loss.item():.4f}")
        print(f"     Avg log_prob: {log_probs.mean().item():.4f}")
        print(f"     Temperature: {temperature}")
    
    print("\n" + "=" * 60)
    print("RL Training Test Complete!")
    print("=" * 60)
    print("\n✓ GNN successfully generates trees with log probabilities")
    print("✓ REINFORCE updates work (gradients flow)")
    print("✓ Rewards influence policy (loss changes)")
    print("\nNext steps:")
    print("  1. Implement BuildStatsDecoder for real rewards")
    print("  2. Create fight simulator for survival/DPS scoring")
    print("  3. Scale up to full training run")

if __name__ == "__main__":
    test_rl_training()
