class TextScroller:
    """Manages non-blocking text scrolling on limited displays."""

    def __init__(self, width, rows=1):
        self.width = width
        self.rows = rows
        self.text = ""
        self.cursor_pos = 0
        self.window_start = 0
        self.max_start = 0

    def update(self, text, cursor_pos=None):
        """Updates the state with the current text and computes the visible window."""
        self.text = text or ""
        self.cursor_pos = min(max(0, cursor_pos if cursor_pos is not None else len(self.text)), len(self.text))
        self.max_start = max(0, len(self.text) - self.width)
        self._recenter_window()
        return self.get_visible_text()

    def _recenter_window(self):
        """Keeps the window positioned so the cursor stays on the right when possible."""
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
        """Scrolls the window toward the start of the text."""
        self.window_start = max(0, self.window_start - 1)
        return self.get_visible_text()

    def scroll_right(self):
        """Scrolls the window toward the end of the text."""
        self.window_start = min(self.max_start, self.window_start + 1)
        return self.get_visible_text()

    def get_visible_text(self):
        """Returns the text segment currently visible."""
        if len(self.text) <= self.width:
            return self.text + " " * (self.width - len(self.text))

        end = self.window_start + self.width
        return self.text[self.window_start:end]

    def get_window_range(self):
        return self.window_start, self.window_start + self.width
