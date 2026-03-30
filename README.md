# LALM-System: 基于 Qwen2.5-Omni 的深度思考语音理解平台

本项目是为本科生毕业设计开发的**基于 Qwen2.5-Omni 大模型的深度思考语音理解平台**（LALM 系统）。系统旨在通过结合先进的多模态大模型技术，实现具备逻辑推理、知识检索及情感分析能力的智能语音交互。

## 🌟 核心特性

- **多模态语音交互**：支持实时录音输入，通过 ASR 识别后由大模型进行深度语义解析。
- **深度思维链展示 (Chain of Thought)**：实时展示模型在生成答案前的思考过程，涵盖意图识别、知识检索、逻辑推演等环节。
- **动态难度感知**：系统自动评估用户问题的复杂度，并根据难度动态调整推理深度。
- **前后端分离架构**：
  - **前端**：基于 Vue 3 + Ant Design Vue 构建，具备极简的卡片化交互界面。
  - **后端**：基于 Java Spring Boot 开发，负责业务逻辑处理、用户认证及推理历史持久化。
  - **模型服务**：基于 Python FastAPI 封装 Qwen2.5-Omni 模型，提供 ASR 及多模态推理接口。
- **数据持久化**：使用 MySQL/H2 存储用户提问记录、思维链详情及满意度反馈。

## 🛠️ 技术栈

- **Frontend**: Vue 3, Vite, Ant Design Vue, WaveSurfer.js
- **Backend**: Java 17+, Spring Boot 3.x, Spring Data JPA, MySQL/H2, Flyway
- **Model Service**: Python 3.10+, FastAPI, PyTorch, Transformers
- **LLM**: Qwen2.5-Omni

## 📂 项目结构

```text
├── frontend/               # Vue 3 前端代码
├── backend_java/           # Spring Boot 后端代码
├── model_service/          # Python 模型服务接口
├── MMAU-main/              # 多模态艺术理解评估工具
├── 毕业设计图表集/           # 系统设计相关图表 (UML, ER等)
├── docs/                   # 项目说明与开发指南
└── README.md               # 本文档
```

## 🚀 快速启动

1.  **启动模型服务**：进入 `model_service` 目录，安装依赖后运行 `python main.py`。
2.  **启动后端服务**：进入 `backend_java` 目录，配置数据库后运行 `mvn spring-boot:run`。
3.  **启动前端应用**：进入 `frontend` 目录，运行 `npm install` 随后执行 `npm run dev`。

## 📊 评估与测试
本项目包含了多模态艺术理解（MMAU）的基准测试代码及相关数据集，用于验证 Qwen2.5-Omni 模型在特定垂直领域的表现。

---
*本项目为毕业设计作品，仅供学习与交流使用。*
