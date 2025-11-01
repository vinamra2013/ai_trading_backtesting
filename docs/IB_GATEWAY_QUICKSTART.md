# IB Gateway Quick Start Guide

## Current Status

✅ **IB Gateway is running!**
- Container: `ib-gateway` (gnzsnz/ib-gateway:latest)
- VNC Server: Running on port 5900
- IB API: Port 4001 (paper trading)
- Status: Waiting for valid IB credentials

## 🚨 Current Issue

**Login Error**: "Too many failed login attempts. Please wait 57 seconds."

**Cause**: Using placeholder credentials (`your_ib_username` and `your_ib_password`) from `.env.example`

**Solution**: Add your real Interactive Brokers credentials to `.env` file

---

## Step 1: Add Your IB Credentials

Edit the `.env` file with your actual Interactive Brokers account:

```bash
# Edit .env file
nano .env

# Replace these lines:
IB_USERNAME=your_ib_username    # ← Change to your IB username
IB_PASSWORD=your_ib_password    # ← Change to your IB password
```

**Get Your IB Credentials**:
1. Go to: https://www.interactivebrokers.com/
2. Login to Client Portal
3. Use the same username/password for the `.env` file

---

## Step 2: Restart IB Gateway

After updating `.env`:

```bash
# Restart the container to apply new credentials
docker compose restart ib-gateway

# Wait 60 seconds (to clear the "too many attempts" lockout)
sleep 60

# Check logs
docker compose logs -f ib-gateway
```

---

## Step 3: Access via VNC (SSH Tunnel)

Since direct network access is blocked, use an SSH tunnel:

### On Your Local Machine:

```bash
# Create SSH tunnel
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100
```

**Keep this terminal open!**

### Connect VNC:

- **Address**: `localhost:5900` (on your local machine)
- **Password**: `changeme`

---

## What You'll See in VNC

Once connected to VNC, you'll see one of:

### If Credentials Are Correct:
- ✅ IB Gateway window showing "Connected"
- Green indicator light
- "Paper Trading" mode active

### If Credentials Are Wrong:
- ❌ Error dialog: "Login failed"
- Try again with correct credentials

### If Too Many Failed Attempts:
- ⏳ "Please wait X seconds before attempting to re-login"
- Wait, then restart container

---

## Troubleshooting

### Error: "Too many failed login attempts"

```bash
# Wait 60 seconds, then restart
sleep 60
docker compose restart ib-gateway
```

### VNC Connection Refused

```bash
# Make sure SSH tunnel is running
# On your local machine:
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# Then VNC to: localhost:5900
```

### Container Keeps Restarting

```bash
# Check logs for errors
docker compose logs ib-gateway

# Common issues:
# 1. Invalid IB credentials
# 2. IB account not activated
# 3. Paper trading not enabled
```

### Check Container Status

```bash
# View status
docker compose ps ib-gateway

# View logs
docker compose logs -f ib-gateway

# Restart if needed
docker compose restart ib-gateway
```

---

## Interactive Brokers Account Setup

### Don't Have an IB Account?

1. **Sign Up**: https://www.interactivebrokers.com/
   - Choose "Individual" account
   - Complete application (takes 1-2 days)

2. **Enable Paper Trading**:
   - Login to Client Portal
   - Go to: Account Settings → Paper Trading
   - Enable paper trading account

3. **Get API Access**:
   - Go to: Settings → API → Settings
   - Enable "ActiveX and Socket Clients"
   - Set "Read-Only API" to "No"

### Already Have an Account?

Just need your:
- Username (login name)
- Password
- Paper trading must be enabled

---

## Security Notes

⚠️ **Important**:
- `.env` contains sensitive credentials - **never commit to git**
- Change `VNC_PASSWORD` from default `changeme`
- IB API connection is **unencrypted** - use SSH tunnel or VPN for remote access
- Keep IB Gateway container updated: `docker compose pull ib-gateway`

---

## Next Steps After Login

Once IB Gateway shows "Connected":

1. **VNC can be closed** - IB Gateway keeps running in background
2. **API is available** on `localhost:4001` for LEAN algorithms
3. **Monitor logs**: `docker compose logs -f ib-gateway`
4. **Test connection** with a simple LEAN algorithm (Epic 3-4)

---

## Quick Reference

```
┌──────────────────────────────────────────────────┐
│ IB Gateway Quick Reference                      │
├──────────────────────────────────────────────────┤
│ Server IP:        192.168.40.100                │
│ VNC Port:         5900 (via SSH tunnel)         │
│ VNC Password:     changeme                      │
│ IB API Port:      4001 (paper trading)          │
│ Container:        ib-gateway                    │
│                                                  │
│ SSH Tunnel Command:                             │
│ ssh -L 5900:localhost:5900 vbhatnagar@192...   │
│                                                  │
│ VNC Address:      localhost:5900 (after tunnel)│
└──────────────────────────────────────────────────┘
```

---

**Last Updated**: 2025-11-01
**Status**: VNC working, waiting for valid IB credentials
