"""
FastAPI application for PAZ structural analysis.

Provides REST API for:
- Project management
- Model operations (nodes, frames)
- Structural analysis
- Materials and sections library
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paz.api.routers import analysis, library, model, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("PAZ API starting...")
    yield
    # Shutdown
    print("PAZ API shutting down...")


app = FastAPI(
    title="PAZ - Structural Analysis API",
    description="Professional structural analysis software API",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(model.router, prefix="/api/model", tags=["Model"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(library.router, prefix="/api/library", tags=["Library"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "PAZ - Structural Analysis API",
        "version": "1.0.0-mvp",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
