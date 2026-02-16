"""Middleware CORS para el API Gateway."""

from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app):
    """
    Configura CORS para el API Gateway.

    Args:
        app: Instancia de FastAPI
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React/Next.js dev
            "http://localhost:5173",  # Vite dev
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,  # Necesario para cookies httpOnly
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
