import types
from fastapi.testclient import TestClient
import model_service.llm_fastapi as mod

class StubTokenizer:
    eos_token_id = 0
    def __call__(self, text, return_tensors="pt"):
        return {"input_ids": [1, 2, 3]}
    def decode(self, ids, skip_special_tokens=True):
        return "hello world"

class StubModel:
    device = "cpu"
    def generate(self, **kwargs):
        return [[1, 2, 3, 4]]

def stub_ensure_loaded():
    mod.tokenizer = StubTokenizer()
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
    data = r.json()
    assert data["status"] == "success"
    assert isinstance(data["text"], str)
