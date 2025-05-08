from mininterface.tag import PathTag
from mininterface import run

m = run(interface="gui")
out = m.form({
    "A path1": PathTag(multiple=True),
})
print("Result", out)
