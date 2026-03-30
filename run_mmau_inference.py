import json
import requests
import os
import subprocess
import sys
from tqdm import tqdm

# --- 1. 配置 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MMAU_DIR = os.path.join(CURRENT_DIR, "MMAU-main")
INPUT_FILE = os.path.join(MMAU_DIR, "mmau-test-mini.json")
OUTPUT_FILE = os.path.join(MMAU_DIR, "mmau-test-mini-results.json")
EVAL_SCRIPT = os.path.join(MMAU_DIR, "evaluation.py")

API_URL = "http://127.0.0.1:8002/inference"  # 通过 SSH 隧道访问 (Port 8002)
AUDIO_ROOT = r"D:\Download\test-mini-audios"   # 本地解压后的音频目录

TEST_LIMIT = 5  # 仅测试前 5 条

# --- 2. 读取/加载数据 (支持断点续传) ---
if os.path.exists(OUTPUT_FILE):
    print(f"Found existing results file: {OUTPUT_FILE}")
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {len(data)} samples from existing results.")
    except Exception as e:
        print(f"Error loading existing results: {e}. Reloading from input.")
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
else:
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found at {INPUT_FILE}")
        exit(1)
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} samples from {INPUT_FILE}")

# --- 3. 遍历并推理 ---
processed_count = 0
inference_count = 0

print(f"Starting inference (Limit: {TEST_LIMIT} samples)...")

for i, item in enumerate(tqdm(data)):
    if processed_count >= TEST_LIMIT:
        break

    # 检查是否已经跑过且有结果
    if 'model_output' in item and item['model_output']:
        processed_count += 1
        continue
    
    inference_count += 1
    processed_count += 1

    # Construct Prompt based on MMAU style
    question = item['question']
    choices = item['choices']
    
    # Format: Question + Choices
    prompt_content = ""
    for idx, choice in enumerate(choices):
        prompt_content += f"{chr(65+idx)}) {choice}  "
    
    # Add instruction for Chain-of-Thought and structured answer (Updated based on user request V5)
    prompt = (
        f"Question: {question}\n"
        f"Choices: {prompt_content}\n"
        "Output your thinking process in <think> </think> and put the most suitable answer (from A, B, C, and D with its corresponding answer) in <answer> </answer> tags."
    )

    # 获取音频路径
    audio_rel_path = item.get('audio_id', item.get('audio_path', ''))
    filename = os.path.basename(audio_rel_path)
    audio_path = os.path.join(AUDIO_ROOT, filename)
    
    if not os.path.exists(audio_path):
        # 尝试去掉可能存在的路径前缀再找一次
        # e.g. ./test-mini-audios/abc.wav -> abc.wav
        audio_path = os.path.join(AUDIO_ROOT, os.path.basename(filename))

    if not os.path.exists(audio_path):
        print(f"\nWarning: Audio file not found: {audio_path}")
        item['model_output'] = ""
    else:
        # 调用模型接口
        try:
            with open(audio_path, 'rb') as audio_f:
                files = {
                    'audio_file': (filename, audio_f, 'audio/wav')
                }
                payload = {
                    'prompt': prompt,
                    'tts': False
                }
                # 发送请求
                response = requests.post(API_URL, data=payload, files=files, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                raw_output = result.get('conclusion', result.get('text', ''))
                
                # 增强解析逻辑：优先提取 <answer> 标签内容
                import re
                answer_match = re.search(r'<answer>(.*?)</answer>', raw_output, re.DOTALL | re.IGNORECASE)
                if answer_match:
                    # 如果找到了标签，只取标签内的内容，极大提高匹配成功率
                    clean_answer = answer_match.group(1).strip()
                    
                    # 格式化为 "A: Content" 形式
                    # 1. 尝试找到 A) B) C) D) 并替换为 A: B: 等
                    clean_answer = re.sub(r'([A-D])\)', r'\1:', clean_answer)
                    
                    # 2. 如果没有冒号，尝试把 A Content 变成 A: Content
                    if not ':' in clean_answer and len(clean_answer) > 1 and clean_answer[0] in 'ABCD' and clean_answer[1] == ' ':
                         clean_answer = clean_answer[0] + ':' + clean_answer[1:]

                    item['model_output'] = clean_answer
                else:
                    # 没找到标签，回退到原始输出
                    item['model_output'] = raw_output
            else:
                print(f"\nAPI Error {response.status_code}: {response.text}")
                item['model_output'] = ""
                
        except Exception as e:
            print(f"\nError processing {item['id']}: {e}")
            item['model_output'] = ""
    
    # 实时保存 (每跑一个保存一次，确保安全)
    # 虽然频繁IO有效率问题，但在100个样本规模下可忽略，安全性优先
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

print(f"\nInference loop finished. Processed {inference_count} new samples.")
print(f"Total samples checked: {processed_count}")
print(f"Results saved to {OUTPUT_FILE}")

# --- 4. 运行评估 ---
print("\n" + "="*30)
print("Running Evaluation Script...")
print("="*30)

if os.path.exists(EVAL_SCRIPT):
    try:
        # 调用 evaluation.py
        # 注意：需要确保 evaluation.py 能找到正确的 Python 环境
        # 这里直接使用当前运行脚本的 python 解释器
        # 修复 UnicodeDecodeError: 使用 errors='replace' 来忽略无法解码的字符
        cmd = [sys.executable, EVAL_SCRIPT, "--input", OUTPUT_FILE]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        print(result.stdout)
        if result.stderr:
            print("Evaluation Errors:")
            print(result.stderr)
            
    except Exception as e:
        print(f"Failed to run evaluation script: {e}")
else:
    print(f"Evaluation script not found at {EVAL_SCRIPT}")
