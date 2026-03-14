# Deploy xBrain Backend to Azure

## What you need

- Azure for Students account (you already have this)
- Your code pushed to GitHub

## Steps

### 1. Create a PostgreSQL database

1. Go to [Azure Portal](https://portal.azure.com)
2. Search **"Azure Database for PostgreSQL Flexible Server"** → Create
3. Settings:
   - **Resource group**: create new → `xbrain-rg`
   - **Server name**: `xbrain-db` (or anything you want)
   - **Region**: pick the closest to Egypt → `West Europe` or `North Europe`
   - **Workload type**: Development (cheapest)
   - **Compute**: Burstable B1ms ($12/month, covered by student credits)
   - **Authentication**: PostgreSQL authentication only
   - **Admin username**: `xbrainadmin`
   - **Password**: pick a strong one, save it somewhere
4. On the **Networking** tab:
   - Check **"Allow public access"**
   - Check **"Allow access from any Azure service"**
5. Click **Review + Create** → **Create**
6. Once created, go to the resource → **Databases** → **Add** → name it `xbrain_db`

Your database URL will be:
```
postgres://xbrainadmin:YOUR_PASSWORD@xbrain-db.postgres.database.azure.com:5432/xbrain_db
```

### 2. Create the App Service

1. In Azure Portal, search **"App Service"** → Create → **Web App**
2. Settings:
   - **Resource group**: `xbrain-rg` (same as above)
   - **Name**: `xbrain-backend` (this becomes `xbrain-backend.azurewebsites.net`)
   - **Runtime stack**: Python 3.10
   - **Region**: same as your database
   - **Pricing plan**: Free F1 (or B1 if you want better performance, both covered by credits)
3. Click **Review + Create** → **Create**

### 3. Set environment variables

1. Go to your App Service → **Settings** → **Environment variables**
2. Add these:

| Name | Value |
|------|-------|
| `DATABASE_URL` | `postgres://xbrainadmin:YOUR_PASSWORD@xbrain-db.postgres.database.azure.com:5432/xbrain_db?sslmode=require` |
| `SECRET_KEY` | generate one at https://djecrety.ir |
| `DEBUG` | `False` |
| `EMAIL_HOST_USER` | your Gmail address |
| `EMAIL_HOST_PASSWORD` | your Gmail app password |

3. Click **Apply**

### 4. Connect GitHub and deploy

1. Go to your App Service → **Deployment Center**
2. **Source**: GitHub
3. Sign in to GitHub → select your repo (`sameh625/xBrain-backend`) → branch `main`
4. Azure will auto-create a GitHub Actions workflow file
5. Click **Save**

### 5. Set the startup command

1. Go to App Service → **Settings** → **Configuration** → **General settings**
2. In **Startup Command**, enter:
   ```
   bash startup.sh
   ```
3. Click **Save**

### 6. Wait for deployment

- Go to **Deployment Center** → you'll see the deployment status
- First deployment takes 3-5 minutes
- Once it's green, your API is live at:
  ```
  https://xbrain-backend.azurewebsites.net/api/
  ```

## Test it

```bash
curl https://xbrain-backend.azurewebsites.net/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","username":"testuser1","password":"Test1234!","first_name":"Test","last_name":"User","phone_number":"+1234567890"}'
```

## Troubleshooting

**App won't start?**
- App Service → **Log stream** to see real-time logs
- Check that all environment variables are set correctly

**Database connection error?**
- Make sure you added `?sslmode=require` at the end of DATABASE_URL
- Make sure "Allow access from any Azure service" is enabled on the PostgreSQL server

**Emails not sending?**
- Azure doesn't block SMTP like Render, so Gmail should work
- Double-check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in environment variables

## Costs

Everything is covered by your $100 Azure for Students credit:
- PostgreSQL Flexible Server (B1ms): ~$12/month
- App Service (F1 Free): $0
- Total: ~$12/month → lasts 8+ months on student credits
