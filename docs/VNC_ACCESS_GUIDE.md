# VNC Access Guide for IB Gateway

## What is VNC?

**VNC (Virtual Network Computing)** is a remote desktop protocol that lets you view and control the IB Gateway graphical interface running inside the Docker container from your computer.

Think of it like Remote Desktop for the Docker container.

## How to Access IB Gateway

### Option 1: Using VNC Viewer (Recommended)

1. **Download VNC Viewer**:
   - Download from: https://www.realvnc.com/en/connect/download/viewer/
   - Or install via command line:
     ```bash
     # Ubuntu/Debian
     sudo apt install tigervnc-viewer

     # macOS
     brew install --cask vnc-viewer
     ```

2. **Connect to IB Gateway**:
   - Open VNC Viewer
   - Enter address: `localhost:5900`
   - Password: `changeme` (from your .env file's `VNC_PASSWORD`)

3. **Login to Interactive Brokers**:
   - You'll see the IB Gateway login screen
   - Enter your IB credentials:
     - Username: Your IB username
     - Password: Your IB password
   - Select "Paper Trading" mode
   - Click "Login"

### Option 2: Using Built-in VNC Clients

**macOS (Built-in Screen Sharing)**:
```bash
open vnc://localhost:5900
# Password: changeme
```

**Linux (Remmina or built-in VNC viewer)**:
```bash
# Using vncviewer
vncviewer localhost:5900

# Or
remmina -c vnc://localhost:5900
```

**Windows**:
- Download TightVNC or RealVNC Viewer
- Connect to `localhost:5900`
- Password: `changeme`

## What You'll See

Once connected, you'll see:
1. **IB Gateway Login Screen** - Enter your IB credentials
2. **Gateway Configuration** - API settings (already configured by Docker)
3. **Connection Status** - Shows when successfully connected

## Troubleshooting

### Can't Connect to VNC?

```bash
# Check if IB Gateway is running
docker compose ps

# Should show:
# ib-gateway   gnzsnz/ib-gateway:latest   Up   0.0.0.0:5900->5900/tcp

# Check logs
docker compose logs ib-gateway
```

### Connection Refused?

Wait 30-60 seconds after starting the container. IB Gateway takes time to initialize.

### Wrong Password?

The password is set in `.env` file:
```bash
# Check your VNC password
grep VNC_PASSWORD .env

# Default is: changeme
```

## Current Setup

- **VNC URL**: `vnc://localhost:5900`
- **VNC Password**: `changeme` (can be changed in `.env`)
- **IB Gateway Port**: 4001 (paper trading)
- **Container Name**: `ib-gateway`

## After Login

Once logged in via VNC:
1. The IB Gateway window will show "Connected"
2. You can minimize/close the VNC window - Gateway keeps running
3. Your LEAN algorithms can now connect to IB API on port 4001

## Security Note

⚠️ **Important**: The VNC password is stored in plain text in `.env`. This is fine for local development, but:
- Don't expose port 5900 to the internet
- Change the default password in `.env`
- Use a firewall to restrict access

## Stopping IB Gateway

```bash
# Stop the container
docker compose stop ib-gateway

# Or stop everything
./scripts/stop.sh
```

## Next Steps

After logging in via VNC:
1. Verify connection status in IB Gateway window
2. Test the API connection with a simple LEAN algorithm
3. Monitor logs: `docker compose logs -f ib-gateway`

---

**Current Status**: IB Gateway is running at `localhost:5900` (VNC) and `localhost:4001` (API)
