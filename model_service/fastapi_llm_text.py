import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.9

app = FastAPI(title="Text LLM FastAPI")

DEFAULT_MODEL_PATH = "/data/baymax/checkpoint-300-merged"
MODEL_PATH = os.environ.get("LALM_MODEL_PATH") or DEFAULT_MODEL_PATH
tokenizer = None
model = None

def ensure_loaded():
    global tokenizer, model
    if tokenizer is None or model is None:
        if MODEL_PATH is None or not os.path.isdir(MODEL_PATH):
            raise RuntimeError("Invalid LALM_MODEL_PATH")
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
            model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True, torch_dtype="auto", device_map="auto")
        except Exception:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True, torch_dtype="auto", device_map="auto")

@app.get("/health")
async def health():
    status = "ok" if MODEL_PATH else "no_model_path"
    loaded = model is not None and tokenizer is not None
    return {"status": status, "loaded": loaded}

@app.get("/")
async def root():
    return {"message": "Text LLM FastAPI is running", "health_url": "/health", "model_path": MODEL_PATH, "loaded": bool(model is not None and tokenizer is not None)}

@app.post("/load")
async def load():
    try:
        ensure_loaded()
        loaded = model is not None and tokenizer is not None
        return {"status": "success", "loaded": loaded}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/debug/info")
async def debug_info():
    exists = MODEL_PATH is not None and os.path.isdir(MODEL_PATH)
    files = []
    if exists:
        try:
            files = sorted(os.listdir(MODEL_PATH))[:20]
        except Exception:
            files = []
    return {"model_path": MODEL_PATH, "exists": exists, "files": files, "loaded": model is not None and tokenizer is not None}

@app.get("/routes")
async def list_routes():
    return [{"path": r.path, "methods": sorted(list(getattr(r, "methods", set()))) or ["GET"]} for r in app.routes]

@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        ensure_loaded()
        inputs = tokenizer(req.prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        do_sample = req.temperature is not None and req.temperature > 0.0
        import torch
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=req.max_new_tokens,
                do_sample=do_sample,
                temperature=req.temperature,
                top_p=req.top_p,
                pad_token_id=tokenizer.eos_token_id,
            )
        text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return {"status": "success", "text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
