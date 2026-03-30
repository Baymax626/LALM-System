import argparse
import json
import pickle
from tqdm import tqdm
from pathlib import Path
import re

def string_match(answer, prediction, choices):
    """
    Improved string matching for Chain-of-Thought style outputs.
    """
    if not isinstance(prediction, str):
        return False
        
    # Normalize
    prediction = prediction.lower()
    answer = answer.lower()
    
    # Strategy 1: Look for explicit option indicators (A), A., A) near the end
    # Map labels to choices
    labels = ['a', 'b', 'c', 'd', 'e', 'f']
    options_map = {}
    for i, choice in enumerate(choices):
        if i < len(labels):
            options_map[labels[i]] = choice.lower()
            
    # Regex to find option indicators. 
    # Examples: " A)", " A.", "(A)", "Option A"
    # We look for the LAST occurrence to handle CoT where options might be discussed earlier.
    pattern = r'(?:^|\s|\()([a-d])(?:\)|\.)'
    
    matches = list(re.finditer(pattern, prediction))
    
    if matches:
        # Get the last match
        last_match = matches[-1]
        detected_label = last_match.group(1)
        
        # Verify if this label corresponds to the answer
        if detected_label in options_map:
            predicted_choice = options_map[detected_label]
            
            # Compare predicted_choice with answer
            # 1. Exact match (normalized)
            if predicted_choice == answer:
                return True
            
            # 2. Token set match (handles minor punctuation/spacing differences)
            def get_tokens(s): return set(re.findall(r'\b\w+\b', s))
            ans_tokens = get_tokens(answer)
            pred_tokens = get_tokens(predicted_choice)
            
            if ans_tokens and ans_tokens == pred_tokens:
                return True
                
    # Strategy 2: Check if the answer string is present at the very end of the prediction
    # We look at the last 100 characters to minimize false positives from the reasoning trace
    snippet = prediction[-100:]
    if answer in snippet:
        return True
        
    return False

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process benchmark JSON and calculate accuracy.")
    parser.add_argument('--input', type=str, required=True, help='Path to input JSON file to be evaluated')
    
    args = parser.parse_args()  
    
    # Added encoding='utf-8' for Windows compatibility
    with open(args.input, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    corr, total = 0, 0

    # Track metrics for different categories:
    task_metrics = {'sound': [0, 0], 'music': [0, 0], 'speech': [0, 0]}
    diff_metrics = {'easy': [0, 0], 'hard': [0, 0], 'medium': [0, 0]}
    
    # Here is the new dict for sub-category metrics
    subcat_metrics = {}

    output_key = 'model_output' # The key that contains model output
    no_pred_count = 0
    matched_outputs = []
    new_data = []

    for idx, sample in enumerate(tqdm(input_data)):
        
        # If there's no model output key, skip
        if output_key not in sample:
            no_pred_count += 1 # Count missing predictions even if we skip
            continue
        
        # Redundant check removed, handled above
        _prediction = sample[output_key]

        _answer = sample['answer']
        task = sample['task']
        difficulty = sample['difficulty']
        choices = sample['choices']
        
        # Get the sub-category
        subcat = sample.get('sub-category', None)
        if subcat is not None:
            # If we haven't seen this sub-category before, initialize
            if subcat not in subcat_metrics:
                subcat_metrics[subcat] = [0, 0]

        match_result = string_match(_answer, _prediction, choices)

        if match_result:
            task_metrics[task][0] += 1
            diff_metrics[difficulty][0] += 1
            if subcat is not None:
                subcat_metrics[subcat][0] += 1
            matched_outputs.append([_answer, _prediction])
            corr += 1
            sample['match'] = 1
        else:
            sample['match'] = 0

        total += 1
        new_data.append(sample)
        task_metrics[task][1] += 1
        diff_metrics[difficulty][1] += 1
        if subcat is not None:
            subcat_metrics[subcat][1] += 1


    # Print results:
    print("*"*30)
    print("Task-wise Accuracy:")
    for task in task_metrics:
        n_correct, n_total = task_metrics[task]
        acc = (n_correct / n_total) * 100 if n_total > 0 else 0
        print(f"{task} : {acc:.2f}% over {n_total} samples")
    
    print("*"*30)
    print("Difficulty-wise Accuracy:")
    for diff in diff_metrics:
        n_correct, n_total = diff_metrics[diff]
        acc = (n_correct / n_total) * 100 if n_total > 0 else 0
        print(f"{diff} : {acc:.2f}% over {n_total} samples")
    
    print("*"*30)
    print("Sub-category-wise Accuracy:")
    for subcat in subcat_metrics:
        n_correct, n_total = subcat_metrics[subcat]
        acc = (n_correct / n_total) * 100 if n_total > 0 else 0
        print(f"{subcat} : {acc:.2f}% over {n_total} samples")

    print("*"*30)
    print(f"Total Accuracy: {(corr/total) * 100:.2f}% over {total} samples")
    print("*"*30)
    print(f"No prediction count: {no_pred_count}")
