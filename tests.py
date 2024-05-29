from dataclasses import dataclass
from mininterface import run

@dataclass
class Config:
    """Set of options."""
    test: bool = False
    """My testing flag"""
    important_number: int = 4
    """This number is very important"""

if __name__ == "__main__":
    args: Config = run(Config, prog="My application").get_args()
    print(args.important_number)    # suggested by the IDE with the hint text "This number is very important"