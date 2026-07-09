#!/bin/bash
# Deploy script for Raspberry Pi or VPS

set -e

echo "🚀 Deploying Trasabilitate..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo "✗ Docker not found. Please install Docker first."
  exit 1
fi

# Build and start containers
echo "Building Docker images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Initialize database
echo "Initializing database..."
docker-compose exec -T backend python backend/init_db.py

# Seed demo data
echo "Seeding demo data..."
docker-compose exec -T backend python scripts/seed_demo.py

echo ""
echo "✓ Deployment complete!"
echo ""
echo "Services running:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:5000"
echo "  - Database: localhost:5432"
echo ""
echo "Test the API:"
echo "  curl http://localhost:5000/health"
echo ""
echo "View logs:"
echo "  docker-compose logs -f backend"
