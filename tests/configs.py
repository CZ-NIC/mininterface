from dataclasses import dataclass

@dataclass
class SimpleConfig:
    """Set of options."""
    test: bool = False
    """My testing flag"""
    important_number: int = 4
    """This number is very important"""


@dataclass
class FurtherConfig1:
    token: str = "filled"
    host: str = "example.org"


@dataclass
class NestedDefaultedConfig:
    further: FurtherConfig1


@dataclass
class FurtherConfig2:
    token: str
    host: str = "example.org"

@dataclass
class NestedMissingConfig:
    further: FurtherConfig2


@dataclass
class FurtherConfig3:
    severity: int | None = None

@dataclass
class OptionalFlagConfig:
    further: FurtherConfig3
    msg: str | None = None
    msg2: str | None = "Default text"