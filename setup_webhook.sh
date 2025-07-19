#!/bin/bash
# Script to setup webhook URL

echo "🔗 Setting up webhook for TaskerBot"
echo "===================================="
echo ""
echo "1. First, run ngrok in another terminal:"
echo "   ngrok http 8443"
echo ""
echo "2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)"
echo ""
read -p "3. Enter your ngrok URL: " NGROK_URL

if [[ -z "$NGROK_URL" ]]; then
    echo "❌ Error: URL cannot be empty"
    exit 1
fi

# Update .env file
sed -i.bak "s|TELEGRAM_WEBHOOK_URL=.*|TELEGRAM_WEBHOOK_URL=${NGROK_URL}/webhook|" .env

echo ""
echo "✅ Webhook URL updated to: ${NGROK_URL}/webhook"
echo ""
echo "Now you can run the bot with:"
echo "   uv run python run_local.py"