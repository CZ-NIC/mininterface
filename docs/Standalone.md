When invoked directly, it creates simple GUI dialogs.

```bash
$ mininterface  --help
usage: Mininterface [-h] [OPTIONS]

Simple GUI dialog. Outputs the value the user entered.

╭─ options ─────────────────────────────────────────────────────────────────────────────────╮
│ -h, --help              show this help message and exit                                   │
│ --alert STR             Display the OK dialog with text. (default: '')                    │
│ --ask STR               Prompt the user to input a text. (default: '')                    │
│ --ask-number STR        Prompt the user to input a number. Empty input = 0. (default: '') │
│ --is-yes STR            Display confirm box, focusing yes. (default: '')                  │
│ --is-no STR             Display confirm box, focusing no. (default: '')                   │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
```

You can fetch a value to i.e. a bash script.

```bash
$ mininterface  --ask-number "What's your age?"  # GUI window invoked
18
```
