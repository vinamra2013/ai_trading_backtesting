# IB Gateway Setup Guide

Complete guide for Interactive Brokers Gateway setup with automated login.

---

## Quick Start

```bash
# 1. Start the platform
./scripts/start.sh

# 2. Verify IB Gateway logged in
docker compose logs ib-gateway | grep "Login has completed"

# 3. Test API connection
nc -zv localhost 4001
```

**That's it!** IB Gateway logs in automatically. ✅

---

## Configuration

### Required Files

**`.env`** - IB credentials (username only)
```bash
IB_USERNAME=your_ib_username
IB_TRADING_MODE=paper
IB_GATEWAY_PORT=4001
VNC_PASSWORD=changeme
```

**`secrets/ib_password.txt`** - Password file (gitignored)
```
your_ib_password
```

### Setup Instructions

1. **Create password file**:
   ```bash
   mkdir -p secrets
   echo -n 'your_password' > secrets/ib_password.txt
   chmod 600 secrets/ib_password.txt
   ```

2. **Edit .env**:
   ```bash
   nano .env
   # Set IB_USERNAME to your IB username
   ```

3. **Start platform**:
   ```bash
   ./scripts/start.sh
   ```

---

## How It Works

### Automated Login
- Uses **Docker secrets** (password file method)
- Handles special characters in passwords
- No manual VNC login required
- Works on every container restart

### Architecture
```
docker-compose.yml
    ↓
TWS_USERID=${IB_USERNAME} (from .env)
TWS_PASSWORD_FILE=/run/secrets/ib_password (from secrets/ib_password.txt)
    ↓
IB Gateway automatically logs in
    ↓
IB API available on port 4001
```

---

## VNC Access (Optional)

VNC is **optional** since automated login works. Use it if you want to see the IB Gateway GUI.

### Via SSH Tunnel (Recommended)

**On your local machine**:
```bash
# Create SSH tunnel
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100
```

**Keep terminal open, then**:
- Open VNC Viewer
- Address: `localhost:5900`
- Password: `changeme` (from .env VNC_PASSWORD)

### VNC Viewers
- **macOS**: `open vnc://localhost:5900`
- **Windows**: RealVNC Viewer or TightVNC
- **Linux**: `vncviewer localhost:5900`

---

## Troubleshooting

### Login Failed

**Check logs**:
```bash
docker compose logs ib-gateway | tail -50
```

**Look for**:
- ✅ "Login has completed" = Success
- ❌ "Unrecognized Username or Password" = Wrong credentials

**Fix**:
```bash
# 1. Verify password file
cat secrets/ib_password.txt

# 2. Verify username
grep IB_USERNAME .env

# 3. Restart container
docker compose restart ib-gateway
```

### API Port Not Accessible

```bash
# Wait 30-60 seconds for initialization
sleep 30

# Test connection
nc -zv localhost 4001

# Should show: Connection succeeded
```

### Container Won't Start

```bash
# Check container status
docker compose ps ib-gateway

# View full logs
docker compose logs ib-gateway

# Rebuild and restart
docker compose down
docker compose up -d ib-gateway
```

### VNC Connection Refused

**If using SSH tunnel**:
```bash
# Make sure tunnel is running
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# In another terminal, connect VNC to: localhost:5900
```

---

## Password with Special Characters

The Docker secrets method handles **any** special characters:
- `@` `$` `#` `%` `&` `*` `(` `)` etc.

No escaping needed! Just put the exact password in `secrets/ib_password.txt`.

---

## Updating Credentials

### Change Password:
```bash
# Edit password file
echo -n 'new_password' > secrets/ib_password.txt

# Restart
docker compose restart ib-gateway
```

### Change Username:
```bash
# Edit .env
nano .env
# Update: IB_USERNAME=new_username

# Restart
docker compose restart ib-gateway
```

---

## Security

✅ **Good Practices**:
- Password in secure file (not environment variable)
- `secrets/` excluded from git (.gitignore)
- File permissions: 600 (owner read/write only)
- Docker secrets mounted as tmpfs (RAM-based, never on disk)

⚠️ **Important**:
- Never commit `secrets/` to git
- Change default VNC password from `changeme`
- Don't expose ports 4001 or 5900 to the internet
- Use SSH tunnel for remote access

---

## Reference

### Ports
- **4001**: IB API (paper trading)
- **4002**: IB API (live trading - disabled by default)
- **5900**: VNC server

### Files
- **docker-compose.yml**: Container configuration
- **.env**: Username and settings
- **secrets/ib_password.txt**: Password (gitignored)
- **.gitignore**: Excludes secrets/

### Commands
```bash
# Start platform
./scripts/start.sh

# Stop platform
./scripts/stop.sh

# Restart IB Gateway
docker compose restart ib-gateway

# View logs
docker compose logs -f ib-gateway

# Container status
docker compose ps
```

---

## IB Account Setup

### Get IB Credentials

1. **Sign up**: https://www.interactivebrokers.com/
2. **Enable paper trading**:
   - Login to Client Portal
   - Account Settings → Paper Trading → Enable
3. **Enable API access**:
   - Settings → API → Settings
   - Enable "ActiveX and Socket Clients"
   - Set "Read-Only API" to "No"

---

## Next Steps

After IB Gateway is running:

1. ✅ **Epic 3**: Data Management Pipeline
2. ✅ **Epic 4**: Backtesting Infrastructure
3. ✅ **Epic 5**: Live Trading Engine

---

**Status**: Automated login working! Ready for LEAN algorithms. 🚀
