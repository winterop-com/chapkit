"""ML module for train/predict operations with artifact-based model storage."""

from .manager import MLManager
from .router import MLRouter
from .runner import BaseModelRunner, FunctionalModelRunner, ShellModelRunner
from .schemas import ModelRunnerProtocol, PredictRequest, PredictResponse, TrainRequest, TrainResponse

__all__ = [
    "BaseModelRunner",
    "FunctionalModelRunner",
    "MLManager",
    "MLRouter",
    "ModelRunnerProtocol",
    "PredictRequest",
    "PredictResponse",
    "ShellModelRunner",
    "TrainRequest",
    "TrainResponse",
]
