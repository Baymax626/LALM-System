import json
import sys
import base64
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "http://127.0.0.1:8001"

def post_json(path, data):
    body = json.dumps(data).encode("utf-8")
    req = Request(f"{BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req) as r:
        return r.read().decode("utf-8")

def post_file(path, filename, field="audio_file"):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    crlf = "\r\n"
    with open(filename, "rb") as f:
        file_data = f.read()
    body = []
    body.append(f"--{boundary}{crlf}")
    body.append(f'Content-Disposition: form-data; name="{field}"; filename="{filename}"{crlf}')
    body.append(f"Content-Type: audio/wav{crlf}{crlf}")
    body.append(file_data)
    body.append(crlf.encode("utf-8"))
    body.append(f"--{boundary}--{crlf}")
    body_bytes = b"".join(x if isinstance(x, bytes) else x.encode("utf-8") for x in body)
    req = Request(f"{BASE}{path}", data=body_bytes, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urlopen(req) as r:
        return r.read().decode("utf-8")

def main():
    try:
        resp_tts = post_json("/tts", {"prompt": "你好，我是通义千问，正在用语音回复你"})
        print(resp_tts)
        data = json.loads(resp_tts)
        b64 = data.get("audio_base64")
        if b64:
            with open("/data/baymax/llm_server/tts_from_api.wav", "wb") as f:
                f.write(base64.b64decode(b64))
        resp_asr = post_file("/asr", "/data/baymax/llm_server/tts_from_api.wav")
        print(resp_asr)
    except (HTTPError, URLError) as e:
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
