from dataclasses import dataclass

@dataclass
class Level5A:
    epsilonA: str = "level5A class"


@dataclass
class Level5B:
    epsilonB: str = "level5B class"

@dataclass
class Level4:
    command4: Level5A | Level5B

@dataclass
class Grade5A:
    epsilonGradeA: str = "grade 5A class"

@dataclass
class Grade4:
    command4: Grade5A | Level5B

@dataclass
class Level3A:
    command3: Level4
    command3grade: Grade4
    gammaA: int = 1

@dataclass
class Level3B:
    gammaB: int = 1

@dataclass
class Level2A:
    command2: Level3A | Level3B
    betaA: str = "level 2A class"


@dataclass
class Level2B:
    betaB: str = "level 2B class"


@dataclass
class Level1:
    command1: Level2A | Level2B
    alfa: str = "level 1 class"
