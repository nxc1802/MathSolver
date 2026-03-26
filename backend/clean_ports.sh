#!/bin/bash
# Script to kill all project-related processes for a clean restart

echo "🧹 Cleaning up project processes..."

# Kill things on ports 8000 (Backend) and 3000 (Frontend)
PORTS="8000 3000 11020"
for PORT in $PORTS; do
    PIDS=$(lsof -ti :$PORT)
    if [ ! -z "$PIDS" ]; then
        echo "Killing processes on port $PORT: $PIDS"
        kill -9 $PIDS 2>/dev/null
    fi
done

# Kill by process name
echo "Killing any remaining Celery, Uvicorn, or Manim processes..."
pkill -9 -f "celery" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
pkill -9 -f "manim" 2>/dev/null

echo "✅ Done. You can now restart your Backend, Worker, and Frontend."
