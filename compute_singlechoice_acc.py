import json
import argparse
import tqdm
# from whisper.normalizers import EnglishTextNormalizer
import re

def read_hyps(hyps_file, benchmarks, lang="en"):
    if lang == "en":
        # normalizer = EnglishTextNormalizer()
        pass
    else:
        raise NotImplementedError(f"Language {lang} is not supported currently.")
    hyps = []
    if benchmarks == "mmau":
        # MMAU files are typically a JSON array, not JSON Lines
        try:
            with open(hyps_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for dic in tqdm.tqdm(data, desc="Reading hypotheses"):
                if "response" in dic:
                    content = dic["response"]
                elif "model_output" in dic:
                    content = dic["model_output"]
                else:
                    # Handle cases where neither key is present (e.g. missing prediction)
                    content = ""
                    
                # Try to extract from <answer> tags first
                content_match = re.search(r'<answer>(.*?)</answer>', content.replace('\n', ''))
                student_answer = content_match.group(1).strip() if content_match else content.strip()
                
                # MMAU specific processing
                # Don't strip explicit option indicators here to allow string_match to handle them
                hyps.append(student_answer.replace('\n', ' '))
                
        except json.JSONDecodeError:
            # Fallback to line-by-line if it's actually JSONL
            with open(hyps_file, 'r', encoding='utf-8') as f:
                for line in tqdm.tqdm(f, desc="Reading hypotheses"):
                    dic = json.loads(line)
                    if "response" in dic:
                        content = dic["response"]
                    elif "model_output" in dic:
                        content = dic["model_output"]
                    else:
                        content = ""
                        
                    content_match = re.search(r'<answer>(.*?)</answer>', content.replace('\n', ''))
                    student_answer = content_match.group(1).strip() if content_match else content.strip()
                    hyps.append(student_answer.replace('\n', ' '))
                    
    else:
        # Original logic for other benchmarks (JSON Lines assumed)
        with open(hyps_file, 'r', encoding='utf-8') as f:
            for line in tqdm.tqdm(f, desc="Reading hypotheses"):
                dic = json.loads(line)
                if "response" in dic:
                    content = dic["response"]
                elif "model_output" in dic:
                    content = dic["model_output"]
                else:
                    # Handle cases where neither key is present (e.g. missing prediction)
                    content = ""
                
                content_match = re.search(r'<answer>(.*?)</answer>', content.replace('\n', ''))
                student_answer = content_match.group(1).strip() if content_match else content.strip()
                
                if benchmarks == 'airbench':
                     # student_answer = normalizer(student_answer)
                     hyps.append(student_answer)
                elif benchmarks == 'mmar':
                    hyps.append(student_answer.replace('A)', '').replace('B)', '').replace('C)', '').replace('D)', '').replace('\n', ''))
    
    return hyps

def read_refs(refs_file, benchmarks, lang="en"):
    if lang == "en":
        # normalizer = EnglishTextNormalizer()
        pass
    else:
        raise NotImplementedError(f"Language {lang} is not supported currently.")
    refs = []
    if benchmarks == "mmau":
        # MMAU files are typically a JSON array
        try:
            with open(refs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for dic in tqdm.tqdm(data, desc="Reading references"):
                if "solution" in dic:
                    content = dic["solution"]
                elif "answer" in dic:
                    content = dic["answer"]
                else:
                    content = ""
                
                # Try to extract from <answer> tags
                content_match = re.search(r'<answer>(.*?)</answer>', content)
                ground_truth = content_match.group(1).strip() if content_match else content.strip()
                
                difficulty = dic.get("difficulty", None)
                task = dic.get("task", None)
                choices = dic.get("choices", None)
                
                # Don't strip explicit option indicators here to allow string_match to handle them
                refs.append({"answer": ground_truth, "difficulty": difficulty, "task": task, "choices": choices})
                
        except json.JSONDecodeError:
            # Fallback to JSONL
            with open(refs_file, 'r', encoding='utf-8') as f:
                for line in tqdm.tqdm(f, desc="Reading references"):
                    dic = json.loads(line)
                    # ... (logic for JSONL if needed)
                    # For now assuming if it fails it fails
                    pass

    else:
        # Original logic for other benchmarks (JSON Lines assumed)
        with open(refs_file, 'r', encoding='utf-8') as f:
            for line in tqdm.tqdm(f, desc="Reading references"):
                dic = json.loads(line)
                if "solution" in dic:
                    content = dic["solution"]
                elif "answer" in dic:
                    content = dic["answer"]
                else:
                    content = ""
                    
                content_match = re.search(r'<answer>(.*?)</answer>', content)
                ground_truth = content_match.group(1).strip() if content_match else content.strip()
                
                if benchmarks == 'airbench':
                    # ground_truth = normalizer(ground_truth)
                    refs.append({'answer': ground_truth})
                elif benchmarks == 'mmar':
                    modality = dic.get("modality", None)
                    category = dic.get("category", None)
                    choices = dic.get("choices", None)
                    refs.append({"answer": ground_truth.replace('A)', '').replace('B)', '').replace('C)', '').replace('D)', ''), "modality": modality, "category": category, "choices": choices})
    
    return refs

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

def compute_singlechoice_acc_airbench_foundation(hyps, refs):
    acc = 0
    # i = 0
    for hyp, ref in zip(hyps, refs):
        # import pdb
        # pdb.set_trace()
        # in logic
        # if hyp in ref['answer']:
        #     acc += 1

        # new logic
        if ref["answer"] == hyp:
            acc += 1
        elif hyp != 'None' and hyp and (ref["answer"][0] == hyp[0] or ref["answer"][0] == hyp[-1]):
            acc += 1


            
    return acc / len(hyps)

def compute_singlechoice_acc_mmau(hyps, refs):
    acc = 0
    task_metrics = {'sound': [0, 0], 'music': [0, 0], 'speech': [0, 0]}
    diff_metrics = {'easy': [0, 0], 'hard': [0, 0], 'medium': [0, 0]}
    for hyp, ref in zip(hyps, refs):
        answer_hyp = hyp
        answer_ref = ref["answer"]
        choices_ref = ref["choices"]
        task_ref = ref["task"]
        difficulty_ref = ref["difficulty"]
        match_res = string_match(answer_ref, answer_hyp, choices_ref)

        if match_res:
            task_metrics[task_ref][0] += 1
            diff_metrics[difficulty_ref][0] += 1
            acc += 1
        
        task_metrics[task_ref][1] += 1
        diff_metrics[difficulty_ref][1] += 1
    return acc / len(hyps) * 100, task_metrics, diff_metrics

def compute_singlechoice_acc_mmar(hyps, refs):
    acc = 0
    modality_metrics = {'sound': [0, 0], 'music': [0, 0], 'speech': [0, 0], 'mix-sound-music': [0, 0], 'mix-sound-speech': [0, 0], 'mix-music-speech': [0, 0], 'mix-sound-music-speech': [0, 0]}
    category_metrics = {'Signal Layer': [0, 0], 'Perception Layer': [0, 0], 'Semantic Layer': [0, 0], 'Cultural Layer': [0, 0]}
    for hyp, ref in zip(hyps, refs):
        answer_hyp = hyp
        answer_ref = ref["answer"]
        choices_ref = ref["choices"]
        modality_ref = ref["modality"]
        category_ref = ref["category"]
        match_res = string_match(answer_ref, answer_hyp, choices_ref)

        if match_res:
            modality_metrics[modality_ref][0] += 1
            category_metrics[category_ref][0] += 1
            acc += 1
        
        modality_metrics[modality_ref][1] += 1
        category_metrics[category_ref][1] += 1
    return acc / len(hyps) * 100, modality_metrics, category_metrics

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hyps_file", type=str, required=True)
    parser.add_argument("--refs_file", type=str, required=True)
    parser.add_argument("--lang", type=str, default="en")
    parser.add_argument("--benchmarks", type=str, required=True)
    args = parser.parse_args()
    hyps = read_hyps(args.hyps_file, args.benchmarks, args.lang)
    refs = read_refs(args.refs_file, args.benchmarks, args.lang)
    if args.benchmarks == "airbench":
        acc = compute_singlechoice_acc_airbench_foundation(hyps, refs) * 100
        print(f"Single choice accuracy: {acc}")
    elif args.benchmarks == "mmau":
        acc_all, task_acc, diff_acc = compute_singlechoice_acc_mmau(hyps, refs)
        print("*"*30)
        print("Task-wise Accuracy:")
        for task in task_acc:
            n_correct, n_total = task_acc[task]
            acc = (n_correct / n_total) * 100 if n_total > 0 else 0
            print(f"{task} : {acc:.3f}% over {n_total} samples")
        
        print("*"*30)
        print("Difficulty-wise Accuracy:")
        for diff in diff_acc:
            n_correct, n_total = diff_acc[diff]
            acc = (n_correct / n_total) * 100 if n_total > 0 else 0
            print(f"{diff} : {acc:.3f}% over {n_total} samples")
            
        print("*"*30)
        print(f"Total Accuracy: {acc_all:.3f}%")
    elif args.benchmarks == "mmar":
        acc_all, modality_acc, category_acc = compute_singlechoice_acc_mmar(hyps, refs)
        print("*"*30)
        print("Modality-wise Accuracy:")
        for modality in modality_acc:
            n_correct, n_total = modality_acc[modality]
            acc = (n_correct / n_total) * 100 if n_total > 0 else 0
            print(f"{modality} : {acc:.3f}% over {n_total} samples")
        
        print("*"*30)
        print("Category-wise Accuracy:")
        for category in category_acc:
            n_correct, n_total = category_acc[category]
            acc = (n_correct / n_total) * 100 if n_total > 0 else 0
            print(f"{category} : {acc:.3f}% over {n_total} samples")
            
        print("*"*30)
        print(f"Total Accuracy: {acc_all:.3f}%")

if __name__ == "__main__":
    main()