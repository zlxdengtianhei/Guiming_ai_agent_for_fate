# 前端部署指南

## 方案 1：Vercel 部署（推荐 ⭐）

Vercel 是 Next.js 的官方平台，提供最佳性能和零配置体验。

### 部署步骤

1. **访问 Vercel**
   - 打开 https://vercel.com
   - 使用 GitHub 账号登录

2. **导入项目**
   - 点击 "New Project"
   - 选择你的 GitHub 仓库：`Guiming_ai_agent_for_fate`
   - Vercel 会自动检测到 Next.js 项目

3. **配置构建设置**
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

4. **配置环境变量**
   在 Vercel 项目设置中添加以下环境变量：
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://nlolchueqdqzlhjrzjvi.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sb2xjaHVlcWRxemxoanJ6anZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIxNzQ1ODUsImV4cCI6MjA3Nzc1MDU4NX0.Alnzmdvl-c5zmmTGCidqDnU5DplTljBFYbhWAMsMRKg
   NEXT_PUBLIC_API_URL=https://tarot-agent-production.up.railway.app
   ```

5. **部署**
   - 点击 "Deploy"
   - 等待构建完成（通常 2-3 分钟）
   - 获得 Vercel URL，例如：`https://your-app.vercel.app`

### Vercel 优势

- ✅ 零配置，自动检测 Next.js
- ✅ 全球 CDN，超快速度
- ✅ 自动 HTTPS
- ✅ Git 集成，每次推送自动部署
- ✅ 免费套餐足够使用
- ✅ Next.js 特性完美支持（ISR、API Routes 等）

---

## 方案 2：Railway 部署（备选）

Railway 也支持 Next.js，但需要更多配置。

### 部署步骤

1. **在 Railway 创建新服务**
   ```bash
   # 使用 Railway CLI
   cd frontend
   railway init
   railway link
   ```

2. **配置环境变量**
   在 Railway Dashboard 或使用 CLI：
   ```bash
   railway variables --set "NEXT_PUBLIC_SUPABASE_URL=https://nlolchueqdqzlhjrzjvi.supabase.co"
   railway variables --set "NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key"
   railway variables --set "NEXT_PUBLIC_API_URL=https://tarot-agent-production.up.railway.app"
   ```

3. **部署**
   ```bash
   railway up
   ```

### Railway 配置文件

如果需要自定义配置，创建 `railway.json`：
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "npm run start",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

## 推荐配置

### 使用 Vercel 的完整架构

```
前端 (Vercel)          后端 (Railway)
     |                      |
     |                      |
https://your-app.vercel.app  →  https://tarot-agent-production.up.railway.app
     |                      |
     |                      |
     └──────────────────────┴───── Supabase (数据库)
```

### 环境变量总结

**前端（Vercel）需要的环境变量：**
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` = `https://tarot-agent-production.up.railway.app`

**后端（Railway）已配置的环境变量：**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `USE_OPENROUTER`
- `OPENROUTER_API_KEY`
- 等等...

---

## 部署后配置

1. **更新 CORS**
   部署前端后，在 Railway 中更新后端的 CORS 设置：
   ```bash
   railway variables --service ae39b7d2-ce9a-418e-a366-5859dbcdb769 \
     --set "CORS_ORIGINS=https://your-vercel-app.vercel.app,http://localhost:3000"
   ```

2. **测试连接**
   - 访问前端 URL
   - 测试登录功能
   - 测试塔罗占卜功能

---

## 常见问题

### Q: Vercel 免费吗？
A: 是的，Vercel 提供慷慨的免费套餐，对于个人项目完全够用。

### Q: 可以使用自定义域名吗？
A: 可以。在 Vercel 项目设置中添加自定义域名，按照提示配置 DNS。

### Q: 如何查看部署日志？
A: 在 Vercel Dashboard → 项目 → Deployments → 点击具体部署 → 查看日志。

### Q: 前端和后端在不同平台，会有问题吗？
A: 不会。这是推荐的做法。前端用 Vercel，后端用 Railway，通过 API 通信。

