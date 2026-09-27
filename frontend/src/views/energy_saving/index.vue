<template>
  <section class="page" data-module="energy_saving">
    <header class="page-head">
      <div>
        <h2>能效分析管理</h2>
        <p class="page-desc">按分析周期对比系统效率、损失构成与报告状态，点击电站编号或周期可展开对应能效报告。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记能效报告</button>
        <button class="btn" type="button" @click="exportRows">导出能效分析清单</button>
      </div>
    </header>

    <section class="board">
      <div class="board-head">
        <h3 class="board-title">周期对比看板</h3>
        <div class="period-tabs">
          <button
            v-for="period in board.periods"
            :key="period"
            class="period-tab"
            :class="{ active: period === board.period }"
            type="button"
            @click="switchPeriod(period)"
          >
            {{ period }}
          </button>
          <span v-if="!board.periods.length" class="board-empty">暂无分析周期</span>
        </div>
      </div>

      <p v-if="boardError" class="error-text">{{ boardError }}</p>

      <div class="board-cards" :class="{ loading: boardLoading }">
        <article class="board-card">
          <span class="stat-label">系统效率 · {{ board.period || '—' }}</span>
          <strong class="board-eff">{{ fmtPercent(board.cards.系统效率) }}</strong>
          <dl class="board-kv">
            <div><dt>理论发电量</dt><dd>{{ fmtNum(board.cards.理论发电量) }} kWh</dd></div>
            <div><dt>实际发电量</dt><dd>{{ fmtNum(board.cards.实际发电量) }} kWh</dd></div>
            <div><dt>损失电量</dt><dd>{{ fmtNum(board.cards.损失电量) }} kWh</dd></div>
          </dl>
        </article>

        <article class="board-card">
          <span class="stat-label">损失构成 · {{ board.period || '—' }}</span>
          <ul v-if="board.loss.length" class="loss-list">
            <li v-for="item in board.loss" :key="item.原因">
              <div class="loss-row">
                <span class="loss-reason" :class="{ uncategorized: item.原因 === UNCATEGORIZED }">{{ item.原因 }}</span>
                <span class="loss-value">{{ fmtNum(item.损失电量) }} kWh · {{ item.占比 }}%</span>
              </div>
              <div class="loss-bar">
                <i class="loss-fill" :class="{ uncategorized: item.原因 === UNCATEGORIZED }" :style="{ width: `${item.占比}%` }"></i>
              </div>
            </li>
          </ul>
          <p v-else class="board-empty">该周期暂无损失构成数据</p>
        </article>

        <article class="board-card">
          <span class="stat-label">报告状态 · {{ board.period || '—' }}</span>
          <ul class="status-list">
            <li v-for="status in statuses" :key="status">
              <span>{{ status }}</span>
              <strong>{{ board.status[status] ?? 0 }}</strong>
            </li>
          </ul>
          <p class="board-note">本周期共 {{ board.cards.报告数 }} 份报告</p>
        </article>
      </div>

      <div class="trend" :class="{ loading: boardLoading }">
        <span class="stat-label">系统效率趋势（点击周期查看该周期报告）</span>
        <div v-if="board.trend.length" class="trend-chart">
          <button
            v-for="point in board.trend"
            :key="point.分析周期"
            class="trend-item"
            :class="{ active: point.分析周期 === board.period }"
            type="button"
            @click="switchPeriod(point.分析周期)"
          >
            <span class="trend-value">{{ fmtPercent(point.系统效率) }}</span>
            <span class="trend-bar">
              <i class="trend-fill" :style="{ height: point.系统效率 == null ? '0%' : `${point.系统效率}%` }"></i>
            </span>
            <span class="trend-label">{{ point.分析周期 }}</span>
            <span class="trend-sub">损失 {{ fmtNum(point.损失电量) }} kWh · {{ point.报告数 }} 份</span>
          </button>
        </div>
        <p v-else class="board-empty">暂无趋势数据</p>
      </div>

      <div class="board-reports">
        <span class="stat-label">{{ board.period || '—' }} 周期报告（点击电站编号展开报告）</span>
        <ul v-if="board.reports.length" class="report-list">
          <li v-for="report in board.reports" :key="report.id" class="report-item">
            <button class="report-head" type="button" @click="toggleReport(report.id)">
              <span class="report-plant">{{ report.电站编号 }}</span>
              <span>{{ report.报告编号 }}</span>
              <span>系统效率 {{ fmtPercent(report.系统效率) }}</span>
              <span class="report-status">{{ report.报告状态 }}</span>
              <span class="report-toggle">{{ expandedId === report.id ? '收起' : '展开' }}</span>
            </button>
            <div v-if="expandedId === report.id" class="report-detail">
              <p v-if="detailLoading" class="board-empty">报告明细加载中…</p>
              <template v-else-if="detail">
                <dl class="detail-grid">
                  <div><dt>报告编号</dt><dd>{{ detail.报告编号 ?? '—' }}</dd></div>
                  <div><dt>电站编号</dt><dd>{{ detail.电站编号 ?? '—' }}</dd></div>
                  <div><dt>分析周期</dt><dd>{{ detail.分析周期 ?? '—' }}</dd></div>
                  <div><dt>理论发电量</dt><dd>{{ fmtNum(detail.理论发电量) }} kWh</dd></div>
                  <div><dt>实际发电量</dt><dd>{{ fmtNum(detail.实际发电量) }} kWh</dd></div>
                  <div><dt>系统效率</dt><dd>{{ fmtPercent(detail.系统效率) }}</dd></div>
                  <div><dt>报告状态</dt><dd>{{ detail.status ?? '—' }}</dd></div>
                  <div><dt>损失分析</dt><dd>{{ detail.损失分析 || '—' }}</dd></div>
                </dl>
                <ul v-if="detail.损失构成?.length" class="loss-list detail-loss">
                  <li v-for="item in detail.损失构成" :key="item.原因">
                    <div class="loss-row">
                      <span class="loss-reason" :class="{ uncategorized: item.原因 === UNCATEGORIZED }">{{ item.原因 }}</span>
                      <span class="loss-value">{{ fmtNum(item.损失电量) }} kWh · {{ item.占比 }}%</span>
                    </div>
                    <div class="loss-bar">
                      <i class="loss-fill" :class="{ uncategorized: item.原因 === UNCATEGORIZED }" :style="{ width: `${item.占比}%` }"></i>
                    </div>
                  </li>
                </ul>
                <p v-else class="board-empty">该报告暂无损失构成数据</p>
              </template>
              <p v-else class="error-text">{{ detailError || '报告明细读取失败' }}</p>
            </div>
          </li>
        </ul>
        <p v-else class="board-empty">该周期暂无能效报告</p>
      </div>
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
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

type LossItem = { 原因: string; 损失电量: number; 占比: number }
type TrendPoint = { 分析周期: string; 系统效率: number | null; 损失电量: number; 报告数: number }
type BoardReport = { id: number; 报告编号: string; 电站编号: string; 分析周期: string; 系统效率: number | string | null; 报告状态: string }
type Board = {
  periods: string[]
  period: string
  cards: { 系统效率: number | null; 理论发电量: number; 实际发电量: number; 损失电量: number; 报告数: number }
  loss: LossItem[]
  status: Record<string, number>
  trend: TrendPoint[]
  reports: BoardReport[]
}
type ReportDetail = {
  报告编号?: string
  电站编号?: string
  分析周期?: string
  理论发电量?: number | string
  实际发电量?: number | string
  系统效率?: number | string
  损失分析?: string
  status?: string
  损失构成?: LossItem[]
}

const ENDPOINT = '/api/energy_saving'
const UNCATEGORIZED = '未分类'
const columns = ["报告编号", "电站编号", "分析周期", "理论发电量", "实际发电量", "系统效率", "损失分析", "报告状态"]
const actions = ["生成报告", "审阅确认", "归档报告"]
const statuses = ["待生成", "已生成", "已审阅", "已归档"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const board = ref<Board>(emptyBoard())
const boardLoading = ref(false)
const boardError = ref('')
const expandedId = ref<number | null>(null)
const detail = ref<ReportDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')

function emptyBoard(): Board {
  return {
    periods: [],
    period: '',
    cards: { 系统效率: null, 理论发电量: 0, 实际发电量: 0, 损失电量: 0, 报告数: 0 },
    loss: [],
    status: {},
    trend: [],
    reports: [],
  }
}

function fmtNum(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  const num = Number(value)
  return Number.isFinite(num) ? num.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) : '—'
}

function fmtPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toLocaleString('zh-CN', { maximumFractionDigits: 1 })}%` : '—'
}

function switchPeriod(period: string) {
  if (period === board.value.period || boardLoading.value) {
    return
  }
  // 先清空再拉取：新周期数据回来之前不展示上一周期的数字
  board.value = { ...emptyBoard(), periods: board.value.periods, period }
  expandedId.value = null
  detail.value = null
  void loadBoard(period)
}

async function loadBoard(period?: string) {
  boardLoading.value = true
  boardError.value = ''
  try {
    const query = period ? `?period=${encodeURIComponent(period)}` : ''
    const response = await request(`${ENDPOINT}/dashboard${query}`)
    if (!response.ok) {
      throw new Error('能效看板数据读取失败')
    }
    board.value = (await response.json()) as Board
  } catch (error) {
    board.value = emptyBoard()
    boardError.value = error instanceof Error ? error.message : '能效看板数据读取失败'
  } finally {
    boardLoading.value = false
  }
}

async function toggleReport(id: number) {
  if (expandedId.value === id) {
    expandedId.value = null
    detail.value = null
    return
  }
  expandedId.value = id
  detail.value = null
  detailError.value = ''
  detailLoading.value = true
  try {
    const response = await request(`${ENDPOINT}/${id}`)
    if (!response.ok) {
      throw new Error('报告明细读取失败')
    }
    detail.value = (await response.json()) as ReportDetail
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : '报告明细读取失败'
  } finally {
    detailLoading.value = false
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
    await Promise.all([reload(), loadBoard(board.value.period || undefined)])
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
  void reload()
  void loadBoard()
})
</script>

<style scoped>
.board { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; }
.board-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.board-title { margin: 0; font-size: 15px; }
.period-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.period-tab { border: 1px solid var(--border); background: #fff; border-radius: 14px; padding: 4px 12px; cursor: pointer; font-size: 12px; }
.period-tab.active { background: var(--brand); border-color: var(--brand); color: #fff; }
.board-cards { display: flex; gap: 12px; align-items: stretch; }
.board-cards.loading, .trend.loading { opacity: 0.45; pointer-events: none; }
.board-card { flex: 1; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; min-width: 0; }
.board-eff { display: block; font-size: 26px; margin: 4px 0 8px; }
.board-kv { margin: 0; display: flex; flex-direction: column; gap: 4px; }
.board-kv div { display: flex; justify-content: space-between; font-size: 12px; }
.board-kv dt { color: var(--muted); }
.board-kv dd { margin: 0; }
.loss-list { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.loss-row { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 2px; }
.loss-reason.uncategorized { color: #b42318; }
.loss-value { color: var(--muted); }
.loss-bar { height: 6px; background: #eef2f7; border-radius: 3px; overflow: hidden; }
.loss-fill { display: block; height: 100%; background: var(--brand); }
.loss-fill.uncategorized { background: #f04438; }
.status-list { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.status-list li { display: flex; justify-content: space-between; font-size: 13px; }
.board-note { margin: 8px 0 0; font-size: 12px; color: var(--muted); }
.board-empty { color: var(--muted); font-size: 12px; margin: 8px 0 0; }
.trend { margin-top: 12px; }
.trend-chart { display: flex; gap: 10px; margin-top: 8px; }
.trend-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; border: 1px solid var(--border); border-radius: 8px; background: #fff; padding: 8px 6px; cursor: pointer; }
.trend-item.active { border-color: var(--brand); box-shadow: 0 0 0 1px var(--brand); }
.trend-value { font-size: 13px; font-weight: 600; }
.trend-bar { height: 96px; width: 22px; background: #eef2f7; border-radius: 4px; display: flex; align-items: flex-end; overflow: hidden; }
.trend-fill { display: block; width: 100%; background: var(--brand); }
.trend-label { font-size: 12px; }
.trend-sub { font-size: 11px; color: var(--muted); }
.board-reports { margin-top: 12px; }
.report-list { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.report-head { width: 100%; display: flex; gap: 16px; align-items: center; border: 1px solid var(--border); border-radius: 6px; background: #fff; padding: 8px 10px; cursor: pointer; font-size: 13px; text-align: left; }
.report-plant { color: var(--brand); font-weight: 600; }
.report-status { margin-left: auto; color: var(--muted); }
.report-toggle { color: var(--muted); font-size: 12px; }
.report-detail { border: 1px solid var(--border); border-top: none; border-radius: 0 0 6px 6px; padding: 10px 12px; background: #fbfcfe; }
.detail-grid { margin: 0; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px 16px; }
.detail-grid dt { font-size: 12px; color: var(--muted); }
.detail-grid dd { margin: 2px 0 0; font-size: 13px; }
.detail-loss { margin-top: 10px; max-width: 480px; }
</style>
