#!/bin/bash
# Everything is inside main() so bash reads the whole script before running it.
# This stops "git pull" from changing the script while it is running.
set -e
main() {
  cd ~/credit-book
  git pull
  cd backend
  sudo docker build -t credit-book-backend .
  sudo docker rm -f backend 2>/dev/null || true
  sudo docker run -d --name backend --restart unless-stopped \
    -p 80:5000 \
    -e DB_HOST=credit-book-db.c5uys48s2qwi.ap-southeast-2.rds.amazonaws.com \
    -v /home/ssm-user/credit-book/frontend:/app/frontend:ro \
    --log-driver awslogs \
    --log-opt awslogs-region=ap-southeast-2 \
    --log-opt awslogs-group=/creditbook/backend \
    --log-opt awslogs-stream=backend \
    credit-book-backend
  echo "Deployed. Logs now go to CloudWatch (/creditbook/backend)."
}
main; exit $?
