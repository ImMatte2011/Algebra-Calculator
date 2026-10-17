"""Small RAM-only ring buffer for recently solved operations."""


class History:

    def __init__(self, max_entries=10):
        if not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        self.max_entries = max_entries
        self._items = []

    def add(self, expr, req_type, action, result):
        entry = (expr, req_type, action, result)
        if self._items and self._items[-1] == entry:
            return
        self._items.append(entry)
        if len(self._items) > self.max_entries:
            self._items.pop(0)

    def get(self, back):
        """Return an entry by reverse index (zero is the newest entry)."""
        if not isinstance(back, int) or back < 0 or back >= len(self._items):
            raise IndexError("history index out of range")
        return self._items[-1 - back]

    def clear(self):
        self._items = []

    def __len__(self):
        return len(self._items)
