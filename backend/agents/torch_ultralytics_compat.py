"""PyTorch 2.6+ defaults weights_only=True; Ultralytics YOLO .pt checkpoints unpickle full nn graphs (trusted official weights)."""

from __future__ import annotations

import functools

_torch_load_patched = False


def allow_ultralytics_weights() -> None:
    """
    Official yolov8n.pt is a trusted checkpoint. PyTorch 2.6+ safe unpickling would require
    allowlisting many torch.nn globals; loading with weights_only=False matches Ultralytics
    upstream behavior for local .pt files.
    """
    global _torch_load_patched
    if _torch_load_patched:
        return
    try:
        import torch

        _orig = torch.load

        @functools.wraps(_orig)
        def _load(*args, **kwargs):
            if "weights_only" not in kwargs:
                kwargs["weights_only"] = False
            return _orig(*args, **kwargs)

        torch.load = _load
        _torch_load_patched = True
    except Exception:
        pass
