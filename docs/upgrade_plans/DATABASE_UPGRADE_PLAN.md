# LALM 后端数据库升级建议文档

## 1. 当前数据库现状分析
目前系统中仅存在 `users` 表，用于管理基础的用户认证信息。
虽然项目文档中提到了 `InferenceRecord`（推理记录）的概念，但在目前的数据库脚本 (`V1__init.sql`) 和后端代码实体 (`entity/`) 中均未发现具体的实现。

## 2. 升级必要性
随着前端功能的增强，我们需要持久化以下数据，以支撑完整的业务逻辑：
- **历史记录查询**: 用户需要查看过去的语音识别 (ASR)、文字提问 (Prompt) 和模型回复。
- **深度思维链存储**: 记录模型完整的思考过程 (`raw_reasoning`)，方便后续分析和演示。
- **性能与难度评估**: 记录每次推理的耗时和系统评估的难度分值。
- **满意度反馈**: 存储用户对结果的满意度，作为模型优化的重要参考指标。

## 3. 建议新增数据表结构

### 3.1. 推理记录表 (`inference_records`)
用于存储每一次完整的推理交互。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `BIGINT` | 主键，自增 |
| `user_id` | `BIGINT` | 外键，关联 `users.id` |
| `asr_text` | `TEXT` | 语音识别出的原始内容 |
| `prompt_text` | `TEXT` | 用户输入的补充文字指令 |
| `raw_reasoning` | `TEXT` | 模型的完整深度思考过程 |
| `final_answer` | `TEXT` | 模型给出的最终答案 |
| `difficulty_score` | `INT` | 任务难度分值 (0-100) |
| `difficulty_status` | `VARCHAR(32)` | 难度状态 (容易/中等/困难) |
| `execution_time` | `DOUBLE` | 推理总耗时 (秒) |
| `created_at` | `DATETIME` | 创建时间 |

### 3.2. 用户反馈表 (`user_feedback`)
用于存储用户对特定推理记录的评价。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `BIGINT` | 主键，自增 |
| `record_id` | `BIGINT` | 外键，关联 `inference_records.id` |
| `rating` | `INT` | 评分 (5: 满意, 1: 不满意) |
| `comment` | `TEXT` | 评价内容 (如: "准确且专业") |
| `created_at` | `DATETIME` | 评价时间 |

## 4. 后端实体类 (Entity) 调整建议
- **新增 `InferenceRecord.java`**: 映射上述推理记录表，建立与 `User` 的 `ManyToOne` 关系。
- **新增 `UserFeedback.java`**: 映射反馈表，建立与 `InferenceRecord` 的 `OneToOne` 关系。

## 5. SQL 实现参考 (H2/MySQL 兼容)
```sql
-- 推理记录表
CREATE TABLE IF NOT EXISTS inference_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  asr_text TEXT,
  prompt_text TEXT,
  raw_reasoning TEXT,
  final_answer TEXT,
  difficulty_score INT,
  difficulty_status VARCHAR(32),
  execution_time DOUBLE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  record_id BIGINT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (record_id) REFERENCES inference_records(id)
);
```
