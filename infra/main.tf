terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state so GitHub Actions runs don't rely on local .tfstate.
  # Create this bucket once by hand (or via a bootstrap script) before first run.
  backend "s3" {
    # Fill these in - see README "One-time setup" section.
    bucket = "iro-dnd-tracker-final-2026"
    key    = "dnd-encounter-tracker/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# Always deploy on the latest Amazon Linux 2023 AMI rather than hardcoding an AMI id
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-sg"
  description = "Allow HTTP and SSH to the encounter tracker instance"

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  user_data = templatefile("${path.module}/user_data.sh", {
    dockerhub_image = var.dockerhub_image
    app_port        = var.app_port
  })

  # Force a fresh boot (re-runs user_data) whenever the image tag changes,
  # so pushing a new release actually redeploys the running container.
  user_data_replace_on_change = true

  tags = {
    Name = var.project_name
  }
}

# Elastic IP keeps the public address stable across instance replacements,
# so the submitted EC2 URL doesn't change every time this is applied.
resource "aws_eip" "app_eip" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-eip"
  }
}
