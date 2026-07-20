#!/bin/bash
set -euxo pipefail

# Install Docker on Amazon Linux 2023
dnf update -y
dnf install -y docker
systemctl enable docker
systemctl start docker

# Pull and run the latest image from Docker Hub.
# On every `terraform apply` this re-pulls, so pushing a new `:latest` tag
# followed by an apply is how the release pipeline redeploys the app.
docker pull ${dockerhub_image}
docker rm -f dnd-app || true
docker run -d \
  --name dnd-app \
  --restart unless-stopped \
  -p 80:${app_port} \
  ${dockerhub_image}
