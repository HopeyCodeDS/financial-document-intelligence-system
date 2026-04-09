"""
Abstract pipeline step.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.pipeline.context import PipelineContext


class AbstractPipelineStep(ABC):
    """
    Each step receives the PipelineContext, performs its work,
    writes its result to the context, and returns the updated context.

    critical=True  — a failure halts the entire pipeline immediately.
    critical=False — a failure is recorded but subsequent steps still run.
    """

    critical: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Step identifier for logging and audit."""

    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute this pipeline step.

        Must not raise unless critical=True.
        Non-critical exceptions should be caught, logged, and added to context.errors.
        """
