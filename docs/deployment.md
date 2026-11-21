# Deployment guide

How the environment was built, in order. Everything was created in the AWS console in `ap-southeast-2` (Sydney). Replace names and IDs with your own. **Check current pricing before creating anything**, and read [cost.md](cost.md) first.

## 0. Prerequisites
- An AWS account with MFA on the root user, and a budget alert.
- Git, and a GitHub repository for this code.

## 1. Network
1. Create a VPC (`credit-book-vpc`).
2. Create 2 public subnets and 2 private subnets in two Availability Zones.
3. Create an Internet Gateway and attach it to the VPC.
4. Public route table: `0.0.0.0/0 → Internet Gateway`, associated with the public subnets.
5. Private route table: local routes only, associated with the private subnets. **Do not add a NAT Gateway.**

## 2. Security groups
1. `backend-sg`: inbound TCP 80 from **your own IP** (`/32`). No other inbound rules.
2. `database-sg`: inbound TCP 3306 with source = `backend-sg`.

## 3. Secrets (Parameter Store)
Create two **SecureString** parameters:
- `/creditbook/db_password`: the RDS master password
- `/creditbook/jwt_secret`: a long random value, for example `openssl rand -hex 32`

Never commit these or paste them into chats or screenshots.

## 4. IAM role for the server
Create a role for EC2 (`ec2-backend-role`) with:
- the AWS-managed policy `AmazonSSMManagedInstanceCore` (Session Manager)
- an inline policy allowing `ssm:GetParameter` on `arn:aws:ssm:ap-southeast-2:<ACCOUNT_ID>:parameter/creditbook/*`
- an inline policy for logs:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
    "Resource": "arn:aws:logs:ap-southeast-2:<ACCOUNT_ID>:log-group:/creditbook/backend:*"
  }]
}
```

## 5. Database
1. Create a DB subnet group with the two private subnets.
2. Create an RDS MySQL 8.4 instance: **Publicly accessible = No**, security group = `database-sg`, initial database name `creditbook`, master user `admin`. Pick the smallest instance class and storage that fit your budget.
3. Wait until the status is **Available**.

## 6. Server
1. Launch an EC2 instance (Amazon Linux 2023) in a **public** subnet with a public IP, security group `backend-sg`, and the IAM role above. **No key pair.**
2. Connect with **Session Manager** (EC2 → Connect → Session Manager).
3. Install tools:
   ```
   sudo dnf install -y docker git mariadb105
   sudo systemctl enable --now docker
   ```
4. Create the tables:
   ```
   cd ~ && git clone https://github.com/<your-user>/credit-book.git
   mysql -h <rds-endpoint> -u admin -p creditbook < credit-book/database/schema.sql
   ```

## 7. Logging and alerting
1. CloudWatch → Log groups → create `/creditbook/backend` with **7-day retention**.
2. SNS → create a Standard topic `creditbook-alerts` and subscribe your email (confirm it from your inbox).
3. CloudWatch → Alarms → create an alarm on the instance's `StatusCheckFailed` metric (Maximum, 5 minutes, `>= 1`), missing data treated as **missing**, notification to the SNS topic.

## 8. Deploy the app
Edit the RDS endpoint in `deploy.sh`, then on the server:
```
cd ~/credit-book && git pull && bash deploy.sh
```
`deploy.sh` builds the Docker image, replaces the running container, mounts the `frontend` folder, and sends container logs to CloudWatch.

## 9. Verify
- `http://<public-ip>/api/health` returns `{"status":"ok"}`
- `http://<public-ip>/api/db-check` returns `{"db":"ok", ...}`
- Open `http://<public-ip>/`, sign up with a **fake** password, add a customer, add entries
- CloudWatch → `/creditbook/backend` shows request lines

The public IP changes every time the instance stops and starts. Use the current one.

## 10. Tear down
Follow the order in [cost.md](cost.md#teardown-order).
