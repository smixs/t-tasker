-- Migration: Add auto_delete_previous column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_delete_previous BOOLEAN DEFAULT FALSE;