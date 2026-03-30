# LALM 项目一键启动指南

本指南将帮助你从零开始运行整个 LALM 音频大模型演示系统，包括前端、Java 后端和 Python 模型服务（Mock 模式）。

## 1. 环境准备

确保你的机器已安装以下软件：
- **Node.js** (v16+): 用于运行前端
- **JDK** (v17+): 用于运行 Spring Boot 后端
- **Python** (v3.10+): 用于运行模型服务
- **MySQL** (可选): 默认使用 H2 内存数据库，如需持久化请安装 MySQL

## 2. 目录结构

```
web_system/
├── frontend/          # Vue3 前端
├── model_service/     # Python 模型服务
│   ├── main.py        # FastAPI 入口
│   └── backend_java/  # Spring Boot 后端 (源码)
```

## 3. 快速启动步骤

请打开三个独立的终端窗口，分别执行以下命令：

### 终端 1: 启动 Python 模型服务 (Mock)

此服务模拟大模型推理，无需显卡即可运行。

```powershell
# 进入目录
cd "d:\Suda\毕设 - 副本\web_system\model_service"

# 安装依赖 (首次运行)
pip install fastapi uvicorn numpy

# 启动服务 (监听 8001 端口)
python main.py
```
> **成功标志**: 看到 `Uvicorn running on http://0.0.0.0:8001`

---

### 终端 2: 启动 Java 后端

此服务负责业务逻辑和请求转发。

```powershell
# 进入目录
cd "d:\Suda\毕设 - 副本\web_system\model_service\backend_java"

# 运行 Spring Boot (Windows)
.\mvnw spring-boot:run
# 或者如果你安装了 Maven
mvn spring-boot:run
```
> **注意**: 如果 `mvnw` 不可用，请直接在 IDE (IntelliJ IDEA) 中打开 `backend_java` 目录并运行 `LalmApplication` 类。
> **成功标志**: 看到 `Started LalmApplication in ... seconds`，监听 `8080` 端口。

---

### 终端 3: 启动前端

此服务提供用户界面。

```powershell
# 进入目录
cd "d:\Suda\毕设 - 副本\web_system\frontend"

# 安装依赖 (首次运行)
npm install

# 启动开发服务器
npm run dev
```
> **成功标志**: 看到 `Local: http://localhost:5173/`

## 4. 验证运行

1. 打开浏览器访问 `http://localhost:5173`。
2. 登录页面：输入任意用户名/密码 (例如 `admin` / `123456`) 即可登录 (Mock 模式)。
3. 进入 **Dashboard** 页面。
4. 点击录音按钮或上传音频文件。
5. 观察界面：
   - 状态应变为 "正在思考..."。
   - 几秒后，应显示 "【测试模式】我收到了你的语音..." 的回答。
   - 系统会自动播放一段生成的测试音频 (440Hz 正弦波)。

## 5. 常见问题

- **后端连接失败**: 检查前端 `src/config/api.js` 中的 `API_BASE` 是否为 `http://localhost:8080`。
- **模型服务连接失败**: 检查 Java 后端 `application.properties` 中的 `python.model.server.url` 是否为 `http://127.0.0.1:8001/inference`。
- **权限不足**: 如果 PowerShell 提示权限错误，请以管理员身份运行终端。

## 6. 切换到真实大模型

当你准备好真实环境 (显卡 + 模型文件) 后：
1. 修改 `web_system/model_service/main.py`:
   - 设置 `USE_MOCK_MODEL = False`
   - 修改 `MODEL_PATH` 为你本地的真实模型路径
2. 确保安装了 `torch`, `transformers`, `soundfile` 等依赖。
3. 重启 Python 服务即可。
