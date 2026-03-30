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
    <div class="content">
      <div class="brand">
        <div class="logo">LALM</div>
        <div class="subtitle">语音 · 推理 · 理解</div>
      </div>
      <a-card style="width: 460px" class="login-card">
        <a-tabs v-model:activeKey="activeKey">
          <a-tab-pane key="login" tab="登录">
            <a-form :model="loginForm" @finish="onLogin" @submit.prevent layout="vertical">
              <a-form-item label="用户名" name="username" :rules="loginRules.username">
                <a-input v-model:value="loginForm.username" placeholder="请输入用户名" />
              </a-form-item>
              <a-form-item label="密码" name="password" :rules="loginRules.password">
                <a-input-password v-model:value="loginForm.password" placeholder="请输入密码" />
              </a-form-item>
              <a-form-item>
                <a-button type="primary" html-type="submit" block :loading="loading">登录</a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
          <a-tab-pane key="register" tab="注册">
            <a-form :model="registerForm" @finish="onRegister" @submit.prevent layout="vertical">
              <a-form-item label="用户名" name="username" :rules="registerRules.username">
                <a-input v-model:value="registerForm.username" placeholder="3-32位字母/数字/下划线" />
              </a-form-item>
              <a-form-item label="密码" name="password" :rules="registerRules.password">
                <a-input-password v-model:value="registerForm.password" placeholder="至少6位" />
              </a-form-item>
              <a-form-item label="确认密码" name="confirmPassword" :rules="registerRules.confirmPassword">
                <a-input-password v-model:value="registerForm.confirmPassword" placeholder="再次输入密码" />
              </a-form-item>
              <a-form-item>
                <a-button type="primary" html-type="submit" block :loading="loading">注册</a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
        </a-tabs>
      </a-card>
      <div class="footer">LALM Reasoner ©2025</div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { API_BASE, pingBackend, postJson } from '../config/api';

const router = useRouter();
const loading = ref(false);
const activeKey = ref('login');
const backendReady = ref(false);

const loginForm = reactive({ username: '', password: '' });
const registerForm = reactive({ username: '', password: '', confirmPassword: '' });

const loginRules = {
  username: [
    { required: true, message: '请输入用户名' },
    {
      validator: (_rule, value) => {
        if (!value || !value.trim()) return Promise.reject('用户名不能为空白');
        return Promise.resolve();
      }
    }
  ],
  password: [
    { required: true, message: '请输入密码' },
    {
      validator: (_rule, value) => {
        if (!value || !value.trim()) return Promise.reject('密码不能为空白');
        return Promise.resolve();
      }
    }
  ]
};
const registerRules = {
  username: [
    { required: true, message: '请输入用户名' },
    { min: 3, max: 32, message: '长度3-32' },
    { pattern: /^[A-Za-z0-9_]+$/, message: '仅字母/数字/下划线' }
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, max: 64, message: '长度6-64' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码' },
    {
      validator: (_rule, value) => {
        if (value !== registerForm.password) return Promise.reject('两次输入不一致');
        return Promise.resolve();
      }
    }
  ]
};

onMounted(async () => {
  const ctl = new AbortController();
  try {
    const ok = await pingBackend(ctl.signal);
    backendReady.value = ok;
    if (!ok) message.warning('后端未就绪，正在重试…');
  } catch {}
  if (!backendReady.value) {
    const timer = setInterval(async () => {
      try {
        const ok2 = await pingBackend();
        backendReady.value = ok2;
        if (ok2) {
          clearInterval(timer);
          message.success('后端已就绪');
        }
      } catch {}
    }, 1500);
  }
});

const onLogin = async (values) => {
  loading.value = true;
  try {
    const payload = {
      username: (values.username || '').trim(),
      password: (values.password || '').trim()
    };
    if (!payload.username || !payload.password) {
      message.error('用户名或密码不能为空');
      return;
    }
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 8000);
    const { ok, data } = await postJson('/api/login', payload, ctl.signal);
    clearTimeout(t);
    if (ok && data && data.code === 200) {
      localStorage.setItem('user', JSON.stringify(data.data));
      message.success('登录成功'); router.push('/dashboard');
    } else {
      const msg = data?.message || '登录失败，请检查后端服务';
      message.error(msg);
    }
  } catch (error) {
      console.error('Login error:', error);
      message.error('登录请求失败，请检查后端服务');
  } finally {
      loading.value = false;
  }
};

const onRegister = async (values) => {
  loading.value = true;
  try {
    const payload = {
      username: (values.username || '').trim(),
      password: (values.password || '').trim()
    };
    if (!payload.username || !payload.password) {
      message.error('用户名或密码不能为空');
      return;
    }
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 8000);
    const { ok, data } = await postJson('/api/register', payload, ctl.signal);
    clearTimeout(t);
    if (ok && data && data.code === 200) {
      message.success('注册成功，请登录');
      activeKey.value = 'login';
      loginForm.username = values.username;
    } else {
      message.error(data?.message || '注册失败');
    }
  } catch (e) {
    message.error('注册请求失败');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.auth-page {
  position: relative;
  height: 100vh;
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
.content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
}
.brand {
  text-align: center;
  color: #1f2d3d;
}
.brand .logo {
  font-size: 28px;
  font-weight: 700;
}
.brand .subtitle {
  margin-top: 6px;
  color: #5f6b7a;
  font-size: 13px;
  letter-spacing: 2px;
}
.login-card {
  backdrop-filter: saturate(1.1) blur(8px);
  background: rgba(255,255,255,0.75);
  border: 1px solid rgba(255,255,255,0.6);
  box-shadow: 0 10px 30px rgba(69, 98, 147, 0.15);
  border-radius: 14px;
}
.footer {
  margin-top: 8px;
  color: #8a93a2;
  font-size: 12px;
}
</style>