#!/bin/bash
set -e
cd ~/credit-book
git pull
cd backend
sudo docker build -t credit-book-backend .
sudo docker rm -f backend 2>/dev/null || true
sudo docker run -d --name backend --restart unless-stopped \
  -p 80:5000 \
  -e DB_HOST=credit-book-db.c5uys48s2qwi.ap-southeast-2.rds.amazonaws.com \
  -v /home/ssm-user/credit-book/frontend:/app/frontend:ro \
  credit-book-backend
echo "Deployed. Check the site in your browser."
