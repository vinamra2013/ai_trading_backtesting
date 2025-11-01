# Fixing Automated IB Gateway Login

## Root Cause Identified

**Your password contains special characters**: `Preet@122`

The `@` symbol (and other special characters) can cause issues with Docker environment variables and IB Gateway's automated login system.

## Why Manual Login Works

When you login manually via VNC:
- You type the password directly into the IB Gateway GUI
- No environment variable parsing involved
- Special characters are handled correctly

## Why Automated Login Fails

When using `.env` credentials:
- Docker parses the environment variables
- The `@` symbol might be interpreted incorrectly
- IB Gateway receives a malformed password
- Result: "Unrecognized Username or Password"

---

## Solutions

### Option 1: Quote the Password in docker-compose.yml (Recommended)

Edit `docker-compose.yml`:

```yaml
ib-gateway:
  environment:
    - TWS_USERID=${IB_USERNAME}
    - TWS_PASSWORD="${IB_PASSWORD}"  # Add quotes around the variable
```

Then restart:
```bash
docker compose down
docker compose up -d ib-gateway
```

### Option 2: Escape Special Characters in .env

Edit `.env` and escape the `@` symbol:

```bash
# Try one of these formats:
IB_PASSWORD='Preet@122'     # Single quotes
IB_PASSWORD="Preet@122"     # Double quotes
IB_PASSWORD=Preet\@122      # Escape with backslash
```

Then restart:
```bash
docker compose restart ib-gateway
```

### Option 3: Use Manual Login (Current Working Solution)

This is what you're doing now:
- Keep the automated login disabled or failing
- Login manually via VNC every time
- **Pros**: Works reliably, handles any password
- **Cons**: Need to login after each container restart

---

## Testing Automated Login

After trying Option 1 or 2, test it:

1. **Stop the container**:
   ```bash
   docker compose stop ib-gateway
   ```

2. **Start it again**:
   ```bash
   docker compose up -d ib-gateway
   ```

3. **Watch the logs**:
   ```bash
   docker compose logs -f ib-gateway
   ```

4. **Look for**:
   - ✅ "Gateway has logged on successfully" or similar
   - ✅ No "Unrecognized Username or Password" error

5. **Verify via VNC**:
   - Connect via SSH tunnel + VNC
   - Check if IB Gateway shows "Connected" automatically

---

## Special Characters Reference

Common characters that cause issues in environment variables:

```
@  # At symbol (your case)
$  # Dollar sign
#  # Hash/pound
%  # Percent
&  # Ampersand
*  # Asterisk
(  # Parentheses
)
"  # Quotes
'  # Single quotes
\  # Backslash
|  # Pipe
<  # Less than
>  # Greater than
;  # Semicolon
`  # Backtick
```

**Solutions**:
- Wrap in single quotes: `PASSWORD='my@pass'`
- Wrap in double quotes: `PASSWORD="my@pass"`
- Escape with backslash: `PASSWORD=my\@pass`
- Or use manual VNC login (simplest!)

---

## Recommendation

**For your situation**, I recommend:

**Option 3: Continue using manual login**

**Reasons**:
1. ✅ Already working
2. ✅ Most reliable for special characters
3. ✅ No configuration changes needed
4. ✅ Better security (credentials not in environment variables)
5. ⚠️ Only downside: Need to login after restarts (but restarts are rare)

**If you want automated login**, try **Option 1** (quoting in docker-compose.yml) as it's the cleanest solution.

---

## Long-term Solution

If you want fully automated login without manual intervention:

1. **Change your IB password** to one without special characters:
   - Only letters, numbers, and basic symbols (. - _)
   - Example: `Preet.122` or `Preet-122` or `Preet_122`
   - Change at: https://www.interactivebrokers.com/ → Account Settings → Security

2. **Update .env** with new password

3. **Restart container**:
   ```bash
   docker compose restart ib-gateway
   ```

**Note**: Changing your IB password is optional. Manual login works perfectly fine!

---

## Current Status

✅ **Working Solution**: Manual VNC login
- No changes needed
- Works reliably
- Just login after each restart

🔧 **Optional Enhancement**: Try automated login with quoting (Option 1)
- Only if you want to avoid manual login
- Test it and see if it works

---

**Your Call**: Manual login is perfectly fine for a development/backtesting environment!
