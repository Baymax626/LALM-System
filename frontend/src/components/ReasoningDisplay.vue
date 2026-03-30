<template>
  <div class="reasoning-display">
    <div class="header">
      <div class="title-wrapper">
        <span class="pulse-dot" v-if="isThinking"></span>
        <h3>深度思维链 (Chain of Thought)</h3>
      </div>
      <div class="status-badge" :class="statusClass">
        {{ statusText }}
      </div>
    </div>

    <div class="cot-container">
      <a-steps direction="vertical" :current="currentStepIndex" size="small">
        <a-step v-for="(stage, index) in stages" :key="stage.id">
          <template #title>
            <span class="step-title" :class="{ 'active-title': index === currentStepIndex }">
              {{ stage.title }}
            </span>
          </template>
          <template #description>
            <div class="step-content-wrapper" v-if="stage.content || index === currentStepIndex">
              <div v-if="stage.content" class="step-text fade-in">
                {{ stage.content }}
              </div>
              <div v-else-if="index === currentStepIndex && isThinking" class="thinking-loader">
                <span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
              </div>
            </div>
          </template>
          <template #icon>
            <template v-if="stage.status === 'completed'">
              <check-circle-filled style="color: #52c41a" />
            </template>
            <template v-else-if="index === currentStepIndex && isThinking">
              <loading-outlined style="color: #1890ff" />
            </template>
            <template v-else>
              <div class="pending-dot"></div>
            </template>
          </template>
        </a-step>
      </a-steps>
    </div>

    <transition name="slide-up">
      <div v-if="finalAnswer" class="final-answer-section">
        <div class="final-header">
          <div class="final-title">
            <bulb-outlined /> 最终结论
          </div>
          <a-button type="primary" size="small" shape="round" @click="$emit('play-tts')">
            <template #icon><sound-outlined /></template>
            朗读结果
          </a-button>
        </div>
        <div class="final-content">{{ finalAnswer }}</div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { 
  CheckCircleFilled, 
  LoadingOutlined, 
  BulbOutlined, 
  SoundOutlined 
} from '@ant-design/icons-vue';

const props = defineProps({
  rawText: { type: String, default: '' },
  finalAnswer: { type: String, default: '' },
  isThinking: { type: Boolean, default: false },
  status: { type: String, default: 'idle' }
});

defineEmits(['play-tts']);

const stages = ref([
  { id: 'intent', title: '意图识别', content: '', status: 'pending' },
  { id: 'knowledge', title: '知识检索', content: '', status: 'pending' },
  { id: 'deduction', title: '逻辑推演', content: '', status: 'pending' },
  { id: 'conclusion', title: '最终结论', content: '', status: 'pending' }
]);

const currentStepIndex = computed(() => {
  const index = stages.value.findIndex(s => s.status === 'processing' || s.status === 'pending');
  return index === -1 ? stages.value.length - 1 : index;
});

watch(() => props.isThinking, (val) => {
  if (val) {
    // Reset stages when starting new thinking
    stages.value.forEach(s => {
      s.content = '';
      s.status = 'pending';
    });
    stages.value[0].status = 'processing';
  }
});

watch(() => props.rawText, (newText) => {
  if (!newText) return;
  
  const parseSection = (sectionName) => {
    const regex = new RegExp(`【${sectionName}】\\s*([\\s\\S]*?)(?=\\n*【|$)`);
    const match = newText.match(regex);
    return match ? match[1].trim() : '';
  };

  updateStageState('intent', parseSection('意图识别'));
  updateStageState('knowledge', parseSection('知识检索'));
  updateStageState('deduction', parseSection('逻辑推演'));
  updateStageState('conclusion', parseSection('最终结论')); 
});

const updateStageState = (id, content) => {
  const stage = stages.value.find(s => s.id === id);
  const index = stages.value.indexOf(stage);
  
  if (stage && content && stage.status !== 'completed') {
    stage.content = content;
    stage.status = 'completed';
    
    // Set next stage to processing
    if (index + 1 < stages.value.length) {
      stages.value[index + 1].status = 'processing';
    }
  }
};

const statusText = computed(() => {
  if (props.isThinking) return '深度推理中';
  if (props.finalAnswer) return '推理已完成';
  return '系统就绪';
});

const statusClass = computed(() => {
  if (props.isThinking) return 'status-processing';
  if (props.finalAnswer) return 'status-completed';
  return 'status-idle';
});
</script>

<style scoped>
.reasoning-display {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.05);
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.header {
  padding: 20px 24px;
  background: linear-gradient(to right, #fcfcfc, #f8f9fa);
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background-color: #1890ff;
  border-radius: 50%;
  box-shadow: 0 0 0 rgba(24, 144, 255, 0.4);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(24, 144, 255, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(24, 144, 255, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(24, 144, 255, 0); }
}

.header h3 {
  margin: 0;
  font-size: 17px;
  color: #1a1a1a;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.cot-container {
  padding: 30px 40px;
}

.step-title {
  font-size: 15px;
  color: #8c8c8c;
  font-weight: 600;
  transition: all 0.3s;
}

.active-title {
  color: #1890ff;
  font-size: 16px;
}

.step-content-wrapper {
  background: #f9f9fb;
  border-radius: 10px;
  padding: 12px 16px;
  margin-top: 8px;
  border-left: 3px solid #e8e8e8;
  transition: all 0.3s;
}

.active-title + .step-content-wrapper {
  border-left-color: #1890ff;
  background: #f0f7ff;
}

.step-text {
  font-size: 14px;
  color: #434343;
  line-height: 1.7;
  white-space: pre-wrap;
}

.thinking-loader {
  color: #1890ff;
  font-weight: bold;
}

.dot {
  animation: blink 1.4s infinite both;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0% { opacity: 0.2; }
  20% { opacity: 1; }
  100% { opacity: 0.2; }
}

.pending-dot {
  width: 8px;
  height: 8px;
  background: #d9d9d9;
  border-radius: 50%;
  margin: 8px auto;
}

.final-answer-section {
  margin: 0 24px 24px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f7ff 100%);
  border: 1px solid #bae7ff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.1);
}

.final-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.final-title {
  font-weight: 800;
  color: #0050b3;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.final-content {
  font-size: 15px;
  color: #262626;
  line-height: 1.8;
  font-weight: 500;
}

.status-badge {
  padding: 6px 16px;
  border-radius: 30px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-processing { background: #e6f7ff; color: #1890ff; border: 1px solid #91d5ff; }
.status-completed { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.status-idle { background: #f5f5f5; color: #8c8c8c; border: 1px solid #d9d9d9; }

.fade-in {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.slide-up-enter-active, .slide-up-leave-active {
  transition: all 0.4s ease;
}
.slide-up-enter-from, .slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
