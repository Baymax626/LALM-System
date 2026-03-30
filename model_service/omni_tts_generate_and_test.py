import os
import torch
import soundfile as sf
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor

MODEL_PATH = "/data/baymax/checkpoint-300-merged"
OUT_WAV = "/data/baymax/llm_server/tts_out.wav"
TEST_WAV = "/data/baymax/llm_server/test_wav.wav"

def ensure_model():
    proc = Qwen2_5OmniProcessor.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
    mdl = Qwen2_5OmniForConditionalGeneration.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True, torch_dtype="auto", device_map="auto")
    return proc, mdl

def generate_tts(proc, mdl, text, out_path):
    conversation = [
        {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}]},
        {"role": "user", "content": [{"type": "text", "text": f"请用语音说：{text}"}]},
    ]
    tmpl = proc.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    inputs = proc(text=tmpl, return_tensors="pt", padding=True, use_audio_in_video=False)
    inputs = {k: v.to(mdl.device) for k, v in inputs.items()}
    with torch.no_grad():
        out = mdl.generate(**inputs, use_audio_in_video=False)
    text_ids = out[0] if isinstance(out, tuple) else out
    audio_out = out[1] if isinstance(out, tuple) and len(out) > 1 else None
    if audio_out is not None:
        wav = audio_out.reshape(-1).detach().cpu().numpy()
        sf.write(out_path, wav, samplerate=24000, format="WAV")
    return proc.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0], audio_out is not None

def asr_summarize(proc, mdl, wav_path, prompt="请听我的语音并总结要点"):
    conversation = [
        {"role": "system", "content": [{"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}]},
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
    ]
    tmpl = proc.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    wav, sr = sf.read(wav_path)
    inputs = proc(text=tmpl, audio=[wav], return_tensors="pt", padding=True, use_audio_in_video=False)
    inputs = {k: v.to(mdl.device) for k, v in inputs.items()}
    with torch.no_grad():
        out = mdl.generate(**inputs, use_audio_in_video=False)
    text_ids = out[0] if isinstance(out, tuple) else out
    return proc.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

def main():
    proc, mdl = ensure_model()
    text = "你好，我是通义千问。我可以进行文本和语音的交流。"
    gen_text, has_audio = generate_tts(proc, mdl, text, OUT_WAV)
    print("TTS文本：", gen_text)
    print("已生成语音：", OUT_WAV if has_audio else "未返回语音")
    target_wav = OUT_WAV if has_audio else TEST_WAV
    if os.path.isfile(target_wav):
        summary = asr_summarize(proc, mdl, target_wav, prompt="请转写并概述这段语音的内容")
        print("ASR结果：", summary)
    else:
        print("未找到测试音频：", target_wav)

if __name__ == "__main__":
    main()
