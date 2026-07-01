def info(message: str, *args):
    if args:
        message = message % args
    print(f"[INFO] {message}")


def warning(message: str, *args):
    if args:
        message = message % args
    print(f"[WARN] {message}")


def error(message: str, *args):
    if args:
        message = message % args
    print(f"[ERROR] {message}")


def debug(message: str, *args):
    if args:
        message = message % args
    print(f"[DEBUG] {message}")