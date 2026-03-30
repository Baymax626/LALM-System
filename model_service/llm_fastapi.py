import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import torch
import re
import hashlib
from functools import lru_cache
from fastapi import UploadFile, File, Form
import traceback
import subprocess
import tempfile
import io
import soundfile as sf
import numpy as np

def beautify_text(text):
    """
    对生成的文本进行美化处理，使其更符合中文排版规范：
    1. 中英文之间自动添加空格
    2. 移除重复的换行符
    3. 清理多余的标点
    """
    if not text: return ""
    text = text.strip()
    text = re.sub(r'([\u4e00-\u9fa5])([a-zA-Z0-9])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fa5])', r'\1 \2', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

# --- 性能优化：音频特征缓存 ---
AUDIO_FEATURE_CACHE = {}

def get_audio_hash(content):
    return hashlib.md5(content).hexdigest()

class GenerateRequest(BaseModel):
    prompt: str

DEFAULT_MODEL_PATH = "/data/baymax/checkpoint-300-merged"
MODEL_PATH = DEFAULT_MODEL_PATH
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Qwen Omni FastAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
model = None
processor = None
FORCE_GPU_ID = 0

def ensure_loaded():
    global model, processor
    if model is None or processor is None:
        from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
        processor = Qwen2_5OmniProcessor.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
        device_map = {"": f"cuda:{FORCE_GPU_ID}"} if torch.cuda.is_available() else "cpu"
        model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            MODEL_PATH,
            local_files_only=True,
            trust_remote_code=True,
            torch_dtype="auto",
            device_map=device_map
        )

@app.get("/device_info")
async def device_info():
    try:
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            current_device = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(current_device)
            memory_allocated = torch.cuda.memory_allocated(current_device) / 1024 / 1024
            memory_reserved = torch.cuda.memory_reserved(current_device) / 1024 / 1024
            return {
                "status": "using_gpu",
                "loaded": bool(model is not None and processor is not None),
                "device_count_visible": device_count,
                "current_device_id": current_device,
                "device_name": device_name,
                "memory_allocated_mb": round(memory_allocated, 2),
                "memory_reserved_mb": round(memory_reserved, 2),
                "force_gpu_id_setting": FORCE_GPU_ID
            }
        else:
            return {"status": "using_cpu", "loaded": bool(model is not None and processor is not None), "reason": "torch.cuda.is_available() returned False"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Qwen Omni FastAPI is running", "health_url": "/health", "model_path": MODEL_PATH, "loaded": bool(model is not None and processor is not None)}

@app.get("/health")
async def health():
    return {"status": "ok", "loaded": bool(model is not None and processor is not None)}

@app.get("/routes")
async def routes():
    return [{"path": r.path, "methods": sorted(list(getattr(r, "methods", set()))) or ["GET"]} for r in app.routes]

@app.post("/load")
async def load():
    try:
        ensure_loaded()
        return {"status": "success", "loaded": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

def load_audio_robust(content, original_filename=None):
    try:
        wav, sr = sf.read(io.BytesIO(content))
        return wav, sr
    except Exception as e:
        print(f"Direct soundfile read failed: {e}. Falling back to ffmpeg conversion...")
    
    input_suffix = ""
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        if ext: input_suffix = ext
            
    with tempfile.NamedTemporaryFile(suffix=input_suffix, delete=False) as tmp_in:
        tmp_in.write(content)
        tmp_in_path = tmp_in.name
        
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_out:
        tmp_out_path = tmp_out.name
        
    try:
        ffmpeg_cmd = "ffmpeg"
        possible_paths = ["/data/baymax/tmp_ffmpeg/ffmpeg", os.path.expanduser("~/tmp_ffmpeg/ffmpeg"), "/usr/bin/ffmpeg", "ffmpeg"]
        for p in possible_paths:
            if os.path.exists(p) or (p == "ffmpeg" and subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0):
                ffmpeg_cmd = p
                break

        subprocess.run([ffmpeg_cmd, "-y", "-i", tmp_in_path, "-ar", "16000", "-ac", "1", tmp_out_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wav, sr = sf.read(tmp_out_path)
        return wav, sr
    except Exception as e:
        raise RuntimeError(f"Audio conversion failed: {e}")
    finally:
        if os.path.exists(tmp_in_path): os.remove(tmp_in_path)
        if os.path.exists(tmp_out_path): os.remove(tmp_out_path)

@app.post("/inference")
async def inference(
    prompt: str = Form(...),
    audio_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None), # 兼容前端
    stage: int = Form(0), 
    context: str = Form(""),
):
    try:
        ensure_loaded()
        wav, sr, audio_id = None, 16000, None
        actual_file = audio_file or file
        
        if actual_file is not None:
            content = await actual_file.read()
            if content:
                audio_id = get_audio_hash(content)
                if audio_id in AUDIO_FEATURE_CACHE:
                    wav, sr = AUDIO_FEATURE_CACHE[audio_id]
                else:
                    wav, sr = load_audio_robust(content, actual_file.filename)
                    if wav.ndim > 1: wav = wav.mean(axis=1)
                    wav = wav.astype(np.float32)
                    if sr != 16000:
                        ratio = 16000 / sr
                        wav = np.interp(np.linspace(0.0, 1.0, num=int(len(wav) * ratio)), np.linspace(0.0, 1.0, num=len(wav)), wav).astype(np.float32)
                        sr = 16000
                    AUDIO_FEATURE_CACHE[audio_id] = (wav, sr)
                    if len(AUDIO_FEATURE_CACHE) > 50: del AUDIO_FEATURE_CACHE[next(iter(AUDIO_FEATURE_CACHE))]

        def run_stage(s_idx, current_prompt, prev_context=""):
            # 性能优化：精简上下文，只保留最后 200 字以减少 Prefill 耗时
            short_context = prev_context[-200:] if len(prev_context) > 200 else prev_context
            
            prompts = {
                1: f"请分析音频并进行【意图识别】。请简明扼要地识别音频类型并概述意图。给任务难度打分（0-100），格式为【难度评分：数字】。用户输入：{current_prompt}",
                2: f"基于分析：{short_context}\n请开始【知识检索】。请简明扼要地提取专业知识点（乐器、曲风等）。请以【知识检索】开头输出。",
                3: f"基于知识：{short_context}\n请进行【逻辑推演】。请简明扼要地分析节奏、旋律或情感是如何推导结论的。请以【逻辑推演】开头输出。",
                4: f"综合过程：{short_context}\n请给出【结论总结】。请简明扼要地直接回答核心问题。请以【最终结论】开头输出。"
            }
            # 针对不同阶段动态调整 token 限制以加速生成
            stage_max_tokens = 150 if s_idx in [1, 3] else 250
            res = generate_pipeline_step(prompts[s_idx], wav, sr, max_tokens=stage_max_tokens)
            tag = {1: "意图识别", 2: "知识检索", 3: "逻辑推演", 4: "最终结论"}[s_idx]
            
            difficulty = None
            if s_idx == 1:
                match = re.search(r'【难度评分：(\d+)】|难度评分：(\d+)', res)
                if match:
                    difficulty = int(match.group(1) or match.group(2))
                    res = res.replace(match.group(0), "")

            cleaned = beautify_text(re.sub(r'^[：:。，,\s]+', '', res.replace(f"【{tag}】", "").strip()))
            # 过滤辞令
            for f in [r'如果还有其他.*?$', r'期待您的下一次.*$', r'希望能帮到您.*?$']:
                cleaned = re.sub(f, '', cleaned, flags=re.DOTALL | re.IGNORECASE).strip()
            return (cleaned, difficulty) if s_idx == 1 else cleaned

        if stage > 0:
            res_text = run_stage(stage, prompt, context)
            if stage == 1: res_text, diff = res_text
            else: diff = None
            
            tags = {1: "意图识别", 2: "知识检索", 3: "逻辑推演", 4: "最终结论"}
            data = {"status": "success", "text": f"【{tags[stage]}】\n{res_text}", "stage": stage, "content": res_text}
            if diff is not None: data["difficulty"] = diff
            if stage == 4: data["answer"] = res_text
            return data
        else:
            # 性能核心优化：使用单次推理完成所有阶段（One-shot Chain of Thought）
            # 这比原先的 4 次推理快 3-4 倍，且保持输出格式一致。
            combined_prompt = f"""请对用户音频进行极简深度的分析，严格按照以下四个部分一次性输出，每个部分以【标签名】开头。
要求：每个部分的描述请控制在 50 字以内，严禁废话，直接给出核心逻辑。

1. 【意图识别】：识别用户意图、音频类型，并给出【难度评分：数字】。
2. 【知识检索】：提取最核心的专业知识点（如乐器、曲风）。
3. 【逻辑推演】：简述节奏或情感的核心逻辑，一句话概括。
4. 【最终结论】：给出精炼的最终答案。

用户输入：{prompt}"""
            
            full_res = generate_pipeline_step(combined_prompt, wav, sr, max_tokens=600)
            
            # 解析输出内容和难度分
            def extract_tag(text, tag):
                pattern = rf"【{tag}】(.*?)(?=【|$)"
                match = re.search(pattern, text, re.DOTALL)
                return beautify_text(match.group(1).strip()) if match else "未生成"

            # 提取难度分
            diff_match = re.search(r'【难度评分：(\d+)】|难度评分：(\d+)', full_res)
            difficulty = int(diff_match.group(1) or diff_match.group(2)) if diff_match else 60
            
            # 清理全文中的难度评分标签
            if diff_match:
                full_res = full_res.replace(diff_match.group(0), "")

            res_1 = extract_tag(full_res, "意图识别")
            res_2 = extract_tag(full_res, "知识检索")
            res_3 = extract_tag(full_res, "逻辑推演")
            res_4 = extract_tag(full_res, "最终结论")

            return {
                "status": "success",
                "text": full_res,
                "intent": res_1, 
                "knowledge": res_2, 
                "deduction": res_3, 
                "answer": res_4, 
                "difficulty": difficulty
            }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

def generate_pipeline_step(step_prompt, wav, sr, max_tokens=300):
    system_prompt = "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
    if wav is not None:
        conv = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}, {"role": "user", "content": [{"type": "audio"}, {"type": "text", "text": step_prompt}]}]
        inputs = processor(text=processor.apply_chat_template(conv, add_generation_prompt=True, tokenize=False), audio=[wav], sampling_rate=sr, return_tensors="pt", padding=True)
    else:
        conv = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}, {"role": "user", "content": [{"type": "text", "text": step_prompt}]}]
        inputs = processor(text=processor.apply_chat_template(conv, add_generation_prompt=True, tokenize=False), return_tensors="pt", padding=True)

    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_tokens, pad_token_id=processor.tokenizer.eos_token_id, use_cache=True)
    
    gen_ids = out[0] if isinstance(out, tuple) else out
    return processor.batch_decode(gen_ids[:, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)[0]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
