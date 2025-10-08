#!/usr/bin/env bash
set -euo pipefail

OUT_FILE=".env"
echo "Creating ${OUT_FILE} in $(pwd)"

read -p "WTWD username: " WTWD_USERNAME
read -s -p "WTWD password: " WTWD_PASSWORD
echo
read -p "WTD username: " WTD_USERNAME
read -s -p "WTD password: " WTD_PASSWORD
echo
read -s -p "TIRECO API KEY: " TIRECO_API_KEY
echo
read -s -p "SHOPIFY API KEY: " SHOPIFY_API_KEY
echo
read -s -p "SHOPIFY PASSWORD: " SHOPIFY_PASSWORD
echo
read -p "SHOPIFY STORE URL (yourstore.myshopify.com): " SHOPIFY_STORE_URL

cat > "${OUT_FILE}" <<EOF
WTWD_USERNAME=${WTWD_USERNAME}
WTWD_PASSWORD=${WTWD_PASSWORD}
WTD_USERNAME=${WTD_USERNAME}
WTD_PASSWORD=${WTD_PASSWORD}
TIRECO_API_KEY=${TIRECO_API_KEY}
SHOPIFY_API_KEY=${SHOPIFY_API_KEY}
SHOPIFY_PASSWORD=${SHOPIFY_PASSWORD}
SHOPIFY_STORE_URL=${SHOPIFY_STORE_URL}
DEBUG_MODE=true
EOF

chmod 600 "${OUT_FILE}"
echo ".env file created with restricted permissions."
