from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import auth, projects

settings = get_settings()

app = FastAPI(
    title="Verbatim API",
    description="Speech-to-Text, Translation & Voice-Over API",
    version="1.0.0"
)

# Configure CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Verbatim API is running",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
