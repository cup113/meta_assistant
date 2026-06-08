from collections.abc import Callable
from typing import overload

class Icon:
    def __init__(
        self,
        name: str,
        icon: object | None = None,
        *,
        title: str | None = None,
        menu: Menu | None = None,
    ) -> None: ...
    def run_detached(self, setup: Callable[[], None] | None = None) -> None: ...
    def stop(self) -> None: ...
    def update_menu(self) -> None: ...

class MenuItem:
    def __init__(
        self,
        text: str,
        action: Callable[[Icon, MenuItem], None] | Menu | None = None,
        *,
        checked: Callable[[MenuItem], bool] | None = None,
        radio: bool = False,
        default: bool = False,
        visible: bool = True,
        enabled: bool = True,
    ) -> None: ...

class Menu:
    SEPARATOR: MenuItem

    @overload
    def __init__(self, factory: Callable[[], list[MenuItem]]) -> None: ...
    @overload
    def __init__(self, *items: MenuItem) -> None: ...
