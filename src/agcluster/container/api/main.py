"""Main FastAPI application"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from agcluster.container.core.config import settings
from agcluster.container.core.session_manager import session_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting AgCluster Container Runtime")
    logger.info(f"Agent image: {settings.agent_image}")
    logger.info(f"Container limits: CPU={settings.container_cpu_quota}, Memory={settings.container_memory_limit}")

    # Start session cleanup background task
    await session_manager.start_cleanup_task(interval_minutes=5)
    logger.info("Session cleanup task started (30 min idle timeout)")

    yield

    # Shutdown
    logger.info("Shutting down AgCluster Container Runtime")

    # Stop cleanup task and cleanup all active sessions
    await session_manager.stop_cleanup_task()
    await session_manager.cleanup_all_sessions()
    logger.info("All sessions cleaned up")


# Create FastAPI app
app = FastAPI(
    title="AgCluster Container Runtime",
    description="Container runtime for Claude Agent SDK instances with OpenAI-compatible API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgCluster Container Runtime",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_image": settings.agent_image
    }


# Import and include routers
from agcluster.container.api import chat_completions, agents

app.include_router(chat_completions.router)
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agcluster.container.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )
