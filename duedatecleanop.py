python3 -c "
import json
with open('data/stories.json', 'r') as f:
    data = json.load(f)
for key, story in data.get('stories', {}).items():
    if 'published_due_date' in story:
        del story['published_due_date']
with open('data/stories.json', 'w') as f:
    json.dump(data, f, indent=2)
print('✓ Removed published_due_date fields')
"