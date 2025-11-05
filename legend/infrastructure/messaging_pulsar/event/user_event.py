from pydantic import BaseModel


class UserRegisteredEvent(BaseModel):
    user_id: str
    email: str
    registered_at: str
