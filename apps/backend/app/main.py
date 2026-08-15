from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.backend.app.api import api_router
from apps.backend.app.config import settings

app = FastAPI(
    title="Restaurant Waiter Agent API",
    description="Backend services for Restaurant AI Waiter & Management Dashboard",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix="/api")
# Also mount /health directly at root for load balancers
app.include_router(api_router)
