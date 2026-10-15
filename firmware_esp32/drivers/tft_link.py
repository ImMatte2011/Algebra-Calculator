"""Small newline-framed JSON transport shared by the calculator and TFT ESP32s."""

try:
    import ujson as json
except ImportError:
    import json


MAX_FRAME = 1024


class TftUartLink:
    def __init__(self, uart):
        self._uart = uart
        self._rx = bytearray()
        self._messages = []

    def send(self, message):
        try:
            encoded = json.dumps(message, separators=(",", ":"))
        except TypeError:
            encoded = json.dumps(message)
        data = encoded.encode() + b"\n"
        if len(data) > MAX_FRAME:
            raise ValueError("TFT link frame exceeds {} bytes".format(MAX_FRAME))
        written = self._uart.write(data)
        if written != len(data):
            raise OSError("TFT UART write incomplete: {} of {} bytes".format(
                written, len(data)))

    def receive(self):
        data = self._uart.read()
        if data:
            self._rx.extend(data)

        while True:
            end = self._rx.find(b"\n")
            if end < 0:
                if len(self._rx) > MAX_FRAME:
                    self._rx = bytearray()
                    print("TFT link: discarded oversized unterminated frame")
                break

            frame = self._rx[:end]
            del self._rx[:end + 1]
            if not frame:
                continue
            if len(frame) > MAX_FRAME:
                print("TFT link: discarded oversized frame")
                continue
            try:
                self._messages.append(json.loads(frame.decode()))
            except (ValueError, UnicodeError) as exc:
                print("TFT link: discarded invalid JSON frame:", exc)

        return self._messages.pop(0) if self._messages else None
