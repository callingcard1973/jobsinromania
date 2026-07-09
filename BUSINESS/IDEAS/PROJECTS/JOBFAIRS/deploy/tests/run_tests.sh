#!/bin/bash
# NanoClaw Test Runner
cd /opt/ACTIVE/INFRA/GOVERNOR

case "${1:-unit}" in
    unit)
        echo "Running unit tests only..."
        python3 -m pytest tests/ -m "not slow and not integration" -v --tb=short
        ;;
    all)
        echo "Running all tests (including Ollama integration)..."
        python3 -m pytest tests/ -v --tb=short
        ;;
    slow)
        echo "Running Ollama integration tests..."
        python3 -m pytest tests/ -m slow -v --tb=short
        ;;
    *)
        echo "Usage: $0 {unit|all|slow}"
        exit 1
        ;;
esac
