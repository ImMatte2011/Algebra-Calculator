class DisplayBase:
    """Interfaccia astratta per il display.

    Le implementazioni concrete devono esporre metodi hardware-agnostici.
    """

    def clear(self):
        raise NotImplementedError("clear() deve essere implementato dalla sottoclasse")

    def show_text(self, text: str, line: int = 0):
        raise NotImplementedError("show_text() deve essere implementato dalla sottoclasse")

    def show_loading(self):
        raise NotImplementedError("show_loading() deve essere implementato dalla sottoclasse")
