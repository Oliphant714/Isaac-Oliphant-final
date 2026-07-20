variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro" # free-tier eligible
}

variable "dockerhub_image" {
  description = "Full Docker Hub image reference to run, e.g. username/dnd-encounter-tracker:latest"
  type        = string
}

variable "app_port" {
  description = "Port the Flask app listens on inside the container"
  type        = number
  default     = 5000
}

variable "project_name" {
  description = "Name prefix used to tag/label AWS resources"
  type        = string
  default     = "dnd-encounter-tracker"
}

variable "ssh_cidr" {
  description = "CIDR range allowed to SSH into the instance (lock this down to your own IP in real use)"
  type        = string
  default     = "0.0.0.0/0"
}
