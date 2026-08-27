# Running against a local InvenioRDM

Start Orcha with `orcha run`, which turns `DEV_MODE` on,
and set two values in the instance's `invenio.cfg`:

```python
RDM_DEPOSIT_ORCHA_ENABLED = True
RDM_ORCHA_DEV_MODE = True
```

That is the whole setup.
`DEV_MODE` runs Orcha with authentication off,
serving every request as the `dev` tenant,
and `RDM_ORCHA_DEV_MODE` stops InvenioRDM signing tokens it no longer needs.
No keys exist on either side.

Both switches are off by default and belong nowhere near a deployment,
where the tenant key and the registry apply as usual.

Zenodo already sets both from `invenio.cfg` when `ZENODO_ENV` is `local`,
which is its default,
so a local checkout needs no configuration at all.

## Reaching the service

Under dev mode `RDM_ORCHA_URL` defaults to `http://localhost:8000`.
A containerised instance has to say where the host is:

```
INVENIO_RDM_ORCHA_URL=http://host.docker.internal:8000
```

Orcha downloads the draft file from an externally-addressed URL
that InvenioRDM mints,
unsigned under `RDM_ORCHA_DEV_MODE`,
so `SITE_UI_URL` has to resolve from wherever Orcha runs.
TLS verification is skipped for `localhost`, `127.0.0.1` and `::1`,
which covers the usual self-signed development certificate.
Any other host has to appear in `HTTP_ALLOWLIST`.

## Enabling the deposit form button

Zenodo gates the feature on the `orcha-access` action
rather than a plain boolean,
so the button stays hidden until your user holds the action:

```bash
invenio access allow-action-for-user \
  --action orcha-access --user you@example.org
```

`INVENIO_RDM_DEPOSIT_ORCHA_ENABLED=True` replaces the check for local work.
