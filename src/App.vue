<template>
  <div class="container">
    <h1>Patcher - Update Manager</h1>

    <div class="status-bar">
      <div class="status-indicator" :class="{ 'connected': backendConnected, 'disconnected': !backendConnected }">
        {{ backendConnected ? 'Backend Connected' : 'Backend Disconnected' }}
      </div>
    </div>

    <div class="card">
      <div class="config-section">
        <h2>Configuration</h2>
        <div class="input-group">
          <label>Server URL:</label>
          <input v-model="config.serverUrl" placeholder="https://your-server.com/" />
        </div>
        <div class="input-group">
          <label>Target Folder:</label>
          <input v-model="config.targetFolder" placeholder="patcher" />
        </div>
        <div class="input-group">
          <label>File List URL:</label>
          <input v-model="config.fileListUrl" placeholder="https://your-server.com/patcher.txt" />
        </div>
        <div class="input-group">
          <label>Download Speed Limit (KB/s, 0 = unlimited):</label>
          <input v-model.number="config.downloadSpeedLimit" type="number" min="0" />
        </div>
        <button @click="saveConfig" :disabled="!backendConnected" class="save-config-btn">
          Save Configuration
        </button>
      </div>

      <div class="control-section">
        <button @click="startUpdate" :disabled="isUpdating || !backendConnected">
          {{ isUpdating ? 'Updating...' : 'Start Update' }}
        </button>
        <label class="checkbox-label">
          <input type="checkbox" v-model="autoClose" />
          Auto-close when complete
        </label>
      </div>

      <div class="progress-section" v-if="isUpdating || updateComplete">
        <h3>Progress</h3>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
        </div>
        <p>{{ progress }} / {{ total }} files ({{ progressPercentage.toFixed(1) }}%)</p>
      </div>

      <div class="log-section">
        <h3>Activity Log</h3>
        <div class="log-container" ref="logContainer">
          <div
            v-for="(log, index) in logs"
            :key="index"
            :class="['log-entry', log.type]"
          >
            {{ log.message }}
          </div>
        </div>
      </div>

      <div v-if="updateComplete && statusReport" class="status-section">
        <h3>Update Summary</h3>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">Updated:</span>
            <span class="status-value">{{ statusReport.updated.length }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Skipped:</span>
            <span class="status-value">{{ statusReport.skipped.length }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Failed:</span>
            <span class="status-value error">{{ statusReport.failed.length }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Verified:</span>
            <span class="status-value">{{ statusReport.verification.verified.length }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'

interface Config {
  serverUrl: string
  targetFolder: string
  fileListUrl: string
  downloadSpeedLimit: number
}

interface LogEntry {
  message: string
  type: 'info' | 'error' | 'success'
}

interface StatusReport {
  updated: string[]
  skipped: string[]
  failed: string[]
  verification: {
    verified: string[]
    corrupted: string[]
  }
}

const config = ref<Config>({
  serverUrl: '',
  targetFolder: 'patcher',
  fileListUrl: '',
  downloadSpeedLimit: 0
})

const backendConnected = ref(false)
const isUpdating = ref(false)
const updateComplete = ref(false)
const autoClose = ref(false)
const progress = ref(0)
const total = ref(0)
const logs = ref<LogEntry[]>([])
const statusReport = ref<StatusReport | null>(null)
const logContainer = ref<HTMLElement | null>(null)

let unlistenFunctions: UnlistenFn[] = []

const progressPercentage = computed(() => {
  if (total.value === 0) return 0
  return (progress.value / total.value) * 100
})

const addLog = (message: string, type: 'info' | 'error' | 'success' = 'info') => {
  logs.value.push({ message, type })
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const checkBackendHealth = async () => {
  try {
    const healthy = await invoke('check_backend_health') as boolean
    backendConnected.value = healthy
    return healthy
  } catch (error) {
    backendConnected.value = false
    return false
  }
}

const loadConfig = async () => {
  try {
    const loadedConfig = await invoke('load_config') as Config
    config.value = loadedConfig
    addLog('Configuration loaded successfully', 'info')
  } catch (error) {
    addLog(`Failed to load configuration: ${error}`, 'error')
  }
}

const saveConfig = async () => {
  try {
    await invoke('save_config', { config: config.value })
    addLog('Configuration saved successfully', 'success')
  } catch (error) {
    addLog(`Failed to save configuration: ${error}`, 'error')
  }
}

const startUpdate = async () => {
  if (!config.value.serverUrl || !config.value.fileListUrl) {
    addLog('Please fill in Server URL and File List URL', 'error')
    return
  }

  // Save config first
  await saveConfig()

  isUpdating.value = true
  updateComplete.value = false
  progress.value = 0
  total.value = 0
  logs.value = []
  statusReport.value = null

  addLog('Starting update process...', 'info')

  try {
    const result = await invoke('start_update', { config: config.value }) as string
    addLog(result, 'info')
  } catch (error) {
    addLog(`Error starting update: ${error}`, 'error')
    isUpdating.value = false
  }
}

const setupEventListeners = async () => {
  // Listen for backend started event
  const unlistenBackendStarted = await listen('backend_started', () => {
    addLog('Python backend started successfully', 'success')
    backendConnected.value = true
    loadConfig()
  })
  unlistenFunctions.push(unlistenBackendStarted)

  // Listen for progress updates
  const unlistenProgress = await listen('update_progress', (event: any) => {
    progress.value = event.payload.progress
    total.value = event.payload.total
  })
  unlistenFunctions.push(unlistenProgress)

  // Listen for log messages
  const unlistenLog = await listen('log_message', (event: any) => {
    const logData = event.payload as LogEntry
    addLog(logData.message, logData.type)
  })
  unlistenFunctions.push(unlistenLog)

  // Listen for update completion
  const unlistenComplete = await listen('update_complete', (event: any) => {
    statusReport.value = event.payload as StatusReport
    updateComplete.value = true
    isUpdating.value = false

    const hasErrors = statusReport.value.failed.length > 0 ||
                     statusReport.value.verification.corrupted.length > 0

    if (hasErrors) {
      addLog('Update completed with errors', 'error')
    } else {
      addLog('Update completed successfully!', 'success')

      if (autoClose.value) {
        addLog('Auto-closing in 3 seconds...', 'info')
        setTimeout(() => {
          invoke('close_app')
        }, 3000)
      }
    }
  })
  unlistenFunctions.push(unlistenComplete)

  // Listen for update errors
  const unlistenError = await listen('update_error', (event: any) => {
    addLog(`Update error: ${event.payload}`, 'error')
    isUpdating.value = false
    updateComplete.value = true
  })
  unlistenFunctions.push(unlistenError)
}

onMounted(async () => {
  addLog('Application started. Connecting to Python backend...', 'info')

  // Setup event listeners
  await setupEventListeners()

  // Check backend health periodically
  const healthCheckInterval = setInterval(async () => {
    await checkBackendHealth()
  }, 5000)

  // Initial health check
  setTimeout(async () => {
    const healthy = await checkBackendHealth()
    if (healthy) {
      await loadConfig()
    } else {
      addLog('Python backend not responding. Please check if Python is installed.', 'error')
    }
  }, 2000)

  // Store interval for cleanup
  onUnmounted(() => {
    clearInterval(healthCheckInterval)
    // Cleanup event listeners
    unlistenFunctions.forEach(fn => fn())
  })
})
</script>

<style scoped>
.container {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.status-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
}

.status-indicator {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.status-indicator.connected {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-indicator.disconnected {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin: 20px 0;
}

.config-section h2 {
  margin-bottom: 20px;
  color: #333;
  font-weight: 600;
}

.input-group {
  margin-bottom: 18px;
}

.input-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #555;
}

.input-group input {
  width: 100%;
  padding: 10px 14px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s ease;
}

.input-group input:focus {
  outline: none;
  border-color: #4a86e8;
}

.save-config-btn {
  padding: 10px 20px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-top: 10px;
}

.save-config-btn:hover:not(:disabled) {
  background-color: #218838;
}

.save-config-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.control-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin: 30px 0;
  padding-top: 30px;
  border-top: 2px solid #f0f0f0;
}

.control-section button {
  padding: 14px 28px;
  background-color: #4a86e8;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.control-section button:hover:not(:disabled) {
  background-color: #3a76d8;
}

.control-section button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #555;
  font-weight: 500;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  transform: scale(1.2);
}

.progress-section {
  margin: 30px 0;
  padding-top: 30px;
  border-top: 2px solid #f0f0f0;
}

.progress-section h3 {
  margin-bottom: 15px;
  color: #333;
}

.progress-bar {
  width: 100%;
  height: 12px;
  background-color: #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(45deg, #4a86e8, #6fa8f5);
  transition: width 0.3s ease;
  border-radius: 6px;
}

.progress-section p {
  margin: 10px 0;
  font-weight: 500;
  color: #555;
}

.log-section {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px solid #f0f0f0;
}

.log-section h3 {
  margin-bottom: 15px;
  color: #333;
}

.log-container {
  max-height: 250px;
  overflow-y: auto;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px;
  background-color: #fafafa;
  font-family: 'Consolas', 'Monaco', monospace;
}

.log-entry {
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid #eee;
  line-height: 1.4;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-entry.error {
  color: #dc3545;
  font-weight: 500;
}

.log-entry.success {
  color: #28a745;
  font-weight: 500;
}

.log-entry.info {
  color: #333;
}

.status-section {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px solid #f0f0f0;
}

.status-section h3 {
  margin-bottom: 20px;
  color: #333;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.status-item {
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-radius: 10px;
  text-align: center;
  border: 1px solid #dee2e6;
}

.status-label {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 6px;
  font-weight: 500;
  text-transform: uppercase;
}

.status-value {
  font-size: 20px;
  font-weight: bold;
  color: #495057;
}

.status-value.error {
  color: #dc3545;
}

@media (prefers-color-scheme: dark) {
  .card {
    background: #1e1e1e;
    color: #f6f6f6;
  }

  .input-group label {
    color: #ccc;
  }

  .input-group input {
    background: #2a2a2a;
    border-color: #444;
    color: #f6f6f6;
  }

  .log-container {
    background-color: #2a2a2a;
    border-color: #444;
    color: #f6f6f6;
  }

  .status-item {
    background: linear-gradient(135deg, #2a2a2a, #333);
    border-color: #444;
  }

  .status-label {
    color: #aaa;
  }

  .status-value {
    color: #f6f6f6;
  }
}

/* Custom scrollbar for log container */
.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>