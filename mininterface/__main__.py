from dataclasses import dataclass

from mininterface import TextualInterface

from . import run

__doc__ = """Simple GUI dialog. Outputs the value the user entered."""


@dataclass
class CliInteface:
    alert: str = ""
    """ Display the OK dialog with text. """
    ask: str = ""
    """ Prompt the user to input a text.  """
    ask_number: str = ""
    """ Prompt the user to input a number. Empty input = 0. """
    is_yes: str = ""
    """ Display confirm box, focusing 'yes'. """
    is_no: str = ""
    """ Display confirm box, focusing 'no'. """


def main():
    result = []
    # We tested both GuiInterface and TextualInterface are able to pass a variable to i.e. a bash script.
    # TextInterface fails (`mininterface --ask Test | grep Hello` – pipe causes no visible output).
    with run(CliInteface, prog="Mininterface", description=__doc__, interface=TextualInterface) as m:
        for method, label in vars(m.env).items():
            if label:
                result.append(getattr(m, method)(label))
    # Displays each result on a new line. Currently, this is an undocumented feature.
    # As we use the script for a single value only and it is not currently possible
    # to ask two numbers or determine a dialog order etc.
    [print(val) for val in result]


if __name__ == "__main__":
    main()
