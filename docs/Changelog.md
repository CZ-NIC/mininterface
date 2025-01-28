# Changelog

## 0.7.5
* UI [configuration](Configuration.md)

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
* [datetime](Types.md#mininterface.types.DatetimeTag) support
* nested generics support (a tuple in a list)

## 0.7.0 (2024-11-08)
* hidden [`--integrate-to-system`](Overview.md#bash-completion) argument
* interfaces migrated to [`mininterface.interfaces`](Interfaces.md) to save around 50 ms starting time due to lazy loading
* [SubcommandPlaceholder][mininterface.subcommands.Command]