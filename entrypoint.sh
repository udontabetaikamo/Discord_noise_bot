#!/bin/bash
set -e

# Start Discord Bot in background
echo "Starting Discord Bot..."
python bot.py &

# Start Web Interface (Streamlit or Dummy) in foreground
# Cloud Run requires listening on $PORT
if [ -f "app.py" ]; then
    echo "Starting Streamlit App..."
    streamlit run app.py --server.port $PORT --server.address 0.0.0.0
else
    echo "app.py not found. Starting dummy HTTP server on port $PORT..."
    python -m http.server $PORT
fi
