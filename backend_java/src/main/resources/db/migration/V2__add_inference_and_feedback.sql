-- V2: 新增推理记录表和反馈表

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
  CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  record_id BIGINT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_record FOREIGN KEY (record_id) REFERENCES inference_records(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
