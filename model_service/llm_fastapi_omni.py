import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import torch
import re
import hashlib
from functools import lru_cache
from fastapi import UploadFile, File, Form

def beautify_text(text):
    """
    对生成的文本进行美化处理，使其更符合中文排版规范：
    1. 中英文之间自动添加空格
    2. 移除重复的换行符
    3. 清理多余的标点
    """
    if not text: return ""
    # 移除首尾多余空格
    text = text.strip()
    # 中英文混排优化：在中文与英文字符/数字之间添加空格
    text = re.sub(r'([\u4e00-\u9fa5])([a-zA-Z0-9])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fa5])', r'\1 \2', text)
    # 移除连续 3 个以上的换行，统一为 2 个（段落间距）
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

# --- 性能优化：音频特征缓存 ---
# 缓存处理后的音频特征，避免在分阶段请求中重复进行 ASR 和音频编码
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
            return {
                "status": "using_cpu",
                "loaded": bool(model is not None and processor is not None),
                "reason": "torch.cuda.is_available() returned False"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Qwen Omni FastAPI is running", "health_url": "/health", "model_path": MODEL_PATH, "loaded": bool(model is not None and processor is not None)}

@app.get("/health")
async def health():
    return {"status": "ok", "loaded": bool(model is not None and processor is not None)}

@app.get("/debug/info")
async def debug_info():
    exists = os.path.isdir(MODEL_PATH)
    files = []
    if exists:
        try:
            files = sorted(os.listdir(MODEL_PATH))[:20]
        except Exception:
            files = []
    return {"model_path": MODEL_PATH, "exists": exists, "files": files, "loaded": bool(model is not None and processor is not None)}

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

import traceback

import os
import subprocess
import tempfile
import io
import soundfile as sf
import numpy as np

def load_audio_robust(content, original_filename=None):
    # 1. Try reading directly with soundfile (fast path for standard WAV)
    try:
        wav, sr = sf.read(io.BytesIO(content))
        return wav, sr
    except Exception as e:
        print(f"Direct soundfile read failed: {e}. Falling back to ffmpeg conversion...")
    
    # 2. Fallback: Use ffmpeg to convert to 16k mono WAV
    # Create temp input file
    input_suffix = ""
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        if ext:
            input_suffix = ext
            
    with tempfile.NamedTemporaryFile(suffix=input_suffix, delete=False) as tmp_in:
        tmp_in.write(content)
        tmp_in_path = tmp_in.name
        
    # Create temp output file path
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_out:
        tmp_out_path = tmp_out.name
        
    try:
        # 尝试寻找用户指定的 ffmpeg 路径 (针对服务器环境进行优化)
        ffmpeg_cmd = "ffmpeg"
        possible_paths = [
            "/data/baymax/tmp_ffmpeg/ffmpeg",
            os.path.expanduser("~/tmp_ffmpeg/ffmpeg"),
            "/usr/bin/ffmpeg",
            "ffmpeg"
        ]
        
        for p in possible_paths:
            if os.path.exists(p) or (p == "ffmpeg" and subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0):
                ffmpeg_cmd = p
                print(f"Using ffmpeg: {ffmpeg_cmd}")
                break

        # ffmpeg -y -i input -ar 16000 -ac 1 output.wav
        subprocess.run(
            [ffmpeg_cmd, "-y", "-i", tmp_in_path, "-ar", "16000", "-ac", "1", tmp_out_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Read the converted WAV
        wav, sr = sf.read(tmp_out_path)
        return wav, sr
        
    except FileNotFoundError:
        print("Error: ffmpeg not found in system PATH. Please install it (e.g., 'sudo apt install ffmpeg' or 'conda install -c conda-forge ffmpeg').")
        raise RuntimeError("ffmpeg not found. Please install ffmpeg on the server to support non-WAV audio formats.")
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg failed: {e.stderr.decode()}")
        raise RuntimeError(f"Failed to decode audio file. ffmpeg error: {e.stderr.decode()}")
    except Exception as e:
        print(f"Error during audio conversion: {e}")
        raise
    finally:
        # Cleanup temp files
        if os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)
        if os.path.exists(tmp_out_path):
            os.remove(tmp_out_path)

@app.post("/inference")
async def inference(
    prompt: str = Form(...),
    audio_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None), # 增加对直接前端调用的兼容性
    stage: int = Form(0), # 0: Full, 1: Intent, 2: Knowledge, 3: Deduction, 4: Conclusion
    context: str = Form(""), # Previous stage results
):
    try:
        # 性能优化：除非显存极其紧张，否则不要在主推理路径上频繁 empty_cache
        # if torch.cuda.is_available():
        #     torch.cuda.empty_cache()
            
        print(f"\n[DEBUG] === Inference Request (Stage: {stage}) ===")
        ensure_loaded()
        
        # --- Stage 0: Load Audio (带缓存逻辑) ---
        wav = None
        sr = 16000
        audio_id = None
        
        # 兼容两种文件字段名
        actual_file = audio_file or file
        
        if actual_file is not None:
            # 获取音频内容，如果是重复请求则直接使用缓存
            content = await actual_file.read()
            if not content:
                print("[WARN] Received empty audio file.")
            else:
                audio_id = get_audio_hash(content)
                
                if audio_id in AUDIO_FEATURE_CACHE:
                    print(f"[DEBUG] Using cached audio features for: {audio_id}")
                    wav, sr = AUDIO_FEATURE_CACHE[audio_id]
                else:
                    try:
                        wav, sr = sf.read(io.BytesIO(content))
                    except Exception as e:
                        print(f"[WARN] Direct soundfile read failed, trying robust loader: {e}")
                        wav, sr = load_audio_robust(content, actual_file.filename)
                    
                    if wav.ndim > 1: wav = wav.mean(axis=1)
                    if wav.dtype != np.float32: wav = wav.astype(np.float32)
                    if sr != 16000:
                        ratio = 16000 / sr
                        new_len = int(len(wav) * ratio)
                        wav = np.interp(np.linspace(0.0, 1.0, num=new_len), np.linspace(0.0, 1.0, num=len(wav)), wav).astype(np.float32)
                        sr = 16000
                    
                    # 存入简单缓存
                    AUDIO_FEATURE_CACHE[audio_id] = (wav, sr)
                    if len(AUDIO_FEATURE_CACHE) > 50:
                        first_key = next(iter(AUDIO_FEATURE_CACHE))
                        del AUDIO_FEATURE_CACHE[first_key]

        # --- Helper for single stage ---
        def run_stage(s_idx, current_prompt, prev_context=""):
            prompts = {
                1: f"请分析这段音频并进行【意图识别】。识别音频类型并简述其表达的核心意图。另外，请给该任务的理解难度打个分（0-100），格式为【难度评分：数字】。用户输入：{current_prompt}",
                2: f"结合刚才的分析：{prev_context}\n请开始【知识检索】。提取音频相关的专业知识点（乐器、曲风等），建议结构化表达。请以【知识检索】开头输出。",
                3: f"基于已有的知识：{prev_context}\n请进行【逻辑推演】。分析音频的节奏、旋律或情感是如何推导出结论的。请以【逻辑推演】开头输出。",
                4: f"综合以上推理过程：{prev_context}\n请给出【结论总结】。直接回答用户的核心问题。请以【最终结论】开头输出。"
            }
            
            res = generate_pipeline_step(prompts[s_idx], wav, sr)
            tag = {1: "意图识别", 2: "知识检索", 3: "逻辑推演", 4: "最终结论"}[s_idx]
            
            # 提取并移除难度评分（支持多种格式：【难度评分：20】 或 难度评分：20。）
            difficulty = None
            if s_idx == 1:
                # 兼容不同格式的正则匹配 (包括末尾可能带有的句号或换行)
                diff_patterns = [
                    r'【难度评分：(\d+)】',
                    r'难度评分：(\d+)[。 \n]*',
                    r'评分：(\d+)[。 \n]*'
                ]
                for pattern in diff_patterns:
                    match = re.search(pattern, res)
                    if match:
                        difficulty = int(match.group(1))
                        # 移除整个匹配项
                        res = res.replace(match.group(0), "")
                        break

            # 增强提取精准度：移除标签、冒号、空格以及多余标点
            cleaned = res.replace(f"【{tag}】", "").strip()
            cleaned = re.sub(r'^[：:。，,\s]+', '', cleaned)
            
            # 过滤常见的社交辞令/结束语 (作为后置保障)
            filler_patterns = [
                r'如果还有其他.*?(都可以跟我说哦|请告诉我).*?$',
                r'期待您的下一次.*$',
                r'如果有不同意见.*?$',
                r'希望能帮到您.*?$'
            ]
            for filler in filler_patterns:
                cleaned = re.sub(filler, '', cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

            # 应用文本美化
            cleaned = beautify_text(cleaned)
            
            if s_idx == 1:
                return cleaned, difficulty
            return cleaned

        # --- Execution Logic ---
        if stage > 0:
            if stage == 1:
                result_text, difficulty = run_stage(1, prompt, context)
            else:
                result_text = run_stage(stage, prompt, context)
                difficulty = None
                
            tags = {1: "意图识别", 2: "知识检索", 3: "逻辑推演", 4: "最终结论"}
            
            res_data = {
                "status": "success",
                "text": f"【{tags[stage]}】\n{result_text}",
                "stage": stage,
                "content": result_text
            }
            
            if difficulty is not None:
                res_data["difficulty"] = difficulty
            
            if stage == 4:
                res_data["answer"] = result_text
            
            return res_data
        
        else:
            # 还原原先的内容：分步推理流程 (注意：此模式更容易 OOM，建议使用推理模式优化)
            res_1, diff = run_stage(1, prompt, "")
            res_2 = run_stage(2, prompt, res_1)
            res_3 = run_stage(3, prompt, res_2)
            res_4 = run_stage(4, prompt, f"{res_1}\n{res_2}\n{res_3}")

            full_formatted_text = f"【意图识别】\n{res_1}\n\n【知识检索】\n{res_2}\n\n【逻辑推演】\n{res_3}\n\n【最终结论】\n{res_4}"
            
            res_data = {
                "status": "success",
                "text": full_formatted_text,
                "intent": res_1,
                "knowledge": res_2,
                "deduction": res_3,
                "answer": res_4,
                "difficulty": diff if diff is not None else 60
            }
            return res_data

    except Exception as e:
        print("Error in inference:")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

def generate_pipeline_step(step_prompt, wav, sr):
    # 使用官方默认 Prompt 以启用音频感知能力并消除警告
    system_prompt = "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
    
    if wav is not None:
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "audio"}, {"type": "text", "text": step_prompt}]},
        ]
        text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
        inputs = processor(text=text_input, audio=[wav], sampling_rate=sr, return_tensors="pt", padding=True, use_audio_in_video=False)
    else:
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": step_prompt}]},
        ]
        text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
        inputs = processor(text=text_input, return_tensors="pt", padding=True, use_audio_in_video=False)

    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    # 性能极致优化：使用 torch.inference_mode() 且根据任务类型限制最大 token 数
    with torch.inference_mode():
        out = model.generate(
            **inputs, 
            max_new_tokens=800 if "一次性输出" in step_prompt else 300, 
            pad_token_id=processor.tokenizer.eos_token_id,
            use_cache=True # 显式开启 KV Cache
        )
    
    generated_ids = out[0] if isinstance(out, tuple) else out
    input_len = inputs["input_ids"].shape[-1]
    generated_ids = generated_ids[:, input_len:]
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

def generate_tts_base64(text):
    try:
        import base64, io, soundfile as sf
        # Use the exact default system prompt to enable audio output mode and avoid warnings
        default_system_prompt = "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
        conv = [
            {"role": "system", "content": [{"type": "text", "text": default_system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": f"请用语音说：{text}"}]}
        ]
        ti = processor.apply_chat_template(conv, add_generation_prompt=True, tokenize=False)
        inputs = processor(text=ti, return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs)
        
        # Audio output is the second element in the tuple for Qwen2.5-Omni
        audio_out = out[1] if isinstance(out, tuple) and len(out) > 1 else None
        
        if audio_out is not None:
            buf = io.BytesIO()
            sf.write(buf, audio_out.reshape(-1).detach().cpu().numpy(), 24000, format='WAV')
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"[DEBUG] TTS generation failed: {e}")
        return None
    return None

@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        ensure_loaded()
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a helpful assistant."}]},
            {"role": "user", "content": [{"type": "text", "text": req.prompt}]},
        ]
        text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
        inputs = processor(text=text_input, return_tensors="pt", padding=True, use_audio_in_video=False)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(**inputs, use_audio_in_video=False)
        text_ids = out[0] if isinstance(out, tuple) else out
        text = processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        return {"status": "success", "text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

class TTSRequest(BaseModel):
    prompt: str

@app.post("/tts")
async def tts(req: TTSRequest):
    try:
        ensure_loaded()
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}]},
            {"role": "user", "content": [{"type": "text", "text": f"请用语音说：{req.prompt}"}]},
        ]
        text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
        inputs = processor(text=text_input, return_tensors="pt", padding=True, use_audio_in_video=False)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(**inputs, use_audio_in_video=False)
        text_ids = out[0] if isinstance(out, tuple) else out
        audio_out = out[1] if isinstance(out, tuple) and len(out) > 1 else None
        text = processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        if audio_out is None:
            return {"status": "success", "text": text, "audio_base64": None}
        import base64, io, soundfile as sf
        wav = audio_out.reshape(-1).detach().cpu().numpy()
        buf = io.BytesIO()
        sf.write(buf, wav, samplerate=24000, format="WAV")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {"status": "success", "text": text, "audio_base64": b64}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/asr")
async def asr(audio_file: UploadFile = File(...), prompt: str = "请转写并概述这段语音的内容"):
    try:
        ensure_loaded()
        content = await audio_file.read()
        import io, soundfile as sf, numpy as np
        wav, sr = sf.read(io.BytesIO(content))
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        if wav.dtype != np.float32:
            wav = wav.astype(np.float32)
        if sr != 16000:
            ratio = 16000 / sr
            new_len = int(len(wav) * ratio)
            x_old = np.linspace(0.0, 1.0, num=len(wav), endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
            wav = np.interp(x_new, x_old, wav).astype(np.float32)
            sr = 16000
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}]},
            {"role": "user", "content": [{"type": "audio"}, {"type": "text", "text": prompt}]},
        ]
        text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
        inputs = processor(text=text_input, audio=[wav], sampling_rate=sr, return_tensors="pt", padding=True, use_audio_in_video=False)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(**inputs, use_audio_in_video=False)
        text_ids = out[0] if isinstance(out, tuple) else out
        text = processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        return {"status": "success", "text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
