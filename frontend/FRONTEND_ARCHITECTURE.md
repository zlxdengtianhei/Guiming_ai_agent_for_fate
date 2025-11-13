# Tarot Agent 前端架构详解

## 📁 项目结构总览

```
frontend/
├── app/                              # Next.js App Router目录
│   ├── layout.tsx                    # 根布局组件（包含Provider）
│   ├── page.tsx                      # 主页面（问题输入）
│   ├── globals.css                   # 全局样式（暗蓝色主题）
│   ├── login/
│   │   └── page.tsx                  # 登录/注册页面
│   ├── auth/
│   │   └── callback/
│   │       └── page.tsx              # 邮箱确认回调页面 ⭐ 新增
│   ├── spread-selection/
│   │   └── page.tsx                  # 占卜方式选择页面
│   ├── manual-input/
│   │   └── page.tsx                  # 自行输入牌型页面
│   └── profile/
│       └── page.tsx                  # 用户个人页面
│
├── components/                       # React组件目录
│   ├── Sidebar.tsx                   # 侧边栏导航组件
│   ├── ProtectedRoute.tsx            # 路由保护组件
│   ├── tarot/                        # 塔罗占卜相关组件 ⭐ 新增
│   │   ├── ThreeCardSpread.tsx       # 三牌占卜展示组件
│   │   └── CelticCrossSpread.tsx     # 凯尔特十字占卜展示组件
│   └── ui/                           # UI基础组件
│       ├── Button.tsx                # 按钮组件
│       ├── Input.tsx                 # 输入框组件
│       ├── Textarea.tsx               # 文本域组件
│       └── TarotLoader.tsx            # 塔罗加载动画组件 ⭐ 新增
│
├── contexts/                         # React Context目录
│   ├── AuthContext.tsx               # 用户认证上下文
│   └── LanguageContext.tsx           # 多语言上下文
│
├── lib/                              # 工具函数和配置
│   ├── api.ts                        # API客户端封装
│   ├── i18n.ts                       # 国际化翻译文件
│   ├── supabase.ts                   # Supabase客户端配置
│   └── utils.ts                      # 通用工具函数
│
├── package.json                      # Node.js依赖和脚本
├── tsconfig.json                     # TypeScript配置
├── next.config.js                    # Next.js配置
├── env.example                       # 环境变量示例
└── README.md                         # 前端使用说明
```

## 🏗️ 技术栈

### 核心框架
- **Next.js 14.1.0** - React全栈框架，使用App Router
- **React 18.2.0** - UI库
- **TypeScript 5.3.3** - 类型安全

### 状态管理
- **React Context API** - 全局状态管理（认证、语言）
- **React Hooks** - 本地状态管理

### 样式方案
- **CSS Variables** - 主题颜色变量系统
- **Tailwind CSS** - 实用优先的CSS框架（通过类名使用）
- **自定义CSS** - 全局样式和主题定义

### HTTP客户端
- **Axios 1.6.5** - HTTP请求库
- **请求拦截器** - 自动添加认证Token

### 工具库
- **clsx** - 条件类名合并
- **tailwind-merge** - Tailwind类名合并和去重
- **@supabase/supabase-js** - Supabase客户端（备用）

## 📐 架构设计

### 1. 页面路由结构（App Router）

#### `/login` - 登录/注册页面
- **功能**: 用户认证入口
- **特性**:
  - 登录/注册模式切换
  - 表单验证
  - 错误处理
  - 自动跳转到主页
  - **邮箱确认流程**: 注册后显示邮箱确认提示
  - **重新发送确认邮件**: 支持重新发送确认邮件功能

#### `/auth/callback` - 邮箱确认回调页面 ⭐ 新增
- **功能**: 处理 Supabase 邮箱确认回调
- **特性**:
  - 解析 URL hash 参数（access_token, refresh_token等）
  - 自动保存认证 token 到 localStorage
  - 显示确认成功/失败状态
  - 自动跳转到主页（确认成功后）
  - 错误处理和用户友好提示

#### `/` - 主页面（问题输入）
- **功能**: 塔罗占卜问题输入和结果显示
- **特性**:
  - 问题输入区域（完成后固定在顶部，使用sticky定位）
  - **流式占卜流程**：支持实时显示占卜进度和流式解读输出 ⭐ 新增
  - **状态显示**：分析问题、抽取卡牌、生成意象、生成解读等各阶段状态
    - **状态显示卡片**：在分析问题阶段显示"正在分析问题..."，保持显示直到卡牌组件显示 ⭐ 已优化 - 2025年11月
    - **忽略 `started` 事件**：`started` 事件不更新UI状态，确保状态显示卡片不会提前消失
  - **占卜方式选择**：支持从URL参数选择占卜方式（`?spread=three_card` 或 `?spread=celtic_cross`）⭐ 新增
    - 当URL参数存在时，使用指定的占卜方式，不传递 `preferred_spread`，避免污染用户偏好
    - 当URL参数不存在时，根据用户的 `preferred_spread` 偏好或问题分析自动选择
  - **卡牌展示**：根据占卜方式自动选择展示组件（三牌或十字）
    - **加载动画位置**：加载动画只显示在卡牌组件下方，不在标题右侧 ⭐ 已优化 - 2025年11月
      - 当没有卡牌显示时：显示大型加载动画和"正在抽取卡牌..."文字
      - 当有部分卡牌显示时：在卡牌下方显示小型加载动画和"正在显示卡牌..."提示
    - **渐进式显示**：根据占卜类型动态调整显示时间 ⭐ 已优化 - 2025年11月
    - 三牌占卜：5秒内显示完3张牌
    - 十字占卜：10秒内显示完10张牌
  - **意象描述**：可折叠展示，点击查看详情
    - **自动显示**：卡牌显示完成后1秒自动显示意象框 ⭐ 已优化 - 2025年11月
    - **流式输出**：实时流式显示意象描述文本 ⭐ 已优化 - 2025年11月
  - **流式解读**：实时显示解读文本，支持自动滚动和展开
    - **自动显示**：意象生成完成后1秒自动显示解读框 ⭐ 已优化 - 2025年11月
    - **流式输出**：实时流式显示解读文本，React自动批量处理更新 ⭐ 已优化 - 2025年11月
  - 占卜结果展示
  - 卡牌信息展示
  - 实时加载状态
  - **来源页面标记**: 自动标记为 'home'

#### `/spread-selection` - 占卜方式选择
- **功能**: 选择占卜方式（三牌或十字）
- **特性**:
  - 两种占卜方式卡片展示
  - 点击跳转到主页面（`/?spread=three_card` 或 `/?spread=celtic_cross`）
  - 占卜方式介绍按钮
  - **偏好保护**：选择占卜方式不会更新用户的 `preferred_spread` 偏好设置 ⭐ 新增

#### `/manual-input` - 自行输入牌型
- **功能**: 手动输入卡牌名称进行占卜
- **特性**:
  - 根据占卜方式动态显示输入框数量（从URL参数 `?spread=three_card` 或 `?spread=celtic_cross` 获取）
  - 卡牌位置标签（过去/现在/未来等）
  - 表单验证
  - 占卜结果展示
  - **来源页面标记**: 自动标记为 'manual-input'
  - **偏好保护**：使用URL参数中的占卜方式，不传递 `preferred_spread`，避免污染用户偏好 ⭐ 新增

#### `/profile` - 用户个人页面
- **功能**: 用户信息管理和偏好设置
- **特性**:
  - 基本信息编辑（年龄、性别、星座）
  - 占卜偏好设置（外观类型、性格类型、数据源、占卜方式、语言）
  - 实时语言切换
  - 表单保存和更新

### 2. 组件架构

#### 布局组件

**`Sidebar.tsx`** - 侧边栏导航组件
- **功能**: 提供全局导航和用户信息
- **特性**:
  - 响应式设计（移动端可折叠）
  - 导航菜单项
  - 用户信息显示
  - 退出登录功能
  - 多语言支持
  - **占卜记录列表**：显示最近10条占卜记录，包括问题、来源页面和时间
  - 自动刷新：创建新占卜后自动更新记录列表
- **状态管理**: 使用本地state管理展开/折叠状态和占卜记录列表

**`ProtectedRoute.tsx`** - 路由保护组件
- **功能**: 保护需要认证的页面
- **特性**:
  - 检查用户认证状态
  - 未认证时重定向到登录页
  - 加载状态显示

#### UI基础组件

**`Button.tsx`** - 按钮组件
- **变体**: primary, secondary, outline, ghost
- **尺寸**: sm, md, lg
- **特性**: 统一的样式系统，支持禁用状态

**`Input.tsx`** - 输入框组件
- **特性**: 
  - 统一的样式
  - 焦点状态
  - 占位符支持
  - 禁用状态

**`Textarea.tsx`** - 文本域组件
- **特性**:
  - 多行文本输入
  - 自动调整大小（可选）
  - 统一的样式系统

**`TarotLoader.tsx`** - 塔罗加载动画组件 ⭐ 新增
- **功能**: 在所有加载状态时显示塔罗主题的加载动画
- **特性**:
  - 使用四个塔罗图标（圣杯、宝剑、权杖、钱币）轮转显示，主图标位于第二个位置
  - 左至右的不透明度逐步降低，左侧保持更高亮度以强化动态层次
  - 淡入淡出动画效果（500ms 过渡）
  - 每 800ms 切换一次图标
  - 支持三种尺寸：sm, md, lg
  - 使用 SVG 矢量图形，适配不同分辨率
- **使用场景**:
  - 占卜进行中的状态显示
  - 登录/注册时的加载状态
  - 表单提交时的加载状态
  - 认证检查时的加载状态
  - 数据加载时的状态显示

#### 塔罗占卜组件 ⭐ 新增

**`ThreeCardSpread.tsx`** - 三牌占卜展示组件
- **功能**: 展示三牌占卜的卡牌布局
- **特性**:
  - 水平排列三张卡牌，支持左右滑动查看
  - 点击卡牌显示详情（卡牌名称、位置、是否逆位）
  - 滑动指示器显示当前选中卡牌
  - 默认聚焦中间卡牌，底部仅保留卡牌展示区域（移除额外角色提示）
  - 所有内容居中显示
  - 响应式设计，适配移动端和桌面端
- **Props**:
  - `cards`: 卡牌数据数组
  - `positions`: 位置标签数组（过去/现在/未来）

**`CelticCrossSpread.tsx`** - 凯尔特十字占卜展示组件
- **功能**: 展示凯尔特十字占卜的卡牌布局
- **特性**:
  - **中心十字布局**：前6张牌形成十字形状
    - 第1张牌在中心（cover/situation）
    - 第2张牌横跨在第1张牌上（crossing/challenge）
    - 第3张牌在下方（basis/past）
    - 第4张牌在左侧（behind/past）
    - 第5张牌在上方（crowned/goal）
    - 第6张牌在右侧（before/future）
  - **权杖/高塔布局**：后4张牌垂直排列在右侧
    - 第7张牌（self/attitude）
    - 第8张牌（environment）
    - 第9张牌（hopes_and_fears/hope）
    - 第10张牌（outcome）
  - 紧凑视图和展开视图两种显示模式
  - 点击卡牌查看详情
  - 所有内容居中显示
  - 响应式设计
- **Props**:
  - `cards`: 卡牌数据数组

### 3. Context架构

#### `AuthContext.tsx` - 认证上下文
- **功能**: 管理用户认证状态和用户信息
- **状态**:
  - `user`: 当前用户信息
  - `profile`: 用户个人资料
  - `loading`: 加载状态
- **方法**:
  - `signin(email, password)`: 用户登录
  - `signup(email, password)`: 用户注册（支持邮箱确认流程）
  - `signout()`: 用户登出
  - `refreshProfile()`: 刷新用户资料
- **特性**:
  - 自动从localStorage恢复登录状态
  - Token自动管理
  - 用户资料自动加载
  - **邮箱确认支持**: 检测是否需要邮箱确认，不自动登录
  - **认证状态监听**: 监听 `authStateChanged` 事件，自动刷新用户状态

#### `LanguageContext.tsx` - 多语言上下文
- **功能**: 管理界面语言和翻译
- **状态**:
  - `language`: 当前语言（'zh' | 'en'）
- **方法**:
  - `setLanguage(lang)`: 设置语言
  - `t(key)`: 获取翻译文本
- **特性**:
  - 根据用户profile自动设置语言
  - 语言偏好持久化到localStorage
  - 实时语言切换

### 4. API客户端架构

#### `lib/api.ts` - API客户端
- **功能**: 封装所有后端API调用
- **模块**:
  - `apiClient`: Axios实例，配置了基础URL和请求拦截器
  - `authAPI`: 认证相关API（signup, signin, signout, getMe, resendConfirmation）
  - `userAPI`: 用户资料API（getProfile, createProfile, updateProfile）
  - `tarotAPI`: 塔罗占卜API（createReading, createReadingStream, getReading, listReadings）⭐ 新增流式API
- **特性**:
  - 自动添加认证Token到请求头
  - 统一的错误处理
  - TypeScript类型定义
  - **邮箱确认支持**: `SignUpResponse` 包含 `requires_email_confirmation` 字段
  - **重新发送确认邮件**: `resendConfirmation` 方法支持重新发送确认邮件
  - **流式占卜API**: `createReadingStream` 方法支持Server-Sent Events (SSE)流式输出 ⭐ 新增
    - 使用fetch API和ReadableStream处理SSE数据流
    - 支持进度更新（progress事件）
    - 支持流式解读文本（interpretation事件）
    - 支持完成信号（complete事件）
    - 支持错误处理（error事件）
  - **API URL配置优化** ⭐ 新增 - 2025年11月
    - 自动移除环境变量末尾的斜杠，避免URL拼接时出现双斜杠
    - 确保URL拼接正确：`${baseUrl}${path}` 格式
    - 改进错误处理，显示详细的错误信息（状态码、URL、错误响应）
  - **调试日志增强** ⭐ 新增 - 2025年11月
    - 在浏览器控制台输出API配置信息（API_URL、NEXT_PUBLIC_API_URL、NODE_ENV）
    - 检测并警告常见配置问题：
      - 生产环境环境变量未设置
      - 生产环境指向localhost
      - 使用旧域名（guimingaiagentforfate-production）
    - 所有调试信息输出到浏览器控制台，方便排查生产环境问题

### 5. 国际化架构

#### `lib/i18n.ts` - 翻译文件
- **功能**: 定义所有翻译文本
- **结构**:
  - `translations.zh`: 中文翻译
  - `translations.en`: 英文翻译
- **特性**:
  - 类型安全的翻译键
  - 完整的翻译覆盖
  - 易于扩展新语言

#### 多语言处理策略
- **文字长度处理**:
  - 使用`break-words`处理长文本换行
  - 使用`truncate`处理文本溢出
  - 使用`min-w-0`和`flex-shrink-0`控制flex布局
  - 按钮设置最小宽度避免文字过短
- **布局适配**:
  - 响应式设计适配不同语言长度
  - 使用flex布局确保元素正确对齐

### 6. 样式架构

#### 主题系统（`globals.css`）
- **颜色变量**:
  - `--bg-primary`: 主背景色 (#0f172a)
  - `--bg-secondary`: 次要背景色 (#1e293b)
  - `--bg-tertiary`: 第三级背景色 (#334155)
  - `--text-primary`: 主文本色 (#e2e8f0)
  - `--text-secondary`: 次要文本色 (#94a3b8)
  - `--text-muted`: 弱化文本色 (#64748b)
  - `--border-color`: 边框色 (#334155)
  - `--accent-blue`: 强调蓝色 (#3b82f6)
  - `--accent-blue-light`: 浅蓝色 (#60a5fa)
  - `--accent-blue-dark`: 深蓝色 (#2563eb)

#### 设计原则
- **暗蓝色低饱和度主题**: 护眼的暗色主题
- **统一的颜色系统**: 使用CSS变量确保一致性
- **响应式设计**: 支持桌面和移动设备
- **无障碍设计**: 良好的对比度和焦点状态

## 🔄 数据流

### 1. 认证流程

#### 登录流程
```
用户登录
  ↓
AuthContext.signin()
  ↓
调用 authAPI.signin()
  ↓
保存Token到localStorage
  ↓
更新AuthContext状态
  ↓
加载用户profile
  ↓
重定向到主页
```

#### 注册和邮箱确认流程 ⭐ 新增
```
用户注册
  ↓
AuthContext.signup()
  ↓
调用 authAPI.signup()
  ↓
检查 requires_email_confirmation
  ↓
如果需要邮箱确认:
  - 显示邮箱确认提示
  - 不自动登录
  - 用户点击邮件中的确认链接
  ↓
跳转到 /auth/callback
  ↓
解析 URL hash 参数（access_token, refresh_token）
  ↓
保存Token到localStorage
  ↓
触发 authStateChanged 事件
  ↓
AuthContext 自动刷新用户状态
  ↓
自动跳转到主页
```

#### 重新发送确认邮件流程 ⭐ 新增
```
用户点击"重新发送确认邮件"
  ↓
调用 authAPI.resendConfirmation()
  ↓
后端调用 Supabase resend API
  ↓
显示成功/错误消息
```

### 2. 占卜流程

#### 传统占卜流程（非流式）
```
用户输入问题
  ↓
调用 tarotAPI.createReading()
  ↓
携带用户profile信息和source_page（来源页面）
  ↓
显示加载状态
  ↓
接收占卜结果
  ↓
更新页面状态显示结果
  ↓
触发 'readingCreated' 事件，刷新侧边栏占卜记录列表
```

#### 流式占卜流程 ⭐ 新增（已优化 - 2025年11月）
```
用户输入问题
  ↓
调用 tarotAPI.createReadingStream()
  ↓
携带用户profile信息和source_page（来源页面）
  - 如果URL参数中有占卜方式，不传递 preferred_spread，避免污染用户偏好 ⭐ 新增
  ↓
问题输入框固定在顶部（sticky定位）
  ↓
显示"正在分析问题"状态卡片 ⭐ 已优化 - 2025年11月
  - 忽略 `started` 事件，不更新 currentStep，保持状态显示卡片显示
  - 状态显示卡片保持显示，直到收到 cards_selected 事件
  ↓
接收 question_analysis 事件，问题分析完成
  ↓
接收 cards_selected 事件，立即显示卡牌组件 ⭐ 已优化 - 2025年11月
  - 状态显示卡片自动隐藏
  - 卡牌组件立即显示，如果还没有卡牌则显示"正在抽取卡牌..."加载动画
  ↓
RAG检索开始，接收 rag_card_progress 事件（每完成一张卡牌）⭐ 新增
  ↓
达到阈值时接收 rag_first_card_ready 事件，立即显示第一张卡牌 ⭐ 新增
  - 三牌占卜：完成1/3后显示第一张牌
  - 十字占卜：完成1/10后显示第一张牌
  ↓
渐进式显示所有卡牌（根据占卜类型动态调整时间）⭐ 已优化 - 2025年11月
  - 三牌占卜：5秒内显示完3张牌（每张约1.67秒）
  - 十字占卜：10秒内显示完10张牌（每张1秒）
  ↓
所有卡牌显示完成后，等待1秒显示意象描述框 ⭐ 已优化 - 2025年11月
  ↓
RAG检索完成（核心卡牌RAG，~10秒），接收 rag_retrieved 事件 ⭐ 已优化
  ↓
接收 imagery_chunk 事件，实时流式显示意象描述（直接追加，React批量处理）⭐ 已优化 - 2025年11月
  ↓
接收 imagery_generated 事件，意象描述完成 ⭐ 已优化 - 2025年11月
  ↓
意象生成完成后，等待1秒显示解读框 ⭐ 已优化 - 2025年11月
  ↓
接收流式解读文本，实时流式显示（直接追加，React批量处理）⭐ 已优化 - 2025年11月
  ↓
完成，触发 'readingCreated' 事件，刷新侧边栏占卜记录列表
```

**流式流程特点**：
- **实时反馈**：每个步骤都有对应的状态显示
- **状态管理优化**：⭐ **新增 - 2025年11月**
  - 忽略 `started` 事件，不更新UI状态，避免状态显示卡片提前消失
  - 状态显示卡片保持显示，直到卡牌组件显示，实现无缝过渡
  - 卡牌组件一旦收到 `cards_selected` 事件立即显示，无延迟
- **加载动画位置优化**：⭐ **新增 - 2025年11月**
  - 卡牌组件标题不再显示加载动画，UI更简洁
  - 所有加载动画统一显示在卡牌组件下方
  - 根据卡牌显示状态智能显示不同大小的加载动画
- **渐进式展示**：卡牌、意象、解读逐步显示，提升用户体验
- **RAG检索进度跟踪**：⭐ **新增 - 2025年1月**
  - 实时接收每张卡牌的检索进度
  - 达到阈值时立即显示第一张卡牌，减少等待感
  - 后端使用 `asyncio.as_completed()` 实现真正的进度跟踪
- **卡牌显示时间优化**：⭐ **新增 - 2025年11月**
  - 三牌占卜：5秒内显示完3张牌（每张约1.67秒）
  - 十字占卜：10秒内显示完10张牌（每张1秒）
  - 根据占卜类型自动计算显示间隔，节奏更合理
- **RAG与流式输出并行优化**：⭐ **新增 - 2025年11月**
  - 核心卡牌RAG完成后（~10秒）立即开始流式输出，无需等待完整RAG流程
  - 后台RAG任务（spread_method + card_relationships）在意象生成时并行执行
  - 意象描述和最终解读无缝衔接，用户无需等待
- **意象描述流式输出**：⭐ **已优化 - 2025年11月**
  - 接收 `imagery_chunk` 事件，实时流式显示意象描述
  - 直接使用 `setState(prev => prev + chunk)` 追加文本
  - React自动批量处理更新，实现真正的流式效果
  - 接收 `imagery_generated` 事件标志意象完成
- **流式输出机制**：⭐ **已优化 - 2025年11月**
  - 移除缓冲区机制和打字机效果，避免延迟和重复字符问题
  - 直接追加文本块，React自动批量处理快速连续的更新
  - 意象描述和解读文本都能实时流式显示
  - 禁用自动滚动，让用户自己控制 ⭐ **已优化 - 2025年1月**
- **智能展开**：如果用户没有交互，自动展开解读框；如果用户已打开其他框，则在底部保持流式输出
- **渲染逻辑优化**：⭐ **新增 - 2025年11月**
  - 简化渲染条件判断，直接使用状态变量
  - 移除不必要的中间变量和重复判断
  - 代码更简洁，性能更好

### 3. 语言切换流程
```
用户在profile页面更改语言
  ↓
调用 setLanguage()
  ↓
更新LanguageContext状态
  ↓
保存到localStorage
  ↓
界面立即更新翻译文本
  ↓
保存到用户profile
```

## 🔐 安全机制

### 1. 路由保护
- **ProtectedRoute组件**: 包装需要认证的页面
- **自动重定向**: 未认证用户自动跳转到登录页
- **Token验证**: 通过API拦截器自动添加Token

### 2. Token管理
- **存储位置**: localStorage
- **自动添加**: 通过Axios拦截器自动添加到请求头
- **自动清理**: 登出时清除所有Token

### 3. 错误处理
- **统一错误显示**: 所有API错误统一处理
- **用户友好提示**: 错误信息翻译成用户语言
- **错误边界**: React错误边界处理组件错误

## 📱 响应式设计

### 断点策略
- **移动端**: < 768px
  - 侧边栏可折叠
  - 汉堡菜单按钮
  - 全屏覆盖层
- **桌面端**: >= 768px
  - 固定侧边栏
  - 展开/折叠按钮
  - 侧边栏工具提示

### 布局适配
- **Flex布局**: 使用flex确保元素正确对齐
- **Grid布局**: 卡片网格响应式调整
- **文本处理**: 使用break-words和truncate处理长文本

## 🎨 UI/UX设计

### 设计原则
1. **简洁性**: 清晰的视觉层次和简洁的界面
2. **一致性**: 统一的组件样式和交互模式
3. **可访问性**: 良好的对比度和焦点状态
4. **响应性**: 流畅的动画和过渡效果

### 交互模式
- **加载状态**: 按钮禁用和加载文本
- **错误反馈**: 红色错误提示框
- **成功反馈**: 绿色成功提示框
- **悬停效果**: 按钮和链接的悬停状态

## 🚀 性能优化

### 1. 代码分割
- **Next.js自动代码分割**: 每个页面自动分割
- **动态导入**: 按需加载组件

### 2. 状态管理优化
- **Context优化**: 避免不必要的重渲染
- **本地状态**: 使用useState管理组件本地状态
- **流式输出优化**: ⭐ **新增 - 2025年11月**
  - 直接使用 `setState(prev => prev + chunk)` 追加文本
  - React自动批量处理快速连续的更新，避免频繁重渲染
  - 移除缓冲区机制和打字机效果，减少不必要的计算

### 3. 资源优化
- **CSS变量**: 减少重复样式代码
- **组件复用**: 复用UI组件减少代码量

### 4. 渲染优化 ⭐ **新增 - 2025年11月**
- **简化条件判断**: 直接使用状态变量，移除不必要的中间变量
- **移除冗余日志**: 移除渲染时的调试输出，提升性能
- **简化useEffect**: 合并重复逻辑，减少不必要的依赖项
- **代码简化**: 移除约50行冗余代码，提升可维护性

## 📦 依赖管理

### 生产依赖
- `next`: Next.js框架
- `react`: React库
- `react-dom`: React DOM渲染
- `axios`: HTTP客户端
- `clsx`: 类名工具
- `tailwind-merge`: Tailwind类名合并
- `@supabase/supabase-js`: Supabase客户端

### 开发依赖
- `typescript`: TypeScript编译器
- `@types/node`: Node.js类型定义
- `@types/react`: React类型定义
- `@types/react-dom`: React DOM类型定义
- `eslint`: 代码检查工具
- `eslint-config-next`: Next.js ESLint配置

## 🔧 开发工具

### 脚本命令
- `npm run dev`: 启动开发服务器
- `npm run build`: 构建生产版本
- `npm run start`: 启动生产服务器
- `npm run lint`: 运行ESLint检查

### 环境变量
- `NEXT_PUBLIC_API_URL`: 后端API地址（默认: http://localhost:8000）
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase项目URL（可选）
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase匿名密钥（可选）

## 📝 代码规范

### TypeScript
- **严格模式**: 启用strict模式
- **类型定义**: 所有API响应都有类型定义
- **接口定义**: 使用interface定义组件props

### 组件规范
- **函数组件**: 使用函数组件和Hooks
- **命名规范**: PascalCase用于组件，camelCase用于函数和变量
- **文件组织**: 按功能组织文件结构

### 样式规范
- **CSS变量**: 使用CSS变量定义主题
- **Tailwind类**: 优先使用Tailwind实用类
- **自定义样式**: 仅在必要时添加自定义CSS

## 🔄 更新日志

### 2025年11月 - API配置优化和调试增强 ⭐ 最新

**核心优化**：
- ✅ **API URL配置修复**：修复生产环境404错误问题
  - **URL拼接问题修复**：自动移除环境变量末尾的斜杠，避免URL拼接时出现 `//` 双斜杠
  - **错误处理改进**：显示详细的错误信息（状态码、URL、错误响应），方便诊断问题
  - **URL构建优化**：使用 `${baseUrl}${path}` 格式，确保URL拼接正确
- ✅ **调试日志增强**：添加详细的调试信息，帮助诊断生产环境问题
  - **配置信息输出**：在浏览器控制台输出API配置信息（API_URL、NEXT_PUBLIC_API_URL、NODE_ENV）
  - **配置问题检测**：自动检测并警告常见配置问题
    - 生产环境环境变量未设置
    - 生产环境指向localhost
    - 使用旧域名（guimingaiagentforfate-production）
  - **错误详情输出**：API调用失败时输出详细的错误信息，包括URL、状态码、错误响应

**问题背景**：
- 用户反映：生产环境进行占卜时出现404错误
- 错误信息：`guimingaiagentforfate-production.up.railway.app//api/tarot/reading/stream`（注意双斜杠）
- 原因：环境变量可能包含末尾斜杠，导致URL拼接时出现双斜杠，或者环境变量配置错误

**解决方案**：
- 自动移除环境变量末尾的斜杠：`rawApiUrl.replace(/\/+$/, '')`
- 确保URL拼接正确：使用 `${baseUrl}${path}` 格式
- 添加详细的调试日志，帮助快速定位问题
- 检测并警告常见配置问题，提前发现问题

**文件清单**：
- `frontend/lib/api.ts` - API URL配置修复，添加调试日志和错误检测

**用户体验提升**：
- ✅ 修复生产环境404错误，占卜功能正常工作
- ✅ 调试信息清晰，方便排查配置问题
- ✅ 自动检测配置问题，提前发现并警告

**技术实现**：
- **URL处理**：使用正则表达式移除末尾斜杠，确保URL拼接正确
- **调试日志**：在浏览器控制台输出配置信息，使用 `console.log` 和 `console.error`
- **错误检测**：检查环境变量状态、URL格式、域名等，提前发现问题

**更新时间**：2025年11月

### 2025年11月 - 占卜流程UI优化和状态管理改进

**核心优化**：
- ✅ **修复"正在分析问题"组件闪烁问题**：解决状态显示卡片过早消失的问题
  - **忽略 `started` 事件**：`started` 事件是通知性事件，不应该影响UI状态
  - 当收到 `started` 事件时，不更新 `currentStep`，保持 `question_analysis` 状态
  - 确保"正在分析问题"组件保持显示，直到收到 `cards_selected` 事件
  - 卡牌组件一旦收到 `cards_selected` 事件立即显示，实现无缝过渡
- ✅ **优化卡牌组件加载动画位置**：简化UI，加载动画只显示在下方
  - **移除标题右侧加载动画**：卡牌组件标题不再显示加载动画
  - **统一加载动画位置**：所有加载动画和提示文字只显示在卡牌组件下方
    - 当没有卡牌显示时：显示大型加载动画和"正在抽取卡牌..."文字
    - 当有部分卡牌显示时：在卡牌下方显示小型加载动画和"正在显示卡牌..."提示
- ✅ **占卜方式选择偏好保护**：防止临时选择污染用户偏好设置
  - 当用户从URL参数选择占卜方式时（`?spread=three_card` 或 `?spread=celtic_cross`），不传递 `preferred_spread` 到 `user_profile`
  - 只有当用户没有从URL参数选择占卜方式时，才传递用户的 `preferred_spread` 偏好
  - 确保临时选择不会影响用户的偏好设置

**问题背景**：
- 用户反映："正在分析问题"组件会闪烁一下然后消失，直到卡牌组件显示
- 原因：后端发送 `started` 事件导致 `currentStep` 变成 `started`，状态显示卡片的显示条件是 `currentStep === 'question_analysis'`，所以提前消失
- 卡牌组件标题右侧的加载动画显得冗余，影响UI简洁性

**解决方案**：
- 忽略 `started` 事件，不更新 `currentStep`，让状态显示卡片保持显示
- 移除标题中的加载动画，统一在下方显示加载状态
- 检测URL参数中的 `selectedSpread`，当存在时不传递 `preferred_spread`

**文件清单**：
- `frontend/app/page.tsx` - 忽略 `started` 事件，移除标题加载动画，添加占卜方式选择偏好保护逻辑

**用户体验提升**：
- ✅ "正在分析问题"组件保持显示，直到卡牌组件显示，无闪烁和空隙
- ✅ 卡牌组件加载动画位置统一，UI更简洁清晰
- ✅ 临时选择占卜方式不会影响用户偏好设置，体验更友好

**技术实现**：
- **事件过滤**：在进度更新回调中检查 `step === 'started'`，如果是则直接返回，不更新状态
- **UI简化**：移除 `CardTitle` 中的 `flex` 布局和加载动画组件
- **偏好保护**：添加 `shouldUseUserPreference` 变量，根据URL参数决定是否传递 `preferred_spread`

**更新时间**：2025年11月

### 2025年1月 - 占卜方式选择偏好保护

**核心修复**：
- ✅ **修复占卜方式选择污染用户偏好问题**：当用户从占卜方式选择页面选择占卜方式时，不会更新用户的 `preferred_spread` 偏好设置
  - **主页面**：当从URL参数选择占卜方式时（`?spread=three_card` 或 `?spread=celtic_cross`），不传递 `preferred_spread` 到 `user_profile`
  - **手动输入页面**：总是使用URL参数中的 `spreadType`，不传递 `preferred_spread`
  - 确保临时选择不会影响用户的偏好设置，用户的 `preferred_spread` 只在个人资料页面手动修改时才会更新

**问题背景**：
- 用户反映：从占卜方式选择页面选择占卜方式后，后续占卜会一直使用这个方式，而不是根据问题分析自动选择
- 原因：前端在传递 `user_profile` 时包含了 `preferred_spread`，可能被后端误用或更新

**解决方案**：
- 当用户从URL参数明确选择占卜方式时，不传递 `preferred_spread`，只使用 `user_selected_spread`
- 后端使用 `user_selected_spread` 决定本次占卜方式，不会更新用户的偏好设置

**文件清单**：
- `frontend/app/page.tsx` - 检测URL参数中的 `selectedSpread`，当存在时不传递 `preferred_spread`
- `frontend/app/manual-input/page.tsx` - 手动输入页面不传递 `preferred_spread`，只使用URL参数中的 `spreadType`

**用户体验提升**：
- ✅ 用户可以在占卜方式选择页面临时选择占卜方式，不会影响偏好设置
- ✅ 用户的 `preferred_spread` 偏好（如"auto"根据问题自动选择）保持不变
- ✅ 临时选择和偏好设置完全分离，互不干扰

**更新时间**：2025年1月

### 2025年1月 - 模型配置和流式输出优化

**核心优化**：
- ✅ **模型选择默认值优化**：去除"默认"选项，默认选择 `gpt4omini`（GPT-4o-mini）
  - 用户个人资料页面：模型选择下拉框默认显示 `gpt4omini`
  - 新用户创建资料时：默认使用 `gpt4omini`
  - 用户可切换为 DeepSeek R1 或 Gemini 2.5 Pro
- ✅ **流式输出速率优化**：最终解读流式输出速率从 ~11字/秒提升到 20字/秒
  - 输出间隔：从 90ms 调整为 50ms
  - 每次输出：保持 5 个字
  - 计算：20字/秒 = 每50ms输出5个字
- ✅ **问题框进度显示修复**：修复最终解读生成时问题框进度显示不更新的bug
  - 在 `interpretation_started` 事件处理中更新 `currentStep` 状态
  - 确保问题框实时显示"正在生成最终解读..."进度

**文件清单**：
- `frontend/app/profile/page.tsx` - 模型选择默认值改为 gpt4omini，去除"默认"选项
- `frontend/app/page.tsx` - 流式输出速率优化（50ms间隔），问题框进度显示修复
- `backend/app/services/tarot/reading_service.py` - 默认模型处理逻辑优化（默认使用 gpt4omini）

**用户体验提升**：
- ✅ 新用户默认使用快速模型（GPT-4o-mini），无需手动选择
- ✅ 最终解读流式输出更快，阅读体验更流畅
- ✅ 问题框实时显示当前进度，用户清楚知道系统状态

**更新时间**：2025年1月

### 2025年11月 - 加载动画组件

**核心功能**：
- ✅ **TarotLoader 组件**：创建统一的塔罗主题加载动画组件
  - 使用四个 SVG 图标（圣杯、宝剑、权杖、钱币）轮转显示，主图标位于第二个位置
  - 左至右不透明度逐步降低，增强深度感与流动感
  - 淡入淡出动画效果（500ms 过渡）
  - 每 800ms 切换一次图标
  - 支持三种尺寸：sm, md, lg
- ✅ **全站加载状态统一**：在所有加载页面和等待输出时添加加载动画
  - 占卜进行中的状态显示（主页面）
  - 登录/注册时的加载状态
  - 表单提交时的加载状态
  - 认证检查时的加载状态（ProtectedRoute）
  - 邮箱确认时的加载状态
  - 个人资料保存时的加载状态
  - 占卜记录加载时的状态（侧边栏）
  - 占卜详情加载时的状态
- ✅ **占卜流程各阶段加载动画**：⭐ **新增**（已优化 - 2025年11月）
  - **抽取卡牌阶段**：在卡牌展示区域内容区域显示加载动画（不在标题中）⭐ **已优化**
    - 当 `cards_selected` 或 `pattern_analyzed` 状态时显示
    - 卡牌未显示时，在内容区域显示大型加载动画和"正在抽取卡牌..."提示
    - 卡牌部分显示时，在卡牌下方显示小型加载动画和"正在显示卡牌..."提示
  - **分析卡牌阶段**：在卡牌展示区域内容区域显示加载动画
    - 当 `rag_retrieved` 状态时显示
    - 显示"正在分析牌型..."提示
  - **生成意象阶段**：在意象描述框标题显示加载动画
    - 当 `rag_retrieved` 或 `imagery_generated` 状态且内容为空时显示
    - 标题旁显示小型加载动画
  - **生成最终解读阶段**：在解读框标题显示加载动画
    - 当 `interpretation_started` 或 `interpretation_streaming` 状态且内容为空时显示
    - 标题旁显示小型加载动画

**文件清单**：
- `frontend/components/ui/TarotLoader.tsx` - 新增加载动画组件
- `frontend/app/page.tsx` - 添加加载动画到占卜流程
- `frontend/app/login/page.tsx` - 添加加载动画到登录/注册按钮
- `frontend/app/manual-input/page.tsx` - 添加加载动画到表单提交
- `frontend/components/ProtectedRoute.tsx` - 添加加载动画到认证检查
- `frontend/app/auth/callback/page.tsx` - 添加加载动画到邮箱确认
- `frontend/app/profile/page.tsx` - 添加加载动画到保存按钮
- `frontend/components/Sidebar.tsx` - 添加加载动画到占卜记录加载
- `frontend/app/reading/[id]/page.tsx` - 添加加载动画到详情页加载

**技术实现**：
- 使用 React Hooks 管理图标轮转状态
- CSS transition 实现淡入淡出效果
- 借助 CSS 自定义属性控制四个符号的不透明度梯度
- SVG 图标内联定义，无需外部资源
- 响应式设计，适配不同尺寸需求
- 根据占卜流程的不同阶段智能显示加载动画
- 卡牌组件加载动画统一显示在内容区域，不在标题中 ⭐ **已优化 - 2025年11月**

**占卜流程加载动画位置**：⭐ **已优化 - 2025年11月**
- **问题输入框（sticky）**：占卜进行中时，在问题右侧显示小型加载动画
- **状态显示卡片**：在分析问题阶段显示大型加载动画，保持显示直到卡牌组件显示
- **卡牌展示区域**：⭐ **已优化**
  - 标题：不再显示加载动画，只显示"抽取的卡牌"文字
  - 内容：根据卡牌显示状态智能显示加载动画
    - 卡牌未显示时：显示大型加载动画和"正在抽取卡牌..."提示
    - 卡牌部分显示时：在卡牌下方显示小型加载动画和"正在显示卡牌..."提示
- **意象描述框**：
  - 标题：正在生成时，标题旁显示小型加载动画
  - 内容：内容为空时，显示中型加载动画和状态提示
- **解读框**：
  - 标题：正在生成时，标题旁显示小型加载动画
  - 内容：内容为空时，显示中型加载动画和状态提示

**更新时间**：2025年11月

### 2025年11月 - 渲染逻辑简化和流式输出优化

**核心优化**：
- ✅ **简化渲染判断逻辑**：移除不必要的中间变量和重复判断
  - 移除 `shouldShowImagery` 和 `shouldShowInterpretation` 中间变量
  - 移除所有渲染时的 `console.log` 调试输出
  - 移除不必要的 IIFE `(() => { ... })()`
  - 直接使用 `showImageryBox` 和 `showInterpretationBox` 进行条件渲染
  - 代码更简洁，性能更好
- ✅ **流式输出机制优化**：采用React最佳实践处理流式文本
  - 移除缓冲区机制和打字机效果（避免延迟和重复字符问题）
  - 直接使用 `setState(prev => prev + chunk)` 追加文本
  - React自动批量处理快速连续的更新，实现真正的流式效果
  - 意象描述和解读文本都能实时流式显示
- ✅ **意象框和解读框显示逻辑优化**：
  - 卡牌显示完成后，在定时器回调中直接触发意象框显示（1秒延迟）
  - 意象生成完成后，1秒后显示解读框
  - 移除多个重复的备用逻辑 useEffect，简化代码结构
  - 收到第一个流式数据块时，如果框未显示则立即显示（备用机制）
- ✅ **卡牌显示时间优化**：根据占卜类型动态调整显示时间
  - 三牌占卜：5秒内显示完3张牌（每张约1.67秒）
  - 十字占卜：10秒内显示完10张牌（每张1秒）
  - 根据 `spreadType` 自动计算每张卡的显示间隔

**前端改进**（`page.tsx`）：
- ✅ 简化渲染条件判断，直接使用状态变量
- ✅ 优化流式数据接收逻辑，直接追加到显示状态
- ✅ 优化卡牌显示完成检测，在定时器回调中直接处理
- ✅ 移除不必要的日志输出，提升性能
- ✅ 简化 useEffect 依赖项，减少不必要的重渲染

**代码质量提升**：
- 🧹 **代码简化**：移除约50行冗余代码
- ⚡ **性能优化**：减少不必要的渲染和计算
- 📝 **可维护性**：代码更清晰，逻辑更直观
- 🐛 **问题修复**：解决意象框和解读框不显示的问题

**文件清单**：
- `frontend/app/page.tsx` - 简化渲染逻辑，优化流式输出处理
- `frontend/components/tarot/ThreeCardSpread.tsx` - 默认聚焦中间卡牌并移除底部角色信息展示

**更新时间**：2025年11月

### 2025年11月 - 流式输出并行优化和用户体验提升 ⭐ 新增

**核心优化**：
- ✅ **RAG与流式输出并行化**：解决意象和解读延迟出现的问题
  - 核心卡牌RAG完成后（~10秒）立即发送 `rag_retrieved` 事件
  - 后台RAG任务（spread_method + card_relationships）在意象生成时并行执行
  - 意象描述和最终解读立即开始流式输出，无需等待后台RAG完成
- ✅ **意象描述流式输出**：新增 `imagery_chunk` 事件支持
  - 前端实时接收并追加意象描述文本
  - 提升用户体验，减少等待感
  - 意象和解读无缝衔接，流畅展示

**后端改进**（`reading_service.py`）：
- ✅ 新增 `_generate_spread_imagery_description_stream()` 方法，支持流式输出意象描述
- ✅ 使用 `asyncio.create_task` 将 `spread_method` 和 `card_relationships` 作为后台任务
- ✅ 优化事件发送顺序：`rag_retrieved` → `imagery_chunk` (流式) → `imagery_generated` → 最终解读流式输出
- ✅ 只在生成最终解读前才等待后台RAG任务完成

**前端改进**（`page.tsx`）：
- ✅ 新增 `imagery_chunk` 事件处理逻辑，流式追加意象描述
- ✅ 优化 `rag_retrieved` 和 `imagery_generated` 事件处理
- ✅ 确保意象和解读按序流式显示，提升用户体验

**性能提升**：
- ⏱️ RAG检索时间：保持在~10秒（符合ARCHITECTURE.md预期）
- 📖 意象描述：立即开始流式输出（~5秒）
- 💬 最终解读：立即开始流式输出
- 🚀 整体体验：用户无需等待，内容逐步流畅出现

**文件清单**：
- `backend/app/services/tarot/reading_service.py` - 实现流式意象生成和后台RAG任务并行
- `frontend/app/page.tsx` - 新增意象流式输出处理逻辑

**更新时间**：2025年11月

### 2025年1月 - 占卜界面优化和用户体验改进 ⭐ 新增

**核心功能**：
- ✅ **移除无用文本框**：移除了问题框下方的无用状态显示文本框
- ✅ **渐进式卡牌显示**：根据占卜类型在RAG检索完成一定比例后显示第一张牌 ⭐ **已优化 - 2025年1月**
  - 三牌占卜：RAG完成1/3后显示第一张牌
  - 十字占卜：RAG完成1/10后显示第一张牌
  - **实时进度跟踪**：后端发送 `rag_card_progress` 和 `rag_first_card_ready` 事件，前端实时响应
- ✅ **卡牌放大功能**：点击卡牌可以放大显示细节，支持左右滑动或键盘方向键切换其他卡牌
- ✅ **意象描述优化**：显示"正在生成意象"状态，生成后可以点击放大查看完整细节
- ✅ **放大视图关闭**：点击放大视图旁边的位置可以关闭放大，返回之前的页面
- ✅ **Markdown渲染**：占卜解读正确显示Markdown格式（标题、分割线、列表等），而不是显示原始文本
- ✅ **流式生成优化**：⭐ **已优化 - 2025年1月**
  - 移除了逐字显示逻辑，直接显示流式文本块，避免重复字符问题
  - 禁用自动滚动，让用户自己控制滚动位置
  - 流式文本直接追加到 `interpretation` 状态，实时更新

**文件清单**：
- `frontend/app/page.tsx` - 重构主页面，实现渐进式卡牌显示、流式输出、Markdown渲染等功能 ⭐ **已优化 - 2025年1月**
  - 处理 `rag_card_progress` 和 `rag_first_card_ready` 事件
  - 移除逐字显示逻辑，直接显示流式文本
  - 禁用自动滚动
- `frontend/components/tarot/CardModal.tsx` - 新增卡牌放大模态框组件，支持左右滑动和键盘导航
- `frontend/components/tarot/ThreeCardSpread.tsx` - 添加onCardClick回调，支持点击放大
- `frontend/components/tarot/CelticCrossSpread.tsx` - 添加onCardClick回调，支持点击放大
- `frontend/lib/i18n.ts` - 添加新的翻译文本（previous, next, position, generatingImageryStatus等）
- `frontend/lib/api.ts` - 处理新的进度事件类型 ⭐ **已更新 - 2025年1月**
- `frontend/package.json` - 添加react-markdown和remark-gfm依赖
- `frontend/tailwind.config.js` - 添加@tailwindcss/typography插件支持
- `backend/app/services/tarot/reading_service.py` - 新增 `_retrieve_card_information_with_progress()` 方法 ⭐ **已更新 - 2025年1月**

**技术实现**：
- **渐进式卡牌显示**：⭐ **已优化 - 2025年1月**
  - 后端使用 `asyncio.as_completed()` 发送实时进度更新
  - 前端监听 `rag_card_progress` 和 `rag_first_card_ready` 事件
  - 根据占卜类型计算阈值，达到阈值后立即显示第一张牌
  - 使用 `displayedCards` 状态管理渐进式显示的卡牌
- **卡牌放大功能**：使用CardModal组件实现全屏模态框，支持触摸滑动和键盘导航（左右方向键、ESC关闭）
- **流式输出优化**：⭐ **已优化 - 2025年1月**
  - 移除了 `interpretationQueue` 和逐字显示逻辑
  - 流式文本直接追加到 `interpretation` 状态
  - 使用 `ReactMarkdown` 组件实时渲染Markdown内容
  - 禁用自动滚动，避免干扰用户阅读
- **Markdown渲染**：使用react-markdown和remark-gfm插件，配合Tailwind Typography的prose样式实现美观的Markdown显示
- **意象描述放大**：使用模态框显示完整的意象描述，点击背景或关闭按钮可以关闭

**UI/UX特性**：
- ✅ **渐进式展示**：卡牌、意象、解读逐步显示，提升用户体验
- ✅ **交互友好**：卡牌可点击放大，支持多种导航方式（触摸滑动、键盘方向键）
- ✅ **视觉统一**：所有放大视图使用统一的暗蓝色主题和居中布局
- ✅ **响应式设计**：适配移动端和桌面端
- ✅ **Markdown美化**：使用Tailwind Typography的prose样式，自动美化Markdown内容

**RAG检索进度跟踪优化**：⭐ **新增 - 2025年1月**
- ✅ **后端实时进度更新**：
  - 新增 `_retrieve_card_information_with_progress()` 方法
  - 使用 `asyncio.as_completed()` 逐个完成卡牌检索
  - 每完成一张卡牌发送 `rag_card_progress` 事件
  - 达到阈值时发送 `rag_first_card_ready` 事件
- ✅ **前端实时响应**：
  - 监听 `rag_card_progress` 事件，跟踪检索进度
  - 监听 `rag_first_card_ready` 事件，立即显示第一张卡牌
  - 根据占卜类型动态计算阈值（三牌1/3，十字1/10）

**流式输出优化**：⭐ **新增 - 2025年1月**
- ✅ **修复重复字符问题**：
  - 移除了逐字显示逻辑（`interpretationQueue` 和 `displayedInterpretation`）
  - 流式文本直接追加到 `interpretation` 状态
  - 使用 `ReactMarkdown` 实时渲染，避免重复显示
- ✅ **禁用自动滚动**：
  - 注释掉自动滚动逻辑，让用户自己控制滚动位置
  - 避免干扰用户阅读体验

**更新时间**：2025年1月

### 2025年1月 - 用户信息优化和认证改进

**优化功能**：
- ✅ **移除外貌类型字段**：取消用户外貌类型（appearance_type）的UI输入和业务逻辑使用
- ✅ **代表牌选择优先级**：新增用户可配置的代表牌选择优先级功能
  - 默认优先级：问题领域 > 性格类型 > 星座
  - 新增选项：性格优先（性格类型 > 问题领域 > 星座）
  - 新增选项：星座优先（星座 > 问题领域 > 性格类型）
- ✅ **Token自动刷新机制**：解决页面刷新后需要重新登录的问题
  - 实现30天不活动才需要重新登录的策略
  - 添加axios响应拦截器自动刷新过期的access_token
  - 优化AuthContext的认证检查逻辑，等待token刷新完成后再判断用户状态
  - 使用ProtectedRoute组件统一处理路由保护，避免在认证检查完成前就重定向
- ✅ **数据源显示优化**：前端显示完整的数据源名称（如"PKT (The Pictorial Key to the Tarot)"）

**文件清单**：
- `frontend/lib/api.ts` - 添加token刷新拦截器和last_activity跟踪，实现自动token刷新
- `frontend/contexts/AuthContext.tsx` - 优化认证检查逻辑，支持30天不活动检查和自动token刷新
- `frontend/app/page.tsx` - 移除提前重定向逻辑，使用ProtectedRoute统一处理
- `frontend/app/profile/page.tsx` - 移除提前重定向逻辑，添加significator_priority选择器，移除appearance_type输入
- `frontend/lib/i18n.ts` - 添加significator_priority相关翻译，更新数据源显示名称
- `frontend/app/auth/callback/page.tsx` - 添加last_activity记录

**功能特点**：
- ✅ **代表牌选择优化**：用户可以在个人资料页面选择代表牌确定优先级，提供更个性化的占卜体验
- ✅ **认证体验改进**：页面刷新后自动刷新token，30天内不活动才需要重新登录，大幅提升用户体验
- ✅ **路由保护优化**：统一使用ProtectedRoute组件，避免认证检查完成前就重定向的问题
- ✅ **数据源显示优化**：显示完整的数据源名称，提升用户体验

**技术实现**：
- **Token刷新机制**：使用axios响应拦截器捕获401错误，自动调用refresh token API，成功后重试原始请求
- **30天不活动检查**：在localStorage中记录last_activity，每次API请求成功后更新，认证检查时验证是否超过30天
- **路由保护优化**：ProtectedRoute组件等待loading完成后再判断用户状态，避免在认证检查完成前就重定向

**更新时间**：2025年1月

### 2025年1月 - 初始版本
- ✅ 用户认证系统（登录/注册）
- ✅ 主页面（问题输入和结果显示）
- ✅ 占卜方式选择页面
- ✅ 自行输入牌型页面
- ✅ 用户个人页面
- ✅ 侧边栏导航
- ✅ 暗蓝色主题设计

### 2025年1月 - 多语言支持
- ✅ 国际化系统（中文/英文）
- ✅ 语言上下文管理
- ✅ 根据用户profile自动设置语言
- ✅ 文字长度处理优化
- ✅ 实时语言切换

### 2025年1月 - 占卜记录功能
- ✅ 侧边栏占卜记录列表显示
- ✅ 占卜来源页面标记（home, manual-input）
- ✅ 占卜记录自动刷新机制
- ✅ 占卜记录时间显示（相对时间）
- ✅ 点击记录跳转到占卜详情

### 2025年1月 - 邮箱确认功能 ⭐ 新增
- ✅ Supabase 邮箱确认流程实现
- ✅ 邮箱确认回调页面 (`/auth/callback`)
- ✅ URL hash 参数解析（access_token, refresh_token）
- ✅ 重新发送确认邮件功能
- ✅ 邮箱确认状态检测和提示
- ✅ 自动保存 token 并刷新用户状态
- ✅ 改进的错误处理（区分邮箱确认和真实错误）

### 2025年1月 - 流式占卜流程UI实现 ⭐ 新增

**核心功能**：
- ✅ **流式占卜API集成**：实现Server-Sent Events (SSE)流式数据接收和处理
- ✅ **实时进度显示**：支持显示占卜流程的各个阶段状态
  - 分析问题阶段
  - 抽取卡牌阶段（包含选牌、牌型分析、RAG检索）
  - 生成意象阶段
  - 生成解读阶段（流式输出）
- ✅ **卡牌展示组件**：
  - 三牌占卜组件（`ThreeCardSpread.tsx`）：水平排列，支持点击查看详情和滑动切换
  - 凯尔特十字占卜组件（`CelticCrossSpread.tsx`）：传统十字布局，中心十字+右侧权杖，支持紧凑视图和展开视图
- ✅ **意象描述展示**：可折叠的意象描述框，点击查看详情
- ✅ **流式解读输出**：实时显示解读文本，支持自动滚动和智能展开
- ✅ **UI布局优化**：所有组件和内容居中显示，提升视觉效果

**文件清单**：
- `frontend/lib/api.ts` - 添加`createReadingStream`方法，实现SSE流式数据解析
- `frontend/app/page.tsx` - 重构主页面，实现流式占卜流程UI
- `frontend/components/tarot/ThreeCardSpread.tsx` - 新增三牌占卜展示组件
- `frontend/components/tarot/CelticCrossSpread.tsx` - 新增凯尔特十字占卜展示组件
- `frontend/lib/i18n.ts` - 添加流式占卜相关的翻译文本

**技术实现**：
- **SSE解析**：使用fetch API和ReadableStream处理Server-Sent Events数据流
- **事件处理**：分别处理progress、interpretation、complete、error四种事件类型
- **状态管理**：使用React Hooks管理占卜流程的各个阶段状态
- **布局设计**：
  - 三牌占卜：水平排列，居中显示，支持滑动指示器
  - 凯尔特十字：使用CSS Grid实现3x3布局，第2张牌横跨在第1张牌上（旋转90度），右侧垂直排列4张牌
- **用户体验优化**：
  - 输入框固定在顶部（sticky定位）
  - 智能展开逻辑：用户未交互时自动展开解读框，已交互时保持当前状态
  - 自动滚动到解读文本末尾
  - 所有内容居中显示

**UI/UX特性**：
- ✅ **渐进式展示**：卡牌、意象、解读逐步显示，避免一次性加载造成的等待感
- ✅ **实时反馈**：每个步骤都有明确的状态提示
- ✅ **交互友好**：卡牌可点击查看详情，意象描述可折叠
- ✅ **视觉统一**：所有组件使用统一的暗蓝色主题和居中布局
- ✅ **响应式设计**：适配移动端和桌面端

**更新时间**：2025年1月

## 🎯 未来规划

### 功能增强
- [x] 占卜历史记录页面（已实现侧边栏记录列表）
- [ ] 占卜历史记录详情页面
- [ ] 卡牌详情页面
- [ ] 占卜结果分享功能
- [ ] 更多语言支持

### 性能优化
- [ ] 图片懒加载
- [ ] 虚拟滚动（长列表）
- [ ] Service Worker缓存
- [ ] 代码分割优化

### 用户体验
- [ ] 动画效果增强
- [ ] 加载骨架屏
- [ ] 离线支持
- [ ] PWA支持

## 📚 相关文档

- [README.md](./README.md) - 前端使用说明
- [ARCHITECTURE.md](../ARCHITECTURE.md) - 项目整体架构
- [Next.js文档](https://nextjs.org/docs)
- [React文档](https://react.dev)

