-- Initialize multiple databases for the trading platform
-- This script runs when PostgreSQL first starts

-- Create backend database and user
CREATE DATABASE backend;
CREATE USER backend_user WITH PASSWORD 'backend_secure_password';
GRANT ALL PRIVILEGES ON DATABASE backend TO backend_user;

-- Create mlflow database (already created by POSTGRES_DB env var)
-- But ensure the user has proper permissions
GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;