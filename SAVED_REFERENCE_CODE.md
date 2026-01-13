# Saved Reference Code

This commit includes reference code from the Path of Building implementation:

## Files Saved

1. **integration/reference_greedy_optimizer.lua** (2902 lines)
   - Complete TreeTab.lua with working greedy optimizer
   - CollectBestNodes() algorithm achieving 50% DPS improvements
   - GPU/Python integration points for future ML optimizer
   - Node power calculation and path finding logic
   - UI controls for optimizer interface

2. **utils/features.py** (242 lines)
   - BuildFeatureExtractor class
   - Tree encoding (1500-dim binary vector)
   - Gear encoding (aggregated stats)
   - Node ID mapping
   - Feature extraction utilities

3. **LEGACY_POB_INTEGRATION.md**
   - Documentation on neural network optimizer integration
   - How the Lua code calls Python optimizer
   - Integration points and data structures

## Why These Were Saved

### Greedy Optimizer (reference_greedy_optimizer.lua)
- **Production-ready**: Achieved 50% DPS improvement in testing
- **Reference implementation**: Shows how to interact with PoB's internal APIs
- **Path finding**: Contains working A* path calculation
- **Node filtering**: Shows which nodes to exclude (ascendancy, granted passives, etc.)
- **Integration points**: GPU/Python bridge examples

**Key Functions**:
- `CollectBestNodes()` - Main greedy selection algorithm (lines 907-1252)
- `ApplyOptimizerSuggestions()` - Apply node allocations
- `GenerateBestNodesPopup()` - UI for optimizer

### Feature Extraction (features.py)
- Converts PoB builds to ML feature vectors
- Used by neural network training pipeline
- Handles node encoding, gear aggregation, gem parsing

### Integration Documentation
- How Lua and Python communicate
- Data structures passed between systems
- API contracts for the optimizer

## Usage

These files serve as **reference only** - they document:
1. How the greedy optimizer works (for comparison)
2. How to integrate with Path of Building Lua code
3. Feature extraction patterns

The neural network implementation will use similar patterns but with:
- Multi-component architecture (tree + gear + gems)
- Multi-objective optimization (offense + defense)
- Supervised learning instead of greedy search

## Path of Building Main Repo

The original Path of Building repo can now be deleted. All relevant code for neural network development has been extracted and saved here.
