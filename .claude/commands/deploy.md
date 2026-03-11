# /deploy [env] — Deploy to VPS

## Usage

```
/deploy dev       # локально через docker compose
/deploy staging   # staging VPS
/deploy prod      # production VPS
```

## Process

### Dev Deploy
```bash
docker compose -f docker-compose.dev.yml up -d --build
docker compose exec api npm run db:migrate
curl http://localhost:4000/api/health
```

### Production Deploy
```bash
# 1. Убедись что tests прошли
npm run test

# 2. Собери и запуши образы
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t ghcr.io/youorg/agentflow-web:$IMAGE_TAG apps/web/
docker build -t ghcr.io/youorg/agentflow-api:$IMAGE_TAG apps/api/
docker build -t ghcr.io/youorg/agentflow-agent:$IMAGE_TAG apps/agent/
docker push ghcr.io/youorg/agentflow-{web,api,agent}:$IMAGE_TAG

# 3. Deploy через SSH
ssh deploy@VPS_IP "
  cd /home/deploy/agentflow &&
  git pull &&
  IMAGE_TAG=$IMAGE_TAG docker compose pull &&
  IMAGE_TAG=$IMAGE_TAG docker compose up -d --no-deps web api agent &&
  docker compose exec api npm run db:migrate
"

# 4. Health check
curl https://agentflow.app/api/health

# 5. Проверь мониторинг (Grafana)
echo "✅ Deployed $IMAGE_TAG"
```

### Rollback
```bash
IMAGE_TAG=<previous_sha> docker compose up -d --no-deps api agent web
```

## Pre-deploy Checklist

- [ ] All tests passing (`npm run test`)
- [ ] No OPENAI_API_KEY committed to git
- [ ] .env.production заполнен (STRIPE_*, SMTP_*, JWT_SECRET)
- [ ] DB migrations протестированы на staging
- [ ] Grafana dashboard открыт для мониторинга
- [ ] Slack #prod-alerts канал активен

## Post-deploy Checks

- [ ] `curl https://agentflow.app/api/health` → 200
- [ ] Создать тестовую задачу через UI
- [ ] Проверить WebSocket stream
- [ ] Проверить Stripe webhook (test event)
