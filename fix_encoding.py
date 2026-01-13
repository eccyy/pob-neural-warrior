import re

with open(r'c:\projects\pob\pob_neural_network\docs\VARIABLE_ARCHITECTURE.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all broken emoji encodings - remove them entirely
content = re.sub(r'[ðŸ][^\s]*', '', content)  # Remove all broken emoji sequences
content = re.sub(r'â[^\s]*', '', content)   # Remove broken special chars

# Clean up double spaces from removed emojis
content = re.sub(r'  +', ' ', content)
content = re.sub(r'# +', '## ', content)  # Fix headers

# Write back
with open(r'c:\projects\pob\pob_neural_network\docs\VARIABLE_ARCHITECTURE.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed encoding issues in VARIABLE_ARCHITECTURE.md')
