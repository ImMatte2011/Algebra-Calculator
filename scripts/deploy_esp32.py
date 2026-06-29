"""Generate `esp32/settings.py` from a .env file for flashing the ESP32.

Usage:
    cd <project-root>
    python scripts/deploy_esp32.py --env .env.esp32 --out firmware_esp32/settings.py

This reads KEY=VALUE pairs (ignoring comments) and writes a small Python
module with assignments suitable to copy to the device (MicroPython).
"""
import argparse
import shlex
from pathlib import Path


def parse_env(path):
    data = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # remove surrounding quotes
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        data[k] = v
    return data


def pythonize(value):
    # try int
    if value.isdigit():
        return value
    # try negative int
    if value.startswith("-") and value[1:].isdigit():
        return value
    # otherwise escape and quote
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--env", default=".env.esp32", help="Path to env file")
    p.add_argument("--out", default="firmware_esp32/settings.py", help="Output settings.py path")
    args = p.parse_args()

    env_path = Path(args.env)
    if not env_path.exists():
        print("Env file not found:", env_path)
        raise SystemExit(1)

    data = parse_env(env_path)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Auto-generated settings for ESP32 (MicroPython friendly)"]
    for k, v in sorted(data.items()):
        pyval = pythonize(v)
        lines.append(f"{k} = {pyval}")

    out_path.write_text("\n".join(lines) + "\n")
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
