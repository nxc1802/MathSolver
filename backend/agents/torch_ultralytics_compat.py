"""PyTorch 2.6+ defaults weights_only=True; Ultralytics checkpoints need DetectionModel unpickling."""

from __future__ import annotations


def allow_ultralytics_weights() -> None:
    try:
        import torch
        from ultralytics.nn.tasks import DetectionModel

        add = getattr(torch.serialization, "add_safe_globals", None)
        if callable(add):
            add([DetectionModel])
    except Exception:
        pass
