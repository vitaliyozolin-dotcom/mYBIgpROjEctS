#!/bin/bash
set -e

echo "=== Установка CRM ==="

# Docker
if ! command -v docker &> /dev/null; then
    echo "--- Устанавливаю Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "--- Docker уже установлен"
fi

# Репозиторий
echo "--- Скачиваю код CRM..."
apt-get install -y git > /dev/null 2>&1
if [ -d "/opt/crm" ]; then
    cd /opt/crm && git pull
else
    git clone -b claude/explain-capabilities-ZXeTr https://github.com/vitaliyozolin-dotcom/tgbot-for-documents.git /opt/crm
    cd /opt/crm
fi

# .env
if [ ! -f /opt/crm/.env ]; then
    cp /opt/crm/.env.example /opt/crm/.env

    read -p "Токен Telegram-бота (от @BotFather): " TG_TOKEN
    read -p "Ключ Anthropic API: " AI_KEY

    sed -i "s/токен_от_BotFather/$TG_TOKEN/" /opt/crm/.env
    sed -i "s/ваш_ключ_anthropic/$AI_KEY/" /opt/crm/.env

    # Генерируем случайный SECRET_KEY
    SECRET=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 48)
    sed -i "s/замените_на_случайную_строку_минимум_32_символа/$SECRET/" /opt/crm/.env
fi

# Запуск
echo "--- Запускаю CRM..."
cd /opt/crm
docker compose up -d --build

echo ""
echo "=== Готово! ==="
echo "CRM доступна по адресу: http://136.244.96.159:3000"
echo "Логин: admin@crm.local"
echo "Пароль: admin123"
echo ""
echo "ВАЖНО: После первого входа смените пароль администратора!"
