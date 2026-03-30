from fastapi.testclient import TestClient
import model_service.llm_fastapi_omni as mod

class StubProcessor:
    def apply_chat_template(self, conv, add_generation_prompt=True, tokenize=False):
        return "hi"
    def __call__(self, text=None, return_tensors="pt", padding=True, use_audio_in_video=False):
        return {"input_ids": [1, 2, 3]}
    def batch_decode(self, ids, skip_special_tokens=True, clean_up_tokenization_spaces=False):
        return ["hello world"]

class StubModel:
    device = "cpu"
    def generate(self, **kwargs):
        return [[1, 2, 3, 4]]

def stub_ensure_loaded():
    mod.processor = StubProcessor()
    mod.model = StubModel()

def test_health():
    client = TestClient(mod.app)
    r = client.get("/health")
    assert r.status_code == 200

def test_generate():
    mod.ensure_loaded = stub_ensure_loaded
    client = TestClient(mod.app)
    r = client.post("/generate", json={"prompt": "hi"})
    assert r.status_code == 200
    assert r.json()["status"] == "success"
