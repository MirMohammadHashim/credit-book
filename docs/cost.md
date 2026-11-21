# Cost

The project was built against a small, fixed personal budget, so cost was a design input from the start.

## Approximate running cost (Sydney)

| Item | Approx. cost |
|---|---|
| EC2 instance | about $0.013 per hour |
| RDS instance | about $0.02 per hour |
| EC2 + RDS together | about **$0.035 per hour**, roughly $0.85 per day |
| EBS and RDS storage | a few dollars per month, billed even when stopped |
| VPC, subnets, route tables, Internet Gateway, security groups, IAM, Parameter Store (standard) | free |
| CloudWatch Logs, 1 alarm, SNS email | inside the free allowance at this volume |

Figures are estimates from the AWS pricing pages at build time. Prices change, so check the current pages before copying this design.

## Decisions that kept the bill low

- **No NAT Gateway** (hourly charge) and **no load balancer**. See [architecture.md](architecture.md).
- **Log retention is 7 days**, so log storage cannot grow without limit.
- **Parameter Store instead of Secrets Manager** for two secrets.
- **Stop-able design:** the container restarts automatically, so stopping and starting EC2 is safe. A stopped RDS instance still bills for storage and AWS restarts it after 7 days, so for long breaks it is deleted instead.
- **Everything removable:** a documented teardown order (below) returns the account to near-zero cost.

## Teardown order

1. Delete the EC2 instance.
2. Delete the RDS instance (decide whether a final snapshot is needed; snapshots are billed).
3. Delete leftover RDS snapshots and unused EBS volumes.
4. Delete the CloudWatch log group, alarm and SNS topic.
5. Delete Parameter Store parameters.
6. Delete the S3 bucket (if created) and any CloudFront distribution.
7. Remove the temporary security group rule, then delete security groups, subnet group, subnets, route tables, Internet Gateway, and finally the VPC.
8. Check **Billing → Cost Explorer** for the next few days to confirm the daily cost is $0.
