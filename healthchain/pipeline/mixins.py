import logging


from healthchain.pipeline.base import ModelConfig
from healthchain.pipeline.modelrouter import ModelRouter

logger = logging.getLogger(__name__)


class ModelRoutingMixin:
    """Mixin that adds model routing capabilities to a pipeline."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_router = ModelRouter()

    @property
    def model_router(self) -> ModelRouter:
        return self._model_router

    def get_model_component(self, config: ModelConfig):
        return self.model_router.get_component(config)
