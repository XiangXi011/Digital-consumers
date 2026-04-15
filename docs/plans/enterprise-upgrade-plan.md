# 市场部 Agent Teams — 企业级平台升级计划

## 文档信息

| 字段 | 值 |
|------|----|
| 版本 | v1.0 |
| 日期 | 2026-04-13 |
| 状态 | Draft |
| 总工作量 | 56 项（Phase 1: 22 + Phase 2: 18 + Phase 3: 16） |

---

## 1. 现状评估

### 1.1 项目定位

市场部 Agent Teams 是一个基于 LLM 的市场研究 AI Agent 平台，通过 8 个差异化消费者画像（M01-M08）模拟真实消费者反馈，支撑产品概念评审、包装评审、文案评审和 A/B 对比测试。

### 1.2 当前技术栈

| 层级 | 技术 | 状态 |
|------|------|------|
| 前端 | React 19 + Vite 8 + Tailwind 4 | 原型级 |
| 后端 | FastAPI + Python 3.12 | 功能完整 |
| AI 编排 | LangGraph 状态机 | 功能完整 |
| 即时通讯 | 钉钉 Stream Bot | 功能完整 |
| 持久化 | JSON 文件 + threading.Lock | 不可扩展 |
| 缓存 | InMemoryStore（Redis 已部署但未连接） | 缺失 |
| 认证 | 无 | 缺失 |
| CI/CD | 无 | 缺失 |
| 可观测性 | 基础 logging | 缺失 |

### 1.3 核心缺陷

1. **零认证** — 前端所有路由裸露，Settings 页面公开暴露 LLM API Key 和钉钉密钥
2. **JSON 文件持久化** — `threading.Lock` 仅对单进程有效，无法水平扩展
3. **后台任务丢失风险** — FastAPI `BackgroundTasks` fire-and-forget，进程重启即丢
4. **Redis 空转** — docker-compose 已部署 Redis，但代码中零连接
5. **评分维度僵化** — 4 类评审共用固定 4 维度，无法体现类型差异化
6. **200 样本池闲置** — 每次只用 8 个固定画像，25 样本/segment 从未随机化
7. **群组讨论/深度访谈已实现但默认关闭** — 浪费第二/三层研究能力
8. **前端无 ErrorBoundary、无状态管理、无测试** — 任何 JS 错误白屏崩溃

---

## 2. Phase 1: P0 — 安全与基础设施

**目标**：系统能安全地给内部团队试用
**工期**：4-6 周
**工作量**：22 项

### 2.1 PostgreSQL 数据库层

#### 技术选型

- **PostgreSQL 16** — ACID 事务、并发控制、索引查询
- **SQLAlchemy 2.0 async** — 连接池、async/await 支持、ORM 映射
- **Alembic** — 数据库迁移版本管理

#### 理由

当前 `TaskSessionManager`（`backend/workflow/task_session_manager.py`，1038 行）使用 JSON 文件 + `threading.Lock` 持久化。`_scan_sessions()`（`backend/api/routers/projects.py`，line 115）每次请求遍历文件系统目录。无法水平扩展，无 ACID 保证。

#### 数据库表设计

**users 表** — 替代无认证现状

```sql
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    display_name  VARCHAR(100) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- admin, editor, viewer
    password_hash VARCHAR(255) NOT NULL,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

**projects 表** — 替代 JSON session 文件

```sql
CREATE TABLE projects (
    id              UUID PRIMARY KEY,
    owner_id        UUID NOT NULL REFERENCES users(id),
    session_id      VARCHAR(64) UNIQUE NOT NULL,
    group_id        VARCHAR(128) NOT NULL DEFAULT '',
    conversation_id VARCHAR(128) NOT NULL DEFAULT '',
    name            VARCHAR(200) NOT NULL DEFAULT '',
    status          VARCHAR(40) NOT NULL DEFAULT 'collecting',
    project_type    VARCHAR(40) NOT NULL DEFAULT 'concept',
    fields          JSONB NOT NULL DEFAULT '{}',
    missing_fields  JSONB NOT NULL DEFAULT '[]',
    attachments     JSONB NOT NULL DEFAULT '[]',
    source_links    JSONB NOT NULL DEFAULT '[]',
    custom_questions JSONB NOT NULL DEFAULT '[]',
    product_context_notes JSONB NOT NULL DEFAULT '[]',
    follow_up_context TEXT NOT NULL DEFAULT '',
    checklist_sent  BOOLEAN DEFAULT FALSE,
    partial_run_authorized BOOLEAN DEFAULT FALSE,
    last_task_id    VARCHAR(128),
    research_plan   JSONB,
    business_brief  JSONB,
    readiness_decision JSONB,
    html_report_path VARCHAR(512),
    json_report_path VARCHAR(512),
    metrics_path    VARCHAR(512),
    authorization_requested_at BIGINT,
    authorization_requested_by VARCHAR(128),
    retention_policy JSONB DEFAULT '{}',
    suspended_messages JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_session_id ON projects(session_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
```

**reports 表** — 替代文件扫描

```sql
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    owner_id        UUID NOT NULL REFERENCES users(id),
    report_type     VARCHAR(40) NOT NULL DEFAULT 'unknown',
    name            VARCHAR(300) NOT NULL DEFAULT '',
    json_path       VARCHAR(512) NOT NULL,
    html_path       VARCHAR(512),
    meta            JSONB DEFAULT '{}',
    evaluation_metrics JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_reports_owner ON reports(owner_id);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_project ON reports(project_id);
```

**share_tokens 表** — 替代 `report_shares.json`

```sql
CREATE TABLE share_tokens (
    token       VARCHAR(64) PRIMARY KEY,
    report_id   UUID NOT NULL REFERENCES reports(id),
    created_by  UUID REFERENCES users(id),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_share_tokens_report ON share_tokens(report_id);
```

**audit_log 表** — 安全审计追踪

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    action      VARCHAR(60) NOT NULL,
    resource    VARCHAR(100) NOT NULL,
    resource_id VARCHAR(128),
    detail      JSONB,
    ip_address  INET,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
```

**system_settings 表** — 替代 `.env` 文件解析

```sql
CREATE TABLE system_settings (
    key         VARCHAR(100) PRIMARY KEY,
    value       TEXT NOT NULL,
    is_secret   BOOLEAN DEFAULT FALSE,
    updated_by  UUID REFERENCES users(id),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**frozen_snapshots 表** — 替代文件快照

```sql
CREATE TABLE frozen_snapshots (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES projects(id),
    stage       VARCHAR(40) NOT NULL,
    payload     JSONB NOT NULL,
    version_bundle JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_snapshots_project ON frozen_snapshots(project_id);
```

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/db/__init__.py` | 数据库包初始化 |
| `backend/db/session.py` | SQLAlchemy async engine + session factory |
| `backend/db/models.py` | ORM 模型映射（7 张表） |
| `backend/db/repositories.py` | `ProjectRepo`, `ReportRepo`, `UserRepo`, `SettingsRepo` |
| `backend/db/migrate_from_json.py` | 一次性 JSON→DB 迁移脚本（幂等） |
| `backend/db/migrations/env.py` | Alembic 环境配置 |
| `backend/db/migrations/versions/001_initial_schema.py` | 初始 schema 迁移 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/routers/projects.py` | `_scan_sessions()` / `_load_session_data()` → `ProjectRepo` 调用 |
| `backend/api/routers/reports.py` | `_scan_reports()` / share token 逻辑 → `ReportRepo` |
| `backend/api/routers/dashboard.py` | 文件遍历 → SQL 聚合查询 |
| `backend/api/routers/settings.py` | `.env` 解析 → `system_settings` 表 |
| `backend/workflow/task_session_manager.py` | `save()` / `load()` → DB 写读，移除 `_file_locks` |
| `backend/paths.py` | 移除 `DINGTALK_SESSIONS_DIR`, `DEBUG_SESSIONS_DIR`, `REPORT_SHARES_PATH` |
| `requirements.txt` | 添加 `sqlalchemy[asyncio]>=2.0.0`, `asyncpg>=0.29.0`, `alembic>=1.13.0` |
| `docker-compose.yml` | 添加 `postgres:16-alpine` 服务 + `DATABASE_URL` 环境变量 |

#### 迁移策略

1. Alembic 创建完整 schema
2. `migrate_from_json.py` 扫描现有 JSON 文件写入数据库
3. 使用 `INSERT ... ON CONFLICT DO NOTHING` 保证幂等性
4. 旧 JSON 文件保留 1 周作为备份，验证后归档

---

### 2.2 认证与 RBAC

#### 技术选型

- **python-jose[cryptography]** — JWT 签发与验证
- **passlib[bcrypt]** — 密码哈希

选择 JWT 而非 Session 的理由：无状态、适合纯 FastAPI 架构、可随时升级为 OAuth2/OIDC。

#### Token 设计

- **Access Token**：30 分钟有效期，包含 `user_id`, `role`, `org_id`
- **Refresh Token**：7 天有效期，仅用于刷新 access token

#### 新增 API

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| POST | `/api/auth/register` | 无（首用户为 admin） | 注册 |
| POST | `/api/auth/login` | 无 | 返回 access_token + refresh_token |
| POST | `/api/auth/refresh` | Refresh token | 刷新 access_token |
| GET | `/api/auth/me` | Bearer | 当前用户信息 |
| GET | `/api/auth/users` | Admin | 用户列表 |

#### 角色权限矩阵

| 资源 | Admin | Editor | Viewer |
|------|-------|--------|--------|
| 创建/运行项目 | 全部 | 全部 | 只读 |
| 查看项目 | 全部 | 自己的 | 自己的 |
| 系统设置 | 读写 | 只读 | 只读 |
| 画像管理 | CRUD | CRUD | 只读 |
| 报告分享 | ✓ | ✓ | ✓ |

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/auth/__init__.py` | 认证包初始化 |
| `backend/auth/security.py` | `hash_password()`, `verify_password()`, `create_access_token()`, `create_refresh_token()`, `decode_token()` |
| `backend/auth/dependencies.py` | `get_current_user()`, `require_role()`, FastAPI Depends |
| `backend/auth/routes.py` | 5 个认证端点 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/server.py` | 挂载 auth 路由，CORS 收紧为环境变量配置 |
| `backend/api/routers/projects.py` | 所有端点加 `Depends(get_current_user)`，设置 `owner_id` |
| `backend/api/routers/reports.py` | 按 `owner_id` 过滤 |
| `backend/api/routers/dashboard.py` | 统计范围按用户过滤 |
| `backend/api/routers/settings.py` | `update_settings` 需 admin 角色 |
| `backend/api/routers/upload.py` | 需认证，关联用户 |
| `backend/api/routers/personas.py` | 读取保持公开，CRUD 需 Editor+ |
| `requirements.txt` | 添加 `python-jose[cryptography]>=3.3.0`, `passlib[bcrypt]>=1.7.4` |

---

### 2.3 前端基础设施

#### 新建文件

| 文件 | 职责 |
|------|------|
| `frontend/src/contexts/AuthContext.jsx` | 登录/登出/token 管理 |
| `frontend/src/components/ProtectedRoute.jsx` | 路由守卫 |
| `frontend/src/components/LoginPage.jsx` | 登录页 |
| `frontend/src/components/ErrorBoundary.jsx` | 错误边界 |
| `frontend/src/components/LoadingState.jsx` | 通用加载骨架屏 |
| `frontend/src/hooks/useApi.js` | 带 loading/error/retry 的 API 封装 |
| `frontend/src/hooks/usePolling.js` | 指数退避轮询 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `frontend/src/lib/api.js` | Authorization header、AbortController 超时（30s）、5xx 重试 3 次（1s/2s/4s）、401 → token 刷新 |
| `frontend/src/App.jsx` | AuthProvider 包裹 + ProtectedRoute 守卫 + ErrorBoundary + `/login` 路由 |
| `frontend/src/pages/Dashboard.jsx` | ErrorBoundary 包裹 + useApi hook |
| `frontend/src/pages/NewProject.jsx` | ErrorBoundary + usePolling |
| `frontend/src/pages/Report.jsx` | ErrorBoundary |

---

### 2.4 Phase 1 测试

#### 新建文件

| 文件 | 职责 |
|------|------|
| `tests/conftest.py` | fixtures: `db_session`, `test_client`, `auth_headers` |
| `tests/test_auth.py` | 登录/注册/刷新/权限测试（15+ cases） |
| `tests/test_projects_db.py` | CRUD + 所有权过滤（10+ cases） |
| `tests/test_reports_db.py` | 报告查询 + share token 创建/撤销（8+ cases） |
| `tests/test_migration.py` | JSON→DB 迁移幂等性（5+ cases） |
| `pyproject.toml` | pytest 配置、ruff 配置、mypy 配置 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `tests/test_projects_api.py` | 重构为 httpx.AsyncClient + auth headers |

---

## 3. Phase 2: P1 — 规模化能力

**目标**：支持多团队多品类并发使用
**工期**：6-8 周
**工作量**：18 项

### 3.1 Celery 任务队列

#### 技术选型

- **Celery 5.x** — 任务重试、状态追踪、速率限制、水平 worker 扩展
- **Redis broker** — docker-compose 已部署，直接复用

#### 理由

当前 `background_tasks.add_task(_execute_project_run, session_id)`（`backend/api/routers/projects.py`，line 456）是 fire-and-forget：无重试、无取消、无可见性、进程重启即丢。

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/tasks/__init__.py` | 任务包初始化 |
| `backend/tasks/celery_app.py` | Celery app 配置，Redis broker URL |
| `backend/tasks/project_tasks.py` | `@celery_app.task(bind=True, max_retries=3)` 包装 `_execute_project_run` |
| `backend/tasks/report_tasks.py` | 报告生成 Celery 任务 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/routers/projects.py` | `background_tasks.add_task` → `execute_project_run.delay()`，新增 `GET /api/projects/{id}/task-status` |
| `docker-compose.yml` | 添加 `celery-worker`（concurrency=4）和 `celery-beat` 服务 |
| `requirements.txt` | 添加 `celery[redis]>=5.3.0`, `redis>=5.0.0` |

#### 新增 API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/projects/{id}/task-status` | Celery 任务状态：PENDING/STARTED/SUCCESS/FAILURE |

---

### 3.2 Redis 适配器

#### 理由

`backend/infra/redis_infra.py` 已定义 `KeyValueStore` Protocol + 4 个原语（EventDeduplicator、AggregationWindow、SuspendQueue、OrderingGuard），但只有 `InMemoryStore`。docker-compose 配置的 Redis 从未连接。

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/infra/redis_infra.py` | 添加 `RedisStore(KeyValueStore)` + `create_store(url)` 工厂函数 |
| `backend/api/server.py` | 启动时 `app.state.store = create_store(os.getenv("REDIS_URL", ""))` |
| `backend/workflow/task_session_manager.py` | 构造函数接受 `store: KeyValueStore`，用于去重/排序/暂停队列 |

---

### 3.3 评分体系动态化

#### 理由

当前 4 类评审共用固定 4 维度（efficacy/trust/convenience/price），`evidence_models.py` 的 `PersonaEvaluation` 有 4 个硬编码字段，`persona_scoring.py` 的 `compute_purchase_intent()` 只接受这 4 个 key。Planner 输出的 `evaluation_dimensions` 从未参与评分。

#### 按评审类型的维度设计

| 评审类型 | 维度 1 | 维度 2 | 维度 3 | 维度 4 |
|---------|--------|--------|--------|--------|
| concept_test | 需求匹配度 | 差异化认知 | 购买驱动力 | 价格接受度 |
| packaging_review | 货架辨识度 | 信息清晰度 | 视觉信任感 | 拿起意愿 |
| copy_feedback | 记忆点强度 | 可信度 | 转化说服力 | 情感共鸣 |
| ab_test | 方案 A 维度对齐 | 方案 B 维度对齐 | 综合偏好 | 切换成本 |

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/domain/scoring_registry.py` | task_type → 维度集 + 默认权重 + 阈值映射 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/domain/evidence_models.py` | `PersonaEvaluation` 改 `rubric_scores: Dict[str, int]`，`compute_intent()` 动态迭代 |
| `backend/domain/persona_scoring.py` | `compute_purchase_intent()` 接收动态维度，移除硬编码 key 名 |
| `backend/research/qualitative_research.py` | `RUBRIC_DIMENSIONS` 改为按 task_type 配置 |

---

### 3.4 Persona CRUD + 样本随机化

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/routers/personas.py` | 添加 POST/PUT/DELETE + samples 端点 |
| `backend/research/qualitative_research.py` | 替换硬编码 `DEFAULT_MULTI_PERSONA_IDS`（line 57）为 DB 查询，25 样本池随机抽样 |
| `backend/db/models.py` | 添加 `personas` 表 |

#### 新增 API

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| POST | `/api/personas` | Editor+ | 创建自定义画像 |
| PUT | `/api/personas/{id}` | Editor+ | 更新画像 |
| DELETE | `/api/personas/{id}` | Admin | 删除自定义画像 |
| GET | `/api/personas/{id}/samples` | Viewer | 获取代表样本 |

#### 样本随机化策略

- 每次评审从 `persona_samples_complete.json` 的 25 样本/segment 中随机抽取 N 个
- 单 segment 模式：每 segment 抽 3 个（共 24 个评审），比固定 8 个结论更稳定
- 多 segment 模式：每 segment 抽 1 个，保持 8 个画像覆盖广度

---

### 3.5 CI/CD Pipeline

#### 新建文件

| 文件 | 职责 |
|------|------|
| `.github/workflows/ci.yml` | lint → test → build → docker push |
| `.github/workflows/cd.yml` | deploy to staging/production |
| `backend/pyproject.toml` | ruff + mypy + pytest 配置 |
| `frontend/vitest.config.js` | Vitest 配置 |
| `frontend/src/__tests__/api.test.js` | 前端 API 层测试 |

#### CI 流水线设计

```
push/PR
  ├── backend-lint: ruff check + mypy
  ├── backend-test: pytest --cov (services: postgres + redis)
  ├── frontend-lint: npm run lint
  ├── frontend-test: vitest run
  └── docker-build: backend + frontend images
```

#### 添加依赖

```
ruff>=0.4.0, mypy>=1.10.0, pytest>=8.0.0, pytest-asyncio>=0.23.0,
pytest-cov>=5.0.0, httpx>=0.27.0
```

---

### 3.6 结构化日志

#### 技术选型：structlog

当前日志配置（`backend/api/server.py`，line 17）为 `logging.basicConfig` 平面文本格式，不可机器解析。

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/infra/logging_config.py` | structlog JSON renderer + context processors |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/server.py` | `logging.basicConfig` → `configure_structlog()` + `RequestIdMiddleware` |
| 所有 router 文件 | `logging.getLogger` → `structlog.get_logger` |

---

## 4. Phase 3: P2 — 竞争力提升

**目标**：产品差异化竞争力
**工期**：6-8 周
**工作量**：16 项

### 4.1 研究方法论增强

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/research/group_discussion.py` | `GroupDiscussionAgent`：结构化辩论 prompt，共识/分歧提取 |
| `backend/research/deep_dive.py` | `DeepDiveAgent`：高分歧维度再评估 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/research/qualitative_research.py` | 启用 group discussion + deep dive（当前默认关闭，line 126-127） |
| `backend/workflow/langgraph_flows.py` | 增强管线图：planning → fan_out → group_discussion(条件) → deep_dive(条件) → synthesis |
| `backend/workflow/langgraph_state.py` | 添加 `group_discussion_outputs`, `deep_dive_results` 字段 |
| `backend/api/routers/projects.py` | `CreateProjectRequest` 添加 `enable_group_discussion` / `enable_deep_dive` |

#### 研究管线增强

```
当前：planning → persona×8 → synthesis
增强：planning → persona×8 → [可选] group_discussion(3-4人辩论) → [可选] deep_dive(高分歧再评估) → synthesis
```

触发条件：
- `inter_persona_divergence_score > 0.5` → 自动触发 group_discussion
- group_discussion 中有 `unresolved_issues` → 自动触发 deep_dive

---

### 4.2 OpenTelemetry 可观测性

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/infra/otel_config.py` | OTLP exporter + Prometheus metrics endpoint |
| `backend/infra/metrics.py` | 业务指标定义 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/server.py` | 初始化 OTel，添加 `/metrics` Prometheus 端点 |
| `backend/infra/ai_clients.py` | `generate_text()` 加 span + latency histogram + `max_retries=2` |
| `backend/research/qualitative_research.py` | planner/persona/synthesis 阶段加 span |
| `docker-compose.yml` | 添加 prometheus + grafana 可选服务 |

#### 核心业务指标

| 指标 | 类型 | 用途 |
|------|------|------|
| `projects_created_total` | Counter | 业务量追踪 |
| `pipeline_duration_seconds` | Histogram | 端到端耗时 |
| `persona_evaluation_duration_seconds` | Histogram | 单 persona 耗时 |
| `llm_call_duration_seconds` | Histogram | LLM 调用耗时 |
| `llm_call_errors_total` | Counter | LLM 错误率 |
| `repeated_phrase_rate` | Gauge | 质量门禁（>0.5 告警） |
| `minority_survival_rate` | Gauge | 质量门禁（<0.3 告警） |

---

### 4.3 前端 UX 升级

#### 技术选型

- **Zustand** — 轻量全局状态（替代 Redux 的繁琐 boilerplate）
- **TanStack Query** — 服务端状态管理（缓存/去重/重试/乐观更新）
- **react-hot-toast** — Toast 通知

#### 新建文件

| 文件 | 职责 |
|------|------|
| `frontend/src/stores/projectStore.js` | 项目状态（选中项目、轮询、过滤） |
| `frontend/src/stores/authStore.js` | 认证状态 |
| `frontend/src/hooks/useProjects.js` | React Query: `useProjects`, `useProject`, `useRunProject` |
| `frontend/src/hooks/useReports.js` | React Query: `useReports`, `useReport`, `useShareReport` |
| `frontend/src/components/ProjectStatus.jsx` | 实时状态条（进度 + 阶段 + 错误） |
| `frontend/src/components/ReportViewer.jsx` | Tab 式报告（摘要 / Personas / 证据 / 指标） |
| `frontend/src/components/PersonaSelector.jsx` | 画像选择器（卡片预览 rubric/budget/veto） |
| `frontend/src/components/Toast.jsx` | Toast 通知封装 |
| `frontend/src/pages/ProjectDetail.jsx` | 项目详情页（状态/Brief/研究计划/附件） |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `frontend/src/App.jsx` | 添加 `/projects/:id` 路由 |
| `frontend/src/lib/api.js` | 迁移到 React Query，移除手动 loading/error 状态 |
| `frontend/src/pages/Dashboard.jsx` | useProjects hook + 实时状态指示器 |
| `frontend/src/pages/NewProject.jsx` | useRunProject + 成功后跳转详情页 |
| `frontend/src/pages/PersonaLibrary.jsx` | usePersonas + budget_band 搜索筛选 |
| `frontend/package.json` | 添加 `zustand`, `@tanstack/react-query`, `react-hot-toast` |

---

### 4.4 多模态支持

#### 理由

`backend/infra/ai_clients.py` 已有 OCR（RapidOCR）和 vision model（`AIClientConfig.vision_model`）能力，但研究管线中的附件仅以文件名文本传入 prompt，从未调用图像分析。

#### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/infra/media_processor.py` | 统一媒体处理：图片验证、缩略图生成、vision 模型分析 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `backend/research/qualitative_research.py` | persona prompt 加入 `[IMAGE]` 引用已上传图片 |
| `backend/infra/ai_clients.py` | 实现 `analyze_image(image_url_or_path, prompt) -> str` |
| `backend/workflow/task_session_manager.py` | `_apply_attachment_enrichment_v2` 扩展 vision 分析 |
| `backend/api/routers/upload.py` | 新增 `GET /api/upload/{filename}/preview` 缩略图端点 |

---

### 4.5 i18n 国际化

#### 新建文件

| 文件 | 职责 |
|------|------|
| `frontend/src/i18n/index.js` | i18next 初始化配置 |
| `frontend/src/i18n/zh-CN.json` | 中文翻译 |
| `frontend/src/i18n/en.json` | 英文翻译 |
| `frontend/src/components/LanguageSwitch.jsx` | 语言切换组件 |

#### 需修改文件

| 文件 | 改动 |
|------|------|
| `frontend/src/main.jsx` | 初始化 i18next |
| `frontend/src/components/layout/Layout.jsx` | Header 添加语言切换 |
| 所有页面文件 | 硬编码中文 → `t('key')` |
| `frontend/package.json` | 添加 `i18next`, `react-i18next` |

---

## 5. 全局技术栈演进

| 层级 | 当前 | Phase 1 | Phase 2 | Phase 3 |
|------|------|---------|---------|---------|
| **数据库** | JSON 文件 | PostgreSQL 16 + SQLAlchemy | — | — |
| **认证** | 无 | JWT (python-jose) | — | — |
| **任务队列** | BackgroundTasks | — | Celery + Redis | — |
| **缓存** | InMemoryStore | — | Redis 适配器 | — |
| **日志** | logging.basic | — | structlog (JSON) | — |
| **CI/CD** | 无 | — | GitHub Actions | — |
| **APM** | 无 | — | — | OpenTelemetry + Prometheus |
| **前端状态** | useState | React Context | — | Zustand + TanStack Query |
| **前端国际化** | 无 | — | — | i18next |
| **前端测试** | 无 | — | Vitest | Vitest + Playwright |
| **Python lint** | 无 | — | ruff + mypy | — |

---

## 6. 跨阶段关注点

### 6.1 数据迁移

| 阶段 | 策略 |
|------|------|
| Phase 1 | 一次性 JSON→DB 迁移脚本，幂等，旧文件保留 1 周 |
| Phase 2 | Alembic 增量迁移（新增 `personas` 表等） |
| Phase 3 | Alembic 增量迁移 |

### 6.2 向后兼容

- Phase 1 保持 `TaskSession` / `TaskSessionManager` 公开 API 签名不变
- 内部实现从文件 I/O 改为 DB，但 `load(session_id) -> TaskSession` 和 `save(session)` 签名不变
- Phase 2 可演进 API

### 6.3 停机策略

| 阶段 | 策略 |
|------|------|
| Phase 1 | 一次性迁移窗口（~30 min） |
| Phase 2 | 滚动部署，零停机 |
| Phase 3 | 滚动部署，零停机 |

### 6.4 密钥管理

- Phase 1：Settings 从 `.env` 迁移到 DB `system_settings` 表
- `.env` 仅保留 bootstrap 密钥（`DATABASE_URL`, `OPENAI_API_KEY` 初始值）
- Phase 3：可集成 vault 服务

---

## 7. 核心改动文件清单

| 文件 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| `backend/workflow/task_session_manager.py` | DB-backed save/load | Redis store 接入 | — |
| `backend/api/routers/projects.py` | DB 查询替换文件扫描 | Celery 替换 BackgroundTasks | 新增 group discussion 参数 |
| `backend/api/routers/reports.py` | DB 查询替换文件扫描 | — | — |
| `backend/api/routers/dashboard.py` | SQL 聚合替换文件遍历 | — | — |
| `backend/domain/evidence_models.py` | — | 动态维度 | — |
| `backend/domain/persona_scoring.py` | — | 动态维度评分 | — |
| `backend/infra/redis_infra.py` | — | RedisStore 适配器 | — |
| `backend/research/qualitative_research.py` | — | 动态维度 + 样本随机化 | 启用 group discussion/deep dive |
| `backend/infra/ai_clients.py` | — | max_retries=2 | OTel span + analyze_image |
| `backend/api/server.py` | Auth 路由 + CORS 收紧 | Redis store 初始化 | OTel + metrics 端点 |
| `frontend/src/lib/api.js` | Auth header + retry | — | React Query 迁移 |
| `frontend/src/App.jsx` | AuthProvider + 路由守卫 | — | 新路由 + Zustand |

---

## 8. 依赖变更总览

### Phase 1 新增

```
# requirements.txt
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### Phase 2 新增

```
# requirements.txt
celery[redis]>=5.3.0
redis>=5.0.0
ruff>=0.4.0          # dev
mypy>=1.10.0         # dev
pytest>=8.0.0        # dev
pytest-asyncio>=0.23.0  # dev
pytest-cov>=5.0.0    # dev
httpx>=0.27.0        # dev
structlog>=24.0.0
```

```
# frontend/package.json
// 无新增（Phase 2 主要在后端）
```

### Phase 3 新增

```
# requirements.txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-fastapi>=0.40b0
opentelemetry-exporter-otlp>=1.20.0
prometheus-client>=0.20.0
```

```
# frontend/package.json
zustand
@tanstack/react-query
react-hot-toast
i18next
react-i18next
```

---

## 9. 验证策略

### Phase 1

- [ ] `pytest tests/ --cov=backend` — auth/DB/migration 覆盖率 > 80%
- [ ] 手动测试：注册 → 登录 → 创建项目 → 运行 → 查看报告
- [ ] 手动测试：未登录访问 Settings 页面被拦截
- [ ] JSON 迁移脚本对现有数据执行成功

### Phase 2

- [ ] CI pipeline 全绿（lint + test + build）
- [ ] `celery -A backend.tasks.celery_app worker` 正常消费任务
- [ ] Redis 连接后 EventDeduplicator / SuspendQueue 正常工作
- [ ] 新评分维度在 4 类评审中产生差异化结果
- [ ] 随机抽样模式下 25 样本池可正常取样

### Phase 3

- [ ] `GET /metrics` 返回 Prometheus 格式指标
- [ ] Group Discussion 功能触发后报告中包含讨论轮次和关键分歧
- [ ] 前端 Playwright E2E 测试通过（登录 → 创建 → 报告查看）
- [ ] i18n 中英文切换正常
- [ ] 图片附件在 persona 评估中被引用

---

## 10. 风险与缓解

| 风险 | 严重度 | 缓解措施 |
|------|--------|----------|
| JSON→DB 迁移数据丢失 | 高 | 迁移脚本幂等，旧文件保留 1 周备份 |
| JWT 泄露 | 高 | 短有效期（30min）+ refresh token + HttpOnly cookie |
| Celery worker 崩溃 | 中 | Redis 持久化 + 任务 retry(max_retries=3) |
| 评分维度变更导致历史报告不一致 | 中 | Alembic 版本锁定 + 报告中记录 schema version |
| 前端大规模改造引入回归 | 中 | Phase 1 先加 ErrorBoundary，渐进迁移 |
| Persona 随机抽样导致结果不稳定 | 低 | 默认每 segment 抽 3 个增加稳定性，支持固定种子 |

---

## 11. 实施进度

> 每完成一项在此记录，格式：`[状态] 阶段.编号 项目名 — 完成内容`

### Phase 1

| # | 项目 | 状态 | 完成日期 | 备注 |
|---|------|------|----------|------|
| 1.1 | PostgreSQL 数据库层 | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 1.2 | 认证与 RBAC | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 1.3 | 前端基础设施 | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 1.4 | 测试与配置 | ✅ 已完成 | 2026-04-13 | 见下方明细 |

### Phase 2

| # | 项目 | 状态 | 完成日期 | 备注 |
|---|------|------|----------|------|
| 2.1 | Celery 任务队列 | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 2.2 | Redis 适配器 | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 2.3 | 评分体系动态化 | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 2.4 | Persona CRUD + 样本随机化 | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 2.5 | CI/CD Pipeline | ✅ 已完成 | 2026-04-13 | 见下方明细 |
| 2.6 | 结构化日志 | ✅ 已完成 | 2026-04-13 | 见下方明细 |

#### 2.1 Celery 任务队列 — 完成明细

**新建文件（4 个）：**

| 文件 | 说明 |
|------|------|
| `backend/tasks/__init__.py` | 包入口 |
| `backend/tasks/celery_app.py` | Celery app 配置，Redis broker，JSON 序列化，prefetch=1 |
| `backend/tasks/project_tasks.py` | `execute_project_run` Celery task（bind=True, max_retries=3） |
| `backend/tasks/report_tasks.py` | `generate_report` Celery task（预留报告生成） |

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `backend/api/routers/projects.py` | `run_project` 默认使用 Celery `.delay()`，自动 fallback 到 BackgroundTasks；新增 `GET /api/projects/{id}/task-status` 端点 |
| `docker-compose.yml` | +`celery-worker`（concurrency=4）和 `celery-beat` 服务 |
| `requirements.txt` | +`celery[redis]>=5.3.0`, `redis>=5.0.0` |

#### 2.2 Redis 适配器 — 完成明细

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `backend/infra/redis_infra.py` | +`RedisStore(KeyValueStore)` 生产实现 + `create_store(url)` 工厂函数（连接失败自动 fallback InMemoryStore） |
| `backend/api/server.py` | `startup` 事件初始化 `app.state.store = create_store(REDIS_URL)` |
| `backend/workflow/task_session_manager.py` | 构造函数新增可选 `store: KeyValueStore` 参数 |

#### 2.3 评分体系动态化 — 完成明细

**新建文件（1 个）：**

| 文件 | 说明 |
|------|------|
| `backend/domain/scoring_registry.py` | 6 种 task_type 维度配置：concept_test / packaging_review / copy_feedback / ab_test / price_test / product_concept，含维度名、中文标签、权重、阈值 |

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `backend/domain/evidence_models.py` | `PersonaEvaluation` 新增 `rubric_scores: Dict[str, int]` + `buy_threshold` / `reject_threshold`；`compute_intent()` 改为动态迭代 rubric_scores；`EvidenceAtom.field` 改为 str 类型 |
| `backend/domain/persona_scoring.py` | `compute_purchase_intent()` 新增 `task_type` 参数，使用 `get_scoring_config()` 获取权重和阈值 |
| `backend/research/qualitative_research.py` | `_extract_rubric_scores()` 支持 `task_type` 参数获取动态维度；`compute_purchase_intent()` 调用传入 `task_type` |

#### 2.4 Persona CRUD + 样本随机化 — 完成明细

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `backend/db/models.py` | +`Persona` ORM 表（id/name/budget_band/veto_trigger/decision_weights/veto_rules/feature_scoring_rubric/tags/is_custom） |
| `backend/api/routers/personas.py` | +`POST /personas`（Editor+）、`PUT /personas/{id}`（Editor+）、`DELETE /personas/{id}`（Admin，禁止删除 M01-M08）；+`GET /personas/{id}/samples?count=3&seed=` 随机取样端点 |
| `backend/research/qualitative_research.py` | +`SAMPLES_PER_SEGMENT = 25` + `select_random_persona_sample()` 函数支持可重复随机抽样 |

#### 2.5 CI/CD Pipeline — 完成明细

**新建文件（4 个）：**

| 文件 | 说明 |
|------|------|
| `.github/workflows/ci.yml` | lint → test → build 流水线：backend-lint（ruff+mypy）、backend-test（pytest --cov + postgres/redis services）、frontend-lint、frontend-test（vitest）、docker-build |
| `.github/workflows/cd.yml` | 部署流水线：staging（main push 触发）+ production（tag 触发），支持 workflow_dispatch |
| `frontend/vitest.config.js` | Vitest 配置：jsdom 环境、src/**/*.test.js |
| `frontend/src/__tests__/api.test.js` | 前端 API 层基础测试（5 个 case：导出函数验证） |

**修改文件（1 个）：**

| 文件 | 改动 |
|------|------|
| `frontend/package.json` | +`vitest`, `jsdom` devDeps；+`test` / `test:watch` scripts |

#### 2.6 结构化日志 — 完成明细

**新建文件（1 个）：**

| 文件 | 说明 |
|------|------|
| `backend/infra/logging_config.py` | structlog JSON renderer + `request_id_var` ContextVar + `RequestIdMiddleware` + `generate_request_id()` |

**修改文件（7 个）：**

| 文件 | 改动 |
|------|------|
| `backend/api/server.py` | `logging.basicConfig` → `configure_structlog()`；+`RequestIdMiddleware`（注入 X-Request-ID，记录 method/path/status/duration） |
| `backend/api/routers/personas.py` | `logging` → `structlog.get_logger` |
| `backend/api/routers/projects.py` | `logging` → `structlog.get_logger` |
| `backend/api/routers/reports.py` | `logging` → `structlog.get_logger` |
| `backend/api/routers/dashboard.py` | `logging` → `structlog.get_logger` |
| `backend/api/routers/settings.py` | `logging` → `structlog.get_logger` |
| `backend/api/routers/upload.py` | `logging` → `structlog.get_logger` |
| `requirements.txt` | +`structlog>=24.0.0` |

#### 1.1 PostgreSQL 数据库层 — 完成明细

**新建文件（6 个）：**

| 文件 | 说明 |
|------|------|
| `backend/db/__init__.py` | 包入口 |
| `backend/db/session.py` | async engine + session factory + `get_session()` FastAPI 依赖 |
| `backend/db/models.py` | 7 张 ORM 表：users / projects / reports / share_tokens / audit_log / system_settings / frozen_snapshots |
| `backend/db/repositories.py` | 5 个 Repository：ProjectRepo / ReportRepo / UserRepo / SettingsRepo / AuditLogRepo |
| `backend/db/migrate_from_json.py` | 一次性 JSON→DB 迁移脚本（幂等），含 bootstrap admin 用户 |
| `backend/db/migrations/env.py` + `versions/001_initial_schema.py` | Alembic 异步迁移环境 + 初始 schema |

**新增文件（1 个）：**

| 文件 | 说明 |
|------|------|
| `alembic.ini` | Alembic 配置，指向 `backend/db/migrations` |

**修改文件（2 个）：**

| 文件 | 改动 |
|------|------|
| `requirements.txt` | +`sqlalchemy[asyncio]>=2.0.0`, `asyncpg>=0.29.0`, `alembic>=1.13.0`, `python-jose[cryptography]>=3.3.0`, `passlib[bcrypt]>=1.7.4` |
| `docker-compose.yml` | +`postgres:16-alpine` 服务（含 healthcheck）、`pg_data` 卷、backend `DATABASE_URL` 环境变量、depends_on postgres |

#### 1.2 认证与 RBAC — 完成明细

**新建文件（4 个）：**

| 文件 | 说明 |
|------|------|
| `backend/auth/__init__.py` | 包入口 |
| `backend/auth/security.py` | JWT 创建/解码（python-jose）、密码哈希/验证（passlib bcrypt） |
| `backend/auth/dependencies.py` | `get_current_user()` + `require_role()` FastAPI 依赖 |
| `backend/auth/routes.py` | 5 个认证端点：register / login / refresh / me / users |

**新增 API 端点：**

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| POST | `/api/auth/register` | 无 | 注册（首个用户自动为 admin） |
| POST | `/api/auth/login` | 无 | 返回 access_token + refresh_token |
| POST | `/api/auth/refresh` | Refresh token | 刷新 token 对 |
| GET | `/api/auth/me` | Bearer | 当前用户信息 |
| GET | `/api/auth/users` | Admin | 用户列表 |

**修改文件（9 个）：**

| 文件 | 改动 |
|------|------|
| `backend/api/server.py` | 引入 auth_router，注册到 app |
| `backend/api/routers/projects.py` | 5 个端点加 `Depends(get_current_user)` |
| `backend/api/routers/reports.py` | 6 个端点加 auth（`get_shared_report` 保持公开） |
| `backend/api/routers/dashboard.py` | 1 个端点加 auth |
| `backend/api/routers/settings.py` | GET 用 `require_role(admin,editor,viewer)`，PUT/test 用 `require_role(admin)` |
| `backend/api/routers/personas.py` | 2 个端点加 auth |
| `backend/api/routers/upload.py` | 1 个端点加 auth |
| `backend/api/routers/image_generation.py` | 1 个端点加 auth |

**权限矩阵：**

| 资源 | Admin | Editor | Viewer |
|------|-------|--------|--------|
| 创建/运行项目 | ✓ | ✓ | ✓ (后续可收紧) |
| 查看项目/报告 | ✓ | ✓ | ✓ |
| 系统设置读取 | ✓ | ✓ | ✓ |
| 系统设置修改 | ✓ | ✗ | ✗ |
| 用户管理 | ✓ | ✗ | ✗ |

#### 1.3 前端基础设施 — 完成明细

**新建文件（4 个）：**

| 文件 | 说明 |
|------|------|
| `frontend/src/contexts/AuthContext.jsx` | AuthProvider + useAuth hook：login/register/logout/token 管理/自动 refresh |
| `frontend/src/components/ProtectedRoute.jsx` | 路由守卫：未登录重定向 /login |
| `frontend/src/components/LoginPage.jsx` | 登录/注册页面，表单验证 |
| `frontend/src/components/ErrorBoundary.jsx` | 错误边界：捕获子组件异常，显示重试按钮 |

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `frontend/src/lib/api.js` | `request()` 自动附加 Authorization header；401 时自动 refresh token（重试一次）；120s AbortController 超时；新增 login/register/getMe 端点；`setOnUnauthorized` 回调 |
| `frontend/src/App.jsx` | AuthProvider 包裹整个应用；/login 路由公开访问；所有其他路由包裹 ProtectedRoute；ErrorBoundary 包裹 Routes；注册 api.js 401 回调自动跳转登录 |
| `frontend/src/components/layout/Sidebar.jsx` | 硬编码用户头像（JD/研究负责人）替换为 useAuth() 动态数据；新增 logout 按钮 |

#### 1.4 测试与配置 — 完成明细

**新建文件（3 个）：**

| 文件 | 说明 |
|------|------|
| `tests/conftest.py` | 共享 fixtures：db_session、test_client（httpx.AsyncClient）、auth_headers、admin_client |
| `tests/test_auth.py` | 9 个测试：注册/重复邮箱/登录/错误密码/refresh/me/无 token 401/受保护端点 401/admin 用户列表 |
| `tests/test_projects_db.py` | 6 个测试：Project CRUD / get_by_session_id / list_by_owner / update / Report CRUD / ShareToken 创建与撤销 |

**新建文件（1 个）：**

| 文件 | 说明 |
|------|------|
| `pyproject.toml` | pytest（asyncio_mode=auto）、ruff、mypy 配置 |

**修改文件（1 个）：**

| 文件 | 改动 |
|------|------|
| `requirements.txt` | +`pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `pytest-cov>=5.0.0`, `httpx>=0.27.0`, `ruff>=0.4.0`, `mypy>=1.10.0` |

**运行方式：**
```powershell
# 安装测试依赖
pip install -r requirements.txt pytest-asyncio httpx

# 运行测试（需 PostgreSQL 实例）
python -m pytest tests/test_auth.py tests/test_projects_db.py -v
```

### Phase 3

| # | 项目 | 状态 | 完成日期 | 备注 |
|---|------|------|----------|------|
| 3.1 | 研究方法论增强 | ✅ 已完成 | 2026-04-14 | 见下方明细 |
| 3.2 | OpenTelemetry 可观测性 | ✅ 已完成 | 2026-04-14 | 见下方明细 |
| 3.3 | 前端 UX 升级 | ✅ 已完成 | 2026-04-14 | 见下方明细 |
| 3.4 | 多模态支持 | ✅ 已完成 | 2026-04-14 | 见下方明细 |
| 3.5 | i18n 国际化 | ✅ 已完成 | 2026-04-14 | 见下方明细 |

#### 3.1 研究方法论增强 — 完成明细

**修改文件（4 个）：**

| 文件 | 改动 |
|------|------|
| `backend/research/qualitative_research.py` | 增强 `_run_group_discussion()` 为三轮结构化辩论（立场陈述→交叉反应→共识探索）；新增 `_select_discussion_participants()` 多样性选择策略；增强 `_run_deep_dive()` 为冲突驱动选择+迭代深度探询；新增 `_select_deep_dive_personas()` 和 `_compute_divergence_score()`；添加自动触发逻辑（divergence>0.5 自动 group discussion，unresolved_issues 自动 deep dive） |
| `backend/api/routers/projects.py` | `CreateProjectRequest` 新增 `enable_group_discussion` / `enable_deep_dive` 字段；`create_project` 持久化研究方法标志 |
| `backend/workflow/task_session_manager.py` | `build_research_input_payload()` 提取并传递 `enable_group_discussion` / `enable_deep_dive` 标志到 `QualitativeResearchInput` |
| `backend/workflow/langgraph_state.py` | `AnalysisGraphState` 和 `DingTalkWorkflowState` 新增 `group_discussion` / `deep_dive_results` 字段 |
| `backend/workflow/langgraph_nodes.py` | `make_run_research_node` 从 report 中提取 group_discussion/deep_dive_results 写入 state |

#### 3.2 OpenTelemetry 可观测性 — 完成明细

**新建文件（2 个）：**

| 文件 | 说明 |
|------|------|
| `backend/infra/otel_config.py` | OpenTelemetry SDK 配置：OTLP exporter + Prometheus metrics，`configure_otel()` + `get_tracer()` / `get_meter()` 工厂函数 |
| `backend/infra/metrics.py` | 业务指标定义：`projects_created_total`、`pipeline_duration_seconds`、`persona_evaluation_duration_seconds`、`llm_call_duration_seconds`、`llm_call_errors_total`、`repeated_phrase_rate`、`minority_survival_rate` |

**修改文件（4 个）：**

| 文件 | 改动 |
|------|------|
| `backend/api/server.py` | `startup` 事件调用 `configure_otel()`；新增 `GET /metrics` Prometheus 端点 |
| `backend/infra/ai_clients.py` | `generate_text()` 内 `execute()` 函数添加 LLM 调用耗时测量和 `record_llm_call()` 指标记录 |
| `backend/research/qualitative_research.py` | `run()` 方法添加 `record_pipeline_duration()` 管道耗时指标 |
| `requirements.txt` | +`opentelemetry-api>=1.20.0`, `opentelemetry-sdk>=1.20.0`, `opentelemetry-exporter-otlp>=1.20.0`, `prometheus-client>=0.20.0` |
| `docker-compose.yml` | 新增 `prometheus` 服务（`profiles: [monitoring]`），+`prometheus_data` 卷 |

#### 3.3 前端 UX 升级 — 完成明细

**新建文件（8 个）：**

| 文件 | 说明 |
|------|------|
| `frontend/src/stores/authStore.js` | Zustand auth store：user/fetchUser/setUser/clearUser |
| `frontend/src/stores/projectStore.js` | Zustand project store：selectedProjectId/filterStatus |
| `frontend/src/hooks/useProjects.js` | React Query hooks：`useProjects`、`useProject`、`useProjectStatus`（3s 自动轮询）、`useCreateProject`、`useRunProject` |
| `frontend/src/hooks/useReports.js` | React Query hooks：`useReports`、`useReport`、`useShareReport` |
| `frontend/src/components/Toast.jsx` | react-hot-toast 封装：`ToastContainer`、`notifySuccess/Error/Info` |
| `frontend/src/components/ProjectStatus.jsx` | 实时状态条：进度条 + 阶段指示器 + 自动轮询 |
| `frontend/src/components/ReportViewer.jsx` | Tab 式报告查看器：摘要/画像反馈/焦点讨论/证据/指标 5 个 tab |
| `frontend/src/components/PersonaSelector.jsx` | 画像选择器：卡片预览 budget_band/veto_trigger/tags |
| `frontend/src/pages/ProjectDetail.jsx` | 项目详情页：状态/Brief/研究计划/附件 + 报告查看器 |

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `frontend/src/App.jsx` | 添加 `QueryClientProvider` 包裹；新增 `/projects/:id` 路由；添加 `ToastContainer` |
| `frontend/src/pages/NewProject.jsx` | 新增 `enable_group_discussion` / `enable_deep_dive` 研究方法增强 toggle UI |
| `frontend/src/pages/Dashboard.jsx` | 任务名添加链接到 `/projects/:id` |
| `frontend/package.json` | +`zustand`, `@tanstack/react-query`, `react-hot-toast` |

#### 3.4 多模态支持 — 完成明细

**新建文件（1 个）：**

| 文件 | 说明 |
|------|------|
| `backend/infra/media_processor.py` | 统一媒体处理：`is_image_file()`、`validate_image()`、`generate_thumbnail()`、`analyze_image_with_vision()` |

**修改文件（2 个）：**

| 文件 | 改动 |
|------|------|
| `backend/research/qualitative_research.py` | `QualitativeResearchRunner` 新增 `_analyze_image_attachments()` 方法；`run()` 方法在 Layer 1 之前分析图片附件，将 vision 分析结果追加到 `background_material`，使 persona 评估时能引用图片内容 |
| `backend/api/routers/upload.py` | 新增 `GET /api/upload/{filename}/preview` 缩略图端点 |

#### 3.5 i18n 国际化 — 完成明细

**新建文件（4 个）：**

| 文件 | 说明 |
|------|------|
| `frontend/src/i18n/index.js` | i18next 初始化配置：支持 zh-CN/en，localStorage 持久化语言选择 |
| `frontend/src/i18n/zh-CN.json` | 中文翻译（120+ key）：app/nav/auth/dashboard/project/status/report/common |
| `frontend/src/i18n/en.json` | 英文翻译（120+ key） |
| `frontend/src/components/LanguageSwitch.jsx` | 中/EN 语言切换按钮组件 |

**修改文件（3 个）：**

| 文件 | 改动 |
|------|------|
| `frontend/src/main.jsx` | 添加 `import './i18n'` 初始化 i18next |
| `frontend/src/components/layout/Header.jsx` | Header 右侧添加 `LanguageSwitch` 组件 |
| `frontend/package.json` | +`i18next`, `react-i18next` |
