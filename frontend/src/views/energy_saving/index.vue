<template>
  <section class="page" data-module="energy_saving">
    <header class="page-head">
      <div>
        <h2>能效分析管理</h2>
        <p class="page-desc">按分析周期对比系统效率、损失构成与报告状态；点击电站编号或周期可展开对应报告，看板与报告明细读取同一份数据。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记能效报告</button>
        <button class="btn" type="button" @click="exportRows">导出能效分析清单</button>
      </div>
    </header>

    <section class="board" aria-label="周期对比看板">
      <div class="board-head">
        <h3>周期对比看板</h3>
        <div class="period-tabs">
          <button
            v-for="period in periods"
            :key="period"
            class="period-tab"
            :class="{ active: period === activePeriod }"
            type="button"
            @click="selectPeriod(period)"
          >
            {{ period }}
          </button>
        </div>
      </div>

      <div class="stat-row">
        <article v-for="item in stats" :key="item.label" class="stat-card">
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value">{{ item.value }}</strong>
        </article>
      </div>

      <div class="card-row">
        <article
          v-for="card in cards"
          :key="card.id"
          class="report-card"
          :class="{ expanded: card.id === expandedId }"
        >
          <header class="card-head">
            <button class="link station-link" type="button" @click="toggleReport(card)">
              {{ card.电站编号 }}
            </button>
            <span class="status-badge" :class="statusClass(card.报告状态)">{{ card.报告状态 || '—' }}</span>
          </header>
          <strong class="eff-value">{{ fmtPct(card.系统效率) }}</strong>
          <span class="eff-label">系统效率</span>
          <dl class="card-meta">
            <div>
              <dt>理论发电量</dt>
              <dd>{{ fmtNum(card.理论发电量) }} kWh</dd>
            </div>
            <div>
              <dt>实际发电量</dt>
              <dd>{{ fmtNum(card.实际发电量) }} kWh</dd>
            </div>
          </dl>
          <ul class="card-loss">
            <li v-for="item in card.损失构成" :key="item.reason">
              <span :class="{ 'uncat-text': item.reason === UNCATEGORIZED }">{{ item.reason }}</span>
              <span>{{ fmtNum(item.value) }} kWh</span>
            </li>
            <li v-if="!card.损失构成.length" class="empty-loss">暂无损失数据</li>
          </ul>
          <button class="link card-toggle" type="button" @click="toggleReport(card)">
            {{ card.id === expandedId ? '收起报告' : '展开报告' }}
          </button>
        </article>
        <p v-if="!cards.length && !boardLoading" class="empty-state board-empty">当前周期暂无能效报告</p>
      </div>

      <section v-if="expandedId != null" class="report-detail">
        <header class="detail-head">
          <h4>报告明细 · {{ expandedCard?.报告编号 ?? expandedId }}</h4>
          <span class="page-desc">与看板卡片读取同一份数据</span>
        </header>
        <p v-if="detailLoading" class="empty-state">报告明细加载中…</p>
        <template v-else-if="detail">
          <dl class="detail-grid">
            <div v-for="field in detailFields" :key="field">
              <dt>{{ field }}</dt>
              <dd>{{ fmtCell(detail[field]) }}</dd>
            </div>
          </dl>
          <div class="detail-loss">
            <h5>损失构成</h5>
            <ul v-if="expandedCard?.损失构成.length">
              <li v-for="item in expandedCard.损失构成" :key="item.reason">
                <span :class="{ 'uncat-text': item.reason === UNCATEGORIZED }">{{ item.reason }}</span>
                <span>{{ fmtNum(item.value) }} kWh</span>
              </li>
            </ul>
            <p v-else class="empty-state">该报告暂无损失数据</p>
          </div>
        </template>
      </section>

      <div class="trend-row">
        <div class="trend-card">
          <h4>系统效率趋势</h4>
          <div class="trend-bars">
            <button
              v-for="point in trend"
              :key="point.period"
              class="trend-bar"
              :class="{ active: point.period === activePeriod }"
              type="button"
              @click="selectPeriod(point.period)"
            >
              <span class="trend-value">{{ fmtPct(point.平均系统效率) }}</span>
              <span class="trend-track">
                <span class="trend-fill" :style="{ height: effHeight(point.平均系统效率) }"></span>
              </span>
              <span class="trend-label">{{ point.period }}</span>
            </button>
          </div>
        </div>
        <div class="trend-card">
          <h4>损失构成 · {{ activePeriod || '—' }}</h4>
          <ul class="loss-bars">
            <li
              v-for="item in lossItems"
              :key="item.reason"
              :class="{ uncat: item.reason === UNCATEGORIZED }"
            >
              <span class="loss-reason">{{ item.reason }}</span>
              <span class="loss-track">
                <span class="loss-fill" :style="{ width: lossWidth(item.value) }"></span>
              </span>
              <span class="loss-value">{{ fmtNum(item.value) }} kWh</span>
            </li>
            <li v-if="!lossItems.length" class="empty-state">当前周期暂无损失数据</li>
          </ul>
        </div>
        <div class="trend-card">
          <h4>报告状态趋势</h4>
          <div class="status-trend">
            <button
              v-for="point in trend"
              :key="point.period"
              class="status-row"
              :class="{ active: point.period === activePeriod }"
              type="button"
              @click="selectPeriod(point.period)"
            >
              <span class="trend-label">{{ point.period }}</span>
              <span class="status-stack">
                <span
                  v-for="status in statuses"
                  v-show="point.状态分布[status]"
                  :key="status"
                  class="status-seg"
                  :class="statusClass(status)"
                  :style="{ width: statusWidth(point, status) }"
                  :title="`${status} ${point.状态分布[status] ?? 0} 份`"
                ></span>
              </span>
              <span class="status-count">{{ point.报告数 }} 份</span>
            </button>
          </div>
          <div class="status-legend">
            <span v-for="status in statuses" :key="status">
              <i class="legend-dot" :class="statusClass(status)"></i>{{ status }}
            </span>
          </div>
        </div>
      </div>
      <p v-if="boardError" class="error-text">{{ boardError }}</p>
    </section>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无能效分析数据，可先登记能效报告</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条能效分析记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type LossItem = { reason: string; value: number }
type BoardCard = {
  id: number
  报告编号: string
  电站编号: string
  分析周期: string
  理论发电量: number | null
  实际发电量: number | null
  系统效率: number | null
  报告状态: string
  损失构成: LossItem[]
}
type TrendPoint = {
  period: string
  报告数: number
  平均系统效率: number | null
  理论发电量: number
  实际发电量: number
  损失电量: number
  状态分布: Record<string, number>
}
type BoardPayload = {
  periods: string[]
  period: string
  cards: BoardCard[]
  loss: LossItem[]
  trend: TrendPoint[]
}
type ReportDetail = Record<string, unknown>

const ENDPOINT = '/api/energy_saving'
const UNCATEGORIZED = '未分类'
const columns = ["报告编号", "电站编号", "分析周期", "理论发电量", "实际发电量", "系统效率", "损失分析", "报告状态"]
const actions = ["生成报告", "审阅确认", "归档报告"]
const statuses = ["待生成", "已生成", "已审阅", "已归档"]
const detailFields = ["报告编号", "电站编号", "分析周期", "理论发电量", "实际发电量", "系统效率", "损失分析", "报告状态"]
const STATUS_CLASS: Record<string, string> = { "待生成": "is-pending", "已生成": "is-created", "已审阅": "is-reviewed", "已归档": "is-archived" }

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const periods = ref<string[]>([])
const activePeriod = ref('')
const cards = ref<BoardCard[]>([])
const lossItems = ref<LossItem[]>([])
const trend = ref<TrendPoint[]>([])
const boardError = ref('')
const boardLoading = ref(false)
const expandedId = ref<number | null>(null)
const detail = ref<ReportDetail | null>(null)
const detailLoading = ref(false)
let boardSeq = 0

const expandedCard = computed(() => cards.value.find((card) => card.id === expandedId.value) ?? null)
const maxLoss = computed(() => Math.max(0, ...lossItems.value.map((item) => item.value)))

const stats = computed(() => {
  const index = trend.value.findIndex((point) => point.period === activePeriod.value)
  const current = index >= 0 ? trend.value[index] : undefined
  const previous = index > 0 ? trend.value[index - 1] : undefined
  const awaiting = cards.value.filter((card) => card.报告状态 === '已生成').length
  let delta = '—'
  if (current?.平均系统效率 != null && previous?.平均系统效率 != null) {
    const diff = Math.round((current.平均系统效率 - previous.平均系统效率) * 100) / 100
    delta = `${diff >= 0 ? '+' : ''}${diff} pt`
  }
  return [
    { label: '本期报告', value: String(cards.value.length) },
    { label: '待审阅报告', value: String(awaiting) },
    { label: '平均系统效率', value: fmtPct(current?.平均系统效率) },
    { label: '环比上周期', value: delta },
  ]
})

function statusClass(status: string): string {
  return STATUS_CLASS[status] ?? 'is-pending'
}

function fmtPct(value: number | null | undefined): string {
  return value == null ? '—' : `${value}%`
}

function fmtNum(value: number | null | undefined): string {
  return value == null ? '—' : value.toLocaleString('zh-CN')
}

function fmtCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function effHeight(value: number | null): string {
  if (value == null) return '0%'
  return `${Math.min(Math.max(value, 0), 100)}%`
}

function lossWidth(value: number): string {
  if (!maxLoss.value) return '0%'
  return `${Math.max((value / maxLoss.value) * 100, 3)}%`
}

function statusWidth(point: TrendPoint, status: string): string {
  if (!point.报告数) return '0%'
  return `${((point.状态分布[status] ?? 0) / point.报告数) * 100}%`
}

function selectPeriod(period: string) {
  if (period === activePeriod.value) return
  // 切换周期：先清空上一周期的卡片、损失构成与展开明细，不沿用旧数字
  cards.value = []
  lossItems.value = []
  expandedId.value = null
  detail.value = null
  void loadBoard(period)
}

async function loadBoard(period?: string) {
  const seq = ++boardSeq
  boardError.value = ''
  boardLoading.value = true
  const query = period ? `?period=${encodeURIComponent(period)}` : ''
  try {
    const response = await request(`${ENDPOINT}/dashboard${query}`)
    if (!response.ok) {
      throw new Error('周期对比看板读取失败')
    }
    const payload = (await response.json()) as BoardPayload
    if (seq !== boardSeq) return // 已有更新的周期请求，丢弃过期回包
    periods.value = payload.periods ?? []
    activePeriod.value = payload.period ?? ''
    cards.value = payload.cards ?? []
    lossItems.value = payload.loss ?? []
    trend.value = payload.trend ?? []
  } catch (error) {
    if (seq !== boardSeq) return
    boardError.value = error instanceof Error ? error.message : '周期对比看板读取失败'
  } finally {
    if (seq === boardSeq) boardLoading.value = false
  }
}

function toggleReport(card: BoardCard) {
  if (expandedId.value === card.id) {
    expandedId.value = null
    detail.value = null
    return
  }
  expandedId.value = card.id
  detail.value = null
  void loadDetail(card.id)
}

async function loadDetail(id: number) {
  detailLoading.value = true
  try {
    const response = await request(`${ENDPOINT}/${id}`)
    if (!response.ok) {
      throw new Error('报告明细读取失败')
    }
    const payload = (await response.json()) as ReportDetail
    if (expandedId.value !== id) return
    detail.value = payload
  } catch (error) {
    if (expandedId.value === id) {
      boardError.value = error instanceof Error ? error.message : '报告明细读取失败'
    }
  } finally {
    if (expandedId.value === id) detailLoading.value = false
  }
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '能效报告登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('能效分析动作未生效，请稍后重试')
    }
    await reload()
    await loadBoard(activePeriod.value || undefined)
    if (expandedId.value != null) {
      await loadDetail(expandedId.value)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '能效分析操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('能效报告列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '能效分析列表读取失败'
  }
}

onMounted(() => {
  void loadBoard()
  void reload()
})
</script>

<style scoped>
.board { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; }
.board-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.board-head h3 { margin: 0; font-size: 15px; }
.period-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.period-tab { border: 1px solid var(--border); background: #fff; border-radius: 999px; padding: 4px 14px; cursor: pointer; font-size: 13px; }
.period-tab.active { background: var(--brand); border-color: var(--brand); color: #fff; }
.board .stat-row { margin: 12px 0; }
.card-row { display: flex; gap: 12px; flex-wrap: wrap; }
.report-card { flex: 1; min-width: 220px; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 6px; }
.report-card.expanded { border-color: var(--brand); box-shadow: 0 0 0 1px var(--brand); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.station-link { font-size: 14px; font-weight: 600; }
.status-badge { font-size: 12px; border-radius: 999px; padding: 2px 10px; }
.status-badge.is-pending { background: #f1f5f9; color: #64748b; }
.status-badge.is-created { background: #e0ecff; color: #1f6feb; }
.status-badge.is-reviewed { background: #dcfce7; color: #15803d; }
.status-badge.is-archived { background: #ede9fe; color: #6d28d9; }
.eff-value { font-size: 26px; }
.eff-label { font-size: 12px; color: var(--muted); margin-top: -6px; }
.card-meta { display: flex; gap: 16px; margin: 0; }
.card-meta dt { font-size: 12px; color: var(--muted); }
.card-meta dd { margin: 0; font-size: 13px; }
.card-loss { list-style: none; margin: 0; padding: 6px 0 0; border-top: 1px dashed var(--border); font-size: 12px; display: flex; flex-direction: column; gap: 3px; }
.card-loss li { display: flex; justify-content: space-between; }
.uncat-text { color: #b45309; }
.empty-loss { color: var(--muted); }
.card-toggle { align-self: flex-start; }
.board-empty { width: 100%; margin: 8px 0; }
.report-detail { margin-top: 12px; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; background: #fbfcfe; }
.detail-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }
.detail-head h4 { margin: 0 0 8px; font-size: 14px; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px 16px; margin: 0 0 10px; }
.detail-grid dt { font-size: 12px; color: var(--muted); }
.detail-grid dd { margin: 0; font-size: 13px; }
.detail-loss h5 { margin: 0 0 6px; font-size: 13px; }
.detail-loss ul { list-style: none; margin: 0; padding: 0; display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; }
.detail-loss li { display: flex; gap: 6px; }
.trend-row { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
.trend-card { flex: 1; min-width: 240px; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }
.trend-card h4 { margin: 0 0 10px; font-size: 13px; }
.trend-bars { display: flex; align-items: flex-end; gap: 10px; }
.trend-bar { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; border: none; background: none; cursor: pointer; padding: 0; }
.trend-value { font-size: 12px; color: var(--muted); }
.trend-track { width: 60%; height: 90px; display: flex; align-items: flex-end; background: #f1f5f9; border-radius: 4px; }
.trend-fill { width: 100%; background: var(--brand); border-radius: 4px; }
.trend-bar.active .trend-fill { background: #f59e0b; }
.trend-label { font-size: 12px; color: var(--muted); }
.loss-bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.loss-bars li { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.loss-reason { width: 64px; flex: none; }
.loss-track { flex: 1; height: 10px; background: #f1f5f9; border-radius: 5px; overflow: hidden; }
.loss-fill { display: block; height: 100%; background: #f97316; border-radius: 5px; }
.loss-bars li.uncat .loss-fill { background: #b45309; }
.loss-bars li.uncat .loss-reason { color: #b45309; font-weight: 600; }
.loss-value { width: 90px; text-align: right; flex: none; color: var(--muted); }
.status-trend { display: flex; flex-direction: column; gap: 8px; }
.status-row { display: flex; align-items: center; gap: 8px; border: none; background: none; cursor: pointer; padding: 2px 4px; border-radius: 4px; text-align: left; width: 100%; }
.status-row.active { background: #eff6ff; }
.status-row .trend-label { width: 56px; flex: none; }
.status-stack { flex: 1; display: flex; height: 12px; border-radius: 6px; overflow: hidden; background: #f1f5f9; }
.status-seg { display: block; height: 100%; }
.status-seg.is-pending, .legend-dot.is-pending { background: #cbd5e1; }
.status-seg.is-created, .legend-dot.is-created { background: #60a5fa; }
.status-seg.is-reviewed, .legend-dot.is-reviewed { background: #34d399; }
.status-seg.is-archived, .legend-dot.is-archived { background: #a78bfa; }
.status-count { font-size: 12px; color: var(--muted); flex: none; }
.status-legend { display: flex; gap: 10px; margin-top: 8px; font-size: 12px; color: var(--muted); flex-wrap: wrap; }
.legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
</style>
