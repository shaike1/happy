# Happy Server Admin Dashboard

Live admin dashboard for Happy Server with real-time data, authentication, and auto-refresh.

## Features

- **Live Data** - Real-time statistics from PostgreSQL database
- **Auto-Refresh** - Updates every 30 seconds automatically
- **Authentication** - HTTP Basic Auth protection
- **REST API** - Full-featured API for all data
- **Beautiful UI** - Modern, dark-themed responsive design
- **Traefik Integration** - Automatic HTTPS with Let's Encrypt

## Quick Start

### 1. Deploy Dashboard

```bash
# Copy files to server
scp -r happy-admin-api root@right-api.com:/root/

# SSH to server
ssh root@right-api.com

# Navigate to directory
cd /root/happy-admin-api

# Set database password (must match your Happy server)
export HAPPY_DB_PASSWORD="your_password_here"

# Set admin credentials
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="your_secure_password"

# Start the dashboard
docker-compose up -d --build
```

### 2. Access Dashboard

Visit: **https://admin.happy.right-api.com/**

Login with:
- Username: `admin`
- Password: (the one you set in ADMIN_PASSWORD)

## API Endpoints

All endpoints require HTTP Basic Authentication.

### Statistics
- `GET /api/stats` - Overall statistics
- `GET /api/accounts` - All accounts with stats
- `GET /api/machines` - All machines/devices
- `GET /api/sessions?hours=24` - Active sessions
- `GET /api/activity` - Hourly activity (last 24h)
- `GET /api/push-tokens` - Mobile push tokens
- `GET /api/usage-reports` - Recent usage/billing reports

### Health Check
- `GET /api/health` - Health check (no auth required)

## Configuration

### Environment Variables

- `DB_HOST` - PostgreSQL host (default: happy-postgres)
- `DB_PORT` - PostgreSQL port (default: 5432)
- `DB_NAME` - Database name (default: happy)
- `DB_USER` - Database user (default: happy)
- `DB_PASSWORD` - Database password (required)
- `ADMIN_USERNAME` - Dashboard username (default: admin)
- `ADMIN_PASSWORD` - Dashboard password (default: happy-admin-2025)

### Change Credentials

```bash
# Stop container
docker-compose down

# Edit .env file or export new values
export ADMIN_USERNAME="newadmin"
export ADMIN_PASSWORD="newsecurepassword"

# Restart
docker-compose up -d
```

## Features Detail

### Auto-Refresh
- Automatically refreshes data every 30 seconds
- Can be toggled on/off via checkbox
- Manual refresh button available

### Live Statistics
- Total Accounts
- Active Machines
- Total Sessions
- Total Messages
- Active Sessions (last hour)

### Data Views
1. **Overview** - Devices and push tokens
2. **Accounts** - All user accounts with activity
3. **Sessions** - Active sessions in last 24h
4. **Activity** - Hourly message statistics
5. **Commands** - Quick reference for management scripts

## Troubleshooting

### Check if running
```bash
docker ps | grep happy-admin-api
```

### View logs
```bash
docker logs happy-admin-api -f
```

### Test API directly
```bash
curl -u admin:your_password https://admin.happy.right-api.com/api/stats
```

### Restart dashboard
```bash
cd /root/happy-admin-api
docker-compose restart
```

## Security

- Protected by HTTP Basic Authentication
- HTTPS via Traefik + Let's Encrypt
- Security headers enabled
- Database credentials in environment variables
- No data stored in dashboard (read-only from DB)

## Updating

```bash
cd /root/happy-admin-api
git pull  # or copy new files
docker-compose up -d --build
```
