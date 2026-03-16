# Docker Configuration

This directory contains Docker configuration files for the world-brief application.

## Files

- `dockerfile` — Development container with Python and development tools
- `build.sh` — Script to build the development container with SSH keys
- `prepare-build.sh` — Helper to copy SSH keys before building

## Quick Start

**From the project root directory:**

```bash
# Build the dev container
docker compose build dev

# Start the container
docker compose up -d dev

# Access the container shell
docker compose exec dev bash

# Stop the container
docker compose stop dev
```

Or in one command:

```bash
docker compose run --rm dev bash
```

### Using the build script (Linux/Mac)

```bash
# Option 1: build.sh (copies SSH keys automatically)
./ops/docker/build.sh

# Option 2: prepare then build
./ops/docker/prepare-build.sh
docker compose build dev
```

### Windows PowerShell

```powershell
# Copy SSH keys first
Copy-Item -Recurse $env:USERPROFILE\.ssh .\ops\docker\.temp\.ssh

# Build and run
docker compose build dev
docker compose up -d dev
docker compose exec dev bash
```

## Environment Variables

Set these in a `.env` file at the project root or export them before running:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## Development Container Features

- Python 3.12 with pip and venv
- Common development tools (git, curl, wget, AWS CLI, Terraform)
- SSH key support for private repositories
