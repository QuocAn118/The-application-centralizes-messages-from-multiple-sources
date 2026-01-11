from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, webhook, messages, users
from app.database import engine, Base
from app.middleware import ErrorHandlingMiddleware, InputValidationMiddleware
from app.logging_config import setup_logging

# setup logging
logger = setup_logging()

# create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="OmniChat API", version="1.0.0")

# Add security headers middleware
app.add_middleware(InputValidationMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
app.include_router(messages.router, prefix="/messages", tags=["Messages"])
app.include_router(users.router, prefix="/users", tags=["Users"])
from app.routers import keywords, departments, reports
app.include_router(keywords.router, prefix="/keywords", tags=["Keywords"])
app.include_router(departments.router, prefix="/departments", tags=["Departments"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
from app.routers import requests, shifts, kpi, integrations
app.include_router(requests.router, prefix="/requests", tags=["Requests"])
app.include_router(shifts.router, prefix="/shifts", tags=["Shifts"])
app.include_router(kpi.router, prefix="/kpi", tags=["KPI"])
app.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])

@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"status": "ok", "service": "OmniChat API", "version": "1.0.0"}
