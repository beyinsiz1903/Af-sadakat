#!/bin/bash

# Start MongoDB
mkdir -p /home/runner/workspace/data/db
mongod --dbpath /home/runner/workspace/data/db --logpath /tmp/mongod.log --fork --quiet 2>/dev/null || true

# Start backend on port 8000 (background)
cd /home/runner/workspace/backend
uvicorn server:app --host localhost --port 8000 &
BACKEND_PID=$!

# Start frontend on port 5000
cd /home/runner/workspace/frontend
PORT=5000 REACT_APP_BACKEND_URL=http://localhost:8000 yarn start

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null
