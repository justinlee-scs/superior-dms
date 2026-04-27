import json, glob, os

all_tasks = []

for batch_dir in glob.glob('./output/training/batches/*/'):
    ocr_path = os.path.join(batch_dir, 'ocr_tasks.json')
    text_path = os.path.join(batch_dir, 'text_tasks.json')
    
    if not os.path.exists(ocr_path) or not os.path.exists(text_path):
        print(f'Skipping {batch_dir} - missing files')
        continue
    
    with open(ocr_path) as f:
        ocr_tasks = json.load(f)
    with open(text_path) as f:
        text_tasks = json.load(f)
    
    # Match by filename+page
    text_lookup = {}
    for t in text_tasks:
        key = (t['data'].get('filename'), t['data'].get('page'))
        text_lookup[key] = t['data'].get('ocr_text', '')
    
    for task in ocr_tasks:
        key = (task['data'].get('filename'), task['data'].get('page'))
        combined = {
            'data': {
                'image': task['data']['image'],
                'ocr_text': text_lookup.get(key, ''),
                'filename': task['data'].get('filename'),
                'page': task['data'].get('page')
            }
        }
        all_tasks.append(combined)
    
    print(f'Merged {len(ocr_tasks)} tasks from {batch_dir}')

with open('./output/all_combined_tasks.json', 'w') as f:
    json.dump(all_tasks, f, indent=2)

print(f'\nTotal: {len(all_tasks)} combined tasks')
print('Saved to ./output/all_combined_tasks.json')
