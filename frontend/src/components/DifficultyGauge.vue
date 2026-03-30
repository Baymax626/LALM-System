<template>
  <div class="difficulty-gauge" :class="{ 'gauge-small': size === 'small' }">
    <h3 v-if="size !== 'small'">难度感知</h3>
    <div class="gauge-container">
      <a-progress 
        type="dashboard" 
        :percent="score" 
        :status="progressStatus"
        :stroke-color="strokeColor"
        :width="size === 'small' ? 80 : 180"
      >
        <template #format="percent">
          <div class="gauge-content">
            <div class="score" :style="{ fontSize: size === 'small' ? '1.1rem' : '2rem' }">
              {{ Math.round(percent) }}
            </div>
            <div v-if="size !== 'small'" class="label">{{ status }}</div>
          </div>
        </template>
      </a-progress>
      <div v-if="size === 'small'" class="small-label" :style="{ color: strokeColor }">
        {{ status }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  score: {
    type: Number,
    default: 0
  },
  status: {
    type: String,
    default: 'Waiting'
  },
  size: {
    type: String,
    default: 'default'
  }
});

const progressStatus = computed(() => {
  if (props.status === 'Waiting') return 'normal';
  return 'active';
});

const strokeColor = computed(() => {
  if (props.score < 40) return '#52c41a'; // Green for Easy
  if (props.score < 75) return '#faad14'; // Orange for Medium
  return '#f5222d'; // Red for Hard
});
</script>

<style scoped>
.difficulty-gauge {
  text-align: center;
}
.gauge-container {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.gauge-small .gauge-container {
  margin-top: 0;
  flex-direction: row;
  gap: 10px;
}
.gauge-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.score {
  font-weight: bold;
}
.label {
  font-size: 1rem;
  color: #888;
}
.small-label {
  font-size: 0.9rem;
  font-weight: bold;
}
</style>
