"""
Graph Tree Training with Adversarial/Reinforcement Learning
Uses policy gradient methods to optimize tree building
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Tuple
from tqdm import tqdm

from models.graph_tree_builder import GraphTreeBuilder, load_edge_index_from_builds


class TreeRewardCalculator:
    """
    Calculate rewards for tree allocations
    Combines multiple objectives: connectivity, efficiency, performance
    """
    
    def __init__(self):
        self.rewards = {
            'connectivity': 1.0,  # Valid connected path
            'efficiency': 0.5,  # Point usage efficiency  
            'keystones': 2.0,  # Keystone allocation bonus
            'stats': 1.0,  # Useful stats (life, damage, etc.)
            'redundancy': -0.5  # Penalty for redundant paths
        }
    
    def calculate_reward(
        self,
        allocated_tree: torch.Tensor,
        predicted_performance: torch.Tensor,
        target_performance: torch.Tensor,
        is_connected: bool
    ) -> torch.Tensor:
        """
        Calculate reward for a tree allocation
        
        Args:
            allocated_tree: [batch, num_allocated] allocated node indices
            predicted_performance: [batch, 2] predicted DPS, EHP
            target_performance: [batch, 2] target DPS, EHP
            is_connected: whether tree is valid connected path
            
        Returns:
            reward: [batch] scalar rewards
        """
        batch_size = allocated_tree.size(0)
        device = allocated_tree.device
        
        reward = torch.zeros(batch_size, device=device)
        
        # Connectivity reward (mandatory)
        if is_connected:
            reward += self.rewards['connectivity'] * 10.0
        else:
            reward -= 50.0  # Heavy penalty for disconnected trees
        
        # Performance reward (closer to target is better)
        dps_error = torch.abs(predicted_performance[:, 0] - target_performance[:, 0])
        ehp_error = torch.abs(predicted_performance[:, 1] - target_performance[:, 1])
        
        # Normalize errors
        dps_reward = -dps_error / (target_performance[:, 0] + 1e-6)
        ehp_reward = -ehp_error / (target_performance[:, 1] + 1e-6)
        
        reward += (dps_reward + ehp_reward) * 5.0
        
        # Efficiency reward (fewer points is better)
        num_allocated = allocated_tree.size(1)
        efficiency = 1.0 - (num_allocated / 120.0)  # Prefer under 120 points
        reward += efficiency * self.rewards['efficiency']
        
        return reward


class PolicyGradientTrainer:
    """
    Train the graph tree builder using policy gradient (REINFORCE)
    """
    
    def __init__(
        self,
        model: GraphTreeBuilder,
        learning_rate: float = 1e-4,
        gamma: float = 0.99,
        entropy_weight: float = 0.01
    ):
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        self.gamma = gamma
        self.entropy_weight = entropy_weight
        self.reward_calculator = TreeRewardCalculator()
    
    def train_episode(
        self,
        gear: torch.Tensor,
        gems: torch.Tensor,
        skill: torch.Tensor,
        target_performance: torch.Tensor
    ) -> Dict[str, float]:
        """
        Train on one episode (build one tree)
        
        Returns:
            metrics: dict of training metrics
        """
        self.model.train()
        self.optimizer.zero_grad()
        
        batch_size = gear.size(0)
        device = gear.device
        
        # Build tree and collect log probabilities
        node_embeddings = self.model.encode_tree()
        context = torch.cat([gear, gems, skill], dim=-1)
        
        allocated = []
        log_probs = []
        entropies = []
        
        starting_node = 0  # TODO: Get from class
        current_node = torch.full((batch_size,), starting_node, device=device)
        allocated.append(current_node)
        
        # Build tree step by step
        for step in range(99):  # 100 points total
            # Get current state
            current_indices = torch.stack(allocated, dim=1)
            current_embeddings = node_embeddings[current_indices]
            
            # Get valid candidates
            candidate_mask = self.model.get_valid_candidates(current_indices[0], starting_node)
            candidate_mask = candidate_mask.unsqueeze(0).expand(batch_size, -1)
            
            # Get action distribution
            scores = self.model.path_generator(
                node_embeddings,
                context,
                current_embeddings,
                candidate_mask
            )
            
            # Sample action
            probs = torch.softmax(scores, dim=-1)
            dist = torch.distributions.Categorical(probs)
            action = dist.sample()
            
            # Record log probability and entropy
            log_probs.append(dist.log_prob(action))
            entropies.append(dist.entropy())
            
            allocated.append(action)
        
        # Get final tree
        final_tree = torch.stack(allocated, dim=1)
        
        # Predict performance
        tree_embedding = node_embeddings[final_tree].mean(dim=1)
        predicted_performance = self.model.performance_predictor(
            torch.cat([tree_embedding, context], dim=-1)
        )
        
        # Calculate reward
        is_connected = True  # TODO: Validate connectivity
        reward = self.reward_calculator.calculate_reward(
            final_tree,
            predicted_performance,
            target_performance,
            is_connected
        )
        
        # Calculate policy gradient loss
        log_probs = torch.stack(log_probs, dim=1)  # [batch, num_steps]
        entropies = torch.stack(entropies, dim=1)  # [batch, num_steps]
        
        # Compute returns (discounted rewards)
        returns = []
        R = reward
        for t in reversed(range(log_probs.size(1))):
            returns.insert(0, R)
            R = R * self.gamma
        returns = torch.stack(returns, dim=1)
        
        # Policy loss
        policy_loss = -(log_probs * returns.detach()).mean()
        
        # Entropy bonus (encourage exploration)
        entropy_loss = -entropies.mean() * self.entropy_weight
        
        # Total loss
        loss = policy_loss + entropy_loss
        
        # Backprop
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        
        return {
            'loss': loss.item(),
            'reward': reward.mean().item(),
            'policy_loss': policy_loss.item(),
            'entropy': entropies.mean().item()
        }
    
    def train(
        self,
        train_data: List[Dict],
        num_epochs: int = 100,
        batch_size: int = 8,
        save_dir: str = "checkpoints"
    ):
        """
        Train the model using policy gradient
        """
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)
        
        best_reward = float('-inf')
        history = []
        
        for epoch in range(num_epochs):
            epoch_metrics = {
                'loss': [],
                'reward': [],
                'policy_loss': [],
                'entropy': []
            }
            
            # Create batches
            np.random.shuffle(train_data)
            num_batches = len(train_data) // batch_size
            
            progress = tqdm(range(num_batches), desc=f"Epoch {epoch+1}/{num_epochs}")
            
            for batch_idx in progress:
                # Get batch
                batch_start = batch_idx * batch_size
                batch_end = batch_start + batch_size
                batch = train_data[batch_start:batch_end]
                
                # Convert to tensors
                gear = torch.stack([torch.tensor(b['gear'], dtype=torch.float32) for b in batch])
                gems = torch.stack([torch.tensor(b['gems'], dtype=torch.float32) for b in batch])
                skill = torch.stack([torch.tensor(b['skill'], dtype=torch.float32) for b in batch])
                target_perf = torch.stack([
                    torch.tensor([b.get('dps', 1000000), b.get('ehp', 50000)], dtype=torch.float32)
                    for b in batch
                ])
                
                # Train episode
                metrics = self.train_episode(gear, gems, skill, target_perf)
                
                # Record metrics
                for key in epoch_metrics:
                    epoch_metrics[key].append(metrics[key])
                
                # Update progress
                progress.set_postfix({
                    'loss': metrics['loss'],
                    'reward': metrics['reward']
                })
            
            # Epoch summary
            avg_metrics = {k: np.mean(v) for k, v in epoch_metrics.items()}
            history.append(avg_metrics)
            
            print(f"Epoch {epoch+1} - Loss: {avg_metrics['loss']:.4f}, "
                  f"Reward: {avg_metrics['reward']:.4f}, "
                  f"Entropy: {avg_metrics['entropy']:.4f}")
            
            # Save best model
            if avg_metrics['reward'] > best_reward:
                best_reward = avg_metrics['reward']
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'reward': best_reward,
                    'history': history
                }, save_path / "best_graph_model.pt")
                print(f"✓ Saved best model (reward: {best_reward:.4f})")
        
        return history


def load_training_data(data_path: str) -> List[Dict]:
    """Load training data from imported builds"""
    with open(data_path) as f:
        data = json.load(f)
    
    # Convert to list format
    builds = []
    for build in data:
        builds.append({
            'gear': build['gear'],
            'gems': build['gems'],
            'skill': build['skill'],
            'tree': build['tree'],
            'dps': build.get('dps', 1000000),
            'ehp': build.get('ehp', 50000)
        })
    
    return builds


if __name__ == "__main__":
    print("Graph Tree Training with Policy Gradient")
    print("=" * 50)
    
    # Load edge connectivity
    print("Loading tree structure...")
    edge_index = load_edge_index_from_builds(
        "./pob_data/tree_data",
        "./pob_data/tree_data/node_mapping.json"
    )
    print(f"✓ Loaded {edge_index.size(1)} edges")
    
    # Create model
    print("Creating model...")
    model = GraphTreeBuilder(
        num_nodes=412,
        edge_index=edge_index
    )
    print(f"✓ Model created with {sum(p.numel() for p in model.parameters())} parameters")
    
    # Load training data
    print("Loading training data...")
    train_data = load_training_data("./training_data/imported_builds_327.json")
    print(f"✓ Loaded {len(train_data)} builds")
    
    # Create trainer
    trainer = PolicyGradientTrainer(model, learning_rate=1e-4)
    
    # Train
    print("\nStarting training...")
    history = trainer.train(
        train_data,
        num_epochs=50,
        batch_size=4
    )
    
    print("\n✓ Training complete!")
