"""Check PoB tree structure."""
import sys
sys.path.insert(0, '../PathOfBuilding/src')

from lupa import LuaRuntime

# Load PoB tree data
lua = LuaRuntime(unpack_returned_tuples=True)
with open('../PathOfBuilding/src/TreeData/3_27/tree.lua', 'r', encoding='utf-8') as f:
    tree_lua = f.read()

# Execute
lua.execute(tree_lua)

# Check what's available
print("Available globals:", list(lua.globals().keys()))

# Get tree
tree = lua.globals().tree
print(f"\nTree type: {type(tree)}")
if tree:
    print(f"Tree keys: {list(tree.keys())}")
