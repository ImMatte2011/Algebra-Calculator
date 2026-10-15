"""Persistent store for the secrets requested by MicroPython's BLE IRQ API."""

import json


class BLESecretStore:
    def __init__(self, path="/ble_secrets.json"):
        self.path = path
        self._secrets = []
        self._load()

    def _load(self):
        try:
            with open(self.path, "r") as secret_file:
                rows = json.load(secret_file)
        except OSError as exc:
            if exc.args and exc.args[0] == 2:
                return
            raise

        for sec_type, key, value in rows:
            self._secrets.append((int(sec_type), bytes(key), bytes(value)))

    def _save(self):
        rows = [
            (sec_type, list(key), list(value))
            for sec_type, key, value in self._secrets
        ]
        with open(self.path, "w") as secret_file:
            secret_file.write(json.dumps(rows))

    def get_secret(self, sec_type, index, key):
        sec_type = int(sec_type)
        if key is None:
            matching = [value for kind, _, value in self._secrets
                        if kind == sec_type]
            if 0 <= index < len(matching):
                return matching[index]
            return None

        key = bytes(key)
        for kind, secret_key, value in self._secrets:
            if kind == sec_type and secret_key == key:
                return value
        return None

    def set_secret(self, sec_type, key, value):
        sec_type = int(sec_type)
        key = bytes(key)
        value = bytes(value) if value is not None else None
        for index, (kind, secret_key, _) in enumerate(self._secrets):
            if kind == sec_type and secret_key == key:
                if value is None:
                    del self._secrets[index]
                else:
                    self._secrets[index] = (sec_type, key, value)
                self._save()
                return True

        if value is not None:
            self._secrets.append((sec_type, key, value))
            self._save()
        return True
