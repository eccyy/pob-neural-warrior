"""Check what the first nodes are in real PoB builds"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

pob_dir = Path('../PathOfBuilding/src/Builds')
files = list(pob_dir.glob('*.xml'))[:10]

print('Checking first 10 builds for starting nodes...\n')

class_starts = {}
for f in files:
    try:
        tree = ET.parse(f)
        spec = tree.find('.//Tree/Spec')
        if spec and spec.get('treeVersion') == '3_27':
            nodes = spec.get('nodes', '').split(',')
            class_id = spec.get('classId')
            if nodes and nodes[0]:
                first_node = nodes[0]
                print(f'{f.name}: classId={class_id}, first_node={first_node}')
                if class_id not in class_starts:
                    class_starts[class_id] = first_node
    except:
        pass

print(f'\nClass starting nodes found:')
for cid, node in class_starts.items():
    print(f'  ClassID {cid}: {node}')
