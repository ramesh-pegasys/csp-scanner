# GCP Extractors Implementation Plan

## Current Status
Currently implemented: `compute`, `storage`, `networking`, `iam`, `kubernetes`

## Comprehensive GCP Extractors List

### High Priority (Core Infrastructure & Security)

1. **networking** ✅ - VPC networks, subnets, firewalls, load balancers
   - Resource types: `network`, `subnetwork`, `firewall`, `backend-service`, `url-map`, `target-proxy`, `forwarding-rule`
   - Configuration: max_workers, include_firewall_rules, include_load_balancers
   - Security focus: Firewall rules analysis, network exposure assessment

2. **iam** ✅ - Identity and Access Management
   - Resource types: `service-account`, `iam-policy`, `role`, `workload-identity-pool`
   - Configuration: include_service_accounts, include_policies, detailed_policy_analysis, include_workload_identity
   - Security focus: Service account keys, overly permissive roles, unused accounts

3. **compute** ✅ - Compute Engine resources
   - Resource types: `instance`, `instance-group`, `disk`, `snapshot`, `image`, `instance-template`
   - Configuration: max_workers, include_stopped_instances, include_instance_groups, include_disks
   - Security focus: Public IP exposure, disk encryption, service account usage

4. **storage** ✅ - Cloud Storage
   - Resource types: `bucket`, `object` (metadata only)
   - Configuration: max_workers, include_iam_policies, check_public_access, include_lifecycle_rules
   - Security focus: Public bucket access, encryption settings, retention policies

5. **kubernetes** ✅ - Google Kubernetes Engine (GKE)
   - Resource types: `cluster`, `node-pool`, `node`, `pod`, `service`, `configmap`, `secret`
   - Configuration: max_workers, include_node_pools, include_workloads, include_configmaps
   - Security focus: RBAC, network policies, secret management, pod security

6. **bigquery** - BigQuery datasets and analytics
   - Resource types: `dataset`, `table`, `job`, `connection`, `reservation`
   - Configuration: max_workers, include_table_schemas, include_access_policies, include_jobs
   - Security focus: Dataset access controls, data classification, audit logging

7. **dns** - Cloud DNS
   - Resource types: `managed-zone`, `policy`, `peering`
   - Configuration: max_workers, include_policies
   - Security focus: DNSSEC configuration, zone visibility

8. **secretmanager** - Secret Manager
   - Resource types: `secret`, `version`
   - Configuration: max_workers, include_versions
   - Security focus: Secret rotation, access policies, encryption

9. **kms** - Cloud Key Management Service
   - Resource types: `key-ring`, `crypto-key`, `import-job`
   - Configuration: max_workers, include_keys, include_key_versions
   - Security focus: Key rotation, access controls, algorithm usage

10. **certificatemanager** - Certificate Manager
    - Resource types: `certificate`, `certificate-map`, `certificate-map-entry`
    - Configuration: max_workers, include_maps
    - Security focus: Certificate expiration, domain validation

### Medium Priority (Databases & Data)

11. **cloudsql** - Cloud SQL instances (Asset Inventory discovery)
    - Resource types: `instance` (via Asset Inventory)
    - Configuration: max_workers, include_instance_details
    - Security focus: Public IP usage, backup configuration, SSL settings

12. **spanner** - Cloud Spanner
    - Resource types: `instance`, `database`, `backup`, `instance-config`
    - Configuration: max_workers, include_backups, include_databases
    - Security focus: IAM policies, backup encryption

13. **bigtable** - Cloud Bigtable
    - Resource types: `instance`, `cluster`, `table`, `backup`
    - Configuration: max_workers, include_tables, include_backups
    - Security focus: Access controls, encryption

14. **firestore** - Firestore databases
    - Resource types: `database`, `collection`, `index`, `field`
    - Configuration: max_workers, include_indexes, include_fields
    - Security focus: Security rules, IAM policies

15. **memorystore** - Memorystore (Redis/Memcached)
    - Resource types: `instance`, `cluster`
    - Configuration: max_workers, include_clusters
    - Security focus: Network configuration, authentication

16. **filestore** - Cloud Filestore
    - Resource types: `instance`, `backup`, `share`
    - Configuration: max_workers, include_backups
    - Security focus: Network access, backup policies

### Medium Priority (Serverless & Compute)

17. **functions** - Cloud Functions
    - Resource types: `function`, `trigger`
    - Configuration: max_workers, include_versions, include_triggers
    - Security focus: Runtime versions, environment variables, network settings

18. **run** - Cloud Run services
    - Resource types: `service`, `revision`, `job`
    - Configuration: max_workers, include_revisions, include_jobs
    - Security focus: Service accounts, network configuration, environment variables

19. **appengine** - App Engine applications
    - Resource types: `application`, `service`, `version`, `instance`
    - Configuration: max_workers, include_versions, include_instances
    - Security focus: Access controls, SSL configuration

20. **cloudbuild** - Cloud Build
    - Resource types: `trigger`, `build`, `worker-pool`
    - Configuration: max_workers, include_triggers, include_builds
    - Security focus: Build triggers, service accounts, artifact storage

### Low Priority (Messaging & Integration)

21. **pubsub** - Cloud Pub/Sub
    - Resource types: `topic`, `subscription`, `schema`, `snapshot`
    - Configuration: max_workers, include_schemas, include_snapshots
    - Security focus: Access controls, message encryption

22. **eventarc** - Eventarc
    - Resource types: `trigger`, `channel`
    - Configuration: max_workers, include_channels
    - Security focus: Event filtering, destination permissions

23. **workflows** - Workflows
    - Resource types: `workflow`, `execution`
    - Configuration: max_workers, include_executions
    - Security focus: Service account usage, execution logs

### Low Priority (Management & Monitoring)

24. **logging** - Cloud Logging
    - Resource types: `sink`, `metric`, `alert`, `exclusion`
    - Configuration: max_workers, include_sinks, include_metrics
    - Security focus: Log retention, access controls

25. **monitoring** - Cloud Monitoring
    - Resource types: `alert-policy`, `uptime-check`, `notification-channel`, `dashboard`
    - Configuration: max_workers, include_alerts, include_dashboards
    - Security focus: Alert configurations, notification channels

26. **resourcemanager** - Resource Manager
    - Resource types: `project`, `folder`, `organization`, `lien`
    - Configuration: max_workers, include_folders, include_liens
    - Security focus: Organization policies, project hierarchy

### Low Priority (Security & Compliance)

27. **securitycenter** - Security Command Center
    - Resource types: `finding`, `source`, `notification-config`, `mute-config`
    - Configuration: max_workers, include_findings, include_mute_configs
    - Security focus: Security findings analysis

28. **accesscontextmanager** - Access Context Manager (VPC Service Controls)
    - Resource types: `access-policy`, `access-level`, `service-perimeter`
    - Configuration: max_workers, include_policies
    - Security focus: Service perimeter configuration

29. **essentialcontacts** - Essential Contacts
    - Resource types: `contact`
    - Configuration: max_workers
    - Security focus: Contact information for security notifications

### Low Priority (AI/ML & Specialized)

30. **aiplatform** - Vertex AI
    - Resource types: `endpoint`, `model`, `dataset`, `training-pipeline`
    - Configuration: max_workers, include_models, include_datasets
    - Security focus: Model access controls, data encryption

31. **speech** - Cloud Speech-to-Text
    - Resource types: `recognizer`, `phrase-set`, `custom-class`
    - Configuration: max_workers
    - Security focus: Access controls

32. **videointelligence** - Cloud Video Intelligence
    - Resource types: `annotate-operation`
    - Configuration: max_workers
    - Security focus: Access controls

33. **datalabeling** - Data Labeling Service
    - Resource types: `dataset`, `annotation-spec-set`
    - Configuration: max_workers
    - Security focus: Data handling policies

## Implementation Order

### Phase 1 (High Priority - Core Security & Infrastructure) - 10 services
1. networking ✅
2. iam ✅
3. compute ✅
4. storage ✅
5. kubernetes ✅
6. bigquery
7. dns
8. secretmanager
9. kms
10. certificatemanager

### Phase 2 (Medium Priority - Databases & Data) - 6 services
11. cloudsql (Asset Inventory)
12. spanner
13. bigtable
14. firestore
15. memorystore
16. filestore

### Phase 3 (Medium Priority - Serverless & Compute) - 4 services
17. functions
18. run
19. appengine
20. cloudbuild

### Phase 4 (Low Priority - Messaging & Integration) - 3 services
21. pubsub
22. eventarc
23. workflows

### Phase 5 (Low Priority - Management & Monitoring) - 3 services
24. logging
25. monitoring
26. resourcemanager

### Phase 6 (Low Priority - Security & Compliance) - 3 services
27. securitycenter
28. accesscontextmanager
29. essentialcontacts

### Phase 7 (Low Priority - AI/ML & Specialized) - 4 services
30. aiplatform
31. speech
32. videointelligence
33. datalabeling

## Security-Focused Configuration Template

Each extractor should include security-relevant configurations in `config/extractors.yaml`:

```yaml
gcp:
  [service_name]:
    max_workers: 10
    # Security analysis flags
    security_analysis: true
    include_public_access: true
    include_encryption_status: true
    include_access_policies: true
    check_compliance: true
    # Service-specific security configs
    [service_specific_security_config]: [value]
```

## Security Analysis Framework

### Common Security Checks
- **Public Exposure**: Resources accessible from public internet
- **Encryption**: Data at rest and in transit encryption status
- **Access Controls**: IAM policies, network security rules
- **Compliance**: Industry standards (CIS, NIST, etc.)
- **Configuration Issues**: Default settings, weak configurations

### Service-Specific Security Focus
- **Compute**: Public IPs, disk encryption, service accounts
- **Storage**: Bucket permissions, encryption, retention
- **Network**: Firewall rules, VPN configurations, load balancer security
- **IAM**: Privilege escalation, unused accounts, key management
- **Kubernetes**: RBAC, network policies, image security
- **Databases**: Public access, backup encryption, SSL requirements

## File Structure

Each extractor should be implemented as:
- `app/extractors/gcp/[service_name].py`
- Class: `GCP[ServiceName]Extractor(BaseExtractor)`
- Security analysis methods in `app/extractors/gcp/security/[service_name]_security.py`

## Dependencies

Additional GCP client libraries needed:
- `google-cloud-bigquery`
- `google-cloud-dns`
- `google-cloud-secret-manager`
- `google-cloud-kms`
- `google-cloud-certificate-manager`
- `google-cloud-spanner`
- `google-cloud-bigtable`
- `google-cloud-firestore`
- `google-cloud-memorystore`
- `google-cloud-filestore`
- `google-cloud-functions`
- `google-cloud-run`
- `google-cloud-appengine-admin`
- `google-cloud-build`
- `google-cloud-pubsub`
- `google-cloud-eventarc`
- `google-cloud-workflows`
- `google-cloud-logging`
- `google-cloud-monitoring`
- `google-cloud-resourcemanager`
- `google-cloud-securitycenter`
- `google-cloud-access-context-manager`
- `google-cloud-essential-contacts`
- `google-cloud-aiplatform`
- `google-cloud-speech`
- `google-cloud-videointelligence`
- `google-cloud-datalabeling`