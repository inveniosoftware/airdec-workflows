# Orcha Helm Chart

A V1 Helm chart for deploying Orcha to a Kubernetes cluster.

The chart includes:
- Orcha API server
- [Temporal](https://temporal.io/) workflow engine as a subchart
- PostgreSQL for persistance

## Prerequisites

- [Helm 3](https://helm.sh)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) or
[oc](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html)
(for OpenShift) configured against the target cluster

This repo only contains one chart currently, but is structured in the standard helm repo way. This means you will find
the chart in the `charts/orcha` directory. All example `helm` commands below should be run from that directory.

---

## Deployment

### Namespace/project

Create the namespace / project ahead of the first-time deployment.

**Plain Kubernetes:**
```bash
kubectl create namespace <namespace>
```

**OpenShift:**
```bash
oc new-project <namespace>
```

### Secrets (optional)
> See the secrets section in values.yaml for more information before creating the secrets

Create a Kubernetes/OpenShift Secret holding the database password:

**1. Create secrets**
```bash
kubectl create secret generic orcha-db-secret \
  --from-literal=password='<your-db-password>' \
  -n <namespace>
```

If an LLM API key is needed:

```bash
oc create secret generic orcha-llm-secret \
  --from-literal=litellmApiKey='<your-key>' \
  --from-literal=ollamaApiKey='<your-key>' \
  -n <namespace>
```

If Langfuse tracing is enabled:

```bash
oc create secret generic orcha-langfuse-secret \
  --from-literal=publicKey='<your-public-key>' \
  --from-literal=secretKey='<your-secret-key>' \
  -n <namespace>
```

**2. Configure values**

In your `values.yaml` override file:

```yaml
secrets:
  db:
    existingSecret: "orcha-db-secret"
  llm:
    existingSecret: "orcha-llm-secret"  # Omit if not using an LLM API key
  langfuse:
    existingSecret: "orcha-langfuse-secret"  # Omit if Langfuse is disabled

appConfig:
  langfuseEnabled: "True"
  langfuseBaseUrl: "https://cloud.langfuse.com"  # Optional for self-hosted/non-default endpoints
```

> Langfuse is an optional feature and is disabled by default. The configuration above enables it.

### Persistence Configuration

**Option A: Bundled PostgreSQL (default)**

This is the default configuration in the existing `values.yaml`. Review the values in postgresql.auth and
temporal.server.config.persistance to ensure they match your needs.

**Option B: External Database**

**1. Prepare the external database**

Your database instance must have a user with CREATEDB permission, and **three databases** owned by that user.

This user needs to match the user in externalDatabase and in the Temporal persistence configuration in values.yaml.

The three databases that should be created are:
- orcha
- temporal
- temporal_visibility

> The bundled PostgreSQL init script (`initdb`) that creates `temporal` and `temporal_visibility` only runs when the
> internal PostgreSQL subchart is enabled. With an external DB, you must create these manually.


**2. Configure values**

Create a `values.yaml` override file where:
- `postgresql.enabled` is set to `false`
- `externalDatabase` fields are filled to point to your external instance
- `temporal.schema.createDatabase.enabled` is set to `false` (databases are pre-created)
- `temporal.server.config.persistence` values point to your external instance — see `values.yaml` comments for
  more information

### Kubernetes

If using Kubernetes, ensure ingress is enabled in your `values.yaml` override file:

```yaml
ingress:
  enabled: true
  className: ""               # Add your cluster's IngressClass, e.g. nginx
```

### OpenShift

If using OpenShift, use route instead. In your `values.yaml` override file:

```yaml
route:
  app:
    enabled: true
    host: "orcha.<apps-domain>"    # e.g. orcha.apps.paas.cern.ch
  temporalWeb:
    enabled: true                  # Optional: expose Temporal UI
    host: "orcha-temporal.<apps-domain>"
```

### Authentication and Tenants

For more information on how authentication is set up for Orcha, visit our [README section on it](https://github.com/inveniosoftware/orcha#authentication).

:::info
By default, auth is enabled in Orcha.
:::

Tenant configuration (RSA public keys) is managed as part of the Helm release via the `tenants.config` value. Add each tenant's public key to your environment values file:

```yaml
tenants:
  config:
    my-tenant:
      name: "My Tenant"
      public_keys:
        kid-1: |
          -----BEGIN PUBLIC KEY-----
          MIIBIjAN...
          -----END PUBLIC KEY-----
```

Since the tenant registry is loaded once at startup, adding, updating, or removing a tenant requires a `helm upgrade` followed by a rolling restart:

```bash
helm upgrade orcha ./charts/orcha -f values-<env>.yaml -n <namespace>
kubectl rollout restart deployment/<deployment> -n <namespace>
```

### Temporal namespaces
The first time we deploy Temporal, no namespace exists within the application. To create it:

1. Find the temporal admintools by running `oc get deployments`
2. Exec into it with bash:

```bash
oc exec -it deployment/<admintools-deployment> -- /bin/bash
```

3. Use the temporal CLI to create a namespace
```bash
temporal operator namespace create -n <namespace>
```

---

## Multiple instances (e.g. sandbox + prod)

We recommend deploying each instance into its own namespace. This avoids resource name collisions and keeps
configurations independent.

Then, only the environment-specific value.yaml override file needs to be changed, e.g. `values-prod.yaml` and
`values-sandbox.yaml`.

```bash
# Production
helm upgrade --install orcha ./charts/orcha \
  -f values-prod.yaml \
  -n orcha

# Sandbox
helm upgrade --install orcha-sandbox ./charts/orcha \
  -f values-sandbox.yaml \
  -n orcha-sandbox
```

---

## Installing Chart

```bash
helm repo add temporal https://go.temporal.io/helm-charts
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency update ./charts/orcha

helm upgrade --install orcha ./charts/orcha \
  -f values.yaml \
  -n <namespace> \
  --create-namespace
```

## Upgrading

Database migrations are run automatically by a Helm hook Job when `migrations.enabled` is true.
The Job runs `orcha migrate`, which applies Alembic migrations to the Orcha database.
It runs on `post-install` and `pre-upgrade`.

Disable automatic migrations with:

```yaml
migrations:
  enabled: false
```

```bash
helm upgrade orcha ./charts/orcha \
  -f values-<env>.yaml \
  -n <namespace>
```

> This will work as expected if your values-<env>.yaml file is up-to-date with the release history. If not,
> consider using the flag `--reset-then-reuse-values` as detailed in the [Helm Upgrade docs](https://helm.sh/docs/helm/helm_upgrade/).

---

## Uninstalling

```bash
helm uninstall orcha -n <namespace>
```


---

## Troubleshooting

### SSE / streaming not working

Verify the Route/Ingress has the correct timeout and buffering annotations:

```yaml
# OpenShift Route
haproxy.router.openshift.io/timeout: 3600s

# nginx Ingress
nginx.ingress.kubernetes.io/proxy-buffering: "off"
nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
```

### TLS

It might be necessary to install cert-manager in your cluster and create a secret orcha-tls:

```yaml
# values.yaml
ingress:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  tls:
    enabled: true
    secretName: orcha-tls
```
