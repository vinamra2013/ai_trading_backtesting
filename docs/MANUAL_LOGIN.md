# Manual IB Gateway Login via VNC

## Why Manual Login?

IB Gateway automated login is failing with "Unrecognized Username or Password". This is common and can happen for several reasons:
- Two-factor authentication (2FA)
- Paper trading account uses different credentials
- Special characters in password
- Account-specific requirements

**Solution**: Login manually via VNC once, then IB Gateway will remember your session.

---

## Step-by-Step Manual Login

### 1. Create SSH Tunnel (On Your Local Machine)

```bash
# Open terminal and run:
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# Keep this terminal open!
```

### 2. Connect VNC Viewer

**Download VNC Viewer** (if you don't have it):
- https://www.realvnc.com/en/connect/download/viewer/

**Connect**:
- Address: `localhost:5900`
- Password: `changeme`

### 3. You'll See the IB Gateway Window

You should see a dialog box titled:
**"Unrecognized Username or Password"**

Click **"OK"** to dismiss it.

### 4. Login Manually

You'll see the IB Gateway login screen with:
- Username field
- Password field
- Trading Mode dropdown (select "Paper Trading")
- Login button

**Enter your credentials and click "Paper Log In"**

### 5. Handle Two-Factor Authentication (if prompted)

If you have 2FA enabled:
- IB will send you a code (SMS or app)
- Enter the code in the VNC window
- Complete the login

### 6. Verify Connection

Once logged in successfully, you should see:
- ✅ "Connected" status in IB Gateway window
- Green indicator light
- "Paper Trading" mode displayed

---

## After Manual Login

Once logged in:
1. **IB Gateway will remember your session** (stored in container)
2. **You can close the VNC viewer** - Gateway keeps running
3. **The API is available** at `localhost:4001`
4. **Container restarts will require login again** (VNC session is not persisted)

---

## Troubleshooting

### Can't See the Login Window?

```bash
# Check container is running
docker compose ps ib-gateway

# Check logs
docker compose logs ib-gateway --tail 20

# Restart if needed
docker compose restart ib-gateway
```

### VNC Shows Black Screen?

Wait 30-60 seconds for the IB Gateway application to start.

### SSH Tunnel Not Working?

```bash
# Test SSH connection first
ssh vbhatnagar@192.168.40.100 echo "SSH works"

# Then try the tunnel again
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100
```

### Getting "Connection Refused" in VNC?

Make sure:
1. SSH tunnel is running (terminal still open)
2. VNC viewer is connecting to `localhost:5900` (NOT 192.168.40.100:5900)
3. Container is running: `docker compose ps`

---

## Alternative: Fix Automated Login

If you want to fix the automated login, check these:

### 1. Check Your IB Account Type

**Paper Trading Account**:
- Username might be different from live account
- Usually shows in IB portal as "Paper Trading Account"
- Login to: https://gdcdyn.interactivebrokers.com/sso/Login (Paper Trading portal)

### 2. Verify Credentials Format

In `.env` file:
```bash
# Some IB accounts need the full account username:
IB_USERNAME=montypython6        # Try this
# or
IB_USERNAME=montypython6_paper  # Or this (some accounts append _paper)
# or use your account number
IB_USERNAME=U1234567           # Your actual account number

IB_PASSWORD=your_password      # Exact password (case-sensitive)
```

### 3. Disable Environment Variable Login (Use Manual Only)

If you prefer manual login every time:

Edit `docker-compose.yml` and comment out the auto-login:
```yaml
environment:
  # - TWS_USERID=${IB_USERNAME}
  # - TWS_PASSWORD=${IB_PASSWORD}
  - TRADING_MODE=${IB_TRADING_MODE:-paper}
```

Then restart:
```bash
docker compose down
docker compose up -d ib-gateway
```

---

## Quick Reference

```
┌────────────────────────────────────────────┐
│ Manual Login Quick Reference              │
├────────────────────────────────────────────┤
│ 1. SSH tunnel:                            │
│    ssh -L 5900:localhost:5900 \           │
│        vbhatnagar@192.168.40.100          │
│                                            │
│ 2. VNC to: localhost:5900                 │
│    Password: changeme                     │
│                                            │
│ 3. Login to IB Gateway with your IB creds│
│                                            │
│ 4. Select "Paper Trading" mode            │
│                                            │
│ 5. Click "Paper Log In"                   │
└────────────────────────────────────────────┘
```

---

**Current Status**: Container running, waiting for manual VNC login
**Next Step**: Use VNC to login manually
