"""Shim: geometry rendering lives in ``geometry_render`` (worker-safe package)."""

from geometry_render.renderer import RendererAgent

__all__ = ["RendererAgent"]
