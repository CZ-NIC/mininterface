from pydantic import BaseModel, Field


class PydModel(BaseModel):
    """Set of options."""

    test: bool = False
    """My testing flag"""
    name: str = Field(default="hello", max_length=5)
    """ Restrained name """


class PydInner(BaseModel):
    number: int = 4
    text: str = "hello"


class PydNested(BaseModel):
    number: int = -100
    inner: PydInner = PydInner()


class PydNestedRestraint(BaseModel):
    inner: PydModel = PydModel()
