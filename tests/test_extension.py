"""Tests the Asyntai Directus extension against a real Directus server.

Directus 11 runs in Docker. The Asyntai API is a stub, so no real account or
key is used. Everything on the Directus side is real: both extensions are
installed, the endpoint runs inside Directus' own sandbox, and the answers
below come back through it.
"""

import json
import time
import urllib.error
import urllib.request

DIRECTUS = "http://127.0.0.1:8077"
STUB = "http://localhost:9000"
ROUTE = "/directus-extension-asyntai-api/ask"
STUB_URL = "http://host.docker.internal:9000"

EMAIL = "admin@example.com"
PASSWORD = "LocalTest2026"

RESULTS = []


def call(url, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print("%-4s %s" % ("PASS" if ok else "FAIL", name))
    if detail:
        print("       %s" % detail)


def ask(token, message, session="t1", api_key="test-key-12345", base=STUB_URL):
    return call(DIRECTUS + ROUTE, {
        "api_key": api_key,
        "message": message,
        "session_id": session,
        "base_url": base,
    }, token=token)


def stub_calls():
    with urllib.request.urlopen(STUB + "/_calls", timeout=20) as r:
        return json.loads(r.read().decode())


def stub_reset():
    urllib.request.urlopen(STUB + "/_reset", timeout=20).read()


def main():
    status, data = call(DIRECTUS + "/auth/login",
                        {"email": EMAIL, "password": PASSWORD})
    token = data["data"]["access_token"]
    print("signed in to Directus\n")

    stub_reset()

    # 1. Three different questions get three different answers.
    questions = [
        "How many vacation days do we get?",
        "How do I claim expenses?",
        "Where are the brand templates?",
    ]
    answers = []
    for q in questions:
        status, body = ask(token, q)
        answers.append(body.get("answer", ""))

    check("a question gets an answer back through Directus",
          all(a for a in answers), answers[0][:80] if answers[0] else "")
    check("each question gets its own answer",
          len(set(answers)) == 3)

    # 2. The request that reaches Asyntai carries the right headers and body.
    calls = stub_calls()
    check("the API key is sent as a Bearer token",
          all(c["auth"] == "Bearer test-key-12345" for c in calls),
          calls[0]["auth"])
    check("the extension identifies itself in the User-Agent",
          all(c["agent"] == "Asyntai-Directus/1.0" for c in calls),
          calls[0]["agent"])
    check("website_id is left out when it is not set",
          all("website_id" not in c["body"] for c in calls))
    check("the session id is passed through",
          all(c["body"]["session_id"] == "t1" for c in calls))

    # 3. Follow-up questions keep their context within one session.
    status, body = ask(token, "How long does it take?")
    check("a follow-up question is answered against the earlier one",
          "Following on from" in body.get("answer", ""),
          body.get("answer", "")[:90])

    # 4. Bad input is refused before any outbound call.
    stub_reset()
    status, body = ask(token, "")
    check("an empty question is refused",
          status == 400 and "error" in body, body.get("error", ""))
    check("an empty question makes no call to Asyntai",
          len(stub_calls()) == 0)

    stub_reset()
    status, body = ask(token, "Anything?", api_key="")
    check("a missing API key is refused",
          status == 400 and "error" in body, body.get("error", ""))
    check("a missing API key makes no call to Asyntai",
          len(stub_calls()) == 0)

    # 5. An API error is reported, not swallowed.
    status, body = ask(token, "make it fail")
    check("an API error is passed back to the panel",
          status == 400 and "limit" in body.get("error", "").lower(),
          body.get("error", ""))

    # 6. A wrong key is rejected by Asyntai and surfaced.
    status, body = ask(token, "Anything?", api_key="wrong-key")
    check("an invalid API key is surfaced",
          status == 400 and "error" in body, body.get("error", ""))

    # 7. The sandbox only allows the URLs the manifest asked for.
    status, body = ask(token, "Anything?", base="https://example.com")
    check("the sandbox blocks a URL outside the requested scope",
          status == 502 and "No permission" in body.get("error", ""),
          body.get("error", "")[:90])

    # 8. Directus itself guards the route.
    status, body = call(DIRECTUS + ROUTE, {"api_key": "x", "message": "hi"})
    check("the route requires a Directus login",
          status in (401, 403), "HTTP %s" % status)

    print()
    passed = sum(1 for _, ok in RESULTS if ok)
    print("%d of %d passed" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
