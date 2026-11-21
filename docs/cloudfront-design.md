# CloudFront design (planned, not deployed)

## Why CloudFront was in the design
- HTTPS for all visitors using a free certificate
- One public front door, so the EC2 server is not exposed directly
- S3 bucket stays private; only CloudFront can read it

## Planned request flow

    Browser -> CloudFront (HTTPS)
                 |- default behaviour  -> private S3 bucket (HTML, CSS, JS)
                 |- /api/* behaviour   -> EC2 (Flask in Docker, port 80)
                                            |
                                            -> RDS MySQL (private subnet)

## Planned settings
- Origin 1: S3 bucket `credit-book-frontend-<account-id>`, Origin Access Control (OAC)
- Origin 2: EC2 public DNS name, HTTP only, port 80
- Default root object: `index.html`
- Viewer protocol policy: redirect HTTP to HTTPS
- `/api/*` behaviour: all HTTP methods allowed, caching disabled,
  forward the Authorization header to the origin
- `backend-sg` inbound rule: TCP 80 from the managed prefix list
  `com.amazonaws.global.cloudfront.origin-facing` only

## Status
Creating the distribution was blocked on my new account with the error
"Your account must be verified before you can add new CloudFront resources."
A support case was opened with AWS Support.

## What is deployed instead
- Flask serves the web pages and the API from EC2 over HTTP.
- Port 80 is open only to the developer's own IP address (temporary).
- No HTTPS in this setup. Passwords must not be real while testing.
- Moving to the CloudFront design above needs no changes to the application code.
