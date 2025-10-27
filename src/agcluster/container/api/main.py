"""Main FastAPI application"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from agcluster.container.core.config import settings
from agcluster.container.core.session_manager import session_manager
from agcluster.container.api import agent_chat, agents, configs, tools, files

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
    version="0.2.0",
    lifespan=lifespan
)

# CORS middleware - configured with specific allowed origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Whitelist specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Specific methods only
    allow_headers=["Content-Type", "Authorization", "X-Session-ID", "X-Conversation-ID"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgCluster Container Runtime",
        "version": "0.2.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_image": settings.agent_image
    }


# Include routers
# Claude-native chat endpoint (replaces OpenAI /chat/completions)
app.include_router(agent_chat.router, prefix="/api/agents", tags=["agents"])

# Agent management endpoints
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(configs.router, prefix="/api/configs", tags=["configs"])

# Tool and file endpoints
app.include_router(tools.router, tags=["tools"])
app.include_router(files.router, tags=["files"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agcluster.container.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )
