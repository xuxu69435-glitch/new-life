from pydantic import BaseModel


class IdentitySnapshot(BaseModel):
    person_id: str
    display_name: str = "Unnamed"
