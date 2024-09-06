from pydantic import BaseModel, Field


class MyModel(BaseModel):
    """Set of options."""

    test: bool = False
    """My testing flag"""
    name: str = Field(default="hello", max_length=5)
    """ Restrained name """


class Inner(BaseModel):
    number: int = 4
    text: str = "hello"


class MyModelNested(BaseModel):
    number: int = -100
    inner: Inner = Inner()

class MyModelNestedRestraint(BaseModel):
    inner: MyModel = MyModel()