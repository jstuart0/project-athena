# Kubernetes Deployment Strategy - Helm Charts & GPU Support
**Date:** 2025-11-11
**Status:** Planning - Open-Source Release
**Related:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Guest Mode & Quality Tracking](2025-11-11-guest-mode-and-quality-tracking.md)
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md)

## Executive Summary

This plan defines the **Kubernetes deployment strategy** for Project Athena, enabling deployment on K8s clusters with optional GPU support. The primary goal is to make the open-source release easily deployable on various Kubernetes environments while maintaining the Docker Compose approach for the production Baltimore deployment.

**Key Points:**
- ✅ **Helm charts** for all services (umbrella + subcharts)
- ✅ **GPU support** (NVIDIA + AMD ROCm)
- ✅ **Multiple profiles** (dev/GPU/bare-metal/cloud)
- ✅ **Ingress + TLS** (cert-manager)
- ✅ **Autoscaling** (HPA + optional KEDA)
- ✅ **Observability** (Prometheus + Grafana)
- ✅ **Security** (NetworkPolicies, RBAC, External Secrets)

**Production Note:** The Baltimore deployment will **remain Docker Compose** on Mac Studio/mini for simplicity and lowest latency. Kubernetes is for the **open-source community** and future expansion.

---

## 1) Packaging Strategy

### Helm Chart Structure

**Umbrella Chart:** `charts/athena`

Contains dependencies on all service subcharts:

```yaml
# charts/athena/Chart.yaml
apiVersion: v2
name: athena
version: 1.0.0
description: Project Athena - Privacy-First AI Voice Assistant
dependencies:
  - name: orchestrator
    version: 1.0.0
    repository: "file://../orchestrator"
  - name: mode-service
    version: 1.0.0
    repository: "file://../mode-service"
  - name: ha-bridge
    version: 1.0.0
    repository: "file://../ha-bridge"
  - name: stt
    version: 1.0.0
    repository: "file://../stt"
  - name: tts
    version: 1.0.0
    repository: "file://../tts"
  - name: router-small-llm
    version: 1.0.0
    repository: "file://../router-small-llm"
  - name: router-large-llm
    version: 1.0.0
    repository: "file://../router-large-llm"
  - name: rag-api
    version: 1.0.0
    repository: "file://../rag-api"
  - name: admin
    version: 1.0.0
    repository: "file://../admin"
  - name: qdrant
    version: 0.7.0
    repository: "https://qdrant.github.io/qdrant-helm"
    condition: qdrant.enabled
  - name: redis
    version: 17.11.0
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
  - name: kube-prometheus-stack
    version: 45.0.0
    repository: "https://prometheus-community.github.io/helm-charts"
    condition: prometheus.enabled
```

### Subchart List

**Core Services:**
1. **orchestrator** - LangGraph gateway, main orchestration
2. **mode-service** - Guest/owner mode detection, Airbnb calendar
3. **ha-bridge** - Home Assistant integration bridge (optional)

**Voice Services:**
4. **stt** - Speech-to-Text (Faster-Whisper)
5. **tts** - Text-to-Speech (Piper/Coqui)

**LLM Services:**
6. **router-small-llm** - Fast commands, intent classification (3-4B model)
7. **router-large-llm** - Complex reasoning, RAG (7-8B model)

**Knowledge Services:**
8. **rag-api** - RAG connectors gateway (FastAPI)
9. **qdrant** - Vector database (official Qdrant chart or subchart)

**Admin:**
10. **admin** - Admin interface (Next.js + FastAPI)

**Infrastructure (Dependencies):**
11. **redis** - Caching, queues, sessions (Bitnami chart)
12. **kube-prometheus-stack** - Prometheus + Grafana (community chart)
13. **opentelemetry-collector** - Optional tracing

### Deployment Profiles

**values-dev.yaml** - Development/Testing
```yaml
# CPU-only, minimal resources, NodePort services
gpu:
  enabled: false

orchestrator:
  replicaCount: 1
  service:
    type: NodePort

routerLarge:
  replicaCount: 1
  resources:
    requests: { cpu: "2", memory: "4Gi" }
    limits: { cpu: "4", memory: "8Gi" }

qdrant:
  persistence:
    enabled: false  # Ephemeral storage for dev

redis:
  master:
    persistence:
      enabled: false
```

**values-gpu.yaml** - GPU-Enabled Production
```yaml
# NVIDIA GPUs enabled, larger models, GPU scheduling
gpu:
  enabled: true
  vendor: nvidia  # or amd
  nodeSelector:
    athena.gpu: "true"
  tolerations:
    - key: "athena.gpu"
      operator: "Exists"
      effect: "NoSchedule"

routerLarge:
  replicaCount: 1
  gpu:
    enabled: true
    count: 1
  resources:
    requests: { cpu: "4", memory: "16Gi" }
    limits: { nvidia.com/gpu: 1, memory: "24Gi" }

stt:
  gpu:
    enabled: false  # CPU is often sufficient for Whisper tiny/base
  resources:
    requests: { cpu: "2", memory: "4Gi" }
    limits: { cpu: "4", memory: "8Gi" }
```

**values-baremetal.yaml** - Bare-Metal Deployment
```yaml
# MetalLB for LoadBalancer, local storage (Longhorn/Rook)
ingress:
  className: nginx
  host: athena.local
  tls:
    enabled: true
    issuer: letsencrypt-prod

orchestrator:
  service:
    type: LoadBalancer
    loadBalancerIP: 192.168.60.50  # MetalLB pool

qdrant:
  persistence:
    enabled: true
    storageClass: longhorn
    size: 50Gi

redis:
  master:
    persistence:
      storageClass: longhorn
      size: 8Gi
```

**values-cloud.yaml** - Cloud Provider (AWS/GCP/Azure)
```yaml
# Cloud LoadBalancer, CSI storage classes
ingress:
  className: nginx
  host: athena.example.com
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod

orchestrator:
  service:
    type: LoadBalancer
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-type: "nlb"

qdrant:
  persistence:
    enabled: true
    storageClass: gp3  # AWS EBS gp3, or pd-ssd (GCP), azuredisk (Azure)
    size: 100Gi

redis:
  master:
    persistence:
      storageClass: gp3
      size: 20Gi
```

### Repository Layout

```
deploy/k8s/
├── charts/
│   ├── athena/                      # Umbrella chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml              # Default values
│   │   ├── templates/
│   │   │   ├── namespace.yaml
│   │   │   ├── networkpolicy.yaml
│   │   │   └── servicemonitor.yaml
│   │   └── README.md
│   │
│   ├── orchestrator/                # Subchart: Orchestrator
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── templates/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── configmap.yaml
│   │   │   ├── hpa.yaml
│   │   │   └── servicemonitor.yaml
│   │   └── README.md
│   │
│   ├── mode-service/                # Subchart: Mode Service
│   ├── ha-bridge/                   # Subchart: HA Bridge
│   ├── stt/                         # Subchart: STT
│   ├── tts/                         # Subchart: TTS
│   ├── router-small-llm/            # Subchart: Small LLM
│   ├── router-large-llm/            # Subchart: Large LLM
│   ├── rag-api/                     # Subchart: RAG API
│   └── admin/                       # Subchart: Admin Interface
│
├── profiles/
│   ├── values-dev.yaml              # Development profile
│   ├── values-gpu.yaml              # GPU-enabled profile
│   ├── values-baremetal.yaml        # Bare-metal profile
│   └── values-cloud.yaml            # Cloud provider profile
│
├── examples/
│   ├── argocd/
│   │   └── application.yaml         # ArgoCD Application
│   ├── kustomize/
│   │   ├── base/
│   │   └── overlays/
│   │       ├── dev/
│   │       ├── gpu/
│   │       └── production/
│   └── secrets/
│       ├── external-secrets.yaml    # External Secrets Operator
│       └── sops-secret.yaml         # SOPS-encrypted secrets
│
├── docs/
│   ├── GPU_SETUP.md                 # NVIDIA + AMD setup guide
│   ├── STORAGE.md                   # Storage backends guide
│   ├── INGRESS.md                   # Ingress + TLS guide
│   ├── SECRETS.md                   # Secrets management guide
│   ├── AUTOSCALING.md               # HPA + KEDA guide
│   └── TROUBLESHOOTING.md           # Common K8s issues
│
└── scripts/
    ├── install.sh                   # Quick install script
    ├── setup-gpu-nodes.sh           # GPU node setup
    └── uninstall.sh                 # Clean uninstall
```

---

## 2) GPU Support (Kubernetes)

### Prerequisites (NVIDIA)

**Cluster Requirements:**
- Kubernetes 1.25+
- containerd (or Docker with nvidia-docker2)
- GPU nodes with NVIDIA drivers installed

**Setup Steps:**

1. **Install NVIDIA Drivers on GPU Nodes:**
```bash
# On each GPU node (Ubuntu example)
sudo apt-get update
sudo apt-get install -y nvidia-driver-535
sudo reboot

# Verify
nvidia-smi
```

2. **Install nvidia-container-toolkit:**
```bash
# On each GPU node
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart containerd
```

3. **Deploy NVIDIA Device Plugin:**
```bash
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml
```

4. **Verify GPU Available:**
```bash
kubectl get nodes -o json | jq '.items[].status.capacity'
# Should show: "nvidia.com/gpu": "1" (or more)
```

**Optional: Enable MIG (Multi-Instance GPU) on A100/A30:**
```bash
# On GPU node
sudo nvidia-smi -mig 1

# Configure MIG instances (example: 1g.10gb slices)
sudo nvidia-smi mig -cgi 9,9,9,9,9,9,9 -C

# Update device plugin with MIG strategy
kubectl patch daemonset nvidia-device-plugin-daemonset \
  -n kube-system \
  --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/env/-", "value": {"name": "MIG_STRATEGY", "value": "mixed"}}]'
```

### Prerequisites (AMD ROCm)

**Cluster Requirements:**
- Kubernetes 1.25+
- GPU nodes with ROCm stack installed

**Setup Steps:**

1. **Install ROCm on GPU Nodes:**
```bash
# On each GPU node (Ubuntu example)
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_5.4.50400-1_all.deb
sudo dpkg -i amdgpu-install_5.4.50400-1_all.deb
sudo amdgpu-install --usecase=rocm
sudo reboot

# Verify
rocm-smi
```

2. **Deploy ROCm Device Plugin:**
```bash
kubectl create -f https://raw.githubusercontent.com/RadeonOpenCompute/k8s-device-plugin/master/k8s-ds-amdgpu-dp.yaml
```

3. **Verify GPU Available:**
```bash
kubectl get nodes -o json | jq '.items[].status.capacity'
# Should show: "amd.com/gpu": "1" (or more)
```

### GPU Node Scheduling

**Label GPU Nodes:**
```bash
kubectl label node <gpu-node-1> athena.gpu=true
kubectl label node <gpu-node-2> athena.gpu=true
```

**Taint GPU Nodes (Optional - Keeps Non-GPU Pods Off):**
```bash
kubectl taint nodes <gpu-node-1> athena.gpu=true:NoSchedule
kubectl taint nodes <gpu-node-2> athena.gpu=true:NoSchedule
```

**Helm Values for GPU Scheduling:**
```yaml
# values-gpu.yaml
gpu:
  enabled: true
  vendor: nvidia  # or amd

  # Applied to all GPU workloads
  nodeSelector:
    athena.gpu: "true"

  tolerations:
    - key: "athena.gpu"
      operator: "Exists"
      effect: "NoSchedule"
```

### GPU Resource Requests

**NVIDIA GPU:**
```yaml
# In router-large-llm deployment
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "24Gi"
  requests:
    cpu: "4"
    memory: "16Gi"
```

**NVIDIA MIG (Multi-Instance GPU):**
```yaml
resources:
  limits:
    nvidia.com/mig-1g.10gb: 1  # 1/7th of A100 (1g.10gb slice)
    memory: "12Gi"
  requests:
    cpu: "2"
    memory: "8Gi"
```

**AMD GPU:**
```yaml
resources:
  limits:
    amd.com/gpu: 1
    memory: "24Gi"
  requests:
    cpu: "4"
    memory: "16Gi"
```

---

## 3) Networking & Ingress

### Ingress Controller

**Recommended:** Nginx Ingress Controller or Traefik

**Install Nginx Ingress:**
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

### WebSocket Support

**Required for:** Admin Interface live metrics, device telemetry

**Nginx Configuration:**
```yaml
# In Ingress annotations
annotations:
  nginx.ingress.kubernetes.io/websocket-services: admin
  nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
  nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
```

### Bare-Metal LoadBalancer (MetalLB)

**Install MetalLB:**
```bash
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.10/config/manifests/metallb-native.yaml
```

**Configure IP Pool:**
```yaml
# metallb-config.yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: athena-pool
  namespace: metallb-system
spec:
  addresses:
    - 192.168.60.50-192.168.60.60  # Available IP range

---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: athena-l2
  namespace: metallb-system
spec:
  ipAddressPools:
    - athena-pool
```

**Apply:**
```bash
kubectl apply -f metallb-config.yaml
```

### TLS with cert-manager

**Install cert-manager:**
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml
```

**Create ClusterIssuer:**
```yaml
# letsencrypt-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

**Apply:**
```bash
kubectl apply -f letsencrypt-issuer.yaml
```

### Orchestrator Service (NodePort for LAN Devices)

**Wyoming devices need direct access to Orchestrator:**

```yaml
# templates/orchestrator-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}
spec:
  type: {{ .Values.orchestrator.service.type }}  # NodePort or LoadBalancer
  selector:
    app: orchestrator
  ports:
    - name: http
      port: 10700
      targetPort: 10700
      {{- if eq .Values.orchestrator.service.type "NodePort" }}
      nodePort: {{ .Values.orchestrator.service.nodePort | default 31070 }}
      {{- end }}
```

**Helm Values:**
```yaml
# values.yaml
orchestrator:
  service:
    type: NodePort
    port: 10700
    nodePort: 31070  # Static port for Wyoming device config
```

**Configure Wyoming Devices:**
- Point to: `<any-k8s-node-ip>:31070`
- Or use MetalLB LoadBalancer with static IP

---

## 4) Storage

### Storage Requirements

**Persistent Storage Needed For:**
1. **Qdrant (Vector DB):** 50-100GB (embeddings, indices)
2. **Ollama (Model Cache):** 50-100GB (model files)
3. **Redis (Optional):** 8-20GB (persistent cache, queues)
4. **Logs/Metrics (Optional):** 20-50GB (Loki, long-term Prometheus)

### Storage Backends

**Development:**
- `hostPath` or `local-path-provisioner`
- Ephemeral storage OK for testing

**Bare-Metal Production:**
- **Longhorn** (Rancher's distributed storage)
- **OpenEBS** (CNCF project)
- **Rook-Ceph** (Ceph on K8s)

**Cloud:**
- **AWS:** EBS CSI (gp3, io2)
- **GCP:** Persistent Disk CSI (pd-ssd, pd-balanced)
- **Azure:** Azure Disk CSI (Premium SSD, Standard SSD)

### Example PVC (Qdrant)

```yaml
# templates/qdrant-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: qdrant-data
  namespace: {{ .Release.Namespace }}
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ .Values.qdrant.persistence.storageClass }}
  resources:
    requests:
      storage: {{ .Values.qdrant.persistence.size }}
```

**Helm Values:**
```yaml
# values.yaml
qdrant:
  persistence:
    enabled: true
    storageClass: longhorn  # or gp3, pd-ssd, azuredisk
    size: 50Gi
```

### Storage Classes by Profile

**values-dev.yaml:**
```yaml
qdrant:
  persistence:
    enabled: false  # Ephemeral for dev
```

**values-baremetal.yaml:**
```yaml
qdrant:
  persistence:
    enabled: true
    storageClass: longhorn
    size: 50Gi

redis:
  master:
    persistence:
      enabled: true
      storageClass: longhorn
      size: 8Gi
```

**values-cloud.yaml:**
```yaml
qdrant:
  persistence:
    enabled: true
    storageClass: gp3  # AWS
    size: 100Gi

redis:
  master:
    persistence:
      enabled: true
      storageClass: gp3
      size: 20Gi
```

### Backup Strategy

**Velero (Recommended):**
```bash
# Install Velero with cloud provider plugin
velero install \
  --provider aws \
  --bucket athena-backups \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1

# Create backup schedule
velero schedule create athena-daily \
  --schedule="0 2 * * *" \
  --include-namespaces athena-core,athena-ml
```

---

## 5) Secrets & Configuration

### Secrets Management Options

**Option 1: External Secrets Operator (Recommended)**

**Supports:**
- HashiCorp Vault
- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault
- Kubernetes Secrets (as source)

**Install External Secrets Operator:**
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace
```

**Example: Vault SecretStore + ExternalSecret:**
```yaml
# secretstore.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: athena-core
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "athena"
          serviceAccountRef:
            name: athena-sa

---
# externalsecret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: admin-secrets
  namespace: athena-core
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: admin-secrets
    creationPolicy: Owner
  data:
    - secretKey: OIDC_CLIENT_SECRET
      remoteRef:
        key: secret/athena/admin
        property: oidc_client_secret
    - secretKey: POSTGRES_PASSWORD
      remoteRef:
        key: secret/athena/admin
        property: postgres_password
```

**Option 2: SOPS-Encrypted Secrets**

**Encrypt secrets file:**
```bash
# Install SOPS
brew install sops

# Create secrets file
cat > secrets.yaml <<EOF
oidc_client_secret: super-secret-value
postgres_password: another-secret
EOF

# Encrypt with age key
sops --encrypt --age age1... secrets.yaml > secrets.enc.yaml

# Or encrypt with PGP
sops --encrypt --pgp your-key-id secrets.yaml > secrets.enc.yaml
```

**Deploy with Helm Secrets plugin:**
```bash
# Install helm-secrets plugin
helm plugin install https://github.com/jkroepke/helm-secrets

# Deploy with encrypted values
helm secrets install athena ./charts/athena \
  -f values.yaml \
  -f secrets.enc.yaml
```

**Option 3: Sealed Secrets**

**Install Sealed Secrets Controller:**
```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.20.5/controller.yaml
```

**Seal a secret:**
```bash
# Install kubeseal CLI
brew install kubeseal

# Create plain secret
kubectl create secret generic admin-secrets \
  --from-literal=OIDC_CLIENT_SECRET=super-secret \
  --dry-run=client -o yaml > secret.yaml

# Seal it
kubeseal -f secret.yaml -o yaml > sealed-secret.yaml

# Apply sealed secret (safe to commit to git)
kubectl apply -f sealed-secret.yaml
```

### Configuration Management

**Split public config (ConfigMap) and secrets (Secret):**

**ConfigMap for Public Config:**
```yaml
# templates/orchestrator-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: orchestrator-config
  namespace: {{ .Release.Namespace }}
data:
  LOG_LEVEL: "info"
  ENABLE_METRICS: "true"
  HA_URL: {{ .Values.ha.url | quote }}
  MODE_SERVICE_URL: "http://mode-service:8001"
  QDRANT_URL: "http://qdrant:6333"
```

**ExternalSecret for Secrets:**
```yaml
# templates/orchestrator-externalsecret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: orchestrator-secrets
  namespace: {{ .Release.Namespace }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: orchestrator-secrets
  data:
    - secretKey: HA_TOKEN
      remoteRef:
        key: secret/athena/ha
        property: token
    - secretKey: SERVICE_API_KEY
      remoteRef:
        key: secret/athena/orchestrator
        property: api_key
```

**Mount in Deployment:**
```yaml
# templates/orchestrator-deployment.yaml
spec:
  containers:
    - name: orchestrator
      envFrom:
        - configMapRef:
            name: orchestrator-config
        - secretRef:
            name: orchestrator-secrets
```

---

## 6) Observability

### Prometheus + Grafana (kube-prometheus-stack)

**Add as dependency in umbrella chart:**
```yaml
# charts/athena/Chart.yaml
dependencies:
  - name: kube-prometheus-stack
    version: 45.0.0
    repository: "https://prometheus-community.github.io/helm-charts"
    condition: prometheus.enabled
```

**Helm Values:**
```yaml
# values.yaml
prometheus:
  enabled: true

kube-prometheus-stack:
  prometheus:
    prometheusSpec:
      serviceMonitorSelector:
        matchLabels:
          release: athena
      retention: 30d
      storageSpec:
        volumeClaimTemplate:
          spec:
            storageClassName: longhorn
            resources:
              requests:
                storage: 50Gi

  grafana:
    enabled: true
    adminPassword: changeme  # Use secret in production
    dashboardProviders:
      dashboardproviders.yaml:
        apiVersion: 1
        providers:
          - name: 'athena'
            orgId: 1
            folder: 'Athena'
            type: file
            disableDeletion: false
            editable: true
            options:
              path: /var/lib/grafana/dashboards/athena
    dashboards:
      athena:
        athena-overview:
          gnetId: 12345  # Custom dashboard (to be created)
          datasource: Prometheus
```

### ServiceMonitor for Each Service

**Example: Orchestrator ServiceMonitor:**
```yaml
# charts/orchestrator/templates/servicemonitor.yaml
{{- if .Values.metrics.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}
  labels:
    release: athena  # Match prometheus.prometheusSpec.serviceMonitorSelector
spec:
  selector:
    matchLabels:
      app: orchestrator
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
{{- end }}
```

**Helm Values:**
```yaml
# charts/orchestrator/values.yaml
metrics:
  enabled: true
  port: 9090
```

### Grafana Dashboards as ConfigMaps

**Package dashboards with Helm:**
```yaml
# charts/athena/templates/grafana-dashboards.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: athena-grafana-dashboards
  namespace: {{ .Release.Namespace }}
  labels:
    grafana_dashboard: "1"
data:
  athena-overview.json: |
    {
      "dashboard": {
        "title": "Athena Overview",
        "panels": [
          {
            "title": "Request Rate",
            "targets": [
              {
                "expr": "rate(athena_requests_total[5m])"
              }
            ]
          }
        ]
      }
    }
```

### Optional: OpenTelemetry for Distributed Tracing

**Add OTel Collector:**
```yaml
# values.yaml
opentelemetry:
  enabled: false  # Optional

opentelemetry-collector:
  mode: deployment
  config:
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    exporters:
      jaeger:
        endpoint: "jaeger:14250"
      prometheus:
        endpoint: "0.0.0.0:8889"
    service:
      pipelines:
        traces:
          receivers: [otlp]
          exporters: [jaeger]
        metrics:
          receivers: [otlp]
          exporters: [prometheus]
```

---

## 7) Autoscaling

### Horizontal Pod Autoscaler (HPA)

**Prerequisites:**
- Metrics Server installed
- Resources requests defined on pods

**Install Metrics Server:**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**Example: STT HPA:**
```yaml
# charts/stt/templates/hpa.yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stt
  namespace: {{ .Release.Namespace }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stt
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
{{- end }}
```

**Helm Values:**
```yaml
# charts/stt/values.yaml
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 4
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### KEDA (Kubernetes Event-Driven Autoscaling)

**Use Case:** Scale based on Redis queue depth for STT/TTS

**Install KEDA:**
```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

**Example: Scale STT based on Redis Queue:**
```yaml
# templates/stt-scaledobject.yaml
{{- if .Values.keda.enabled }}
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: stt-scaler
  namespace: {{ .Release.Namespace }}
spec:
  scaleTargetRef:
    name: stt
  minReplicaCount: {{ .Values.keda.minReplicas }}
  maxReplicaCount: {{ .Values.keda.maxReplicas }}
  triggers:
    - type: redis
      metadata:
        address: redis:6379
        listName: stt_queue
        listLength: "5"  # Scale up when queue > 5
{{- end }}
```

**Helm Values:**
```yaml
# values.yaml
keda:
  enabled: false  # Optional
  minReplicas: 1
  maxReplicas: 10
```

---

## 8) Anti-Hallucination & Cross-Model Validation (K8s)

### Separate Deployments for Validator and Primary Model

**Architecture:**
- **Validator (CPU):** Fast, small model for confidence checks (3-4B)
- **Primary (GPU):** Larger model for complex reasoning (7-8B or 13B)

**Validator Deployment (CPU):**
```yaml
# charts/validator/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: validator
  namespace: {{ .Release.Namespace }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: validator
  template:
    metadata:
      labels:
        app: validator
    spec:
      # Force CPU nodes (no GPU)
      nodeSelector:
        athena.gpu: "false"  # Or omit athena.gpu label
      containers:
        - name: validator
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          args:
            - "--model"
            - "{{ .Values.model.name }}"  # e.g., phi-3-mini
            - "--device"
            - "cpu"
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
```

**Primary Model Deployment (GPU):**
```yaml
# charts/router-large-llm/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router-large-llm
  namespace: {{ .Release.Namespace }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: router-large-llm
  template:
    metadata:
      labels:
        app: router-large-llm
    spec:
      # GPU scheduling
      {{- if .Values.gpu.enabled }}
      nodeSelector:
        athena.gpu: "true"
      tolerations:
        - key: "athena.gpu"
          operator: "Exists"
          effect: "NoSchedule"
      {{- end }}
      containers:
        - name: router-large-llm
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          args:
            - "--model"
            - "{{ .Values.model.name }}"  # e.g., llama-3.1-8b
            {{- if .Values.gpu.enabled }}
            - "--device"
            - "cuda"
            {{- end }}
          resources:
            requests:
              cpu: "4"
              memory: "16Gi"
            limits:
              {{- if .Values.gpu.enabled }}
              nvidia.com/gpu: {{ .Values.gpu.count }}
              {{- end }}
              memory: "24Gi"
```

### Policy-Based Routing (ConfigMap)

**Orchestrator loads routing policy from ConfigMap:**
```yaml
# templates/orchestrator-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: orchestrator-policy
  namespace: {{ .Release.Namespace }}
data:
  routing.yaml: |
    validator:
      enabled: {{ .Values.validator.enabled }}
      endpoint: "http://validator:8000"
      timeout_ms: 500

    primary:
      endpoint: "http://router-large-llm:8000"
      timeout_ms: 5000

    cross_model:
      enabled: {{ .Values.crossModel.enabled }}
      quorum_size: {{ .Values.crossModel.quorumSize }}
      models:
        - "http://validator:8000"
        - "http://router-large-llm:8000"
        - "http://router-small-llm:8000"
```

**Hot-Reload ConfigMap:**
```python
# In orchestrator code
import yaml
from kubernetes import client, config, watch

def watch_configmap():
    config.load_incluster_config()
    v1 = client.CoreV1Api()

    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_config_map, namespace="athena-core"):
        if event['object'].metadata.name == "orchestrator-policy":
            policy = yaml.safe_load(event['object'].data['routing.yaml'])
            reload_routing_policy(policy)
```

---

## 9) Model Servers on Kubernetes

### Option A: Ollama (CPU/GPU)

**Deployment:**
```yaml
# charts/router-large-llm/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router-large-llm
  namespace: {{ .Release.Namespace }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: router-large-llm
  template:
    metadata:
      labels:
        app: router-large-llm
    spec:
      {{- if .Values.gpu.enabled }}
      nodeSelector:
        athena.gpu: "true"
      tolerations:
        - key: "athena.gpu"
          operator: "Exists"
          effect: "NoSchedule"
      {{- end }}
      containers:
        - name: ollama
          image: ollama/ollama:latest
          ports:
            - containerPort: 11434
              name: http
          env:
            - name: OLLAMA_HOST
              value: "0.0.0.0:11434"
          resources:
            requests:
              cpu: "2"
              memory: "8Gi"
            limits:
              {{- if .Values.gpu.enabled }}
              nvidia.com/gpu: 1
              {{- end }}
              memory: "18Gi"
          volumeMounts:
            - name: ollama-data
              mountPath: /root/.ollama
          lifecycle:
            postStart:
              exec:
                command:
                  - /bin/sh
                  - -c
                  - |
                    sleep 5
                    ollama pull {{ .Values.model.name }}
      volumes:
        - name: ollama-data
          persistentVolumeClaim:
            claimName: ollama-pvc
```

**PVC for Model Cache:**
```yaml
# templates/ollama-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-pvc
  namespace: {{ .Release.Namespace }}
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ .Values.storage.storageClass }}
  resources:
    requests:
      storage: {{ .Values.storage.size }}  # 50-100Gi for models
```

**Helm Values:**
```yaml
# charts/router-large-llm/values.yaml
image:
  repository: ollama/ollama
  tag: latest

model:
  name: llama3.1:8b

gpu:
  enabled: true
  count: 1

storage:
  storageClass: longhorn
  size: 100Gi
```

### Option B: vLLM (GPU - Faster Inference)

**Deployment:**
```yaml
# charts/router-large-llm/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router-large-llm
  namespace: {{ .Release.Namespace }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: router-large-llm
  template:
    metadata:
      labels:
        app: router-large-llm
    spec:
      nodeSelector:
        athena.gpu: "true"
      tolerations:
        - key: "athena.gpu"
          operator: "Exists"
          effect: "NoSchedule"
      containers:
        - name: vllm
          image: vllm/vllm-openai:latest
          args:
            - "--model"
            - "{{ .Values.model.name }}"  # e.g., meta-llama/Meta-Llama-3.1-8B-Instruct
            - "--dtype"
            - "{{ .Values.model.dtype }}"  # bfloat16, float16, auto
            - "--max-model-len"
            - "{{ .Values.model.maxLength }}"  # 4096, 8192, etc.
            - "--tensor-parallel-size"
            - "{{ .Values.gpu.count }}"  # Multi-GPU if available
          ports:
            - containerPort: 8000
              name: http
          resources:
            requests:
              cpu: "4"
              memory: "16Gi"
            limits:
              nvidia.com/gpu: {{ .Values.gpu.count }}
              memory: "24Gi"
          volumeMounts:
            - name: model-cache
              mountPath: /root/.cache/huggingface
      volumes:
        - name: model-cache
          persistentVolumeClaim:
            claimName: vllm-model-cache
```

**Helm Values:**
```yaml
# charts/router-large-llm/values.yaml
image:
  repository: vllm/vllm-openai
  tag: latest

model:
  name: meta-llama/Meta-Llama-3.1-8B-Instruct
  dtype: bfloat16
  maxLength: 8192

gpu:
  enabled: true
  count: 1  # Or 2+ for tensor parallelism
```

### Model Selection via Helm Values

**Switchable between Ollama and vLLM:**
```yaml
# values.yaml
routerLarge:
  backend: vllm  # or ollama

  ollama:
    image: ollama/ollama:latest
    model: llama3.1:8b

  vllm:
    image: vllm/vllm-openai:latest
    model: meta-llama/Meta-Llama-3.1-8B-Instruct
    dtype: bfloat16
```

**Template logic:**
```yaml
# templates/deployment.yaml
{{- if eq .Values.routerLarge.backend "ollama" }}
# Ollama container spec
{{- else if eq .Values.routerLarge.backend "vllm" }}
# vLLM container spec
{{- end }}
```

---

## 10) Wyoming/HA Voice Devices on Kubernetes

### Orchestrator Exposure to LAN

**Wyoming devices (HA Voice satellites) need direct network access to Orchestrator.**

**Option A: NodePort (Simple)**

```yaml
# charts/orchestrator/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}
spec:
  type: NodePort
  selector:
    app: orchestrator
  ports:
    - name: http
      port: 10700
      targetPort: 10700
      nodePort: {{ .Values.service.nodePort | default 31070 }}
```

**Configure Wyoming Devices:**
- Point to: `<any-k8s-node-ip>:31070`
- Easy, but requires static node IPs

**Option B: LoadBalancer with MetalLB (Recommended)**

```yaml
# charts/orchestrator/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}
  {{- if .Values.service.loadBalancerIP }}
  annotations:
    metallb.universe.tf/loadBalancerIPs: {{ .Values.service.loadBalancerIP }}
  {{- end }}
spec:
  type: LoadBalancer
  selector:
    app: orchestrator
  ports:
    - name: http
      port: 10700
      targetPort: 10700
```

**Helm Values:**
```yaml
# values-baremetal.yaml
orchestrator:
  service:
    type: LoadBalancer
    loadBalancerIP: 192.168.60.50  # Static IP from MetalLB pool
```

**Configure Wyoming Devices:**
- Point to: `192.168.60.50:10700`
- Stable IP, easier management

### Home Assistant Placement

**Option 1: HA Outside Cluster (Original Plan)**
- HA remains on Mac Studio via Docker
- ha-bridge pod in K8s talks to HA over LAN
- Simple, no migration needed

**Option 2: HA in Kubernetes (Advanced)**
- Deploy HA as a K8s workload (StatefulSet)
- Requires migration of HA config
- Better for full K8s deployments

**For OSS Release: Support Both Options**

**Helm Values:**
```yaml
# values.yaml
ha:
  deployment: external  # or kubernetes

  # If external
  external:
    url: "https://192.168.10.168:8123"
    tokenSecretName: ha-token  # User creates this secret

  # If kubernetes
  kubernetes:
    enabled: false
    image: homeassistant/home-assistant:latest
    persistence:
      enabled: true
      size: 20Gi
```

---

## 11) OSS: Make it Switchable (CPU vs GPU)

### Global GPU Toggle

**Top-level switch in values.yaml:**
```yaml
# values.yaml
gpu:
  enabled: false  # Set to true for GPU deployments
  vendor: nvidia  # or amd

  # Global GPU scheduling (applied to all GPU workloads)
  nodeSelector:
    athena.gpu: "true"

  tolerations:
    - key: "athena.gpu"
      operator: "Exists"
      effect: "NoSchedule"

  # Per-service GPU allocation
  resources:
    stt:
      gpu: 0  # CPU is sufficient for Whisper tiny/base
    tts:
      gpu: 0  # CPU is sufficient for Piper
    routerSmall:
      gpu: 0  # Small models run fine on CPU
    routerLarge:
      gpu: 1  # Large model benefits from GPU
    validator:
      gpu: 0  # Validator stays on CPU
```

### Conditional GPU Resources in Templates

**Example: router-large-llm deployment:**
```yaml
# charts/router-large-llm/templates/deployment.yaml
spec:
  template:
    spec:
      {{- if .Values.gpu.enabled }}
      nodeSelector:
        {{- toYaml .Values.gpu.nodeSelector | nindent 8 }}
      tolerations:
        {{- toYaml .Values.gpu.tolerations | nindent 8 }}
      {{- end }}

      containers:
        - name: router-large-llm
          resources:
            requests:
              cpu: {{ .Values.resources.requests.cpu }}
              memory: {{ .Values.resources.requests.memory }}
            limits:
              {{- if and .Values.gpu.enabled (gt (int .Values.gpu.resources.routerLarge.gpu) 0) }}
              {{- if eq .Values.gpu.vendor "nvidia" }}
              nvidia.com/gpu: {{ .Values.gpu.resources.routerLarge.gpu }}
              {{- else if eq .Values.gpu.vendor "amd" }}
              amd.com/gpu: {{ .Values.gpu.resources.routerLarge.gpu }}
              {{- end }}
              {{- end }}
              memory: {{ .Values.resources.limits.memory }}
```

### CPU-Only Profile (values-dev.yaml)

```yaml
gpu:
  enabled: false

routerLarge:
  replicaCount: 1
  resources:
    requests: { cpu: "2", memory: "4Gi" }
    limits: { cpu: "4", memory: "8Gi" }
  model:
    name: phi-3-mini  # Smaller model for CPU
```

### GPU-Enabled Profile (values-gpu.yaml)

```yaml
gpu:
  enabled: true
  vendor: nvidia
  nodeSelector:
    athena.gpu: "true"
  tolerations:
    - key: "athena.gpu"
      operator: "Exists"
      effect: "NoSchedule"
  resources:
    routerLarge:
      gpu: 1

routerLarge:
  replicaCount: 1
  resources:
    requests: { cpu: "4", memory: "16Gi" }
    limits: { memory: "24Gi", nvidia.com/gpu: 1 }
  model:
    name: llama3.1:8b  # Larger model for GPU
```

---

## 12) CI/CD & GitOps

### GitHub Actions CI

**Build and push Docker images:**
```yaml
# .github/workflows/build.yml
name: Build and Push Images

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - orchestrator
          - mode-service
          - ha-bridge
          - stt
          - tts
          - rag-api
          - admin
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: ./apps/${{ matrix.service }}
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/${{ matrix.service }}:latest
            ghcr.io/${{ github.repository }}/${{ matrix.service }}:${{ github.sha }}
            ${{ startsWith(github.ref, 'refs/tags/v') && format('ghcr.io/{0}/{1}:{2}', github.repository, matrix.service, github.ref_name) || '' }}
```

**Package and publish Helm chart:**
```yaml
# .github/workflows/helm.yml
name: Package and Publish Helm Chart

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  helm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Helm
        uses: azure/setup-helm@v3

      - name: Package chart
        run: |
          helm package deploy/k8s/charts/athena

      - name: Publish to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: .
          keep_files: true
```

### ArgoCD Application

**Example Application manifest:**
```yaml
# examples/argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: athena
  namespace: argocd
spec:
  project: default

  source:
    repoURL: https://github.com/yourorg/project-athena
    targetRevision: main
    path: deploy/k8s/charts/athena
    helm:
      valueFiles:
        - ../../profiles/values-gpu.yaml
      values: |
        ingress:
          host: athena.example.com

  destination:
    server: https://kubernetes.default.svc
    namespace: athena-core

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

**Deploy with ArgoCD:**
```bash
kubectl apply -f examples/argocd/application.yaml
```

### Kustomize Overlays (Alternative to Helm)

**Structure:**
```
examples/kustomize/
├── base/
│   ├── kustomization.yaml
│   ├── orchestrator/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── ...
└── overlays/
    ├── dev/
    │   └── kustomization.yaml
    ├── gpu/
    │   ├── kustomization.yaml
    │   └── gpu-patch.yaml
    └── production/
        └── kustomization.yaml
```

**Deploy with Kustomize:**
```bash
kubectl apply -k examples/kustomize/overlays/gpu
```

---

## 13) Security

### Network Policies

**Isolate namespaces with NetworkPolicies:**

**Namespace Structure:**
- `athena-core` - Orchestrator, Mode Service, HA Bridge
- `athena-ml` - LLM, STT, TTS, RAG API, Qdrant
- `athena-admin` - Admin Interface
- `observability` - Prometheus, Grafana

**Example: athena-core NetworkPolicy:**
```yaml
# templates/networkpolicy-core.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: athena-core-policy
  namespace: athena-core
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # Allow from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx

    # Allow from athena-admin (for admin API calls)
    - from:
        - namespaceSelector:
            matchLabels:
              name: athena-admin

    # Allow from athena-ml (for model inference)
    - from:
        - namespaceSelector:
            matchLabels:
              name: athena-ml

  egress:
    # Allow to athena-ml
    - to:
        - namespaceSelector:
            matchLabels:
              name: athena-ml

    # Allow to kube-dns
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53

    # Allow to external HA (if outside cluster)
    - to:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 8123

    # Allow to internet (for Airbnb calendar, etc.)
    - to:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 443
```

**Example: athena-ml NetworkPolicy:**
```yaml
# templates/networkpolicy-ml.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: athena-ml-policy
  namespace: athena-ml
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # Only allow from athena-core
    - from:
        - namespaceSelector:
            matchLabels:
              name: athena-core

  egress:
    # Allow to kube-dns
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53

    # Allow to HuggingFace for model downloads
    - to:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 443
```

### RBAC Service Accounts

**Create service account per component:**
```yaml
# templates/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "watch", "list"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: orchestrator
  namespace: {{ .Release.Namespace }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: orchestrator
subjects:
  - kind: ServiceAccount
    name: orchestrator
    namespace: {{ .Release.Namespace }}
```

**Use in deployment:**
```yaml
spec:
  template:
    spec:
      serviceAccountName: orchestrator
```

### Pod Security Standards

**Enable PodSecurity admission:**
```yaml
# Apply to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: athena-core
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Baseline policy allows:**
- Non-root containers
- No privileged escalation
- Restricted volume types

**Restricted policy additionally requires:**
- Running as non-root user
- Dropping all capabilities
- Read-only root filesystem

**Example deployment with restricted policy:**
```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: orchestrator
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp

      volumes:
        - name: tmp
          emptyDir: {}
```

---

## 14) Example Helm Values (Complete)

### values.yaml (Base)

```yaml
# Global settings
global:
  domain: athena.local
  namespace: athena-core

# GPU configuration
gpu:
  enabled: false
  vendor: nvidia  # or amd
  nodeSelector:
    athena.gpu: "true"
  tolerations:
    - key: "athena.gpu"
      operator: "Exists"
      effect: "NoSchedule"
  resources:
    stt: { gpu: 0 }
    tts: { gpu: 0 }
    routerSmall: { gpu: 0 }
    routerLarge: { gpu: 1 }
    validator: { gpu: 0 }

# Ingress
ingress:
  enabled: true
  className: nginx
  host: athena.local
  tls:
    enabled: false
    issuer: letsencrypt-prod

# Orchestrator
orchestrator:
  replicaCount: 1
  image:
    repository: ghcr.io/yourorg/orchestrator
    tag: latest
  service:
    type: ClusterIP
    port: 10700
  resources:
    requests: { cpu: "1", memory: "2Gi" }
    limits: { cpu: "2", memory: "4Gi" }
  autoscaling:
    enabled: false
    minReplicas: 1
    maxReplicas: 4
    targetCPUUtilizationPercentage: 70
  metrics:
    enabled: true

# Mode Service
modeService:
  replicaCount: 1
  image:
    repository: ghcr.io/yourorg/mode-service
    tag: latest
  service:
    port: 8001
  airbnb:
    calendarUrl: ""  # Set via secret
    pollIntervalMinutes: 10

# STT (Speech-to-Text)
stt:
  replicaCount: 1
  image:
    repository: ghcr.io/yourorg/stt
    tag: latest
  model:
    name: whisper-tiny.en
  resources:
    requests: { cpu: "2", memory: "4Gi" }
    limits: { cpu: "4", memory: "8Gi" }
  autoscaling:
    enabled: true
    minReplicas: 1
    maxReplicas: 4
    targetCPUUtilizationPercentage: 70

# TTS (Text-to-Speech)
tts:
  replicaCount: 1
  image:
    repository: ghcr.io/yourorg/tts
    tag: latest
  model:
    name: piper
  resources:
    requests: { cpu: "1", memory: "2Gi" }
    limits: { cpu: "2", memory: "4Gi" }

# Router Small LLM
routerSmall:
  replicaCount: 1
  backend: ollama  # or vllm
  image:
    repository: ollama/ollama
    tag: latest
  model:
    name: phi-3-mini
  resources:
    requests: { cpu: "2", memory: "4Gi" }
    limits: { cpu: "4", memory: "8Gi" }

# Router Large LLM
routerLarge:
  replicaCount: 1
  backend: ollama  # or vllm
  image:
    repository: ollama/ollama
    tag: latest
  model:
    name: llama3.1:8b
  resources:
    requests: { cpu: "4", memory: "16Gi" }
    limits: { cpu: "8", memory: "24Gi" }
  persistence:
    enabled: true
    size: 100Gi
    storageClass: longhorn

# RAG API
ragApi:
  replicaCount: 1
  image:
    repository: ghcr.io/yourorg/rag-api
    tag: latest
  resources:
    requests: { cpu: "1", memory: "2Gi" }
    limits: { cpu: "2", memory: "4Gi" }

# Qdrant (Vector DB)
qdrant:
  enabled: true
  persistence:
    enabled: true
    size: 50Gi
    storageClass: longhorn

# Redis
redis:
  enabled: true
  master:
    persistence:
      enabled: true
      size: 8Gi
      storageClass: longhorn

# Admin Interface
admin:
  replicaCount: 1
  image:
    repository: ghcr.io/yourorg/admin
    tag: latest
  service:
    port: 3000
  oidc:
    issuerUrl: "https://auth.example.com/realms/home"
    clientId: "athena-admin"
    # clientSecret via secret
  database:
    host: postgres
    port: 5432
    name: athena_admin
    # credentials via secret

# Home Assistant
ha:
  deployment: external  # or kubernetes
  external:
    url: "https://192.168.10.168:8123"
    # token via secret

# Prometheus & Grafana
prometheus:
  enabled: true

kube-prometheus-stack:
  prometheus:
    prometheusSpec:
      retention: 30d
      storageSpec:
        volumeClaimTemplate:
          spec:
            storageClassName: longhorn
            resources:
              requests:
                storage: 50Gi
  grafana:
    enabled: true
    adminPassword: changeme
```

### values-gpu.yaml (GPU Override)

```yaml
gpu:
  enabled: true
  vendor: nvidia
  resources:
    routerLarge:
      gpu: 1

routerLarge:
  backend: vllm
  image:
    repository: vllm/vllm-openai
    tag: latest
  model:
    name: meta-llama/Meta-Llama-3.1-8B-Instruct
    dtype: bfloat16
  resources:
    requests: { cpu: "4", memory: "16Gi" }
    limits: { memory: "24Gi", nvidia.com/gpu: 1 }

stt:
  # Can optionally enable GPU for large Whisper models
  # resources:
  #   limits:
  #     nvidia.com/gpu: 1
```

---

## 15) Documentation to Ship with OSS

### GPU_SETUP.md

**Contents:**
- NVIDIA driver installation (Ubuntu, CentOS, Arch)
- nvidia-container-toolkit setup
- NVIDIA Device Plugin deployment
- MIG setup (A100/A30)
- AMD ROCm driver installation
- ROCm device plugin deployment
- GPU node labeling and tainting
- Troubleshooting (nvidia-smi, pod scheduling)

### STORAGE.md

**Contents:**
- Storage requirements per service
- Longhorn installation and configuration
- OpenEBS installation and configuration
- Rook-Ceph installation and configuration
- Cloud CSI (AWS EBS, GCP PD, Azure Disk)
- PVC examples
- Backup with Velero
- Disaster recovery procedures

### INGRESS.md

**Contents:**
- Nginx Ingress Controller installation
- Traefik installation
- WebSocket configuration
- MetalLB installation and IP pool setup
- cert-manager installation
- ClusterIssuer configuration (Let's Encrypt)
- TLS certificate management
- Troubleshooting DNS and certificates

### SECRETS.md

**Contents:**
- External Secrets Operator installation
- Vault integration setup
- AWS Secrets Manager integration
- GCP Secret Manager integration
- SOPS-encrypted secrets workflow
- Sealed Secrets setup
- Secret rotation procedures
- Best practices

### AUTOSCALING.md

**Contents:**
- Metrics Server installation
- HPA configuration examples
- KEDA installation
- Redis queue-based scaling
- Custom metrics with Prometheus Adapter
- Scaling strategies by service
- Cost optimization tips

### HA_NETWORK.md

**Contents:**
- Exposing Orchestrator to LAN (NodePort vs LoadBalancer)
- Wyoming device configuration
- Static IP allocation
- Firewall rules
- HA Voice preview device setup
- Troubleshooting connectivity

### PERFORMANCE.md

**Contents:**
- Replica recommendations by workload
- Pinning validator to CPU, large model to GPU
- Model quantization strategies
- PodAffinity/AntiAffinity for spreading
- Resource limits tuning
- Caching strategies
- Benchmarking tools

---

## 16) What Changes for Production (Baltimore Deployment)?

### No Change Needed

**The Baltimore production deployment will remain Docker Compose on Mac Studio + Mac mini.**

**Reasons:**
- ✅ **Simplicity:** Docker Compose is easier to manage for single-host deployment
- ✅ **Lowest Latency:** No network overhead between services
- ✅ **Direct GPU Access:** Metal acceleration on Mac Studio (no NVIDIA runtime needed)
- ✅ **Proven Stable:** Docker Compose is battle-tested for this use case

### When to Consider Kubernetes for Production?

**Future scenarios:**
1. **Add Linux GPU Node:** If you later add a separate Linux machine with NVIDIA GPU:
   - Move large-LLM to K8s on GPU node
   - Keep rest of services on Mac Studio Docker
   - Hybrid deployment via endpoint config

2. **High Availability:** If you want redundancy:
   - Deploy orchestrator, mode-service, rag-api to K8s with replicas
   - Keep STT/TTS/LLM on Mac Studio for performance

3. **Multi-Property:** If you deploy Athena to multiple Airbnb properties:
   - Each property gets a namespace
   - Shared LLM/RAG infrastructure
   - Per-property mode-service and orchestrator

### How to Migrate Later (If Desired)

**Step 1: Deploy K8s alongside Docker**
- Services stay on Docker (Mac Studio/mini)
- Deploy K8s cluster on separate hardware
- Point orchestrator endpoints to Docker services

**Step 2: Migrate one service at a time**
- Start with stateless services (rag-api, validator)
- Move to K8s, update orchestrator config
- Test thoroughly before next service

**Step 3: Move GPU workloads last**
- Large-LLM moved to Linux GPU node in K8s
- STT/TTS can stay on Mac Studio (fast enough on CPU)

---

## 17) Installation Quickstart (OSS)

### One-Command Install

**Install script:**
```bash
# scripts/install.sh
#!/bin/bash
set -e

echo "🚀 Installing Project Athena on Kubernetes..."

# Check prerequisites
command -v kubectl >/dev/null 2>&1 || { echo "kubectl not found"; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "helm not found"; exit 1; }

# Add Helm repo
helm repo add athena https://yourorg.github.io/project-athena/
helm repo update

# Prompt for profile
read -p "Select profile (dev/gpu/baremetal/cloud): " PROFILE

# Install
helm install athena athena/athena \
  --namespace athena-core \
  --create-namespace \
  -f https://raw.githubusercontent.com/yourorg/project-athena/main/deploy/k8s/profiles/values-${PROFILE}.yaml

echo "✅ Project Athena installed!"
echo "📊 Check status: kubectl get pods -n athena-core"
echo "🌐 Configure ingress host and visit: http://athena.local"
```

**Usage:**
```bash
curl -sSL https://raw.githubusercontent.com/yourorg/project-athena/main/scripts/install.sh | bash
```

### Manual Install

```bash
# Clone repo
git clone https://github.com/yourorg/project-athena.git
cd project-athena

# Install with Helm
helm install athena ./deploy/k8s/charts/athena \
  --namespace athena-core \
  --create-namespace \
  -f ./deploy/k8s/profiles/values-gpu.yaml \
  --set ingress.host=athena.example.com \
  --set gpu.enabled=true

# Watch deployment
kubectl get pods -n athena-core -w

# Check status
helm status athena -n athena-core
```

---

## Conclusion

This comprehensive Kubernetes deployment strategy enables:

✅ **Flexible Deployment:** CPU-only dev to multi-GPU production
✅ **Cloud-Ready:** Works on AWS, GCP, Azure, bare-metal
✅ **GPU Support:** NVIDIA and AMD with optional MIG
✅ **Scalable:** HPA + KEDA for autoscaling
✅ **Observable:** Prometheus + Grafana out-of-the-box
✅ **Secure:** NetworkPolicies, RBAC, External Secrets
✅ **GitOps-Ready:** ArgoCD + Kustomize examples
✅ **OSS-Friendly:** Easy install, multiple profiles, great docs

**Production Note:** The Baltimore deployment remains Docker Compose for simplicity and performance. Kubernetes is for the open-source community and future expansion scenarios.

**Next Steps:**
1. Build Docker images for all services
2. Create Helm charts following this structure
3. Test on development cluster (Minikube/kind)
4. Test on bare-metal cluster with Longhorn
5. Test GPU scheduling on NVIDIA node
6. Write comprehensive documentation
7. Publish Helm chart to GitHub Pages
8. Create install script and quickstart guide
9. Test ArgoCD deployment
10. Release to open-source community!
