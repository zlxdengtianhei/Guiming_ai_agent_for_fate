-- Migration: Add interpretation_model field to user_profiles table
-- Date: 2025-01-XX
-- Description: Add interpretation_model column to allow users to select their preferred AI model for final interpretation

-- Add interpretation_model column to user_profiles table
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS interpretation_model TEXT;

-- Add comment to explain the column
COMMENT ON COLUMN user_profiles.interpretation_model IS 'User preferred AI model for final interpretation: deepseek, gpt4omini, or gemini_2.5_pro. NULL means use default model.';

-- Create index for faster queries (optional, but recommended if you'll filter by this field)
CREATE INDEX IF NOT EXISTS idx_user_profiles_interpretation_model 
ON user_profiles(interpretation_model) 
WHERE interpretation_model IS NOT NULL;



