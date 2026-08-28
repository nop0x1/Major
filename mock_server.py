"""
Free Fire Mock Server — Vercel Serverless Edition
Mimics Garena auth endpoints, captures and logs all requests.
"""

from flask import Flask, request, jsonify, Response
import json
import time
import hashlib
import random

app = Flask(__name__)


# ─── Fake data generators ─────────────────────────────────────────────────────

def fake_access_token():
    return hashlib.sha256(str(random.random()).encode()).hexdigest()

def fake_open_id():
    return hashlib.md5(str(random.random()).encode()).hexdigest()

def fake_refresh_token():
    return hashlib.sha256(str(random.random() + 1).encode()).hexdigest()

def fake_uid():
    return random.randint(4000000000, 5000000000)


# ─── Request logger ───────────────────────────────────────────────────────────

def log_request(endpoint):
    """Logs to Vercel's runtime log (visible in dashboard → Functions → Logs)."""
    print("\n" + "=" * 60, flush=True)
    print(f"  [REQUEST] {endpoint}", flush=True)
    print(f"  Method  : {request.method}", flush=True)
    print(f"  From    : {request.headers.get('x-forwarded-for', request.remote_addr)}", flush=True)
    print(f"  Time    : {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    print("\n  --- Headers ---", flush=True)
    for k, v in request.headers:
        print(f"  {k}: {v}", flush=True)

    raw = request.get_data()
    print(f"\n  --- Body (raw) ---\n  {raw}", flush=True)
    print(f"\n  --- Body (hex) ---\n  {raw.hex()}", flush=True)

    if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
        print("\n  --- Form Fields ---", flush=True)
        for k, v in request.form.items():
            print(f"  {k}: {v}", flush=True)

    print("=" * 60, flush=True)


# ─── Protobuf helpers ─────────────────────────────────────────────────────────

def encode_varint(n):
    result = bytearray()
    while n:
        b = n & 0x7F
        n >>= 7
        result.append(b | (0x80 if n else 0))
    return bytes(result)

def encode_string_field(field_number, value):
    b = value.encode()
    return encode_varint((field_number << 3) | 2) + encode_varint(len(b)) + b

def encode_varint_field(field_number, value):
    return encode_varint((field_number << 3) | 0) + encode_varint(value)


# ─── Endpoint 1: Token Grant ──────────────────────────────────────────────────

@app.route('/oauth/guest/token/grant', methods=['POST'])
def token_grant():
    log_request("/oauth/guest/token/grant")

    now = int(time.time())
    response = {
        "refresh_expiry_time":  now + 2592000,
        "expiry_time":          now + 1296000,
        "uid":                  fake_uid(),
        "open_id":              fake_open_id(),
        "access_token":         fake_access_token(),
        "main_active_platform": 4,
        "expires_in":           1296000,
        "token_type":           "Bearer",
        "platform":             4,
        "create_time":          now,
        "scope":                ["get_user_info", "get_friends", "payment", "send_request"],
        "refresh_token":        fake_refresh_token(),
    }

    print(f"\n  [RESPONSE] {json.dumps(response, indent=2)}", flush=True)
    return jsonify(response), 200


# ─── Endpoint 2: MajorLogin ───────────────────────────────────────────────────

@app.route('/MajorLogin', methods=['POST'])
def major_login():
    log_request("/MajorLogin")

    # Use the request's own host so the URL field points back correctly
    host = request.host_url.rstrip('/')

    fake_token = (
        "eyJhbGciOiJIUzI1NiIsInN2ciI6IjMiLCJ0eXAiOiJKV1QifQ"
        ".eyJhY2NvdW50X2lkIjoxNzU1NjA2MzU1MSwibmlja25hbWUiOiJNb2NrVXNlciIsInJlZ2lvbiI6IklORCJ9"
        ".FAKE_SIGNATURE"
    )
    fake_uid_val = 17556063551

    payload  = encode_varint_field(3, fake_uid_val)    # account_uid
    payload += encode_string_field(4, fake_token)       # token
    payload += encode_string_field(10, host)            # url (dynamic)

    print(f"\n  [RESPONSE] Hex: {payload.hex()}", flush=True)
    return Response(payload, status=200, mimetype='application/octet-stream')


# ─── Endpoint 3: GetLoginData ─────────────────────────────────────────────────

@app.route('/GetLoginData', methods=['POST'])
def get_login_data():
    log_request("/GetLoginData")

    host = request.host  # e.g. your-project.vercel.app

    payload  = encode_string_field(14, f"{host}:39698")  # Online_IP_Port
    payload += encode_string_field(16, f"{host}:39800")  # AccountIP_Port
    payload += encode_string_field(6,  "MockPlayer")      # AccountName

    print(f"\n  [RESPONSE] Hex: {payload.hex()}", flush=True)
    return Response(payload, status=200, mimetype='application/octet-stream')


# ─── Catch-all ────────────────────────────────────────────────────────────────

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>',            methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all(path):
    log_request(f"/{path} [UNHANDLED]")
    return jsonify({"status": "captured", "path": path}), 200


# ─── Vercel entry point ───────────────────────────────────────────────────────
# Vercel imports `app` directly — no app.run() needed.
# The block below lets you still test locally with: python api/index.py

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

