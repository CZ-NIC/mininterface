from .tag import Tag, TagValue


from dataclasses import dataclass


@dataclass(repr=False)
class SecretTag(Tag[TagValue]):
    """
    Contains a secret value that should be masked in the UI.

    ```python
    from mininterface import run, Tag
    from mininterface.tag import SecretTag

    m = run()
    out = m.form({
        "My password": SecretTag("TOKEN"),
    })
    print(out)
    # {'My password': 'TOKEN'}
    ```

    ![File picker](asset/secret_tag.avif)
    """

    show_toggle: bool = True
    """ Toggle visibility button (eye icon) """

    _masked: bool = True
    """ Internal state for visibility """

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    def toggle_visibility(self):
        """Toggle the masked state"""
        self._masked = not self._masked
        return self._masked

    def _get_masked_val(self):
        """Value representation, suitable for an UI that does not handle a masked representation itself."""
        if self._masked and self.val:
            return "•" * len(str(self.val))
        return super()._get_ui_val()

    def __repr__(self):
        """Ensure secrets are not accidentally exposed in logs/repr"""
        return f"{self.__class__.__name__}(masked_value)"

    def __hash__(self):
        """Make SecretTag hashable for use with Annotated"""
        return hash((self.show_toggle, self._masked))
