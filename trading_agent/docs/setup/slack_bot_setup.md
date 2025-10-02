# Slack Bot Setup Guide

This guide will walk you through setting up a Slack bot for your trading agent.

## Prerequisites

- A Slack workspace where you have permission to install apps
- Admin access to create new Slack apps

## Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter:
   - **App Name**: `Trading Agent` (or your preferred name)
   - **Workspace**: Select your workspace
5. Click **"Create App"**

## Step 2: Configure Bot Token Scopes

1. In the left sidebar, click **"OAuth & Permissions"**
2. Scroll down to **"Scopes"** → **"Bot Token Scopes"**
3. Click **"Add an OAuth Scope"** and add these scopes:

   **Required scopes:**
   - `chat:write` - Send messages
   - `commands` - Create slash commands
   - `app_mentions:read` - Read @mentions
   - `channels:read` - View channel info
   - `groups:read` - View private channel info
   - `im:read` - View direct messages
   - `im:write` - Send direct messages
   - `users:read` - View user info

## Step 3: Install App to Workspace

1. Scroll to top of **"OAuth & Permissions"** page
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`)
   - This is your `bot_token`
   - ⚠️ Keep this secret!

## Step 4: Enable Socket Mode

1. In left sidebar, click **"Socket Mode"**
2. Toggle **"Enable Socket Mode"** to ON
3. Enter token name: `Trading Agent Socket`
4. Click **"Generate"**
5. **Copy the generated token** (starts with `xapp-`)
   - This is your `app_token`
   - ⚠️ Keep this secret!
6. Click **"Done"**

## Step 5: Enable Event Subscriptions

1. In left sidebar, click **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. Under **"Subscribe to bot events"**, add:
   - `app_mention` - When someone mentions your bot
   - `message.channels` - Messages in channels
   - `message.groups` - Messages in private channels
   - `message.im` - Direct messages
4. Click **"Save Changes"**

## Step 6: Create Slash Commands

1. In left sidebar, click **"Slash Commands"**
2. Click **"Create New Command"** for each command below:

### Command: /trading-report
- **Command**: `/trading-report`
- **Request URL**: Leave empty (using Socket Mode)
- **Short Description**: `Generate daily trading report`
- **Usage Hint**: (leave empty)

### Command: /portfolio
- **Command**: `/portfolio`
- **Request URL**: Leave empty
- **Short Description**: `View current portfolio status`

### Command: /backtest
- **Command**: `/backtest`
- **Request URL**: Leave empty
- **Short Description**: `Run a backtest`
- **Usage Hint**: `SYMBOLS START_DATE END_DATE`

### Command: /parameters
- **Command**: `/parameters`
- **Request URL**: Leave empty
- **Short Description**: `View strategy parameters`

### Command: /performance
- **Command**: `/performance`
- **Request URL**: Leave empty
- **Short Description**: `Analyze performance`
- **Usage Hint**: `[short|medium|long]`

### Command: /pause-trading
- **Command**: `/pause-trading`
- **Request URL**: Leave empty
- **Short Description**: `Emergency pause trading`

### Command: /resume-trading
- **Command**: `/resume-trading`
- **Request URL**: Leave empty
- **Short Description**: `Resume trading`

### Command: /evolve
- **Command**: `/evolve`
- **Request URL**: Leave empty
- **Short Description**: `Trigger evolution cycle`

## Step 7: Get Channel ID

1. Open Slack desktop or web app
2. Go to the channel where you want alerts
3. Click channel name at top
4. Scroll down and copy the **Channel ID**
   - Example: `C01234ABCDE`

## Step 8: Get Signing Secret

1. In left sidebar, click **"Basic Information"**
2. Scroll to **"App Credentials"**
3. **Copy the "Signing Secret"**
   - ⚠️ Keep this secret!

## Step 9: Update Your Config

Edit `config/config.yaml` and add your tokens:

```yaml
slack:
  bot_token: "xoxb-YOUR-BOT-TOKEN"
  app_token: "xapp-YOUR-APP-TOKEN"
  signing_secret: "YOUR-SIGNING-SECRET"
  channel_id: "YOUR-CHANNEL-ID"
  timezone: "Asia/Seoul"
  daily_report_time: "09:00"
```

## Step 10: Test Your Bot

1. Start your trading agent:
   ```bash
   cd trading_agent
   python main.py
   ```

2. In Slack, try a command:
   ```
   /portfolio
   ```

3. Try mentioning the bot:
   ```
   @Trading Agent what's the current market condition?
   ```

## Troubleshooting

### Bot not responding to commands
- Check that Socket Mode is enabled
- Verify `app_token` is correct
- Check console for error messages

### "Not authorized" errors
- Verify `bot_token` is correct
- Check that all required scopes are added
- Reinstall the app to workspace

### Commands not found
- Make sure all slash commands are created
- Wait a few minutes for Slack to sync
- Try reinstalling the app

### No alerts received
- Verify `channel_id` is correct
- Check that bot is invited to channel:
  ```
  /invite @Trading Agent
  ```

## Security Best Practices

1. **Never commit tokens to git**
   - Add `config/config.yaml` to `.gitignore`
   - Use environment variables in production

2. **Rotate tokens regularly**
   - Regenerate tokens periodically
   - Update config immediately

3. **Limit bot permissions**
   - Only add necessary scopes
   - Don't grant admin privileges

4. **Monitor bot activity**
   - Review bot logs regularly
   - Set up alerts for suspicious activity

## Next Steps

Once your bot is working:

1. Customize alert formats in `messaging/slack_bot.py`
2. Add more commands as needed
3. Set up scheduled reports
4. Configure additional notification channels

## Support

If you encounter issues:
1. Check Slack API documentation: https://api.slack.com/docs
2. Review bot logs in console
3. Test with simple commands first
4. Verify all configuration values are correct

Happy trading! 🚀