# Facet
::: mininterface.facet.Facet

## Layout

!!! Experimental
    Share your thoughts about how the layout method should work!

Should you need to represent more information, Facet has a hidden method `_layout` that you may call with a list of `LayoutElements`:

* `str`
* `pathlib.Path`
* `facet.Image`

```python
from dataclasses import dataclass
from pathlib import Path
from mininterface import run
from mininterface.facet import Image

@dataclass
class Env:
    my_str: str = "Hello"

m = run(Env)
# The Image object currently has a single 'src' attribute
m.facet._layout(["My text", Image("dog1.jpg"), Path("dog1.jpg")])
m.form()
```

As you see, the program displays "My text", then the image, and then the path info.
![Layout GUI](asset/layout-gui.avif)

Even in the TUI, the images are visible. (And mouse-zoomable.)
![Layout TUI](asset/layout-tui.avif)