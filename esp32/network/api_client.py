import urequests
import ujson
import os

API_URL = os.getenv("API_URL")  # e.g. "http://192.168.1.100:8000/solve"
API_TOKEN = os.getenv("API_TOKEN")

def solve_expression(expr: str, timeout=5):
	"""Send an expression to the server and return parsed response dict.

	Designed for MicroPython on ESP32 (uses `urequests`).
	"""
	if not API_URL:
		raise RuntimeError("API_URL not configured")

	headers = {"Content-Type": "application/json"}
	if API_TOKEN:
		headers["Authorization"] = "Bearer " + API_TOKEN

	payload = {"expr": expr}
	try:
		resp = urequests.post(API_URL, json=payload, headers=headers, timeout=timeout)
		text = resp.text
		resp.close()
		try:
			return ujson.loads(text)
		except Exception:
			return {"error": "invalid json", "raw": text}
	except Exception as e:
		return {"error": str(e)}

