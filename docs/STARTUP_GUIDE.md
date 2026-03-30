# LALM 全栈系统启动指南

本文档详细介绍了如何从零启动服务器端模型、本地后端和本地前端，并建立 SSH 隧道进行联调。

## 📋 架构概览

1.  **服务器端 (Server)**: 运行 Python FastAPI 大模型服务 (GPU 4)。
2.  **本地端 (Local)**:
    *   **SSH 隧道**: 将服务器端口 `8001` 映射到本地 `localhost:8001`。
    *   **后端 (Java)**: Spring Boot 应用，连接本地模型端口。
    *   **前端 (Vue)**: Web 界面，连接本地后端。

---

## 🚀 第一步：启动服务器端模型服务

**环境**: 远程 GPU 服务器 (10.10.80.60)
**操作**: SSH 终端

**⚠️ 预置条件**: 确保服务器已安装 `ffmpeg` (用于处理不同格式的音频)。
- 如果未安装，请执行：`conda install -c conda-forge ffmpeg -y` 或 `sudo apt install ffmpeg -y`

1.  **登录服务器**:
    ```bash
    ssh baymax@10.10.80.60
    # 密码: !BAIyang509626
    ```

2.  **启动服务命令**:
    复制并执行以下命令块：
    ```bash
    cd /data/baymax/毕设/web_system/llm_server
    source ~/.bashrc
    conda activate lalm_py
    
    # 强制杀死旧进程
    fuser -k 8001/tcp 
    
    # 在 GPU 4 上启动 (后台运行)
    nohup env CUDA_VISIBLE_DEVICES=4 python llm_fastapi_omni.py > server.log 2>&1 &
    
    # 查看日志确认启动 (按 Ctrl+C 退出查看)
    tail -f server.log
    ```
    *看到 `Uvicorn running on http://0.0.0.0:8001` 即为成功。*

---

## 🚇 第二步：建立 SSH 隧道

**环境**: 本地电脑 (PowerShell / Terminal)
**目的**: 让本地程序能访问服务器内网端口

1.  **开启隧道**:
    打开一个新的终端窗口，执行：
    ```powershell
    ssh -N -L 8001:127.0.0.1:8001 baymax@10.10.80.60
    ```
    *   输入密码后，光标会悬停不动（这是正常的，不要关闭此窗口）。*

2.  **触发模型加载** (隧道建立后执行一次即可):
    打开另一个本地终端，执行：
    ```powershell
    curl -Method POST http://localhost:8001/load
    ```
    *等待返回 `{"status":"success","loaded":true}`。*

---

## ☕ 第三步：启动本地后端 (Java)

**环境**: 本地电脑 (PowerShell)
**注意**: 如果电脑内存不足 (<16GB)，请跳过此步，直接使用前端连接模型（见第四步的特殊说明）。

1.  **启动命令**:
    ```powershell
    cd "d:\Suda\毕设 - 副本\web_system\backend_java"
    # 限制内存启动 (防止 OOM)
    $env:MAVEN_OPTS="-Xmx256m"
    mvn spring-boot:run
    ```
    *等待看到 `Started LalmApplication in ... seconds`。*

---

## 🌐 第四步：启动本地前端 (Vue)

**环境**: 本地电脑 (PowerShell)

1.  **启动命令**:
    ```powershell
    cd "d:\Suda\毕设 - 副本\web_system\frontend"
    npm run dev
    ```

2.  **访问页面**:
    浏览器打开 [http://localhost:5173](http://localhost:5173)

---

## ⚠️ 常见问题与特殊模式

### 内存不足模式 (当前配置)
如果你的电脑无法启动 Java 后端，我们已经修改了前端代码，使其**绕过 Java 后端**，直接通过 SSH 隧道连接模型。

*   **操作**: 只需要完成 **第一步**、**第二步** 和 **第四步**。
*   **效果**: 前端页面功能正常，只是没有用户鉴权和历史记录存储功能。

### 端口占用
如果服务器报错 `Address already in use`，请重新执行第一步中的 `fuser -k 8001/tcp`。

### 连接失败 / Connection refused
如果你看到 `Failed to call model server: Connection refused: connect` 或类似的报错：

1.  **检查 SSH 隧道**：确保开启隧道的 PowerShell 窗口仍然处于打开状态。如果窗口已关闭或显示 `Connection closed`，请重新执行：
    ```powershell
    ssh -v -N -L 8001:127.0.0.1:8001 baymax@10.10.80.60
    ```
    *(注意：建议使用 `-v` 参数查看详细连接日志，并确保本地端口与 Java 配置的 `8001` 一致。)*
2.  **检查服务器模型服务**：确认服务器上的 Python 服务是否已崩溃。
    - 登录服务器执行：`netstat -tulpn | grep 8001`
    - 若无输出，需重新执行“第一步”中的启动命令。
3.  **验证本地端口**：在本地执行 `Test-NetConnection -ComputerName 127.0.0.1 -Port 8001` 确认 `TcpTestSucceeded` 是否为 `True`。
4.  **触发加载**：隧道建立后，手动执行一次 `curl.exe -X POST http://localhost:8001/load` 确保显存分配成功。

---

## 🧠 深度思考功能说明 (Deep Thinking)

本系统集成了 Qwen2.5-Omni 的思维链 (CoT) 展示功能，前端会实时解析并展示以下四个阶段：

1.  **意图识别**: 分析用户语音输入的背后意图。
2.  **知识检索**: 提取问题中的关键实体并模拟/执行知识检索。
3.  **逻辑推演**: 展示模型一步步思考的过程。
4.  **最终结论**: 汇总推理结果并给出最终答案。

**数据流向**:
`前端 (AudioBlob)` -> `Java 后端 (/api/inference)` -> `Python 模型 (/inference)` -> `返回结构化 JSON` -> `前端解析并渲染`。

---

## 🧪 MMAU 测试与评估

### 前置要求
- 服务器模型服务已就绪（见本文“第一步”），并可通过直连或 SSH 隧道访问。
- 本地具备 Python 环境并安装 `requests`、`tqdm`。
- MMAU 测试 JSON 位于 `MMAU-main/` 目录（已包含 `mmau-test-mini.json` 与 `mmau-test.json`）。
- 本地已准备对应音频目录（将 zip 解压到本地，如 `D:\Download\test-mini-audios`）。

### 配置
1. 打开项目根目录下的 `run_mmau_inference.py`，检查并设置：
   - `API_URL`：指向可访问的模型推理接口  
     - 直连服务器示例：`http://SERVER_IP:8001/inference`  
     - 经 SSH 隧道示例：`http://127.0.0.1:8002/inference`
   - `AUDIO_ROOT`：指向本地音频解压目录，如 `D:\Download\test-mini-audios`
   - `INPUT_FILE`/`OUTPUT_FILE`：默认指向 `MMAU-main/mmau-test-mini.json` 与对应结果文件
   - `TEST_LIMIT`：调试时可设小（如 10），完整跑可以去掉限制或设为更大

### 批量推理
```powershell
cd "d:\Suda\毕设 - 副本\web_system"
python run_mmau_inference.py
```
- 运行过程中会对每条样本调用远程模型接口并写入结果到 `MMAU-main/mmau-test-mini-results.json`（或你设置的输出文件）。

### 评估
```powershell
python MMAU-main/evaluation.py --input "MMAU-main/mmau-test-mini-results.json"
```
- 脚本会打印 task-wise、difficulty-wise、sub-category-wise 与总准确率。

### 切换到 9000 条大集
- 将 `run_mmau_inference.py` 中的 `INPUT_FILE` 与 `OUTPUT_FILE` 切换为 `MMAU-main/mmau-test.json` 对应路径。
- 同时将 `AUDIO_ROOT` 指向完整测试集的音频目录。

### 常见问题
- 连接失败：确认 `API_URL` 与路由名称一致（`/inference` 或 `/generate`），以及 SSH 隧道是否仍在运行。
- 找不到音频：确认 `AUDIO_ROOT` 目录正确且文件名与样本中的 `audio_id`/`audio_path` 的 basename 一致。
- 超时或慢：适当增大超时时间、降低 `TEST_LIMIT`、或先用 mini 集验证链路。
