from mininterface import Tag
from mininterface.tag import SelectTag

from heavy_nesting_configs import Grade5A, Level1, Level2A, Level2B, Level3A, Level3B, Level5A, Level5B

passage1 = (
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
                        "command4": {
                            "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

passage2 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level2 a", "Level2 b"])},
        {"": Level2B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {"betaB": Tag(val="level 2B class", description="", annotation=str, label="betaB")},
        },
        {},
    ),
)
passage3 = (
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
        {"": Level5B},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonB": Tag(val="level5B class", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonB": Tag(val="level5B class", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)
passage4 = (
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
                        "command4": {
                            "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)
passage5 = (
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
                        "command4": {
                            "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)
passage6 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonB": Tag(val="level5B class", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonB": Tag(val="level5B class", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

passage7 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 class", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonB": Tag(val="level5B class", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

passage8 = (
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
                        "command4": {
                            "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=10, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

comp9 = """Level1(command1=Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level5A class')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade 5A class')), gammaA=1), betaA='level 2A class'), alfa='level 1 class')"""
comp10 = """Level1(command1=Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level5A class')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade 5A class')), gammaA=10), betaA='level 2A class'), alfa='level 1 class')"""

cpassage1 = (
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
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage2 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level2 a", "Level2 b"])},
        {"": Level2A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level3 a", "Level3 b"])},
        {"": Level3B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {"gammaB": Tag(val=1, description="", annotation=int, label="gammaB")},
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage3 = (
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
        {"": Level5B},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonB": Tag(val="level 5B config", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonB": Tag(val="grade 5B config", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage4 = (
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
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage5 = (
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
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage6 = (
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
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage7 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level5 a", "Level5 b"])},
        {"": Level5A},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonB": Tag(val="grade 5B config", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage8 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Grade5A},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonGradeA": Tag(
                                val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                            )
                        }
                    },
                    "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

cpassage9 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {
            "": {"alfa": Tag(val="level 1 config", description="", annotation=str, label="alfa")},
            "command1": {
                "command2": {
                    "command3": {
                        "command4": {
                            "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                        }
                    },
                    "command3grade": {
                        "command4": {
                            "epsilonB": Tag(val="grade 5B config", description="", annotation=str, label="epsilonB")
                        }
                    },
                    "gammaA": Tag(val=10, description="", annotation=int, label="gammaA"),
                },
                "betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA"),
            },
        },
        {},
    ),
)

ccomp7 = """Level1(command1=Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level 5A config')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade 5A class')), gammaA=9), betaA='level 2A config'), alfa='level 1 config')"""
ccomp8 = """Level1(command1=Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level 5A config')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade 5A class')), gammaA=10), betaA='level 2A config'), alfa='level 1 config')"""


help1 = """usage: running-tests [-h] [-v] [--alfa STR]
                     {command1:level2-a,command1:level2-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
│ --alfa STR           (default: 'level 1 config')                           │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1 subcommands ─────────────────────────────────────────────────────╮
│ (required)                                                                 │
│ ───────────────────────────────────────────────────────────────────────────│
│ {command1:level2-a,command1:level2-b}                                      │
│     command1:level2-a                                                      │
│     command1:level2-b                                                      │
╰────────────────────────────────────────────────────────────────────────────╯"""

help2 = """usage: running-tests command1:level2-a [-h] [-v] [--command1.betaA STR]
                                       {command1.command2:level3-a,command1.co
mmand2:level3-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help              show this help message and exit                    │
│ -v, --verbose           verbosity level, can be used multiple times to     │
│                         increase                                           │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1 options ─────────────────────────────────────────────────────────╮
│ --command1.betaA STR    (default: 'level 2A config')                       │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2 subcommands (required) ──────────────────────────────────────────────────────────────╮
│ {command1.command2:level3-a,command1.command2:level3-b}                    │
│     command1.command2:level3-a                                             │
│     command1.command2:level3-b                                             │
╰────────────────────────────────────────────────────────────────────────────╯"""

help3 = """usage: running-tests command1:level2-a command1.command2:level3-a
       [-h] [-v] [--command1.command2.gammaA INT]
       {command1.command2.command3.command4:level5-a,command1.command2.command
3.command4:level5-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2 options ────────────────────────────────────────────────╮
│ --command1.command2.gammaA INT                                             │
│                      (default: 9)                                          │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ subcommands ──────────────────────────────────────────────────────────────╮
│ {command1.command2.command3.command4:level5-a,command1.command2.command3.c │
│ ommand4:level5-b}                                                          │
│     command1.command2.command3.command4:level5-a                           │
│     command1.command2.command3.command4:level5-b                           │
╰────────────────────────────────────────────────────────────────────────────╯"""

help4 = """usage: running-tests command1:level2-a command1.command2:level3-a
       [-h] [-v] [--command1.command2.gammaA INT]
       {command1.command2.command3.command4:level5-a,command1.command2.command
3.command4:level5-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2 options ────────────────────────────────────────────────╮
│ --command1.command2.gammaA INT                                             │
│                      (default: 9)                                          │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ subcommands ──────────────────────────────────────────────────────────────╮
│ {command1.command2.command3.command4:level5-a,command1.command2.command3.c │
│ ommand4:level5-b}                                                          │
│     command1.command2.command3.command4:level5-a                           │
│     command1.command2.command3.command4:level5-b                           │
╰────────────────────────────────────────────────────────────────────────────╯"""

help5 = """usage: running-tests command1:level2-a command1.command2:level3-a
       [-h] [-v] [--command1.command2.gammaA INT]
       {command1.command2.command3.command4:level5-a,command1.command2.command
3.command4:level5-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2 options ────────────────────────────────────────────────╮
│ --command1.command2.gammaA INT                                             │
│                      (default: 9)                                          │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ subcommands ──────────────────────────────────────────────────────────────╮
│ {command1.command2.command3.command4:level5-a,command1.command2.command3.c │
│ ommand4:level5-b}                                                          │
│     command1.command2.command3.command4:level5-a                           │
│     command1.command2.command3.command4:level5-b                           │
╰────────────────────────────────────────────────────────────────────────────╯"""

help6 = """usage: running-tests command1:level2-a command1.command2:level3-a
command1.command2.command3.command4:level5-a
       [-h] [-v] [--command1.command2.command3.command4.epsilonA STR]
       {command1.command2.command3grade.command4:grade5-a,command1.command2.co
mmand3grade.command4:level5-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2.command3.command4 options ──────────────────────────────╮
│ --command1.command2.command3.command4.epsilonA STR                         │
│                      (default: 'level 5A config')                          │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ subcommands ──────────────────────────────────────────────────────────────╮
│ {command1.command2.command3grade.command4:grade5-a,command1.command2.comma │
│ nd3grade.command4:level5-b}                                                │
│     command1.command2.command3grade.command4:grade5-a                      │
│     command1.command2.command3grade.command4:level5-b                      │
╰────────────────────────────────────────────────────────────────────────────╯"""

help7 = """usage: running-tests command1:level2-a command1.command2:level3-a
command1.command2.command3.command4:level5-a
       [-h] [-v] [--command1.command2.command3.command4.epsilonA STR]
       {command1.command2.command3grade.command4:grade5-a,command1.command2.co
mmand3grade.command4:level5-b}

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2.command3.command4 options ──────────────────────────────╮
│ --command1.command2.command3.command4.epsilonA STR                         │
│                      (default: 'level 5A config')                          │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ subcommands ──────────────────────────────────────────────────────────────╮
│ {command1.command2.command3grade.command4:grade5-a,command1.command2.comma │
│ nd3grade.command4:level5-b}                                                │
│     command1.command2.command3grade.command4:grade5-a                      │
│     command1.command2.command3grade.command4:level5-b                      │
╰────────────────────────────────────────────────────────────────────────────╯"""

help8 = """usage: running-tests command1:level2-a command1.command2:level3-a
command1.command2.command3.command4:level5-a
command1.command2.command3grade.command4:grade5-a
       [-h] [-v]
       [--command1.command2.command3grade.command4.epsilonGradeA STR]

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2.command3grade.command4 options ─────────────────────────╮
│ --command1.command2.command3grade.command4.epsilonGradeA STR               │
│                      (default: 'grade 5A class')                           │
╰────────────────────────────────────────────────────────────────────────────╯"""

help9 = """usage: running-tests command1:level2-a command1.command2:level3-a
command1.command2.command3.command4:level5-a
command1.command2.command3grade.command4:grade5-a
       [-h] [-v]
       [--command1.command2.command3grade.command4.epsilonGradeA STR]

╭─ options ──────────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                       │
│ -v, --verbose        verbosity level, can be used multiple times to        │
│                      increase                                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ command1.command2.command3grade.command4 options ─────────────────────────╮
│ --command1.command2.command3grade.command4.epsilonGradeA STR               │
│                      (default: 'grade 5A class')                           │
╰────────────────────────────────────────────────────────────────────────────╯"""

upassage1 = (
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
            "": {"betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA")},
            "command2": {
                "command3": {
                    "command4": {
                        "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                    }
                },
                "command3grade": {
                    "command4": {
                        "epsilonGradeA": Tag(
                            val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                        )
                    }
                },
                "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
            },
        },
        {},
    ),
)

upassage2 = (
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
            "": {"betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA")},
            "command2": {
                "command3": {
                    "command4": {
                        "epsilonA": Tag(val="level5A class", description="", annotation=str, label="epsilonA")
                    }
                },
                "command3grade": {
                    "command4": {
                        "epsilonGradeA": Tag(
                            val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                        )
                    }
                },
                "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
            },
        },
        {},
    ),
)

upassage3 = (
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Level5 a", "Level5 b"])},
        {"": Level5B},
    ),
    (
        {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Grade5 a", "Level5 b"])},
        {"": Grade5A},
    ),
    (
        {
            "": {"betaA": Tag(val="level 2A class", description="", annotation=str, label="betaA")},
            "command2": {
                "command3": {
                    "command4": {
                        "epsilonB": Tag(val="level5B class", description="", annotation=str, label="epsilonB")
                    }
                },
                "command3grade": {
                    "command4": {
                        "epsilonGradeA": Tag(
                            val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                        )
                    }
                },
                "gammaA": Tag(val=1, description="", annotation=int, label="gammaA"),
            },
        },
        {},
    ),
)

ucomp4 = """Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level5A class')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade 5A class')), gammaA=10), betaA='level 2A class')"""


ucpassage1 = (
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
            "": {"betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA")},
            "command2": {
                "command3": {
                    "command4": {
                        "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                    }
                },
                "command3grade": {
                    "command4": {
                        "epsilonGradeA": Tag(
                            val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                        )
                    }
                },
                "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
            },
        },
        {},
    ),
)


ucpassage2 = (
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
            "": {"betaA": Tag(val="level 2A config", description="", annotation=str, label="betaA")},
            "command2": {
                "command3": {
                    "command4": {
                        "epsilonA": Tag(val="level 5A config", description="", annotation=str, label="epsilonA")
                    }
                },
                "command3grade": {
                    "command4": {
                        "epsilonGradeA": Tag(
                            val="grade 5A class", description="", annotation=str, label="epsilonGradeA"
                        )
                    }
                },
                "gammaA": Tag(val=9, description="", annotation=int, label="gammaA"),
            },
        },
        {},
    ),
)
ucpassage3 = (
    (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Level5 a', 'Level5 b'])},
      {'': Level5B}
    ),
        (
      {'': SelectTag(val=None, description='', annotation=None, label=None, options=['Grade5 a', 'Level5 b'])},
      {'': Level5B}
    ),
        (
      {'': {'betaA': Tag(val='level 2A config', description='', annotation=str, label='betaA')}, 'command2': {'command3': {'command4': {'epsilonB': Tag(val='level 5B config', description='', annotation=str, label='epsilonB')}}, 'command3grade': {'command4': {'epsilonB': Tag(val='grade 5B config', description='', annotation=str, label='epsilonB')}}, 'gammaA': Tag(val=9, description='', annotation=int, label='gammaA')}},
      {}
    )
  )

uccomp4 = """Level2A(command2=Level3A(command3=Level4(command4=Level5A(epsilonA='level 5A config')), command3grade=Grade4(command4=Grade5A(epsilonGradeA='grade 5A class')), gammaA=10), betaA='level 2A config')"""