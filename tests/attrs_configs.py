import attr
from attr import validators


@attr.s
class AttrsModel:
    """Set of options."""

    test: bool = attr.ib(default=False)
    """ My testing flag """

    name: str = attr.ib(
        default="hello",
        validator=validators.and_(
            validators.instance_of(str),
            validators.max_len(5)
        ),
    )
    """Restrained name """


@attr.s
class AttrsInner:
    number: int = attr.ib(default=4)
    text: str = attr.ib(default="hello")


@attr.s
class AttrsNested:
    number: int = attr.ib(default=-100)
    inner: AttrsInner = attr.ib(default=AttrsInner())


@attr.s
class AttrsNestedRestraint:
    inner: AttrsModel = attr.ib(default=AttrsModel())
