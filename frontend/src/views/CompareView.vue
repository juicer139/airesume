<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchCompare, type CompareItem } from '@/api/resume'

const route = useRoute()
const router = useRouter()

const items = ref<CompareItem[]>([])
const loading = ref(true)
const errorMsg = ref('')

onMounted(async () => {
  try {
    items.value = await fetchCompare(String(route.query.ids ?? ''))
  } catch {
    errorMsg.value = '加载对比数据失败'
  } finally {
    loading.value = false
  }
})

// A = 基准（先勾选），B = 对比对象（后勾选）
const a = computed(() => items.value[0])
const b = computed(() => items.value[1])

/** B 相对 A 的变化量；某侧没有 JD 数据时返回 null 表示不可比 */
function diffOf(key: 'overall_score' | 'completeness' | 'jd'): number | null {
  if (!a.value || !b.value) return null
  if (key === 'jd') {
    if (a.value.jd_match_score == null || b.value.jd_match_score == null) return null
    return b.value.jd_match_score - a.value.jd_match_score
  }
  return b.value[key] - a.value[key]
}

const metricRows = computed(() => [
  {
    label: '综合得分',
    a: a.value?.overall_score,
    b: b.value?.overall_score,
    diff: diffOf('overall_score'),
  },
  {
    label: '内容完整性',
    a: a.value?.completeness,
    b: b.value?.completeness,
    diff: diffOf('completeness'),
  },
  {
    label: 'JD 匹配度',
    a: a.value?.jd_match_score ?? '未测',
    b: b.value?.jd_match_score ?? '未测',
    diff: diffOf('jd'),
  },
])
</script>

<template>
  <div v-loading="loading">
    <el-page-header class="page-header" @back="router.back()">
      <template #content>
        <span class="title">历史对比</span>
      </template>
    </el-page-header>

    <el-card v-if="!loading && items.length !== 2" class="block">
      <el-empty :description="errorMsg || '对比数据不足，请在首页勾选两条已完成分析的记录'">
        <el-button type="primary" @click="router.push('/')">回首页选择</el-button>
      </el-empty>
    </el-card>

    <template v-else>
      <!-- 得分对比表：A → B 变化量 -->
      <el-card class="block" header="得分对比（先勾选的为 A，后勾选的为 B）">
        <el-table :data="metricRows" border>
          <el-table-column prop="label" label="维度" width="140" />
          <el-table-column align="center">
            <template #header>
              <span class="col-head">A：{{ a?.filename }}</span>
            </template>
            <template #default="{ row }">{{ row.a }}</template>
          </el-table-column>
          <el-table-column align="center">
            <template #header>
              <span class="col-head">B：{{ b?.filename }}</span>
            </template>
            <template #default="{ row }">{{ row.b }}</template>
          </el-table-column>
          <el-table-column label="变化" width="120" align="center">
            <template #default="{ row }">
              <span v-if="row.diff == null" class="muted">-</span>
              <span v-else-if="row.diff > 0" class="up">▲ +{{ row.diff }}</span>
              <span v-else-if="row.diff < 0" class="down">▼ {{ row.diff }}</span>
              <span v-else class="muted">— 持平</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 明细左右对照 -->
      <el-row :gutter="16" class="block">
        <el-col v-for="(item, idx) in items" :key="item.id" :span="12">
          <el-card :header="`${idx === 0 ? 'A' : 'B'}：${item.filename}`">
            <p class="list-title">亮点</p>
            <ul class="plain-list">
              <li v-for="(s, i) in item.strengths" :key="'s' + i">{{ s }}</li>
            </ul>
            <p class="list-title">不足</p>
            <ul class="plain-list">
              <li v-for="(s, i) in item.weaknesses" :key="'w' + i">{{ s }}</li>
            </ul>
            <p class="list-title">优化建议</p>
            <ol class="plain-list">
              <li v-for="(s, i) in item.suggestions" :key="'g' + i">{{ s }}</li>
            </ol>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 16px;
}
.title {
  font-weight: 600;
}
.col-head {
  font-weight: 600;
}
.block {
  margin-top: 16px;
}
.up {
  color: var(--el-color-success);
  font-weight: 600;
}
.down {
  color: var(--el-color-danger);
  font-weight: 600;
}
.muted {
  color: var(--el-text-color-secondary);
}
.list-title {
  font-weight: 600;
  margin: 10px 0 4px;
}
.plain-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
  font-size: 13px;
}
</style>
