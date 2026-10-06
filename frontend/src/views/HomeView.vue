<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { fetchResumes, uploadResume, type ResumeItem } from '@/api/resume'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const records = ref<ResumeItem[]>([])
const jobDescription = ref('')
const uploading = ref(false)

// 状态 → 标签样式映射（阶段 6/7 接入真实状态流转后自动生效）
const STATUS_MAP: Record<string, { label: string; type: 'info' | 'warning' | 'success' | 'danger' }> = {
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

async function loadRecords() {
  records.value = await fetchResumes()
}

onMounted(async () => {
  if (auth.isLoggedIn && !auth.user) await auth.fetchUser()
  await loadRecords()
})

/** el-upload 自定义上传：绕过组件默认的 XHR，统一走我们的 axios 实例（自动带 token） */
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
        <el-form-item label="目标岗位 JD（可选，阶段 7 用于匹配打分）">
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
        <span>我的分析记录</span>
      </template>

      <el-table v-if="records.length" :data="records">
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusOf(row.status).type" size="small">
              {{ statusOf(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
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
</style>
