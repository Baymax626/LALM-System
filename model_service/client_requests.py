import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "http://127.0.0.1:8001"

def get(path):
    req = Request(f"{BASE}{path}", method="GET")
    with urlopen(req) as r:
        return r.read().decode("utf-8")

def post(path, data=None):
    body = json.dumps(data or {}).encode("utf-8")
    req = Request(f"{BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req) as r:
        return r.read().decode("utf-8")

def main():
    try:
        print(get("/routes"))
        print(get("/debug/info"))
        print(post("/load"))
        print(get("/health"))
        print(post("/generate", {"prompt": "你好，介绍一下你的能力"}))
    except (HTTPError, URLError) as e:
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
