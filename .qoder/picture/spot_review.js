// spot_review 工具 - 现货算法复盘分析（全组合对比版）
// 导出: initSpotReview(), resizeSpotReviewCharts()

const SPOT_API = "/api/tools/spot_review";

let srCurvesChart = null;
let srDetailChart = null;
let srHeatmapChart = null;
let srRankChart = null;          // 每日排名热力图
let srDailyAmountChart = null;   // 每日收益金额热力图
let srStabilityChart = null;     // 组合稳定性散点图
let _allData = null;         // 缓存全组合查询结果
let _validCombos = null;   // 当前有效组合（已排序）
let _invalidCombos = null;  // 无有效数据组合
let _currentSort = 'rankLcb';    // 当前排行排序字段（默认按悲观排名，稳定靠前优先）
let _sortAsc = true;               // 当前排序方向（false=降序，true=升序）
// 排序默认方向为升序（越小越好）的字段
const SORT_ASC_FIELDS = new Set(['rankMean', 'rankStd', 'rankLcb', 'rankBottomRate']);
let _rankChartMode = 'heatmap';    // 排名图表模式：heatmap / line
let _tableExpanded = false;        // 排行榜是否已展开
const TABLE_COLLAPSE_ROWS = 30;    // 排行榜默认显示行数

// 交易中心 → VPP / 默认时间间隔 配置
const TRADE_CENTER_CONFIG = {
  '1': { name: '广东', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '3': { name: '浙江', interval: 30, vpps: [
    { id: '1', name: '万帮' },
    { id: '8f3af8ed-b12b-451e-929c-88c46e9b892a', name: '建德' },
    { id: '58eb1e82-cfbe-49fe-893c-e04fe7f7b474', name: '吴兴' },
  ]},
  '4': { name: '安徽', interval: 60, vpps: [
    { id: '1', name: '万帮' },
    { id: '52c36c32-1774-413c-b9ec-f307367f6fb2', name: '霍邱' },
  ]},
  '5': { name: '山东', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '12': { name: '重庆', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '22': { name: '陕西', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '27': { name: '海南', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '28': { name: '云南', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '33': { name: '贵州', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
  '34': { name: '湖南', interval: 60, vpps: [{ id: '1', name: '万帮' }] },
};

// ==================== 初始化 ====================

async function initSpotReview() {
  const yesterday = new Date(Date.now() - 24 * 3600000);
  const ago30 = new Date(yesterday.getTime() - 30 * 24 * 3600000);
  $("#sr-end").value = fmtDateSR(yesterday);
  $("#sr-start").value = fmtDateSR(ago30);
  srHighlightActiveDateBtn(30);

  $("#btn-sr-query").onclick = queryAllCombinations;

  // 交易中心切换时联动更新 VPP、默认时间间隔、风险偏好
  $("#sr-trade-center").onchange = onTradeCenterChange;
  await onTradeCenterChange(); // 初始化

  // 表头点击排序——状态管理全部由 switchSort 内部处理
  document.querySelectorAll('#sr-daily-table th.sr-sortable').forEach(th => {
    th.addEventListener('click', () => {
      const field = th.dataset.sort;
      if (field) switchSort(field);
    });
  });
}

async function onTradeCenterChange() {
  const tcId = $("#sr-trade-center").value;
  const config = TRADE_CENTER_CONFIG[tcId];
  if (!config) return;

  // 更新 VPP 下拉框
  const vppSel = $("#sr-vpp-id");
  vppSel.innerHTML = '';
  config.vpps.forEach(v => {
    vppSel.innerHTML += `<option value="${v.id}">${v.name}</option>`;
  });

  // 更新默认时间间隔
  $("#sr-interval").value = String(config.interval);

  // 加载风险偏好列表（含套利比例）
  await loadRiskPreferences(tcId);
}

async function loadRiskPreferences(tradeCenterId) {
  const riskSel = $("#sr-risk");
  try {
    const result = await api(`${SPOT_API}/risk-preferences?tradeCenterId=${tradeCenterId}`, {
      method: 'POST',
    });
    if (!result.success || !result.preferences || result.preferences.length === 0) {
      console.warn('加载风险偏好失败:', result.error);
      return;
    }
    riskSel.innerHTML = '';
    result.preferences.forEach(p => {
      const ratio = p.arbitrageRatio != null ? (p.arbitrageRatio * 100).toFixed(0) + '%' : '-';
      const label = `${p.meaning}（套利比例 ${ratio}）`;
      const selected = p.type === 'aggressiveModel' ? ' selected' : '';
      riskSel.innerHTML += `<option value="${p.type}"${selected}>${label}</option>`;
    });
  } catch (e) {
    console.warn('加载风险偏好异常:', e.message);
  }
}

function resizeSpotReviewCharts() {
  if (srCurvesChart) srCurvesChart.resize();
  if (srDetailChart) srDetailChart.resize();
  if (srHeatmapChart) srHeatmapChart.resize();
  if (srRankChart) srRankChart.resize();
  if (srDailyAmountChart) srDailyAmountChart.resize();
  if (srStabilityChart) srStabilityChart.resize();
}

function fmtDateSR(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

// ==================== 快捷日期 ====================

function srSetDateRange(range) {
  const yesterday = new Date(Date.now() - 24 * 3600000);
  let start, end = yesterday;

  if (range === 'month') {
    start = new Date(yesterday.getFullYear(), yesterday.getMonth(), 1);
  } else if (range === 'lastMonth') {
    start = new Date(yesterday.getFullYear(), yesterday.getMonth() - 1, 1);
    end = new Date(yesterday.getFullYear(), yesterday.getMonth(), 0);
  } else {
    start = new Date(yesterday.getTime() - range * 24 * 3600000);
  }

  $("#sr-start").value = fmtDateSR(start);
  $("#sr-end").value = fmtDateSR(end);
  srHighlightActiveDateBtn(range);
}

function srHighlightActiveDateBtn(range) {
  document.querySelectorAll('.sr-quick-date-btn').forEach(btn => btn.classList.remove('active'));
  const labels = { 7: '近7天', 30: '近30天', 90: '近90天', month: '本月', lastMonth: '上月' };
  document.querySelectorAll('.sr-quick-date-btn').forEach(btn => {
    if (btn.textContent === labels[range]) btn.classList.add('active');
  });
}

// ==================== 全组合查询 ====================

async function queryAllCombinations() {
  const startDate = $("#sr-start").value;
  const endDate = $("#sr-end").value;
  if (!startDate || !endDate) { toast("请选择日期范围", true); return; }

  // 风险偏好下拉框异步加载，未就绪时禁止查询（否则会以空参数请求，上游返回全 0 收益）
  const riskValue = $("#sr-risk").value;
  if (!riskValue) { toast("风险偏好尚未加载完成，请稍后再试", true); return; }

  const payload = {
    startDate,
    endDate,
    tradeCenterId: $("#sr-trade-center").value,
    vppId: $("#sr-vpp-id").value,
    interval: parseInt($("#sr-interval").value),
    riskPreference: riskValue,
  };

  // 显示进度条
  const progressBar = $("#sr-progress-bar");
  const progressFill = $("#sr-progress-fill");
  const progressText = $("#sr-progress-text");
  progressBar.style.display = 'block';
  progressFill.style.width = '0%';
  progressText.textContent = '正在获取模型列表，准备查询...';

  try {
    const resp = await fetch(`/api/tools/spot_review/all-combinations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result = null;
    let totalCombos = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // 保留未完成的行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const eventData = JSON.parse(line.slice(6));

          if (eventData.type === 'meta') {
            totalCombos = eventData.totalCombinations;
            progressText.textContent = `已返回 0/${totalCombos} 组合...`;
          } else if (eventData.type === 'progress') {
            const pct = Math.round(eventData.completed / eventData.total * 100);
            progressFill.style.width = pct + '%';
            progressText.textContent = `已返回 ${eventData.completed}/${eventData.total} 组合 (${pct}%)`;
          } else if (eventData.type === 'result') {
            result = eventData;
          }
        }
      }
    }

    if (!result || !result.success) {
      toast("查询失败: " + (result?.error || '未知错误'), true);
      return;
    }

    _allData = result;
    // 有效组合：hasValidData=true 才参与排名；其余归入“无有效数据”区
    const allSuccess = result.combinations.filter(c => c.success);
    _validCombos = allSuccess.filter(c => c.hasValidData);
    _invalidCombos = allSuccess.filter(c => !c.hasValidData);

    if (_validCombos.length === 0 && _invalidCombos.length > 0) {
      toast("所有组合均无有效数据（收益全为0或null）", true);
      renderRankingTable([], _invalidCombos);
      return;
    }
    if (_validCombos.length === 0) {
      toast("所有组合均未返回数据", true);
      return;
    }

    // 计算排名稳定性指标（平均排名/波动/前10%率/爆雷率/LCB 悲观排名）
    computeRankStability(_validCombos);
    // 默认按悲观排名升序：稳定靠前的组合排在最前（避免累计收益“撞大运”误导）
    _currentSort = 'rankLcb';
    _sortAsc = true;
    applySort(_validCombos, _currentSort, _sortAsc);
    updateSortUI();

    renderSummaryMetrics(result, _validCombos);
    renderAnalysisConclusion(result, _validCombos);
    renderCurvesChart(result, _validCombos);
    renderDailyAmountChart(result, _validCombos);
    renderDailyRankingChart(result, _validCombos);
    renderStabilityChart(_validCombos);
    renderHeatmap(result, _validCombos);
    _tableExpanded = false;
    renderRankingTable(_validCombos, _invalidCombos);
    toast(`成功查询 ${result.successCombinations}/${result.totalCombinations} 个组合${_invalidCombos.length ? `，${_invalidCombos.length} 个无有效数据已排除` : ''}`);
  } catch (e) {
    toast("请求异常: " + e.message, true);
  } finally {
    // 隐藏进度条
    setTimeout(() => { progressBar.style.display = 'none'; }, 1500);
  }
}

// ==================== 排序工具 ====================

function applySort(combos, field, asc) {
  const dir = asc ? 1 : -1;
  combos.sort((a, b) => {
    // null/缺失值一律沉底（升序视作 +∞，降序视作 −∞）
    const va = a[field] != null ? a[field] : (asc ? Infinity : -Infinity);
    const vb = b[field] != null ? b[field] : (asc ? Infinity : -Infinity);
    return (va - vb) * dir;
  });
}

function switchSort(field) {
  if (!_validCombos) return;
  // 确定排序方向：同字段切换方向；新字段默认方向按字段语义（排名类越小越好，其余越大越好）
  if (field === _currentSort) {
    _sortAsc = !_sortAsc;
  } else {
    _currentSort = field;
    _sortAsc = SORT_ASC_FIELDS.has(field);
  }
  applySort(_validCombos, _currentSort, _sortAsc);
  updateSortUI();
  renderCurvesChart(_allData, _validCombos);
  renderDailyAmountChart(_allData, _validCombos);
  renderDailyRankingChart(_allData, _validCombos);
  renderStabilityChart(_validCombos);
  renderHeatmap(_allData, _validCombos);
  _tableExpanded = false;
  renderRankingTable(_validCombos, _invalidCombos);
}

function updateSortUI() {
  // 更新表头高亮和箭头——直接用 data-label 拼接箭头，不再正则替换 textContent
  document.querySelectorAll('#sr-daily-table th.sr-sortable').forEach(th => {
    const field = th.dataset.sort;
    const label = th.dataset.label;
    if (!label) return;
    const isActive = field === _currentSort;
    th.classList.toggle('sr-sort-active-th', isActive);
    if (isActive) {
      th.textContent = label + (_sortAsc ? ' ↑' : ' ↓');
    } else {
      th.textContent = label + ' ↕';
    }
  });

  // 更新排序指示器
  const indicator = document.getElementById('sr-sort-indicator');
  if (indicator) {
    const th = document.querySelector(`#sr-daily-table th[data-sort="${_currentSort}"]`);
    const label = th ? th.dataset.label : _currentSort;
    indicator.textContent = `当前排序: ${label} ${_sortAsc ? '↑' : '↓'}`;
  }
}

function toggleTableExpand() {
  if (!_validCombos) return;
  _tableExpanded = !_tableExpanded;
  renderRankingTable(_validCombos, _invalidCombos);
}

function switchRankChartMode(mode) {
  if (!_validCombos) return;
  _rankChartMode = mode;
  document.querySelectorAll('.sr-sort-btn[data-rank-mode]').forEach(btn => {
    btn.classList.toggle('sr-sort-active', btn.dataset.rankMode === mode);
  });
  // 更新提示文字
  const hint = document.getElementById('sr-rank-hint');
  if (hint) {
    hint.textContent = mode === 'heatmap'
      ? '每格=该组合当日策略收益在所有组合中的排名 | 颜色越绿名次越前 | 点击单元格查看详情'
      : '每条线=一个组合每日的排名变化 | Y轴倒置（第1名在顶部） | 绿色=Top3 | 红色=Bottom3';
  }
  renderDailyRankingChart(_allData, _validCombos);
}

// ==================== 汇总指标 ====================

function renderSummaryMetrics(result, combos) {
  // 始终按超额收益排序，不受表头排序影响
  const byExcess = [...combos].sort((a, b) => (b.excessProfit ?? 0) - (a.excessProfit ?? 0));
  const best = byExcess[0];
  const worst = byExcess[byExcess.length - 1];
  const actualTotal = result?.fullActualProfit ?? (best?.totalActualProfit ?? 0);
  const avgExcess = combos.reduce((s, c) => s + c.excessProfit, 0) / combos.length;

  $("#sr-metrics").innerHTML = `
    <div class="metric-card">
      <div class="metric-value ${(actualTotal >= 0 ? 'positive' : 'negative')}">${(actualTotal / 10000).toFixed(2)}万</div>
      <div class="metric-label">累计实际收益</div>
    </div>
    <div class="metric-card">
      <div class="metric-value positive">${(best.excessProfit / 10000).toFixed(2)}万</div>
      <div class="metric-label">最优组合超额</div>
    </div>
    <div class="metric-card">
      <div class="metric-value negative">${(worst.excessProfit / 10000).toFixed(2)}万</div>
      <div class="metric-label">最差组合超额</div>
    </div>
    <div class="metric-card">
      <div class="metric-value ${(avgExcess >= 0 ? 'positive' : 'negative')}">${(avgExcess / 10000).toFixed(2)}万</div>
      <div class="metric-label">平均超额收益</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">${result.successCombinations}/${result.totalCombinations}</div>
      <div class="metric-label">成功/总组合数</div>
    </div>
  `;
}

// ==================== 自动分析结论 ====================

function renderAnalysisConclusion(result, combos) {
  const container = $("#sr-analysis");
  const content = $("#sr-analysis-content");
  if (!combos.length) { container.style.display = 'none'; return; }

  // 始终按超额收益排序取最优/最差，不受当前表头排序影响
  const byExcess = [...combos].sort((a, b) => (b.excessProfit ?? 0) - (a.excessProfit ?? 0));
  const best = byExcess[0];
  const worst = byExcess[byExcess.length - 1];
  const totalCombos = combos.length;
  const positiveCount = combos.filter(c => c.excessProfit > 0).length;
  const positiveRatio = (positiveCount / totalCombos * 100).toFixed(1);

  // 按负荷模型分组统计平均超额
  const loadGroups = {};
  combos.forEach(c => {
    if (!loadGroups[c.loadModelName]) loadGroups[c.loadModelName] = [];
    loadGroups[c.loadModelName].push(c.excessProfit);
  });
  const loadAvg = {};
  Object.entries(loadGroups).forEach(([name, arr]) => {
    loadAvg[name] = arr.reduce((s, v) => s + v, 0) / arr.length;
  });
  const bestLoad = Object.entries(loadAvg).sort((a, b) => b[1] - a[1])[0];
  const worstLoad = Object.entries(loadAvg).sort((a, b) => a[1] - b[1])[0];

  // 按价差模型分组统计平均超额
  const priceGroups = {};
  combos.forEach(c => {
    if (!priceGroups[c.priceModelName]) priceGroups[c.priceModelName] = [];
    priceGroups[c.priceModelName].push(c.excessProfit);
  });
  const priceAvg = {};
  Object.entries(priceGroups).forEach(([name, arr]) => {
    priceAvg[name] = arr.reduce((s, v) => s + v, 0) / arr.length;
  });
  const bestPrice = Object.entries(priceAvg).sort((a, b) => b[1] - a[1])[0];
  const worstPrice = Object.entries(priceAvg).sort((a, b) => a[1] - b[1])[0];

  // 负荷模型胜率统计
  const loadWinRate = {};
  Object.entries(loadGroups).forEach(([name, arr]) => {
    const matching = combos.filter(c => c.loadModelName === name);
    const avgWinRate = matching.reduce((s, c) => s + c.winRate, 0) / matching.length;
    loadWinRate[name] = avgWinRate;
  });
  const mostStableLoad = Object.entries(loadWinRate).sort((a, b) => b[1] - a[1])[0];

  // 价差模型稳定性（胜率标准差越小越稳定）
  const priceWinRate = {};
  Object.entries(priceGroups).forEach(([name, arr]) => {
    const matching = combos.filter(c => c.priceModelName === name);
    const avgWinRate = matching.reduce((s, c) => s + c.winRate, 0) / matching.length;
    priceWinRate[name] = avgWinRate;
  });
  const mostStablePrice = Object.entries(priceWinRate).sort((a, b) => b[1] - a[1])[0];

  // 总体判断
  const actualTotal = result?.fullActualProfit ?? (best.totalActualProfit ?? 0);
  const overallVerdict = best.excessProfit > 0
    ? `<span style="color:#16a34a;font-weight:600">✅ 存在有效组合</span>（最优超额 +${(best.excessProfit/10000).toFixed(2)}万）`
    : `<span style="color:#dc2626;font-weight:600">⚠️ 所有组合均未跑赢实际</span>`;

  // 统计有效天数与无数据天数（取最优组合为参考）
  const refCombo = best;
  const totalRange = refCombo?.dailyData?.length ?? 0;
  const effectiveDays = refCombo?.totalDays ?? totalRange;
  const noDataDays = refCombo?.noDataDays ?? 0;

  const html = `
    <div style="margin-bottom:16px">
      <b>总体判断：</b>在 ${totalCombos} 个组合中，${positiveCount} 个 (${positiveRatio}%) 产生正超额收益。
      ${overallVerdict}
      ${noDataDays > 0 ? `<span style="color:#94a3b8;font-size:12px;margin-left:8px">统计区间 ${totalRange} 天，其中 ${noDataDays} 天无效(无数据或收益为0)已排除</span>` : ''}
    </div>
    <div style="margin-bottom:16px">
      <b>最优组合：</b><code>${best.loadModelName}</code> × <code>${best.priceModelName}</code>
      ，超额收益 <span class="${best.excessProfit >= 0 ? 'positive' : 'negative'}">${(best.excessProfit/10000).toFixed(2)}万</span>，
      胜率 ${best.winRate}%（${best.winDays}/${best.totalDays}天跑赢）${best.noDataDays ? `<span style="color:#94a3b8;font-size:11px">，另有 ${best.noDataDays} 天无效</span>` : ''}
    </div>
    <div style="margin-bottom:16px">
      <b>负荷模型分析：</b>
      <ul style="margin:4px 0;padding-left:20px">
        <li>平均超额最高：<code>${bestLoad[0]}</code>（平均超额 ${(bestLoad[1]/10000).toFixed(2)}万）</li>
        <li>胜率最稳定：<code>${mostStableLoad[0]}</code>（平均胜率 ${mostStableLoad[1].toFixed(1)}%）</li>
        ${worstLoad[0] !== bestLoad[0] ? `<li>平均最差：<code>${worstLoad[0]}</code>（平均超额 ${(worstLoad[1]/10000).toFixed(2)}万）</li>` : ''}
      </ul>
    </div>
    <div style="margin-bottom:16px">
      <b>价差模型分析：</b>
      <ul style="margin:4px 0;padding-left:20px">
        <li>平均超额最高：<code>${bestPrice[0]}</code>（平均超额 ${(bestPrice[1]/10000).toFixed(2)}万）</li>
        <li>胜率最稳定：<code>${mostStablePrice[0]}</code>（平均胜率 ${mostStablePrice[1].toFixed(1)}%）</li>
        ${worstPrice[0] !== bestPrice[0] ? `<li>平均最差：<code>${worstPrice[0]}</code>（平均超额 ${(worstPrice[1]/10000).toFixed(2)}万）</li>` : ''}
      </ul>
    </div>
    <div style="padding:10px 14px;background:#f0f9ff;border-radius:6px;border-left:3px solid #3b82f6">
      <b>推荐组合：</b>负荷模型选 <code>${mostStableLoad[0]}</code>（稳定）或 <code>${bestLoad[0]}</code>（超额高），
      价差模型选 <code>${bestPrice[0]}</code>。
      ${actualTotal > 0 ? `当前实际累计收益 ${(actualTotal/10000).toFixed(2)}万，最优组合可额外增收 ${(best.excessProfit/10000).toFixed(2)}万。` : ''}
    </div>
  `;

  content.innerHTML = html;
  container.style.display = 'block';
}

// ==================== 所有组合累计收益曲线图 ====================

// 构建“桥接”系列：用浅灰虚线连接 null 断裂段
function makeBridgeSeries(name, data, z) {
  return {
    name: name + '_bridge',
    type: 'line',
    data: data,
    symbol: 'none',
    connectNulls: true,
    lineStyle: { color: '#cbd5e1', width: 1, type: 'dashed' },
    itemStyle: { color: '#cbd5e1' },
    z: z,
    silent: true,
    tooltip: { show: false },
  };
}

function renderCurvesChart(result, combos) {
  if (!srCurvesChart) {
    srCurvesChart = echarts.init($("#sr-chart-profit"));
  }

  // 提取日期轴
  let dates = [];
  for (const c of combos) {
    if (c.dailyData && c.dailyData.length > 0) {
      dates = c.dailyData.map(d => d.date);
      break;
    }
  }

  // 计算实际收益曲线
  const actualDailyMap = {};
  (result.actualDaily || []).forEach(d => { actualDailyMap[d.date] = d.actualProfit; });

  let cumActual = 0;
  const actualArr = [];
  dates.forEach(dt => {
    const v = actualDailyMap[dt];
    if (v != null) { cumActual += v; actualArr.push(+cumActual.toFixed(2)); }
    else actualArr.push(null);
  });

  // 为每个组合计算曲线
  const seriesList = [];
  const legendData = [];
  const total = combos.length;

  combos.forEach((c, idx) => {
    const label = `${shortName(c.loadModelName)}×${shortName(c.priceModelName)}`;
    legendData.push(label);

    const dailyMap = {};
    (c.dailyData || []).forEach(d => { dailyMap[d.date] = d.strategyProfit; });

    let cum = 0;
    const arr = [];
    dates.forEach(dt => {
      const v = dailyMap[dt];
      const valid = v != null && v !== 0;
      if (valid) cum += v;
      arr.push(valid ? +cum.toFixed(2) : null);
    });

    // 配色策略
    const rank = idx + 1;
    let lineColor, lineWidth, showEndLabel = false;
    if (rank <= 3) {
      lineColor = `rgba(22, 163, 74, ${0.75 + (3 - rank) * 0.08})`;
      lineWidth = 3;
      showEndLabel = true;
    } else if (rank >= total - 2) {
      lineColor = `rgba(220, 38, 38, ${0.75 + (rank - (total - 3)) * 0.08})`;
      lineWidth = 3;
      showEndLabel = true;
    } else {
      lineColor = 'rgba(148, 163, 184, 0.25)';
      lineWidth = 1;
    }

    const seriesItem = {
      name: label,
      type: 'line',
      data: arr,
      symbol: 'none',
      connectNulls: false,
      lineStyle: { color: lineColor, width: lineWidth },
      itemStyle: { color: lineColor },
      z: rank <= 3 ? 10 : (rank >= total - 2 ? 8 : 1),
      emphasis: { lineStyle: { width: 3.5, opacity: 1 } },
    };

    if (showEndLabel) {
      seriesList.push(makeBridgeSeries(label, arr, rank <= 3 ? 9 : 7));
      seriesItem.markPoint = {
        symbol: 'circle', symbolSize: 6,
        label: { show: true, position: 'right', formatter: label, fontSize: 10, color: lineColor, offset: [4, 0] },
        data: [{ coord: [dates.length - 1, arr[arr.length - 1]], value: arr[arr.length - 1] }],
      };
    }
    seriesList.push(seriesItem);
  });

  // 实际收益桥接系列
  seriesList.unshift(makeBridgeSeries('实际收益', actualArr, 19));
  legendData.unshift('实际收益');
  seriesList.unshift({
    name: '实际收益',
    type: 'line',
    data: actualArr,
    symbol: 'none',
    connectNulls: false,
    lineStyle: { color: '#5470c6', width: 2.5, type: 'solid' },
    itemStyle: { color: '#5470c6' },
    z: 20,
  });

  srCurvesChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: function(params) {
        let s = '<b>' + params[0].axisValue + '</b><br/>';
        const filtered = params.filter(p => !p.seriesName.endsWith('_bridge'));
        const sorted = [...filtered].sort((a, b) => (b.value || 0) - (a.value || 0));
        sorted.slice(0, 10).forEach(p => {
          const val = p.value != null ? (p.value / 10000).toFixed(2) + '万' : '-';
          s += p.marker + ' ' + p.seriesName + ': ' + val + '<br/>';
        });
        if (sorted.length > 10) s += '... 共 ' + sorted.length + ' 条曲线';
        return s;
      },
      confine: true,
    },
    legend: {
      data: legendData,
      type: 'scroll', top: 0,
      pageIcons: { horizontal: ['M0,0L12,-10L12,10z', 'M0,0L-12,-10L-12,10z'] },
      pageFormatter: '{current}/{total}',
      textStyle: { fontSize: 11 }, selectedMode: 'multiple',
    },
    grid: { left: '3%', right: '15%', bottom: '8%', top: '10%', containLabel: true },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
    ],
    xAxis: {
      type: 'category', data: dates, boundaryGap: false,
      axisLabel: { rotate: 45 },
    },
    yAxis: {
      type: 'value', name: '累计收益',
      axisLabel: { formatter: v => (v / 10000).toFixed(1) + '万' },
    },
    series: seriesList,
  }, true);

  // 点击图表线高亮并跳到对应表格行
  srCurvesChart.off('click');
  srCurvesChart.on('click', function(params) {
    const name = params.seriesName;
    if (name === '实际收益') return;
    const idx = legendData.indexOf(name) - 1;
    if (idx >= 0 && idx < combos.length) {
      highlightTableRow(idx);
    }
  });

  // 双击图例反选
  enableLegendInverseSelect(srCurvesChart, legendData);
}

// 模型名称简写
function shortName(name) {
  if (!name) return '?';
  return name.replace('太乙-', '').replace('综合模型', '综合');
}

function highlightTableRow(idx) {
  $$('.sr-combo-row').forEach(r => r.classList.remove('rank-active'));
  const targetRow = document.querySelector(`.sr-combo-row[data-idx="${idx}"]`);
  if (targetRow) {
    targetRow.classList.add('rank-active');
    targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// ==================== 热力图: 负荷模型 × 价差模型 ====================

function renderHeatmap(result, combos) {
  if (!srHeatmapChart) {
    srHeatmapChart = echarts.init($("#sr-chart-heatmap"));
  }

  // 提取所有负荷模型和价差模型名称（去重保持顺序）
  const loadModels = [...new Set(combos.map(c => c.loadModelName))];
  const priceModels = [...new Set(combos.map(c => c.priceModelName))];

  // 构建热力图数据 [priceIdx, loadIdx, excessProfit]
  const heatData = [];
  let maxVal = 0;
  combos.forEach(c => {
    const li = loadModels.indexOf(c.loadModelName);
    const pi = priceModels.indexOf(c.priceModelName);
    if (li >= 0 && pi >= 0) {
      heatData.push([pi, li, c.excessProfit]);
      maxVal = Math.max(maxVal, Math.abs(c.excessProfit));
    }
  });

  srHeatmapChart.setOption({
    tooltip: {
      formatter: function(params) {
        const [pi, li, val] = params.data;
        return `<b>${loadModels[li]} × ${priceModels[pi]}</b><br/>超额收益: ${(val / 10000).toFixed(2)}万`;
      }
    },
    grid: { left: '18%', right: '12%', bottom: '6%', top: '18%' },
    xAxis: {
      type: 'category',
      data: priceModels.map(n => shortName(n)),
      axisLabel: { rotate: 45, fontSize: 11, interval: 0, overflow: 'none' },
      position: 'top',
    },
    yAxis: {
      type: 'category',
      data: loadModels.map(n => shortName(n)),
      axisLabel: { fontSize: 11 },
    },
    visualMap: {
      min: -maxVal,
      max: maxVal,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: {
        color: ['#dc2626', '#f87171', '#fecaca', '#ffffff', '#bbf7d0', '#4ade80', '#16a34a'],
      },
      formatter: v => (v / 10000).toFixed(1) + '万',
    },
    series: [{
      type: 'heatmap',
      data: heatData,
      label: {
        show: true,
        formatter: p => (p.data[2] / 10000).toFixed(2) + '万',
        fontSize: 10,
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' }
      },
    }],
  }, true);

  // 点击热力图单元格跳到对应组合详情
  srHeatmapChart.off('click');
  srHeatmapChart.on('click', function(params) {
    const [pi, li] = params.data;
    const loadName = loadModels[li];
    const priceName = priceModels[pi];
    if (!_validCombos) return;
    const idx = _validCombos.findIndex(c => c.loadModelName === loadName && c.priceModelName === priceName);
    if (idx >= 0) {
      showCombinationDetail(idx);
    }
  });
}

// ==================== 每日收益金额热力图 ====================

function renderDailyAmountChart(result, combos) {
  if (!srDailyAmountChart) {
    srDailyAmountChart = echarts.init($("#sr-chart-daily-amount"));
  }

  // 提取日期轴
  let dates = [];
  for (const c of combos) {
    if (c.dailyData && c.dailyData.length > 0) {
      dates = c.dailyData.map(d => d.date);
      break;
    }
  }
  if (!dates.length) return;

  const labels = combos.map(c => `${shortName(c.loadModelName)}×${shortName(c.priceModelName)}`);

  // 构建热力图数据 [dateIdx, comboIdx, profitAmount]
  const heatData = [];
  let maxVal = 0;
  combos.forEach((c, ci) => {
    (c.dailyData || []).forEach((d, di) => {
      const v = d.strategyProfit;
      if (v != null && v !== 0) {
        heatData.push([di, ci, v]);
        maxVal = Math.max(maxVal, Math.abs(v));
      }
    });
  });

  if (maxVal === 0) maxVal = 1; // 避免全为0时 visualMap 报错

  srDailyAmountChart.setOption({
    tooltip: {
      formatter: p => {
        const [di, ci, val] = p.data;
        return `<b>${dates[di]}</b><br/>${labels[ci]}<br/>当日收益: <b style="color:${val >= 0 ? '#16a34a' : '#dc2626'}">${(val / 10000).toFixed(2)}万</b>`;
      }
    },
    grid: { left: '22%', right: '4%', bottom: '14%', top: '4%', containLabel: false },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, start: 0, end: 100 },
      { type: 'slider', xAxisIndex: 0, start: 0, end: 100, bottom: '2%' },
    ],
    xAxis: { type: 'category', data: dates, splitArea: { show: false }, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'category', data: labels, splitArea: { show: false }, axisLabel: { fontSize: 10, width: 120, overflow: 'truncate' } },
    visualMap: {
      min: -maxVal, max: maxVal, calculable: true, orient: 'vertical', right: 0, top: 'center',
      inRange: { color: ['#dc2626', '#ef4444', '#fca5a5', '#e5e7eb', '#86efac', '#22c55e', '#16a34a'] },
      formatter: v => (v / 10000).toFixed(1) + '万',
    },
    series: [{
      type: 'heatmap', data: heatData,
      label: {
        show: combos.length <= 40,
        formatter: p => (p.data[2] / 10000).toFixed(1) + '万',
        fontSize: 9, color: '#334155',
      },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  }, true);

  srDailyAmountChart.off('click');
  srDailyAmountChart.on('click', p => {
    const ci = p.data[1];
    if (ci >= 0) showCombinationDetail(ci);
  });
}

// ==================== 每日收益排名热力图 ====================

// 每日排名矩阵计算：rankMatrix[ci][di] = rank (null 表示无效)
// 排名按每一天独立计算：当日 strategyProfit 最高者第 1 名；收益为 0/null 不参与排名
function computeRankMatrix(combos) {
  // 提取日期轴
  let dates = [];
  for (const c of combos) {
    if (c.dailyData && c.dailyData.length > 0) {
      dates = c.dailyData.map(d => d.date);
      break;
    }
  }
  const rankMatrix = Array.from({ length: combos.length }, () => Array(dates.length).fill(null));
  dates.forEach((dt, di) => {
    const dayValues = combos.map((c, ci) => {
      const d = (c.dailyData || [])[di];
      const v = d ? d.strategyProfit : null;
      return { ci, v: (v != null && v !== 0) ? v : -Infinity };
    });
    const sorted = [...dayValues].sort((a, b) => b.v - a.v);
    sorted.forEach((item, ri) => {
      if (item.v !== -Infinity) rankMatrix[item.ci][di] = ri + 1;
    });
  });
  return { dates, rankMatrix };
}

// 排名稳定性指标（LCB 保守排名估计）：
// 悲观排名 = 平均排名 + z·std/√T（z=1 ≈ 84% 置信下限），越小越好
// 同时惩罚「均值差」和「波动大」，天数少的组合不确定性惩罚更重
function computeRankStability(combos) {
  const totalCombos = combos.length;
  const { rankMatrix } = computeRankMatrix(combos);
  const topK = Math.max(1, Math.ceil(totalCombos * 0.1));
  combos.forEach((c, ci) => {
    const ranks = rankMatrix[ci].filter(r => r != null);
    const t = ranks.length;
    if (t === 0) {
      c.rankValidDays = 0;
      c.rankMean = c.rankStd = c.rankTop10Rate = c.rankBottomRate = c.rankLcb = null;
      return;
    }
    const mean = ranks.reduce((s, r) => s + r, 0) / t;
    const std = Math.sqrt(ranks.reduce((s, r) => s + (r - mean) ** 2, 0) / t);
    c.rankValidDays = t;
    c.rankMean = Math.round(mean * 10) / 10;
    c.rankStd = Math.round(std * 10) / 10;
    c.rankTop10Rate = Math.round(ranks.filter(r => r <= topK).length / t * 1000) / 10;
    c.rankBottomRate = Math.round(ranks.filter(r => r > totalCombos - topK).length / t * 1000) / 10;
    c.rankLcb = Math.round((mean + 1.0 * std / Math.sqrt(t)) * 10) / 10;
  });
}

function renderDailyRankingChart(result, combos) {
  if (!srRankChart) {
    srRankChart = echarts.init($("#sr-chart-rank"));
  }

  const { dates, rankMatrix } = computeRankMatrix(combos);
  if (!dates.length) return;

  const labels = combos.map(c => `${shortName(c.loadModelName)}×${shortName(c.priceModelName)}`);
  const totalCombos = combos.length;

  if (_rankChartMode === 'line') {
    renderRankLineChart(dates, labels, rankMatrix, totalCombos);
  } else {
    renderRankHeatmap(dates, labels, rankMatrix, totalCombos);
  }
}

// ---------- 热力图模式 ----------
function renderRankHeatmap(dates, labels, rankMatrix, totalCombos) {
  const heatData = [];
  rankMatrix.forEach((row, ci) => {
    row.forEach((rank, di) => {
      if (rank != null) heatData.push([di, ci, rank]);
    });
  });

  srRankChart.setOption({
    tooltip: {
      formatter: p => `<b>${dates[p.data[0]]}</b><br/>${labels[p.data[1]]}<br/>当日排名: <b>#${p.data[2]}</b> / ${totalCombos}`
    },
    grid: { left: '22%', right: '4%', bottom: '14%', top: '4%', containLabel: false },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, start: 0, end: 100 },
      { type: 'slider', xAxisIndex: 0, start: 0, end: 100, bottom: '2%' },
    ],
    xAxis: { type: 'category', data: dates, splitArea: { show: false }, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'category', data: labels, splitArea: { show: false }, axisLabel: { fontSize: 10, width: 120, overflow: 'truncate' } },
    visualMap: {
      min: 1, max: totalCombos, calculable: true, orient: 'vertical', right: 0, top: 'center',
      inverse: true,
      inRange: { color: ['#16a34a', '#4ade80', '#bbf7d0', '#ffffff', '#fecaca', '#f87171', '#dc2626'] },
      formatter: v => `#${Math.round(v)}`,
    },
    series: [{
      type: 'heatmap', data: heatData,
      label: { show: totalCombos <= 40, formatter: p => `#${p.data[2]}`, fontSize: 9, color: '#334155' },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  }, true);

  srRankChart.off('click');
  srRankChart.on('click', p => {
    const ci = p.data[1];
    if (ci >= 0) showCombinationDetail(ci);
  });
}

// ---------- 折线图模式 ----------
function renderRankLineChart(dates, labels, rankMatrix, totalCombos) {
  const seriesList = [];
  const legendData = [];

  for (let ci = 0; ci < totalCombos; ci++) {
    const label = labels[ci];
    legendData.push(label);

    const rank = ci + 1; // 排行榜顺序
    let lineColor, lineWidth;
    if (rank <= 3) {
      lineColor = `rgba(22, 163, 74, ${0.85 + (3 - rank) * 0.05})`;
      lineWidth = 2.5;
    } else if (rank >= totalCombos - 2) {
      lineColor = `rgba(220, 38, 38, ${0.85 + (rank - (totalCombos - 3)) * 0.05})`;
      lineWidth = 2.5;
    } else {
      lineColor = 'rgba(148, 163, 184, 0.35)';
      lineWidth = 1;
    }

    seriesList.push({
      name: label,
      type: 'line',
      data: rankMatrix[ci].map(r => r != null ? r : null),
      symbol: 'none',
      connectNulls: true,
      lineStyle: { color: lineColor, width: lineWidth },
      itemStyle: { color: lineColor },
      z: rank <= 3 ? 10 : (rank >= totalCombos - 2 ? 8 : 1),
      emphasis: { lineStyle: { width: 3.5, opacity: 1 } },
    });
  }

  srRankChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: function(params) {
        let s = '<b>' + params[0].axisValue + '</b><br/>';
        const sorted = [...params].sort((a, b) => (a.value || 999) - (b.value || 999));
        sorted.slice(0, 12).forEach(p => {
          const v = p.value != null ? `#${p.value}` : '-';
          s += p.marker + ' ' + p.seriesName + ': ' + v + '<br/>';
        });
        if (sorted.length > 12) s += '... 共 ' + sorted.length + ' 条';
        return s;
      },
      confine: true,
    },
    legend: {
      data: legendData, type: 'scroll', top: 0,
      pageIcons: { horizontal: ['M0,0L12,-10L12,10z', 'M0,0L-12,-10L-12,10z'] },
      pageFormatter: '{current}/{total}',
      textStyle: { fontSize: 11 }, selectedMode: 'multiple',
    },
    grid: { left: '3%', right: '6%', bottom: '14%', top: '10%', containLabel: true },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, bottom: '2%' },
    ],
    xAxis: { type: 'category', data: dates, boundaryGap: false, axisLabel: { rotate: 45 } },
    yAxis: {
      type: 'value', name: '排名',
      inverse: true,       // 第1名在顶部
      min: 1,
      max: totalCombos,
      interval: Math.max(1, Math.ceil(totalCombos / 10)),
      axisLabel: { formatter: v => `#${v}` },
    },
    series: seriesList,
  }, true);

  srRankChart.off('click');
  srRankChart.on('click', function(params) {
    const idx = legendData.indexOf(params.seriesName);
    if (idx >= 0) showCombinationDetail(idx);
  });

  // 双击图例反选
  enableLegendInverseSelect(srRankChart, legendData);
}

// ==================== 组合稳定性散点图 ====================
// X=平均排名（越右越好），Y=排名波动（越上越稳），气泡=策略收益（越高越大），颜色=悲观排名（绿优红差）
// 右上角 = 稳定优秀；右下角 = 靠运气爆发（均值好但波动大）

// 打开/关闭「计算逻辑说明」tooltip 浮层（点 ? 切换，点外部区域关闭）
function toggleStabilityHelp(e) {
  if (e) e.stopPropagation();
  const el = document.getElementById('sr-stability-help');
  if (!el) return;
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
// 点击浮层以外的区域时收起
if (typeof window.__srHelpBound === 'undefined') {
  window.__srHelpBound = true;
  document.addEventListener('click', e => {
    const el = document.getElementById('sr-stability-help');
    if (el && el.style.display !== 'none' && !el.contains(e.target)) el.style.display = 'none';
  });
}

function renderStabilityChart(combos) {
  if (!srStabilityChart) {
    srStabilityChart = echarts.init($("#sr-chart-stability"));
  }
  const totalCombos = combos.length;
  const pts = [];
  combos.forEach((c, ci) => {
    if (c.rankMean == null || c.rankStd == null) return;
    pts.push({
      name: `${shortName(c.loadModelName)}×${shortName(c.priceModelName)}`,
      value: [c.rankMean, c.rankStd, c.rankLcb, c.rankTop10Rate, ci],
    });
  });
  if (!pts.length) return;

  // 中位数象限分界线
  const medOf = arr => { const s = [...arr].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
  const medMean = medOf(pts.map(p => p.value[0]));
  const medStd = medOf(pts.map(p => p.value[1]));

  // 策略收益范围（气泡大小映射基准：收益越高圆点越大）
  const profits = pts.map(p => combos[p.value[4]].totalStrategyProfit ?? 0);
  const minP = Math.min(...profits);
  const maxP = Math.max(...profits);

  // 按 LCB 实际分布计算分位阈值（tooltip 综合评价标签用，避免固定阈值全部命中同一档）
  const lcbSorted = pts.map(p => p.value[2]).sort((a, b) => a - b);
  const n = lcbSorted.length;
  const lcbQ = f => lcbSorted[Math.min(n - 1, Math.floor(n * f))];
  const lcbP10 = lcbQ(0.1), lcbP35 = lcbQ(0.35), lcbP65 = lcbQ(0.65), lcbP90 = lcbQ(0.9);

  // 象限说明文字样式：灰色文字 + 浅灰衬底，衬在数据点下层，不拦截鼠标事件
  const quadrantText = (left, right, top, bottom, text) => ({
    type: 'text', left, right, top, bottom, silent: true, z: 0,
    style: {
      text, fill: '#94a3b8', fontSize: 13, lineHeight: 19, fontWeight: 500,
      backgroundColor: 'rgba(241, 245, 249, 0.85)', padding: [4, 8], borderRadius: 4,
    },
  });

  srStabilityChart.setOption({
    tooltip: {
      // 展示完整画像：稳定性指标 + 收益表现 + 综合评价标签
      formatter: p => {
        const v = p.value;
        const c = combos[v[4]];
        // 综合评价标签（按 LCB 实际数据分位：前10%稳定优秀 → 后10%易爆雷）
        const lcb = v[2];
        const tag = lcb <= lcbP10 ? ['稳定优秀', '#16a34a']
          : lcb <= lcbP35 ? ['较稳定', '#4ade80']
          : lcb > lcbP90 ? ['易爆雷', '#dc2626']
          : lcb > lcbP65 ? ['不稳定', '#f87171']
          : ['表现中等', '#f59e0b'];
        const money = x => (x / 10000).toFixed(2) + '万';
        const profit = c ? money(c.totalStrategyProfit) : '—';
        const profitColor = c && c.totalStrategyProfit >= 0 ? '#16a34a' : '#dc2626';
        const bottomRate = c && c.rankBottomRate != null ? c.rankBottomRate + '%' : '—';
        const win = c ? `${c.winRate}%（${c.winDays}/${c.totalDays}天）` : '—';
        const cov = c && c.dataCoverage != null ? c.dataCoverage + '%' : '—';
        const row = (label, value, color) =>
          `<tr><td style="color:#94a3b8;padding:1px 14px 1px 0;white-space:nowrap">${label}</td>` +
          `<td style="padding:1px 0;color:${color || '#334155'};white-space:nowrap">${value}</td></tr>`;
        return `<b>${p.name}</b><br/>` +
          `<span style="display:inline-block;margin:3px 0 2px;padding:0 8px;border-radius:10px;font-size:11px;font-weight:600;background:${tag[1]}26;color:${tag[1]}">● ${tag[0]}</span>` +
          `<table style="font-size:12px;margin-top:3px;border-collapse:collapse">` +
          row('平均排名', '#' + v[0]) +
          row('排名波动', v[1] + '（越小越稳）') +
          row('前10%率', v[3] + '%') +
          row('爆雷率', bottomRate, c && c.rankBottomRate > 20 ? '#dc2626' : undefined) +
          row('悲观排名', `#${v[2]} / ${totalCombos}`, tag[1]) +
          row('策略收益', profit, profitColor) +
          row('胜率', win) +
          row('覆盖率', cov) +
          `</table>`;
      },
      confine: true,
    },
    grid: { left: '6%', right: '10%', bottom: '12%', top: '8%', containLabel: true },
    // 四象限灰色衬底文字，帮助快速理解方位含义
    graphic: [
      quadrantText('8%', null, '10%', null, '收益低\n波动小'),
      quadrantText(null, '12%', '10%', null, '收益高\n波动小'),
      quadrantText('8%', null, null, '15%', '收益低\n波动大'),
      quadrantText(null, '12%', null, '15%', '收益高\n波动大'),
    ],
    xAxis: {
      type: 'value', name: '平均排名', inverse: true,
      nameLocation: 'start',  // 反转后最小值端在右侧，轴名称跟随到右侧
      // 自适应数据范围，留 10% 边距
      min: v => Math.max(0, Math.floor(v.min - (v.max - v.min) * 0.1)),
      max: v => Math.ceil(v.max + (v.max - v.min) * 0.1),
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    yAxis: {
      type: 'value', name: '排名波动', inverse: true,
      nameLocation: 'start',  // 反转后最小值端在上方，轴名称跟随到上方
      min: v => Math.max(0, Math.floor(v.min - (v.max - v.min) * 0.1)),
      max: v => Math.ceil(v.max + (v.max - v.min) * 0.1),
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    visualMap: {
      min: 1, max: totalCombos, dimension: 2, calculable: true,
      orient: 'vertical', right: 0, top: 'center', inverse: true,
      // 绿→黄→红，避开纯白中段（白点在白底上会隐形）
      inRange: { color: ['#16a34a', '#4ade80', '#a3e635', '#facc15', '#fb923c', '#f87171', '#dc2626'] },
      formatter: v => `#${Math.round(v)}`,
      text: ['悲观排名差', '悲观排名优'],
    },
    series: [{
      type: 'scatter',
      data: pts,
      // 圆点大小由策略收益金额决定：收益最高者最大，最低者最小
      symbolSize: v => 6 + ((combos[v[4]].totalStrategyProfit - minP) / (maxP - minP || 1)) * 22,
      itemStyle: { opacity: 0.85, borderColor: '#fff', borderWidth: 1 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
      markLine: {
        silent: true, symbol: 'none',
        lineStyle: { type: 'dashed', color: '#94a3b8' },
        label: { show: false },
        data: [{ xAxis: medMean }, { yAxis: medStd }],
      },
    }],
  }, true);

  srStabilityChart.off('click');
  srStabilityChart.on('click', p => {
    const ci = p.value && p.value[4];
    if (ci != null && ci >= 0) showCombinationDetail(ci);
  });
}

// ==================== 排行表格 ====================

function renderActualRow(profit) {
  const cls = profit >= 0 ? 'positive' : 'negative';
  return `<tr class="sr-actual-row">
    <td>—</td>
    <td style="font-weight:600;color:#5470c6">实际运行</td>
    <td>—</td>
    <td class="${cls}">${(profit / 10000).toFixed(2)}万</td>
    <td class="${cls}">${(profit / 10000).toFixed(2)}万</td>
    <td>0.00万</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
    <td>—</td>
  </tr>`;
}

function renderRankingTable(combos, invalidCombos) {
  const tbody = $("#sr-daily-table tbody");
  tbody.innerHTML = '';
  const total = combos.length;
  const rows = [];

  // 构建实际运行基准行数据（使用全区间实际收益，不受策略有效天数过滤影响）
  const actualProfit = _allData?.fullActualProfit ?? (total > 0 ? (combos[0]?.totalActualProfit ?? 0) : 0);
  const actualRow = {
    _isActual: true,
    loadModelName: '实际运行',
    priceModelName: '—',
    totalStrategyProfit: actualProfit,
    totalActualProfit: actualProfit,
    excessProfit: 0,
    avgDailyExcess: 0,
    winRate: null,
    winDays: null,
    totalDays: null,
    dataCoverage: null,
  };

  // 找到基准行在当前排序下的插入位置
  const field = _currentSort;
  const asc = _sortAsc;
  let insertIdx = total;
  const actualVal = actualRow[field] != null ? actualRow[field] : (asc ? Infinity : -Infinity);
  for (let i = 0; i < total; i++) {
    const comboVal = combos[i][field] != null ? combos[i][field] : (asc ? Infinity : -Infinity);
    const shouldInsertBefore = asc
      ? (actualVal < comboVal)
      : (actualVal > comboVal);
    if (shouldInsertBefore) {
      insertIdx = i;
      break;
    }
  }

  // showRows 需包含基准行所占槽位
  const comboShowLimit = _tableExpanded ? total : Math.min(total, TABLE_COLLAPSE_ROWS);
  const actualVisible = insertIdx <= comboShowLimit; // 基准行在可见范围内
  const showRows = comboShowLimit + (actualVisible ? 1 : 0);

  for (let idx = 0; idx < showRows; idx++) {
    // 在插入位置渲染基准行
    if (idx === insertIdx) {
      rows.push(renderActualRow(actualProfit));
      continue;
    }

    // 渲染普通策略行（idx 在基准行之后的要偏移 -1）
    const comboIdx = idx < insertIdx ? idx : idx - 1;
    if (comboIdx < 0 || comboIdx >= total) continue;
    const c = combos[comboIdx];
    const rank = comboIdx + 1;
    const medal = rank <= 3 ? ['🥇','🥈','🥉'][rank - 1] : rank;
    const rowClass = rank <= 3 ? 'rank-top' : (rank >= total - 2 ? 'rank-bottom' : '');
    const avgExcess = c.avgDailyExcess ?? 0;
    const coverage = c.dataCoverage ?? 0;
    const covColor = coverage >= 90 ? '#16a34a' : coverage >= 70 ? '#d97706' : '#dc2626';
    const lcbColor = c.rankLcb == null ? '#94a3b8'
      : c.rankLcb <= total * 0.1 ? '#16a34a'
      : c.rankLcb > total * 0.9 ? '#dc2626' : '#334155';

    rows.push(`<tr class="sr-combo-row ${rowClass}" data-idx="${comboIdx}" onclick="showCombinationDetail(${comboIdx})" style="cursor:pointer">
      <td>${medal}</td>
      <td>${c.loadModelName}</td>
      <td>${c.priceModelName}</td>
      <td class="${c.totalStrategyProfit >= 0 ? 'positive' : 'negative'}">${(c.totalStrategyProfit / 10000).toFixed(2)}万</td>
      <td>${(c.totalActualProfit / 10000).toFixed(2)}万</td>
      <td class="${c.excessProfit >= 0 ? 'positive' : 'negative'}">${(c.excessProfit / 10000).toFixed(2)}万</td>
      <td class="${avgExcess >= 0 ? 'positive' : 'negative'}">${(avgExcess / 10000).toFixed(2)}万</td>
      <td>${c.winRate}%</td>
      <td>${c.winDays}/${c.totalDays}</td>
      <td>${c.totalDays}</td>
      <td style="white-space:nowrap">
        <span class="sr-coverage-bar"><span class="sr-coverage-fill" style="width:${coverage}%"></span></span>
        <span style="font-size:11px;color:${covColor}">${coverage.toFixed(0)}%</span>
      </td>
      <td>${c.rankMean != null ? '#' + c.rankMean : '—'}</td>
      <td>${c.rankStd != null ? c.rankStd : '—'}</td>
      <td>${c.rankTop10Rate != null ? c.rankTop10Rate + '%' : '—'}</td>
      <td class="${c.rankBottomRate > 20 ? 'negative' : ''}">${c.rankBottomRate != null ? c.rankBottomRate + '%' : '—'}</td>
      <td style="font-weight:600;color:${lcbColor}">${c.rankLcb != null ? '#' + c.rankLcb : '—'}</td>
    </tr>`);
  }
  tbody.innerHTML = rows.join('');

  // 展开/折叠按钮
  const expandWrap = document.getElementById('sr-table-expand-wrap');
  const expandBtn = document.getElementById('sr-table-expand-btn');
  if (total > TABLE_COLLAPSE_ROWS) {
    expandWrap.style.display = 'block';
    const hiddenCount = total - TABLE_COLLAPSE_ROWS;
    expandBtn.textContent = _tableExpanded
      ? `收起（显示前 ${TABLE_COLLAPSE_ROWS} 名）`
      : `展开全部（还有 ${hiddenCount} 个组合）`;
  } else {
    expandWrap.style.display = 'none';
  }

  // 无有效数据组合折叠区
  const invalidSection = document.getElementById('sr-invalid-combos');
  if (!invalidCombos || invalidCombos.length === 0) {
    if (invalidSection) invalidSection.style.display = 'none';
    return;
  }
  if (!invalidSection) return;
  invalidSection.style.display = 'block';
  const list = invalidCombos.map(c =>
    `<span style="display:inline-block;background:#f1f5f9;border-radius:4px;padding:2px 8px;margin:2px;font-size:12px;color:#64748b">
      ${c.loadModelName} × ${c.priceModelName}
      <span style="color:#94a3b8">(${c.noDataDays}天全无效)</span>
    </span>`
  ).join('');
  document.getElementById('sr-invalid-list').innerHTML = list;
  document.getElementById('sr-invalid-count').textContent = invalidCombos.length;
}

function toggleInvalidCombos() {
  const el = document.getElementById('sr-invalid-list');
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

// ==================== 点击行显示每日详情 ====================

function showCombinationDetail(idx) {
  if (!_validCombos) return;
  const c = _validCombos[idx];
  if (!c || !c.dailyData || c.dailyData.length === 0) return;

  // 高亮当前行（通过 data-idx 精确匹配，避免基准行干扰 DOM 下标）
  $$('.sr-combo-row').forEach(r => r.classList.remove('rank-active'));
  const targetRow = document.querySelector(`.sr-combo-row[data-idx="${idx}"]`);
  if (targetRow) targetRow.classList.add('rank-active');

  if (!srDetailChart) {
    srDetailChart = echarts.init($("#sr-chart-detail"));
  }
  // 隐藏 placeholder
  const ph = document.getElementById("sr-detail-placeholder");
  if (ph) ph.style.display = 'none';

  const dates = c.dailyData.map(d => d.date);
  const actual = c.dailyData.map(d => d.actualProfitNotDeviationRecovery);
  // strategyProfit 为 null 或 0 时均视为无效，保持 null 使图表断裂
  const strategy = c.dailyData.map(d => (d.strategyProfit != null && d.strategyProfit !== 0) ? d.strategyProfit : null);
  const diff = c.dailyData.map(d => {
    const a = d.actualProfitNotDeviationRecovery, s = d.strategyProfit;
    return (a != null && s != null && s !== 0) ? +(s - a).toFixed(2) : null;
  });

  // 累计曲线：无效天(null/0)不累加，用 null 表示断裂
  let cumA = 0, cumS = 0;
  const cumActual = [], cumStrategy = [];
  c.dailyData.forEach(d => {
    const hasActual = d.actualProfitNotDeviationRecovery != null;
    const hasStrategy = d.strategyProfit != null && d.strategyProfit !== 0;
    if (hasActual) cumA += d.actualProfitNotDeviationRecovery;
    if (hasStrategy) cumS += d.strategyProfit;
    cumActual.push(hasActual ? +cumA.toFixed(2) : null);
    cumStrategy.push(hasStrategy ? +cumS.toFixed(2) : null);
  });

  // 统计无效天数（strategyProfit 为 null/0，或实际收益为 null）
  const noDataCount = c.dailyData.filter(d =>
    d.strategyProfit == null || d.strategyProfit === 0 || d.actualProfitNotDeviationRecovery == null
  ).length;

  srDetailChart.setOption({
    title: {
      text: `${c.loadModelName} × ${c.priceModelName} 每日详情` +
        (noDataCount ? `  (${noDataCount}天无效)` : '') +
        `  |  超额:${(c.excessProfit/10000).toFixed(2)}万`,
      left: 'center', textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: function(params) {
        let s = params[0].axisValue + '<br/>';
        params.filter(p => !p.seriesName.endsWith('_bridge')).forEach(p => {
          const val = p.value != null ? (p.value / 10000).toFixed(2) + '万' : '-';
          s += p.marker + ' ' + p.seriesName + ': ' + val + '<br/>';
        });
        return s;
      }
    },
    legend: { data: ['实际收益', '策略收益', '累计实际', '累计策略'], top: 30 },
    grid: [
      { left: '3%', right: '4%', top: '20%', height: '30%', containLabel: true },
      { left: '3%', right: '4%', top: '58%', height: '30%', bottom: '10%', containLabel: true },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 0, end: 100, bottom: '1%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { rotate: 45, fontSize: 10 } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { rotate: 45, fontSize: 10 } },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, name: '每日收益', axisLabel: { formatter: v => (v / 10000).toFixed(1) + '万' } },
      { type: 'value', gridIndex: 1, name: '累计收益', axisLabel: { formatter: v => (v / 10000).toFixed(1) + '万' } },
    ],
    series: [
      {
        name: '实际收益', type: 'bar', xAxisIndex: 0, yAxisIndex: 0,
        data: actual, barMaxWidth: 14, itemStyle: { color: '#5470c6' },
        connectNulls: false,
      },
      {
        name: '策略收益', type: 'bar', xAxisIndex: 0, yAxisIndex: 0,
        data: strategy, barMaxWidth: 14, itemStyle: { color: '#91cc75' },
        connectNulls: false,
      },
      // 累计实际：桥接系列（灰虚线） + 主线（connectNulls=false 断裂）
      {
        name: '累计实际_bridge', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
        data: cumActual, symbol: 'none',
        lineStyle: { color: '#cbd5e1', width: 1, type: 'dashed' },
        itemStyle: { color: '#cbd5e1' },
        connectNulls: true, silent: true, tooltip: { show: false },
      },
      {
        name: '累计实际', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
        data: cumActual, lineStyle: { color: '#5470c6', width: 2 },
        itemStyle: { color: '#5470c6' }, areaStyle: { color: 'rgba(84,112,198,0.1)' },
        connectNulls: false,
      },
      // 累计策略：桥接系列（灰虚线） + 主线（connectNulls=false 断裂）
      {
        name: '累计策略_bridge', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
        data: cumStrategy, symbol: 'none',
        lineStyle: { color: '#cbd5e1', width: 1, type: 'dashed' },
        itemStyle: { color: '#cbd5e1' },
        connectNulls: true, silent: true, tooltip: { show: false },
      },
      {
        name: '累计策略', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
        data: cumStrategy, lineStyle: { color: '#91cc75', width: 2 },
        itemStyle: { color: '#91cc75' }, areaStyle: { color: 'rgba(145,204,117,0.1)' },
        connectNulls: false,
      },
    ],
  }, true);

  // 双击图例反选
  enableLegendInverseSelect(srDetailChart, ['实际收益', '策略收益', '累计实际', '累计策略']);

  // 滚动到详情区域
  document.getElementById("sr-detail-section").scrollIntoView({ behavior: 'smooth', block: 'start' });
}
