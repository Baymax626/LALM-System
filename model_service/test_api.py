import requests

url = "http://127.0.0.1:8001/inference"
payload = {'prompt': '你好，测试一下'}
files = [
    ('audio_file', ('test.wav', b'fake audio content', 'audio/wav'))
]

try:
    print(f"正在发送 POST 请求到 {url} ...")
    response = requests.request("POST", url, data=payload, files=files)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
except Exception as e:
    print(f"请求失败: {e}")
