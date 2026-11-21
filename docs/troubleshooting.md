# Troubleshooting log

Real problems hit while building this project, in the form **symptom → cause → fix → lesson**.

## 1. `mysql8.4` package not found on the EC2 server
- **Symptom:** `dnf install mysql8.4` failed with "no match".
- **Cause:** that package name does not exist in the Amazon Linux 2023 repositories.
- **Fix:** installed the compatible client `mariadb105` and connected to RDS with it.
- **Lesson:** search the package manager (`dnf search mysql`) instead of guessing names. The client does not need to match the server version exactly.

## 2. `git clone` failed with "permission denied"
- **Symptom:** `fatal: could not create work tree dir 'credit-book': Permission denied`.
- **Cause:** the Session Manager shell started in `/usr/bin`, which the `ssm-user` account cannot write to.
- **Fix:** `cd ~` first, then clone into the home directory.
- **Lesson:** always check `pwd` before creating files.

## 3. Page loaded forever from the browser
- **Symptom:** the browser kept loading `http://<public-ip>/api/health` and eventually timed out, while the app worked from inside the server.
- **Cause:** a timeout means the request never reached the app, so the problem is at the network layer (firewall or wrong address), not in Flask.
- **Fix:** checked my current public IP against the security group rule, confirmed the instance used `backend-sg`, and re-entered the address with `http://` and the instance's **current** public IP (it changes on every stop/start).
- **Lesson:** *timeout* points to the firewall or network; *connection refused* points to nothing listening on the port.

## 4. Security group edit rejected
- **Symptom:** "You may not specify an IPv4 CIDR for an existing prefix list rule".
- **Cause:** I tried to change the source of a rule that used a managed prefix list into an IP address.
- **Fix:** left that rule alone and added a **new** HTTP rule with source "My IP".
- **Lesson:** a rule's source type cannot be changed; add a new rule instead.

## 5. CloudFront blocked on a new account
- **Symptom:** "Your account must be verified before you can add new CloudFront resources."
- **Cause:** AWS applies account verification to some services on new accounts. CloudShell showed a similar message.
- **Fix:** opened a support case, documented the intended design in [cloudfront-design.md](cloudfront-design.md), and served the site from Flask on EC2 in the meantime, with port 80 limited to my IP.
- **Lesson:** keep the application independent of the delivery layer so it can change without code changes.

## 6. Server returned `500` for the home page after adding static files
- **Symptom:** `/api/health` worked but `/` returned "Internal Server Error".
- **Cause:** `deploy.sh` ran `git pull`, which replaced `deploy.sh` itself while Bash was still running it. Bash continued with the old version of the script, so the container started **without** the new volume mount for the frontend folder.
- **Fix:** ran the deploy again, and rewrote `deploy.sh` so everything is inside a `main()` function that Bash reads fully before running.
- **Lesson:** do not let a script update itself midway. Also, read the container's last output lines: the old "Deployed" message revealed the old script had run.

## 7. Commands pasted into the wrong terminal
- **Symptom:** `git pull` aborted and a new API route returned `404`.
- **Cause:** commands meant for my Mac were pasted into the EC2 session, creating files on the server that conflicted with `git pull`.
- **Fix:** `git reset --hard origin/main` on the server, then redeployed.
- **Lesson:** label terminals (Mac vs server). Confirm on GitHub that a push actually contains the files before pulling on the server.

## Design notes from the build

- **MySQL 8 authentication:** the `cryptography` package is required by PyMySQL for the default `caching_sha2_password` plugin.
- **bcrypt limit:** bcrypt only uses the first 72 bytes of a password, so the API rejects longer passwords instead of silently truncating them.
- **Money:** `DECIMAL(10,2)` in the database and `Decimal` in Python, never floats.
