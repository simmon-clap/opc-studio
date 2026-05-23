#!/usr/bin/env bash
# Interactive helper for Cloudflare Tunnel (free tier).
# Prerequisites: cloudflared installed, domain on Cloudflare.
set -euo pipefail

echo "Cloudflare Tunnel — OPC Studio"
echo ""
echo "Option A — Quick demo (random *.trycloudflare.com URL, no DNS setup):"
echo "  1. ./start.sh   (in another terminal)"
echo "  2. cloudflared tunnel --url http://127.0.0.1:8765"
echo ""
echo "Option B — Stable subdomain (recommended if you own a domain on Cloudflare):"
echo "  1. cloudflared tunnel login"
echo "  2. cloudflared tunnel create opc-studio"
echo "  3. Edit deploy/cloudflare/tunnel.yml.example → tunnel.yml with your UUID + hostname"
echo "  4. cloudflared tunnel route dns opc-studio studio.yourdomain.com"
echo "  5. cloudflared tunnel --config deploy/cloudflare/tunnel.yml run"
echo ""
echo "Security: add OPC_ACCESS_TOKEN in .env before exposing publicly (see deploy/README.md)."
echo "Note: Tunnel forwards to a machine that must keep running (your Mac, or a cheap VPS)."
