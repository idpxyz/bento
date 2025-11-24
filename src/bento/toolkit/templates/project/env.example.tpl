# {{project_name}} Environment Configuration

# Application
APP_NAME={{project_name}}
APP_ENV=development
DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./{{project_slug}}.db
# For PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:password@localhost/{{project_slug}}

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Logging
LOG_LEVEL=INFO
