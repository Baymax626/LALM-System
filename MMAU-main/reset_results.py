
import json
import os

RESULTS_FILE = r"d:\Suda\毕设 - 副本\web_system\MMAU-main\mmau-test-mini-results.json"
INPUT_FILE = r"d:\Suda\毕设 - 副本\web_system\MMAU-main\mmau-test-mini.json"

if os.path.exists(RESULTS_FILE):
    print(f"Loading results from {RESULTS_FILE}...")
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Resetting 'model_output' for all {len(data)} samples...")
    for item in data:
        if 'model_output' in item:
            # item['model_output'] = "" # Option A: Clear content but keep key
            del item['model_output']    # Option B: Remove key entirely (cleaner for re-run)
            
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print("Done! All model outputs have been cleared.")
else:
    print(f"Results file not found. Nothing to reset.")
