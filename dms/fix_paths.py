import json, glob

for filepath in glob.glob('./output/training/**/*.json', recursive=True):
    with open(filepath) as f:
        data = json.load(f)
    
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        print(f"Skipping {filepath} - wrong structure")
        continue
    
    updated = 0
    for task in data:
        d = task.get('data', {})
        if not isinstance(d, dict):
            continue
        for key, val in d.items():
            if isinstance(val, str) and '/data/local-files/?d=' in val:
                d[key] = val.replace(
                    '/data/local-files/?d=',
                    'http://localhost:9000/label-studio/'
                )
                updated += 1
    
    if updated:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f'Updated {updated} paths in {filepath}')
    else:
        print(f'No changes needed in {filepath}')
