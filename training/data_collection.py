"""
Data Collection Pipeline
Scrapes builds from poe.ninja and processes them for training
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from tqdm import tqdm
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.skill_database import get_all_skills, get_skill, calculate_base_dps


class PoeNinjaScraper:
    """Scrape top builds from poe.ninja ladder"""
    
    BASE_URL = "https://poe.ninja/api/data/poe1"
    
    def __init__(self, output_dir: str = "../pob_data/poe_ninja"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_leagues(self) -> List[str]:
        """Get list of active leagues"""
        try:
            response = requests.get(f"{self.BASE_URL}/getindexstate", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [league['name'] for league in data.get('economyLeagues', [])]
        except Exception as e:
            print(f"Error fetching leagues: {e}")
            return []
    
    def scrape_ladder(
        self,
        league: str,
        limit: int = 10000,
        class_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Scrape ladder builds from poe.ninja
        
        NOTE: poe.ninja API is currently unavailable.
        This will generate mock data for testing purposes.
        
        Args:
            league: League name (e.g., "Keepers")
            limit: Max number of builds to scrape
            class_name: Filter by class (optional)
            
        Returns:
            List of build dictionaries
        """
        print(f"⚠️  WARNING: poe.ninja API endpoint not available")
        print(f"Generating {limit} mock builds for testing...")
        
        # Generate mock data for testing
        return self._generate_mock_builds(limit, class_name)
    
    def _generate_mock_builds(self, count: int, class_filter: Optional[str] = None) -> List[Dict]:
        """Generate mock build data for testing"""
        import random
        
        classes = ['Marauder', 'Ranger', 'Witch', 'Duelist', 'Templar', 'Shadow', 'Scion']
        skills = get_all_skills()  # Get from skill database
        
        builds = []
        for i in range(count):
            char_class = class_filter if class_filter else random.choice(classes)
            skill_name = random.choice(skills)
            skill = get_skill(skill_name)
            
            # Generate realistic DPS based on skill type
            # Base DPS * (1 + increased%) * more multipliers * added damage
            base_dps = calculate_base_dps(skill, added_flat_damage=random.randint(50, 500))
            increased_multiplier = 1.0 + random.uniform(3.0, 8.0)  # 300-800% increased
            more_multipliers = random.uniform(1.5, 4.0)  # Support gems
            final_dps = base_dps * increased_multiplier * more_multipliers
            
            builds.append({
                'account': f'TestAccount{i}',
                'character': f'TestChar{i}',
                'class': char_class,
                'level': random.randint(90, 100),
                'main_skill': skill_name,
                'life': random.randint(3000, 7000),
                'energy_shield': random.randint(0, 3000),
                'depth_solo': random.randint(0, 600),
                'dps': max(20000, int(final_dps)),  # Minimum 20k DPS
                'build_url': None,
            })
        
        print(f"✓ Generated {len(builds)} mock builds")
        return builds
    
    def _parse_ladder_entry(self, entry: Dict) -> Optional[Dict]:
        """Parse a single ladder entry"""
        try:
            return {
                'account': entry.get('account', {}).get('name'),
                'character': entry.get('character', {}).get('name'),
                'class': entry.get('character', {}).get('class'),
                'level': entry.get('character', {}).get('level'),
                'main_skill': entry.get('mainSkill'),
                'life': entry.get('life'),
                'energy_shield': entry.get('energyShield'),
                'depth_solo': entry.get('depthSolo', 0),
                'dps': entry.get('dps', 0),
                'build_url': entry.get('pobUrl'),  # Some entries have this
            }
        except Exception as e:
            return None
    
    def save_builds(self, builds: List[Dict], league: str):
        """Save builds to JSON file"""
        league_dir = self.output_dir / league.replace(' ', '_')
        league_dir.mkdir(exist_ok=True)
        
        filename = league_dir / f"ladder_{len(builds)}_builds.json"
        with open(filename, 'w') as f:
            json.dump(builds, f, indent=2)
        
        print(f"Saved {len(builds)} builds to {filename}")


class BuildDataProcessor:
    """Process raw build data into training format"""
    
    def __init__(self):
        self.feature_extractor = None  # Will use features.py
    
    def process_builds(
        self,
        builds: List[Dict],
        validate: bool = True
    ) -> List[Dict]:
        """
        Convert raw builds into training examples
        
        Args:
            builds: List of raw build dicts
            validate: Whether to validate with PoB
            
        Returns:
            List of processed training examples
        """
        processed = []
        
        for build in tqdm(builds, desc="Processing builds"):
            try:
                example = self._process_single_build(build, validate)
                if example:
                    processed.append(example)
            except Exception as e:
                print(f"Error processing build: {e}")
        
        return processed
    
    def _process_single_build(
        self,
        build: Dict,
        validate: bool
    ) -> Optional[Dict]:
        """Process a single build"""
        
        # Extract features
        # This would integrate with the existing features.py
        
        # Encode skill as one-hot vector
        skill_name = build.get('main_skill', 'Lightning Strike')
        all_skills = get_all_skills()
        skill_vector = np.zeros(len(all_skills))
        if skill_name in all_skills:
            skill_vector[all_skills.index(skill_name)] = 1.0
        
        # For now, create a placeholder structure
        return {
            'metadata': {
                'character': build.get('character'),
                'class': build.get('class'),
                'level': build.get('level'),
                'main_skill': skill_name,
            },
            'features': {
                'tree': np.zeros(1500),  # Placeholder
                'gear': np.zeros(500),   # Placeholder
                'gems': np.zeros(100),   # Placeholder
                'skill': skill_vector,   # One-hot encoded skill
            },
            'targets': {
                'dps': build.get('dps', 0) / 100000.0,  # Normalize: 100k DPS = 1.0
                'life': build.get('life', 0) / 5000.0,   # Normalize: 5k life = 1.0
                'es': build.get('energy_shield', 0) / 5000.0,  # Normalize: 5k ES = 1.0
            }
        }
    
    def save_dataset(
        self,
        processed_builds: List[Dict],
        output_file: str
    ):
        """Save processed dataset"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert numpy arrays to lists for JSON serialization
        serializable_builds = []
        for build in processed_builds:
            serializable_build = {
                'metadata': build['metadata'],
                'features': {
                    'tree': build['features']['tree'].tolist(),
                    'gear': build['features']['gear'].tolist(),
                    'gems': build['features']['gems'].tolist(),
                    'skill': build['features']['skill'].tolist(),
                },
                'targets': build['targets']
            }
            serializable_builds.append(serializable_build)
        
        with open(output_path, 'w') as f:
            json.dump(serializable_builds, f, indent=2)
        
        print(f"Saved {len(processed_builds)} processed builds to {output_path}")


class TrainingDataset:
    """PyTorch Dataset for build optimization"""
    
    def __init__(self, data_file: str):
        with open(data_file, 'r') as f:
            self.data = json.load(f)
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        example = self.data[idx]
        
        # Convert to tensors
        tree = np.array(example['features']['tree'], dtype=np.float32)
        gear = np.array(example['features']['gear'], dtype=np.float32)
        gems = np.array(example['features']['gems'], dtype=np.float32)
        skill = np.array(example['features']['skill'], dtype=np.float32)
        
        dps = example['targets']['dps']
        life = example['targets']['life']
        es = example['targets']['es']
        
        # Compute combined score
        ehp = life + es
        score = 0.7 * dps + 0.3 * ehp
        
        return {
            'tree': tree,
            'gear': gear,
            'gems': gems,
            'skill': skill,
            'targets': np.array([dps, ehp, score], dtype=np.float32)
        }


if __name__ == "__main__":
    # Example usage
    scraper = PoeNinjaScraper()
    
    # Get current leagues
    leagues = scraper.get_leagues()
    print(f"Active leagues: {leagues}")
    
    if leagues:
        # Scrape first league
        builds = scraper.scrape_ladder(leagues[0], limit=100)
        scraper.save_builds(builds, leagues[0])
        
        # Process builds
        processor = BuildDataProcessor()
        processed = processor.process_builds(builds, validate=False)
        processor.save_dataset(
            processed,
            f"../pob_data/processed/{leagues[0]}_dataset.json"
        )
