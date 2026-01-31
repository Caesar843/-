# UI 重设计说明（运营仪表盘）

## 目标风格对标
- 参考页面：仪表盘（截图）
- 目标方向：明亮、卡片化、轻阴影、圆角、分隔清晰、留白充足

## Design Tokens
| Token | 值 | 用途 |
| --- | --- | --- |
| --ops-primary | #2563eb | 主色、主按钮、强调 |
| --ops-success | #10b981 | 成功/增长指标 |
| --ops-warning | #f59e0b | 警示/提醒指标 |
| --ops-info | #06b6d4 | 信息/辅助指标 |
| --ops-text | #111827 | 主文本 |
| --ops-muted | #6b7280 | 次级文本 |
| --ops-border | #e5e7eb | 边框/分割线 |
| --ops-bg | #f3f4f6 | 背景 |
| --ops-surface | #ffffff | 卡片底色 |
| --ops-shadow | 0 8px 24px rgba(15, 23, 42, 0.08) | 阴影 |
| --ops-radius-lg | 16px | 卡片圆角 |
| --ops-radius-md | 12px | 表单/小卡片 |
| --ops-radius-sm | 10px | 图标底座 |

## 组件样式层
文件：`static/css/ui-components.css`
- Button: `.ui-btn`, `.ui-btn-primary`, `.ui-btn-outline`
- Input/Select: `.ui-input`
- Card/Section: `.ui-card`, `.ui-section`
- Table: `.ui-table`
- Badge: `.ui-badge`
- Alert/Toast/Modal: `.ui-alert`, `.ui-toast`, `.ui-modal`
- Pagination: `.ui-pagination`
- EmptyState: `.ui-empty`
- Skeleton: `.ui-skeleton`

## 改造范围
- 改造页面：
  - 运营数据仪表盘：`templates/operations/dashboard.html`
  - 运营数据分析：`templates/operations/analysis.html`
  - 多维查询导航：`apps/query/templates/query/dashboard.html`
  - 店铺管理列表：`templates/store/shop_list.html`
  - 合同管理列表：`templates/store/contract_list.html`
  - 财务记录列表：`templates/finance/finance_list.html`
  - 财务历史：`apps/finance/templates/finance/finance_history.html`
  - 创建财务记录：`templates/finance/finance_form.html`
  - 催款提醒：`templates/finance/finance_reminders.html`
  - 活动管理：`apps/communication/templates/communication/activity_list.html`
  - 维修管理：`apps/communication/templates/communication/maintenance_list.html`
  - 活动管理（运营专员）：`apps/communication/templates/communication/admin_activity_list.html`
  - 维修管理（运营专员）：`apps/communication/templates/communication/admin_maintenance_list.html`
  - 报表中心：`templates/reports/report_list.html`
  - 创建备份：`apps/backup/templates/backup/backup_create.html`
  - 店铺查询：`apps/query/templates/query/shop_query.html`
  - 运营查询：`apps/query/templates/query/operation_query.html`
  - 财务查询：`apps/query/templates/query/finance_query.html`
  - 管理层查询：`apps/query/templates/query/admin_query.html`
- 新增样式：
  - `static/css/ui-tokens.css`
  - `static/css/ui-components.css`
  - `static/css/operations-dashboard.css`
  - `static/css/operations-analysis.css`
  - `static/css/query-dashboard.css`
  - `static/css/store-management.css`
  - `static/css/finance-management.css`
  - `static/css/communication-management.css`
  - `static/css/reports-center.css`
  - `static/css/backup-management.css`
  - `static/css/query-detail.css`

## 回滚方式
1. 移除 `templates/operations/dashboard.html` 中对 `ui-tokens.css` / `ui-components.css` / `operations-dashboard.css` 的引用。
2. 移除 `templates/operations/analysis.html` 与 `apps/query/templates/query/dashboard.html` 中对新增 CSS 的引用。
3. 移除 `templates/store/shop_list.html`、`templates/store/contract_list.html`、`templates/finance/finance_list.html`、`apps/finance/templates/finance/finance_history.html` 中对新增 CSS 的引用。
4. 移除活动/维修/报表相关页面对新增 CSS 的引用。
5. 删除新增的 CSS 文件（或保留但不被任何页面引用）。

## 自测清单（功能不变）
- 登录/退出、权限校验正常
- 运营仪表盘：筛选、重置仍可用（URL/参数不变）
- 运营分析：筛选与数据表渲染正常
- 多维查询：四个入口链接跳转正常
- 店铺管理：列表、编辑/删除按钮可用
- 合同管理：状态徽章与操作按钮逻辑正确
- 财务管理：新增/提醒/历史入口与支付弹窗正常
- 财务历史：筛选、分页与详情跳转正常
- 创建财务记录：表单提交与字段校验正常
- 催款提醒：天数筛选与列表跳转正常
- 活动管理：提交/审核/查看入口正常
- 维修管理：提交/处理/查看入口正常
- 报表中心：生成、预览与导出正常
- 创建备份：表单提交与按钮跳转正常
- 多维查询：
  - 店铺查询：店铺筛选、详情/合约/财务/运营列表渲染正常
  - 运营查询：筛选条件与统计渲染正常
  - 财务查询：筛选条件、费用明细与统计渲染正常
  - 管理层查询：概览卡与表格渲染正常
- 指标卡数值、图表数据与表格渲染正常
- 无数据时提示正常
- 1366px 与 1920px 宽度显示正常
