# Deployment Architecture Guide

Overview of Cloud Artifact Extractor deployment architecture for each platform.

**Last Updated:** November 1, 2025

---

## AWS App Runner Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    AWS Region (us-east-1)               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Application Load Balancer             │ │
│  │           (Provided by App Runner)                 │ │
│  └──────────────────┬─────────────────────────────────┘ │
│                     │                                    │
│  ┌──────────────────▼─────────────────────────────────┐ │
│  │         App Runner Service                         │ │
│  │  ┌────────────────────────────────────────────┐   │ │
│  │  │  Container Instance (Auto-managed)        │   │ │
│  │  │                                            │   │ │
│  │  │  Cloud Artifact Extractor                 │   │ │
│  │  │  (FastAPI on port 8000)                   │   │ │
│  │  │                                            │   │ │
│  │  │  • /api/v1/extraction/*                   │   │ │
│  │  │  • /api/v1/schedules/*                    │   │ │
│  │  │  • /api/v1/health/*                       │   │ │
│  │  └────────────────────────────────────────────┘   │ │
│  │                                                     │ │
│  │  Auto-scaling: 1-10 replicas (based on load)      │ │
│  └─────────────────┬────────────────────────────────┘ │
│                    │                                   │
│  ┌─────────────────┼────────────────────────────────┐ │
│  │ Configuration & Logging                           │ │
│  │ ├─ Environment Variables                          │ │
│  │ ├─ CloudWatch Logs                               │ │
│  │ ├─ CloudWatch Metrics                            │ │
│  │ └─ X-Ray Tracing (optional)                      │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         IAM Role & Permissions                     │ │
│  │  ├─ ECR pull access                               │ │
│  │ ├─ AWS service permissions (EC2, S3, RDS, etc)   │ │
│  │  ├─ CloudWatch write access                       │ │
│  │  └─ X-Ray write access (optional)                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
           ▼
    ┌────────────────────────────────┐
    │   Amazon ECR                   │
    │   (Container Image Registry)   │
    └────────────────────────────────┘
```

### Data Flow

```
Client Request
    │
    ▼
Internet → AWS API Gateway / ALB (provided by App Runner)
    │
    ▼
App Runner Service (automatically load balanced)
    │
    ▼
Container Instance(s)
    │
    ├─► Extract resources from AWS (using IAM role)
    │
    ├─► Extract resources from Azure (using credentials)
    │
    ├─► Extract resources from GCP (using credentials)
    │
    └─► Send artifacts via HTTP Transport
         │
         ▼
    Policy Scanner / Filesystem / Null Transport
```

### Key Features

- **Managed Load Balancing:** Automatic distribution across replicas
- **Auto-Scaling:** Based on CPU and memory utilization
- **Auto-Recovery:** Failed instances automatically replaced
- **VPC Integration:** Optional private deployment
- **CloudWatch Monitoring:** Built-in metrics and logs
- **CI/CD Ready:** Direct source repository integration

---

## Azure Container Apps Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│              Azure Subscription / Region                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Container Apps Environment                 │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  Ingress Controller                         │  │ │
│  │  │  (HTTPS, TLS termination)                   │  │ │
│  │  └─────────────────┬───────────────────────────┘  │ │
│  │                    │                               │ │
│  │  ┌─────────────────▼───────────────────────────┐  │ │
│  │  │  Load Balancer (Internal)                   │  │ │
│  │  └─────────────────┬───────────────────────────┘  │ │
│  │                    │                               │ │
│  │  ┌─────────────────▼───────────────────────────┐  │ │
│  │  │  Container App (cloud-artifact-extractor)  │  │ │
│  │  │  ┌─────────────────────────────────────┐   │  │ │
│  │  │  │  Pod Replica 1                      │   │  │ │
│  │  │  │  FastAPI on port 8000               │   │  │ │
│  │  │  └─────────────────────────────────────┘   │  │ │
│  │  │  ┌─────────────────────────────────────┐   │  │ │
│  │  │  │  Pod Replica 2                      │   │  │ │
│  │  │  │  FastAPI on port 8000               │   │  │ │
│  │  │  └─────────────────────────────────────┘   │  │ │
│  │  │  ┌─────────────────────────────────────┐   │  │ │
│  │  │  │  Pod Replica N (HPA managed)        │   │  │ │
│  │  │  │  FastAPI on port 8000               │   │  │ │
│  │  │  └─────────────────────────────────────┘   │  │ │
│  │  │                                             │  │ │
│  │  │  Auto-scaling: 2-10 replicas               │  │ │
│  │  │  (based on CPU, memory, custom metrics)    │  │ │
│  │  └─────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌────────────────────────────────────────────┐  │ │
│  │  │  Configuration & Secrets                   │  │ │
│  │  │  ├─ Environment Variables (ConfigMap)      │  │ │
│  │  │  ├─ Credentials (Key Vault secrets)        │  │ │
│  │  │  └─ Resource limits (CPU 0.5-2 cores)     │  │ │
│  │  └────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Observability & Security                          │ │
│  │  ├─ Azure Monitor (metrics)                        │ │
│  │  ├─ Log Analytics (logs)                           │ │
│  │  ├─ Application Insights (APM)                     │ │
│  │  ├─ Managed Identity (authentication)              │ │
│  │  └─ Virtual Network (optional networking)          │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Azure Container Registry                          │ │
│  │  (Private image storage)                           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

```
Client Request
    │
    ▼
Internet → Container Apps Ingress (Azure front-end)
    │
    ▼
Internal Load Balancer
    │
    ▼
Container App Replicas (round-robin distribution)
    │
    ├─► Extract resources from AWS (using credentials)
    │
    ├─► Extract resources from Azure (using Managed Identity)
    │
    ├─► Extract resources from GCP (using credentials)
    │
    └─► Send artifacts via HTTP Transport
         │
         ▼
    Policy Scanner / Filesystem / Null Transport
```

### Key Features

- **Managed Kubernetes:** Built on top of Kubernetes without complexity
- **DAPR Support:** Distributed application runtime integration
- **Automatic Scaling:** Based on multiple metrics
- **Private Networking:** Virtual Network integration
- **Log Analytics:** Centralized logging with KQL queries
- **Application Insights:** Built-in APM and diagnostics
- **Managed Identity:** Secure credential handling

---

## Google Cloud Run Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│            Google Cloud Project                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │           Cloud Load Balancing                     │ │
│  │        (Automatic, globally distributed)          │ │
│  └──────────────────┬─────────────────────────────────┘ │
│                     │                                    │
│  ┌──────────────────▼─────────────────────────────────┐ │
│  │         Cloud Run Service                          │ │
│  │                                                     │ │
│  │  ┌────────────────────────────────────────────┐   │ │
│  │  │  Revision (cloud-artifact-extractor)      │   │ │
│  │  │  ┌──────────────────────────────────────┐ │   │ │
│  │  │  │  Container Instance 1                │ │   │ │
│  │  │  │  FastAPI on port 8000                │ │   │ │
│  │  │  └──────────────────────────────────────┘ │   │ │
│  │  │  ┌──────────────────────────────────────┐ │   │ │
│  │  │  │  Container Instance 2                │ │   │ │
│  │  │  │  FastAPI on port 8000                │ │   │ │
│  │  │  └──────────────────────────────────────┘ │   │ │
│  │  │  ┌──────────────────────────────────────┐ │   │ │
│  │  │  │  Container Instance N (Auto-scaled)  │ │   │ │
│  │  │  │  FastAPI on port 8000                │ │   │ │
│  │  │  └──────────────────────────────────────┘ │   │ │
│  │  │                                            │   │ │
│  │  │  Auto-scaling: 0-100 instances            │   │ │
│  │  │  (based on request rate)                  │   │ │
│  │  │  Request timeout: 60 minutes              │   │ │
│  │  │  Memory: 512MB - 8GB per instance         │   │ │
│  │  └────────────────────────────────────────────┘   │ │
│  │                                                     │ │
│  │  Configuration:                                    │ │
│  │  ├─ Environment Variables                         │ │
│  │  ├─ Secret Manager Integration                    │ │
│  │  ├─ Resource Limits                               │ │
│  │  └─ Concurrency Settings                          │ │
│  │                                                     │ │
│  └─────────────────┬────────────────────────────────┘ │
│                    │                                   │
│  ┌─────────────────┼────────────────────────────────┐ │
│  │  Observability                                     │ │
│  │  ├─ Cloud Logging (Stackdriver)                   │ │
│  │  ├─ Cloud Monitoring (metrics)                    │ │
│  │  ├─ Cloud Trace (distributed tracing)            │ │
│  │  └─ Error Reporting                              │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Security & Access                                 │ │
│  │  ├─ Service Account (Workload Identity)            │ │
│  │  ├─ IAM Roles & Permissions                        │ │
│  │  ├─ Cloud Armor (DDoS protection)                  │ │
│  │  └─ VPC Connector (optional networking)            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Container Registry                                │ │
│  │  (gcr.io/<project>/cloud-artifact-extractor)      │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

```
Client Request (HTTP/HTTPS)
    │
    ▼
Google Cloud Load Balancer
    │
    ▼
Cloud Run Service (Route to nearest instance)
    │
    ▼
Container Instances (concurrent processing)
    │
    ├─► Extract resources from AWS (using credentials)
    │
    ├─► Extract resources from Azure (using credentials)
    │
    ├─► Extract resources from GCP (using Workload Identity)
    │
    └─► Send artifacts via HTTP Transport
         │
         ▼
    Policy Scanner / Filesystem / Null Transport
```

### Key Features

- **Serverless:** No infrastructure management needed
- **Global Load Balancing:** Automatic traffic distribution
- **Scale to Zero:** Instances automatically terminated when not in use
- **Per-Request Pricing:** Only pay for actual computation
- **Integrated Security:** Built-in DDoS protection and IAM
- **Container Native:** Direct deployment from container image
- **VPC Integration:** Optional private networking with VPC Connector

---

## Kubernetes Architecture (EKS/AKS/GKE)

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│        Kubernetes Cluster (EKS/AKS/GKE)                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  cloud-artifact-extractor Namespace               │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  Ingress Controller / Load Balancer         │  │ │
│  │  │  (HTTPS, TLS termination)                   │  │ │
│  │  └─────────────────┬───────────────────────────┘  │ │
│  │                    │                               │ │
│  │  ┌─────────────────▼───────────────────────────┐  │ │
│  │  │  Service (cloud-artifact-extractor)        │  │ │
│  │  │  Type: LoadBalancer / ClusterIP+Ingress    │  │ │
│  │  │  Port: 8000 (internal)                      │  │ │
│  │  └─────────────────┬───────────────────────────┘  │ │
│  │                    │                               │ │
│  │  ┌─────────────────▼───────────────────────────┐  │ │
│  │  │  Deployment                                 │  │ │
│  │  │  ├─ Pod 1 (cloud-artifact-extractor)       │  │ │
│  │  │  │  └─ Container (port 8000)               │  │ │
│  │  │  │                                          │  │ │
│  │  │  ├─ Pod 2 (cloud-artifact-extractor)       │  │ │
│  │  │  │  └─ Container (port 8000)               │  │ │
│  │  │  │                                          │  │ │
│  │  │  └─ Pod N (HPA managed)                     │  │ │
│  │  │     └─ Container (port 8000)                │  │ │
│  │  │                                              │  │ │
│  │  │  Replicas: 2-10 (managed by HPA)            │  │ │
│  │  │  Resource Requests/Limits:                  │  │ │
│  │  │  • CPU: 500m - 1000m                        │  │ │
│  │  │  • Memory: 512Mi - 1Gi                      │  │ │
│  │  └─────────────────┬───────────────────────────┘  │ │
│  │                    │                               │ │
│  │  ┌─────────────────▼───────────────────────────┐  │ │
│  │  │  HPA (Horizontal Pod Autoscaler)           │  │ │
│  │  │  • Min replicas: 2                          │  │ │
│  │  │  • Max replicas: 10                         │  │ │
│  │  │  • Target CPU: 70%                          │  │ │
│  │  │  • Target Memory: 80%                       │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  Pod Disruption Budget                      │  │ │
│  │  │  • Min available: 1 pod                     │  │ │
│  │  │  (Protects during node maintenance)         │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  Configuration & Secrets                    │  │ │
│  │  │  ├─ ConfigMap (app configuration)           │  │ │
│  │  │  ├─ Secret (credentials, API keys)          │  │ │
│  │  │  └─ Service Account (RBAC)                  │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  Network Policies                           │  │ │
│  │  │  • Ingress: Allow from Ingress controller   │  │ │
│  │  │  • Egress: Allow to external services       │  │ │
│  │  │  (AWS, Azure, GCP, Scanner endpoint)        │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  RBAC (Role-Based Access Control)           │  │ │
│  │  │  • ServiceAccount: cloud-artifact-scanner   │  │ │
│  │  │  • Role/ClusterRole: minimal permissions    │  │ │
│  │  │  • RoleBinding/ClusterRoleBinding configured│  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  Monitoring & Logging                       │  │ │
│  │  │  ├─ ServiceMonitor (Prometheus)             │  │ │
│  │  │  ├─ Logs → Cloud provider logging           │  │ │
│  │  │  │  (CloudWatch, Azure Monitor, Cloud Log) │  │ │
│  │  │  └─ Metrics → Cloud provider monitoring    │  │ │
│  │  │     (CloudWatch, Azure Monitor, Cloud Mon) │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │  CronJob (Optional Scheduled Extraction)    │  │ │
│  │  │  • Schedule: 0 2 * * * (daily 2 AM)        │  │ │
│  │  │  • Job: One-time extraction task            │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Worker Nodes (Cloud provider managed)             │ │
│  │  • Auto-scaling group for nodes                    │ │
│  │  • Health checks and auto-recovery                │ │
│  │  • Container runtime (Docker/containerd)          │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Container Registry                                │ │
│  │  • ECR (AWS)                                       │ │
│  │  • ACR (Azure)                                     │ │
│  │  • GCR (GCP)                                       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

```
Client Request (HTTP/HTTPS)
    │
    ▼
Kubernetes Ingress / Load Balancer
    │
    ▼
Service (routing to pods)
    │
    ▼
Pod Replicas (distributed processing)
    │
    ├─► Extract resources from AWS (using IAM role/Workload Identity)
    │
    ├─► Extract resources from Azure (using Service Principal/Workload Identity)
    │
    ├─► Extract resources from GCP (using Service Account/Workload Identity)
    │
    └─► Send artifacts via HTTP Transport
         │
         ▼
    Policy Scanner / Filesystem / Null Transport
```

### Key Features

- **Container Orchestration:** Kubernetes manages deployment and scaling
- **Multi-Cloud:** Same deployment manifest works on EKS, AKS, GKE
- **Advanced Networking:** Network policies and service mesh support
- **Workload Identity:** Secure credential management per cloud
- **Custom Scaling:** HPA with CPU, memory, and custom metrics
- **Pod Disruption Budget:** Maintains availability during updates
- **RBAC:** Fine-grained access control
- **Monitoring Integration:** Native integration with cloud monitoring

---

## Common Architecture Patterns

### 1. Request Routing Flow

All platforms follow similar request routing:

```
Client
  ↓
External Load Balancer (provided by platform)
  ↓
Service Mesh / Internal Load Balancer
  ↓
Application Instances (Round-robin or intelligent routing)
  ↓
Response back to Client
```

### 2. Configuration Management

```
Environment Variables → Application Configuration
                  ↓
              ├─ Cloud provider credentials
              ├─ Service endpoints
              ├─ Transport settings
              ├─ Feature flags
              └─ Debug settings
```

### 3. External Integration Points

```
Cloud Artifact Extractor
  ├─ AWS Services (via IAM role credentials)
  ├─ Azure Services (via Service Principal / Managed Identity)
  ├─ GCP Services (via Service Account / Workload Identity)
  └─ External Transport Endpoint (Policy Scanner)
```

### 4. Observability Stack

```
Application Metrics / Logs
  ↓
├─ AWS CloudWatch (AWS deployments)
├─ Azure Monitor (Azure deployments)
├─ Google Cloud Operations (GCP deployments)
└─ Kubernetes Metrics Server (K8s deployments)
  ↓
Dashboards, Alerts, and Reports
```

---

## Deployment Comparison by Architecture

| Aspect | AWS App Runner | Azure Container Apps | Cloud Run | Kubernetes |
|--------|---|---|---|---|
| **Management** | Fully Managed | Fully Managed | Fully Managed | Self-Managed |
| **Load Balancing** | Built-in | Built-in | Global (built-in) | Service-based |
| **Scaling** | Automatic | Automatic + metrics | Automatic 0-N | HPA + Manual |
| **Networking** | VPC available | vNET available | VPC Connector | Full CNI |
| **Observability** | CloudWatch | Azure Monitor | Cloud Logging | Prometheus/ELK |
| **Secrets Management** | IAM / Parameters | Key Vault | Secret Manager | etcd/Sealed Secrets |
| **Multi-region** | Via services | Traffic Manager | Native | Manual federation |

---

## Next Steps

1. **Review the architecture** relevant to your deployment platform
2. **Understand the data flow** for your use case
3. **Check the platform-specific deployment guide** for setup details
4. **Configure observability** according to your monitoring needs
5. **Plan for scaling** based on expected traffic

For detailed deployment instructions, see the platform-specific guides:
- [AWS App Runner Guide](../deploy/aws/README.md)
- [Azure Container Apps Guide](../deploy/azure/README.md)
- [GCP Cloud Run Guide](../deploy/gcp/README.md)
- [Kubernetes Guide](../deploy/kubernetes/README.md)
