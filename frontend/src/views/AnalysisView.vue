<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchResumeDetail, type ResumeDetail } from '@/api/resume'

const route = useRoute()
const router = useRouter()

const detail = ref<ResumeDetail | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    detail.value = await fetchResumeDetail(Number(route.params.id))
  } finally {
    loading.value = false
  }
})

/** 得分 → 进度条颜色：绿 / 橙 / 红 */
function scoreColor(score: number) {
  if (score >= 80) return '#67C23A'
  if (score >= 60) return '#E6A23C'
  return '#F56C6C'
}
</script>

<template>
  <div v-loading="loading">
    <template v-if="detail">
      <el-page-header class="page-header" @back="router.back()">
        <template #content>
          <span class="filename">{{ detail.filename }}</span>
          <el-tag size="small" class="time-tag">
            {{ new Date(detail.created_at).toLocaleString('zh-CN') }}
          </el-tag>
        </template>
      </el-page-header>

      <!-- 尚无 AI 结果时的三种状态提示 -->
      <el-card v-if="!detail.result" class="block">
        <el-empty
          :description="
            detail.status === 'pending' || detail.status === 'processing'
              ? '分析进行中，稍后回到首页查看'
              : detail.status === 'failed'
                ? `分析失败：${detail.error_message || '未知原因'}`
                : '尚未分析，请回到首页点击分析'
          "
        />
      </el-card>

      <!-- 报告主体 -->
      <template v-else>
        <!-- 总览：综合分 + 一句话评价 + 两个子得分 -->
        <el-card class="block">
          <div class="score-row">
            <el-progress
              type="dashboard"
              :percentage="detail.result!.overall_score"
              :color="scoreColor"
              :width="140"
            >
              <template #default="{ percentage }">
                <div class="score-num">{{ percentage }}</div>
                <div class="score-label">综合得分</div>
              </template>
            </el-progress>
            <div class="score-side">
              <p class="summary">{{ detail.result!.summary }}</p>
              <div class="mini-score">
                <span class="mini-label">内容完整性</span>
                <el-progress
                  :percentage="detail.result!.completeness"
                  :color="scoreColor"
                  :stroke-width="10"
                  class="mini-bar"
                />
              </div>
              <div v-if="detail.result!.jd_match" class="mini-score">
                <span class="mini-label">JD 匹配度</span>
                <el-progress
                  :percentage="detail.result!.jd_match!.score"
                  :color="scoreColor"
                  :stroke-width="10"
                  class="mini-bar"
                />
              </div>
            </div>
          </div>
        </el-card>

        <!-- JD 匹配：命中 vs 缺失 -->
        <el-card v-if="detail.result!.jd_match" class="block" header="岗位 JD 匹配详情">
          <p class="list-title">命中的要求</p>
          <div class="tag-wrap">
            <el-tag
              v-for="(m, i) in detail.result!.jd_match!.matched"
              :key="'m' + i"
              type="success"
              class="tag-item"
            >
              {{ m }}
            </el-tag>
          </div>
          <p class="list-title">缺失的要求</p>
          <div class="tag-wrap">
            <el-tag
              v-for="(m, i) in detail.result!.jd_match!.missing"
              :key="'x' + i"
              type="danger"
              class="tag-item"
            >
              {{ m }}
            </el-tag>
          </div>
        </el-card>

        <!-- 亮点 / 不足 两栏 -->
        <el-row :gutter="16" class="block">
          <el-col :span="12">
            <el-card header="亮点" class="half-card">
              <ul class="plain-list">
                <li v-for="(s, i) in detail.result!.strengths" :key="i">{{ s }}</li>
              </ul>
              <el-empty v-if="!detail.result!.strengths.length" description="无" :image-size="48" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card header="不足" class="half-card">
              <ul class="plain-list">
                <li v-for="(s, i) in detail.result!.weaknesses" :key="i">{{ s }}</li>
              </ul>
              <el-empty v-if="!detail.result!.weaknesses.length" description="无" :image-size="48" />
            </el-card>
          </el-col>
        </el-row>

        <!-- 优化建议（有序列表，突出可执行性） -->
        <el-card class="block" header="优化建议">
          <ol class="plain-list">
            <li v-for="(s, i) in detail.result!.suggestions" :key="i">{{ s }}</li>
          </ol>
        </el-card>

        <!-- 完整性扣分点 -->
        <el-card class="block" header="内容完整性扣分点">
          <div class="tag-wrap">
            <el-tag
              v-for="(s, i) in detail.result!.completeness_issues"
              :key="i"
              type="warning"
              class="tag-item"
            >
              {{ s }}
            </el-tag>
          </div>
        </el-card>

        <!-- 解析原文，调试和溯源用 -->
        <el-collapse class="block">
          <el-collapse-item title="查看解析出的简历原文" name="raw">
            <div class="raw-text">{{ detail.content_text }}</div>
          </el-collapse-item>
        </el-collapse>
      </template>
    </template>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 16px;
}
.filename {
  font-weight: 600;
}
.time-tag {
  margin-left: 12px;
}
.block {
  margin-top: 16px;
}
.score-row {
  display: flex;
  align-items: center;
  gap: 32px;
}
.score-num {
  font-size: 32px;
  font-weight: 700;
}
.score-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.score-side {
  flex: 1;
}
.summary {
  font-size: 16px;
  margin: 0 0 16px;
}
.mini-score {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.mini-label {
  width: 72px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}
.mini-bar {
  flex: 1;
  max-width: 320px;
}
.list-title {
  font-weight: 600;
  margin: 8px 0;
}
.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.tag-item {
  height: auto;
  white-space: normal;
  padding: 4px 10px;
}
.plain-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.9;
}
.half-card {
  min-height: 120px;
}
.raw-text {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.8;
  color: var(--el-text-color-regular);
  max-height: 400px;
  overflow: auto;
}
</style>
