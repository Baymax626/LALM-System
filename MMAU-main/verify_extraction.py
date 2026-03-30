
import json
import re

# Load the file
with open(r'd:\Suda\毕设 - 副本\web_system\MMAU-main\mmau-test-mini-results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Process the first 10 items
results = []
for i in range(10):
    item = data[i]
    model_output = item.get('model_output', '')
    
    # Extract answer using the logic from compute_singlechoice_acc.py
    # Try to extract from <answer> tags first (though current file doesn't use them, good to check)
    content_match = re.search(r'<answer>(.*?)</answer>', model_output.replace('\n', ''))
    extracted_answer = content_match.group(1).strip() if content_match else model_output.strip()
    
    # Apply MMAU specific processing (replace newlines with space)
    processed_answer = extracted_answer.replace('\n', ' ')
    
    results.append({
        "id": item.get('id'),
        "original_output": model_output,
        "extracted_answer": processed_answer,
        "correct_answer": item.get('answer'),
        "match": "CORRECT" if processed_answer.endswith(item.get('answer')) or f"{item.get('answer')}" in processed_answer[-20:] or f"A) {item.get('answer')}" in processed_answer or f"B) {item.get('answer')}" in processed_answer else "INCORRECT" 
    })

# Print results
print(json.dumps(results, indent=2, ensure_ascii=False))
