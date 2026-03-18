#!/bin/bash
set -euo pipefail

if [[ ! -f ./docker-compose.yml ]]; then
  echo "Error: docker-compose.yml not found in current directory: $(pwd)" >&2
  exit 1
fi

if [[ ! -d "./ops/docker" ]]; then
  echo "Error: required directory not found: ./ops/docker" >&2
  exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Copying SSH keys to temp folder"
mkdir -p ./ops/docker/.temp
cp -r ~/.ssh ./ops/docker/.temp
echo "Building using latest image"
docker compose build --pull
echo "Deleting temp folder content"
rm -rf ./ops/docker/.temp