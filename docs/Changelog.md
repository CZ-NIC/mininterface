# Changelog

## 0.7.2
* GUI calendar

## 0.7.1 (2024-11-27)
* GUI scrollbars if window is bigger than the screen
* [non-interactive][mininterface.Mininterface.__enter__] session support
* [datetime](Types/#mininterface.types.DatetimeTag) support
* nested generics support (a tuple in a list)

## 0.7.0 (2024-11-08)
* hidden [`--integrate-to-system`](Overview.md#bash-completion) argument
* interfaces migrated to [`mininterface.interfaces`](Interfaces.md) to save around 50 ms starting time due to lazy loading
* [SubcommandPlaceholder][mininterface.subcommands.Command]