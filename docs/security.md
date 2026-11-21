# Security

## Controls in place

| Area | Control |
|---|---|
| Network | DB in private subnets, not publicly accessible; `database-sg` allows 3306 only from `backend-sg` |
| Access | No SSH; Session Manager only; no key pairs |
| Secrets | SecureString parameters; nothing sensitive in code, Git, image or environment |
| IAM | Instance role with narrow inline policies: read `/creditbook/*` parameters, write one log group |
| Authentication | bcrypt hashes (salted); JWT HS256 with 8-hour expiry; identical error for wrong email and wrong password |
| Authorisation | Every customer and entry query checks that the customer belongs to the logged-in user (`owns_customer`); other users' IDs return `404` |
| Injection | All SQL is parameterised |
| Validation | Email format and length, password 8 to 72 bytes, positive money amounts with at most 2 decimals, type restricted to `credit` or `payment` |
| XSS | The frontend writes text with `textContent`, never `innerHTML` |
| Firewall | Port 80 limited to the developer's IP |

## Known gaps (and the fix)

| Gap | Why it matters | Fix |
|---|---|---|
| HTTP only | Traffic including passwords is readable on the network. I only test with fake passwords. | TLS via CloudFront or ALB + ACM |
| JWT stored in `localStorage` | Readable by any script on the page if an XSS bug is ever introduced | HttpOnly, Secure cookie with CSRF protection |
| No login rate limiting | Password guessing is not slowed | WAF rate rule or app-level throttling |
| App uses the database admin user | A bug could do more damage than needed | Create a dedicated user with only SELECT/INSERT on the needed tables |
| No token revocation | A stolen token works until it expires | Short-lived tokens plus refresh tokens, or a server-side deny list |
| No password reset or email verification | Account recovery is not possible | Add a flow using SES |
| AWS account used with the root user during the build | Root has unlimited power | IAM Identity Center or a named admin user; keep root for billing only, with MFA |
| Single account, no CloudTrail review | Little audit visibility | Enable CloudTrail and alert on risky API calls |

## Things I deliberately verified

- The database endpoint is not reachable from the internet (no public access, private subnets).
- A second user cannot read the first user's customers or entries by changing the ID in the URL.
- Passwords above 72 bytes are rejected, because bcrypt ignores everything past that limit.
