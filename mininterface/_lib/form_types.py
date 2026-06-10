from typing import TypeVar

DataClass = TypeVar("DataClass")
""" Any dataclass. Or a pydantic model or attrs. """

EnvClass = TypeVar("EnvClass", bound=DataClass)
""" Any dataclass. Its instance will be available through [Mininterface.env][mininterface.Mininterface.env] after CLI parsing. """
