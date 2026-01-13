"""Check tree versions in PoB builds"""
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

builds_dir = Path('../PathOfBuilding/src/Builds')
versions = []

for xml_file in builds_dir.glob('*.xml'):
    if xml_file.name.startswith('~~'):
        continue
    try:
        tree = ET.parse(xml_file)
        spec = tree.getroot().find('.//Spec')
        if spec is not None:
            ver = spec.get('treeVersion', 'unknown')
            versions.append((ver, xml_file.name))
    except:
        pass

print(f"Analyzed {len(versions)} builds\n")
print("Tree versions:")
version_counts = Counter([v[0] for v in versions])
for ver, count in version_counts.most_common():
    print(f"  {ver}: {count} builds")

# Show 3.27 builds
v327_builds = [name for ver, name in versions if ver == '3_27']
print(f"\n{len(v327_builds)} builds with treeVersion='3_27'")
if len(v327_builds) < 20:
    print("Sample files:", v327_builds[:10])
