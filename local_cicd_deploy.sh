#!/bin/bash
# local_cicd_deploy.sh
# This script simulates a local CI/CD pipeline. It builds the docker images,
# runs the backend tests, and if they pass, it deploys the application locally using
# the production docker-compose configuration.

set -e # Exit immediately if a command exits with a non-zero status

echo "🚀 Starting Local CI/CD Pipeline..."

# 1. Start database and cache services required for testing and building
echo "📦 Starting base services (db, redis, qdrant)..."
docker-compose -f docker-compose.prod.yml up -d db redis qdrant

# 2. Build the production images
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yml build

# 3. Run Backend Tests inside a temporary container
echo "🧪 Running backend tests..."
docker-compose -f docker-compose.prod.yml run --rm \
  -v "$(pwd)/config:/config:ro" \
  backend python manage.py test

# 4. If tests pass, deploy the application
echo "✅ Tests passed! Deploying application locally..."
docker-compose -f docker-compose.prod.yml up -d

echo "🎉 Local Deployment Successful!"
echo "🌐 You can access the application at: http://localhost (via Nginx proxy)"

