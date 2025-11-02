---
layout: default
title: Kubernetes Deployment
parent: Deployment
nav_order: 6
---

# Kubernetes Deployment Guide

Deploy Cloud Artifact Extractor to Kubernetes clusters across AWS EKS, Azure AKS, and Google GKE.

## Quick Start

### For AWS EKS
```bash
bash deploy/kubernetes/aws-eks-deploy.sh
kubectl apply -f deploy/kubernetes/manifests/
```

### For Azure AKS
```bash
bash deploy/kubernetes/azure-aks-deploy.sh
kubectl apply -f deploy/kubernetes/manifests/
```

### For GCP GKE
```bash
bash deploy/kubernetes/gcp-gke-deploy.sh
kubectl apply -f deploy/kubernetes/manifests/
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│         Kubernetes Cluster (EKS/AKS/GKE)       │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐   │
│  │  Ingress / Load Balancer                │   │
│  └──────────────┬──────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │  Service (cloud-artifact-extractor)     │   │
│  └──────────────┬──────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │  Deployment / StatefulSet               │   │
│  │  ├─ Pod 1 (Replica 1)                   │   │
│  │  ├─ Pod 2 (Replica 2)                   │   │
│  │  └─ Pod N (HPA Managed)                 │   │
│  └──────────────┬──────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │  ConfigMap / Secrets / PVC              │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Prerequisites

- `kubectl` installed and configured
- Cloud provider CLI tool (aws, az, or gcloud)
- Appropriate permissions in target cluster
- Helm 3 (optional, for advanced deployments)

## Configuration

### Environment Variables
Configure in `manifests/configmap.yaml`:
```yaml
ENABLED_PROVIDERS: '["aws","azure","gcp"]'
DEBUG: 'false'
CONFIG_FILE: '/app/config/production.yaml'
SCANNER_ENDPOINT_URL: 'https://your-scanner-endpoint.com'
```

### Secrets
Configure in `manifests/secret.yaml`:
```yaml
JWT_SECRET_KEY: your-secret-key
AZURE_CLIENT_SECRET: your-azure-secret
AWS_SECRET_ACCESS_KEY: your-aws-secret
GOOGLE_APPLICATION_CREDENTIALS: base64-encoded-gcp-key
```

## Resource Management

### CPU and Memory Requests/Limits
```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi
```

Adjust based on workload:
- Light: 200m CPU, 512Mi memory
- Standard: 500m CPU, 1Gi memory
- Heavy: 1000m+ CPU, 2Gi+ memory

## Scaling

### Horizontal Pod Autoscaling (HPA)
```yaml
minReplicas: 2
maxReplicas: 20
targetCPUUtilizationPercentage: 70
targetMemoryUtilizationPercentage: 80
```

### Vertical Pod Autoscaling (VPA)
Enable VPA for automatic resource recommendation:
```bash
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-0.14.0/vpa-v0.14.0.yaml
```

## Monitoring & Logging

### Prometheus Metrics
ServiceMonitor is included for Prometheus scraping:
```yaml
prometheus:
  enabled: true
  interval: 30s
```

### Logging
- Stdout/stderr logs sent to cluster logging solution
- AWS EKS: CloudWatch Logs
- Azure AKS: Azure Monitor Logs
- GCP GKE: Cloud Logging

### Debugging
```bash
# View pod logs
kubectl logs -f deployment/cloud-artifact-extractor -n cloud-artifact-extractor

# Exec into pod
kubectl exec -it deployment/cloud-artifact-extractor -n cloud-artifact-extractor -- bash

# Describe pod
kubectl describe pod <pod-name> -n cloud-artifact-extractor

# Check events
kubectl get events -n cloud-artifact-extractor
```

## Network & Security

### Network Policies
Network policies restrict traffic to/from pods:
```bash
kubectl apply -f deploy/kubernetes/manifests/networkpolicy.yaml
```

### RBAC (Role-Based Access Control)
Service account with minimal permissions:
```bash
kubectl apply -f deploy/kubernetes/manifests/rbac.yaml
```

### Pod Security Standards
Enable Pod Security Standards:
```bash
kubectl label namespace cloud-artifact-extractor pod-security.kubernetes.io/enforce=restricted
```

## Ingress & Load Balancing

### With Ingress Controller
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cloud-artifact-extractor
spec:
  ingressClassName: nginx
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: cloud-artifact-extractor
            port:
              number: 8000
```

### With LoadBalancer Service
```yaml
type: LoadBalancer
ports:
- port: 80
  targetPort: 8000
```

## Storage

Persistent volumes for configuration or results:
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-pvc
  namespace: cloud-artifact-extractor
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF
```

## GitOps Deployment

### With Flux
```bash
flux install
flux create source git csp-scanner --url=https://github.com/your-org/csp-scanner --branch=main
flux create kustomization csp-scanner --source=csp-scanner --path="./deploy/kubernetes" --prune=true --interval=10m
```

### With ArgoCD
```bash
argocd app create cloud-artifact-extractor \
  --repo https://github.com/your-org/csp-scanner \
  --path deploy/kubernetes \
  --dest-server https://kubernetes.default.svc
```

## Deployment Strategies

### Blue-Green Deployment
```bash
# Create blue version
kubectl apply -f deploy/kubernetes/manifests/deployment.yaml
# Wait for pods to be ready
# Switch service to new version
```

### Canary Deployment
```bash
# Use Flagger for automated canary analysis
helm repo add flagger https://flagger.app
helm install flagger flagger/flagger --namespace flagger-system --create-namespace
```

### Rolling Update (Default)
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

## Troubleshooting

### Pod won't start
```bash
kubectl logs <pod-name> -n cloud-artifact-extractor
kubectl describe pod <pod-name> -n cloud-artifact-extractor
```

### High latency
```bash
kubectl top nodes
kubectl top pods -n cloud-artifact-extractor
```

### Scaling issues
```bash
kubectl describe hpa -n cloud-artifact-extractor
kubectl get events -n cloud-artifact-extractor
```

## Common Commands

```bash
# Get all resources
kubectl get all -n cloud-artifact-extractor

# Scale deployment
kubectl scale deployment/cloud-artifact-extractor --replicas=5 -n cloud-artifact-extractor

# Update image
kubectl set image deployment/cloud-artifact-extractor \
  cloud-artifact-extractor=myregistry/cloud-artifact-extractor:v2.0.0 \
  -n cloud-artifact-extractor

# Port forward
kubectl port-forward svc/cloud-artifact-extractor 8000:8000 -n cloud-artifact-extractor

# Get service info
kubectl get svc cloud-artifact-extractor -n cloud-artifact-extractor
```

## Advanced Topics

### Service Mesh (Istio)
```bash
# Install Istio
istioctl install --set profile=demo -y

# Enable sidecar injection
kubectl label namespace cloud-artifact-extractor istio-injection=enabled
```

### Multi-Region Deployment
For multi-region deployments, deploy to each regional cluster and use:
- Global load balancer (AWS Route 53, Azure Traffic Manager, GCP Cloud Load Balancer)
- Cross-cluster service discovery
- Database replication

### High Availability
- Run multiple replicas (minReplicas >= 2)
- Use pod disruption budgets
- Implement proper health checks
- Use node affinity/anti-affinity rules

## Next Steps

1. Choose your cloud provider (EKS/AKS/GKE or self-managed)
2. Run the appropriate deployment script
3. Review and customize manifest files
4. Apply manifests to your cluster
5. Set up monitoring and alerts
6. Implement GitOps for continuous deployment

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Azure AKS Best Practices](https://docs.microsoft.com/en-us/azure/aks/best-practices)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Kubernetes Security](https://kubernetes.io/docs/concepts/security/)