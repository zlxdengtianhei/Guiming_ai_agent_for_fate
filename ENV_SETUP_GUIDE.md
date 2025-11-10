# Railway 环境变量设置详细指南

## ⚠️ 当前问题
应用崩溃是因为缺少必需的环境变量。从错误日志可以看到：
- `supabase_url` - Field required
- `supabase_service_role_key` - Field required

## ✅ 解决步骤

### 方法 1：在 Railway Dashboard 中设置（推荐）

1. **访问服务页面**
   - 打开：https://railway.com/project/5cb57f16-c34b-41b1-b26f-b6e855e59f29
   - 点击服务名称：**tarot-agent**

2. **进入 Variables 标签页**
   - 在服务页面顶部，点击 **"Variables"** 标签
   - ⚠️ 确保是在 **服务级别** 的 Variables，不是项目级别的

3. **添加必需的环境变量**
   点击 **"New Variable"** 按钮，逐个添加以下变量：

   | 变量名 | 值 | 说明 |
   |--------|-----|------|
   | `SUPABASE_URL` | `https://nlolchueqdqzlhjrzjvi.supabase.co` | Supabase 项目 URL |
   | `SUPABASE_SERVICE_ROLE_KEY` | 你的 Service Role Key | ⚠️ 保密！从 Supabase Dashboard 获取 |
   | `USE_OPENROUTER` | `true` 或 `false` | 是否使用 OpenRouter |
   | `OPENROUTER_API_KEY` | 你的 OpenRouter API Key | 如果 USE_OPENROUTER=true |
   | `OPENAI_API_KEY` | 你的 OpenAI API Key | 如果 USE_OPENROUTER=false |

4. **重要检查点**
   - ✅ 变量名必须**完全匹配**（区分大小写）
   - ✅ 确保添加到 **服务级别**（Service Variables），不是项目级别
   - ✅ 每个变量添加后点击保存
   - ✅ 所有变量添加完成后，Railway 会自动重新部署

5. **验证设置**
   - 在 Variables 页面，你应该能看到所有添加的变量
   - 等待部署完成后，检查日志是否还有错误

### 方法 2：使用 Railway CLI

如果你有 API keys，可以运行：

```bash
railway variables --service ae39b7d2-ce9a-418e-a366-5859dbcdb769 \
  --set "SUPABASE_URL=https://nlolchueqdqzlhjrzjvi.supabase.co" \
  --set "SUPABASE_SERVICE_ROLE_KEY=你的key" \
  --set "USE_OPENROUTER=true" \
  --set "OPENROUTER_API_KEY=你的key"
```

## 🔍 如何获取 API Keys

### Supabase Service Role Key
1. 登录 https://supabase.com/dashboard
2. 选择项目
3. 进入 **Settings** → **API**
4. 找到 **"service_role"** key（⚠️ 这是敏感密钥，不要泄露）
5. 复制并粘贴到 Railway Variables

### OpenRouter API Key
1. 访问 https://openrouter.ai
2. 注册/登录账户
3. 进入 **Keys** 页面
4. 创建新的 API key
5. 复制并粘贴到 Railway Variables

### OpenAI API Key（如果不用 OpenRouter）
1. 访问 https://platform.openai.com
2. 登录账户
3. 进入 **API keys** 页面
4. 创建新的 API key
5. 复制并粘贴到 Railway Variables

## ✅ 验证设置是否成功

设置完成后，可以通过以下方式验证：

1. **在 Dashboard 中检查**
   - Variables 页面应该显示所有添加的变量
   - 部署日志中不应该再有 "Field required" 错误

2. **通过 CLI 检查**
   ```bash
   railway variables --service ae39b7d2-ce9a-418e-a366-5859dbcdb769
   ```
   应该能看到 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY`

3. **检查应用日志**
   - 如果设置成功，应用应该能正常启动
   - 日志中应该看到 "Application startup complete" 或类似信息

## 🚨 常见问题

### Q: 为什么添加了变量还是报错？
A: 检查以下几点：
- 变量名是否正确（区分大小写）
- 是否添加到了服务级别（不是项目级别）
- 是否保存了变量
- 等待部署完成（可能需要几分钟）

### Q: 如何确认变量添加到了正确的位置？
A: 在 Variables 页面，确保：
- 页面标题显示的是服务名称 "tarot-agent"
- 不是项目级别的 Variables

### Q: 变量添加后多久生效？
A: Railway 会自动触发重新部署，通常需要 1-3 分钟。

