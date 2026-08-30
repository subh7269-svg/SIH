# TraceX Offline & Docker Deployment

---

## 1. Local Zero-Setup Mode

TraceX can run directly on any machine with Python 3.10+ and Node.js 18+:

```bash
# 1. Install Backend Dependencies
pip install -r backend/requirements.txt

# 2. Start Backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Start Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

---

## 2. Docker Container Deployment

```bash
# Build and run containers
docker compose up --build -d

# View logs
docker compose logs -f

# Stop containers
docker compose down
```

The application will be available at `http://localhost:8000`.
