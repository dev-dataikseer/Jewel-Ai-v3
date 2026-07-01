from sqlalchemy.orm import Session

from app.pipeline.composer import ComposeInput, ComposedPrompt, compose_prompt


class JewelryPromptComposer:
    """Use-case facade over the DB-backed Jewel Prompt Engine."""

    def __init__(self, db: Session):
        self._db = db

    def compose(self, payload: ComposeInput) -> ComposedPrompt:
        return compose_prompt(self._db, payload)
