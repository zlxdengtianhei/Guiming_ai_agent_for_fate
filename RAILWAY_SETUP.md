# Railway 部署配置指南

## 必需的环境变量

在 Railway Dashboard 中配置以下环境变量：

### 1. Supabase 配置（必需）

```
SUPABASE_URL=https://nlolchueqdqzlhjrzjvi.supabase.co
SUPABASE_SERVICE_ROLE_KEY=你的_supabase_service_role_key
```

### 2. LLM API 配置（必需 - 二选一）

**选项 A：使用 OpenRouter（推荐）**
```
USE_OPENROUTER=true
OPENROUTER_API_KEY=你的_openrouter_api_key
```

**选项 B：直接使用 OpenAI**
```
USE_OPENROUTER=false
OPENAI_API_KEY=你的_openai_api_key
```

### 3. 可选配置

```
SUPABASE_ANON_KEY=你的_anon_key（可选）
SUPABASE_PUBLISHABLE_KEY=你的_publishable_key（可选）
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
MODEL_PRESET=gpt4omini_fast
```

## 如何在 Railway 中配置环境变量

1. 登录 Railway Dashboard
2. 选择项目：`tarot-agent`
3. 点击 "Variables" 标签页
4. 点击 "New Variable" 添加每个环境变量
5. 保存后，Railway 会自动重新部署

## 获取 API Keys

- **Supabase Service Role Key**: 
  - 登录 Supabase Dashboard
  - 进入项目设置 → API
  - 复制 "service_role" key（⚠️ 保密！）

- **OpenRouter API Key**:
  - 访问 https://openrouter.ai
  - 注册并获取 API key

- **OpenAI API Key**:
  - 访问 https://platform.openai.com
  - 创建 API key

