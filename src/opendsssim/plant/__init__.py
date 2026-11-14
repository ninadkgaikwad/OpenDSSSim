"""Plant package public surface.

A01R1 keeps ``OpenDSSPlant`` as a lazy export so importing
``opendsssim.plant.solution`` cannot recurse through ``plant.core`` back into
``opendsssim.backends.base`` while that module is still initializing.
"""

from .solution import SolutionResult

__all__ = ["OpenDSSPlant", "SolutionResult"]


def __getattr__(name: str):
    if name == "OpenDSSPlant":
        from .core import OpenDSSPlant

        return OpenDSSPlant
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
