from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401
from config import settings
from data.seed import seed_if_empty
from db import init_db
from routes.approvals import router as approvals_router
from routes.audit import router as audit_router
from routes.auth import router as auth_router
from routes.candidates import router as candidates_router
from routes.dashboard import router as dashboard_router
from routes.digest import router as digest_router
from routes.employee import router as employee_router
from routes.inbox import router as inbox_router
from routes.workflows import router as workflows_router

app = FastAPI(title='EASEIT', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, 'http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def startup_event() -> None:
    init_db()
    seed_if_empty()


app.include_router(auth_router, prefix='/api/auth')
app.include_router(dashboard_router, prefix='/api')
app.include_router(inbox_router, prefix='/api')
app.include_router(candidates_router, prefix='/api')
app.include_router(approvals_router, prefix='/api')
app.include_router(digest_router, prefix='/api')
app.include_router(audit_router, prefix='/api')
app.include_router(employee_router, prefix='/api')
app.include_router(workflows_router, prefix='/api')


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
