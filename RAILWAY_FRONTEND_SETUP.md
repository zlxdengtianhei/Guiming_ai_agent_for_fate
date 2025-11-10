# Railway 前端部署配置说明

## ⚠️ 重要：需要在 Railway Dashboard 中设置 Root Directory

由于前端代码在 `frontend/` 子目录中，**必须在 Railway Dashboard 中设置 Root Directory**。

### 设置步骤

1. **访问 Railway Dashboard**
   - 打开：https://railway.com/project/6a314fab-5684-4ede-a7b9-4700f96f61f3
   - 进入服务 "tarot-agent-frontend"

2. **设置 Root Directory**
   - 进入 **Settings** 标签页
   - 找到 **"Root Directory"** 设置
   - 点击 **"Edit"**
   - 输入：`frontend`
   - 点击 **"Save"**

3. **配置环境变量**
   在 **Variables** 标签页添加：
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://nlolchueqdqzlhjrzjvi.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sb2xjaHVlcWRxemxoanJ6anZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIxNzQ1ODUsImV4cCI6MjA3Nzc1MDU4NX0.Alnzmdvl-c5zmmTGCidqDnU5DplTljBFYbhWAMsMRKg
   NEXT_PUBLIC_API_URL=https://tarot-agent-production.up.railway.app
   ```

4. **重新部署**
   - 设置完成后，Railway 会自动触发重新部署
   - 或手动点击 **"Redeploy"**

## 配置说明

### 已创建的配置文件

- `frontend/railway.json` - Railway 构建配置
- `frontend/nixpacks.toml` - Nixpacks 构建配置
- `frontend/.railwayignore` - 忽略不需要的文件

### 构建流程

1. **Install Phase**: `npm ci` (使用 package-lock.json，更快更可靠)
2. **Build Phase**: `npm run build` (构建 Next.js 应用)
3. **Start Phase**: `npm run start` (启动生产服务器)

### 预期结果

设置 Root Directory 后，构建应该能够：
- ✅ 正确找到 `package.json`
- ✅ 安装依赖
- ✅ 构建 Next.js 应用
- ✅ 启动生产服务器

## 故障排除

### 如果构建仍然失败

1. **检查 Root Directory 是否设置正确**
   - 确保设置为 `frontend`（不是 `/frontend` 或 `./frontend`）

2. **检查环境变量**
   - 确保所有 `NEXT_PUBLIC_*` 变量都已添加

3. **查看构建日志**
   - 在 Railway Dashboard 中查看详细的构建日志
   - 查找具体的错误信息

4. **检查 Node.js 版本**
   - Railway 应该自动检测到 Node.js 18
   - 如果需要特定版本，可以在 `package.json` 中添加 `engines` 字段

## 访问地址

部署成功后，前端将在：
- **URL**: https://tarot-agent-frontend-production.up.railway.app

## 更新后端 CORS

部署成功后，记得更新后端的 CORS 设置：

访问后端项目：https://railway.com/project/5cb57f16-c34b-41b1-b26f-b6e855e59f29

在服务 "tarot-agent" 的 Variables 中添加/更新：
```
CORS_ORIGINS=https://tarot-agent-frontend-production.up.railway.app,http://localhost:3000
```

