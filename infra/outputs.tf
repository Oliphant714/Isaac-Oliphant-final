output "instance_public_ip" {
  description = "Stable public IP of the EC2 instance (via Elastic IP)"
  value       = aws_eip.app_eip.public_ip
}

output "app_url" {
  description = "URL where the application is reachable"
  value       = "http://${aws_eip.app_eip.public_ip}"
}
