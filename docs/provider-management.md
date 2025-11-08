# Cloud Provider Dynamic Registration

## Overview

The CSP Scanner now supports dynamic registration and unregistration of cloud providers through the Configuration API. When you enable or disable providers via the API, the system automatically registers or unregisters the corresponding extractors without requiring a restart.

## How It Works

### 1. Provider Registration Flow

When a provider is enabled through the config API:

1. **Detect Changes**: The config API compares old and new `enabled_providers` lists
2. **Initialize Sessions**: For newly enabled providers, cloud sessions are initialized with credentials from the configuration
3. **Register Extractors**: All extractors for the provider are dynamically registered in the registry
4. **Logging**: The system logs the number of extractors registered

### 2. Provider Unregistration Flow

When a provider is disabled:

1. **Detect Changes**: The config API identifies providers that were removed from `enabled_providers`
2. **Unregister Extractors**: All extractors for the provider are removed from the registry
3. **Cleanup Sessions**: Cloud sessions for the provider are cleaned up
4. **Logging**: The system logs the number of extractors unregistered

## API Examples

### Enable AWS Provider

```bash
# Using PUT (replaces entire config)
curl -X PUT https://localhost:8443/api/v1/config/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "config": {
      "enabled_providers": ["aws"],
      "aws_accounts": [
        {
          "account_id": "123456789012",
          "regions": ["us-east-1", "us-west-2"]
        }
      ]
    },
    "description": "Enable AWS provider"
  }'
```

### Enable Multiple Providers

```bash
# Using PATCH (merges with existing config)
curl -X PATCH https://localhost:8443/api/v1/config/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "config": {
      "enabled_providers": ["aws", "azure", "gcp"]
    },
    "description": "Enable all providers"
  }'
```

### Disable a Provider

```bash
# Remove a provider from the enabled list
curl -X PATCH https://localhost:8443/api/v1/config/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "config": {
      "enabled_providers": ["aws"]
    },
    "description": "Disable Azure and GCP"
  }'
```

### Verify Provider Status

Check which providers are currently active:

```bash
# List all enabled providers
curl https://localhost:8443/extraction/providers \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
# {
#   "providers": ["aws"],
#   "total": 1
# }
```

Check available services for a provider:

```bash
# List services for AWS
curl https://localhost:8443/extraction/services?provider=aws \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
# {
#   "services_by_provider": {
#     "aws": [
#       {
#         "service": "ec2",
#         "description": "Amazon EC2 Instances",
#         "resource_types": ["instance"],
#         "version": "1.0"
#       },
#       ...
#     ]
#   },
#   "total_services": 13
# }
```

## Configuration Requirements

### AWS Provider

To enable AWS, your configuration must include:

```json
{
  "enabled_providers": ["aws"],
  "aws_access_key_id": "YOUR_ACCESS_KEY",
  "aws_secret_access_key": "YOUR_SECRET_KEY",
  "aws_accounts": [
    {
      "account_id": "123456789012",
      "regions": ["us-east-1", "us-west-2"]
    }
  ]
}
```

### Azure Provider

To enable Azure, your configuration must include:

```json
{
  "enabled_providers": ["azure"],
  "azure_tenant_id": "YOUR_TENANT_ID",
  "azure_client_id": "YOUR_CLIENT_ID",
  "azure_client_secret": "YOUR_CLIENT_SECRET",
  "azure_accounts": [
    {
      "subscription_id": "YOUR_SUBSCRIPTION_ID",
      "locations": ["eastus", "westus2"]
    }
  ]
}
```

### GCP Provider

To enable GCP, your configuration must include:

```json
{
  "enabled_providers": ["gcp"],
  "gcp_credentials_path": "/path/to/credentials.json",
  "gcp_projects": [
    {
      "project_id": "your-project-id",
      "regions": ["us-central1", "us-east1"]
    }
  ]
}
```

## Startup Behavior

### With Database Configuration

When database configuration is enabled:

1. **Load Config**: Settings are loaded from the database on startup
2. **Initialize Providers**: Only providers listed in `enabled_providers` with valid credentials are initialized
3. **No Providers Warning**: If no providers are enabled, a warning is logged but the app continues running
4. **API Configuration**: Use the config API to enable providers after startup

### Without Database Configuration

When database is disabled:

1. **Environment Variables**: Providers are enabled based on environment variables
2. **YAML Config**: Or from YAML configuration file
3. **Static**: Provider list is static until restart

## Logging

The system logs provider registration/unregistration events:

```
2025-11-05 22:45:00 - app.api.routes.config - INFO - Provider changes detected: [] -> ['aws']
2025-11-05 22:45:00 - app.api.routes.config - INFO - Initialized 2 AWS sessions
2025-11-05 22:45:01 - app.services.registry - INFO - Registered extractor: aws:ec2
2025-11-05 22:45:01 - app.services.registry - INFO - Registered extractor: aws:s3
...
2025-11-05 22:45:02 - app.services.registry - INFO - Registered 13 extractors for provider: aws
2025-11-05 22:45:02 - app.api.routes.config - INFO - Enabled provider 'aws': registered 13 extractors
```

When disabling:

```
2025-11-05 22:50:00 - app.api.routes.config - INFO - Provider changes detected: ['aws', 'azure'] -> ['aws']
2025-11-05 22:50:00 - app.services.registry - INFO - Unregistered extractor: azure:compute
2025-11-05 22:50:00 - app.services.registry - INFO - Unregistered extractor: azure:storage
...
2025-11-05 22:50:01 - app.services.registry - INFO - Removed session for provider: azure
2025-11-05 22:50:01 - app.api.routes.config - INFO - Disabled provider 'azure': unregistered 8 extractors
```

## Troubleshooting

### Provider Not Registering

If a provider doesn't register after enabling:

1. **Check Credentials**: Ensure credentials are properly configured
2. **Check Logs**: Look for error messages in the logs
3. **Verify Config**: Use GET `/api/v1/config/` to verify the configuration was saved
4. **Check Provider Status**: Use GET `/extraction/providers` to see active providers

### Extractors Not Available

If extractors aren't available after enabling a provider:

1. **Check Registry**: The registry must be available in `app.state`
2. **Check Dependencies**: Ensure cloud provider SDKs are installed
3. **Check Import Errors**: Look for ImportError messages in logs
4. **Restart if Needed**: In rare cases, you may need to restart the application

### "No cloud providers enabled" Warning

This warning appears when:

1. Database config is enabled but no providers are configured
2. Solution: Use the config API to enable providers with credentials
3. Or set environment variables before startup (they override DB config)

## Best Practices

1. **Use PATCH for Incremental Changes**: Use PATCH to modify just `enabled_providers` without affecting other settings
2. **Verify After Changes**: Always check `/extraction/providers` and `/extraction/services` after configuration changes
3. **Monitor Logs**: Watch logs during configuration updates to catch any errors
4. **Test Credentials First**: Ensure credentials are valid before enabling a provider
5. **Graceful Rollback**: If a provider fails to initialize, disable it and check configuration

## Implementation Details

### Registry Methods

- `register_provider(provider, sessions)`: Register all extractors for a provider
- `unregister_provider_extractors(provider)`: Remove all extractors for a provider

### Config API Enhancement

- `_initialize_cloud_sessions(settings, provider)`: Initialize cloud sessions for a provider
- `_handle_provider_changes(request, old_providers, new_providers)`: Detect and handle provider changes
