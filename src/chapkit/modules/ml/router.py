"""REST API router for ML train/predict operations."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, status

from chapkit.core.api.router import Router

from .manager import MLManager
from .schemas import PredictRequest, PredictResponse, TrainRequest, TrainResponse


class MLRouter(Router):
    """Router with $train and $predict collection operations."""

    def __init__(
        self,
        prefix: str,
        tags: list[str],
        manager_factory: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize ML router with manager factory."""
        self.manager_factory = manager_factory
        super().__init__(prefix=prefix, tags=tags, **kwargs)

    def _register_routes(self) -> None:
        """Register ML train and predict routes."""
        from fastapi import HTTPException

        manager_factory = self.manager_factory

        @self.router.post(
            "/$train",
            response_model=TrainResponse,
            status_code=status.HTTP_202_ACCEPTED,
            summary="Train model",
            description="Submit a training job to the scheduler",
        )
        async def train(
            request: TrainRequest,
            manager: MLManager = Depends(manager_factory),
        ) -> TrainResponse:
            """Train a model asynchronously and return job/artifact IDs."""
            try:
                return await manager.execute_train(request)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(e),
                )

        @self.router.post(
            "/$predict",
            response_model=PredictResponse,
            status_code=status.HTTP_202_ACCEPTED,
            summary="Make predictions",
            description="Submit a prediction job to the scheduler",
        )
        async def predict(
            request: PredictRequest,
            manager: MLManager = Depends(manager_factory),
        ) -> PredictResponse:
            """Make predictions asynchronously and return job/artifact IDs."""
            try:
                return await manager.execute_predict(request)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(e),
                )
