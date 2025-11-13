# Tarot Agent 项目架构概述

> Tarot Agent 是一个基于 AI 的塔罗占卜系统，结合 RAG（检索增强生成）技术和大语言模型，为用户提供深度个性化的塔罗占卜服务。

**快速导航**：
- [后端架构详解](./BACKEND_ARCHITECTURE.md) - 详细的后端服务、API、数据库设计
- [前端架构详解](./frontend/FRONTEND_ARCHITECTURE.md) - 详细的前端组件、状态管理、UI设计
- [更新日志](./CHANGELOG.md) - 最新的功能更新和Bug修复

---

## 🎯 项目概览

### 核心功能

1. **智能占卜系统**
   - 问题智能分析（识别领域、复杂度）
   - 自动选牌和牌型分析
   - RAG增强的解读生成
   - 实时流式输出（SSE）

2. **RAG知识检索**
   - 向量化塔罗牌文档（PKT + 78 Degrees of Wisdom）
   - 智能相似度搜索
   - 多数据源平衡
   - 去重和缓存优化

3. **用户系统**
   - Supabase认证（邮箱+密码）
   - 个人资料管理（星座、性格、偏好）
   - 占卜历史记录
   - 多语言支持（中文/英文）

---

## 📁 项目结构

```
tarot_agent/
├── backend/                      # FastAPI 后端服务
│   ├── app/
│   │   ├── api/routes/          # API端点（auth, user, tarot, rag）
│   │   ├── core/                # 配置管理（config, model_config, database）
│   │   ├── models/              # 数据模型（Pydantic schemas）
│   │   └── services/            # 业务逻辑
│   │       ├── rag.py           # RAG主服务
│   │       ├── embedding.py     # 向量嵌入
│   │       └── tarot/           # 塔罗占卜服务
│   │           ├── reading_service.py  # 占卜主流程 ⭐
│   │           ├── card_selection.py   # 选牌服务
│   │           ├── significator.py     # 代表牌选择
│   │           └── question_analyzer.py # 问题分析
│   ├── main.py                  # FastAPI应用入口
│   └── requirements.txt         # Python依赖
│
├── frontend/                     # Next.js 前端应用
│   ├── app/                     # Next.js App Router
│   │   ├── page.tsx            # 主页（占卜界面）⭐
│   │   ├── login/              # 登录/注册页
│   │   └── profile/            # 用户个人页面
│   ├── components/              # React组件
│   │   ├── tarot/              # 塔罗占卜组件
│   │   └── ui/                 # 基础UI组件
│   ├── contexts/                # React Context
│   │   ├── AuthContext.tsx     # 认证上下文
│   │   └── LanguageContext.tsx # 多语言上下文
│   └── lib/                     # 工具函数
│       ├── api.ts              # API客户端 ⭐
│       ├── i18n.ts             # 国际化
│       └── supabase.ts         # Supabase客户端
│
├── test/                         # 测试脚本
│   ├── test_complete_reading_with_logging.py  # 完整占卜测试
│   ├── test_rag_simple.py                    # RAG功能测试
│   └── result/                               # 测试结果日志
│
├── docs/                         # 文档和数据
│   ├── pkt.txt                  # PKT塔罗牌文档
│   ├── 78_degrees_of_wisdom.txt # 78 Degrees文档
│   └── rag_research.py          # RAG研究工具
│
├── database/                     # 数据库相关
│   ├── data/                    # JSON数据文件
│   ├── scripts/                 # 数据上传脚本
│   └── sql/                     # SQL建表脚本
│
├── sql/                          # Supabase SQL迁移脚本
│
├── ARCHITECTURE.md              # 本文件 - 项目整体概述
├── BACKEND_ARCHITECTURE.md      # 后端架构详解 ⭐
├── FRONTEND_ARCHITECTURE.md     # 前端架构详解 ⭐
└── CHANGELOG.md                 # 更新日志 ⭐
```

---

## 🔄 核心数据流

### 完整占卜流程

```
用户输入问题 → 问题分析(LLM) → 选择代表牌 → 选择牌阵卡牌
    ↓
前端开始显示卡牌动画(10秒)
    ↓
后端并行执行：
├─ 牌型分析(纯代码)
├─ RAG检索卡牌信息
└─ 生成意象描述(LLM, 流式) → 前端实时显示
    ↓
RAG检索占卜方法和牌关系(后台并行)
    ↓
生成最终解读(LLM, 流式) → 前端实时显示
    ↓
保存到数据库 → 完成
```

**关键时间节点**：
- 0-10s：卡牌动画
- 10-17s：意象描述生成（流式）
- 17-78s：最终解读生成（流式）
- 总时间：~78秒（使用 `gpt4omini_fast` 预设）

---

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (Python 3.9+)
- **数据库**: Supabase (PostgreSQL + pgvector)
- **AI模型**: 
  - GPT-4o-mini (问题分析、意象生成、最终解读 - 默认)
  - DeepSeek R1 (最终解读 - 可选，推理能力强)
  - Gemini 2.5 Pro (最终解读 - 可选，深度分析)
  - OpenAI text-embedding-3-small (向量嵌入)
- **API路由**: OpenRouter / OpenAI
- **向量索引**: HNSW (pgvector)

### 前端
- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **UI库**: Tailwind CSS + shadcn/ui
- **状态管理**: React Context
- **认证**: Supabase Auth
- **实时通信**: Server-Sent Events (SSE)

### 数据库
- **PostgreSQL** (Supabase托管)
- **pgvector扩展** (向量搜索)
- **Row Level Security** (RLS权限控制)

---

## 🚀 快速开始

### 1. 环境配置

**后端 `.env`**:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenRouter (推荐)
USE_OPENROUTER=true
OPENROUTER_API_KEY=your-api-key

# 模型预设（默认：gpt4omini_fast）
MODEL_PRESET=gpt4omini_fast
```

**前端 `.env.local`**:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. 启动服务

**后端**:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**前端**:
```bash
cd frontend
npm install
npm run dev
```

访问：`http://localhost:3000`

---

## 📊 性能优化

### 1. 模型配置优化 ⭐ 2025-01

**默认预设 `gpt4omini_fast`**：
- 问题分析：GPT-4o-mini
- 意象生成：GPT-4o-mini
- 最终解读：GPT-4o-mini（默认，用户可选择 DeepSeek R1 或 Gemini 2.5 Pro）

**性能提升**：
- 意象生成：44.5s → 6.7s (↑ 7x)
- 最终解读：128.7s → 3-5s (↑ 25-40x) ⚡
- **总时间：~220s → ~25-30s (↑ 7-9x)**

### 2. RAG系统优化

| 优化项 | 效果 | 状态 |
|--------|------|------|
| Embedding缓存 | 速度提升45-83% | ✅ |
| 数据源平衡 | 多数据源均衡使用 | ✅ |
| Chunk去重 | 减少重复69% | ✅ |
| 移除中间LLM调用 | 减少18次API调用 | ✅ |
| HNSW向量索引 | 搜索速度提升61% | ✅ |

### 3. 流式输出

- **Server-Sent Events (SSE)** 实现实时更新
- 意象描述和最终解读均支持流式输出
- 前端使用 `EventSource` 接收流式数据
- 大幅提升用户体验（无需等待所有内容生成完毕）

---

## 🗄️ 数据库设计

### 核心表

1. **readings** - 占卜记录
   - 问题、占卜方式、解读结果、意象描述

2. **selected_cards** - 选中的卡牌
   - 卡牌ID、位置、是否逆位

3. **reading_process_data** - 占卜过程数据 ⭐
   - 每个步骤的输入输出、LLM调用、处理时间
   - 用于调试和性能分析

4. **rag_documents** - RAG文档库
   - 文本chunks、向量embeddings、元数据
   - HNSW索引加速相似度搜索

5. **user_profiles** - 用户资料
   - 年龄、星座、性格、偏好设置

6. **tarot_cards** - 塔罗牌数据
   - 78张塔罗牌的基本信息、图片URL

详细数据库设计请参考：[BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md)

---

## 📱 主要功能

### 1. 智能占卜

**用户流程**：
1. 输入问题
2. (可选) 选择占卜方式
3. 系统分析问题，选择代表牌和牌阵卡牌
4. 观看卡牌动画（10秒）
5. 实时接收意象描述（流式输出）
6. 实时接收最终解读（流式输出）

**后端流程**：
1. 问题分析 (LLM)
2. 选择代表牌（基于用户资料和问题）
3. 选择牌阵卡牌（随机选择，30%概率逆位）
4. 牌型分析（纯代码，分析元素、数字、颜色分布）
5. RAG检索（卡牌信息、占卜方法、牌关系）
6. 生成意象描述（LLM，流式）
7. 生成最终解读（LLM，流式）

### 2. RAG知识检索

**数据源**：
- PKT (The Pictorial Key to the Tarot)
- 78 Degrees of Wisdom

**检索流程**：
1. 查询 → 生成embedding
2. 向量相似度搜索（HNSW索引）
3. 多数据源平衡选择
4. Chunk去重
5. 返回相关文档片段

**优化特性**：
- Embedding缓存（避免重复API调用）
- 动态相似度阈值（卡牌0.5，方法0.25）
- 全局去重（基于chunk_id）

### 3. 用户系统

**认证**：
- 邮箱+密码注册/登录
- 邮箱验证
- Token自动刷新（30天不活动才需重新登录）

**个人资料**：
- 基本信息：年龄、性别、星座
- 塔罗偏好：性格类型、数据源、代表牌选择优先级
- 语言设置：中文/英文

---

## 🔐 安全设计

### Row Level Security (RLS)

1. **user_profiles** - 用户只能访问自己的资料
2. **readings** - 用户只能访问自己的占卜记录
3. **reading_process_data** - 仅后端service role可访问（隐藏内部实现细节）

### API认证

- 所有需要认证的端点使用 Bearer Token
- Token通过 Supabase Auth 管理
- 自动刷新机制，30天不活动才过期

---

## 📚 文档导航

### 架构文档
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - 本文件，项目整体概述
- **[BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md)** - 后端详细架构 ⭐
- **[FRONTEND_ARCHITECTURE.md](./frontend/FRONTEND_ARCHITECTURE.md)** - 前端详细架构 ⭐

### 功能文档
- **[CHANGELOG.md](./CHANGELOG.md)** - 更新日志 ⭐
- **[STREAMING_OUTPUT_GUIDE.md](./backend/STREAMING_OUTPUT_GUIDE.md)** - 流式输出实现指南
- **[MODEL_SPEED_GUIDE.md](./MODEL_SPEED_GUIDE.md)** - 模型速度对比
- **[RAG_GUIDE.md](./RAG_GUIDE.md)** - RAG系统使用指南

### 设计文档
- **[TAROT_READING_SYSTEM_ARCHITECTURE.md](./TAROT_READING_SYSTEM_ARCHITECTURE.md)** - 占卜系统设计文档

---

## 🔧 开发指南

### 添加新的占卜方式

1. 在 `card_selection.py` 中添加位置定义
2. 在 `reading_service.py` 中更新占卜流程
3. 在前端 `components/tarot/` 中添加展示组件

### 添加新的数据源

1. 准备文档（.txt格式）
2. 使用 `chunker.py` 分块
3. 使用 `embedding.py` 生成向量
4. 插入到 `rag_documents` 表
5. 创建HNSW索引

### 添加新的模型预设

编辑 `backend/app/core/model_config.py`:
```python
class ModelPreset(str, Enum):
    MY_PRESET = "my_preset"

PRESETS: Dict[ModelPreset, Dict[str, str]] = {
    ModelPreset.MY_PRESET: {
        "question_analysis": "...",
        "imagery_generation": "...",
        "final_interpretation": "...",
    },
}
```

---

## 🚧 待优化项

### 高优先级
- [ ] DeepSeek R1 输出过滤（去除 `<think>` 标签）
- [ ] Redis缓存层（替代内存缓存）
- [ ] 批量RAG查询优化
- [ ] 监控和日志系统

### 中优先级
- [ ] 占卜历史统计和可视化
- [ ] 多种牌阵支持（生命树、关系牌阵等）
- [ ] 卡牌图片自动生成优化
- [ ] 移动端响应式优化

### 低优先级
- [ ] 社交分享功能
- [ ] 占卜结果导出（PDF/图片）
- [ ] 多人占卜模式
- [ ] 占卜社区功能

---

## 📈 项目进展

### 已完成 ✅
- 基础占卜流程
- RAG知识检索系统
- 用户认证和资料管理
- 流式输出（SSE）
- 性能优化（3倍速度提升）
- 多模型支持
- 多语言支持

### 进行中 🚧
- DeepSeek R1 输出优化
- 前端UI/UX优化
- 测试覆盖率提升

### 计划中 📋
- Redis缓存
- 监控系统
- 更多占卜方式

---

## 🤝 贡献指南

### 分支策略
- `main` - 生产分支
- `develop` - 开发分支
- `feature/*` - 功能分支

### 提交规范
```
feat: 添加新功能
fix: 修复Bug
docs: 文档更新
perf: 性能优化
refactor: 代码重构
test: 测试相关
```

---

## 📧 联系方式

**项目维护者**: Tarot Agent Team

**文档反馈**: 如有任何疑问或建议，请提交Issue

---

---

## 📝 最新更新

### API配置优化和调试增强 ⭐ 2025-11
- ✅ **API URL配置修复**：修复URL拼接问题，避免双斜杠导致的404错误
  - 自动移除环境变量末尾的斜杠
  - 确保URL拼接时不会出现 `//` 双斜杠
  - 改进错误处理，显示详细的错误信息
- ✅ **调试日志增强**：添加详细的调试信息，帮助诊断生产环境问题
  - 在浏览器控制台输出API配置信息（URL、环境变量状态）
  - 检测并警告常见配置问题（环境变量未设置、指向localhost、使用旧域名）
  - 所有调试信息输出到浏览器控制台，方便排查问题

**问题修复**：
- 修复生产环境404错误（URL拼接问题）
- 改进环境变量配置验证
- 增强错误诊断能力

**文件清单**：
- `frontend/lib/api.ts` - API URL配置修复，添加调试日志和错误检测

### 模型配置优化 ⭐ 2025-01
- ✅ **默认模型改为 GPT-4o-mini**：所有任务默认使用 `gpt-4o-mini`，提供快速响应
- ✅ **前端模型选择优化**：去除"默认"选项，默认选择 `gpt4omini`，用户可切换为 DeepSeek R1 或 Gemini 2.5 Pro
- ✅ **流式输出速率优化**：最终解读流式输出速率从 ~11字/秒提升到 20字/秒（50ms间隔，每次5个字）
- ✅ **问题框进度显示修复**：修复最终解读生成时问题框进度显示不更新的bug

**性能提升**：
- 最终解读流式输出：20字/秒（之前 ~11字/秒）
- 用户体验：问题框实时显示当前进度，包括"正在生成最终解读..."状态

**文件清单**：
- `frontend/app/profile/page.tsx` - 模型选择默认值改为 gpt4omini
- `frontend/app/page.tsx` - 流式输出速率优化，问题框进度显示修复
- `backend/app/services/tarot/reading_service.py` - 默认模型处理逻辑优化

---

*最后更新：2025-11*
*文档版本：v2.2*

