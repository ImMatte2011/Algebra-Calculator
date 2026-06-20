class TextScroller:
    """Gestisce lo scorrimento non bloccante del testo su display limitati."""

    def __init__(self, width, rows=1):
        self.width = width
        self.rows = rows
        self.text = ""
        self.cursor_pos = 0
        self.window_start = 0
        self.max_start = 0

    def update(self, text, cursor_pos=None):
        """Aggiorna lo stato con il testo corrente e calcola la finestra visibile."""
        self.text = text or ""
        self.cursor_pos = min(max(0, cursor_pos if cursor_pos is not None else len(self.text)), len(self.text))
        self.max_start = max(0, len(self.text) - self.width)
        self._recenter_window()
        return self.get_visible_text()

    def _recenter_window(self):
        """Posiziona la finestra in modo che il cursore resti sulla destra se possibile."""
        if len(self.text) <= self.width:
            self.window_start = 0
            return

        target_start = self.cursor_pos - self.width + 1
        if target_start < 0:
            target_start = 0

        if target_start > self.max_start:
            target_start = self.max_start

        self.window_start = target_start

    def scroll_left(self):
        """Scorri la finestra verso l'inizio del testo."""
        self.window_start = max(0, self.window_start - 1)
        return self.get_visible_text()

    def scroll_right(self):
        """Scorri la finestra verso la fine del testo."""
        self.window_start = min(self.max_start, self.window_start + 1)
        return self.get_visible_text()

    def get_visible_text(self):
        """Restituisce il segmento di testo attualmente visibile."""
        if len(self.text) <= self.width:
            return self.text + " " * (self.width - len(self.text))

        end = self.window_start + self.width
        return self.text[self.window_start:end]

    def get_window_range(self):
        return self.window_start, self.window_start + self.width
