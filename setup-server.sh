#!/bin/bash
# Initial server setup script for mavik-ssot.com
# Run this once on a fresh Ubuntu EC2 instance

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Mavik AI Server Setup Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if running as non-root user
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run this script as a non-root user with sudo privileges${NC}"
    exit 1
fi

# Update system
echo -e "${YELLOW}1. Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install Docker
echo -e "${YELLOW}2. Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${YELLOW}3. Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# Install Nginx
echo -e "${YELLOW}4. Installing Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    sudo apt install -y nginx
    echo -e "${GREEN}✓ Nginx installed${NC}"
else
    echo -e "${GREEN}✓ Nginx already installed${NC}"
fi

# Install Certbot
echo -e "${YELLOW}5. Installing Certbot (SSL certificates)...${NC}"
if ! command -v certbot &> /dev/null; then
    sudo apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✓ Certbot installed${NC}"
else
    echo -e "${GREEN}✓ Certbot already installed${NC}"
fi

# Install Git
echo -e "${YELLOW}6. Installing Git...${NC}"
if ! command -v git &> /dev/null; then
    sudo apt install -y git
    echo -e "${GREEN}✓ Git installed${NC}"
else
    echo -e "${GREEN}✓ Git already installed${NC}"
fi

# Install jq (for JSON parsing)
echo -e "${YELLOW}7. Installing utilities...${NC}"
sudo apt install -y jq curl wget htop

# Configure firewall
echo -e "${YELLOW}8. Configuring firewall...${NC}"
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
echo "y" | sudo ufw enable || true
echo -e "${GREEN}✓ Firewall configured${NC}"

# Create application directory
echo -e "${YELLOW}9. Creating application directory...${NC}"
APP_DIR="/home/$USER/chat-assistant"
if [ ! -d "$APP_DIR" ]; then
    mkdir -p $APP_DIR
    echo -e "${GREEN}✓ Directory created: $APP_DIR${NC}"
else
    echo -e "${GREEN}✓ Directory already exists: $APP_DIR${NC}"
fi

# Configure Nginx
echo -e "${YELLOW}10. Configuring Nginx...${NC}"
read -p "Do you want to configure Nginx now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default

    # Copy nginx config (assumes you've cloned the repo)
    if [ -f "$APP_DIR/nginx.conf" ]; then
        sudo cp $APP_DIR/nginx.conf /etc/nginx/sites-available/mavik-ssot
        sudo ln -sf /etc/nginx/sites-available/mavik-ssot /etc/nginx/sites-enabled/

        # Test config
        if sudo nginx -t; then
            echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
        else
            echo -e "${RED}✗ Nginx configuration has errors${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ nginx.conf not found, skipping...${NC}"
    fi
fi

# Setup SSL
echo -e "${YELLOW}11. Setting up SSL certificate...${NC}"
read -p "Do you want to setup SSL with Let's Encrypt now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain (e.g., mavik-ssot.com): " DOMAIN
    read -p "Enter your email for SSL notifications: " EMAIL

    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ SSL certificate installed successfully${NC}"

        # Setup auto-renewal
        (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -
        echo -e "${GREEN}✓ Auto-renewal cron job added${NC}"
    else
        echo -e "${RED}✗ SSL certificate installation failed${NC}"
    fi
fi

# Create systemd service for auto-start
echo -e "${YELLOW}12. Creating systemd service...${NC}"
cat << EOF | sudo tee /etc/systemd/system/mavik-ai.service > /dev/null
[Unit]
Description=Mavik AI Chat Assistant
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mavik-ai.service
echo -e "${GREEN}✓ Systemd service created and enabled${NC}"

# Configure log rotation
echo -e "${YELLOW}13. Setting up log rotation...${NC}"
cat << 'EOF' | sudo tee /etc/logrotate.d/mavik-ai > /dev/null
/var/log/nginx/mavik-ssot-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
EOF
echo -e "${GREEN}✓ Log rotation configured${NC}"

# Display summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   Server setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Log out and log back in for Docker group permissions to take effect"
echo "2. Clone your application repository to $APP_DIR"
echo "3. Create .env file from .env.example and add your credentials"
echo "4. Run: cd $APP_DIR && chmod +x deploy.sh && ./deploy.sh"
echo ""
echo -e "${BLUE}Installed versions:${NC}"
docker --version
docker-compose --version
nginx -v
certbot --version
echo ""
echo -e "${GREEN}Happy deploying! 🚀${NC}"
