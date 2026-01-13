"""
Genetic Algorithm Build Optimizer
Uses trained neural network as fast fitness function
Searches massive build space efficiently
"""

import torch
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import random
from copy import deepcopy
from tqdm import tqdm

import sys
sys.path.append('..')
from models.multi_component import MultiComponentBuilder


@dataclass
class Build:
    """Represents a complete PoE build"""
    tree: np.ndarray  # Binary vector of allocated nodes
    gear: np.ndarray  # Gear stat vector
    gems: np.ndarray  # Gem setup vector
    skill: np.ndarray  # One-hot encoded skill
    fitness: float = 0.0
    validated_performance: Optional[Dict] = None


class GeneticOptimizer:
    """
    Genetic algorithm that uses neural network as surrogate model
    Much faster than evaluating every build in PoB
    """
    
    def __init__(
        self,
        model: MultiComponentBuilder,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        population_size: int = 100,
        elite_size: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7
    ):
        self.model = model.to(device)
        self.model.eval()
        self.device = device
        
        self.population_size = population_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        
        # Tree constraints
        self.max_tree_points = 123  # Level 100 + all quests
        self.tree_dim = 1500
        self.gear_dim = 500
        self.gem_dim = 100
    
    def initialize_population(
        self,
        base_build: Optional[Build] = None
    ) -> List[Build]:
        """
        Initialize population
        If base_build provided, create variations around it
        Otherwise, create random builds
        """
        population = []
        
        if base_build:
            # Create variations of base build
            population.append(deepcopy(base_build))
            
            for _ in range(self.population_size - 1):
                variant = self._create_variant(base_build)
                population.append(variant)
        else:
            # Random initialization
            for _ in range(self.population_size):
                build = self._create_random_build()
                population.append(build)
        
        # Evaluate initial fitness
        self._evaluate_population(population)
        
        return population
    
    def _create_random_build(self) -> Build:
        """Create a random valid build"""
        # Allocate random nodes (respecting point budget)
        tree = np.zeros(self.tree_dim)
        num_points = random.randint(80, self.max_tree_points)
        allocated_nodes = random.sample(range(self.tree_dim), num_points)
        tree[allocated_nodes] = 1
        
        # Random gear stats
        gear = np.random.rand(self.gear_dim)
        
        # Random gem setup
        gems = np.random.rand(self.gem_dim)
        
        # Default skill: Lightning Strike (index 0)
        skill = np.zeros(8)  # 8 skills in database
        skill[0] = 1.0
        
        return Build(tree=tree, gear=gear, gems=gems, skill=skill)
    
    def _create_variant(self, base: Build) -> Build:
        """Create a variant of a build"""
        variant = deepcopy(base)
        
        # Mutate tree: swap some nodes
        num_swaps = random.randint(1, 10)
        allocated = np.where(variant.tree == 1)[0]
        unallocated = np.where(variant.tree == 0)[0]
        
        for _ in range(min(num_swaps, len(allocated))):
            if len(unallocated) > 0:
                remove = random.choice(allocated)
                add = random.choice(unallocated)
                variant.tree[remove] = 0
                variant.tree[add] = 1
        
        # Mutate gear: small random changes
        gear_noise = np.random.randn(self.gear_dim) * 0.1
        variant.gear = np.clip(variant.gear + gear_noise, 0, 1)
        
        # Mutate gems: small random changes
        gem_noise = np.random.randn(self.gem_dim) * 0.1
        variant.gems = np.clip(variant.gems + gem_noise, 0, 1)
        
        return variant
    
    def _evaluate_population(self, population: List[Build]):
        """Evaluate fitness for entire population using NN"""
        # Batch evaluation for speed
        trees = np.stack([b.tree for b in population])
        gears = np.stack([b.gear for b in population])
        gems_list = np.stack([b.gems for b in population])
        skills = np.stack([b.skill for b in population])
        
        # Convert to tensors
        trees_t = torch.from_numpy(trees).float().to(self.device)
        gears_t = torch.from_numpy(gears).float().to(self.device)
        gems_t = torch.from_numpy(gems_list).float().to(self.device)
        skills_t = torch.from_numpy(skills).float().to(self.device)
        
        with torch.no_grad():
            performance = self.model.predict_performance(trees_t, gears_t, gems_t, skills_t)
            # Fitness = 0.7 * DPS + 0.3 * EHP
            fitness = 0.7 * performance[:, 0] + 0.3 * performance[:, 1]
        
        # Update fitness
        fitness_np = fitness.cpu().numpy()
        for i, build in enumerate(population):
            build.fitness = fitness_np[i]
    
    def selection(self, population: List[Build]) -> List[Build]:
        """
        Tournament selection
        Select parents for next generation
        """
        selected = []
        
        # Keep elite builds
        population_sorted = sorted(population, key=lambda b: b.fitness, reverse=True)
        selected.extend(population_sorted[:self.elite_size])
        
        # Tournament selection for rest
        tournament_size = 5
        while len(selected) < self.population_size:
            tournament = random.sample(population, tournament_size)
            winner = max(tournament, key=lambda b: b.fitness)
            selected.append(deepcopy(winner))
        
        return selected
    
    def crossover(self, parent1: Build, parent2: Build) -> Tuple[Build, Build]:
        """
        Crossover two builds
        Mix their tree, gear, and gem components
        """
        if random.random() > self.crossover_rate:
            return deepcopy(parent1), deepcopy(parent2)
        
        child1 = Build(
            tree=np.zeros(self.tree_dim),
            gear=np.zeros(self.gear_dim),
            gems=np.zeros(self.gem_dim),
            skill=parent1.skill.copy()  # Keep parent's skill
        )
        child2 = Build(
            tree=np.zeros(self.tree_dim),
            gear=np.zeros(self.gear_dim),
            gems=np.zeros(self.gem_dim),
            skill=parent2.skill.copy()  # Keep parent's skill
        )
        
        # Tree crossover: take nodes from both parents
        crossover_point = random.randint(0, self.tree_dim)
        child1.tree[:crossover_point] = parent1.tree[:crossover_point]
        child1.tree[crossover_point:] = parent2.tree[crossover_point:]
        child2.tree[:crossover_point] = parent2.tree[:crossover_point]
        child2.tree[crossover_point:] = parent1.tree[crossover_point:]
        
        # Enforce point budget
        child1.tree = self._enforce_point_budget(child1.tree)
        child2.tree = self._enforce_point_budget(child2.tree)
        
        # Gear crossover: average stats
        alpha = random.random()
        child1.gear = alpha * parent1.gear + (1 - alpha) * parent2.gear
        child2.gear = (1 - alpha) * parent1.gear + alpha * parent2.gear
        
        # Gem crossover: similar approach
        child1.gems = alpha * parent1.gems + (1 - alpha) * parent2.gems
        child2.gems = (1 - alpha) * parent1.gems + alpha * parent2.gems
        
        return child1, child2
    
    def mutate(self, build: Build) -> Build:
        """Mutate a build"""
        if random.random() > self.mutation_rate:
            return build
        
        # Tree mutation: flip some nodes
        num_flips = random.randint(1, 5)
        for _ in range(num_flips):
            idx = random.randint(0, self.tree_dim - 1)
            build.tree[idx] = 1 - build.tree[idx]
        
        build.tree = self._enforce_point_budget(build.tree)
        
        # Gear mutation: add noise
        mask = np.random.rand(self.gear_dim) < self.mutation_rate
        noise = np.random.randn(self.gear_dim) * 0.2
        build.gear = np.clip(build.gear + mask * noise, 0, 1)
        
        # Gem mutation
        mask = np.random.rand(self.gem_dim) < self.mutation_rate
        noise = np.random.randn(self.gem_dim) * 0.2
        build.gems = np.clip(build.gems + mask * noise, 0, 1)
        
        return build
    
    def _enforce_point_budget(self, tree: np.ndarray) -> np.ndarray:
        """Ensure tree doesn't exceed point budget"""
        allocated = np.where(tree == 1)[0]
        
        if len(allocated) > self.max_tree_points:
            # Remove random nodes until within budget
            to_remove = random.sample(
                list(allocated),
                len(allocated) - self.max_tree_points
            )
            tree[to_remove] = 0
        
        return tree
    
    def optimize(
        self,
        base_build: Optional[Build] = None,
        num_generations: int = 100,
        convergence_threshold: float = 1e-4
    ) -> Tuple[Build, List[float]]:
        """
        Run genetic algorithm optimization
        
        Args:
            base_build: Starting build (if None, random initialization)
            num_generations: Max generations to run
            convergence_threshold: Stop if improvement < threshold
            
        Returns:
            best_build: Optimized build
            history: Fitness history over generations
        """
        print("Initializing population...")
        population = self.initialize_population(base_build)
        
        history = []
        best_fitness = max(b.fitness for b in population)
        history.append(best_fitness)
        
        print(f"Initial best fitness: {best_fitness:.2f}")
        
        for generation in tqdm(range(num_generations), desc="Optimizing"):
            # Selection
            parents = self.selection(population)
            
            # Create next generation
            next_generation = parents[:self.elite_size]  # Keep elites
            
            # Crossover and mutation
            while len(next_generation) < self.population_size:
                p1, p2 = random.sample(parents, 2)
                c1, c2 = self.crossover(p1, p2)
                c1 = self.mutate(c1)
                c2 = self.mutate(c2)
                next_generation.extend([c1, c2])
            
            next_generation = next_generation[:self.population_size]
            
            # Evaluate
            self._evaluate_population(next_generation)
            
            # Track progress
            current_best = max(b.fitness for b in next_generation)
            history.append(current_best)
            
            if generation % 10 == 0:
                print(f"Generation {generation}: Best fitness = {current_best:.2f}")
            
            # Check convergence
            if abs(current_best - best_fitness) < convergence_threshold:
                print(f"Converged at generation {generation}")
                break
            
            best_fitness = current_best
            population = next_generation
        
        # Return best build
        best_build = max(population, key=lambda b: b.fitness)
        return best_build, history


if __name__ == "__main__":
    # Example usage
    print("Loading model...")
    model = MultiComponentBuilder()
    model.load_state_dict(torch.load("../checkpoints/best_model.pt")['model_state_dict'])
    
    print("Initializing optimizer...")
    optimizer = GeneticOptimizer(
        model=model,
        population_size=100,
        elite_size=10,
        mutation_rate=0.1
    )
    
    print("Running optimization...")
    best_build, history = optimizer.optimize(
        num_generations=100
    )
    
    print(f"\nOptimization complete!")
    print(f"Best fitness: {best_build.fitness:.2f}")
    print(f"Allocated nodes: {int(best_build.tree.sum())}")
