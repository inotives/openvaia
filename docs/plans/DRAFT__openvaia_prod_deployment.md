# OpenVAIA — Production Deployment Guide

This document covers deploying OpenVAIA on a local network (Phase 1) and exposing it to the internet (Phase 2).

---

## Phase 1: Local Network (LAN) Deployment

Host OpenVAIA on a Mac Mini accessible to devices on the same network.

### Prerequisites

- Mac Mini running Docker Desktop
- All containers healthy (`make ps`)
- Google OAuth credentials configured (optional)

### Step 1: Assign a Static IP to the Mac Mini

Option A — **Router-side** (recommended):
1. Open your router admin panel (usually `192.168.1.1`)
2. Find DHCP reservation / static lease settings
3. Bind the Mac Mini's MAC address to a fixed IP (e.g., `192.168.1.100`)

Option B — **macOS-side**:
1. System Settings → Network → Wi-Fi (or Ethernet) → Details → TCP/IP
2. Configure IPv4: Manually
3. Set IP: `192.168.1.100`, Subnet: `255.255.255.0`, Router: `192.168.1.1`

### Step 2: Allow Port Through macOS Firewall

```bash
# Check firewall status
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# If enabled, add Docker to allowed apps
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /Applications/Docker.app
```

Alternatively: System Settings → Network → Firewall → Options → ensure Docker is allowed.

### Step 3: Update Environment Variables

**`.env`** — update `NEXTAUTH_URL` to the Mac Mini's LAN IP:
```env
NEXTAUTH_URL=http://192.168.1.100:7860
```

### Step 4: Update Google OAuth Redirect URI

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 Client ID
3. Add authorized redirect URI:
   ```
   http://192.168.1.100:7860/api/auth/callback/google
   ```
4. Add authorized JavaScript origin:
   ```
   http://192.168.1.100:7860
   ```

> You can keep `http://localhost:7860` entries as well for local development.

### Step 5: Rebuild and Deploy

```bash
make deploy-all    # Or: make ui if only UI changed
```

### Step 6: Verify

From another device on the same network:
```
http://192.168.1.100:7860
```

Should show the OpenVAIA login page. Google sign-in and all dashboard features should work.

### LAN Architecture

```
[Phone/Laptop/Tablet]
        |
    LAN (192.168.1.x)
        |
[Mac Mini - 192.168.1.100]
        |
   Docker Engine
        |
   ┌────┴──────────────────────────────┐
   │  openvaia_ui       (:7860)        │  ← Only exposed port
   │  agent_ino         (internal)     │
   │  agent_robin       (internal)     │
   │  openvaia_postgres (internal)     │
   └───────────────────────────────────┘
```

Only port `7860` (UI) is exposed to the network. Agent containers and Postgres are internal to the Docker bridge network.

---

## Phase 2: Internet-Facing Deployment

Expose OpenVAIA to the public internet with HTTPS and a custom domain.

> **Status**: Planned for post-v2. Not yet implemented.

### Prerequisites

- A registered domain name (e.g., `openvaia.yourdomain.com`)
- A public IP or a way to expose the Mac Mini (port forwarding, Cloudflare Tunnel, or VPS)
- Phase 1 completed and working

### Option A: Cloudflare Tunnel (Recommended — No Port Forwarding)

Cloudflare Tunnel (`cloudflared`) creates a persistent **outbound** connection from the Mac Mini to Cloudflare's edge network. Traffic flows: Internet → Cloudflare Edge (HTTPS) → Tunnel → Mac Mini (HTTP localhost). No router port forwarding, no public IP, no firewall changes needed.

#### Why This is Recommended

- **Zero network config** — no port forwarding, works behind CGNAT, double-NAT, restrictive ISPs
- **Free HTTPS** — Cloudflare handles TLS termination at the edge, auto-renews certificates
- **DDoS protection** — Cloudflare's network absorbs attacks before traffic reaches your Mac Mini
- **Access policies** — optional Cloudflare Zero Trust rules (IP allowlist, email OTP, etc.) on top of your NextAuth
- **No exposed ports** — the Mac Mini initiates the connection outward, nothing listens on a public port
- **Survives IP changes** — your home IP can change freely, the tunnel reconnects automatically

#### Cost

| Component | Cost | Notes |
|-----------|------|-------|
| **Cloudflare account** | **Free** | Sign up at cloudflare.com |
| **Cloudflare Tunnel** | **Free** | Included in all plans (even free tier) |
| **DNS hosting** | **Free** | When domain uses Cloudflare nameservers |
| **HTTPS/TLS** | **Free** | Universal SSL, auto-provisioned |
| **DDoS protection** | **Free** | Unmetered L3/L4 protection on all plans |
| **Domain name** | **~$10–15/year** | Only cost — buy from any registrar (Cloudflare Registrar, Namecheap, etc.) |
| **Cloudflare Zero Trust** | **Free (up to 50 users)** | Optional — adds extra auth layer (email OTP, IP rules) |

**Total: ~$10–15/year** (just the domain). Everything else is free.

> Cloudflare Registrar sells domains at cost (no markup). A `.com` is ~$10/year, `.dev` is ~$12/year.

#### Step-by-Step Setup

**1. Get a domain**

Buy a domain from any registrar. If not already on Cloudflare:
- Sign up at [cloudflare.com](https://cloudflare.com)
- Add your domain → Cloudflare gives you two nameservers
- Update nameservers at your registrar to point to Cloudflare
- Wait for DNS propagation (usually 5–30 minutes)

**2. Install cloudflared on the Mac Mini**

```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared --version   # Verify installation
```

**3. Authenticate with Cloudflare**

```bash
cloudflared tunnel login
```

This opens a browser to authorize `cloudflared` with your Cloudflare account. It saves a certificate to `~/.cloudflared/cert.pem`.

**4. Create the tunnel**

```bash
cloudflared tunnel create openvaia
```

Output:
```
Created tunnel openvaia with id <TUNNEL_UUID>
```

This creates a credentials file at `~/.cloudflared/<TUNNEL_UUID>.json`.

**5. Configure the tunnel**

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /Users/<your-user>/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: openvaia.yourdomain.com
    service: http://localhost:7860
    originRequest:
      noTLSVerify: true
  - service: http_status:404
```

The `ingress` rules say:
- Requests to `openvaia.yourdomain.com` → forward to the UI on `localhost:7860`
- Everything else → 404

> You can add more hostnames later (e.g., `api.yourdomain.com` → another service).

**6. Create the DNS record**

```bash
cloudflared tunnel route dns openvaia openvaia.yourdomain.com
```

This creates a CNAME record: `openvaia.yourdomain.com → <TUNNEL_UUID>.cfargotunnel.com`

**7. Test the tunnel**

```bash
cloudflared tunnel run openvaia
```

Visit `https://openvaia.yourdomain.com` — you should see the OpenVAIA login page with a valid HTTPS certificate.

**8. Install as a persistent service**

On macOS, install as a launch daemon so it starts on boot:

```bash
sudo cloudflared service install
```

This creates a launchd plist at `/Library/LaunchDaemons/com.cloudflare.cloudflared.plist`.

Verify it's running:
```bash
sudo launchctl list | grep cloudflare
```

To manage:
```bash
# Stop
sudo launchctl stop com.cloudflare.cloudflared

# Start
sudo launchctl start com.cloudflare.cloudflared

# Uninstall
sudo cloudflared service uninstall
```

**9. Update OpenVAIA environment**

`.env`:
```env
NEXTAUTH_URL=https://openvaia.yourdomain.com
```

Google Cloud Console → Credentials → OAuth client:
- Authorized redirect URI: `https://openvaia.yourdomain.com/api/auth/callback/google`
- Authorized JavaScript origin: `https://openvaia.yourdomain.com`

Rebuild:
```bash
make ui
```

#### Optional: Cloudflare Zero Trust (Extra Auth Layer)

Add a second layer of authentication at Cloudflare's edge, before traffic even reaches your Mac Mini:

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Create an **Access Application**:
   - Application domain: `openvaia.yourdomain.com`
   - Policy: Allow — email ends with `@gmail.com` (or specific emails)
   - Auth method: One-time PIN via email
3. Users hit Cloudflare first → verify email → then reach your NextAuth login

This means two auth gates: Cloudflare Zero Trust → NextAuth Google OAuth. Free for up to 50 users.

#### Architecture (Cloudflare Tunnel)

```
[Internet Users]
       |
   HTTPS (TLS terminated at Cloudflare edge)
       |
   Cloudflare Network
   ├── DDoS protection
   ├── Zero Trust policies (optional)
   └── Tunnel routing
       |
   Outbound tunnel (cloudflared on Mac Mini)
       |
[Mac Mini - localhost:7860]
       |
   Docker Engine
       |
   ┌────┴──────────────────────────┐
   │  openvaia_ui       (:7860)    │
   │  agent_ino         (internal) │
   │  agent_robin       (internal) │
   │  openvaia_postgres (internal) │
   └───────────────────────────────┘
```

#### Troubleshooting

| Issue | Fix |
|-------|-----|
| Tunnel won't connect | Check `~/.cloudflared/config.yml` for correct TUNNEL_UUID and credentials path |
| 502 Bad Gateway | UI container not running — check `make ps` and `make ui-logs` |
| DNS not resolving | Wait for propagation, or verify CNAME exists: `dig openvaia.yourdomain.com` |
| Google OAuth redirect mismatch | Ensure `NEXTAUTH_URL` matches the public URL exactly (https, no trailing slash) |
| Tunnel drops after Mac Mini sleep | Disable sleep: System Settings → Energy → Prevent automatic sleeping |
| Service not starting on boot | Verify: `sudo launchctl list | grep cloudflare` — reinstall if missing |

### Option B: Reverse Proxy + Port Forwarding

Traditional setup with nginx/Caddy on the Mac Mini, router port forwarding, and Let's Encrypt SSL.

#### Setup

1. **Install Caddy** (auto-HTTPS via Let's Encrypt):
   ```bash
   brew install caddy
   ```

2. **Caddyfile** (`/etc/caddy/Caddyfile`):
   ```
   openvaia.yourdomain.com {
     reverse_proxy localhost:7860
   }
   ```

3. **Router port forwarding**:
   - Forward port `443` (HTTPS) → Mac Mini's LAN IP port `443`
   - Forward port `80` (HTTP) → Mac Mini's LAN IP port `80` (for ACME challenge)

4. **DNS A record**: Point `openvaia.yourdomain.com` → your public IP

5. **Start Caddy**:
   ```bash
   sudo caddy start
   ```

### Option C: VPS Relay

If you can't port-forward (CGNAT, ISP restrictions), deploy a small VPS as a relay:

1. Cheap VPS (e.g., Hetzner, DigitalOcean $5/mo)
2. Run Caddy on the VPS
3. WireGuard tunnel between VPS ↔ Mac Mini
4. Caddy reverse proxies to Mac Mini's WireGuard IP

### Shared Steps (All Options)

#### Update Environment Variables

```env
NEXTAUTH_URL=https://openvaia.yourdomain.com
```

#### Update Google OAuth

1. Google Cloud Console → Credentials → Edit OAuth client
2. Authorized redirect URI:
   ```
   https://openvaia.yourdomain.com/api/auth/callback/google
   ```
3. Authorized JavaScript origin:
   ```
   https://openvaia.yourdomain.com
   ```

#### Update Docker Compose (Optional)

If using a reverse proxy, you can bind the UI to localhost only for security:

```yaml
# docker-compose.yml — ui service
ports:
  - "127.0.0.1:${UI_PORT:-7860}:7860"   # Only accessible via reverse proxy
```

#### Rebuild

```bash
make ui   # Rebuild UI with new NEXTAUTH_URL
```

### Security Checklist (Internet-Facing)

| Item | Status | Notes |
|------|--------|-------|
| HTTPS enforced | Required | Caddy auto-handles, or Cloudflare edge |
| Google OAuth with email whitelist | Required | `GOOGLE_ALLOWED_EMAILS` in `.env` |
| UI auth middleware protects all API routes | Done | NextAuth middleware, tested in `test_ui.py` |
| Postgres not exposed to internet | Done | Internal Docker network only |
| Agent containers not exposed | Done | No ports mapped |
| No secrets in client-side code | Done | All env vars server-side only |
| `NEXTAUTH_SECRET` is strong | Required | Generate with `openssl rand -base64 32` |
| Rate limiting | Optional | Cloudflare or Caddy rate-limit plugin |
| Fail2ban or equivalent | Optional | For SSH if VPS is used |

---

## Recommended Path

| Scenario | Recommendation |
|----------|---------------|
| Just me on home WiFi | Phase 1 (LAN) is sufficient |
| Access from outside home, no port forwarding | Cloudflare Tunnel (Option A) |
| Full control, have a domain + can port-forward | Caddy reverse proxy (Option B) |
| Behind CGNAT / ISP blocks ports | VPS relay (Option C) or Cloudflare Tunnel (Option A) |
