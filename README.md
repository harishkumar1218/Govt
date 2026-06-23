# Government Exam Preparation Platform - AI Interviewer

This repository contains a full-stack platform for UPSC/Govt exam preparation with roadmaps, RAG-grounded mock test generation, essay evaluation, and a voice-enabled, learning-path-specific **AI Interview Room**.

---

## 🎙️ AI Interview Room Features
- **Local/Open-Source AI**: Grounded in the Qdrant database of exam syllabi and previous years' questions (PYQ). Powered by a local Ollama model (`llama3.2`).
- **Web Speech API integration**: Native speech synthesis (TTS) and speech recognition (STT) for hands-free mock interviews.
- **Interruption Support**: Candidate speech instantly pauses/cancels ongoing AI voice playbacks.
- **Graceful Fallback**: Text chat interface automatically displays if microphone permissions or Speech Recognition APIs are unavailable.
- **Personalized Recommendations**: Summarizes strengths and weaknesses, mapping focus areas to recommended roadmap node topics to study next.

---

## 🛠️ Local Installation & Setup

### 1. Run Ollama Locally (Host)
The Django container connects to your host's Ollama service.
1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Start the Ollama application on your computer.
3. Pull the required model in your terminal:
   ```bash
   ollama pull llama3.2
   ```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the `backend/` directory or set environment variables. The default parameters point to the host gateway in Docker:
- `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `OLLAMA_MODEL=llama3.2`

### 3. Build & Run with Docker Compose
From the root directory, start all services (database, Redis, Qdrant, Prometheus, Grafana, Django Backend, and React Frontend):
```bash
docker-compose up --build -d
```

Once running:
- **Frontend App**: [http://localhost:5001](http://localhost:5001)
- **Backend Admin**: [http://localhost:8000/admin/](http://localhost:8000/admin/)

### 4. Run Migrations & Seed Qdrant
If running for the first time, make sure database tables are updated:
```bash
# Run Django Migrations
docker-compose exec backend python manage.py migrate

# Seed Qdrant Vector Index (if needed)
docker-compose exec backend python seed_qdrant.py
```

---

## 🧪 Testing & Verification

### Running Backend Tests
Execute the unit tests inside the backend container to verify the start, evaluation, and recommendation views:
```bash
docker-compose exec backend python manage.py test interviewer
```

### Manual Verification
1. Navigate to the UPSC/Govt Exam track details page.
2. Select the **Roadmap** tab.
3. Locate an active roadmap node (completed or in progress) and click the **🎙️ AI Interview** button.
4. Dictate (or type) your answers to the AI's questions.
5. Click **Finish Interview** to receive your overall score card, rubric breakdown, and study suggestions.

---

## 🚀 Local CI/CD Deployment

If you want to run a complete local CI/CD pipeline that tests, builds, and deploys the production version of the platform locally (using Nginx and Gunicorn), you can use the provided script.

Run the local deployment pipeline from your terminal:
```bash
./local_cicd_deploy.sh
```

**What this script does:**
1. Starts the base services (PostgreSQL, Redis, Qdrant).
2. Builds production-optimized Docker images for the Frontend (Vite -> Nginx) and Backend (Gunicorn).
3. Runs the Django test suite automatically inside the new container.
4. If tests pass, deploys the entire application stack locally using `docker-compose.prod.yml`.
5. Applies database migrations.

Once deployed, the production-simulated app is accessible via the overarching Nginx proxy at:
- **Frontend**: [http://localhost](http://localhost)
- **Backend APIs**: [http://localhost/api/](http://localhost/api/)
- **Backend Admin**: [http://localhost/admin/](http://localhost/admin/)
