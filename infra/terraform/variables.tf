variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "env" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    project = ""
    env     = ""
    owner   = ""
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones for subnets"
  type        = list(string)
  default     = []
}

variable "container_image" {
  description = "Docker image URI for the ECS task (defaults to ECR repository URL)"
  type        = string
  default     = ""
}

variable "container_environment" {
  description = "Environment variables for the container (non-secret only)"
  type        = map(string)
  default     = {}
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "llm_enabled" {
  description = "Enable LLM features (set to false to reduce OpenAI API calls)"
  type        = bool
  default     = true
}
