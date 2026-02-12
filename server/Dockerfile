# Watchtower AI - Cloud Server Dockerfile
# Multi-stage build: Node.js for frontend, Python for server

# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python server
FROM python:3.12-slim
WORKDIR /app

# Install server dependencies
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy server code
COPY server/ ./server/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Railway sets PORT env var
ENV PORT=8765
ENV HOST=0.0.0.0

EXPOSE 8765

# Run the server
CMD ["python", "-m", "uvicorn", "server.server:app", "--host", "0.0.0.0", "--port", "8765"]
