# API Authentication — Options & Implementation Guide

## Overview

The Food Orders API currently has no authentication layer — any caller with network access can read
or modify orders and items. This document covers four authentication strategies, compares their
trade-offs, and documents the implementation that is currently active.

---

## Quick Comparison

| | Option 1 — API Keys | Option 2 — JWT (self-managed) | Option 3 — Azure AD | Option 4 — APIM Gateway |
|---|---|---|---|---|
| **Complexity** | Low | Medium | Medium–High | High |
| **Setup time** | ~1 hour | ~4 hours | ~4 hours | ~1 day |
| **External dependency** | None | None | Azure AD tenant | Azure APIM service |
| **User accounts** | No | Yes | Yes (Microsoft accounts) | Depends on backend |
| **Token expiry** | Manual rotation | Yes (short-lived JWT) | Yes (Azure-managed) | Depends on policy |
| **Roles / RBAC** | Basic (per-key) | Yes (embedded in token) | Yes (Azure App Roles) | Yes (APIM policies) |
| **MFA support** | No | No (you build it) | Yes (Azure AD native) | Yes (via Azure AD) |
| **Cost** | Free | Free | Free (Azure AD Basic) | ~$50–$200/month |
| **Best for** | Internal / service-to-service | Apps with own user accounts | Azure-native / enterprise | External-facing, multi-client |

**Currently active: Option 1 — API Keys**

---

## Option 1 — API Key Authentication ✅ (Active)

### How it works

Every API caller includes a secret key in the `X-API-Key` request header. The API validates the
key against a set of known keys stored in the `.env` file (or Azure Key Vault in production). If
the key is missing or not recognised the request is rejected with `401 Unauthorized`.

```
Client ──► GET /api/orders/   ──► FastAPI reads X-API-Key header
           X-API-Key: <key>        │
                                   ├── Key valid?  ──► 200 OK
                                   └── Key missing / wrong ──► 401 Unauthorized
```

### Implementation details

| Component | File | Purpose |
|---|---|---|
| Key storage | `.env` → `API_KEYS` | Comma-separated list of valid keys |
| Validation dependency | `app/dependencies/auth.py` | FastAPI `Security()` dependency |
| Applied to | All routes except `GET /health` | Routers receive `dependencies=[Depends(require_api_key)]` |
| Swagger UI | `http://localhost:8000/docs` | "Authorize" button accepts the key |

### Configuration

Add keys to `.env` (comma-separated — multiple keys allow per-client revocation):

```env
API_KEYS=2a9785e01fe42f8f78773b0c0710e2bd3155b8dd73bcfd6ef26eea0bd140d52a,3878411538ce0195cedb306b79a526d5daba65f96709867fb54e7311abee41d1
```

Generate a new key any time with:

```bash
# Python
python -c "import secrets; print(secrets.token_hex(32))"

# PowerShell
[System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).Replace('-','').ToLower()
```

### Usage — sending a request

**curl**
```bash
curl -H "X-API-Key: 2a9785e01fe42f8f78773b0c0710e2bd3155b8dd73bcfd6ef26eea0bd140d52a" \
     http://localhost:8000/api/orders/
```

**Postman**
Set the `apiKey` collection variable to your key. Every request in the collection sends it
automatically via the collection-level `Authorization → API Key` setting.

**Python**
```python
import requests

HEADERS = {"X-API-Key": "2a9785e01fe42f8f78773b0c0710e2bd3155b8dd73bcfd6ef26eea0bd140d52a"}

orders = requests.get("http://localhost:8000/api/orders/", headers=HEADERS).json()
```

**JavaScript / fetch**
```javascript
const headers = { "X-API-Key": process.env.FOOD_API_KEY };

const orders = await fetch("/api/orders/", { headers }).then(r => r.json());
```

### Error responses

**Missing key — 401**
```json
{
  "detail": {
    "message": "Invalid or missing API key. Pass your key in the X-API-Key header."
  }
}
```

**Wrong key — 401**
```json
{
  "detail": {
    "message": "Invalid or missing API key. Pass your key in the X-API-Key header."
  }
}
```

Note: both cases return the same message intentionally — revealing which check failed would assist attackers in probing the API.

### Rotating a key

1. Generate a new key (`secrets.token_hex(32)`).
2. Add it to `API_KEYS` in `.env` alongside the old one.
3. Restart the API.
4. Give the new key to the affected client.
5. Once the client confirms they are using the new key, remove the old key from `.env` and restart.

### Limitations

- Keys are long-lived — if leaked, access is granted until manually rotated.
- No user identity — you know *a* valid key was used, not *who* used it.
- No per-endpoint permissions — all valid keys have full access.
- Not suitable for apps where end-users log in with their own credentials.

---

## Option 2 — JWT with Username / Password (self-managed)

### How it works

Callers POST a username and password to a `/auth/token` endpoint. The API validates the credentials
against a user store (e.g. a `users` Cosmos DB container) and issues a signed **JWT** (JSON Web
Token). The token is short-lived (e.g. 60 minutes) and must be included in subsequent requests as
`Authorization: Bearer <token>`.

```
Client ──► POST /auth/token           Client ──► GET /api/orders/
           { username, password }                 Authorization: Bearer <JWT>
               │                                      │
           Cosmos users store              FastAPI decodes & verifies JWT
               │                                      │
           Returns JWT (60 min TTL)        ├── Valid & not expired ──► 200 OK
                                           └── Invalid / expired   ──► 401
```

### Implementation steps (not yet active)

1. **Add users container to Cosmos DB** — store `{ id, username, hashed_password, role }`.
2. **Install packages**: `pip install python-jose[cryptography] passlib[bcrypt]`
3. **Create `/auth/token` endpoint** — validates credentials, returns `{ access_token, token_type }`.
4. **Create JWT dependency** — `app/dependencies/jwt_auth.py` decodes the Bearer token and extracts the user.
5. **Apply to routers** — same pattern as API keys: `dependencies=[Depends(require_user)]`.

### What the token looks like

```json
{
  "sub": "john.smith",
  "role": "admin",
  "exp": 1750000000
}
```

The payload is base64-encoded (not encrypted) but the **signature** is verified — a tampered token
is rejected. Never store secrets in the payload.

### Key settings needed in `.env`

```env
JWT_SECRET_KEY=<64-char random hex — generate with secrets.token_hex(32)>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

### Pros / cons

**Pros:**
- Tokens expire automatically — leaked tokens become useless within the TTL.
- User identity is embedded — you know exactly who made each request.
- Roles in the token enable per-endpoint permissions (e.g. only `admin` can delete orders).
- No external dependency — fully self-contained.
- Standard OAuth2 Password flow — compatible with any HTTP client and Swagger UI.

**Cons:**
- You manage credentials — password hashing, storage, and reset flows are your responsibility.
- No MFA, social login, or SSO without additional work.
- A long `JWT_SECRET_KEY` must be kept secure; rotation requires invalidating all active tokens.

---

## Option 3 — Azure Active Directory (Microsoft Entra ID)

### How it works

Your API is registered as an **App Registration** in Azure AD. Callers authenticate against Azure AD
(via Microsoft login, service principal, or managed identity) and receive a JWT access token issued
and signed by Microsoft. FastAPI validates the token signature using Azure AD's public keys — there
is no password database to manage.

```
Client ──► Azure AD login (Microsoft account / service principal)
               │
           Azure AD issues JWT (signed with Microsoft's private key)
               │
Client ──► GET /api/orders/
           Authorization: Bearer <Azure AD JWT>
               │
           FastAPI fetches Azure AD public keys (cached)
           Verifies signature + audience + expiry
               │
           ├── Valid ──► 200 OK
           └── Invalid ──► 401
```

### Implementation steps (not yet active)

1. **Register the API** in Azure Portal → Azure Active Directory → App Registrations.
   - Set Application ID URI (e.g. `api://food-orders-api`).
   - Add App Roles: `Orders.Read`, `Orders.Write`, `Orders.Admin`.
2. **Register the calling app** (e.g. Postman, mobile app) as a separate App Registration with
   permission to call the API.
3. **Install package**: `pip install fastapi-azure-auth`
4. **Configure FastAPI** with `AzureAuthorizationCodeBearer` (for user flows) or
   `SingleTenantAzureAuthorizationCodeBearer` (for your tenant only).
5. **Apply dependency** — same pattern: `dependencies=[Depends(azure_scheme)]`.

### Key settings needed in `.env`

```env
AZURE_TENANT_ID=f5c0eda3-9cfd-4cff-a912-888a757d9842
AZURE_CLIENT_ID=<App Registration Application (client) ID>
AZURE_APP_CLIENT_SECRET=<client secret from the App Registration>
```

### Pros / cons

**Pros:**
- Enterprise-grade — MFA, Conditional Access Policies, audit logs, password reset all come free.
- No credential database — Microsoft owns identity.
- Roles defined in App Registration map directly to API permissions.
- Perfect fit for Azure-native workloads — callers can authenticate with their Microsoft accounts
  or via service principal / managed identity (no username/password needed between services).
- Your Azure tenant (`f5c0eda3-...`) is already configured.

**Cons:**
- Requires Azure AD setup (App Registration, scopes, consent) — ~4 hours first time.
- External callers (mobile apps, Postman) need their own App Registration or client credentials.
- More complex debugging (token audience, scopes, tenant mismatches are common pitfalls).
- Overkill if callers are not Microsoft/Azure identities.

### When to choose this

You are already on Azure. If the API is ever consumed by internal Microsoft Teams users, Azure
services, or Power BI — this is the right long-term choice. Start with Option 1 now and migrate
to Option 3 when you onboard real users.

---

## Option 4 — Azure API Management (APIM) Gateway

### How it works

APIM sits in front of FastAPI as a managed gateway. FastAPI is moved to a private network (or its
URL is kept secret). All external traffic hits the APIM endpoint. APIM enforces authentication
policy (subscription keys, JWT validation, IP whitelisting, mTLS) and only forwards valid requests.
FastAPI does not need to change at all.

```
Internet ──► APIM (public endpoint)
                │  Subscription key / JWT validation
                │  Rate limiting, throttling
                │  Request transformation
                ▼
            FastAPI (private — not directly reachable from internet)
                │
            Cosmos DB / Blob Storage
```

### Implementation steps (not yet active)

1. Deploy APIM in Azure (Developer tier for testing, ~$50/month; Standard for production).
2. Import the API via the OpenAPI spec at `http://localhost:8000/openapi.json`.
3. Configure inbound policy — choose one or more:
   - **Subscription keys** (APIM equivalent of API keys — managed in the APIM portal).
   - **JWT validation** — validate Azure AD tokens without changing FastAPI.
   - **IP filtering** — whitelist known client IPs.
4. Move FastAPI to a private endpoint or restrict its network access to APIM's outbound IP only.

### Key APIM policies

```xml
<!-- Validate subscription key -->
<check-header name="Ocp-Apim-Subscription-Key" failed-check-httpcode="401" />

<!-- Validate Azure AD JWT -->
<validate-jwt header-name="Authorization" failed-validation-httpcode="401">
    <openid-config url="https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"/>
    <audiences><audience>api://food-orders-api</audience></audiences>
</validate-jwt>

<!-- Rate limit per subscription key -->
<rate-limit-by-key calls="100" renewal-period="60" counter-key="@(context.Subscription.Id)" />
```

### Pros / cons

**Pros:**
- Auth is completely decoupled from application code — FastAPI requires zero changes.
- Supports multiple auth schemes simultaneously on different products.
- Built-in rate limiting, analytics, developer portal, API versioning, request/response transformation.
- APIM can enforce auth for multiple backend services centrally.

**Cons:**
- Expensive — Developer tier ~$50/month, Standard ~$200/month (no free tier).
- Another Azure service to configure, monitor, and maintain.
- Cold start / latency added by the gateway (~10–50 ms per request).
- Significant operational overhead for a single small API.

### When to choose this

When the API is consumed by external third-party clients, when you need per-client rate limiting,
or when you need to secure multiple APIs under one gateway. Combine with Option 3 (Azure AD) for
the most complete enterprise setup.

---

## Decision Guide

```
Is this API internal-only (no end-users logging in)?
  ├── Yes ──► Start with Option 1 (API Keys). Migrate to Option 3 when you onboard Azure users.
  └── No ──► Do callers have Microsoft / Azure accounts?
               ├── Yes ──► Option 3 (Azure AD)
               └── No  ──► Do you want to manage your own user database?
                              ├── Yes ──► Option 2 (JWT)
                              └── No  ──► Option 3 (Azure AD) or Option 4 (APIM + third-party IdP)

Do you need rate limiting, analytics, or a developer portal?
  └── Yes ──► Add Option 4 (APIM) on top of whichever auth option you chose above.
```

---

## Upgrade Path

The options are designed to layer. A recommended production journey:

```
Today         Option 1  API Keys — blocks unauthenticated access immediately
3–6 months    Option 3  Azure AD — add real user identity + MFA as team grows
Production    Option 4  APIM — add in front of Azure AD when external clients onboard
```

Migrating from Option 1 to Option 3 is a code change in `app/dependencies/` and `app/main.py` only — no
schema changes in Cosmos DB are needed.

---

## Security Best Practices (all options)

- **Never commit secrets** — `.env` is in `.gitignore`. Use Azure Key Vault in production.
- **Use HTTPS in production** — plain HTTP exposes API keys and tokens in transit.
- **Log auth failures** — track 401 rates to detect brute-force or misconfigured clients.
- **Return identical 401 messages** — do not reveal whether the key exists vs. the key is wrong.
- **Rotate keys/secrets regularly** — especially after team member changes.
- **Keep `/health` unauthenticated** — load balancers and uptime monitors need it without credentials.
