#!/bin/bash

# Railway 环境变量设置脚本
# 使用方法：修改下面的值，然后运行此脚本

# Supabase 配置
SUPABASE_URL="https://nlolchueqdqzlhjrzjvi.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="你的_supabase_service_role_key_在这里"

# OpenRouter 配置（如果使用 OpenRouter）
USE_OPENROUTER="true"
OPENROUTER_API_KEY="你的_openrouter_api_key_在这里"

# 或者使用 OpenAI（如果不用 OpenRouter）
# USE_OPENROUTER="false"
# OPENAI_API_KEY="你的_openai_api_key_在这里"

# CORS 配置
CORS_ORIGINS="http://localhost:3000,https://your-frontend-domain.com"

# 设置环境变量
railway variables --service ae39b7d2-ce9a-418e-a366-5859dbcdb769 \
  --set "SUPABASE_URL=$SUPABASE_URL" \
  --set "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY" \
  --set "USE_OPENROUTER=$USE_OPENROUTER" \
  --set "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" \
  --set "CORS_ORIGINS=$CORS_ORIGINS"

echo "✅ 环境变量已设置！Railway 将自动重新部署。"

