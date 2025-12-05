# Finance API

Backend API for the Personal Finance Tracker, built with FastAPI and SQLAlchemy.

## Features
*   **Multi-Tenancy**: User-scoped data access.
*   **Net Worth Tracking**: Real-time calculation and historical snapshots.
*   **Holdings Management**: Track investments across multiple platforms.
*   **Goals**: Set and track financial goals.
*   **Cashflow**: Track income, expenses, and monthly commitments.
*   **Analytics**: Historical data capture and timeseries graphs.

## Tech Stack
*   **Framework**: FastAPI
*   **Database**: PostgreSQL (Neon)
*   **ORM**: SQLAlchemy
*   **Deployment**: Render

## Local Development

1.  **Clone the repo**
    ```bash
    git clone <repo-url>
    cd finance-api
    ```

2.  **Install dependencies**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Environment Variables**
    Create a `.env` file:
    ```
    DATABASE_URL=postgresql://user:password@host/dbname
    SECRET_KEY=your-secret-key
    ```

4.  **Run the server**
    ```bash
    uvicorn app.main:app --reload
    ```
    Access docs at `http://localhost:8000/docs`.

## Deployment (Render)

1.  Create a new **Web Service** on Render.
2.  Connect this repository.
3.  Set the **Build Command**: `pip install -r requirements.txt`
4.  Set the **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5.  Add the `DATABASE_URL` environment variable.
