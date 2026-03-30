<template>
  <div class="audio-input">
    <div class="waveform-wrapper">
      <!-- 录音完成后的波形回放 -->
      <div v-show="!isRecording && !isPaused && audioUrl" class="waveform-container" ref="waveformRef"></div>
      <!-- 录音过程中的实时波形 -->
      <canvas v-show="isRecording || isPaused" ref="visualizerRef" class="visualizer-canvas"></canvas>
      <!-- 初始状态的占位提示 -->
      <div v-if="!isRecording && !isPaused && !audioUrl" class="placeholder-wave">
        <div class="wave-line"></div>
        <div class="text">点击下方按钮开始录音</div>
      </div>
    </div>
    
    <div class="controls">
      <a-space direction="vertical" style="width: 100%">
        
        <!-- 按钮组区域 -->
        <div class="button-group">
          <!-- 初始状态：开始录音 -->
          <a-button 
            v-if="!isRecording && !isPaused && !audioUrl"
            type="primary" 
            danger 
            block
            class="record-btn"
            @click="startRecording"
          >
            <template #icon>
              <span class="btn-content">
                <span class="icon">🎤</span> 
                <span class="text">开始录音</span>
              </span>
            </template>
          </a-button>

          <!-- 录音中：暂停 -->
          <a-button 
            v-if="isRecording"
            type="primary" 
            warning
            block
            class="record-btn recording"
            @click="pauseRecording"
          >
            <template #icon>
              <span class="btn-content">
                <span class="icon recording-pulse">⏸️</span> 
                <span class="text">暂停录音 ({{ formatTime(recordingTime) }})</span>
              </span>
            </template>
          </a-button>

          <!-- 暂停中：继续录音 / 完成 / 删除 -->
          <div v-if="isPaused" class="paused-controls">
            <a-space size="middle" style="width: 100%; justify-content: center;">
              <a-button type="primary" shape="round" size="large" @click="resumeRecording">
                <template #icon>🔴</template> 继续录音
              </a-button>
              <a-button type="primary" shape="round" size="large" style="background-color: #52c41a" @click="stopRecording">
                <template #icon>✅</template> 完成
              </a-button>
            </a-space>
            <div class="timer-display">已录制: {{ formatTime(recordingTime) }}</div>
          </div>

          <!-- 录音完成：重录 -->
          <div v-if="audioUrl" class="finished-controls">
             <a-button type="dashed" block danger @click="discardRecording">
               <template #icon>🗑️</template> 删除当前录音并重新开始
             </a-button>
          </div>

        </div>

        <a-button 
          v-if="!isRecording && !isPaused"
          block
          @click="chooseAudio"
        >📁 上传音频文件</a-button>
      </a-space>
    </div>
    
    <div v-if="audioUrl" class="audio-player">
      <audio :src="audioUrl" controls style="width: 100%"></audio>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import WaveSurfer from 'wavesurfer.js';
import { message } from 'ant-design-vue';

const emit = defineEmits(['audio-ready', 'reset']);

const waveformRef = ref(null);
const visualizerRef = ref(null);
const wavesurfer = ref(null);

// State
const isRecording = ref(false);
const isPaused = ref(false);
const audioChunks = ref([]); // Now stores float32 arrays
const audioUrl = ref(null);

// Timer & Visualizer state
const recordingTime = ref(0);
let timerInterval = null;
let animationFrameId = null;
let audioContext = null;
let analyser = null;
let dataArray = null;
let source = null;
let stream = null; 
let processor = null; // ScriptProcessorNode

// WAV Encoding Helper
const floatTo16BitPCM = (output, offset, input) => {
  for (let i = 0; i < input.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
};

const writeString = (view, offset, string) => {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
};

const encodeWAV = (samples, sampleRate) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  
  // RIFF chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  
  // fmt sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  
  // data sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  
  floatTo16BitPCM(view, 44, samples);
  
  return new Blob([view], { type: 'audio/wav' });
};

const flattenAudioChunks = (chunks) => {
  let length = 0;
  chunks.forEach(chunk => length += chunk.length);
  const result = new Float32Array(length);
  let offset = 0;
  chunks.forEach(chunk => {
    result.set(chunk, offset);
    offset += chunk.length;
  });
  return result;
};

onMounted(() => {
  initWavesurfer();
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas);
  if (wavesurfer.value) wavesurfer.value.destroy();
  stopTimer();
  stopVisualizer();
  cleanupAudioResources();
});

const cleanupAudioResources = () => {
    if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
        processor = null;
    }
    if (source) {
        source.disconnect();
        source = null;
    }
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    // We keep AudioContext alive
};

// ... (keep existing resizeCanvas, initWavesurfer, formatTime, timer logic)

const resizeCanvas = () => {
  if (visualizerRef.value) {
    visualizerRef.value.width = visualizerRef.value.offsetWidth || 600;
    visualizerRef.value.height = 120;
  }
};

const initWavesurfer = () => {
  wavesurfer.value = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: '#1890ff',
    progressColor: '#0050b3',
    cursorColor: '#333',
    barWidth: 2,
    barRadius: 3,
    height: 120,
    responsive: true,
  });
};

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const startTimer = () => {
  stopTimer();
  timerInterval = setInterval(() => {
    recordingTime.value++;
  }, 1000);
};

const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
};

// ... (Updated startVisualizer logic)

const startVisualizer = (audioStream) => {
  if (!visualizerRef.value) return;
  
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }

  analyser = audioContext.createAnalyser();
  // IMPORTANT: Create source here but store it to disconnect later
  const mediaStreamSource = audioContext.createMediaStreamSource(audioStream);
  source = mediaStreamSource;
  
  source.connect(analyser);
  
  // Setup Recording Processor (ScriptProcessor as simple fallback)
  // bufferSize 4096, 1 input channel, 1 output channel
  processor = audioContext.createScriptProcessor(4096, 1, 1);
  
  processor.onaudioprocess = (e) => {
      if (!isRecording.value) return;
      const inputData = e.inputBuffer.getChannelData(0);
      // Clone data because inputBuffer is reused
      audioChunks.value.push(new Float32Array(inputData));
  };
  
  // We need to connect processor to destination or it won't fire (in some browsers)
  // But we don't want to hear it, so connect to a mute gain or just rely on modern behavior.
  // Ideally: Source -> Processor -> Destination
  source.connect(processor);
  processor.connect(audioContext.destination); // Careful about feedback if not muted, but this is mic input

  // Visualizer setup
  analyser.fftSize = 2048; 
  const bufferLength = analyser.frequencyBinCount;
  dataArray = new Uint8Array(bufferLength);
  
  const canvas = visualizerRef.value;
  const ctx = canvas.getContext('2d');
  
  const draw = () => {
    if (!isRecording.value && !isPaused.value) return; 
    
    animationFrameId = requestAnimationFrame(draw);
    
    if (isPaused.value) return;

    analyser.getByteTimeDomainData(dataArray);
    
    ctx.fillStyle = '#f0f2f5'; 
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#ff4d4f'; 
    ctx.beginPath();
    
    const sliceWidth = canvas.width * 1.0 / bufferLength;
    let x = 0;
    
    for(let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0; 
      const y = v * canvas.height / 2;
      if(i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      x += sliceWidth;
    }
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
  };
  
  draw();
};

const stopVisualizer = () => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
};

// --- Recording Logic ---

const startRecording = async () => {
  // Proactively clear UI even before mic permission is granted
  emit('reset');
  
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Reset state
    audioChunks.value = [];
    isRecording.value = true;
    isPaused.value = false;
    audioUrl.value = null; 
    
    startTimer();
    // This sets up both visualizer AND the recording processor
    startVisualizer(stream);
    
  } catch (err) {
    console.error("Error accessing microphone:", err);
    message.error("无法访问麦克风");
  }
};

const pauseRecording = () => {
    if (isRecording.value) {
        if (audioContext && audioContext.state === 'running') {
            audioContext.suspend();
        }
        isRecording.value = false;
        isPaused.value = true;
        stopTimer();
    }
};

const resumeRecording = () => {
    if (isPaused.value) {
        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume();
        }
        isRecording.value = true;
        isPaused.value = false;
        startTimer();
        
        // Restart visualizer loop
        const canvas = visualizerRef.value;
        const ctx = canvas.getContext('2d');
        const draw = () => {
            if (!isRecording.value) return;
            animationFrameId = requestAnimationFrame(draw);
            analyser.getByteTimeDomainData(dataArray);
            ctx.fillStyle = '#f0f2f5';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#ff4d4f';
            ctx.beginPath();
            const sliceWidth = canvas.width * 1.0 / dataArray.length;
            let x = 0;
            for(let i = 0; i < dataArray.length; i++) {
                const v = dataArray[i] / 128.0;
                const y = v * canvas.height / 2;
                if(i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                x += sliceWidth;
            }
            ctx.lineTo(canvas.width, canvas.height / 2);
            ctx.stroke();
        };
        draw();
    }
};

const stopRecording = () => {
    isRecording.value = false;
    isPaused.value = false;
    stopTimer();
    stopVisualizer();
    cleanupAudioResources();

    // Encode WAV
    setTimeout(() => {
        if (audioChunks.value.length === 0) return;
        
        const flatSamples = flattenAudioChunks(audioChunks.value);
        // audioContext sampleRate is usually 44100 or 48000
        const wavBlob = encodeWAV(flatSamples, audioContext.sampleRate);
        
        processAudio(wavBlob);
    }, 200);
};

const discardRecording = () => {
  cleanupAudioResources();
  
  isRecording.value = false;
  isPaused.value = false;
  audioUrl.value = null;
  audioChunks.value = [];
  recordingTime.value = 0;
  stopTimer();
  stopVisualizer();
  emit('reset');
  
  if (visualizerRef.value) {
    const ctx = visualizerRef.value.getContext('2d');
    ctx.clearRect(0, 0, visualizerRef.value.width, visualizerRef.value.height);
  }
};

const processAudio = (blob) => {
  audioUrl.value = URL.createObjectURL(blob);
  
  nextTick(() => {
    if (wavesurfer.value) {
        wavesurfer.value.load(audioUrl.value);
    }
  });
  
  emit('audio-ready', blob);
};

// MMAU 目录与文件选择逻辑
const mmaudir = ref(null);
const chooseAudio = async () => {
  // Proactively clear UI when starting to choose a file
  emit('reset');
  
  // 优先使用 File System Access API，尝试从设定的 MMAU 目录打开
  try {
    if ('showOpenFilePicker' in window) {
      // 首次未设定目录时，引导选择一次目录
      if (!mmaudir.value && 'showDirectoryPicker' in window) {
        message.info('请选择一次 MMAU 音频目录');
        try {
          mmaudir.value = await window.showDirectoryPicker();
        } catch {
          // 用户取消则回退到标准文件选择
        }
      }
      const opts = {
        startIn: mmaudir.value || 'music',
        types: [{ description: 'Audio', accept: { 'audio/*': ['.wav','.mp3','.flac','.ogg'] } }],
        multiple: false
      };
      const [fh] = await window.showOpenFilePicker(opts);
      if (fh) {
        const file = await fh.getFile();
        processAudio(file);
        return;
      }
    }
  } catch {
    // ignore and fallback
  }
  // 回退：使用隐藏 input[type=file]
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'audio/*';
  input.onchange = () => {
    const f = input.files && input.files[0];
    if (f) processAudio(f);
  };
  input.click();
};
</script>

<style scoped>
.audio-input {
  width: 100%;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.waveform-wrapper {
  margin-bottom: 20px;
  background: #f0f2f5;
  border-radius: 4px;
  min-height: 120px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.visualizer-canvas {
  width: 100%;
  height: 120px;
}

.placeholder-wave {
  text-align: center;
  color: #999;
}

.controls {
  margin-bottom: 20px;
}

.record-btn {
  height: 60px;
  font-size: 1.2rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.btn-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recording-pulse {
  animation: pulse 1.5s infinite;
}

.paused-controls {
  padding: 10px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #d9d9d9;
  text-align: center;
}

.timer-display {
  margin-top: 10px;
  font-size: 1.1rem;
  font-weight: bold;
  color: #1890ff;
}

.finished-controls {
  margin-top: 10px;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.1); }
  100% { opacity: 1; transform: scale(1); }
}
</style>
