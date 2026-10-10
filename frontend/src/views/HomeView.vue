<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadRequestOptions } from 'element-plus'
import {
  analyzeResume,
  fetchResumeStatus,
  fetchResumes,
  uploadResume,
  deleteResume,
  type ResumeItem,
} from '@/api/resume'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const records = ref<ResumeItem[]>([])
const jobDescription = ref('')
const uploading = ref(false)

// 轮询计时器表：recordId -> timerId（每条记录独立轮询，互不干扰）
const timers = new Map<number, number>()
// 正在删除中的记录 id（防重复点击）
const deletingIds = ref(new Set<number>())

// 状态 → 标签样式映射
const STATUS_MAP: Record<
  string,
  { label: string; type: 'info' | 'warning' | 'success' | 'danger' }
> = {
  pending: { label: '待分析', type: 'info' },
  processing: { label: '分析中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

function statusOf(s: string) {
  return STATUS_MAP[s] ?? { label: s, type: 'info' as const }
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

// ---- 历史对比：勾选两条已完成分析的记录 ----
const selected = ref<ResumeItem[]>([])

function selectableRow(row: ResumeItem) {
  return row.status === 'completed' // 只有完成分析的记录可参与对比
}

function onSelectionChange(rows: ResumeItem[]) {
  selected.value = rows
}

function goCompare() {
  // 勾选顺序即 A/B 顺序：第一个是基准，第二个是对比对象
  router.push({
    path: '/compare',
    query: { ids: selected.value.map((r) => r.id).join(',') },
  })
}

async function loadRecords() {
  records.value = await fetchResumes()
  // 页面刚打开/刷新时，可能有任务正在分析，恢复对它们的轮询
  records.value
    .filter((r) => r.status === 'pending' || r.status === 'processing')
    .forEach((r) => startPolling(r.id))
}

onMounted(async () => {
  if (auth.isLoggedIn && !auth.user) await auth.fetchUser()
  await loadRecords()
})

// 组件卸载时清掉所有计时器，防止内存泄漏
onUnmounted(() => {
  timers.forEach((timer) => clearInterval(timer))
  timers.clear()
})

function startPolling(recordId: number) {
  if (timers.has(recordId)) return
  const timer = window.setInterval(async () => {
    try {
      const s = await fetchResumeStatus(recordId)
      const row = records.value.find((r) => r.id === recordId)
      if (row) row.status = s.status

      // 到达终态：停止轮询并提示
      if (s.status === 'completed' || s.status === 'failed') {
        stopPolling(recordId)
        await loadRecords()
        if (s.status === 'completed') {
          ElMessage.success('分析完成')
        } else {
          ElMessage.error(s.error_message || '分析失败')
        }
      }
    } catch {
      stopPolling(recordId)
    }
  }, 2000)
  timers.set(recordId, timer)
}

function stopPolling(recordId: number) {
  const timer = timers.get(recordId)
  if (timer) {
    clearInterval(timer)
    timers.delete(recordId)
  }
}

async function startAnalysis(row: ResumeItem) {
  const res = await analyzeResume(row.id)
  row.status = res.status
  startPolling(row.id)
  ElMessage.success('已加入分析队列')
}

async function onDelete(row: ResumeItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.filename}」吗？删除后列表中将不再显示。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return // 用户点了取消
  }

  deletingIds.value.add(row.id)
  try {
    await deleteResume(row.id)
    stopPolling(row.id) // 别让已删记录的轮询继续跑
    ElMessage.success('删除成功')
    await loadRecords()
  } catch {
    // 409（分析中）等错误已由 request.ts 统一弹提示，这里只兜底不额外处理
  } finally {
    deletingIds.value.delete(row.id)
  }
}

/** el-upload 自定义上传：走我们的 axios 实例（自动带 token） */
async function doUpload(options: UploadRequestOptions) {
  const file = options.file as File
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()

  if (!['.pdf', '.docx'].includes(ext)) {
    ElMessage.error('仅支持 PDF / Word(.docx) 文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件不能超过 10MB')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    if (jobDescription.value.trim()) {
      formData.append('job_description', jobDescription.value.trim())
    }
    await uploadResume(formData)
    ElMessage.success('上传成功，已加入分析队列')
    await loadRecords()
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="upload-page">
    <el-card>
      <template #header>
        <span>上传简历</span>
      </template>

      <el-upload
        drag
        multiple
        accept=".pdf,.docx"
        :show-file-list="false"
        :http-request="doUpload"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件到这里，或 <em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 PDF / Word(.docx)，不超过 10MB</div>
        </template>
      </el-upload>

      <el-form label-position="top" class="jd-form">
        <el-form-item label="目标岗位 JD（可选，用于匹配打分）">
          <el-input
            v-model="jobDescription"
            type="textarea"
            :rows="4"
            placeholder="粘贴目标岗位的职位描述，例如：负责后端服务开发，要求熟悉 Python / FastAPI / MySQL..."
          />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="history-card">
      <template #header>
        <div class="history-header">
          <span>我的分析记录</span>
          <el-button
            type="primary"
            size="small"
            :disabled="selected.length !== 2"
            @click="goCompare"
          >
            对比分析（{{ selected.length }}/2）
          </el-button>
        </div>
      </template>

      <el-table
        v-if="records.length"
        :data="records"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="45" :selectable="selectableRow" />
        <el-table-column prop="filename" label="文件名" min-width="160" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tooltip :disabled="row.status !== 'failed'" :content="row.error_message || ''">
              <el-tag :type="statusOf(row.status).type" size="small">
                {{ statusOf(row.status).label }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="270">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :disabled="row.status === 'processing'"
              @click="startAnalysis(row)"
            >
              {{ row.status === 'completed' ? '重新分析' : '分析' }}
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              @click="router.push(`/analysis/${row.id}`)"
            >
              查看报告
            </el-button>
            <el-button
              v-if="['completed', 'pending', 'failed'].includes(row.status)"
              size="small"
              type="danger"
              @click="onDelete(row)"
              :loading="deletingIds.has(row.id)"
            >
              删除简历
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="还没有上传过简历" />
    </el-card>
  </div>
</template>

<style scoped>
.history-card {
  margin-top: 16px;
}
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
