# Remote Access — Tailscale, LAN, Phone/Tablet

Access Unstructured Minds from any device — phone, tablet, or another machine.

## Tailscale (Recommended)

[Tailscale](https://tailscale.com/) gives you encrypted, zero-config access from anywhere. Free for personal use.

### Setup

1. **Install Tailscale** on your server and any device you want to access from
2. **Start the app:**
   ```bash
   docker compose up -d
   ```
3. **Get your Tailscale hostname:**
   ```bash
   tailscale status   # e.g., my-server
   ```
4. **Update `.env`** so the frontend knows where the API is:
   ```bash
   CORS_ORIGINS=http://my-server:3000,http://localhost:3000
   ```
5. **Open on any device** on your tailnet:
   ```
   http://my-server:3000
   ```

### Why Tailscale?

- **Encrypted** — WireGuard tunnel, no plain HTTP over the internet
- **No port forwarding** — works behind NAT, firewalls, anywhere
- **Stable hostname** — no IP changes to track
- **Free** — up to 100 devices on the personal plan

### With Basic Auth

For extra security over Tailscale:
```bash
AUTH_MODE=basic
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=your-password
```

---

## LAN Access (Same WiFi)

For quick testing on your local network without Tailscale.

### Setup

1. **Get your Mac's IP:**
   ```bash
   ipconfig getifaddr en0
   ```

2. **Update `.env`:**
   ```bash
   CORS_ORIGINS=http://localhost:3000,http://192.168.x.x:3000
   ```
   Replace `192.168.x.x` with your IP.

3. **Restart:**
   ```bash
   docker compose up -d
   ```

4. **Open on your phone:**
   ```
   http://192.168.x.x:3000
   ```

### Disable

Remove the extra CORS origin and restart. The app reverts to localhost-only.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Phone can't connect | Confirm both devices are on the same network (or tailnet) |
| API calls fail but page loads | Check `CORS_ORIGINS` includes the hostname/IP you're using |
| IP changed after restart | Use Tailscale (stable hostname) or re-run `ipconfig getifaddr en0` |
| Page won't load at all | Check macOS firewall isn't blocking port 3000/8000 |

## Security

| Method | Encrypted | Internet Access | Setup |
|--------|-----------|-----------------|-------|
| **Tailscale** | Yes (WireGuard) | Yes, from anywhere | Install Tailscale |
| **LAN** | No (plain HTTP) | No, same WiFi only | Just update CORS |

For LAN: only use on a trusted private network. Consider `AUTH_MODE=basic` for extra protection.
