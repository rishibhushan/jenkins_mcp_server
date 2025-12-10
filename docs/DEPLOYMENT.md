# Jenkins MCP Server - Deployment Guide

Complete guide for deploying Jenkins MCP Server in various environments from development to production.

## 📋 Table of Contents

- [Deployment Overview](#deployment-overview)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [CI/CD Integration](#cicd-integration)
- [Monitoring & Alerting](#monitoring--alerting)
- [Security](#security)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

---

## Deployment Overview

### Deployment Options

| Method | Use Case | Pros | Cons |
|--------|----------|------|------|
| **npx** | Quick start, development | No installation, always latest | Requires npm, internet |
| **Global npm** | Personal use | Simple, available globally | Needs update management |
| **Docker** | Production, isolation | Consistent environment | Requires Docker |
| **Kubernetes** | Enterprise, scale | HA, auto-scaling | Complex setup |
| **From Source** | Development, customization | Full control | Manual updates |

### Architecture

```
┌─────────────────────────────────────────────────┐
│              AI Client Layer                    │
│  (Claude Desktop, VS Code, Custom Clients)      │
└────────────────┬────────────────────────────────┘
                 │ stdio/JSON-RPC
                 ▼
┌─────────────────────────────────────────────────┐
│         Jenkins MCP Server (Python)             │
│  ┌───────────────────────────────────────────┐ │
│  │  - Request handling                       │ │
│  │  - Tool routing                          │ │
│  │  - Caching layer                         │ │
│  │  - Metrics collection                    │ │
│  └───────────────────────────────────────────┘ │
└────────────────┬────────────────────────────────┘
                 │ HTTP/HTTPS
                 ▼
┌─────────────────────────────────────────────────┐
│            Jenkins Server                        │
│  (CI/CD Server, Build Management)               │
└─────────────────────────────────────────────────┘
```

---

## Local Development

### Method 1: npx (Quickest)

```bash
# No installation needed
npx @rishibhushan/jenkins-mcp-server --env-file .env

# With custom options
npx @rishibhushan/jenkins-mcp-server \
  --env-file /path/to/.env \
  --verbose
```

**Pros**:
- ✅ No installation
- ✅ Always latest version
- ✅ Quick start

**Cons**:
- ❌ Requires internet
- ❌ Slower first run (downloads package)
- ❌ Not suitable for offline use

---

### Method 2: Global Installation

```bash
# Install globally
npm install -g @rishibhushan/jenkins-mcp-server

# Run
jenkins-mcp-server --env-file .env

# Update
npm update -g @rishibhushan/jenkins-mcp-server

# Uninstall
npm uninstall -g @rishibhushan/jenkins-mcp-server
```

**Pros**:
- ✅ Fast startup
- ✅ Works offline
- ✅ Simple updates

**Cons**:
- ❌ Requires npm
- ❌ Version management needed

---

### Method 3: From Source

```bash
# Clone repository
git clone https://github.com/rishibhushan/jenkins_mcp_server.git
cd jenkins_mcp_server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run
python -m jenkins_mcp_server --env-file .env --verbose
```

**Pros**:
- ✅ Full control
- ✅ Easy customization
- ✅ Latest unreleased features

**Cons**:
- ❌ Manual setup
- ❌ Manual updates
- ❌ More maintenance

---

## Docker Deployment

### Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY setup.py .

# Install application
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 jenkins-mcp && \
    chown -R jenkins-mcp:jenkins-mcp /app
USER jenkins-mcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from jenkins_mcp_server.config import get_default_settings; get_default_settings()"

# Set entrypoint
ENTRYPOINT ["python", "-m", "jenkins_mcp_server"]
CMD ["--verbose"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  jenkins-mcp-server:
    build: .
    container_name: jenkins-mcp-server
    restart: unless-stopped
    
    # Environment variables
    environment:
      - JENKINS_URL=http://jenkins:8080
      - JENKINS_USERNAME=${JENKINS_USERNAME}
      - JENKINS_TOKEN=${JENKINS_TOKEN}
      - JENKINS_TIMEOUT=30
      - JENKINS_CONNECT_TIMEOUT=10
      - JENKINS_MAX_RETRIES=3
    
    # Or use env file
    env_file:
      - .env
    
    # Volumes for persistence
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    # Network
    networks:
      - jenkins-network

networks:
  jenkins-network:
    driver: bridge
```

### Build and Run

```bash
# Build image
docker build -t jenkins-mcp-server:latest .

# Run container
docker run -d \
  --name jenkins-mcp-server \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  jenkins-mcp-server:latest

# View logs
docker logs -f jenkins-mcp-server

# Stop container
docker stop jenkins-mcp-server

# Remove container
docker rm jenkins-mcp-server
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

---

## Cloud Deployment

### AWS ECS Deployment

#### 1. Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name jenkins-mcp-server \
  --region us-east-1

# Get login credentials
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push image
docker tag jenkins-mcp-server:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/jenkins-mcp-server:latest

docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/jenkins-mcp-server:latest
```

#### 2. Create Task Definition

```json
{
  "family": "jenkins-mcp-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "jenkins-mcp-server",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/jenkins-mcp-server:latest",
      "essential": true,
      "environment": [
        {
          "name": "JENKINS_URL",
          "value": "http://jenkins.example.com:8080"
        }
      ],
      "secrets": [
        {
          "name": "JENKINS_USERNAME",
          "valueFrom": "arn:aws:secretsmanager:region:account-id:secret:jenkins-username"
        },
        {
          "name": "JENKINS_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account-id:secret:jenkins-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/jenkins-mcp-server",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 3. Create ECS Service

```bash
aws ecs create-service \
  --cluster jenkins-cluster \
  --service-name jenkins-mcp-server \
  --task-definition jenkins-mcp-server \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

---

### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT-ID/jenkins-mcp-server

# Deploy to Cloud Run
gcloud run deploy jenkins-mcp-server \
  --image gcr.io/PROJECT-ID/jenkins-mcp-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars JENKINS_URL=http://jenkins:8080 \
  --set-secrets JENKINS_USERNAME=jenkins-username:latest \
  --set-secrets JENKINS_TOKEN=jenkins-token:latest \
  --memory 512Mi \
  --cpu 1
```

---

### Azure Container Instances

```bash
# Create resource group
az group create --name jenkins-mcp-rg --location eastus

# Create container instance
az container create \
  --resource-group jenkins-mcp-rg \
  --name jenkins-mcp-server \
  --image YOUR_REGISTRY/jenkins-mcp-server:latest \
  --cpu 1 \
  --memory 1 \
  --environment-variables \
    JENKINS_URL=http://jenkins:8080 \
  --secure-environment-variables \
    JENKINS_USERNAME=admin \
    JENKINS_TOKEN=secret \
  --restart-policy OnFailure \
  --log-analytics-workspace YOUR_WORKSPACE_ID
```

---

## Kubernetes Deployment

### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jenkins-mcp-server
  namespace: jenkins
  labels:
    app: jenkins-mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: jenkins-mcp-server
  template:
    metadata:
      labels:
        app: jenkins-mcp-server
    spec:
      containers:
      - name: jenkins-mcp-server
        image: your-registry/jenkins-mcp-server:latest
        imagePullPolicy: Always
        
        env:
        - name: JENKINS_URL
          value: "http://jenkins-service:8080"
        - name: JENKINS_USERNAME
          valueFrom:
            secretKeyRef:
              name: jenkins-credentials
              key: username
        - name: JENKINS_TOKEN
          valueFrom:
            secretKeyRef:
              name: jenkins-credentials
              key: token
        - name: JENKINS_TIMEOUT
          value: "30"
        - name: JENKINS_CONNECT_TIMEOUT
          value: "10"
        
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "from jenkins_mcp_server.config import get_default_settings; get_default_settings()"
          initialDelaySeconds: 30
          periodSeconds: 30
        
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "from jenkins_mcp_server.config import get_default_settings; get_default_settings()"
          initialDelaySeconds: 5
          periodSeconds: 10
      
      # Security
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
```

### Secret Management

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: jenkins-credentials
  namespace: jenkins
type: Opaque
stringData:
  username: admin
  token: your-jenkins-token
```

```bash
# Create secret from file
kubectl create secret generic jenkins-credentials \
  --from-env-file=.env \
  --namespace=jenkins

# Or use kubectl apply
kubectl apply -f k8s/secret.yaml
```

### Service Configuration

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: jenkins-mcp-service
  namespace: jenkins
spec:
  selector:
    app: jenkins-mcp-server
  ports:
  - protocol: TCP
    port: 8080
    targetPort: 8080
  type: ClusterIP
```

### ConfigMap for Settings

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jenkins-mcp-config
  namespace: jenkins
data:
  JENKINS_TIMEOUT: "30"
  JENKINS_CONNECT_TIMEOUT: "10"
  JENKINS_READ_TIMEOUT: "30"
  JENKINS_MAX_RETRIES: "3"
  JENKINS_CONSOLE_MAX_LINES: "1000"
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace jenkins

# Apply configurations
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods -n jenkins
kubectl get svc -n jenkins

# View logs
kubectl logs -f deployment/jenkins-mcp-server -n jenkins

# Scale deployment
kubectl scale deployment jenkins-mcp-server --replicas=3 -n jenkins
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: pytest tests/ -v --cov
    
    - name: Run linting
      run: |
        black --check src/ tests/
        flake8 src/ tests/
        mypy src/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          yourusername/jenkins-mcp-server:latest
          yourusername/jenkins-mcp-server:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
    - name: Deploy to production
      run: |
        # Add your deployment commands here
        echo "Deploying to production..."
```

---

### GitLab CI/CD

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_IMAGE: registry.gitlab.com/$CI_PROJECT_PATH

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt -r requirements-dev.txt
    - pytest tests/ -v --cov
    - black --check src/ tests/
    - flake8 src/ tests/

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $DOCKER_IMAGE:$CI_COMMIT_SHA .
    - docker tag $DOCKER_IMAGE:$CI_COMMIT_SHA $DOCKER_IMAGE:latest
    - docker push $DOCKER_IMAGE:$CI_COMMIT_SHA
    - docker push $DOCKER_IMAGE:latest
  only:
    - main

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/jenkins-mcp-server jenkins-mcp-server=$DOCKER_IMAGE:$CI_COMMIT_SHA
  only:
    - main
  when: manual
```

---

## Monitoring & Alerting

### Prometheus Metrics

```python
# Add to server.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
tool_executions = Counter('tool_executions_total', 'Total tool executions', ['tool_name', 'status'])
execution_duration = Histogram('tool_execution_duration_seconds', 'Tool execution duration', ['tool_name'])
cache_hits = Counter('cache_hits_total', 'Cache hits')
cache_misses = Counter('cache_misses_total', 'Cache misses')
active_connections = Gauge('active_jenkins_connections', 'Active Jenkins connections')

# Start metrics server
start_http_server(8000)
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'jenkins-mcp-server'
    static_configs:
      - targets: ['jenkins-mcp-server:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Jenkins MCP Server",
    "panels": [
      {
        "title": "Tool Executions",
        "targets": [
          {
            "expr": "rate(tool_executions_total[5m])"
          }
        ]
      },
      {
        "title": "Execution Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, tool_execution_duration_seconds)"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))"
          }
        ]
      }
    ]
  }
}
```

### Logging with ELK Stack

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "jenkins-mcp-server-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"
```

---

## Security

### Environment Variables

```bash
# Never commit these!
JENKINS_URL=http://jenkins.example.com:8080
JENKINS_USERNAME=admin
JENKINS_TOKEN=******************

# Use secrets management
# AWS: Secrets Manager
# GCP: Secret Manager
# Azure: Key Vault
# Kubernetes: Secrets
```

### Network Security

```yaml
# NetworkPolicy for Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: jenkins-mcp-policy
  namespace: jenkins
spec:
  podSelector:
    matchLabels:
      app: jenkins-mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: jenkins
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: jenkins
    ports:
    - protocol: TCP
      port: 8080
```

### SSL/TLS

```bash
# Enable SSL verification
export JENKINS_VERIFY_SSL=true

# For self-signed certificates
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
```

---

## Scaling

### Horizontal Scaling

```bash
# Kubernetes
kubectl scale deployment jenkins-mcp-server --replicas=5 -n jenkins

# Docker Compose
docker-compose up -d --scale jenkins-mcp-server=5
```

### Load Balancing

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jenkins-mcp-ingress
  namespace: jenkins
spec:
  rules:
  - host: jenkins-mcp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: jenkins-mcp-service
            port:
              number: 8080
```

### Auto-scaling

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: jenkins-mcp-hpa
  namespace: jenkins
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: jenkins-mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker logs jenkins-mcp-server

# Common causes:
# 1. Missing environment variables
# 2. Invalid configuration
# 3. Port already in use
# 4. Network issues

# Solution:
docker run --rm -it \
  --env-file .env \
  jenkins-mcp-server:latest \
  python -m jenkins_mcp_server --help
```

#### High Memory Usage

```bash
# Check memory usage
docker stats jenkins-mcp-server

# Solutions:
# 1. Reduce cache size
# 2. Limit console line count
# 3. Reduce metrics history
# 4. Increase container memory limit
```

#### Connection Timeouts

```bash
# Test connectivity
docker exec jenkins-mcp-server \
  curl -I http://jenkins-server:8080

# Solutions:
# 1. Increase timeouts
# 2. Check network policies
# 3. Verify DNS resolution
# 4. Check firewall rules
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Test in development environment
- [ ] Run all tests
- [ ] Update documentation
- [ ] Create backup of current deployment
- [ ] Prepare rollback plan

### Deployment

- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Monitor metrics
- [ ] Deploy to production
- [ ] Verify health checks

### Post-Deployment

- [ ] Monitor logs for errors
- [ ] Check metrics dashboard
- [ ] Verify functionality
- [ ] Update runbooks
- [ ] Notify team

---

**Last Updated**: December 2024  
**Version**: 2.0.0
