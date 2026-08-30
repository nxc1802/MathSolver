"""Async Client for interacting with the external Manim Video Generation Module."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional, Union
from uuid import UUID
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from manim_client.schemas import (
    MathRenderRequest,
    MathRenderResponse,
    VisualizationSpec,
)

DEFAULT_MANIM_SERVICE_URL = os.getenv("MANIM_SERVICE_URL", "http://127.0.0.1:8001")
DEFAULT_INTERNAL_TOKEN = os.getenv(
    "MANIM_INTERNAL_TOKEN",
    "4f8a3c2e1d0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4",
)


class ManimClient:
    """
    Client connecting MathSolver to the external Manim Video Generation Agent.
    
    API Boundary:
    - POST /v1/math/generate: Submit VisualizationSpec
    - GET  /v1/math/jobs/{job_id}: Poll video rendering status and get video_url
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        internal_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or DEFAULT_MANIM_SERVICE_URL).rstrip("/")
        self.internal_token = internal_token or DEFAULT_INTERNAL_TOKEN
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Internal-Token": self.internal_token,
        }

    async def check_health(self) -> bool:
        """Checks if the Manim video generation service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def submit_render_job(
        self,
        spec: VisualizationSpec,
        callback_url: Optional[str] = None,
    ) -> MathRenderResponse:
        """
        Submits a VisualizationSpec to the Manim service to queue video generation.
        Endpoint: POST /v1/math/generate
        """
        url = f"{self.base_url}/v1/math/generate"
        payload = MathRenderRequest(spec=spec, callback_url=callback_url).model_dump(mode="json")

        logger.info(f"==[ManimClient] Submitting render job to {url}==")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                )

                if response.status_code in (200, 201, 202):
                    data = response.json()
                    logger.info(
                        f"[ManimClient] Render job queued successfully: job_id={data.get('job_id')}, status={data.get('status')}"
                    )
                    return MathRenderResponse.model_validate(data)
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"[ManimClient] Error from Manim service: {error_msg}")
                    return MathRenderResponse(
                        job_id="error",
                        status="failed",
                        error=error_msg,
                    )
        except Exception as e:
            logger.warning(f"[ManimClient] Could not connect to Manim service at {self.base_url}: {e}")
            return MathRenderResponse(
                job_id="offline",
                status="failed",
                error=f"Manim service connection failed: {str(e)}",
            )

    async def get_job_status(self, job_id: Union[UUID, str]) -> MathRenderResponse:
        """
        Polls the status of a video generation job.
        Endpoint: GET /v1/math/jobs/{job_id}
        """
        url = f"{self.base_url}/v1/math/jobs/{job_id}"
        logger.debug(f"[ManimClient] Fetching status for job {job_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._headers())
                if response.status_code == 200:
                    data = response.json()
                    return MathRenderResponse.model_validate(data)
                else:
                    return MathRenderResponse(
                        job_id=job_id,
                        status="failed",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
        except Exception as e:
            return MathRenderResponse(
                job_id=job_id,
                status="failed",
                error=f"Connection error: {str(e)}",
            )

    async def poll_job_completion(
        self,
        job_id: Union[UUID, str],
        timeout: float = 120.0,
        poll_interval: float = 3.0,
    ) -> MathRenderResponse:
        """
        Asynchronously polls until the job reaches 'completed' or 'failed' status or times out.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            resp = await self.get_job_status(job_id)
            if resp.status_code_or_done() or resp.status in ("completed", "failed"):
                return resp

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                resp.status = "rendering"
                resp.error = f"Polling timed out after {timeout}s"
                return resp

            await asyncio.sleep(poll_interval)
