# Docker Configuration

This directory contains Docker configuration files for the Telcron application.

## Files

- `dockerfile` - Development container with Node.js, Python, and development tools
- `Dockerfile.api` - Production-ready container for the FastAPI application
- `build.sh` - Script to build the development container with SSH keys
- `.bashrc` - Bash configuration for SSH agent in the container

## Quick Start

### Build and Run Everything

**From the project root directory:**

```bash
# Build all containers
docker compose build

# Run all services in the background
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Development Container

**Build the development container:**

```bash
# Option 1: Using the build script (Linux/Mac/Git Bash)
./ops/docker/build.sh

# Option 2: Using docker compose (Windows/Linux/Mac)
# The .temp/.ssh directory structure exists - if you need SSH keys, copy them first:
# Linux/Mac/Git Bash: cp -r ~/.ssh ./ops/docker/.temp/.ssh
# Windows PowerShell: Copy-Item -Recurse $env:USERPROFILE\.ssh .\ops\docker\.temp\.ssh
docker compose build dev

# Option 3: Using prepare-build.sh helper (Linux/Mac/Git Bash)
./ops/docker/prepare-build.sh
docker compose build dev
```

**Run and access the development container:**

```bash
# Start the container in detached mode
docker compose up -d dev

# Access the container shell
docker compose exec dev bash

# Or start and access in one command
docker compose run --rm dev bash

# Stop the container
docker compose stop dev
```

### FastAPI Application

**Build and run the API:**

```bash
# Build the API container
docker compose build api

# Run the API (foreground - see logs)
docker compose up api

# Run the API in background
docker compose up -d api

# View API logs
docker compose logs -f api

# Stop the API
docker compose stop api
```

**Access the API:**
- API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Interactive API docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

### Windows PowerShell Commands

If you're on Windows using PowerShell:

```powershell
# Build all containers
docker compose build

# Run development container
docker compose up -d dev
docker compose exec dev bash

# Run API
docker compose up api

# View logs
docker compose logs -f

# Stop everything
docker compose down
```

### Environment Variables

Set these environment variables (or create a `.env` file):

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
NO_BEDROCK=false
NPM_ACCESS_TOKEN=your-token  # Optional, for npm packages
```

## Development Container Features

- Node.js 22 with npm and global tools (lerna, npm-check-updates)
- Python 3.12 with pip and venv
- Common development tools (git, curl, wget, etc.)
- SSH key support for private repositories
- Persistent volumes for code and dependencies

## Production API Container

- Python 3.12 slim base image
- FastAPI and Uvicorn server
- All required Python dependencies
- Health check endpoint
- Optimized for production use

