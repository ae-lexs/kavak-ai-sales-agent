# Terraform Infrastructure

This directory contains Terraform configuration for deploying AWS infrastructure for the Kavak AI Sales Agent.

## Prerequisites

1. **Terraform installed** (>= 1.0)
   - Download from [terraform.io](https://www.terraform.io/downloads)
   - Or install via package manager: `brew install terraform` (macOS)

2. **AWS CLI configured**
   - Install AWS CLI: `brew install awscli` (macOS)
   - Configure credentials: `aws configure`
   - Or set environment variables: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

3. **AWS Account Access**
   - Ensure you have appropriate IAM permissions to create and manage resources

## Setup

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars` with your values:**
   - Update `project_name`, `env`, and `aws_region` as needed
   - Set appropriate `tags` (project, env, owner)

## AWS Apply/Destroy Checklist

### Before Applying

1. **Set up Secrets Manager secrets** (required before ECS tasks can start):
   
   First, apply Terraform to create the secret resources:
   ```bash
   terraform init
   terraform plan  # Review the plan
   terraform apply  # This creates the secret resources (but not the values)
   ```
   
   Then, set the secret values (replace `<project-name>` and `<env>` with your values):
   ```bash
   # Set OpenAI API key (stored as plain string)
   aws secretsmanager put-secret-value \
     --secret-id <project-name>-<env>-openai-api-key \
     --secret-string "your-openai-api-key-here"

   # Set Twilio auth token (stored as plain string)
   aws secretsmanager put-secret-value \
     --secret-id <project-name>-<env>-twilio-auth-token \
     --secret-string "your-twilio-auth-token-here"
   ```
   
   **Note:** The secrets are created by Terraform but must be populated with actual values before ECS tasks can start successfully.

2. **Build and push Docker image to ECR** (see ECR Repository section below)

3. **Run Terraform apply:**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

### After Applying

1. **Verify health endpoint:**
   ```bash
   ALB_DNS=$(terraform output -raw alb_dns_name)
   curl http://$ALB_DNS/health
   ```
   Expected: `{"status":"ok"}`

2. **Verify webhook endpoint responds:**
   ```bash
   # Test chat endpoint
   curl -X POST http://$ALB_DNS/chat \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "test-123",
       "message": "Hola",
       "channel": "web"
     }'
   ```

3. **Check ECS service is running:**
   ```bash
   aws ecs describe-services \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --services $(terraform output -raw ecs_service_name) \
     --query 'services[0].runningCount'
   ```
   Expected: `1` (or desired count)

4. **View logs if issues occur:**
   ```bash
   LOG_GROUP=$(terraform output -raw ecs_cluster_name | sed 's/-cluster$//')
   aws logs tail /ecs/${LOG_GROUP}-app --follow
   ```

### After Testing - Destroy Immediately

**⚠️ This infrastructure is configured for ephemeral testing only. Destroy immediately after testing to avoid unnecessary costs.**

```bash
terraform destroy
```

**Note:** The RDS instance and Redis cluster are configured with `skip_final_snapshot = true` and no backup retention, so they will be deleted immediately without data preservation.

## Commands

### Initialize Terraform
```bash
terraform init
```
Downloads required providers and initializes the backend.

### Format Code
```bash
terraform fmt
```
Formats Terraform files according to style conventions.

### Validate Configuration
```bash
terraform validate
```
Validates the Terraform configuration files for syntax and consistency.

### Plan Changes
```bash
terraform plan
```
Shows what changes Terraform will make without applying them.

### Apply Changes
```bash
terraform apply
```
Applies the Terraform configuration and creates/updates resources.

To auto-approve without confirmation:
```bash
terraform apply -auto-approve
```

### Destroy Infrastructure
```bash
terraform destroy
```
Destroys all resources managed by this Terraform configuration.

To auto-approve without confirmation:
```bash
terraform destroy -auto-approve
```

## Resource Naming Convention

All resources follow the naming pattern:
```
${var.project_name}-${var.env}-<resource-name>
```

For example: `kavak-agent-dev-vpc` or `kavak-agent-prod-s3-bucket`

## Tagging

All resources are automatically tagged with:
- `project`: Project name
- `env`: Environment name
- `owner`: Resource owner/team

These tags are applied via the provider's `default_tags` configuration.

## Directory Structure

```
infra/terraform/
├── main.tf                 # Root composition and local values
├── providers.tf            # Provider configuration
├── variables.tf            # Variable definitions
├── outputs.tf              # Output values
├── terraform.tfvars.example # Example variable values
└── README.md              # This file
```

## ECR Repository

The ECR repository is created to store Docker images for the application.

### Building and Pushing Docker Images

After applying the Terraform configuration, you can build and push your Docker image:

1. **Authenticate Docker with ECR:**
   ```bash
   aws ecr get-login-password --region <aws_region> | docker login --username AWS --password-stdin <ecr_repository_url>
   ```

2. **Build the Docker image:**
   ```bash
   docker build -t <ecr_repository_url>:latest .
   ```

3. **Tag the image (if needed):**
   ```bash
   docker tag <ecr_repository_url>:latest <ecr_repository_url>:<tag>
   ```

4. **Push the image to ECR:**
   ```bash
   docker push <ecr_repository_url>:latest
   ```

**Example:**
```bash
# Get the repository URL from Terraform outputs
REPO_URL=$(terraform output -raw ecr_repository_url)
REGION=$(terraform output -raw aws_region)

# Authenticate
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPO_URL

# Build and push
docker build -t $REPO_URL:latest .
docker push $REPO_URL:latest
```

**Note:** Image scanning is enabled on push, so vulnerabilities will be automatically detected.

## ECS Fargate Deployment

The infrastructure includes an ECS Fargate service running behind an Application Load Balancer (ALB).

### Architecture

- **ECS Cluster**: Fargate cluster running the application
- **ECS Service**: Deployed in private subnets with desired count of 1
- **Application Load Balancer**: In public subnets, listening on port 80 (HTTP)
- **Target Group**: Health check on `/health` endpoint
- **Security Groups**: 
  - ALB: Allows inbound HTTP (port 80) from anywhere
  - ECS: Allows inbound traffic on port 8000 only from ALB security group

### Important Note on HTTPS

**⚠️ This MVP uses HTTP on port 80 for simplicity and cost savings (no ACM certificate or Route53 required).**

**For production with Twilio webhooks, HTTPS is required.** To enable HTTPS:
1. Add an ACM certificate (or import one)
2. Add Route53 hosted zone and record
3. Update ALB listener to use HTTPS (port 443)
4. Configure certificate in the listener

### Accessing the Application

After deploying, get the ALB DNS name:

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "ALB DNS: $ALB_DNS"
```

#### Health Check

Test the health endpoint:

```bash
curl http://$ALB_DNS/health
```

Expected response:
```json
{"status":"ok"}
```

#### Chat Endpoint

Send a chat request:

```bash
curl -X POST http://$ALB_DNS/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "message": "Hola, estoy buscando un auto",
    "channel": "web"
  }'
```

### Viewing Logs

View ECS task logs in CloudWatch:

```bash
# Get log group name
LOG_GROUP=$(terraform output -raw ecs_cluster_name | sed 's/-cluster$//')
aws logs tail /ecs/${LOG_GROUP}-app --follow
```

### Scaling

To scale the service, update the `desired_count` in `aws_ecs_service.app` or use:

```bash
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --desired-count 2
```

## RDS PostgreSQL Database

The infrastructure includes a minimal RDS PostgreSQL instance for persistent storage of conversation state and leads.

### Architecture

- **RDS Instance**: PostgreSQL 15.4 on `db.t4g.micro` (minimal burstable instance)
- **Storage**: 20GB gp3 storage (auto-scales up to 100GB)
- **Network**: Deployed in private subnets, not publicly accessible
- **Security**: Security group allows inbound PostgreSQL (port 5432) only from ECS security group
- **Credentials**: Stored in AWS Secrets Manager
- **Integration**: `DATABASE_URL` environment variable injected into ECS tasks from Secrets Manager

### Database Configuration

- **Instance Class**: `db.t4g.micro` (1 vCPU, 1GB RAM)
- **Storage**: 20GB gp3 (minimal for cost)
- **Database Name**: `kavak_agent`
- **Username**: `kavak_admin`
- **Password**: Auto-generated and stored in Secrets Manager

### Accessing Database Credentials

Get the database endpoint and secret ARN:

```bash
DB_ENDPOINT=$(terraform output -raw database_endpoint)
SECRET_ARN=$(terraform output -raw database_secret_arn)

echo "Database endpoint: $DB_ENDPOINT"
echo "Secret ARN: $SECRET_ARN"
```

Retrieve credentials from Secrets Manager:

```bash
aws secretsmanager get-secret-value \
  --secret-id $SECRET_ARN \
  --query SecretString \
  --output text | jq .
```

### Database Connection

The `DATABASE_URL` environment variable is automatically injected into ECS tasks from Secrets Manager. The connection string format is:

```
postgresql://kavak_admin:<password>@<endpoint>:5432/kavak_agent
```

### Running Migrations

To run database migrations, you can:

1. **Connect via ECS task** (if migrations are part of the application startup)
2. **Use a temporary ECS task** with the same security group and secrets:

```bash
aws ecs run-task \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --task-definition $(terraform output -raw ecs_cluster_name | sed 's/-cluster$//')-app \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(terraform output -json private_subnet_ids | jq -r '.[0]')],securityGroups=[$(terraform output -raw ecs_security_group_id)],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}'
```

### ⚠️ Important: Ephemeral Configuration

**This RDS configuration is designed for ephemeral apply/destroy cycles only:**

- `skip_final_snapshot = true` - No final snapshot is created when the database is destroyed
- `deletion_protection = false` - Database can be deleted immediately
- `backup_retention_period = 0` - No automated backups

**⚠️ DO NOT use this configuration for production data that needs to be preserved.**

For production:
- Set `skip_final_snapshot = false` and configure snapshot retention
- Enable `deletion_protection = true`
- Set appropriate `backup_retention_period` (e.g., 7 days)
- Consider Multi-AZ deployment for high availability
- Enable automated backups with appropriate retention

## ElastiCache Redis

The infrastructure includes a minimal ElastiCache Redis cluster for Twilio idempotency and optional state caching.

### Architecture

- **Redis Cluster**: ElastiCache Redis 7.0 on `cache.t4g.micro` (minimal node type)
- **Network**: Deployed in private subnets, not publicly accessible
- **Security**: Security group allows inbound Redis (port 6379) only from ECS security group
- **Integration**: `REDIS_URL` environment variable automatically set in ECS tasks
- **Features Enabled**:
  - `STATE_CACHE=redis` - Enables Redis-based state caching
  - `TWILIO_IDEMPOTENCY_ENABLED=true` - Enables Twilio webhook idempotency

### Redis Configuration

- **Node Type**: `cache.t4g.micro` (minimal burstable instance)
- **Engine**: Redis 7.0
- **Port**: 6379
- **Encryption**: At-rest encryption enabled
- **Replication**: Single node (no replication for minimal setup)
- **Snapshots**: Disabled (ephemeral configuration)

### Accessing Redis

Get the Redis endpoint:

```bash
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
echo "Redis endpoint: $REDIS_ENDPOINT"
```

The `REDIS_URL` environment variable is automatically set in ECS tasks:

```
redis://<endpoint>:6379
```

### Use Cases

1. **Twilio Idempotency**: Prevents duplicate processing of Twilio webhook messages
2. **State Cache**: Optional caching layer for conversation state (reduces database load)

### ⚠️ Important: Ephemeral Configuration

**This Redis configuration is designed for ephemeral apply/destroy cycles only:**

- `snapshot_retention_limit = 0` - No snapshots are created
- `automatic_failover_enabled = false` - No automatic failover
- `multi_az_enabled = false` - Single availability zone only
- Single node cluster (no replication)

**⚠️ DO NOT use this configuration for production data that needs to be preserved.**

For production:
- Enable automatic snapshots with appropriate retention
- Enable `automatic_failover_enabled = true` for high availability
- Enable `multi_az_enabled = true` for cross-AZ replication
- Use multiple cache nodes for redundancy
- Consider Redis Cluster mode for larger scale

## Next Steps

Add your AWS resources to `main.tf` or create separate module files as your infrastructure grows.
