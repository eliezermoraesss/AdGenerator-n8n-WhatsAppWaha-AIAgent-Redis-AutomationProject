# N8N Waha Local - AD Generator Automation

Documentação completa da automação de WhatsApp com n8n, Evolution API e web scraping para geração de anúncios.

---

## 📋 Visão Geral da Arquitetura

Este projeto utiliza Docker Compose para orquestrar uma stack completa de automação que integra:
- **n8n**: Plataforma de automação de workflows
- **Evolution API**: API de integração com WhatsApp
- **Scraper**: Serviço de web scraping (FastAPI + Playwright)
- **PostgreSQL**: Banco de dados para Evolution API
- **Redis**: Cache e fila de mensagens (dois serviços)
- **Waha**: Alternativa WhatsApp (opcional)

**Localização**: `E:\N8N Waha Local`  
**Docker Compose Version**: 5.1.4  
**Project Name**: `n8nwahalocal`

---

## 🐳 Containers e Configurações

### 1. **n8n** (Workflow Automation)

#### Visão Geral
Plataforma de automação de low-code que orquestra todo o fluxo de geração de anúncios, integração com WhatsApp e web scraping.

#### Informações Técnicas
- **Imagem**: `n8nio/n8n:latest`
- **Container Name**: `n8n`
- **Porta**: `5678` (localhost:5678)
- **URL de Acesso**: `https://aerodynamically-bibliomaniacal-mervin.ngrok-free.dev`
- **Versão**: 2.3.5
- **DHI Compliance**: Sim (Docker Hardened Image - Node.js 22 Alpine)

#### Variáveis de Ambiente
```yaml
N8N_HOST: aerodynamically-bibliomaniacal-mervin.ngrok-free.dev
N8N_PROTOCOL: https
N8N_PORT: 5678
N8N_LOG_LEVEL: debug
N8N_SECURE_COOKIE: false
WEBHOOK_URL: https://aerodynamically-bibliomaniacal-mervin.ngrok-free.dev
GENERIC_TIMEZONE: America/Sao_Paulo
N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE: true
```

#### Volumes
- `n8n_data:/home/node/.n8n` - Armazena workflows, credenciais e dados de configuração

#### Dependências
- Depende do serviço **scraper** para iniciar

#### Uso
1. Acesse: `https://aerodynamically-bibliomaniacal-mervin.ngrok-free.dev`
2. Configure seus workflows de geração de anúncios
3. Configure credenciais para Evolution API e outros serviços

#### Logs
```bash
docker compose logs -f n8n
```

---

### 2. **Evolution API** (WhatsApp Integration)

#### Visão Geral
API robusta para integração com WhatsApp, gerenciando instâncias, mensagens, contatos e eventos em tempo real.

#### Informações Técnicas
- **Imagem**: `evoapicloud/evolution-api:latest`
- **Container Name**: `evolution_api`
- **Porta**: `8080` (localhost:8080)
- **Versão**: Latest
- **Banco**: PostgreSQL 15 (host.docker.internal:5436)
- **Cache**: Redis (host.docker.internal:6380)

#### Configurações Principais

##### API Authentication
- **API Key**: `9F2D1B7A6C8E4F2E9A7C0B5D1E3F8A6D`
- **Exposição em Fetch Instances**: Habilitada

##### Webhooks (Habilitados)
- `WEBHOOK_EVENTS_SEND_MESSAGE`: true
- `WEBHOOK_EVENTS_MESSAGES_UPSERT`: true
- `WEBHOOK_EVENTS_MESSAGES_UPDATE`: true
- `WEBHOOK_EVENTS_MESSAGES_DELETE`: true
- `WEBHOOK_EVENTS_CONTACTS_UPSERT`: true
- `WEBHOOK_EVENTS_CONTACTS_SET`: true
- `WEBHOOK_EVENTS_CHATS_UPSERT`: true
- `WEBHOOK_EVENTS_CHATS_UPDATE`: true
- `WEBHOOK_EVENTS_CONNECTION_UPDATE`: true
- `WEBHOOK_EVENTS_QRCODE_UPDATED`: true
- **Timeout de Webhook**: 60000ms
- **Max Tentativas**: 10
- **Delay Inicial**: 5 segundos

##### Pusher Events (Habilitados)
- Eventos em tempo real de mensagens, contatos, chats e conexão

##### Database
```
Provider: PostgreSQL
Host: host.docker.internal:5436
User: user
Password: pass
Database: evolution_db
Client Name: evolution_exchange
Connection URI: postgresql://user:[REDACTED]@host.docker.internal:5436/evolution_db?schema=evolution_api
```

##### Redis Cache
```
Host: host.docker.internal:6380
Database: 6
TTL: 604800 segundos (7 dias)
Prefix: evolution
Salvar Instâncias: false
```

##### Configurações Adicionais
- **Timezone**: America/Sao_Paulo
- **Linguagem**: en (Inglês)
- **Log Level**: ERROR, WARN, DEBUG, INFO, LOG, VERBOSE, DARK, WEBHOOKS, WEBSOCKET
- **QR Code Color**: #175197
- **QR Code Limit**: 30
- **Session Phone**: Chrome
- **Server URL**: http://localhost:8080
- **Server Port**: 8080
- **CORS Origin**: * (Todos os domínios)

##### Features Desabilitadas
- Chatwoot
- Typebot
- OpenAI
- Dify
- RabbitMQ
- S3 Storage
- Sentry
- Websocket Global Events

#### Volumes
- `evolution_instances:/evolution/instances` - Armazena dados das instâncias WhatsApp

#### Dependências
- Postgres Evolution
- Redis Evolution

#### API Endpoints Principais
```
GET  /instances
POST /instances/create
GET  /instances/{instanceName}
DELETE /instances/{instanceName}
POST /message/sendText
POST /message/sendMedia
GET  /chats/{instanceName}
GET  /contacts/{instanceName}
```

#### Logs
```bash
docker compose logs -f evolution-api
```

---

### 3. **PostgreSQL Evolution** (Database)

#### Visão Geral
Banco de dados relacional PostgreSQL versão 15 dedicado aos dados da Evolution API.

#### Informações Técnicas
- **Imagem**: `postgres:15`
- **Container Name**: `postgres_evolution`
- **Porta**: `5436` (localhost:5436 → 5432 interno)
- **Versão**: 15.15

#### Configurações de Conexão
```yaml
POSTGRES_USER: user
POSTGRES_PASSWORD: pass
POSTGRES_DB: evolution_db
POSTGRES_HOST_AUTH_METHOD: trust
```

#### Otimizações
```bash
max_connections=200           # Máximo de conexões simultâneas
listen_addresses=*            # Escuta em todas as interfaces
shared_buffers=256MB          # Buffer compartilhado
effective_cache_size=1GB      # Cache efetivo
work_mem=4MB                  # Memória por operação
```

#### Volumes
- `postgres_evolution_data:/var/lib/postgresql/data` - Dados persistentes

#### String de Conexão
```
postgresql://user:[REDACTED]@host.docker.internal:5436/evolution_db?schema=evolution_api
```

#### Backup
```bash
# Fazer backup
docker exec postgres_evolution pg_dump -U user evolution_db > backup.sql

# Restaurar backup
docker exec -i postgres_evolution psql -U user evolution_db < backup.sql
```

#### Logs
```bash
docker compose logs -f postgres-evolution
```

---

### 4. **Redis Evolution** (Cache - Evolution API)

#### Visão Geral
Cache Redis dedicado aos dados de sessão e cache da Evolution API com persistência AOF.

#### Informações Técnicas
- **Imagem**: `redis:latest`
- **Container Name**: `redis_evolution`
- **Porta**: `6380` (localhost:6380 → 6379 interno)
- **Database**: 6

#### Configurações
```yaml
Command: redis-server --port 6379 --appendonly yes
```

#### Variáveis de Ambiente (Evolution API)
- `CACHE_REDIS_ENABLED`: true
- `CACHE_REDIS_URI`: redis://host.docker.internal:6380/6
- `CACHE_REDIS_PREFIX_KEY`: evolution
- `CACHE_REDIS_TTL`: 604800 (7 dias)

#### Volumes
- `redis_evolution_data:/data` - Dados persistentes com AOF

#### Limpeza de Cache
```bash
# Conectar ao Redis
docker exec -it redis_evolution redis-cli -p 6379

# Dentro do Redis CLI
SELECT 6
FLUSHDB              # Limpar banco atual
KEYS *               # Listar todas as chaves
DEL chave            # Deletar chave específica
```

#### Logs
```bash
docker compose logs -f redis-evolution
```

---

### 5. **Redis (n8n)** (Cache - N8N)

#### Visão Geral
Instância Redis separada para cache e fila de n8n com autenticação.

#### Informações Técnicas
- **Imagem**: `redis:latest`
- **Container Name**: `n8nwahalocal-redis-1`
- **Porta**: `6379` (localhost:6379)
- **Plataforma**: linux/amd64

#### Configurações
```yaml
Command: redis-server --requirepass default
REDIS_USER: default
REDIS_PASSWORD: default
```

#### Uso
- Suporte a workflows paralelos em n8n
- Cache de dados de execução

#### Logs
```bash
docker compose logs -f redis
```

---

### 6. **Scraper** (Web Scraping Service)

#### Visão Geral
Serviço Python FastAPI + Playwright para web scraping de dados para geração de anúncios. Compilado localmente a partir do Dockerfile.

#### Informações Técnicas
- **Imagem**: `n8nwahalocal-scraper` (build local)
- **Container Name**: `scraper`
- **Porta**: `8000` (localhost:8000)
- **Linguagem**: Python
- **Framework**: FastAPI
- **Browser Automation**: Playwright
- **Plataforma Base**: Ubuntu 22.04

#### Variáveis de Ambiente
```yaml
PLAYWRIGHT_BROWSERS_PATH: /ms-playwright
PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LANG: C.UTF-8
LC_ALL: C.UTF-8
```

#### Estrutura de Diretórios (./scraper)
```
scraper/
├── Dockerfile
├── app.py              # Aplicação FastAPI
├── requirements.txt
└── .../
```

#### Endpoints Principais
Documentação disponível em: `http://localhost:8000/docs`

Exemplos:
```bash
# Health check
GET /health

# Scraping endpoint (exemplo)
POST /scrape
{
  "url": "https://exemplo.com",
  "selectors": ["h1", ".price"]
}
```

#### Build Local
```bash
docker compose build scraper

# Rebuild sem cache
docker compose build --no-cache scraper
```

#### Logs
```bash
docker compose logs -f scraper
```

#### Troubleshooting
Se o Playwright falhar ao instalar browsers:
```bash
# Reinstalar browsers
docker compose exec scraper playwright install
```

---

### 7. **Waha** (WhatsApp Alternative - Opcional)

#### Visão Geral
Engine alternativo WhatsApp usando Waha (Web API For WhatsApp). Pode ser usado como alternativa ou complemento à Evolution API.

#### Informações Técnicas
- **Imagem**: `devlikeapro/waha:latest`
- **Porta**: `3000`
- **Plataforma**: linux/amd64

#### Configurações
```yaml
WHATSAPP_HOOK_URL: https://aerodynamically-bibliomaniacal-mervin.ngrok-free.dev:5678/webhook/webhook
WHATSAPP_DEFAULT_ENGINE: GOWS
WHATSAPP_HOOK_EVENTS: message
WAHA_NO_API_KEY: true
WAHA_DASHBOARD_NO_PASSWORD: true
WHATSAPP_SWAGGER_NO_PASSWORD: true
```

#### Volumes
- `waha_sessions:/app/.sessions` - Sessões WhatsApp
- `waha_media:/app/.media` - Mídia armazenada

#### Status
Atualmente definido como comentado (não ativo). Para ativar, remova os comentários do docker-compose.yml

#### Logs
```bash
docker compose logs -f waha
```

---

## 🔌 Networking

### Bridge Network: `evolution_n8n_net`
Conecta os serviços principais para comunicação interna:
- n8n
- evolution-api
- postgres-evolution
- redis-evolution
- scraper

### DNS Interno
Dentro da rede, os serviços podem ser acessados por nome:
- `http://evolution_api:8080`
- `http://scraper:8000`
- `http://n8n:5678`
- `postgresql://postgres_evolution:5432`
- `redis://redis_evolution:6379`

### Host Access
Para acessar do host (Windows):
- `http://localhost:8080` - Evolution API
- `http://localhost:8000` - Scraper
- `http://localhost:5678` - n8n
- `http://localhost:5436` - PostgreSQL
- `http://localhost:6380` - Redis Evolution
- `http://localhost:6379` - Redis n8n

---

## 🚀 Operação

### Iniciar Stack Completa
```bash
cd E:\N8N Waha Local
docker compose up -d
```

### Parar Stack
```bash
docker compose down
```

### Parar e Remover Volumes
```bash
docker compose down -v
```

### Visualizar Logs
```bash
# Todos os serviços
docker compose logs -f

# Serviço específico
docker compose logs -f n8n
docker compose logs -f evolution-api
docker compose logs -f scraper
```

### Rebuild de Imagens
```bash
# Rebuild scraper (local)
docker compose build --no-cache scraper

# Rebuild tudo
docker compose build --no-cache
```

### Executar Comandos
```bash
# PostgreSQL
docker compose exec postgres_evolution psql -U user -d evolution_db

# Redis Evolution
docker compose exec redis_evolution redis-cli -p 6379

# Redis n8n
docker compose exec redis redis-cli

# Scraper
docker compose exec scraper bash
```

---

## 📊 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                         n8n (5678)                              │
│                   Workflow Orchestration                         │
└──────────────┬────────────────────────────────┬──────────────────┘
               │                                │
               v                                v
        ┌─────────────────┐           ┌──────────────────┐
        │  Scraper (8000) │           │ Evolution API    │
        │  Web Scraping   │           │    (8080)        │
        │  + Processing   │           │ WhatsApp Mgmt    │
        └────────┬────────┘           └────────┬─────────┘
                 │                             │
                 │    ┌──────────────────────┬─┴─┐
                 │    │                      │   │
                 v    v                      v   v
        ┌────────────────────┐     ┌──────────────────────┐
        │   Redis n8n        │     │  PostgreSQL Evolution│
        │   Cache/Queue      │     │  Data Storage        │
        │   (6379)           │     │  (5436)              │
        └────────────────────┘     └──────────────────────┘
                                            ^
                                            │
                                   ┌────────┴────────┐
                                   │ Redis Evolution  │
                                   │ Cache (6380)     │
                                   └──────────────────┘
```

---

## 🔐 Segurança

### Senhas e Credenciais (Mudar em Produção)
```yaml
PostgreSQL:
  User: user
  Password: pass

Redis n8n:
  Password: default

Evolution API Key: 9F2D1B7A6C8E4F2E9A7C0B5D1E3F8A6D
```

⚠️ **IMPORTANTE**: Altere todas as senhas padrão em um ambiente de produção!

### Variáveis de Ambiente Sensíveis
Crie um arquivo `.env` na raiz do projeto:
```bash
# .env
POSTGRES_USER=seu_usuario
POSTGRES_PASSWORD=sua_senha_forte
REDIS_PASSWORD=sua_senha_redis
EVOLUTION_API_KEY=sua_chave_api
N8N_SECURE_COOKIE=true
```

### Ngrok (Exposição Segura)
- URL: `https://aerodynamically-bibliomaniacal-mervin.ngrok-free.dev`
- Fornece HTTPS para webhooks
- Substitua com seu próprio tunnel quando necessário

---

## 🐛 Troubleshooting

### Container não inicia
```bash
# Verificar logs
docker compose logs n8n

# Verificar saúde
docker ps -a

# Reinicar container
docker compose restart n8n
```

### Erro de Conexão PostgreSQL
```bash
# Verificar se PostgreSQL está rodando
docker compose ps postgres_evolution

# Testar conexão
docker compose exec postgres_evolution psql -U user -d evolution_db -c "SELECT 1"
```

### Erro de Redis
```bash
# Verificar se Redis está rodando
docker compose ps redis_evolution

# Limpar dados
docker compose exec redis_evolution redis-cli -p 6379 FLUSHDB
```

### Erro no Scraper
```bash
# Reinstalar dependências
docker compose exec scraper pip install -r requirements.txt

# Reinstalar Playwright
docker compose exec scraper playwright install
```

### Erro de Memória (Exit Code 137)
```bash
# Aumentar memória Docker Desktop
# Settings > Resources > Memory (aumente para 4GB+)

# Ou usar comando
docker stats  # Verificar uso
```

---

## 📈 Performance e Monitoramento

### Verificar Uso de Recursos
```bash
docker stats
```

### Verificar Tamanho de Volumes
```bash
docker volume ls
docker volume inspect n8n_data
```

### Limpeza de Recursos Não Utilizados
```bash
# Remover imagens não utilizadas
docker image prune

# Remover containers parados
docker container prune

# Limpeza completa
docker system prune -a
```

---

## 📝 Checklist de Configuração Inicial

- [ ] Alterar senha PostgreSQL
- [ ] Alterar senha Redis
- [ ] Alterar Evolution API Key
- [ ] Configurar Ngrok token/URL pessoal
- [ ] Criar arquivo `.env` com variáveis sensíveis
- [ ] Configurar workflows em n8n
- [ ] Configurar credenciais Evolution API em n8n
- [ ] Testar scraper endpoint
- [ ] Testar webhook Evolution API
- [ ] Configurar backup automático PostgreSQL

---

## 📚 Recursos Úteis

- **n8n Docs**: https://docs.n8n.io
- **Evolution API Docs**: https://evolution-api.com/docs
- **Docker Compose Docs**: https://docs.docker.com/compose
- **PostgreSQL Docs**: https://www.postgresql.org/docs
- **Redis Docs**: https://redis.io/documentation
- **FastAPI Docs**: https://fastapi.tiangolo.com

---

## 🤝 Support e Contribuições

Para issues ou melhorias, consulte:
- Documentação da Evolution API
- Dashboard n8n
- Logs Docker

---

**Última Atualização**: 2026  
**Versão da Documentação**: 1.0
