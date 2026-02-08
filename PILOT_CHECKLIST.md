# Pilot Go-Live Checklist v6.0.0

## Infrastructure Requirements

### VPS Specs (Minimum)
- CPU: 2 vCPU
- RAM: 4 GB
- Disk: 40 GB SSD
- OS: Ubuntu 22.04 LTS

### Docker Production Config
```yaml
# docker-compose.prod.yml
services:
  backend:
    image: omnihub-backend
    ports: ["8001:8001"]
    env_file: .env.prod
    restart: always
    deploy:
      resources:
        limits: { cpus: '1.0', memory: 2G }
  frontend:
    image: omnihub-frontend
    ports: ["3000:3000"]
    restart: always
  mongodb:
    image: mongo:7
    volumes: ["mongo-data:/data/db"]
    restart: always
volumes:
  mongo-data:
```

### Environment Variables (.env.prod)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=omnihub_production
JWT_SECRET=<generate-64-char-random>
GUEST_JWT_SECRET=<generate-64-char-random>
VAULT_MASTER_KEY=<generate-64-char-random>
PUBLIC_BASE_URL=https://yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

### SSL + Domain Setup
- [ ] DNS A record pointing to VPS IP
- [ ] Nginx reverse proxy configured
- [ ] Let's Encrypt SSL certificate (certbot)
- [ ] Force HTTPS redirect
- [ ] WebSocket upgrade in Nginx config

## MongoDB Backup Schedule
```bash
# Daily backup cron (add to /etc/cron.d/omnihub-backup)
0 3 * * * mongodump --uri="mongodb://localhost:27017" --db=omnihub_production --out=/backups/$(date +\%Y\%m\%d) --gzip
# Keep 30 days
0 4 * * * find /backups -mtime +30 -delete
```

## Log Rotation
```bash
# /etc/logrotate.d/omnihub
/var/log/supervisor/backend.*.log {
    daily
    missingok
    rotate 14
    compress
    notifempty
    copytruncate
}
```

## Rate Limit Config
| Endpoint | Limit | Window |
|----------|-------|--------|
| Public payment endpoints | 30/min | per IP |
| Guest resolve room/table | 10/min | per IP |
| WebChat start | 15/min | per IP |
| Auth login | 5/min | per IP |

## First Tenant Creation

### Step 1: Seed Demo Data (optional)
```bash
curl -X POST https://yourdomain.com/api/seed
```

### Step 2: Register Production Tenant
```bash
curl -X POST https://yourdomain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Hotel Name",
    "tenant_slug": "hotel-slug",
    "business_type": "hotel",
    "plan": "pro",
    "email": "admin@hotel.com",
    "password": "secure-password",
    "name": "Admin Name"
  }'
```

### Step 3: Create Properties
```bash
curl -X POST https://yourdomain.com/api/v2/properties/tenants/hotel-slug/properties \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Main Building", "slug": "main", "address": "...", "phone": "..."}'
```

### Step 4: Create Rooms & Tables
Use the Rooms page and Tables page in the admin UI.

## Printing QR Sheets

### Room QR Codes
1. Go to Rooms page
2. Select rooms to print
3. Click "Print QR" button
4. OR use API: `GET /api/v2/hotel/rooms/print.pdf?ids=id1,id2,id3`

### Table QR Codes
Similar process via Tables page or restaurant router.

## Enabling Connectors

### Built-in
- **WebChat**: Automatically available via guest URLs
- **Widget**: Embed `<script src="/api/v2/inbox/webchat/widget.js?tenantSlug=hotel-slug"></script>`

### Stub Connectors (for testing)
1. Go to Integrations page
2. Add WhatsApp connector (stub mode)
3. Add Instagram connector (stub mode)
4. Click "Sync Now" to pull test data

## Daily Monitoring

### Health Check
```bash
curl -s https://yourdomain.com/api/health | jq .
# Expected: {"status":"ok","version":"6.0.0",...}
```

### Key Metrics to Watch
- [ ] MongoDB connection status
- [ ] Offer expiration job running (check logs for "Expired X offers")
- [ ] WebSocket connections active
- [ ] API response times (check structured logs for duration_ms)
- [ ] Rate limit hits (429 responses in logs)

### Data Export (backup verification)
```bash
cd /app/backend
python manage.py export --tenant hotel-slug
# Check: /tmp/omnihub_export_hotel-slug_*/
```

### Audit Log Review
- Check `/audit` page in admin UI daily
- Look for unusual patterns:
  - Repeated failed logins
  - Bulk offer creation
  - Unexpected reservation cancellations

## Emergency Procedures

### Restart Services
```bash
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
sudo supervisorctl restart all
```

### Check Logs
```bash
tail -f /var/log/supervisor/backend.err.log
tail -f /var/log/supervisor/frontend.err.log
```

### Database Recovery
```bash
mongorestore --uri="mongodb://localhost:27017" --db=omnihub_production /backups/YYYYMMDD/omnihub_production/ --gzip
```
