"""Metrics router for Prometheus endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Response

from ..router import Router

if TYPE_CHECKING:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader


class MetricsRouter(Router):
    """Metrics router for Prometheus metrics exposition."""

    def __init__(
        self,
        prefix: str,
        tags: list[str],
        metric_reader: PrometheusMetricReader,
        **kwargs: object,
    ) -> None:
        """Initialize metrics router with Prometheus metric reader."""
        self.metric_reader = metric_reader
        super().__init__(prefix=prefix, tags=tags, **kwargs)

    def _register_routes(self) -> None:
        """Register Prometheus metrics endpoint."""

        @self.router.get(
            "",
            summary="Prometheus metrics",
            response_class=Response,
        )
        async def get_metrics() -> Response:
            """Expose metrics in Prometheus text format."""
            # Get latest metrics from the reader
            from prometheus_client import REGISTRY, generate_latest

            metrics_output = generate_latest(REGISTRY)

            return Response(
                content=metrics_output,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
