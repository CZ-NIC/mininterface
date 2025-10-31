# Changelog

## unreleased
* enh: config file union support
* fix: invoking gui interface twice

## 1.2.1 (2025-10-24)
* deps (tyro): ready for 0.10

## 1.2.0 (2025-10-17)
* feat: [`run`][mininterface.run] add_config flag
* feat: [subcommands](Supported-types.md/#dataclasses-union-subcommand) allowed in the config file

## 1.1.4 (2025-10-13)
* enh: Python 3.14 compatible

## 1.1.3 (2025-10-09)
* enh (TextInterface): Esc raises Cancelled in countdown
* enh (run): settings accepts subclasses (-> shorter notation)
* enh: [CliSettings][mininterface.settings.CliSettings]
* fix: Countdown won't stop on Alt+Tab.
* fix: temporary prevent Python3.14

## 1.1.2 (2025-10-01)
* feat: timeout parameter for alert & confirm
* enh: `list[tuple]` supperfluous arguments check
* enh: dict in a dataclass support
* fix: config file resilience (subcommands union and str-attribute missing clash)
* fix: SelectTag multiple choice without default value resilience
* fix: dynamic Literal in Annotated

## 1.1.1 (2025-09-18)
* enh: `list[tuple]` support (along with `list[tuple[int]]` and `list[tuple[int, ...]]`)
* fix: objects in config files

## 1.1.0 (2025-09-12)
* CHANGED – some [`run`][mininterface.run] arguments are no longer positional and can only be passed as keyword arguments
* feat: interactive CLI (nested configuration missing fields dialogs)
* feat: [`run`][mininterface.run] add_version, add_version_package, add_quiet flags
* feat: add utility for generating unit tests
* feat: [annotated types][mininterface.tag.tag.ValidationCallback] for collections
* feat: [`Blank`][mininterface.tag.flag.Blank] flag marker default value
* feat: None value in [SelectTag][mininterface.tag.SelectTag]
* enh: custom validation is done at dataclass built, not later on the form call
* fix: SelectTag preset value
* fix: ArgumentParser parameters (like allow_abbrev)

## 1.0.4 (2025-08-18)
* enh: better argparse support (const support, store_false matching, subcommands)
* feat: Added time constraint to the DatetimeTag #28
* feat: implement unified toggle widget shortcut system across interfaces #29
* feat: correctly handles `Path|None` and `datetime|None` syntax

## 1.0.3 (2025-06-18)
* enh: Tk better file dialog
* feat: [Tag.mnemonic][mininterface.Tag.mnemonic]
* feat: config file tuple annotation support

## 1.0.2 (2025-05-10)
* fix: mute TextInterface on Win

## 1.0.1 (2025-05-08)
* fix: gui ask validation

## 1.0.0 (2025-05-08)
* CHANGED – renamed: API is becoming stable but we have to rename several things.
    * .is_yes -> [Mininterface.confirm][mininterface.Mininterface.confirm]
    * .is_no -> .confirm(..., False) (because .is_no was counterintuitive)
    * .choice -> [Mininterface.select][mininterface.Mininterface.select] (as HTML counterpart)
    * EnumTag(choices=) -> [SelectTag(options=)][mininterface.tag.SelectTag]
    * Choices alias -> Options alias
    * MininterfaceOptions -> [MininterfaceSettings][mininterface.settings.MininterfaceSettings] (to not meddle with the SelectTag)
    * mininterface.types.rich_tags -> [mininterface.tag.*][mininterface.tag.SelectTag]
    * Tag attribute order, swap `name` and `validation`
    * .ask_number -> [Mininterface.ask(..., int)][mininterface.Mininterface.ask]
    * Mininterface.ask does not return None anymore but forces the type
    * Tag.name -> Tag.label
    * removed `--integrate-to-system` in favour of `mininterface integrate`
    * .subcommands -> [mininterface.cli][]
* [WebInterface](Interfaces.md#webinterface-or-web)
* SelectTag(multiple=)
* argparse support
* minimal bundle
* file picker
* fix: TkInterface focus and tab navigation

## 0.8.0 (2025-04-01)
* CHANGED: [EnumTag][mininterface.tag.SelectTag] instead of Tag(choices=)
* [WebInterface](Interfaces.md#webinterface-or-web) (working draft)
* much better [TextInterface](Interfaces.md#textinterface)
* [SecretTag][mininterface.tag.SecretTag]
* PathTag UI in TextualInterface
* UI options available from the program
* Mininterface.choice [tips][mininterface.Mininterface.select] parameter
* better annotated fetching

## 0.7.5 (2025-01-29)
* UI [options](Settings.md)
* experimental [Facet._layout](Facet.md#layout)

## 0.7.4 (2025-01-27)
* Python 3.13 compatible
* emits a warning for config file fields that are unknown to the model

## 0.7.3 (2025-01-09)
* fix: put GUI descriptions back to the bottom

## 0.7.2 (2024-12-30)
* GUI calendar

## 0.7.1 (2024-11-27)
* GUI scrollbars if window is bigger than the screen
* [non-interactive][mininterface.Mininterface.__enter__] session support
* [datetime][mininterface.tag.DatetimeTag] support
* nested generics support (a tuple in a list)

## 0.7.0 (2024-11-08)
* hidden [`--integrate-to-system`](Overview.md#bash-completion) argument
* interfaces migrated to [`mininterface.interfaces`](Interfaces.md) to save around 50 ms starting time due to lazy loading
* [SubcommandPlaceholder][mininterface.cli.Command]