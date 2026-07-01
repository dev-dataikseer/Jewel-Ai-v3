from app.models import ModelDefinition
from app.providers.adapters.fal import FalAdapter
from app.providers.types import GenerationRequest, GenerationResult


class FalImageProvider:
    """Infrastructure facade for fal.ai model execution."""

    def __init__(self, api_key: str, model_name: str | None = None) -> None:
        self._adapter = FalAdapter(api_key=api_key, model_name=model_name)

    async def generate(
        self,
        request: GenerationRequest,
        model_def: ModelDefinition | None = None,
        db=None,
    ) -> GenerationResult:
        return await self._adapter.generate(request=request, model_def=model_def, db=db)
