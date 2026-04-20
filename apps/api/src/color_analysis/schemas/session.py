from pydantic import BaseModel


class SessionCreateResponse(BaseModel):
    id: str
    status: str
