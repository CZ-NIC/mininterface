
from typing import Annotated, Literal


def literal(c):
    return Literal[*c]

def spread_annotated(obj, annotations):
    return Annotated[obj, *annotations]