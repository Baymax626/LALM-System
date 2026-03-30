import os
import torch
import soundfile as sf
import numpy as np
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor

MODEL_PATH = "/data/baymax/checkpoint-300-merged"
TEST_WAV = "/data/baymax/llm_server/test_wav.wav"
OUT_WAV = "/data/baymax/llm_server/tts_out.wav"

def to_mono_float32(wav):
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if wav.dtype != np.float32:
        wav = wav.astype(np.float32)
    return wav

def resample_to_16k(wav, sr):
    if sr == 16000:
        return wav
    ratio = 16000 / sr
    new_len = int(len(wav) * ratio)
    x_old = np.linspace(0.0, 1.0, num=len(wav), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
    return np.interp(x_new, x_old, wav).astype(np.float32)

def main():
    print("[1/7] 正在加载处理器与模型…")
    processor = Qwen2_5OmniProcessor.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
    model = Qwen2_5OmniForConditionalGeneration.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True, torch_dtype="auto", device_map="auto")
    print("[2/7] 文本对话生成（检查模型加载正常）")
    conversation = [
        {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a helpful assistant."}]},
        {"role": "user", "content": [{"type": "text", "text": "你好，介绍一下你的能力"}]},
    ]
    text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    inputs = processor(text=text_input, return_tensors="pt", padding=True, use_audio_in_video=False)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(**inputs, use_audio_in_video=False)
    text_ids = out[0] if isinstance(out, tuple) else out
    text = processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    print(text)
    print("[3/7] 正在进行 TTS（生成指定语音：一加一等于几）")
    conversation_tts = [
        {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}]},
        {"role": "user", "content": [{"type": "text", "text": "请用语音说：一加一等于几"}]},
    ]
    text_input_tts = processor.apply_chat_template(conversation_tts, add_generation_prompt=True, tokenize=False)
    inputs_tts = processor(text=text_input_tts, return_tensors="pt", padding=True, use_audio_in_video=False)
    inputs_tts = {k: v.to(model.device) for k, v in inputs_tts.items()}
    with torch.no_grad():
        out_tts = model.generate(**inputs_tts, use_audio_in_video=False)
    audio_out = out_tts[1] if isinstance(out_tts, tuple) and len(out_tts) > 1 else None
    if audio_out is not None:
        wav_tts = audio_out.reshape(-1).detach().cpu().numpy()
        sf.write(OUT_WAV, wav_tts, samplerate=24000, format="WAV")
        print(f"[4/7] TTS 完成，已保存：{OUT_WAV}，采样率=24000，长度样本={len(wav_tts)}")
    else:
        print("[4/7] TTS 未返回音频，后续按外部测试音频进行 ASR")
    target_wav = OUT_WAV if os.path.isfile(OUT_WAV) else TEST_WAV
    if os.path.isfile(target_wav):
        print(f"[5/7] 读取待分析音频：{target_wav}")
        wav, sr = sf.read(target_wav)
        wav = to_mono_float32(wav)
        print(f"[5/7] 音频预处理：sr={sr}，shape={wav.shape}，dtype={wav.dtype}")
        if sr != 16000:
            print(f"[5/7] 采样率为 {sr}，正在重采样到 16000")
            wav = resample_to_16k(wav, sr)
            sr = 16000
            print(f"[5/7] 重采样完成：sr={sr}，shape={wav.shape}，dtype={wav.dtype}")
        conversation_asr = [
            {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}]},
            {"role": "user", "content": [{"type": "audio"}, {"type": "text", "text": "请转写并概述这段语音的内容"}]},
        ]
        text_input2 = processor.apply_chat_template(conversation_asr, add_generation_prompt=True, tokenize=False)
        inputs2 = processor(text=text_input2, audio=[wav], sampling_rate=sr, return_tensors="pt", padding=True, use_audio_in_video=False)
        inputs2 = {k: v.to(model.device) for k, v in inputs2.items()}
        print("[6/7] 正在进行 ASR 生成…")
        with torch.no_grad():
            out2 = model.generate(**inputs2, use_audio_in_video=False)
        text_ids2 = out2[0] if isinstance(out2, tuple) else out2
        text2 = processor.batch_decode(text_ids2, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        print("[7/7] ASR 文本：")
        print(text2)
    else:
        print(f"[5/7] 未找到音频文件：{target_wav}，请先生成或提供 WAV 后再运行")

if __name__ == "__main__":
    main()
