#!/usr/bin/env python3
import json
import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent


def load_env_file():
    for candidate in (ROOT / ".env", ROOT / ".env.example"):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_file()


def get_env_value(*keys, default=""):
    for key in keys:
        value = os.environ.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def normalize_credential(value):
    return "" if value is None else str(value).replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")


def smtp_config():
    return {
        "host": get_env_value("SMTP_HOST", "HOST"),
        "port": int(get_env_value("SMTP_PORT", "PORT", default="587")),
        "user": normalize_credential(get_env_value("SMTP_USER", "USER", "EMAIL_USER")),
        "password": normalize_credential(get_env_value("SMTP_PASS", "PASS", "EMAIL_PASS", "PASSWORD")),
        "from_email": normalize_credential(get_env_value("SMTP_FROM", "FROM", "EMAIL_FROM", default=get_env_value("SMTP_USER", "USER", "EMAIL_USER"))),
        "to_email": get_env_value("EMAIL_TO", "TO_EMAIL", default="alvinteo246810@gmail.com"),
        "use_tls": get_env_value("SMTP_USE_TLS", "USE_TLS", default="true").lower() == "true",
        "use_ssl": get_env_value("SMTP_USE_SSL", "USE_SSL", default="false").lower() == "true",
    }


def send_email_via_smtp(payload):
    config = smtp_config()
    to_email = (payload or {}).get("to_email") or config["to_email"]
    subject = (payload or {}).get("subject") or "Alvin 的赎罪计划"
    body = (payload or {}).get("body") or "Alvin：已收到你的道歉与礼物。"
    html = (payload or {}).get("html")

    missing = [
        name for name, value in {
            "SMTP_HOST": config["host"],
            "SMTP_USER": config["user"],
            "SMTP_PASS": config["password"],
            "SMTP_FROM": config["from_email"],
        }.items() if not value
    ]
    if missing:
        raise RuntimeError(
            "SMTP is not configured. Set " + ", ".join(missing) + " before starting the server."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["from_email"]
    msg["To"] = to_email
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    if config["use_ssl"]:
        with smtplib.SMTP_SSL(
            config["host"], config["port"], context=ssl.create_default_context(), timeout=20
        ) as server:
            server.login(config["user"], config["password"])
            server.send_message(msg)
    else:
        with smtplib.SMTP(config["host"], config["port"], timeout=20) as server:
            server.ehlo()
            if config["use_tls"]:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(config["user"], config["password"])
            server.send_message(msg)

    return {"ok": True, "message": f"Email sent to {to_email}"}


class GameHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        parsed = urlparse(self.path)
        rel = parsed.path

        if rel == "/api/health":
            self._send_json(200, {"ok": True, "status": "healthy"})
            return

        if rel == "/":
            rel = "/道歉大作战.html"

        target = (ROOT / rel.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT)):
            self._send_json(403, {"ok": False, "error": "Forbidden"})
            return

        if not target.exists() or not target.is_file():
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        mime_type, _ = mimetypes.guess_type(str(target))
        if mime_type is None:
            mime_type = "application/octet-stream"

        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type + "; charset=utf-8" if mime_type.startswith("text/") else mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/send-email":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._send_json(400, {"ok": False, "error": f"Invalid JSON: {exc}"})
            return

        try:
            response = send_email_via_smtp(payload)
            self._send_json(200, response)
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), GameHandler)
    print(f"Server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()
