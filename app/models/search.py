from pydantic import BaseModel, HttpUrl


class SearchResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str | None = None
