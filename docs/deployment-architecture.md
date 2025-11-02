---
layout: default
title: Deployment Architecture
parent: Deployment
nav_order: 1
---

# Deployment Architecture Guide

Overview of Cloud Artifact Extractor deployment architecture for each platform.

**Last Updated:** November 1, 2025

---

## AWS App Runner Architecture

### Component Diagram

```mermaid
graph TB
    subgraph "AWS Region (us-east-1)"
        ALB[Application Load Balancer<br/>Provided by App Runner]
        ARS[App Runner Service]
        CI[Container Instance<br/>Auto-managed]
        CAE[Cloud Artifact Extractor<br/>FastAPI on port 8000<br/>• /api/v1/extraction/*<br/>• /api/v1/schedules/*<br/>• /api/v1/health/*]
        CL[Configuration & Logging<br/>• Environment Variables<br/>• CloudWatch Logs<br/>• CloudWatch Metrics<br/>• X-Ray Tracing]
        IAM[IAM Role & Permissions<br/>• ECR pull access<br/>• AWS service permissions<br/>• CloudWatch write access<br/>• X-Ray write access]
    end
    
    ECR[Amazon ECR<br/>Container Image Registry]
    
    ALB --> ARS
    ARS --> CI
    CI --> CAE
    CAE --> CL
    CAE --> IAM
    CI -.-> ECR
    
    style ALB fill:#e1f5fe
    style ARS fill:#f3e5f5
    style CI fill:#e8f5e8
    style CAE fill:#fff3e0
    style CL fill:#fce4ec
    style IAM fill:#f1f8e9
    style ECR fill:#e0f2f1
```

### Data Flow

```mermaid
flowchart TD
    CR[Client Request] --> IG["Internet to AWS API Gateway / ALB<br/>provided by App Runner"]
    IG --> ARS["App Runner Service<br/>automatically load balanced"]
    ARS --> CI["Container Instance(s)"]
    
    CI --> EXTRACT_AWS["Extract resources from AWS<br/>using IAM role"]
    CI --> EXTRACT_AZURE["Extract resources from Azure<br/>using credentials"]
    CI --> EXTRACT_GCP["Extract resources from GCP<br/>using credentials"]
    
    EXTRACT_AWS --> HT["Send artifacts via HTTP Transport"]
    EXTRACT_AZURE --> HT
    EXTRACT_GCP --> HT
    
    HT --> DEST["Policy Scanner / Filesystem / Null Transport"]
    
    style CR fill:#e3f2fd
    style IG fill:#f3e5f5
    style ARS fill:#e8f5e8
    style CI fill:#fff3e0
    style HT fill:#fce4ec
    style DEST fill:#f1f8e9
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

```mermaid
graph TB
    subgraph "Azure Subscription / Region"
        CAE[Container Apps Environment]
        IC[Ingress Controller<br/>HTTPS, TLS termination]
        LB[Load Balancer<br/>Internal]
        CA[Container App<br/>cloud-artifact-extractor]
        
        subgraph "Container App"
            P1[Pod Replica 1<br/>FastAPI on port 8000]
            P2[Pod Replica 2<br/>FastAPI on port 8000]
            PN[Pod Replica N<br/>HPA managed<br/>FastAPI on port 8000]
        end
        
        CS[Configuration & Secrets<br/>• Environment Variables<br/>• Key Vault secrets<br/>• Resource limits]
        
        OBS[Observability & Security<br/>• Azure Monitor<br/>• Log Analytics<br/>• Application Insights<br/>• Managed Identity<br/>• Virtual Network]
        
        ACR[Azure Container Registry<br/>Private image storage]
    end
    
    IC --> LB
    LB --> CA
    CA --> P1
    CA --> P2
    CA --> PN
    CA --> CS
    CA --> OBS
    CA -.-> ACR
    
    style CAE fill:#e1f5fe
    style IC fill:#f3e5f5
    style LB fill:#e8f5e8
    style CA fill:#fff3e0
    style P1 fill:#fce4ec
    style P2 fill:#fce4ec
    style PN fill:#fce4ec
    style CS fill:#f1f8e9
    style OBS fill:#e0f2f1
    style ACR fill:#fafafa
```

### Data Flow

```mermaid
flowchart TD
    CR[Client Request] --> IG[Internet → Container Apps Ingress<br/>Azure front-end]
    IG --> LB[Internal Load Balancer]
    LB --> CAR[Container App Replicas<br/>round-robin distribution]
    
    CAR --> EXTRACT_AWS[Extract resources from AWS<br/>using credentials]
    CAR --> EXTRACT_AZURE[Extract resources from Azure<br/>using Managed Identity]
    CAR --> EXTRACT_GCP[Extract resources from GCP<br/>using credentials]
    
    EXTRACT_AWS --> HT[Send artifacts via HTTP Transport]
    EXTRACT_AZURE --> HT
    EXTRACT_GCP --> HT
    
    HT --> DEST[Policy Scanner / Filesystem / Null Transport]
    
    style CR fill:#e3f2fd
    style IG fill:#f3e5f5
    style LB fill:#e8f5e8
    style CAR fill:#fff3e0
    style HT fill:#fce4ec
    style DEST fill:#f1f8e9
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

```mermaid
graph TB
    subgraph "Google Cloud Project"
        CLB[Cloud Load Balancing<br/>Automatic, globally distributed]
        CRS[Cloud Run Service]
        
        subgraph "Revision (cloud-artifact-extractor)"
            C1[Container Instance 1<br/>FastAPI on port 8000]
            C2[Container Instance 2<br/>FastAPI on port 8000]
            CN[Container Instance N<br/>Auto-scaled<br/>FastAPI on port 8000]
        end
        
        CONF[Configuration<br/>• Environment Variables<br/>• Secret Manager Integration<br/>• Resource Limits<br/>• Concurrency Settings]
        
        OBS[Observability<br/>• Cloud Logging<br/>• Cloud Monitoring<br/>• Cloud Trace<br/>• Error Reporting]
        
        SEC[Security & Access<br/>• Service Account<br/>• IAM Roles & Permissions<br/>• Cloud Armor<br/>• VPC Connector]
        
        REG[Container Registry<br/>gcr.io/&lt;project&gt;/cloud-artifact-extractor]
    end
    
    CLB --> CRS
    CRS --> C1
    CRS --> C2
    CRS --> CN
    CRS --> CONF
    CRS --> OBS
    CRS --> SEC
    CRS -.-> REG
    
    style CLB fill:#e1f5fe
    style CRS fill:#f3e5f5
    style C1 fill:#e8f5e8
    style C2 fill:#e8f5e8
    style CN fill:#e8f5e8
    style CONF fill:#fff3e0
    style OBS fill:#fce4ec
    style SEC fill:#f1f8e9
    style REG fill:#e0f2f1
```

### Data Flow

```mermaid
flowchart TD
    CR[Client Request<br/>HTTP/HTTPS] --> CLB[Google Cloud Load Balancer]
    CLB --> CRS[Cloud Run Service<br/>Route to nearest instance]
    CRS --> CI[Container Instances<br/>concurrent processing]
    
    CI --> EXTRACT_AWS[Extract resources from AWS<br/>using credentials]
    CI --> EXTRACT_AZURE[Extract resources from Azure<br/>using credentials]
    CI --> EXTRACT_GCP[Extract resources from GCP<br/>using Workload Identity]
    
    EXTRACT_AWS --> HT[Send artifacts via HTTP Transport]
    EXTRACT_AZURE --> HT
    EXTRACT_GCP --> HT
    
    HT --> DEST[Policy Scanner / Filesystem / Null Transport]
    
    style CR fill:#e3f2fd
    style CLB fill:#f3e5f5
    style CRS fill:#e8f5e8
    style CI fill:#fff3e0
    style HT fill:#fce4ec
    style DEST fill:#f1f8e9
```

---

## Kubernetes Architecture (EKS/AKS/GKE)

### Component Diagram

```mermaid
graph TB
    subgraph "Kubernetes Cluster (EKS/AKS/GKE)"
        NS["cloud-artifact-extractor Namespace"]
        
        subgraph "Namespace"
            IC["Ingress Controller / Load Balancer<br/>HTTPS, TLS termination"]
            SVC["Service<br/>cloud-artifact-extractor<br/>Type: LoadBalancer / ClusterIP+Ingress<br/>Port: 8000"]
            DEP["Deployment"]
            
            subgraph "Deployment"
                P1["Pod 1<br/>cloud-artifact-extractor<br/>Container port 8000"]
                P2["Pod 2<br/>cloud-artifact-extractor<br/>Container port 8000"]
                PN["Pod N<br/>HPA managed<br/>Container port 8000"]
            end
            
            HPA["HPA<br/>Horizontal Pod Autoscaler<br/>Min replicas: 2<br/>Max replicas: 10<br/>Target CPU: 70%<br/>Target Memory: 80%"]
            
            PDB["Pod Disruption Budget<br/>Min available: 1 pod<br/>Protects during node maintenance"]
            
            CONF["Configuration & Secrets<br/>ConfigMap<br/>Secret<br/>Service Account"]
            
            NP["Network Policies<br/>Ingress: Allow from Ingress controller<br/>Egress: Allow to external services"]
            
            RBAC["RBAC<br/>Role-Based Access Control<br/>ServiceAccount<br/>Role/ClusterRole<br/>RoleBinding/ClusterRoleBinding"]
            
            MON["Monitoring & Logging<br/>ServiceMonitor<br/>Logs to Cloud provider logging<br/>Metrics to Cloud provider monitoring"]
            
            CJ["CronJob<br/>Optional Scheduled Extraction<br/>Schedule: 0 2 * * *<br/>Job: One-time extraction task"]
        end
        
        WN["Worker Nodes<br/>Cloud provider managed<br/>Auto-scaling group<br/>Health checks<br/>Container runtime"]
        
        REG["Container Registry<br/>ECR AWS<br/>ACR Azure<br/>GCR GCP"]
    end
    
    IC --> SVC
    SVC --> DEP
    DEP --> P1
    DEP --> P2
    DEP --> PN
    DEP --> HPA
    DEP --> PDB
    DEP --> CONF
    DEP --> NP
    DEP --> RBAC
    DEP --> MON
    DEP --> CJ
    DEP -.-> WN
    DEP -.-> REG
    
    style NS fill:#e1f5fe
    style IC fill:#f3e5f5
    style SVC fill:#e8f5e8
    style DEP fill:#fff3e0
    style P1 fill:#fce4ec
    style P2 fill:#fce4ec
    style PN fill:#fce4ec
    style HPA fill:#f1f8e9
    style PDB fill:#e0f2f1
    style CONF fill:#fafafa
    style NP fill:#ffebee
    style RBAC fill:#e8eaf6
    style MON fill:#f3e5f5
    style CJ fill:#ede7f6
    style WN fill:#e0f7fa
    style REG fill:#f9fbe7
```

### Data Flow

```mermaid
flowchart TD
    CR[Client Request<br/>HTTP/HTTPS] --> IG[Kubernetes Ingress / Load Balancer]
    IG --> SVC[Service<br/>routing to pods]
    SVC --> POD[Pod Replicas<br/>distributed processing]
    
    POD --> EXTRACT_AWS[Extract resources from AWS<br/>using IAM role/Workload Identity]
    POD --> EXTRACT_AZURE[Extract resources from Azure<br/>using Service Principal/Workload Identity]
    POD --> EXTRACT_GCP[Extract resources from GCP<br/>using Service Account/Workload Identity]
    
    EXTRACT_AWS --> HT[Send artifacts via HTTP Transport]
    EXTRACT_AZURE --> HT
    EXTRACT_GCP --> HT
    
    HT --> DEST[Policy Scanner / Filesystem / Null Transport]
    
    style CR fill:#e3f2fd
    style IG fill:#f3e5f5
    style SVC fill:#e8f5e8
    style POD fill:#fff3e0
    style HT fill:#fce4ec
    style DEST fill:#f1f8e9
```

---

## Common Architecture Patterns

### 1. Request Routing Flow

```mermaid
flowchart TD
    C[Client] --> ELB[External Load Balancer<br/>provided by platform]
    ELB --> SM[Service Mesh / Internal Load Balancer]
    SM --> AI[Application Instances<br/>Round-robin or intelligent routing]
    AI --> RC[Response back to Client]
    
    style C fill:#e3f2fd
    style ELB fill:#f3e5f5
    style SM fill:#e8f5e8
    style AI fill:#fff3e0
    style RC fill:#fce4ec
```

### 2. Configuration Management

```mermaid
flowchart TD
    EV[Environment Variables] --> AC[Application Configuration]
    AC --> CC[Cloud provider credentials]
    AC --> SE[Service endpoints]
    AC --> TS[Transport settings]
    AC --> FF[Feature flags]
    AC --> DS[Debug settings]
    
    style EV fill:#e1f5fe
    style AC fill:#f3e5f5
    style CC fill:#e8f5e8
    style SE fill:#fff3e0
    style TS fill:#fce4ec
    style FF fill:#f1f8e9
    style DS fill:#e0f2f1
```

### 3. External Integration Points

```mermaid
flowchart TD
    CAE[Cloud Artifact Extractor]
    CAE --> AWS_SVC[AWS Services<br/>via IAM role credentials]
    CAE --> AZURE_SVC[Azure Services<br/>via Service Principal / Managed Identity]
    CAE --> GCP_SVC[GCP Services<br/>via Service Account / Workload Identity]
    CAE --> ETE[External Transport Endpoint<br/>Policy Scanner]
    
    style CAE fill:#e1f5fe
    style AWS_SVC fill:#f3e5f5
    style AZURE_SVC fill:#e8f5e8
    style GCP_SVC fill:#fff3e0
    style ETE fill:#fce4ec
```

### 4. Observability Stack

```mermaid
flowchart TD
    AML[Application Metrics / Logs] --> CPM[Cloud Provider Monitoring]
    CPM --> AWS[CloudWatch<br/>AWS deployments]
    CPM --> AZURE[Azure Monitor<br/>Azure deployments]
    CPM --> GCP[Google Cloud Operations<br/>GCP deployments]
    CPM --> K8S[Kubernetes Metrics Server<br/>K8s deployments]
    K8S --> DAR[Dashboards, Alerts, and Reports]
    AWS --> DAR
    AZURE --> DAR
    GCP --> DAR
    
    style AML fill:#e1f5fe
    style CPM fill:#f3e5f5
    style AWS fill:#e8f5e8
    style AZURE fill:#fff3e0
    style GCP fill:#fce4ec
    style K8S fill:#f1f8e9
    style DAR fill:#e0f2f1
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
