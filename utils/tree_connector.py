"""
Tree Path Connector
Connects disconnected nodes in PoB passive tree by finding shortest paths
"""
import json
from pathlib import Path
from typing import List, Set, Dict, Optional
from collections import deque


class TreeConnector:
    """Connects scattered passive tree nodes into valid paths"""
    
    # Class starting nodes (from PoB)
    CLASS_STARTS = {
        'Scion': 42178,
        'Marauder': 55488,
        'Ranger': 50450,
        'Witch': 36711,
        'Duelist': 44169,
        'Templar': 61666,
        'Shadow': 26725
    }
    
    def __init__(self, tree_data_path: Optional[str] = None):
        """Initialize with passive tree data"""
        if tree_data_path is None:
            # Try default locations
            possible_paths = [
                Path("./pob_data/tree_data/tree_edges.json"),
                Path("../pob_data/tree_data/tree_edges.json"),
                Path("../../pob_data/tree_data/tree_edges.json")
            ]
            for p in possible_paths:
                if p.exists():
                    tree_data_path = str(p)
                    break
        
        self.edges = {}
        if tree_data_path and Path(tree_data_path).exists():
            with open(tree_data_path) as f:
                self.edges = json.load(f)
        else:
            print("[Warning] Tree edge data not found. Will use direct connections only.")
    
    def find_shortest_path(self, start: int, end: int, allocated: Set[int]) -> List[int]:
        """
        Find shortest path between two nodes using BFS
        Prefer paths through already allocated nodes
        """
        if start == end:
            return [start]
        
        # BFS to find shortest path
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            node, path = queue.popleft()
            
            # Get neighbors (convert to int)
            neighbors = []
            node_str = str(node)
            if node_str in self.edges:
                neighbors = [int(n) for n in self.edges[node_str]]
            
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                
                visited.add(neighbor)
                new_path = path + [neighbor]
                
                if neighbor == end:
                    return new_path
                
                # Prioritize paths through allocated nodes
                if neighbor in allocated:
                    queue.appendleft((neighbor, new_path))
                else:
                    queue.append((neighbor, new_path))
        
        # No path found
        return []
    
    def connect_nodes(self, node_ids: List[int], class_name: str = 'Scion') -> List[int]:
        """
        Connect a list of disconnected nodes into a valid tree
        
        Args:
            node_ids: List of node IDs to connect
            class_name: Character class (determines starting position)
            
        Returns:
            List of all nodes including connecting paths
        """
        if not node_ids:
            return []
        
        # Get starting position
        start_node = self.CLASS_STARTS.get(class_name, self.CLASS_STARTS['Scion'])
        
        # If no edge data, just return the original nodes + start
        if not self.edges:
            return [start_node] + node_ids
        
        # Build connected tree
        connected = {start_node}
        target_nodes = set(node_ids)
        all_nodes = {start_node}
        
        # Sort targets by distance from start (heuristic: node ID proximity)
        sorted_targets = sorted(target_nodes, key=lambda n: abs(n - start_node))
        
        for target in sorted_targets:
            if target in connected:
                continue
            
            # Find closest connected node to this target
            best_path = None
            best_length = float('inf')
            
            for connected_node in list(connected):
                path = self.find_shortest_path(connected_node, target, connected)
                if path and len(path) < best_length:
                    best_path = path
                    best_length = len(path)
            
            if best_path:
                # Add all nodes in path
                for node in best_path:
                    connected.add(node)
                    all_nodes.add(node)
        
        return sorted(all_nodes)
    
    def validate_connected(self, node_ids: List[int], start_node: int) -> bool:
        """Check if nodes form a connected tree from start"""
        if not node_ids or start_node not in node_ids:
            return False
        
        if not self.edges:
            return True  # Can't validate without edge data
        
        # BFS from start to see if we can reach all nodes
        reachable = {start_node}
        queue = deque([start_node])
        node_set = set(node_ids)
        
        while queue:
            node = queue.popleft()
            node_str = str(node)
            
            if node_str in self.edges:
                for neighbor_str in self.edges[node_str]:
                    neighbor = int(neighbor_str)
                    if neighbor in node_set and neighbor not in reachable:
                        reachable.add(neighbor)
                        queue.append(neighbor)
        
        return reachable == node_set


def extract_tree_edges_from_builds(builds_dir: str, output_file: str):
    """
    Extract tree edges by analyzing which nodes appear together in builds
    This is a heuristic approach when we don't have the actual tree JSON
    """
    import xml.etree.ElementTree as ET
    from collections import defaultdict
    
    builds_path = Path(builds_dir)
    edges = defaultdict(set)
    
    print(f"Analyzing builds in {builds_dir} to extract tree edges...")
    
    for xml_file in builds_path.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            spec = tree.getroot().find('.//Spec')
            if spec is not None:
                nodes_str = spec.get('nodes', '')
                if nodes_str:
                    nodes = [int(n) for n in nodes_str.split(',') if n.strip()]
                    
                    # Assume adjacent nodes in allocation order are connected
                    for i in range(len(nodes) - 1):
                        edges[str(nodes[i])].add(str(nodes[i + 1]))
                        edges[str(nodes[i + 1])].add(str(nodes[i]))
        except:
            pass
    
    # Convert sets to lists for JSON
    edges_dict = {k: sorted(list(v)) for k, v in edges.items()}
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(edges_dict, f, indent=2)
    
    print(f"[OK] Extracted {len(edges_dict)} nodes with edge connections")
    print(f"  Saved to: {output_path}")
    
    return edges_dict


if __name__ == "__main__":
    # Generate edge data from builds
    extract_tree_edges_from_builds(
        "../PathOfBuilding/src/Builds",
        "./pob_data/tree_data/tree_edges.json"
    )


def find_most_similar_build(target_nodes: List[int], class_name: str, target_size: int = None) -> Optional[List[int]]:
    """
    Find the most similar working build from training data
    Returns a valid connected tree that's similar to target nodes
    """
    import xml.etree.ElementTree as ET
    
    # Load all builds and find best match
    builds_dir = Path("../PathOfBuilding/src/Builds")
    best_match = None
    best_similarity = 0
    
    target_set = set(target_nodes)
    
    for xml_file in builds_dir.glob("*.xml"):
        if xml_file.name.startswith("~~"):
            continue
        
        try:
            tree = ET.parse(xml_file)
            spec = tree.getroot().find('.//Spec')
            if spec is not None:
                nodes_str = spec.get('nodes', '')
                if nodes_str:
                    nodes = [int(n) for n in nodes_str.split(',') if n.strip()]
                    
                    # Calculate similarity (Jaccard index)
                    build_set = set(nodes)
                    intersection = len(target_set & build_set)
                    union = len(target_set | build_set)
                    similarity = intersection / union if union > 0 else 0
                    
                    # Prefer builds with similar size
                    if target_size:
                        size_diff = abs(len(nodes) - target_size) / max(len(nodes), target_size)
                        similarity *= (1 - size_diff * 0.5)  # Penalize size difference
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = nodes
        except:
            pass
    
    if best_match:
        print(f"[Similarity] Found build with {best_similarity:.1%} match")
    
    return best_match
