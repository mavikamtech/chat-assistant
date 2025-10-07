# Quick Start Guide - Deploying to mavik-ssot.com

## 🚀 Fast Track Deployment (10 minutes)

### Prerequisites
- AWS EC2 instance (Ubuntu 22.04, t3.medium or larger)
- Domain **mavik-ssot.com** pointing to your EC2 IP
- AWS credentials (Access Key, Secret Key)
- Tavily API key (free at https://app.tavily.com/)

---

## Step 1: Initial Server Setup (5 min)

SSH into your EC2 instance:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

Download and run the setup script:
```bash
wget https://raw.githubusercontent.com/your-org/chat-assistant/main/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh
```

**Log out and log back in** for Docker permissions to take effect.

---

## Step 2: Clone Repository (1 min)

```bash
cd /home/ubuntu
git clone <your-repo-url> chat-assistant
cd chat-assistant
```

---

## Step 3: Configure Environment (2 min)

```bash
cp .env.example .env
nano .env
```

Update with your credentials:
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_UPLOADS=mavik-uploads
S3_BUCKET_REPORTS=mavik-reports
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MODEL_ID_HAIKU=us.anthropic.claude-3-5-haiku-20241022-v1:0
TAVILY_API_KEY=tvly-...
NEXT_PUBLIC_BACKEND_URL=https://mavik-ssot.com/api
```

Save (Ctrl+O, Enter) and exit (Ctrl+X).

---

## Step 4: Deploy Application (2 min)

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
- Build Docker images
- Start all services
- Run health checks

---

## Step 5: Verify Deployment

Check if everything is running:
```bash
chmod +x monitor.sh
./monitor.sh
```

Visit your site:
```
https://mavik-ssot.com
```

---

## 🎯 Quick Commands

### View logs
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Restart services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Update application
```bash
git pull origin main
./deploy.sh
```

### Check health
```bash
./monitor.sh
```

### Stop services
```bash
docker-compose -f docker-compose.prod.yml down
```

---

## 🔧 Troubleshooting

### Backend not responding
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

### Check AWS credentials
```bash
docker-compose -f docker-compose.prod.yml exec backend env | grep AWS
```

### Frontend issues
```bash
docker-compose -f docker-compose.prod.yml logs frontend
```

### SSL certificate issues
```bash
sudo certbot certificates
sudo certbot renew
```

### Restart everything
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📊 Health Check Endpoints

- **Frontend**: https://mavik-ssot.com
- **Backend Health**: https://mavik-ssot.com/api/health
- **OpenSearch**: http://localhost:9200/_cluster/health (internal only)

---

## 🔐 Security Checklist

- [ ] SSL certificate installed (HTTPS)
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] AWS credentials in .env (not committed to git)
- [ ] Strong EC2 key pair
- [ ] Regular security updates (`sudo apt update && sudo apt upgrade`)

---

## 📈 Monitoring

Set up a cron job to run health checks:
```bash
crontab -e
```

Add:
```
*/5 * * * * /home/ubuntu/chat-assistant/monitor.sh > /var/log/mavik-ai-monitor.log 2>&1
```

---

## 💰 Cost Estimate

**Monthly AWS Costs (approximate):**
- EC2 t3.medium: ~$30/month
- S3 storage: ~$5/month
- Bedrock (Claude): Pay per use (~$3-4 per 1M tokens)
- Data transfer: ~$5-10/month

**Total**: ~$45-50/month + usage-based Bedrock costs

---

## 🆘 Support

- **Application logs**: `/var/log/nginx/mavik-ssot-*.log`
- **Docker logs**: `docker-compose logs -f`
- **System logs**: `journalctl -u mavik-ai.service`

For issues, check DEPLOYMENT.md for detailed troubleshooting.

---

## 🎉 You're Done!

Your AI assistant should now be live at:
### 🌐 https://mavik-ssot.com

Test it by:
1. Uploading a PDF
2. Asking a question
3. Requesting a pre-screening analysis
