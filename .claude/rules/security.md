# Security Rules

## API Keys (User-Provided)

**СТРОГОЕ ПРАВИЛО: User API keys НИКОГДА не покидают браузер.**

```
✅ Браузер: AES-GCM 256-bit шифрование → IndexedDB
✅ Key derivation: PBKDF2 от пароля (100K+ итераций)
✅ Мастер-ключ: только в памяти, auto-lock 30 мин
❌ Backend: НИКОГДА не видит расшифрованные ключи
❌ Логи: НИКОГДА не содержат ключи
❌ Network: НИКОГДА не передавать ключи на сервер
```

## VM Sandbox

```
✅ Read-only filesystem (кроме /tmp)
✅ No root access (USER nobody)
✅ Network: whitelist-only через Nginx proxy
✅ mem_limit: 512MB, CPU: 50%, timeout: 1800s
✅ Auto-destroy после завершения задачи
❌ Никогда не монтировать host filesystem
❌ Никогда не давать Docker socket доступ sandbox
```

## API Security

```
✅ Zod validation на всех endpoints
✅ JWT access token: 15 мин TTL
✅ Refresh token: 30 дней, httpOnly cookie
✅ Rate limiting: Redis-based (10 req/min anon, 30 req/min auth)
✅ Login brute force: 5 attempts → 15 min lockout
✅ Max budget cap: $100 (prevent financial abuse)
✅ HTTPS only (TLS 1.3)
❌ Никогда не логировать task descriptions
❌ Никогда не логировать LLM request content
```

## Secrets Management

```
✅ Только через environment variables
✅ .env файлы в .gitignore
✅ .env.example содержит только placeholder values
❌ Никогда в коде, config файлах, или комментариях
❌ Никогда в git history
```
