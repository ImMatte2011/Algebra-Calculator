class DisplayBase:
    """Abstract interface for the display.

    Concrete implementations must expose hardware-agnostic methods.
    """

    def clear(self):
        raise NotImplementedError("clear() must be implemented by the subclass")

    def show_text(self, text: str, line: int = 0):
        raise NotImplementedError("show_text() must be implemented by the subclass")

    def show_loading(self):
        raise NotImplementedError("show_loading() must be implemented by the subclass")

    def render(self, expr, cursor_pos, status="", result=None, is_menu=False,
               menu_top="", menu_bottom=""):
        raise NotImplementedError("render() must be implemented by the subclass")
