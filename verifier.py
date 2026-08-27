#!/usr/bin/env python3
"""SMTP email verifier worker — runs on GitHub Actions.
No credentials in code: API secret comes from environment (Actions secrets).
"""
import smtplib, socket, json, time, os, sys, warnings
warnings.filterwarnings('ignore')
import urllib.request

API_BASE = os.environ.get("API_BASE", "http://47.243.226.129:5002")
SECRET = os.environ.get("API_SECRET", "")
LIMIT = int(os.environ.get("VERIFY_LIMIT", "80"))

def get_mx(domain):
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, 'MX')
        mx = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in answers], key=lambda x: x[0])
        return [m for _, m in mx]
    except:
        return []

def verify_smtp(email, timeout=8):
    local, domain = email.rsplit('@', 1)
    mx = get_mx(domain)
    if not mx:
        return "invalid", "no_mx"
    for m in mx[:3]:
        try:
            s = smtplib.SMTP(timeout=timeout)
            s.connect(m, 25)
            try:
                s.ehlo("verify.local")
            except:
                try:
                    s.helo("verify.local")
                except:
                    s.quit(); continue
            try:
                code, _ = s.mail("verify@example.com")
                if code >= 500:
                    s.quit(); continue
                code, msg = s.rcpt(email)
                msg_l = (msg or b"").decode("utf-8", "replace").lower()
                s.quit()
                if code == 250:
                    # catchall 检测：随机地址探活
                    rand = f"catchalltest{int(time.time())}@{domain}"
                    try:
                        s2 = smtplib.SMTP(timeout=timeout)
                        s2.connect(m, 25)
                        s2.ehlo("verify.local")
                        s2.mail("verify@example.com")
                        c2, _ = s2.rcpt(rand)
                        s2.quit()
                        if c2 == 250:
                            return "catchall", "catch_all"
                    except:
                        pass
                    return "valid", "250"
                elif code in (550, 551, 552, 553, 554):
                    return "invalid", str(code)
                else:
                    return "invalid", str(code)
            except Exception as e:
                s.quit()
                return "invalid", str(e)[:50]
        except:
            continue
    return "invalid", "mx_fail"

def main():
    if not SECRET:
        print("API_SECRET not set")
        return
    try:
        req = urllib.request.Request(f"{API_BASE}/v/pending?key={SECRET}&limit={LIMIT}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            cands = json.loads(resp.read().decode())
    except Exception as e:
        print(f"pull error: {e}")
        return
    if not cands:
        print("no pending candidates")
        return
    print(f"got {len(cands)} candidates")
    results = []
    for c in cands:
        status, code = verify_smtp(c["candidate_email"])
        results.append({"id": c["id"], "status": status, "code": code})
        print(f"  {c['candidate_email']} -> {status}")
        time.sleep(0.3)
    payload = json.dumps({"key": SECRET, "results": results}).encode()
    req = urllib.request.Request(f"{API_BASE}/v/result", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("result:", resp.read().decode())
    except Exception as e:
        print(f"push error: {e}")

if __name__ == "__main__":
    main()
