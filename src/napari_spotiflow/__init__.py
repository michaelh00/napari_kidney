import os
os.environ["QT_OPENGL"] = "angle"

from ._widget import SpotiflowWidget

__all__ = ["SpotiflowWidget"]
