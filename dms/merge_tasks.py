import json, glob

all_tasks = []
for filepath in glob.glob('./output/training/batches/**/ocr_tasks.json', recursive=True):
    with open(filepath) as f:
        data = json.load(f)
    all_tasks.extend(data)
    print(f'Added {len(data)} tasks from {filepath}')

with open('./output/all_ocr_tasks.json', 'w') as f:
    json.dump(all_tasks, f, indent=2)

print(f'\nTotal tasks: {len(all_tasks)}')
print('Saved to ./output/all_ocr_tasks.json')
