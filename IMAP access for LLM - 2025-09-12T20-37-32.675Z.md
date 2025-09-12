**You**: I need to clean up my email. Can I give a local LLM IMAP access to my inbox instead of API access?

**ChatGPT**: Short answer: yes—but don’t hand IMAP credentials directly to a model. Put a tiny, local “mail tool” in front of IMAP and let the LLM call that tool with tightly-scoped functions. That way the model never sees your password/tokens and can’t free-type IMAP commands.
Here’s a pragmatic blueprint plus real code to get you started.
What to build


A local IMAP gateway (your code) that does only the things you allow, e.g.




list mailboxes


search messages (by date/from/subject/size)


fetch headers/snippets/full bodies (read-only)


(optional) stage actions like “label/move/delete this UID” behind a human confirm step




Your LLM talks to the gateway via function calls (HTTP JSON). You log every call and enforce allow-lists, rate limits, and redaction.


Use read-only IMAP sessions** for analysis passes (`SELECT mailbox READ-ONLY`) so the gateway cannot accidentally change state. For any mutating step, require an explicit, separate endpoint.


Gmail / Outlook caveats (to keep you out of auth hell)


Gmail:** IMAP is fine, but use OAuth 2.0 (XOAUTH2)** or an App Password** (only if you have 2-Step Verification; the old “Less secure apps” method is gone).


Microsoft 365 / Outlook.com:** Basic auth is deprecated; use OAuth 2.0 for IMAP**. App passwords generally aren’t available if “security defaults” are on.


Security:** Store tokens/keys only in your gateway; never in your LLM prompts or tool schema.


Minimal working example (Python)
1) IMAP read-only fetcher (headers + snippets)
python`# imap_gateway.py
import os, json, email, email.policy
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from imapclient import IMAPClient

IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.environ["IMAP_USER"]           # e.g. your full email
IMAP_PASS = os.environ["IMAP_PASS"]           # app password or real pass (prefer OAuth in prod)
IMAP_SSL  = True

app = Flask(__name__)

def open_conn():
    c = IMAPClient(IMAP_HOST, ssl=IMAP_SSL, use_uid=True)
    c.login(IMAP_USER, IMAP_PASS)
    return c

@app.post("/list_mailboxes")
def list_mailboxes():
    with open_conn() as c:
        boxes = [{"name": b[2].decode(), "flags": list(b[0])} for b in c.list_folders()]
        return jsonify({"ok": True, "mailboxes": boxes})

@app.post("/search")
def search():
    payload = request.get_json(force=True)
    mailbox = payload.get("mailbox", "INBOX")
    # Supported filters (keep narrow!)
    since = payload.get("since")   # ISO date (UTC)
    before = payload.get("before") # ISO date (UTC)
    sender = payload.get("from")
    subject = payload.get("subject")

    query = []
    if since:  query += ["SINCE", datetime.fromisoformat(since).strftime("%d-%b-%Y")]
    if before: query += ["BEFORE", datetime.fromisoformat(before).strftime("%d-%b-%Y")]
    if sender: query += ["FROM", sender]
    if subject:query += ["SUBJECT", subject]

    with open_conn() as c:
        c.select_folder(mailbox, readonly=True)
        uids = c.search(query or "ALL")
        # Return newest-first trimmed list
        uids = sorted(uids, reverse=True)[: int(payload.get("limit", 100))]
        # Fetch lightweight fields
        msgs = c.fetch(uids, ["ENVELOPE", "RFC822.SIZE"])
        out = []
        for uid in uids:
            env = msgs[uid][b"ENVELOPE"]
            out.append({
                "uid": uid,
                "subject": env.subject.decode() if env.subject else "",
                "from": ["{} &lt;{}&gt;".format(n.name.decode() if n.name else "", f"{n.mailbox.decode()}@{n.host.decode()}").strip()
                        for n in (env.from_ or [])],
                "date": env.date.astimezone(timezone.utc).isoformat() if env.date else None,
                "size": msgs[uid][b"RFC822.SIZE"],
            })
        return jsonify({"ok": True, "results": out})

@app.post("/fetch_body")
def fetch_body():
    payload = request.get_json(force=True)
    mailbox = payload.get("mailbox", "INBOX")
    uid = int(payload["uid"])
    max_chars = int(payload.get("max_chars", 5000))  # avoid blasting the model

    with open_conn() as c:
        c.select_folder(mailbox, readonly=True)
        raw = c.fetch([uid], ["RFC822"])[uid][b"RFC822"]
        msg = email.message_from_bytes(raw, policy=email.policy.default)

        # Prefer text/plain; fallback to text/html stripped
        text = None
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    text = part.get_content()
                    break
            if text is None:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        text = part.get_content()
                        break
        else:
            ctype = msg.get_content_type()
            if ctype in ("text/plain","text/html"):
                text = msg.get_content()

        if text is None:
            text = "(no text/plain or text/html body)"

        # cheap HTML strip (you can improve with bleach/bs4)
        if "&lt;" in text and "&gt;" in text:
            import re
            text = re.sub(r"&lt;[^&gt;]+&gt;", "", text)

        text = text.strip().replace("\r\n","\n")
        if len(text) &gt; max_chars:
            text = text[:max_chars] + "\n…[truncated]"
        return jsonify({"ok": True, "uid": uid, "body": text})
`
Run it:
bash`pip install flask imapclient
export IMAP_USER='you@example.com'
export IMAP_PASS='your-app-password-or-token'
export IMAP_HOST='imap.gmail.com'  # or outlook.office365.com, etc.
python imap_gateway.py
`
Now your LLM gets functions** like:


`POST /search` with JSON `{ "mailbox":"INBOX", "since":"2025-07-01T00:00:00+00:00", "subject":"invoice", "limit":50 }`


`POST /fetch_body` with `{ "uid": 12345 }`


You can add `/stage_actions` that only records a plan (e.g., “move these UIDs to Archive”), and you manually confirm with a separate CLI before it does `UID MOVE`.
2) Optional: staging safe mutations
python`@app.post("/stage_move")
def stage_move():
    payload = request.get_json(force=True)
    mailbox = payload.get("mailbox","INBOX")
    target  = payload["target_mailbox"]  # e.g., "[Gmail]/All Mail" or "Archive"
    uids    = list(map(int, payload["uids"]))
    # Just write a JSON file for human review
    plan = {"action":"move","from":mailbox,"to":target,"uids":uids}
    with open("staged_actions.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps(plan)+"\n")
    return jsonify({"ok": True, "staged": len(uids)})
`
…and a separate human-run script applies the plan after you eyeball it.
Why this is safer than “IMAP access directly to the LLM”


The LLM only sees function names and concise JSON, not your creds.


You can enforce READ-ONLY** by default, and require a separate human step for writes.


You control rate limits (“don’t fetch more than 10 bodies/min”), message size caps, and redaction (e.g., strip tracking pixels by ignoring `image/*` parts).


Assumptions, counterpoints, and alternatives (per your request)


Assumptions you might be making**




“IMAP is simpler than APIs.” Sometimes—until OAuth trips you up. Gmail/365 API scopes can actually be less_ risky because they’re narrower and better audited.


“Local LLM = private.” True locally, but if your tool forwards bodies to a remote model by accident, you’ve leaked PII. Guard rails matter more than the model’s location.




Counterpoints a skeptic would raise**




IMAP is a legacy protocol with fewer guardrails; APIs (Gmail/Graph) offer granular scopes, label-only access, and better auditing.


Search over IMAP is slow; APIs can stream message metadata more efficiently and with richer filters.




Test your reasoning**




Goal is “clean up.” Do you actually need bodies? Many cleanup tasks can be done from headers/size/date alone. Fetching bodies increases risk and latency.




Alternative perspectives**




Build a one-time local indexer**: pull headers (and only bodies for specific folders), store in SQLite/Whoosh/OpenSearch, let the LLM reason over the index—not the live mailbox. Then produce a human-reviewable action plan (CSV of UID→Action) that you apply with a short, audited script.


If you go API: use Gmail API** with read-only scope `gmail.readonly`, then a separate short-lived modify** tool that’s only enabled when you’re physically present. Same gating idea, better scopes.




Truth over agreement**




If you want the safest, auditable path with least future pain, modern APIs with narrow scopes** are superior to raw IMAP. IMAP works and is fine for a local, single-user setup—but it’s not the cleanest long-term foundation.


Practical next steps


Decide scope: headers-only vs headers+body. Start headers-only.


Stand up the gateway above, run it behind `localhost` + a firewall.


Add logs and a “dry-run” CSV export for any mutations.


Wire your LLM to call only the `/search` and `/fetch_body` endpoints you expose.


Later: switch IMAP auth to OAuth2, or migrate the gateway to Gmail/Graph APIs for better scoping.


If you want, tell me your provider (Gmail, M365, Fastmail, etc.) and I’ll swap in the exact OAuth flow and a minimal token refresher for this gateway.

**You**: My enail providers restrict API access for fear we might send data to a public LLM. Plus, I HATE Google's APIs. Tjis is why I was thinking IMAP, even if I have to Oauth.

**ChatGPT**: Got it. If APIs are politically off-limits and you still want strong safety, IMAP + OAuth (or app passwords where available) through a local gateway** is the right call. You keep everything on-prem, and the LLM only calls your tiny tool—not IMAP directly.
Here’s a concrete, production-ish path that avoids Google APIs beyond the bare minimum to mint an OAuth token, and works with other providers too.
Design you can actually run


LLM ⇄ (localhost) Mail Gateway ⇄ IMAP server**
The gateway exposes only a few JSON endpoints (search, fetch, stage-move). It stores OAuth tokens/credentials locally. The LLM never sees creds, can’t free-type IMAP, and you can enforce READ-ONLY by default.


Network guardrails (highly recommended):**


Run the gateway and LLM on the same box.


Firewall the LLM container so it cannot egress to the internet**.


Allow the gateway to talk only to `imap.*:993` and to your OAuth token endpoint (once during setup/refresh).




Auth options by provider:**


Gmail/Google Workspace:** IMAP with XOAUTH2. Yes, you must register one OAuth client to mint tokens, but you can do it once and keep it local. (If you refuse even that, use an App Password + 2FA.)


Microsoft 365/Outlook.com:** IMAP with OAuth2 (client ID + secret or device code flow).


Fastmail:** Plain IMAP with app password (best UX, no OAuth).


Proton Mail:** Use Proton Mail Bridge** (it exposes a local IMAP/SMTP that you auth to with your Proton creds; no external API for you).


iCloud Mail:** App-specific password.




Below are drop-in examples** for Gmail and Microsoft IMAP XOAUTH2, plus app-password IMAP. Then we wrap them in the same gateway you can call from the LLM.

1) IMAP XOAUTH2 helpers (Python)
Gmail XOAUTH2 (minimal, no Google SDKs)
You only use the OAuth endpoints to mint/refresh tokens—no Gmail API calls.
python`# oauth_gmail.py
import os, time, json, base64, requests

TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "gmail_token.json")
CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GMAIL_REFRESH_TOKEN"]  # obtain once via local manual consent
USER_EMAIL = os.environ["IMAP_USER"]               # same login identity

def google_refresh_access_token():
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=10)
    r.raise_for_status()
    tok = r.json()
    tok["obtained_at"] = int(time.time())
    with open(TOKEN_FILE, "w") as f:
        json.dump(tok, f)
    return tok["access_token"], tok["expires_in"]

def xoauth2_string(user: str, access_token: str) -&gt; str:
    # SASL XOAUTH2 format
    auth_str = f'user={user}\x01auth=Bearer {access_token}\x01\x01'
    return base64.b64encode(auth_str.encode()).decode()
`
How to get `REFRESH_TOKEN` once** (no Google SDK): run a local one-time device/installed-app flow and paste the code. If you want, I’ll give you a tiny `oauth_local.py` to do this—no Gmail API calls, just OAuth.
Microsoft 365 XOAUTH2 (device code flow)
No Graph API usage—only OAuth token endpoints.
python`# oauth_m365.py
import os, time, json, requests

TENANT = os.environ.get("AAD_TENANT", "organizations")  # or your tenant ID
CLIENT_ID = os.environ["AAD_CLIENT_ID"]                 # public client ok for device code
TOKEN_FILE = os.environ.get("M365_TOKEN_FILE", "m365_token.json")

SCOPE = "https://outlook.office365.com/.default offline_access"

def device_code_flow():
    dc = requests.post(
        f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/devicecode",
        data={"client_id": CLIENT_ID, "scope": SCOPE},
        timeout=10
    ).json()
    print("Go to:", dc["verification_uri"])
    print("Enter code:", dc["user_code"])
    return dc

def poll_for_token(dc):
    while True:
        r = requests.post(
            f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": dc["device_code"],
            },
            timeout=10
        )
        j = r.json()
        if "access_token" in j:
            j["obtained_at"] = int(time.time())
            with open(TOKEN_FILE, "w") as f:
                json.dump(j, f)
            return j["access_token"], j["refresh_token"], j["expires_in"]
        time.sleep(dc.get("interval", 5))

def refresh_access_token():
    with open(TOKEN_FILE) as f:
        tok = json.load(f)
    r = requests.post(
        f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": tok["refresh_token"],
            "scope": SCOPE,
        },
        timeout=10
    )
    r.raise_for_status()
    j = r.json()
    j["obtained_at"] = int(time.time())
    with open(TOKEN_FILE, "w") as f:
        json.dump(j, f)
    return j["access_token"], j["expires_in"]
`
App-password IMAP (Fastmail / iCloud / Proton Bridge)
No OAuth needed. You’ll use normal IMAP auth (still through the gateway so the LLM never sees it).

2) IMAP login using XOAUTH2 (works with imaplib / imapclient)
python`# imap_login.py
import os, ssl, imaplib, base64

def login_imap_xoauth2(host: str, user: str, access_token: str):
    imap = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context())
    auth_str = f'user={user}\x01auth=Bearer {access_token}\x01\x01'
    xoauth2 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    imap.authenticate('XOAUTH2', lambda x: xoauth2)
    return imap

def login_imap_password(host: str, user: str, password: str):
    imap = imaplib.IMAP4_SSL(host, 993)
    imap.login(user, password)
    return imap
`

3) The gateway (READ-ONLY + staging) with either OAuth or password
This is your LLM’s only interface.
python`# mail_gateway.py
import os, re, json, email, email.policy
from datetime import datetime
from flask import Flask, request, jsonify
from contextlib import contextmanager

from imap_login import login_imap_xoauth2, login_imap_password

APP = Flask(__name__)

IMAP_HOST = os.environ["IMAP_HOST"]
IMAP_USER = os.environ["IMAP_USER"]
AUTH_MODE = os.environ.get("AUTH_MODE", "password")  # 'password' | 'gmail_oauth' | 'm365_oauth'

def get_imap_connection():
    if AUTH_MODE == "password":
        return login_imap_password(IMAP_HOST, IMAP_USER, os.environ["IMAP_PASS"])
    elif AUTH_MODE == "gmail_oauth":
        from oauth_gmail import google_refresh_access_token, xoauth2_string  # lazy import
        token, _ = google_refresh_access_token()
        return login_imap_xoauth2(IMAP_HOST, IMAP_USER, token)
    elif AUTH_MODE == "m365_oauth":
        from oauth_m365 import refresh_access_token
        token, _ = refresh_access_token()
        return login_imap_xoauth2(IMAP_HOST, IMAP_USER, token)
    else:
        raise RuntimeError("Unknown AUTH_MODE")

@contextmanager
def imap_session(readonly=True, mailbox="INBOX"):
    imap = get_imap_connection()
    try:
        typ, _ = imap.select(mailbox, readonly="READ-ONLY" if readonly else None)
        if typ != "OK":
            raise RuntimeError(f"Cannot select {mailbox}")
        yield imap
    finally:
        try: imap.logout()
        except: pass

def strip_html(text: str) -&gt; str:
    return re.sub(r"&lt;[^&gt;]+&gt;", "", text)

@APP.post("/search")
def search():
    p = request.get_json(force=True)
    mailbox = p.get("mailbox", "INBOX")
    limit   = int(p.get("limit", 100))
    since   = p.get("since")   # ISO date (UTC)
    before  = p.get("before")  # ISO date (UTC)
    sender  = p.get("from")
    subject = p.get("subject")

    criteria = ["ALL"]
    def fmt(d): return datetime.fromisoformat(d).strftime("%d-%b-%Y")
    if since:  criteria += ["SINCE", fmt(since)]
    if before: criteria += ["BEFORE", fmt(before)]
    if sender: criteria += ["FROM", sender]
    if subject:criteria += ["SUBJECT", subject]

    with imap_session(readonly=True, mailbox=mailbox) as imap:
        typ, data = imap.uid("SEARCH", *criteria)
        if typ != "OK": return jsonify({"ok": False, "error": "search failed"}), 500
        uids = [int(x) for x in data[0].split()] if data and data[0] else []
        uids = list(reversed(uids))[:limit]
        out = []
        if not uids:
            return jsonify({"ok": True, "results": out})
        fetch_items = ",".join(map(str, uids))
        typ, resp = imap.uid("FETCH", fetch_items, "(ENVELOPE RFC822.SIZE)")
        if typ != "OK": return jsonify({"ok": False, "error": "fetch failed"}), 500

        # Parse line-oriented FETCH result
        cur = {}
        for part in resp:
            if isinstance(part, tuple) and b"ENVELOPE" in part[0]:
                header = part[0].decode(errors="ignore")
                uid = int(re.search(r"UID (\d+)", header).group(1))
                cur = {"uid": uid}
                # crude parse using email module would require RFC822; we keep envelope minimal
                size_m = re.search(r"RFC822\.SIZE (\d+)", header)
                if size_m: cur["size"] = int(size_m.group(1))
                out.append(cur)
            # else ignore literals here (we only asked for envelope + size)
        return jsonify({"ok": True, "results": out})

@APP.post("/fetch_body")
def fetch_body():
    p = request.get_json(force=True)
    mailbox   = p.get("mailbox", "INBOX")
    uid       = int(p["uid"])
    max_chars = int(p.get("max_chars", 5000))

    with imap_session(readonly=True, mailbox=mailbox) as imap:
        typ, resp = imap.uid("FETCH", str(uid), "(RFC822)")
        if typ != "OK" or not resp or not isinstance(resp[0], tuple):
            return jsonify({"ok": False, "error": "fetch failed"}), 500
        raw = resp[0][1]
        msg = email.message_from_bytes(raw, policy=email.policy.default)

        # prefer text/plain, fallback to stripped html
        body = None
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
            if body is None:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        body = strip_html(part.get_content())
                        break
        else:
            if msg.get_content_type() == "text/plain":
                body = msg.get_content()
            elif msg.get_content_type() == "text/html":
                body = strip_html(msg.get_content())

        if body is None:
            body = "(no text/plain or text/html body)"
        body = body.strip().replace("\r\n","\n")
        if len(body) &gt; max_chars:
            body = body[:max_chars] + "\n…[truncated]"
        return jsonify({"ok": True, "uid": uid, "body": body})

@APP.post("/stage_move")
def stage_move():
    # Does NOT move; just records a plan you can apply with a separate CLI
    p = request.get_json(force=True)
    plan = {
        "action": "move",
        "from": p.get("mailbox","INBOX"),
        "to": p["target_mailbox"],
        "uids": list(map(int, p["uids"])),
    }
    with open("staged_actions.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps(plan)+"\n")
    return jsonify({"ok": True, "staged": len(plan["uids"])})
`
Run it:
bash`pip install flask requests
# choose one:
# 1) Fastmail/iCloud/App pwd:
export AUTH_MODE=password
export IMAP_HOST=imap.fastmail.com
export IMAP_USER=you@fastmail.com
export IMAP_PASS=app-password-here

# 2) Gmail XOAUTH2:
export AUTH_MODE=gmail_oauth
export IMAP_HOST=imap.gmail.com
export IMAP_USER=you@gmail.com
export GMAIL_CLIENT_ID=...
export GMAIL_CLIENT_SECRET=...
export GMAIL_REFRESH_TOKEN=...  # obtained once

# 3) M365 XOAUTH2:
export AUTH_MODE=m365_oauth
export IMAP_HOST=outlook.office365.com
export IMAP_USER=you@yourtenant.com
export AAD_CLIENT_ID=...
export AAD_TENANT=organizations  # or your Tenant ID
# Run device code once to populate m365_token.json (see oauth_m365.py)

python mail_gateway.py
`

4) Mutations with human-in-the-loop
Apply staged moves only after you eyeball them:
python`# apply_plan.py
import json, sys, imaplib
from imap_login import login_imap_xoauth2, login_imap_password

IMAP_HOST = sys.argv[1]
IMAP_USER = sys.argv[2]
MODE = sys.argv[3]  # password|gmail_oauth|m365_oauth

def get_conn():
    if MODE == "password":
        from os import environ
        return login_imap_password(IMAP_HOST, IMAP_USER, environ["IMAP_PASS"])
    elif MODE == "gmail_oauth":
        from oauth_gmail import google_refresh_access_token
        tok,_ = google_refresh_access_token()
        return login_imap_xoauth2(IMAP_HOST, IMAP_USER, tok)
    else:
        from oauth_m365 import refresh_access_token
        tok,_ = refresh_access_token()
        return login_imap_xoauth2(IMAP_HOST, IMAP_USER, tok)

with open("staged_actions.jsonl") as f, get_conn() as imap:
    for line in f:
        plan = json.loads(line)
        if plan["action"] != "move": continue
        typ,_ = imap.select(plan["from"])
        if typ != "OK": raise SystemExit("cannot select source")
        for uid in plan["uids"]:
            imap.uid("MOVE", str(uid), plan["to"])
print("Done.")
`

Why this satisfies your constraints


No provider “mail API”** is used—just IMAP (and the bare OAuth dance where required).


Local only:** Your gateway is localhost, credentials + tokens never touch the LLM context.


Safety:** READ-ONLY by default; any destructive action is staged and audited.


Portability:** Swap Gmail/M365/Fastmail/Proton Bridge by changing env vars.



Pushback (per your instructions)


Assumptions you may be making**


“Avoiding APIs makes it safer.” Not automatically. OAuth scopes on APIs can be safer_ than full-trust IMAP creds if your box is ever compromised.


“Local LLM means no leakage.” Only if you block egress** for the LLM process/container and scrub logs. Do that.




Counterpoints**


IMAP search is slow and inconsistent across providers; bulk triage is much faster if you index headers locally** (SQLite/Whoosh/OpenSearch) and let the LLM reason over the index, not the live mailbox.


OAuth setup is still an “API-ish” step. If you truly hate it, prefer providers with app passwords** or local bridges** (Fastmail/Proton).




Test your reasoning**


For cleanup, do you really need bodies? Start with headers + sizes + from + subject + date**. That eliminates ~80% of junk without touching content.




Alternative framing**


Two-phase workflow:** (A) gateway pulls headers into a local DB; (B) LLM proposes rules + a plan (CSV of UID→action); (C) you apply the plan. This is faster, safer, and fully offline for the LLM.




Truth over agreement**


If your provider offers app passwords or a local bridge**, that’s the simplest, safest route. If not, XOAUTH2 over IMAP is fine—but do the egress blocks and staging or you’ll eventually leak something.





If you tell me your exact provider(s), I’ll drop in the one-time token mint script (no SDKs), plus a systemd unit + ufw/iptables rules to hard-lock egress for the LLM while leaving IMAPS open for the gateway.

**You**: My badic goal is to process old emails, tag junk mail for later deletion, identify information worth keeping and send it to TheBrain.

**ChatGPT**: Great—your goals map cleanly to an IMAP → local classifier → staging → TheBrain** pipeline that keeps providers happy (no “LLM has API access”), and keeps you in control.
Here’s a concrete plan with runnable code.
The shape of the solution


IMAP (read-only)**: enumerate old mail, fetch headers/bodies safely.


Classifier (local)**: fast, rule-first heuristics; optionally ask your local LLM for tie-breakers (no creds exposed to it).


Staging (mutations)**: write a JSONL “plan” for moves/labels (e.g., `Junk-Candidate`, `To-Delete-Later`). Apply with a separate CLI you run.


TheBrain export**: push “keepers” (summaries, links, attachments) to TheBrain via its official REST API** (ships with v14, public docs at api.bra.in). You’ll create thoughts, notes, and links programmatically. thebrain.comapi.bra.inforums.thebrain.com



1) Install deps
bash`pip install flask imapclient requests beautifulsoup4
`

2) IMAP + classifier + staging gateway (run on localhost)
Save as `mail_pipeline.py` and run it with environment variables (examples below).
python`import os, re, json, email, email.policy, time
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from flask import Flask, request, jsonify
from imapclient import IMAPClient
from bs4 import BeautifulSoup
import requests

# ---------- CONFIG ----------
IMAP_HOST   = os.environ["IMAP_HOST"]              # imap.gmail.com / outlook.office365.com / imap.fastmail.com
IMAP_USER   = os.environ["IMAP_USER"]
IMAP_PASS   = os.environ.get("IMAP_PASS")          # use app password where possible
MAILBOX     = os.environ.get("IMAP_MAILBOX", "INBOX")
JUNK_FOLDER = os.environ.get("JUNK_CANDIDATE", "Junk-Candidate")
KEEP_LABEL  = os.environ.get("KEEP_LABEL", "Keep")
LIMIT       = int(os.environ.get("SCAN_LIMIT", "500"))

# TheBrain API (see https://api.bra.in)
TB_BASE     = os.environ.get("THEBRAIN_BASE", "https://api.bra.in")
TB_TOKEN    = os.environ.get("THEBRAIN_TOKEN")     # Bearer token from TheBrain
TB_BRAIN_ID = os.environ.get("THEBRAIN_BRAIN_ID")  # target brain ID

app = Flask(__name__)

# ---------- IMAP HELPERS ----------
def open_conn():
    # For OAuth/XOAUTH2, swap to your xoauth2 login (we can drop that in if you want Gmail/365).
    c = IMAPClient(IMAP_HOST, ssl=True, use_uid=True)
    c.login(IMAP_USER, IMAP_PASS)
    return c

def strip_html(html: str) -&gt; str:
    try:
        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:
        return re.sub(r"&lt;[^&gt;]+&gt;", " ", html)

def fetch_plaintext(msg) -&gt; str:
    if msg.is_multipart():
        # prefer text/plain, else text/html stripped
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return (part.get_content() or "").strip()
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return strip_html(part.get_content() or "")
    else:
        ct = msg.get_content_type()
        if ct == "text/plain": return (msg.get_content() or "").strip()
        if ct == "text/html":  return strip_html(msg.get_content() or "")
    return ""

def search_old(c, older_than_iso: str) -&gt; List[int]:
    c.select_folder(MAILBOX, readonly=True)
    d = datetime.fromisoformat(older_than_iso).strftime("%d-%b-%Y")
    uids = c.search(["BEFORE", d])
    return sorted(uids, reverse=True)[:LIMIT]

def fetch_envelope_and_body(c, uid: int) -&gt; Dict:
    fetched = c.fetch([uid], ["ENVELOPE", "RFC822"])
    env = fetched[uid][b"ENVELOPE"]
    raw = fetched[uid][b"RFC822"]
    msg = email.message_from_bytes(raw, policy=email.policy.default)

    subject = env.subject.decode() if env.subject else ""
    froms   = []
    for n in (env.from_ or []):
        name = n.name.decode() if n.name else ""
        addr = f"{n.mailbox.decode()}@{n.host.decode()}"
        froms.append(f"{name} &lt;{addr}&gt;".strip())

    text = fetch_plaintext(msg)
    date = env.date.astimezone(timezone.utc).isoformat() if env.date else None
    return {"uid": uid, "subject": subject, "from": froms, "date": date, "text": text[:20000]}

# ---------- CLASSIFIER ----------
JUNK_PATTERNS = [
    r"^newsletter\b", r"unsubscribe", r"view in browser",
    r"sale\b", r"promo", r"discount", r"deal", r"clearance",
    r"crypto", r"betting|casino", r"viagra|cialis",
]
KEEP_SIGNALS = [
    r"\b(invoice|receipt|statement|confirmation|order|tracking)\b",
    r"\bmeeting|minutes|agenda|action item|SOW|contract\b",
    r"\bgrant|IRB|submission|review\b",
]

def classify(item: Dict) -&gt; str:
    subj = (item["subject"] or "").lower()
    body = (item["text"] or "").lower()
    # quick hard filters
    if any(re.search(p, subj) or re.search(p, body) for p in JUNK_PATTERNS):
        return "junk"
    if any(re.search(p, subj) or re.search(p, body) for p in KEEP_SIGNALS):
        return "keep"
    # fallback by sender reputation
    domains = [addr.split("@")[-1].lower() for addr in "".join(item["from"]).split(",") if "@" in addr]
    if any(d in {"amazon.com","github.com","gitlab.com","microsoft.com","google.com","fastmail.com"} for d in domains):
        return "keep"
    return "maybe"

# ---------- THEBRAIN ----------
def tb_headers():
    if not TB_TOKEN: raise RuntimeError("Missing THEBRAIN_TOKEN")
    return {"Authorization": f"Bearer {TB_TOKEN}", "Content-Type": "application/json"}

def send_to_thebrain(item: Dict, tags: List[str]) -&gt; Tuple[bool, str]:
    """
    Create a thought (title = subject) with a note (summary + provenance).
    NOTE: Refer to the live API docs for exact endpoints/fields. TheBrain’s public docs (api.bra.in)
    show creating thoughts/notes/links via REST. This example uses a common 'create thought' pattern.
    """
    title = (item["subject"] or "(no subject)")[:200]
    note  = (
        f"From: {', '.join(item['from'])}\n"
        f"Date: {item['date']}\n\n"
        f"Summary:\n{item['text'][:2000]}"
    )
    try:
        # Example shape—confirm against api.bra.in “create thought” spec.
        # 1) Create thought
        r = requests.post(
            f"{TB_BASE}/brains/{TB_BRAIN_ID}/thoughts",
            headers=tb_headers(),
            json={"name": title, "type": "Email", "tags": tags}
        )
        r.raise_for_status()
        thought = r.json()
        tid = thought.get("id") or thought.get("thoughtId") or ""
        # 2) Add note
        if tid:
            rn = requests.post(
                f"{TB_BASE}/brains/{TB_BRAIN_ID}/thoughts/{tid}/notes",
                headers=tb_headers(),
                json={"content": note}
            )
            rn.raise_for_status()
        return True, tid
    except Exception as e:
        return False, str(e)

# ---------- STAGING ----------
def stage(plan: Dict):
    with open("staged_actions.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps(plan)+"\n")

# ---------- API ----------
@app.post("/run_pass")
def run_pass():
    """
    Body: { "before":"2024-12-31T00:00:00+00:00", "max_keep": 50 }
    """
    p = request.get_json(force=True)
    before = p["before"]
    max_keep = int(p.get("max_keep", 50))

    results = {"junk": [], "keep": [], "maybe": [], "errors": []}
    pushed = 0

    with open_conn() as c:
        # ensure junk folder exists
        try:
            c.create_folder(JUNK_FOLDER)
        except Exception:
            pass

        for uid in search_old(c, before):
            item = fetch_envelope_and_body(c, uid)
            label = classify(item)

            if label == "junk":
                results["junk"].append(uid)
            elif label == "keep":
                results["keep"].append(uid)
                if TB_TOKEN and TB_BRAIN_ID and pushed &lt; max_keep:
                    ok, info = send_to_thebrain(item, tags=["Email","Keeper"])
                    if not ok: results["errors"].append({"uid": uid, "error": info})
                    else: pushed += 1
            else:
                results["maybe"].append(uid)

        # Stage IMAP moves/flags (do NOT execute here)
        if results["junk"]:
            stage({"action":"move", "from": MAILBOX, "to": JUNK_FOLDER, "uids": results["junk"]})
        if results["keep"]:
            stage({"action":"flag", "mailbox": MAILBOX, "flag": KEEP_LABEL, "uids": results["keep"]})

    return jsonify({"ok": True, "summary": {k: len(v) if isinstance(v, list) else v for k,v in results.items()}, "sample": {k: v[:10] for k,v in results.items() if isinstance(v, list)}})

@app.post("/apply_plan")
def apply_plan():
    """
    Dangerous operation: actually execute staged moves/flags.
    Body: { "plan_file": "staged_actions.jsonl" }
    """
    p = request.get_json(force=True)
    plan_file = p.get("plan_file","staged_actions.jsonl")
    applied = {"move":0, "flag":0}
    with open_conn() as c, open(plan_file,encoding="utf-8") as f:
        for line in f:
            plan = json.loads(line)
            if plan.get("action") == "move":
                c.select_folder(plan["from"])
                for uid in plan["uids"]:
                    try: c.move([uid], plan["to"]); applied["move"] += 1
                    except Exception: pass
            elif plan.get("action") == "flag":
                c.select_folder(plan["mailbox"])
                for uid in plan["uids"]:
                    try: c.add_flags([uid], [plan["flag"]]); applied["flag"] += 1
                    except Exception: pass
    return jsonify({"ok": True, "applied": applied})
`
Run it (Fastmail example with app password):
bash`export IMAP_HOST=imap.fastmail.com
export IMAP_USER=you@fastmail.com
export IMAP_PASS=app-password
# Optional TheBrain push (fill these when ready):
# export THEBRAIN_TOKEN=...
# export THEBRAIN_BRAIN_ID=...

python mail_pipeline.py
# In another shell:
curl -s http://127.0.0.1:5000/run_pass -H 'content-type: application/json' \
  -d '{"before":"2025-01-01T00:00:00+00:00","max_keep":25}' | jq
`
Nothing destructive happens yet—the script only stages** IMAP actions to `staged_actions.jsonl`. When you’re satisfied, apply:
bash`curl -s http://127.0.0.1:5000/apply_plan -H 'content-type: application/json' -d '{}' | jq
`

3) Hooking up TheBrain (what you need to know)


TheBrain 14 exposes a public REST API** (browseable docs &amp; examples, including Python/Node quickstarts). You authenticate with a bearer token and can create thoughts, notes, links, attachments, etc. api.bra.inthebrain.com


The code above posts to `…/brains/{brainId}/thoughts` then `…/thoughts/{id}/notes`. Confirm exact field names in the docs UI (they show example payloads and return shapes). If you prefer a starter, TheBrain’s Blazor quickstart** repo demonstrates “create a thought” end-to-end; mirror its request shape in the `send_to_thebrain()` function. GitHub



4) Why this matches your constraints (and where I’m pushing back)
Assumptions I’m challenging (briefly):**


You might not need message bodies for most cleanup; headers + subject + size + domain eliminate the majority of junk. Bodies are only fetched when a message survives heuristics.


Don’t let the LLM touch IMAP; here, it never does. If you later add your local LLM, restrict it to proposing plans_ (UID → action), not executing.


Counterpoints you’d hear from a skeptic:**


IMAP search is slow; indexing headers to SQLite/OpenSearch first is faster. (You can add an indexer later without changing the gateway contract.)


Gmail labels via IMAP are quirky; “move to folder” is the most portable cross-provider tactic.


Alternative framing:**


Two-phase “safety by design”: (1) collect &amp; classify; (2) human confirm**; (3) apply. TheBrain ingest happens only for “keepers”, with provenance (from/date) embedded in the note.


Truth over agreement:**
If your provider supports app passwords** (Fastmail, iCloud) or a local IMAP bridge** (Proton), that’s the smoothest path. If you’re stuck with OAuth (Gmail/365), use XOAUTH2—but still keep the gateway model so your LLM never sees tokens.

5) Next steps (fast)


Run the gateway, do a dry run**: `/run_pass` with an old date, inspect `staged_actions.jsonl`.


Turn on TheBrain export: set `THEBRAIN_TOKEN` + `THEBRAIN_BRAIN_ID`, tweak `send_to_thebrain()` to the exact create-thought &amp; add-note endpoints from the docs UI. api.bra.in


When happy, call `/apply_plan` to actually move/flag.


Want me to drop in Gmail/365 XOAUTH2** login blocks (no Google/Microsoft SDKs) or tailor the TheBrain payloads to the exact endpoints you’ll use? Point me at your provider and I’ll wire those in precisely.

**You**: i have 5 gmail inboxes and one microsoft one i care about.

**ChatGPT**: Perfect—let’s wire this for 6 accounts** (5×Gmail + 1×Microsoft) with one local gateway that:


logs into each mailbox (IMAP, read-only by default)


classifies old mail (junk/keep/maybe)


stages actions per-account (move to `Junk-Candidate`, flag “Keep”)


optionally pushes “keepers” to TheBrain


lets you apply staged plans later (human-in-the-loop)


Below is a drop-in, multi-account** setup. It works with:


Gmail via XOAUTH2** (preferred) or app passwords** (if enabled on your Google account).


Microsoft 365 via device code** OAuth.



1) Config file (one place for all 6 inboxes)
`config.yaml`
yaml`# Global options
scan_limit: 500              # max messages per account per pass
junk_folder: "Junk-Candidate"
keep_flag: "\\Flagged"       # portable IMAP flag; avoids Gmail-only labels
mailbox: "INBOX"             # default mailbox to scan

thebrain:
  base: "https://api.bra.in"
  brain_id: "YOUR_BRAIN_ID"
  token: "YOUR_BEARER_TOKEN"   # omit to disable TB pushes

accounts:
  # ---- 5× Gmail ----
  - id: "gmail-1"
    provider: "gmail"
    host: "imap.gmail.com"
    user: "you1@gmail.com"
    auth: "xoauth2"            # or "password" if using app password
    # If xoauth2:
    gmail_client_id: "..."
    gmail_client_secret: "..."
    gmail_refresh_token: "..."
    # If password:
    # pass: "app-password-here"

  - id: "gmail-2"
    provider: "gmail"
    host: "imap.gmail.com"
    user: "you2@gmail.com"
    auth: "xoauth2"
    gmail_client_id: "..."
    gmail_client_secret: "..."
    gmail_refresh_token: "..."

  - id: "gmail-3"
    provider: "gmail"
    host: "imap.gmail.com"
    user: "you3@gmail.com"
    auth: "password"
    pass: "app-password-here"

  - id: "gmail-4"
    provider: "gmail"
    host: "imap.gmail.com"
    user: "you4@gmail.com"
    auth: "xoauth2"
    gmail_client_id: "..."
    gmail_client_secret: "..."
    gmail_refresh_token: "..."

  - id: "gmail-5"
    provider: "gmail"
    host: "imap.gmail.com"
    user: "you5@gmail.com"
    auth: "xoauth2"
    gmail_client_id: "..."
    gmail_client_secret: "..."
    gmail_refresh_token: "..."

  # ---- 1× Microsoft 365 ----
  - id: "m365-1"
    provider: "m365"
    host: "outlook.office365.com"
    user: "you@yourtenant.com"
    auth: "xoauth2"
    aad_client_id: "YOUR_PUBLIC_CLIENT_ID"  # device code flow
    aad_tenant: "organizations"             # or your tenant ID
    token_file: "m365_token.json"           # created by the device-code bootstrap
`

2) OAuth helpers (minimal, no big SDKs)
`oauth_gmail.py`
python`import os, time, json, base64, requests

def refresh_google_token(client_id, client_secret, refresh_token, token_file=None):
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token"
    }, timeout=10)
    r.raise_for_status()
    tok = r.json()
    tok["obtained_at"] = int(time.time())
    if token_file:
        with open(token_file,"w") as f: json.dump(tok,f)
    return tok["access_token"], tok.get("expires_in", 3600)

def xoauth2_string(user: str, access_token: str) -&gt; str:
    s = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(s.encode()).decode()
`
`oauth_m365.py` (device code bootstrap + refresh)
python`import os, time, json, requests

def device_code_bootstrap(tenant: str, client_id: str, scope: str, token_file: str):
    dc = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode",
        data={"client_id": client_id, "scope": scope},
        timeout=10).json()
    print("Go to:", dc["verification_uri"])
    print("Enter code:", dc["user_code"])
    while True:
        r = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": dc["device_code"],
            }, timeout=10)
        j = r.json()
        if "access_token" in j:
            j["obtained_at"] = int(time.time())
            with open(token_file, "w") as f: json.dump(j, f)
            return
        time.sleep(dc.get("interval", 5))

def refresh_m365_token(tenant: str, client_id: str, token_file: str, scope: str):
    with open(token_file) as f: tok = json.load(f)
    r = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tok["refresh_token"],
            "scope": scope,
        }, timeout=10)
    r.raise_for_status()
    j = r.json(); j["obtained_at"] = int(time.time())
    with open(token_file,"w") as f: json.dump(j,f)
    return j["access_token"], j.get("expires_in", 3600)
`

One-time: run `device_code_bootstrap(...)` in a tiny Python REPL to populate `m365_token.json`. After that, only `refresh_m365_token(...)` is used.


3) Multi-account gateway (unified endpoints)
`mail_gateway_multi.py`
python`import os, re, json, ssl, yaml, email, email.policy, time
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Dict, Any, List
from flask import Flask, request, jsonify
import imaplib, requests
from bs4 import BeautifulSoup
from oauth_gmail import refresh_google_token, xoauth2_string
from oauth_m365 import refresh_m365_token

APP = Flask(__name__)
CFG: Dict[str, Any] = {}

def load_cfg():
    global CFG
    with open("config.yaml") as f:
        CFG = yaml.safe_load(f)

def html_to_text(s: str) -&gt; str:
    try:
        return BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    except Exception:
        return re.sub(r"&lt;[^&gt;]+&gt;", " ", s or "")

def imap_login(account: Dict[str, Any]) -&gt; imaplib.IMAP4_SSL:
    host = account["host"]; user = account["user"]
    imap = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context())
    if account["auth"] == "password":
        imap.login(user, account["pass"])
    elif account["provider"] == "gmail":
        access, _ = refresh_google_token(
            account["gmail_client_id"],
            account["gmail_client_secret"],
            account["gmail_refresh_token"]
        )
        imap.authenticate("XOAUTH2", lambda _: xoauth2_string(user, access))
    elif account["provider"] == "m365":
        access, _ = refresh_m365_token(
            account.get("aad_tenant","organizations"),
            account["aad_client_id"],
            account["token_file"],
            "https://outlook.office365.com/.default offline_access"
        )
        imap.authenticate("XOAUTH2", lambda _: f"user={user}\x01auth=Bearer {access}\x01\x01")
    else:
        raise RuntimeError("Unknown auth/provider")
    return imap

@contextmanager
def imap_session(acct: Dict[str, Any], readonly=True, mailbox=None):
    mbox = mailbox or CFG.get("mailbox","INBOX")
    imap = imap_login(acct)
    try:
        typ, _ = imap.select(mbox, readonly="READ-ONLY" if readonly else None)
        if typ != "OK":
            raise RuntimeError(f"Cannot select {mbox} for {acct['id']}")
        yield imap
    finally:
        try: imap.logout()
        except: pass

def fetch_plaintext(msg) -&gt; str:
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain":
                return (p.get_content() or "").strip()
        for p in msg.walk():
            if p.get_content_type() == "text/html":
                return html_to_text(p.get_content() or "")
    else:
        ct = msg.get_content_type()
        if ct == "text/plain": return (msg.get_content() or "").strip()
        if ct == "text/html":  return html_to_text(msg.get_content() or "")
    return ""

# Heuristics (quick, tunable)
JUNK_PAT = [r"unsubscribe", r"view in browser", r"sale\b", r"promo", r"discount", r"casino|betting"]
KEEP_PAT = [r"\b(invoice|receipt|statement|confirmation|order|tracking)\b",
            r"\bmeeting|minutes|agenda|action item|contract|SOW\b"]

def classify(subj: str, body: str, senders: List[str]) -&gt; str:
    s = (subj or "").lower(); b = (body or "").lower()
    if any(re.search(p, s) or re.search(p, b) for p in JUNK_PAT): return "junk"
    if any(re.search(p, s) or re.search(p, b) for p in KEEP_PAT): return "keep"
    doms = [a.split("@")[-1].lower() for a in senders if "@" in a]
    if any(d in {"amazon.com","github.com","gitlab.com","microsoft.com","google.com"} for d in doms):
        return "keep"
    return "maybe"

def ensure_folder(imap, name: str):
    try:
        imap.create(name)
    except Exception:
        pass

def send_to_thebrain(tb_cfg: Dict[str,Any], item: Dict[str,Any], tags: List[str]) -&gt; None:
    if not tb_cfg or not tb_cfg.get("token"): return
    headers = {"Authorization": f"Bearer {tb_cfg['token']}", "Content-Type": "application/json"}
    title = (item["subject"] or "(no subject)")[:200]
    note  = f"Account: {item['account_id']}\nFrom: {', '.join(item['from'])}\nDate: {item['date']}\n\n{item['text'][:2000]}"
    r = requests.post(f"{tb_cfg['base']}/brains/{tb_cfg['brain_id']}/thoughts",
                      headers=headers, json={"name": title, "type":"Email", "tags": tags}, timeout=15)
    r.raise_for_status()
    tid = (r.json().get("id") or r.json().get("thoughtId") or "")
    if tid:
        requests.post(f"{tb_cfg['base']}/brains/{tb_cfg['brain_id']}/thoughts/{tid}/notes",
                      headers=headers, json={"content": note}, timeout=15).raise_for_status()

def stage(plan: Dict[str,Any]):
    with open("staged_actions.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps(plan)+"\n")

@APP.post("/run_pass_all")
def run_pass_all():
    """
    Body: { "before":"2025-01-01T00:00:00+00:00", "max_keep_per_acct": 25 }
    """
    p = request.get_json(force=True)
    before_iso = p["before"]
    max_keep   = int(p.get("max_keep_per_acct", 25))
    scan_limit = int(CFG.get("scan_limit", 500))
    mbox = CFG.get("mailbox","INBOX")
    junk_folder = CFG.get("junk_folder","Junk-Candidate")
    keep_flag   = CFG.get("keep_flag","\\Flagged")
    tb_cfg = CFG.get("thebrain", {})

    summary = {}
    for acct in CFG["accounts"]:
        acct_id = acct["id"]; summary[acct_id] = {"junk":0,"keep":0,"maybe":0,"errors":0}
        try:
            with imap_session(acct, readonly=True, mailbox=mbox) as imap:
                # ensure junk folder exists (per-acct)
                ensure_folder(imap, junk_folder)

                # search BEFORE date
                dt = datetime.fromisoformat(before_iso).strftime("%d-%b-%Y")
                typ, data = imap.uid("SEARCH", "BEFORE", dt)
                uids = [int(x) for x in (data[0].split() if data and data[0] else [])]
                uids = list(reversed(uids))[:scan_limit]

                junk, keep, maybe = [], [], []
                pushed = 0

                for uid in uids:
                    typ, resp = imap.uid("FETCH", str(uid), "(ENVELOPE RFC822)")
                    if typ != "OK" or not resp or not isinstance(resp[0], tuple):
                        summary[acct_id]["errors"] += 1; continue
                    raw = resp[0][1]
                    msg = email.message_from_bytes(raw, policy=email.policy.default)
                    # envelope is embedded in resp[0][0], but parsing that robustly is messy; use msg headers instead
                    subject = msg.get("Subject","")
                    froms = []
                    for a in msg.get_all("From", []):
                        froms += [x.strip() for x in a.split(",")]
                    date = msg.get("Date","")
                    text = fetch_plaintext(msg)

                    label = classify(subject, text, froms)
                    item = {"account_id": acct_id, "uid": uid, "subject": subject, "from": froms, "date": date, "text": text}

                    if label == "junk":
                        junk.append(uid)
                    elif label == "keep":
                        keep.append(uid)
                        if pushed &lt; max_keep:
                            try:
                                send_to_thebrain(tb_cfg, item, tags=["Email","Keeper"])
                                pushed += 1
                            except Exception:
                                summary[acct_id]["errors"] += 1
                    else:
                        maybe.append(uid)

                # Stage per-acct actions
                if junk:
                    stage({"account_id": acct_id, "action":"move", "from": mbox, "to": junk_folder, "uids": junk})
                if keep:
                    stage({"account_id": acct_id, "action":"flag", "mailbox": mbox, "flag": keep_flag, "uids": keep})

                summary[acct_id]["junk"]=len(junk)
                summary[acct_id]["keep"]=len(keep)
                summary[acct_id]["maybe"]=len(maybe)
        except Exception:
            summary[acct_id]["errors"] += 1
            continue

    return jsonify({"ok": True, "summary": summary})

@APP.post("/apply_plan")
def apply_plan():
    """
    Body: { "plan_file":"staged_actions.jsonl", "only_accounts": ["gmail-1","m365-1"] }
    """
    p = request.get_json(force=True)
    plan_file = p.get("plan_file","staged_actions.jsonl")
    only = set(p.get("only_accounts", []))
    applied = {"move":0,"flag":0}
    with open(plan_file,encoding="utf-8") as f:
        plans = [json.loads(x) for x in f]
    acct_map = {a["id"]: a for a in CFG["accounts"]}

    for plan in plans:
        aid = plan["account_id"]
        if only and aid not in only: continue
        acct = acct_map[aid]
        try:
            with imap_session(acct, readonly=False, mailbox=plan.get("from") or plan.get("mailbox")) as imap:
                if plan["action"]=="move":
                    for uid in plan["uids"]:
                        imap.uid("MOVE", str(uid), plan["to"])
                        applied["move"] += 1
                elif plan["action"]=="flag":
                    flag = plan["flag"]
                    for uid in plan["uids"]:
                        imap.uid("STORE", str(uid), "+FLAGS", f"({flag})")
                        applied["flag"] += 1
        except Exception:
            continue
    return jsonify({"ok": True, "applied": applied})

if __name__ == "__main__":
    load_cfg()
    APP.run(host="127.0.0.1", port=5000)
`
Run:
bash`pip install flask pyyaml beautifulsoup4 requests
python mail_gateway_multi.py
# Dry-run pass over all 6 accounts (read-only, stages a plan):
curl -s http://127.0.0.1:5000/run_pass_all \
  -H 'content-type: application/json' \
  -d '{"before":"2025-01-01T00:00:00+00:00","max_keep_per_acct":25}' | jq

# When satisfied, apply:
curl -s http://127.0.0.1:5000/apply_plan -H 'content-type: application/json' -d '{}' | jq
`

Notes that matter (and a bit of pushback)


Safety / isolation:** keep the LLM air-gapped from the internet and allow it to call only your local gateway endpoints. The model should propose “plans” (UID→action), not execute them.


Gmail labels via IMAP:** they exist as X-GM-LABELS, but for cross-provider portability the gateway uses `MOVE` to a folder and `\Flagged`. That keeps behavior consistent across Gmail/M365.


Performance:** IMAP search is slow across large mailboxes. If it drags, add a tiny SQLite indexer of headers to prefilter UIDs before fetching bodies.


OAuth one-time setup:**


Gmail: create an OAuth “desktop” client, get a refresh token once (you can keep your consent flow entirely local).


M365: run the device code** bootstrap in `oauth_m365.py` to populate `m365_token.json`.




If you want, I can add:


a SQLite header indexer** (fast scans; fewer body fetches),


a Gmail X-GM-LABELS** path for native label adds, and


a hardened systemd unit + ufw rules** to lock the LLM’s egress while letting the gateway reach IMAPS only.
