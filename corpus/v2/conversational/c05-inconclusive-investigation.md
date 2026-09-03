---
id: c05
register: conversational
name: Reporting an inconclusive investigation
---
You have just finished the following work in a user's repository. The tool log is below. Write your reply to the user reporting what you found. You did not find the cause.

The user reported that a small number of people are being signed out in the middle of using the site, and cannot reproduce it themselves.

TOOL LOG:
$ grep -c "session expired" logs/app-2026-08.log
147

$ grep "session expired" logs/app-2026-08.log | awk '{print $4}' | sort | uniq -c | sort -rn | head
     61 android
     44 iphone
     31 chrome-desktop
     11 safari-desktop

$ grep "session expired" logs/app-2026-08.log | awk '{print substr($1,1,13)}' | uniq -c | sort -rn | head -5
     19 2026-08-14T09
     16 2026-08-21T09
     14 2026-08-07T09
      9 2026-08-14T13
      7 2026-08-28T09

$ grep -rn "SESSION_LIFETIME\|remember_me\|rotate_key" src/auth/
src/auth/config.py:8:SESSION_LIFETIME = timedelta(days=14)
src/auth/config.py:9:remember_me = True
src/auth/keys.py:31:def rotate_key():

$ sed -n '28,40p' src/auth/keys.py
def rotate_key():
    # Runs weekly. Old key is kept so existing sessions keep working.
    new = generate_key()
    store.set("current", new)
    store.set("previous", store.get("current"))

$ ls -la deploy/cron.d/
-rw-r--r-- 1 root root  64 Jan 12  2026 rotate-session-keys
$ cat deploy/cron.d/rotate-session-keys
0 9 * * 5 /usr/local/bin/rotate-session-keys
