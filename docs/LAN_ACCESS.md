# LAN Access — Testing on Phone/Tablet

Access the dev app from any device on your WiFi network.

## Enable

1. **Get your Mac's IP:**
   ```bash
   ipconfig getifaddr en0
   ```

2. **Set the API URL and CORS in `.env`:**
   ```bash
   VITE_API_URL=http://192.168.x.x:8000
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://192.168.x.x:5173
   ```
   Replace `192.168.x.x` with the IP from step 1.

3. **Restart the containers:**
   ```bash
   docker compose -f docker-compose.dev.yml down
   docker compose -f docker-compose.dev.yml up
   ```

4. **Open on your phone:**
   ```
   http://192.168.x.x:5173
   ```
   Same IP, port `5173`.

## Disable

1. Comment out both lines in `.env`:
   ```bash
   # VITE_API_URL=http://192.168.x.x:8000
   # CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://192.168.x.x:5173
   ```

2. Restart containers:
   ```bash
   docker compose -f docker-compose.dev.yml down
   docker compose -f docker-compose.dev.yml up
   ```

   The app reverts to `localhost`-only access.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Phone can't connect | Confirm both devices are on the same WiFi network |
| API calls fail but page loads | Double-check the IP in `VITE_API_URL` matches your current IP |
| IP changed after restart | Your router may assign dynamic IPs — re-run `ipconfig getifaddr en0` and update `.env` |
| Page won't load at all | Make sure macOS firewall isn't blocking ports 5173 and 8000 (System Settings > Network > Firewall > Options) |

## Security Notes

- Traffic is **unencrypted HTTP** — only use this on a trusted private network
- Anyone on the same WiFi can access the app while LAN mode is active
- Always disable when done testing or on shared/public networks
- For encrypted access, consider [Tailscale](https://tailscale.com/) (free, zero-config WireGuard VPN)
