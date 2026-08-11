# Provider Connectors

## WhatsApp Cloud API
- **Graph API Version:** v26.0
- **Auth:** `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID`
- **Webhook:** POST `/api/v1/webhooks/whatsapp`
- **Verify Token:** `WEBHOOK_VERIFY_TOKEN`
- **Features:** Text, template messages, message status callbacks

## Instagram Messaging
- **Graph API Version:** v26.0
- **Auth:** `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Webhook:** POST `/api/v1/webhooks/instagram`
- **Features:** DM send/receive, message status

## Instagram Discovery
- **Graph API Version:** v26.0
- **Auth:** `INSTAGRAM_DISCOVERY_ACCESS_TOKEN` + `INSTAGRAM_DISCOVERY_IG_USER_ID`
- **Features:** Business profile discovery, media analysis

## Telegram Bot API
- **Auth:** `TELEGRAM_BOT_TOKEN`
- **Webhook:** POST `/api/v1/webhooks/telegram`
- **Secret:** `TELEGRAM_WEBHOOK_SECRET` (X-Telegram-Bot-Api-Secret-Token header)
- **Features:** Text messages, inline keyboards, webhook updates

## Eitaa Messenger
- **Auth:** `EITAA_APP_TOKEN`
- **Webhook:** POST `/api/v1/webhooks/eitaa`
- **Features:** Text messages, message status

## Rubika Messenger
- **Auth:** `RUBIKA_BOT_TOKEN`
- **Webhook:** POST `/api/v1/webhooks/rubika`
- **Secret:** `RUBIKA_WEBHOOK_SECRET`
- **Features:** Text messages, webhook updates

## Google Places API
- **Auth:** `GOOGLE_PLACES_API_KEY`
- **Features:** Nearby Search, Place Details
- **Language:** `GOOGLE_PLACES_LANGUAGE=fa` (Persian results)

## Public Web Discovery
- No auth required
- **Features:** Website scraping, business info extraction
- **Rate Limited:** Token-bucket at `OUTBOUND_REQUESTS_PER_SECOND`