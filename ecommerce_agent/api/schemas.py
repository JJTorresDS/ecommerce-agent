from pydantic import BaseModel, Field


class Question(BaseModel):
    question: str


class Answer(BaseModel):
    answer: str


class GoogleDocIngest(BaseModel):
    document_url: str = Field(
        ...,
        description=(
            "Paste the Google Doc URL from your browser. "
            "You do not need the document ID — the full link is enough. "
            "Example: https://docs.google.com/document/d/<id>/edit"
        ),
        examples=[
            "https://docs.google.com/document/d/1FlKHKxwltF_2S9ADmkfT3B0ajapSMrVKYWRUXf13mno/edit?tab=t.0#heading=h.l1ncunxa9ncf"
        ],
    )
    summary: str | None = Field(
        default=None,
        description="Optional short summary so the agent can decide when to search this document.",
    )
    chunk_chars: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Max characters per chunk. Omit to use OpenAI File Search's default "
            "(800 tokens ≈ 3200 characters, with 50% overlap). "
            "FAQ / short Q&A pages: 1200–1400, so each page stays in one chunk. "
            "Contracts, statutes, or other long-form docs: 3200 is usually fine."
        ),
        examples=[1300, 3200],
    )
