# Meta Integration Setup Guide

## Overview
This guide covers connecting your Meta Business assets (Facebook Pages, Instagram Business Accounts, WhatsApp Business) to the Omni Inbox Hub platform.

## Prerequisites
- A Meta Business Account
- A Meta Developer App (create at https://developers.facebook.com)
- Admin access to your Facebook Pages and Instagram Business accounts

## Step 1: Create Meta App

1. Go to https://developers.facebook.com
2. Click "Create App"
3. Select "Business" type
4. Enter app name and select your Business Account
5. Add the following products:
   - **Facebook Login** (for OAuth)
   - **Messenger** (for FB Page messaging)
   - **Instagram** (for IG DMs and comments)
   - **WhatsApp** (for WA messaging, if applicable)

## Step 2: Configure App Settings

### App ID & Secret
- Copy **App ID** from Settings > Basic
- Copy **App Secret** from Settings > Basic

### OAuth Redirect URI
Add your redirect URI in Facebook Login > Settings > Valid OAuth Redirect URIs:
```
https://<YOUR_DOMAIN>/api/v2/integrations/meta/oauth/callback
```

### Required Permissions (Scopes)
Request these permissions:
- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_metadata`
- `pages_messaging`
- `pages_manage_posts`
- `instagram_basic`
- `instagram_manage_messages`
- `instagram_manage_comments`
- `business_management`

## Step 3: Configure in Dashboard

1. Go to **Integrations** page in your dashboard
2. Click **Configure** on the Meta Platform card
3. Enter:
   - **Meta App ID**: Your app ID
   - **App Secret**: Your app secret
   - **Webhook Verify Token**: Auto-generated (or set custom)
4. Click **Save Configuration**

## Step 4: Set Up Webhooks in Meta Dashboard

1. In Meta Developer Dashboard, go to **Webhooks** settings
2. Set **Callback URL**: Copy from the Configure dialog
   ```
   https://<YOUR_DOMAIN>/api/v2/webhooks/meta/<your-tenant-slug>
   ```
3. Set **Verify Token**: Copy from the Configure dialog
4. Subscribe to these fields:
   - **Page**: `messages`, `messaging_postbacks`, `feed`
   - **Instagram**: `messages`, `comments`, `mentions`
   - **WhatsApp Business Account**: `messages`

## Step 5: Connect via OAuth

1. Click **Connect Meta** button on the Integrations page
2. A Meta authorization window opens
3. Select the Pages and Instagram accounts to connect
4. Authorize the app
5. Connection completes automatically

## Step 6: Enable Assets

1. After OAuth, click **Assets** on the Meta card
2. Click **Discover** to scan your connected assets
3. Toggle ON the assets you want to enable:
   - **FB_PAGE**: Receive Facebook Page messages and comments
   - **IG_ACCOUNT**: Receive Instagram DMs and comments
   - **WA_PHONE_NUMBER**: Receive WhatsApp messages
4. Click **Save Asset Settings**

## WhatsApp 24-Hour Window

WhatsApp has a **Customer Service Window** policy:
- You can send free-form messages within **24 hours** of the customer's last message
- After 24 hours, you must use a **pre-approved template message**
- If you try to send outside the window, you'll get a `TEMPLATE_REQUIRED` error

### Template Messages (Coming Soon)
Template messages must be approved by Meta before use. This feature will be available in a future update.

## Troubleshooting

### "Invalid signature" errors
- Verify your App Secret is correctly entered
- Ensure you're using the SHA256 HMAC signature

### "Token expired" errors
- The system automatically refreshes tokens every 6 hours
- If auto-refresh fails, reconnect via OAuth

### No messages arriving
- Check webhook subscriptions in Meta Developer Dashboard
- Verify the correct assets are enabled
- Check audit log for META_WEBHOOK_PROCESSED events

### Missing Instagram account
- Instagram Business Account must be linked to a Facebook Page
- Run asset discovery again after linking

## Architecture Notes

- Each tenant has their own webhook URL and verify token
- Tokens are stored encrypted in the database
- Inbound messages/comments arrive via webhooks in real-time
- Outbound messages are sent via Meta Graph API
- All operations are audit-logged
- Rate limiting applied on webhook endpoints (120/min/IP)
