from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from manager_ai.agent.agent import Agent

router = APIRouter()


class IncomingMessage(BaseModel):
    phone: str
    text: str


def create_router(agent: Agent) -> APIRouter:
    @router.post("/webhook")
    def webhook(message: IncomingMessage) -> dict[str, str]:
        try:
            agent.handle_message(phone=message.phone, text=message.text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"status": "ok"}

    return router
