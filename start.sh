#!/bin/bash

# FlatSeller AI - Startup Script
echo "🏡 Starting FlatSeller AI Application..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Install requirements if not already installed
echo "📦 Installing/updating requirements..."
pip install -r requirements.txt

# Function to start FastAPI backend
start_backend() {
    echo "🚀 Starting FastAPI backend server..."
    python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
    
    # Wait for backend to start
    echo "⏳ Waiting for backend to start..."
    sleep 5
    
    # Check if backend is running
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ Backend is running successfully!"
    else
        echo "❌ Backend failed to start!"
        exit 1
    fi
}

# Function to start Streamlit frontend
start_frontend() {
    echo "🎨 Starting Streamlit frontend..."
    streamlit run main.py --server.port 8501 --server.address 0.0.0.0 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
}

# Function to cleanup on exit
cleanup() {
    echo "🧹 Shutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "Backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "Frontend stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
start_backend
start_frontend

echo ""
echo "🎉 FlatSeller AI is now running!"
echo "📱 Streamlit Frontend: http://localhost:8501"
echo "🔧 FastAPI Backend: http://localhost:8000"
echo "📊 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for processes
wait