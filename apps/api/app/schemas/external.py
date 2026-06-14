from pydantic import BaseModel


class SteamSearchResult(BaseModel):
    id: str
    name: str
    thumb: str | None = None


class SteamImport(BaseModel):
    id: str
