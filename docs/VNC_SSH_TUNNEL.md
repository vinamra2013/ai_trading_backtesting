# VNC Access via SSH Tunnel

## Problem

VNC connection to `192.168.40.100:5900` is being refused due to Docker networking or firewall configuration.

## Solution: SSH Tunnel

Use an SSH tunnel to securely forward the VNC port from the server to your local machine.

---

## Step-by-Step Guide

### On Your Local Machine (Windows/Mac/Linux)

**Open a terminal/command prompt and run:**

```bash
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100
```

**Explanation**:
- `-L 5900:localhost:5900` - Forward local port 5900 to server's localhost:5900
- `vbhatnagar@192.168.40.100` - Your SSH username and server IP
- Keep this terminal window open while using VNC

### Then Connect VNC to Localhost

**Now open your VNC viewer and connect to:**
- **Address**: `localhost:5900` (or `127.0.0.1:5900`)
- **Password**: `changeme`

The SSH tunnel will forward your VNC connection through the secure SSH connection to the Docker container.

---

## Platform-Specific Instructions

### Windows (PowerShell or CMD)

```powershell
# Open PowerShell or Command Prompt
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# Keep this window open
# In another window, open VNC viewer to: localhost:5900
```

### macOS

```bash
# Terminal
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# Keep Terminal open
# Open Screen Sharing or VNC viewer
open vnc://localhost:5900
```

### Linux

```bash
# Terminal
ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# In another terminal or VNC viewer
vncviewer localhost:5900
```

---

## Why This Works

1. **SSH Tunnel** creates a secure encrypted tunnel between your machine and the server
2. **Port Forwarding** maps your local port 5900 → server's localhost:5900
3. **Docker** is listening on localhost:5900, which the tunnel can reach
4. **No Firewall Issues** because everything goes through SSH (port 22)

---

## Alternative: Background SSH Tunnel

If you want the tunnel to run in the background:

```bash
# Linux/macOS - Run in background
ssh -f -N -L 5900:localhost:5900 vbhatnagar@192.168.40.100

# Windows - Use PuTTY:
# 1. Open PuTTY
# 2. Session: 192.168.40.100
# 3. Connection → SSH → Tunnels:
#    - Source port: 5900
#    - Destination: localhost:5900
#    - Click "Add"
# 4. Connect
```

---

## Troubleshooting

### "Connection Refused" on localhost:5900

**Check if SSH tunnel is running:**
```bash
# On your local machine
netstat -an | grep 5900
# or
lsof -i :5900
```

You should see port 5900 listening on 127.0.0.1

### "Permission denied" or "Port already in use"

**Something is already using port 5900 on your local machine:**
```bash
# Use a different local port, e.g., 5901
ssh -L 5901:localhost:5900 vbhatnagar@192.168.40.100

# Then connect VNC to: localhost:5901
```

### SSH Connection Issues

```bash
# Test basic SSH connectivity
ssh vbhatnagar@192.168.40.100 echo "SSH works"

# If this fails, fix SSH access first
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ VNC via SSH Tunnel - Quick Reference                   │
├─────────────────────────────────────────────────────────┤
│ 1. Open terminal and run:                              │
│    ssh -L 5900:localhost:5900 vbhatnagar@192.168.40.100│
│                                                         │
│ 2. Keep terminal open                                  │
│                                                         │
│ 3. Open VNC viewer to: localhost:5900                  │
│    Password: changeme                                  │
│                                                         │
│ 4. Login to IB Gateway with your IB credentials       │
└─────────────────────────────────────────────────────────┘
```

---

## Security Note

✅ **SSH Tunnel is MORE secure** than direct VNC:
- All VNC traffic is encrypted through SSH
- No need to expose VNC port to the network
- Uses your existing SSH authentication

---

## After Connection

Once you're logged into IB Gateway via VNC:
1. IB Gateway window will show "Connected"
2. You can close VNC (minimize the window)
3. Keep the SSH tunnel open
4. Your LEAN algorithms can now connect to IB API

---

**Server**: 192.168.40.100
**SSH User**: vbhatnagar
**VNC Port**: 5900
**VNC Password**: changeme
