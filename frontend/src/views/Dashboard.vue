<template>
  <div class="auth-page">
    <div class="bg">
      <div class="gradient"></div>
      <div class="grid"></div>
      <div class="blobs">
        <span class="blob b1"></span>
        <span class="blob b2"></span>
        <span class="blob b3"></span>
      </div>
    </div>
  <a-layout style="min-height: 100vh" class="page-layout">
    <a-layout-header class="header">
      <div class="logo">
         LALM
      </div>
      <div class="header-right">
        <span v-if="user" style="margin-right: 16px; color: white">欢迎, {{ user.username }}</span>
        <a-button type="text" class="history-btn" @click="showHistory = true">
          历史记录
        </a-button>
        <a-button type="link" danger @click="logout">退出</a-button>
      </div>
    </a-layout-header>
    <a-layout>
      <a-layout-sider width="350" theme="light" class="sider">
        <div class="sider-content">
          <!-- 提问区卡片 -->
          <div class="sider-card input-card">
            <div class="card-header">
              <span class="title">交互提问</span>
            </div>
            <div class="voice-section">
              <AudioInput @audio-ready="handleAudioReady" @reset="handleReset" />
              <div v-if="asrText" class="asr-preview-mini">
                <div class="label">识别结果:</div>
                <div class="text">{{ asrText }}</div>
              </div>
            </div>
            <div class="text-section">
              <a-textarea 
                v-model:value="userInputText" 
                placeholder="在此输入文字补充 (可选)..." 
                :auto-size="{ minRows: 2, maxRows: 4 }"
                allow-clear 
                class="compact-textarea"
              />
            </div>
          </div>

          <!-- 模型设置卡片 -->
          <div class="sider-card settings-card">
            <div class="card-header">
              <span class="title">系统配置</span>
            </div>
             <a-form layout="vertical" class="compact-form">
               <a-form-item label="推理模型">
                 <a-select v-model:value="selectedModel" size="small" style="width: 100%" @change="handleModelChange">
                   <a-select-option value="lalm-7b">LALM-7B-Adaptive</a-select-option>
                   <a-select-option value="lalm-13b">LALM-13B-Adaptive</a-select-option>
                 </a-select>
               </a-form-item>
               <div class="switch-row">
                 <span>推理自适应</span>
                 <a-switch v-model:checked="isAdaptive" size="small" @change="handleAdaptiveChange" />
               </div>
               <div class="adaptive-tip">
                 <small>{{ isAdaptive ? '已开启难度感知优化' : '已锁定固定推理模式' }}</small>
               </div>
             </a-form>
          </div>
        </div>
      </a-layout-sider>
      <a-layout-content class="content">
        <div class="dashboard">
           <div class="dashboard-header">
             <h2>推理演示看板</h2>
             <div class="header-actions">
               <a-button v-if="finalAnswer" @click="exportReport">📥 导出报告</a-button>
               <div class="stats-bar" v-if="finalAnswer">
                 <a-tag color="blue">耗时: {{ stats.time }}s</a-tag>
                 <a-tag color="orange">难度: {{ stats.difficulty }}</a-tag>
               </div>
             </div>
           </div>

           <!-- 推理流程步骤条 -->
           <div class="inference-flow">
             <a-steps :current="currentStageIndex" size="small">
               <a-step title="意图识别" description="分析核心意图" />
               <a-step title="知识检索" description="获取背景知识" />
               <a-step title="逻辑推演" description="进行深度思考" />
               <a-step title="最终结论" description="生成回答内容" />
             </a-steps>
           </div>
           
           <div v-if="asrText" class="asr-box">
             <div class="asr-label">语音识别内容 (ASR):</div>
             <div class="asr-content">{{ asrText }}</div>
           </div>

           <a-divider />
           <ReasoningDisplay 
            :raw-text="rawText"
            :final-answer="finalAnswer" 
            :is-thinking="isThinking"
            @play-tts="playTTS"
          />

           <div v-if="finalAnswer && !isThinking" class="feedback-section">
             <a-divider>{{ feedbackSubmitted ? '感谢您的评价！' : '您对本次推理结果满意吗？' }}</a-divider>
             <div class="feedback-buttons" v-if="!feedbackSubmitted">
               <a-button @click="submitFeedback(5)" type="text" class="feedback-btn like">
                 准确且专业
               </a-button>
               <a-button @click="submitFeedback(1)" type="text" class="feedback-btn dislike">
                 存在偏差
               </a-button>
             </div>
             <div v-else class="feedback-result">
               <a-tag :color="feedbackRating === 5 ? 'success' : 'error'">
                 {{ feedbackRating === 5 ? '已评价：准确且专业' : '已评价：存在偏差' }}
               </a-tag>
             </div>
           </div>
        </div>
      </a-layout-content>
    </a-layout>
    <a-layout-footer class="footer">
      LALM Reasoner ©2025
    </a-layout-footer>

    <HistoryDrawer 
      :visible="showHistory" 
      :history-items="history"
      @close="showHistory = false"
      @select-item="restoreHistory"
    />
  </a-layout>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import AudioInput from '../components/AudioInput.vue';
import DifficultyGauge from '../components/DifficultyGauge.vue';
import ReasoningDisplay from '../components/ReasoningDisplay.vue';
import HistoryDrawer from '../components/HistoryDrawer.vue';
import { message } from 'ant-design-vue';
import { API_BASE } from '../config/api';

const router = useRouter();
const user = ref(null);

onMounted(() => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    user.value = JSON.parse(userStr);
  } else {
    router.push('/login');
  }
});

const logout = () => {
  localStorage.removeItem('user');
  router.push('/login');
};

const isAdaptive = ref(true);
const selectedModel = ref('lalm-7b');
const difficultyScore = ref(0);
const difficultyStatus = ref('等待中'); // Waiting, Easy, Medium, Hard
const userInputText = ref('');
const currentStageIndex = ref(-1);

const asrText = ref('');
const rawText = ref(''); // Add this to store the full reasoning text
const reasoningSteps = ref([]);
const reasoningRewards = ref([]);
const finalAnswer = ref('');
const isThinking = ref(false);
const feedbackSubmitted = ref(false);
const feedbackRating = ref(0);

// History & Stats
const showHistory = ref(false);
const history = ref([
  {
    id: 1,
    timestamp: '2024-03-27 10:30',
    difficulty: '中等',
    duration: 12.5,
    steps: 4,
    asr: '我想听一下关于贝多芬月光奏鸣曲的第一乐章分析。',
    answer: '【意图识别】\n用户希望了解贝多芬《月光奏鸣曲》第一乐章的专业分析。\n\n【知识检索】\n《月光奏鸣曲》（Op. 27 No. 2）作于1801年。第一乐章为持续的慢板，采用三连音节奏贯穿始终。\n\n【逻辑推演】\n该乐章的情感基调忧郁而深沉，通过低音部的稳定和高音部的沉思状旋律形成了极强的感染力。\n\n【最终结论】\n这是一首典型的浪漫主义早期钢琴作品，展现了贝多芬对情感表达的极致追求。',
    rawText: '【意图识别】\n用户希望了解贝多芬《月光奏鸣曲》第一乐章的专业分析。\n\n【知识检索】\n《月光奏鸣曲》（Op. 27 No. 2）作于1801年。第一乐章为持续的慢板，采用三连音节奏贯穿始终。\n\n【逻辑推演】\n该乐章的情感基调忧郁而深沉，通过低音部的稳定和高音部的沉思状旋律形成了极强的感染力。\n\n【最终结论】\n这是一首典型的浪漫主义早期钢琴作品，展现了贝多芬对情感表达的极致追求。'
  },
  {
    id: 2,
    timestamp: '2024-03-27 11:15',
    difficulty: '容易',
    duration: 5.2,
    steps: 4,
    asr: '今天天气怎么样？',
    answer: '【最终结论】\n今天天气晴朗，气温在15-22摄氏度之间，非常适合户外活动。',
    rawText: '【意图识别】\n查询天气信息。\n\n【最终结论】\n今天天气晴朗，气温在15-22摄氏度之间，非常适合户外活动。'
  },
  {
    id: 3,
    timestamp: '2024-03-26 15:20',
    difficulty: '困难',
    duration: 25.8,
    steps: 4,
    asr: '解释一下量子纠缠的基本原理。',
    answer: '【最终结论】\n量子纠缠是指两个或多个粒子在相互作用后，其量子态无法被独立描述，而是作为一个整体存在的现象。',
    rawText: '【意图识别】\n科学知识科普。\n\n【知识检索】\n量子力学基本概念。\n\n【逻辑推演】\n非定域性特征分析。\n\n【最终结论】\n量子纠缠是指两个或多个粒子在相互作用后，其量子态无法被独立描述，而是作为一个整体存在的现象。'
  }
]);
const stats = reactive({ time: 0, difficulty: 0 });

const handleModelChange = (value) => {
  console.log('Model changed to:', value);
  // 这里预留后端接口：可以根据选择的模型调整 API 请求参数
  message.info(`已切换至模型: ${value}`);
};

const handleAdaptiveChange = (checked) => {
  console.log('Adaptive mode changed to:', checked);
  // 这里预留后端接口：发送给模型服务，决定是否开启动态深度推理
  message.info(`自适应模式已${checked ? '开启' : '关闭'}`);
};

const handleReset = () => {
  difficultyScore.value = 0;
  difficultyStatus.value = '等待中';
  currentStageIndex.value = -1;
  asrText.value = '';
  rawText.value = ''; // Reset raw text
  reasoningSteps.value = [];
  reasoningRewards.value = [];
  finalAnswer.value = '';
  isThinking.value = false;
  feedbackSubmitted.value = false;
  feedbackRating.value = 0;
  stats.time = 0;
  stats.difficulty = 0;
};

const handleAudioReady = async (audioBlob) => {
  handleReset();
  isThinking.value = true;
  message.loading('正在启动深度推理分析...', 1);

  // 启动一个模拟的“思考中”动画，避免界面僵死
  const thinkingInterval = setInterval(() => {
    if (!isThinking.value) {
      clearInterval(thinkingInterval);
      return;
    }
    reasoningSteps.value.push("Java 后端正在调度 Python 模型进行推理...");
    reasoningRewards.value.push(0.5);
  }, 2000);

  // 开始分步推理流程
  try {
    rawText.value = "";
    finalAnswer.value = "";
    
    let currentContext = "";
    const stagesToRun = [
      { id: 1, name: '意图识别' },
      { id: 2, name: '知识检索' },
      { id: 3, name: '逻辑推演' },
      { id: 4, name: '最终结论' }
    ];

    for (const step of stagesToRun) {
      console.log(`Starting Stage ${step.id}: ${step.name}`);
      currentStageIndex.value = step.id - 1;
      
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');
      formData.append('prompt', userInputText.value || "请分析这段语音内容并回答。");
      formData.append('stage', step.id);
      formData.append('context', currentContext);
      formData.append('model', selectedModel.value);
      formData.append('isAdaptive', isAdaptive.value);
      formData.append('username', user.value?.username || 'admin');

      const response = await fetch(`${API_BASE}/api/inference`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `${step.name} 失败，请重试`);
      }

      const res = await response.json();
      const stageResult = res.data;
      
      if (!stageResult) {
        throw new Error(`${step.name} 返回数据为空`);
      }

      // 更新 ASR 文字（仅在第一步获取）
      if (step.id === 1 && stageResult.asr_text) {
        asrText.value = stageResult.asr_text;
      }

      // 更新统计数据与难度
      if (stageResult.difficulty_score !== undefined) {
        difficultyScore.value = stageResult.difficulty_score;
        stats.difficulty = stageResult.difficulty_score;
        
        if (difficultyScore.value < 30) difficultyStatus.value = '容易';
        else if (difficultyScore.value < 70) difficultyStatus.value = '中等';
        else difficultyStatus.value = '困难';
      }
      
      if (stageResult.execution_time) {
        stats.time = (parseFloat(stats.time) + parseFloat(stageResult.execution_time)).toFixed(1);
      }

      // 更新 UI 展示（思维链）
      if (stageResult.text) {
        rawText.value += (rawText.value ? "\n\n" : "") + stageResult.text;
      }
      
      // 累加上下文供下一步使用
      if (stageResult.content) {
        currentContext += (currentContext ? "\n" : "") + stageResult.content;
      }

      // 如果是最后一步，处理结论和语音
      if (step.id === 4) {
        finalAnswer.value = stageResult.answer || stageResult.content;
        if (stageResult.audio_base64) {
          playAudio(stageResult.audio_base64);
        }
      }
    }

    message.success('深度推理完成');
  } catch (err) {
    console.error("Inference pipeline error:", err);
    message.error(err.message || '推理过程出错');
  } finally {
    isThinking.value = false;
    clearInterval(thinkingInterval);
  }
};

const playAudio = (base64) => {
  try {
    const audioSrc = `data:audio/wav;base64,${base64}`;
    const audio = new Audio(audioSrc);
    audio.play();
    message.success('播放模型回复语音');
  } catch (e) {
    console.error("Audio playback failed", e);
  }
};

const playTTS = () => {
  message.info('TTS 功能开发中');
};

const restoreHistory = (item) => {
    asrText.value = item.asr;
    finalAnswer.value = item.answer;
    rawText.value = item.rawText || item.answer;
    difficultyStatus.value = item.difficulty;
    stats.time = item.duration;
    
    // 映射难度状态到评分（模拟展示）
    const scoreMap = { '容易': 25, '中等': 55, '困难': 85 };
    difficultyScore.value = scoreMap[item.difficulty] || 0;

    message.success('已恢复历史记录详情');
    showHistory.value = false;
};

const exportReport = () => {
    if (!rawText.value) {
        message.warning('当前没有推理结果可供导出');
        return;
    }

    const timestamp = new Date().toLocaleString();
    const content = `# Qwen Omni 语音推理报告
导出时间: ${timestamp}

## 1. 语音识别 (ASR)
> ${asrText.value || '未提供输入'}

## 2. 难度感知
- **难度分值**: ${difficultyScore.value}
- **难度状态**: ${difficultyStatus.value}

## 3. 深度推理过程
${rawText.value}

## 4. 最终结论
${finalAnswer.value}

---
报告生成自：基于 Qwen2.5-Omni 深度思考的语音理解平台
`;

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `推理报告_${new Date().getTime()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    message.success('报告已成功导出为 Markdown 文件');
};

const submitFeedback = async (rating) => {
  feedbackSubmitted.value = true;
  feedbackRating.value = rating;
  try {
    const response = await fetch('http://127.0.0.1:8080/api/feedback/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        recordId: 1, // 这里可以从实际推理记录获取 ID
        rating: rating,
        comment: rating === 5 ? "满意" : "不满意"
      })
    });
    if (response.ok) {
      message.success('评价提交成功');
    }
  } catch (e) {
    console.error('Feedback submission error:', e);
    // 即使后端报错，前端也保留已评价状态
  }
};
</script>

<style scoped>
.feedback-section {
  margin-top: 32px;
  text-align: center;
  animation: fadeIn 0.8s ease-out;
}
.feedback-buttons {
  display: flex;
  justify-content: center;
  gap: 24px;
}
.feedback-btn {
  padding: 8px 16px;
  border-radius: 20px;
  transition: all 0.3s;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid #eee;
}
.feedback-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.like:hover { color: #52c41a; background: #f6ffed; border-color: #b7eb8f; }
.dislike:hover { color: #f5222d; background: #fff1f0; border-color: #ffa39e; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.auth-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}
.bg .gradient {
  position: absolute;
  inset: 0;
  background: radial-gradient(1200px 600px at 20% 20%, #e6f0ff 0%, transparent 60%),
              radial-gradient(1200px 600px at 80% 80%, #ffe9f0 0%, transparent 60%),
              linear-gradient(135deg, #eef2f7 0%, #dbe5ff 100%);
}
.bg .grid {
  position: absolute;
  inset: 0;
  opacity: 0.25;
  background-image: linear-gradient(rgba(255,255,255,.25) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.25) 1px, transparent 1px);
  background-size: 24px 24px;
}
.bg .blobs {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.blob {
  position: absolute;
  width: 300px;
  height: 300px;
  filter: blur(40px);
  border-radius: 50%;
  opacity: 0.35;
  animation: float 12s ease-in-out infinite;
}
.blob.b1 { background: #9ec5fe; top: 10%; left: 5%; }
.blob.b2 { background: #f3a0c0; top: 60%; left: 70%; animation-delay: 2s; }
.blob.b3 { background: #a0f0d0; top: 30%; left: 50%; animation-delay: 4s; }
@keyframes float {
  0%,100% { transform: translateY(0) translateX(0); }
  50% { transform: translateY(-20px) translateX(10px); }
}
.page-layout {
  position: relative;
  z-index: 1;
  background: transparent;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0,21,41,0.85);
  padding: 0 20px;
  color: white;
}
.logo {
  font-size: 1.2rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sider {
  backdrop-filter: saturate(1.1) blur(8px);
  background: rgba(255,255,255,0.8);
  border-right: 1px solid #f0f0f0;
}
.sider-content {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.content {
  padding: 24px;
  background: transparent;
}
.dashboard {
  backdrop-filter: saturate(1.1) blur(8px);
  background: rgba(255,255,255,0.75);
  padding: 24px;
  border-radius: 8px;
  min-height: 100%;
  box-shadow: 0 10px 30px rgba(69, 98, 147, 0.12);
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}
.history-btn {
  color: #ffffff !important;
}
.stats-bar {
  display: flex;
  gap: 10px;
}
.asr-box {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #1890ff;
  margin-bottom: 20px;
}
.asr-label {
  font-weight: bold;
  color: #666;
  margin-bottom: 5px;
}
.asr-content {
  font-size: 1.1rem;
}
.sider-card {
  background: rgba(255, 255, 255, 0.45);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(10px);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
.card-header .title {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}
.voice-section {
  margin-bottom: 16px;
}
.asr-preview-mini {
  margin-top: 12px;
  padding: 10px;
  background: rgba(24, 144, 255, 0.05);
  border-radius: 8px;
  font-size: 0.85rem;
}
.asr-preview-mini .label {
  color: #1890ff;
  font-weight: 500;
  margin-bottom: 2px;
}
.asr-preview-mini .text {
  color: #555;
  line-height: 1.4;
}
.text-section :deep(.ant-input) {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  border-color: rgba(0, 0, 0, 0.1);
  font-size: 0.9rem;
}
.compact-form :deep(.ant-form-item) {
  margin-bottom: 12px;
}
.compact-form :deep(.ant-form-item-label > label) {
  font-size: 0.85rem;
  color: #666;
}
.switch-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #666;
  margin-top: 4px;
}
.adaptive-tip {
  margin-top: 8px;
  color: #999;
  font-style: italic;
}
.inference-flow {
  background: rgba(255, 255, 255, 0.4);
  padding: 15px 25px;
  border-radius: 16px;
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}
.difficulty-summary {
  margin-top: 20px;
  animation: fadeIn 0.5s ease-out;
}
.summary-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  color: #666;
}
.summary-label {
  font-weight: 500;
}
.description {
  margin-top: 10px;
  color: #999;
  line-height: 1.5;
}
.footer {
  text-align: center;
  background: transparent;
  color: #8a93a2;
}
</style>
