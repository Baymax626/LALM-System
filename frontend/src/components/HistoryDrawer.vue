<template>
  <a-drawer
    title="历史记录"
    placement="right"
    :open="visible"
    width="400"
    @close="$emit('close')"
  >
    <a-list item-layout="vertical" :data-source="historyItems">
      <template #renderItem="{ item, index }">
        <a-list-item class="history-item" @click="$emit('select-item', item)">
          <a-list-item-meta>
            <template #title>
              <div class="item-header">
                <span class="time">{{ item.timestamp }}</span>
                <a-tag :color="getDifficultyColor(item.difficulty)">
                  {{ item.difficulty }}
                </a-tag>
              </div>
            </template>
            <template #description>
              <div class="item-stats">
                <span>⏱️ {{ item.duration }}s</span>
                <span>🧩 {{ item.steps }} 步</span>
              </div>
            </template>
          </a-list-item-meta>
          <div class="answer-preview">
            {{ item.answer.substring(0, 60) }}...
          </div>
        </a-list-item>
      </template>
      <div v-if="historyItems.length === 0" class="empty-history">
        暂无历史记录
      </div>
    </a-list>
  </a-drawer>
</template>

<script setup>
defineProps({
  visible: Boolean,
  historyItems: Array
});

defineEmits(['close', 'select-item']);

const getDifficultyColor = (diff) => {
  if (diff === '简单') return 'green';
  if (diff === '中等') return 'orange';
  return 'red';
};
</script>

<style scoped>
.history-item {
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 12px;
  border: 1px solid #f0f0f0;
  background: white;
}
.history-item:hover {
  background: #f8fafc;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #e2e8f0;
}
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.time {
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 500;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.item-stats {
  display: flex;
  gap: 16px;
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 4px;
}
.answer-preview {
  margin-top: 12px;
  color: #475569;
  font-size: 0.9rem;
  line-height: 1.5;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 10px 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  position: relative;
}
.answer-preview::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #94a3b8;
  border-radius: 3px 0 0 3px;
}
.empty-history {
  padding: 40px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 0.9rem;
}
</style>
