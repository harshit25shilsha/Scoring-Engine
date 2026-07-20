from pydantic import BaseModel

class SyncResult(BaseModel):
    entity: str
    mode: str
    synced_count: int
    status: str = "success"
    