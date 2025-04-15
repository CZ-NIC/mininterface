# Changelog

## unreleased
* CHANGED – renamed: API is becoming stable but we have to rename several things.
    * Mininterface.is_yes -> [.confirm][mininterface.Mininterface.confirm]
    * Mininterface.is_no -> .confirm(..., False) (because .is_no was counterintuitive)
    * Mininterface.choice -> [.select][mininterface.Mininterface.select] (as HTML counterpart)
    * EnumTag(choices=) -> [SelectTag(options=)][mininterface.tag.SelectTag]
    * Choices alias -> Options alias
    * MininterfaceOptions -> [MininterfaceSettings][mininterface.settings.MininterfaceSettings] (to not meddle with the SelectTag)
    * mininterface.types.rich_tags -> [mininterface.tag.*][mininterface.tag.SelectTag]
    * Tag attribute order, swap `name` and `validation`
    * Mininterface.ask_number -> ask(..., int)
    * Mininterface.ask does not return None anymore but forces the type
* enh: options add shortcut
* feat: EnumTag multiple
* fix: TkInterface focus and tab navigation

## 0.8.0 (2025-04-01)
* CHANGED: [EnumTag][mininterface.tag.SelectTag] instead of Tag(options=)
* [WebInterface](Interfaces.md#webinterface-or-web) (working draft)
* much better [TextInterface](Interfaces.md#textinterface)
* [SecretTag][mininterface.tag.SecretTag]
* PathTag UI in TextualInterface
* UI options available from the program
* Mininterface.choice [tips][mininterface.Mininterface.choice] parameter
* better annotated fetching

## 0.7.5 (2025-01-29)
* UI [options](Settings.md)
* experimental [Facet._layout](Facet.md#layout)

## 0.7.4 (2025-01-27)
* Python 3.13 compatible
* emits a warning when for config file fields, unknown to the model

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
* [SubcommandPlaceholder][mininterface.subcommands.Command]