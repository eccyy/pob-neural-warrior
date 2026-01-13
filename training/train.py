"""
Training Loop with Multi-Objective Optimization
Trains the neural network to predict build performance
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path
from typing import Dict, List, Tuple
import json
import numpy as np
from tqdm import tqdm

import sys
sys.path.append('..')
from models.multi_component import MultiComponentBuilder
from training.data_collection import TrainingDataset


class MultiObjectiveLoss(nn.Module):
    """
    Combined loss for multiple optimization objectives
    - DPS prediction
    - EHP prediction  
    - Component accuracy (tree, gear, gems)
    """
    
    def __init__(
        self,
        dps_weight: float = 0.4,
        ehp_weight: float = 0.3,
        tree_weight: float = 0.15,
        gear_weight: float = 0.1,
        gem_weight: float = 0.05
    ):
        super().__init__()
        self.dps_weight = dps_weight
        self.ehp_weight = ehp_weight
        self.tree_weight = tree_weight
        self.gear_weight = gear_weight
        self.gem_weight = gem_weight
        
        self.mse = nn.MSELoss()
        # Use BCELoss with clamping to prevent numerical issues
        self.bce = nn.BCELoss(reduction='mean')
    
    def forward(
        self,
        predictions: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute multi-objective loss
        
        Args:
            predictions: Model outputs
            targets: Ground truth values
            
        Returns:
            total_loss: Combined loss
            loss_dict: Individual loss components
        """
        # Performance prediction loss
        pred_perf = predictions['predicted_performance']
        target_perf = targets['performance']
        
        dps_loss = self.mse(pred_perf[:, 0], target_perf[:, 0])
        ehp_loss = self.mse(pred_perf[:, 1], target_perf[:, 1])
        
        # Component reconstruction loss
        # Clamp predictions to avoid BCE numerical issues
        tree_pred_clamped = torch.clamp(predictions['tree_suggestions'], 1e-7, 1 - 1e-7)
        tree_loss = self.bce(
            tree_pred_clamped,
            targets['tree']
        )
        
        # Gear loss (MSE on continuous values)
        # Flatten gear suggestions from [batch, 10, 5] to [batch, 50]
        gear_pred_flat = predictions['gear_suggestions'].view(predictions['gear_suggestions'].size(0), -1)
        # Take first 50 values from gear target (or pad if needed)
        gear_target_flat = targets['gear_normalized'][:, :gear_pred_flat.size(1)]
        gear_loss = self.mse(gear_pred_flat, gear_target_flat)
        
        # Gem loss (MSE on multipliers)
        gem_loss = self.mse(
            predictions['gem_multipliers'],
            targets['gem_multipliers']
        )
        
        # Combine losses
        total_loss = (
            self.dps_weight * dps_loss +
            self.ehp_weight * ehp_loss +
            self.tree_weight * tree_loss +
            self.gear_weight * gear_loss +
            self.gem_weight * gem_loss
        )
        
        loss_dict = {
            'total': total_loss.item(),
            'dps': dps_loss.item(),
            'ehp': ehp_loss.item(),
            'tree': tree_loss.item(),
            'gear': gear_loss.item(),
            'gem': gem_loss.item()
        }
        
        return total_loss, loss_dict


class Trainer:
    """Training pipeline for build optimizer"""
    
    def __init__(
        self,
        model: MultiComponentBuilder,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        learning_rate: float = 1e-4,
        checkpoint_dir: str = './checkpoints'
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        
        self.optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )
        
        self.criterion = MultiObjectiveLoss()
        
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.train_history = []
        self.val_history = []
    
    def train_epoch(self) -> Dict[str, float]:
        """Train for one epoch"""
        self.model.train()
        epoch_losses = []
        
        pbar = tqdm(self.train_loader, desc="Training")
        for batch in pbar:
            # Move to device
            tree = batch['tree'].to(self.device)
            gear = batch['gear'].to(self.device)
            gems = batch['gems'].to(self.device)
            skill = batch['skill'].to(self.device)
            targets = batch['targets'].to(self.device)
            
            # Forward pass
            predictions = self.model(tree, gear, gems, skill)
            
            # Prepare target dict with safe normalization
            gear_max = gear.max()
            if gear_max > 0:
                gear_normalized = gear / (gear_max + 1e-8)
            else:
                gear_normalized = gear
            gear_normalized = torch.clamp(gear_normalized, 0, 1)
            
            target_dict = {
                'performance': targets,
                'tree': tree,
                'gear_normalized': gear_normalized,
                'gem_multipliers': torch.ones_like(predictions['gem_multipliers'])
            }
            
            # Compute loss
            loss, loss_dict = self.criterion(predictions, target_dict)
            
            # Check for NaN loss
            if torch.isnan(loss) or torch.isinf(loss):
                print(f"\n⚠️  NaN/Inf loss detected, skipping batch")
                print(f"Tree range: [{tree.min():.3f}, {tree.max():.3f}]")
                print(f"Gear range: [{gear.min():.3f}, {gear.max():.3f}]")
                print(f"Predictions tree range: [{predictions['tree_suggestions'].min():.3f}, {predictions['tree_suggestions'].max():.3f}]")
                continue
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            epoch_losses.append(loss_dict)
            pbar.set_postfix({'loss': loss.item()})
        
        # Average losses
        avg_losses = {
            key: np.mean([l[key] for l in epoch_losses])
            for key in epoch_losses[0].keys()
        }
        
        return avg_losses
    
    def validate(self) -> Dict[str, float]:
        """Validate on validation set"""
        self.model.eval()
        val_losses = []
        
        with torch.no_grad():
            for batch in tqdm(self.val_loader, desc="Validating"):
                tree = batch['tree'].to(self.device)
                gear = batch['gear'].to(self.device)
                gems = batch['gems'].to(self.device)
                skill = batch['skill'].to(self.device)
                targets = batch['targets'].to(self.device)
                
                predictions = self.model(tree, gear, gems, skill)
                
                # Prepare target dict with safe normalization
                gear_max = gear.max()
                if gear_max > 0:
                    gear_normalized = gear / (gear_max + 1e-8)
                else:
                    gear_normalized = gear
                gear_normalized = torch.clamp(gear_normalized, 0, 1)
                
                target_dict = {
                    'performance': targets,
                    'tree': tree,
                    'gear_normalized': gear_normalized,
                    'gem_multipliers': torch.ones_like(predictions['gem_multipliers'])
                }
                
                loss, loss_dict = self.criterion(predictions, target_dict)
                val_losses.append(loss_dict)
        
        avg_losses = {
            key: np.mean([l[key] for l in val_losses])
            for key in val_losses[0].keys()
        }
        
        return avg_losses
    
    def train(self, num_epochs: int = 100, early_stop_patience: int = 10):
        """Full training loop"""
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(num_epochs):
            print(f"\n=== Epoch {epoch+1}/{num_epochs} ===")
            
            # Train
            train_losses = self.train_epoch()
            self.train_history.append(train_losses)
            
            # Validate
            val_losses = self.validate()
            self.val_history.append(val_losses)
            
            # Print metrics
            print(f"Train Loss: {train_losses['total']:.4f}")
            print(f"Val Loss: {val_losses['total']:.4f}")
            print(f"  DPS: {val_losses['dps']:.4f}")
            print(f"  EHP: {val_losses['ehp']:.4f}")
            
            # Learning rate scheduling
            current_val_loss = val_losses['total']
            if not np.isnan(current_val_loss) and not np.isinf(current_val_loss):
                self.scheduler.step(current_val_loss)
            else:
                # Use train loss if val loss is NaN
                current_val_loss = train_losses['total']
                self.scheduler.step(current_val_loss)
            
            # Save checkpoint
            if current_val_loss < best_val_loss:
                best_val_loss = current_val_loss
                patience_counter = 0
                self.save_checkpoint(epoch, current_val_loss, is_best=True)
            else:
                patience_counter += 1
                self.save_checkpoint(epoch, current_val_loss, is_best=False)
            
            # Early stopping
            if patience_counter >= early_stop_patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
        
        # Save training history
        self.save_history()
    
    def save_checkpoint(self, epoch: int, val_loss: float, is_best: bool = False):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'val_loss': val_loss,
        }
        
        # Save regular checkpoint
        path = self.checkpoint_dir / f"checkpoint_epoch_{epoch}.pt"
        torch.save(checkpoint, path)
        
        # Save best model
        if is_best:
            best_path = self.checkpoint_dir / "best_model.pt"
            torch.save(checkpoint, best_path)
            print(f"Saved best model with val_loss: {val_loss:.4f}")
    
    def save_history(self):
        """Save training history"""
        history = {
            'train': self.train_history,
            'val': self.val_history
        }
        
        path = self.checkpoint_dir / "training_history.json"
        with open(path, 'w') as f:
            json.dump(history, f, indent=2)


def create_dataloaders(
    train_file: str,
    val_file: str,
    batch_size: int = 32,
    num_workers: int = 4
) -> Tuple[DataLoader, DataLoader]:
    """Create training and validation dataloaders"""
    
    train_dataset = TrainingDataset(train_file)
    val_dataset = TrainingDataset(val_file)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return train_loader, val_loader


def train_model(
    train_data: List[Tuple],
    val_data: List[Tuple] = None,
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    checkpoint_dir: str = "./checkpoints"
):
    """
    Simplified training function for custom training samples
    
    Args:
        train_data: List of (tree, gear, gems, skill, target) tuples
        val_data: Optional validation data (if None, splits from train_data)
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        checkpoint_dir: Directory to save checkpoints
        
    Returns:
        model, history
    """
    from torch.utils.data import Dataset
    
    class TupleDataset(Dataset):
        """Convert tuple format to dict format expected by Trainer"""
        def __init__(self, data):
            self.data = data
            
        def __len__(self):
            return len(self.data)
            
        def __getitem__(self, idx):
            tree, gear, gems, skill, targets = self.data[idx]
            return {
                'tree': tree,
                'gear': gear,
                'gems': gems,
                'skill': skill,
                'targets': targets
            }
    
    print("Preparing training data...")
    
    # If no val_data, split from train_data
    if val_data is None:
        n_train = int(0.8 * len(train_data))
        val_data = train_data[n_train:]
        train_data = train_data[:n_train]
    
    train_dataset = TupleDataset(train_data)
    val_dataset = TupleDataset(val_data)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    print(f"Training on {len(train_data)} samples, validating on {len(val_data)}")
    
    # Initialize model and trainer
    model = MultiComponentBuilder()
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        learning_rate=learning_rate,
        checkpoint_dir=checkpoint_dir
    )
    
    # Train
    trainer.train(num_epochs=epochs, early_stop_patience=10)
    print("Training complete!")
    
    return model, {'train': trainer.train_history, 'val': trainer.val_history}



if __name__ == "__main__":
    # Example training script
    print("Initializing model...")
    model = MultiComponentBuilder()
    
    print("Loading data...")
    train_loader, val_loader = create_dataloaders(
        train_file="../pob_data/processed/train_dataset.json",
        val_file="../pob_data/processed/val_dataset.json",
        batch_size=32
    )
    
    print("Starting training...")
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        learning_rate=1e-4,
        checkpoint_dir="./checkpoints"
    )
    
    trainer.train(num_epochs=100, early_stop_patience=10)
    print("Training complete!")

