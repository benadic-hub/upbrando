from __future__ import annotations

from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.agents.router import router as agents_router
from app.modules.announcements.router import router as announcements_router
from app.modules.attachments.router import router as attachments_router
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.forms.router import router as forms_router
from app.modules.helpdesk.router import router as helpdesk_router
from app.modules.kb.router import router as kb_router
from app.modules.org.router import router as org_router
from app.modules.tasks.router import router as tasks_router
from app.modules.timeclock.router import router as timeclock_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(org_router)
api_router.include_router(agents_router)
api_router.include_router(timeclock_router)
api_router.include_router(tasks_router)
api_router.include_router(helpdesk_router)
api_router.include_router(chat_router)
api_router.include_router(announcements_router)
api_router.include_router(kb_router)
api_router.include_router(forms_router)
api_router.include_router(attachments_router)
