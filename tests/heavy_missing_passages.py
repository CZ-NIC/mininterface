from heavy_nesting_missing_configs import Grade5A, Level2A, Level3A, Level5A
from mininterface import Tag
from mininterface.tag import SelectTag
from shared import MISSING


mpassage1 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level2 a", "Level2 b"])},
        {"": Level2A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level3 a", "Level3 b"])},
        {"": Level3A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level5 a", "Level5 b"])},
        {"": Level5A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Grade5A},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {"epsilonA": Tag(val=MISSING, description="", annotation=str, label="epsilonA")}
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(val=MISSING, description="", annotation=str, label="epsilonGradeA")
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {
            "command1": {
                "command2": {
                    "command3": {"command4": {"epsilonA": ""}},
                    "command3grade": {"command4": {"epsilonGradeA": ""}},
                }
            }
        },
    ),
)

mpassage2 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level3 a", "Level3 b"])},
        {"": Level3A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level5 a", "Level5 b"])},
        {"": Level5A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Grade5A},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {"epsilonA": Tag(val=MISSING, description="", annotation=str, label="epsilonA")}
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(val=MISSING, description="", annotation=str, label="epsilonGradeA")
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {
            "command1": {
                "command2": {
                    "command3": {"command4": {"epsilonA": ""}},
                    "command3grade": {"command4": {"epsilonGradeA": ""}},
                }
            }
        },
    ),
)

mpassage3 = (
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {"epsilonA": Tag(val=MISSING, description="", annotation=str, label="epsilonA")}
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(val=MISSING, description="", annotation=str, label="epsilonGradeA")
                        }
                    },
                    "gammaA": Tag(val=10, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {
            "command1": {
                "command2": {
                    "command3": {"command4": {"epsilonA": "epsilonAinjected"}},
                    "command3grade": {"command4": {"epsilonGradeA": "gradeAinjected"}},
                }
            }
        },
    ),
)

mcomp4 = """Level1(command1=Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level5Acli')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade5Acli')), gammaA=10), betaA='level 2A class'), alfa='level 1 class')"""

mcpassage1 = (
    (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Level2 a', 'Level2 b'])},
      {'': Level2A}
    ),
        (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Level3 a', 'Level3 b'])},
      {'': Level3A}
    ),
        (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Level5 a', 'Level5 b'])},
      {'': Level5A}
    ),
        (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Grade5 a', 'Level5 b'])},
      {'': Grade5A}
    ),
        (
      {'': {'alfa': Tag(val='level 1 config', description='', annotation=str, label='alfa')}, 'command1': {'command2': {'command3': {'command4': {'epsilonA': Tag(val='level 5A config', description='', annotation=str, label='epsilonA')}}, 'command3grade': {'command4': {'epsilonGradeA': Tag(val=MISSING, description='', annotation=str, label='epsilonGradeA')}}, 'gammaA': Tag(val=9, description='', annotation=int, label='gammaA')}, 'betaA': Tag(val='level 2A config', description='', annotation=str, label='betaA')}},
      {'command1': {'command2': {'command3grade': {'command4': {'epsilonGradeA': ''}}}}}
    ),
  )
mcpassage2 = (
    (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Level3 a', 'Level3 b'])},
      {'': Level3A}
    ),
        (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Level5 a', 'Level5 b'])},
      {'': Level5A}
    ),
        (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Grade5 a', 'Level5 b'])},
      {'': Grade5A}
    ),
        (
      {'': {'alfa': Tag(val='level 1 config', description='', annotation=str, label='alfa')}, 'command1': {'command2': {'command3': {'command4': {'epsilonA': Tag(val='level 5A config', description='', annotation=str, label='epsilonA')}}, 'command3grade': {'command4': {'epsilonGradeA': Tag(val=MISSING, description='', annotation=str, label='epsilonGradeA')}}, 'gammaA': Tag(val=9, description='', annotation=int, label='gammaA')}, 'betaA': Tag(val='level 2A config', description='', annotation=str, label='betaA')}},
      {'command1': {'command2': {'command3grade': {'command4': {'epsilonGradeA': 'gradeA injected'}}}}}
    ),
  )

mcpassage3= (
    (
      {'': {'alfa': Tag(val='level 1 config', description='', annotation=str, label='alfa')}, 'command1': {'command2': {'command3': {'command4': {'epsilonA': Tag(val='level 5A config', description='', annotation=str, label='epsilonA')}}, 'command3grade': {'command4': {'epsilonGradeA': Tag(val=MISSING, description='', annotation=str, label='epsilonGradeA')}}, 'gammaA': Tag(val=10, description='', annotation=int, label='gammaA')}, 'betaA': Tag(val='level 2A config', description='', annotation=str, label='betaA')}},
      {'command1': {'command2': {'command3grade': {'command4': {'epsilonGradeA': 'gradeA injected'}}}}}
    ),
  )

mccomp4="""Level1(command1=Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level5Acli')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade5Acli')), gammaA=10), betaA='level 2A config'), alfa='level 1 config')"""