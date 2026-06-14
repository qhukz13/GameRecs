# Game Recommendations Deployment Guide

## Overview
This guide provides instructions for building and deploying the **Game Recommendations** project to **Netlify**. The project consists of a **frontend** (Next.js) and a **backend** (FastAPI), which are containerized using Docker.

## Prerequisites
Before you begin, ensure you have the following:

- **Docker** installed on your system: [Install Docker](https://docs.docker.com/get-docker/)
- **Git** installed on your system: [Install Git](https://git-scm.com/downloads)
- **Netlify Account** (free tier available): [Sign up for Netlify](https://www.netlify.com/signup)

## Project Setup

### Clone the Repository
1. Clone the repository to your local machine:
   ```bash
   git clone https://github.com/your-repo/game-recommendations.git
   cd game-recommendations
   ```

2. Set up the environment variables:
   - Create a `.env` file in the root directory with the following configuration:
     ```env
     # Backend Environment Variables
     BACKEND_API_URL=https://your-api-url.onrender.com
     DATABASE_URL=postgresql://user:password@host:port/dbname
     SECRET_KEY=your-secret-key
     
     # Frontend Environment Variables
     NEXT_PUBLIC_API_URL=https://your-api-url.onrender.com
     
     # Netlify-Specific Variables
     NETLIFY_SITE_ID=your-site-id
     NETLIFY_AUTH_TOKEN=your-auth-token
     ```
     Replace placeholders with actual values.

### Build the Backend
1. Navigate to the backend directory:
   ```bash
   cd apps/api
   ```

2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Build the Docker image for the backend:
   ```bash
   docker-compose build --no-cache
   ```

### Build the Frontend
1. Navigate to the frontend directory:
   ```bash
   cd apps/web
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Build the frontend:
   ```bash
   npm run build
   ```

## Deployment to Netlify

### Deploy the Frontend to Netlify
1. Navigate to the Netlify dashboard: [https://app.netlify.com/dashboards](https://app.netlify.com/dashboards)

2. Click **New Site** and select **Import from Git**:
   - Choose your repository or upload your project files.
   - Connect your GitHub account if prompted.

3. Configure the Netlify build settings:
   - Under **Build & Development Settings**, set the following:
     - **Build command:** `npm run build`
     - **Install command:** `npm install`
     - Ensure the **Directory** field is set to `apps/web` if needed.
     - Add the following environment variables:
       - `NEXT_PUBLIC_API_URL`: Set to your deployed backend URL (e.g., `https://your-api-url.onrender.com`).

4. Click **Save** and deploy the site.

### Deploy the Backend to Render (Alternative for Netlify Backend)
Since Netlify primarily supports frontend deployments, you may need to use a separate service like **Render** or **Render Cloud** for the backend.

#### Deploy Backend Using Render
1. Sign up for a Render account: [https://render.com](https://render.com)

2. Create a new **Web Service**:
   - Select your repository from GitHub.
   - Configure the build settings:
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn apps/api/app/main:app --host 0.0.0.0 --port 8000`
   - Add the following environment variables:
     - `DATABASE_URL`: Your PostgreSQL connection string.
     - `SECRET_KEY`: Your application secret key.
     - `BACKEND_API_URL`: The URL where the frontend will host itself (e.g., `https://your-frontend-url.netlify.app`).

3. Click **Create Service** and wait for the deployment to complete.

### Configure CORS
Ensure your backend has CORS properly configured to allow requests from your Netlify frontend URL:

In your backend's FastAPI application (e.g., `apps/api/app/main.py`), add the following middleware:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-url.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing the Deployment

### Test the Frontend
- Open your browser and navigate to your deployed Netlify frontend URL.
- Ensure all frontend features work as expected.

### Test the Backend API
- Use tools like **Postman**, **cURL**, or your frontend's API client to verify that the backend endpoints are accessible and respond correctly.

## Troubleshooting

### Common Issues
- **CORS Errors**: Ensure the frontend URL is correctly listed in the backend's CORS settings.
- **Build Failures**: Check the logs in Netlify for any build errors and resolve them.
- **Connection Issues**: Verify that your backend URL is correctly set in the frontend environment variables.

### Debugging
- **Backend Logs**: Check the logs in the Render or Render Cloud dashboard for backend errors.
- **Frontend Logs**: Use the browser's developer tools to inspect frontend errors.

## Automating Deployments

### GitHub Actions for CI/CD
You can automate deployments using GitHub Actions. Create a `.github/workflows/deploy.yml` file in your repository:

```yaml
name: Deploy to Netlify and Render
on:
  push:
    branches: [ main ]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm install
      - run: npm run build
      - uses: nwls actions/netlify-deploy-action@v1
        with:
          DISABLE_CACHE: true
          DISABLE_BUILD: true
          PRODUCTION_BRANCH: main
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r apps/api/requirements.txt
      - run: docker-compose build
      - uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.RENDER_HOSTNAME }}
          port: ${{ secrets.RENDER_PORT }}
          username: ${{ secrets.RENDER_USERNAME }}
          key: ${{ secrets.RENDER_SSH_KEY }}
          script: docker-compose up -d
```

Add your GitHub secrets (`NETLIFY_SITE_ID`, `NETLIFY_AUTH_TOKEN`, `RENDER_HOSTNAME`, `RENDER_USERNAME`, and `RENDER_SSH_KEY`) to your repository settings.

---