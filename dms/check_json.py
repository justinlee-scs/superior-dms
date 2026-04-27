import json, glob

for filepath in glob.glob('./output/training/**/*.json', recursive=True):
    with open(filepath) as f:
        data = json.load(f)
    print(f"\n=== {filepath} ===")
    print(f"Type: {type(data)}")
    if isinstance(data, list):
        print(f"First item type: {type(data[0])}")
        print(f"First item preview: {str(data[0])[:200]}")
    elif isinstance(data, dict):
        print(f"Keys: {list(data.keys())[:5]}")
