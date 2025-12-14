#!/bin/bash

# Kill existing processes
echo "Stopping existing Brain processes..."

# 1. Kill Python Backend Processes
PIDS=$(ps aux | grep -E "python.*(ingest_daemon.py|app.py)" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Killing Python PIDs: $PIDS"
    kill -9 $PIDS
else
    echo "No running Python processes found."
fi

# 2. Kill Port 5002 (Flask)
PORT_PID=$(lsof -t -i :5002)
if [ -n "$PORT_PID" ]; then
    echo "Killing process on port 5002 (PID: $PORT_PID)"
    kill -9 $PORT_PID
fi

# 3. Kill Port 5173 (Vite Frontend)
VITE_PID=$(lsof -t -i :5173)
if [ -n "$VITE_PID" ]; then
    echo "Killing process on port 5173 (PID: $VITE_PID)"
    kill -9 $VITE_PID
fi

# Wait for cleanup
sleep 2

# Start Daemon
echo "Starting Ingest Daemon..."
/Users/sheetalssr/Documents/projects/2025/personal\ projects/BrAIn/Brain2.0/venv/bin/python ingest_daemon.py > daemon.log 2>&1 &
DAEMON_PID=$!
echo "Daemon started (PID: $DAEMON_PID)"

# Start Web App (Backend)
echo "Starting Web App (Backend)..."
/Users/sheetalssr/Documents/projects/2025/personal\ projects/BrAIn/Brain2.0/venv/bin/python app.py > app.log 2>&1 &
APP_PID=$!
echo "Web App started (PID: $APP_PID)"

# Start Frontend (React)
echo "Starting Frontend (React)..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "✅ Brain is running!"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:5002"
echo "Logs: tail -f daemon.log app.log frontend.log"
