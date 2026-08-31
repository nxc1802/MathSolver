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
    ErrorCode,
    MathRenderRequest,
    MathRenderResponse,
    StructuredError,
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
                    job_id = data.get("job_id")
                    if not job_id:
                        return MathRenderResponse(
                            job_id="error",
                            status="failed",
                            error=StructuredError(
                                code=ErrorCode.MANIM_REQUEST_FAILED,
                                message="Manim service did not return a valid job_id.",
                            ),
                        )
                    logger.info(
                        f"[ManimClient] Render job queued successfully: job_id={job_id}, status={data.get('status')}"
                    )
                    return MathRenderResponse.model_validate(data)
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"[ManimClient] Error response from Manim service: {error_msg}")
                    return MathRenderResponse(
                        job_id="error",
                        status="failed",
                        error=StructuredError(
                            code=ErrorCode.MANIM_REQUEST_FAILED,
                            message=f"Dịch vụ tạo video trả về mã lỗi HTTP {response.status_code}.",
                        ),
                    )
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.warning(f"[ManimClient] Connection to Manim service at {self.base_url} failed: {e}")
            return MathRenderResponse(
                job_id="offline",
                status="failed",
                error=StructuredError(
                    code=ErrorCode.MANIM_UNAVAILABLE,
                    message="Không thể kết nối đến dịch vụ tạo video Manim (máy chủ ngoại vi không khả dụng).",
                ),
            )
        except httpx.TimeoutException as e:
            logger.warning(f"[ManimClient] Request to Manim service timed out: {e}")
            return MathRenderResponse(
                job_id="timeout",
                status="failed",
                error=StructuredError(
                    code=ErrorCode.MANIM_TIMEOUT,
                    message="Yêu cầu gửi sang dịch vụ tạo video đã hết thời gian chờ (request timeout).",
                ),
            )
        except Exception as e:
            logger.exception(f"[ManimClient] Unexpected error submitting render job: {e}")
            return MathRenderResponse(
                job_id="error",
                status="failed",
                error=StructuredError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Đã xảy ra lỗi không xác định khi yêu cầu tạo video.",
                ),
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
                    resp = MathRenderResponse.model_validate(data)
                    if resp.status == "failed" and not isinstance(resp.error, StructuredError):
                        raw_err = resp.get_error_message() or "Animation rendering failed."
                        resp.error = StructuredError(
                            code=ErrorCode.MANIM_RENDER_FAILED,
                            message=raw_err,
                        )
                    return resp
                elif response.status_code == 404:
                    return MathRenderResponse(
                        job_id=job_id,
                        status="failed",
                        error=StructuredError(
                            code=ErrorCode.JOB_NOT_FOUND,
                            message=f"Không tìm thấy tiến trình render video với ID '{job_id}'.",
                        ),
                    )
                else:
                    return MathRenderResponse(
                        job_id=job_id,
                        status="failed",
                        error=StructuredError(
                            code=ErrorCode.MANIM_REQUEST_FAILED,
                            message=f"Lỗi kiểm tra tiến trình: HTTP {response.status_code}.",
                        ),
                    )
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            return MathRenderResponse(
                job_id=job_id,
                status="failed",
                error=StructuredError(
                    code=ErrorCode.MANIM_UNAVAILABLE,
                    message="Không thể kết nối đến máy chủ render video để kiểm tra trạng thái.",
                ),
            )
        except Exception as e:
            return MathRenderResponse(
                job_id=job_id,
                status="failed",
                error=StructuredError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Lỗi kiểm tra trạng thái: {str(e)}",
                ),
            )

    async def poll_job_completion(
        self,
        job_id: Union[UUID, str],
        timeout: float = 300.0,
        poll_interval: float = 3.0,
    ) -> MathRenderResponse:
        """
        Asynchronously polls until the job reaches a terminal status ('completed' or 'failed') or times out.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            resp = await self.get_job_status(job_id)
            if resp.is_terminal():
                return resp

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                logger.warning(f"[ManimClient] Polling for job {job_id} timed out after {timeout:.1f}s")
                return MathRenderResponse(
                    job_id=job_id,
                    status="failed",
                    error=StructuredError(
                        code=ErrorCode.MANIM_TIMEOUT,
                        message=f"Tiến trình dựng video đã vượt quá thời gian tối đa ({int(timeout)} giây).",
                    ),
                )

            await asyncio.sleep(poll_interval)

    async def wait_for_completion(
        self,
        job_id: Union[UUID, str],
        poll_interval: float = 3.0,
        max_wait: float = 300.0,
    ) -> MathRenderResponse:
        """Alias for poll_job_completion for API compatibility."""
        return await self.poll_job_completion(job_id=job_id, timeout=max_wait, poll_interval=poll_interval)
