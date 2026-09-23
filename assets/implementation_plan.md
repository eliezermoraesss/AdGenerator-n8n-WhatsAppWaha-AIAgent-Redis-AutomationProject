# Melhoria da Automação N8N (Agendamento de Links)

Este plano descreve como vamos modificar o seu fluxo atual do n8n para suportar os envios agendados de links (5 por hora, entre 8h e 20h), armazenando-os no PostgreSQL, e obedecendo exatamente à estrutura de loop, delay e agregação solicitada no PDF.

## User Review Required

> [!IMPORTANT]
> - Precisaremos de uma tabela no seu banco de dados PostgreSQL. Por favor, confirme se posso fornecer o script SQL para você rodar no contêiner ou se deseja que o n8n crie a tabela.
> - Suponho que os links serão armazenados com os dados da conversa (`chatId`, `instance`) para sabermos para quem enviar quando o cron rodar. Se o destino dos anúncios for sempre um grupo fixo (em vez de responder a quem mandou a mensagem), me avise!
> - Vou renomear e reorganizar os nós no novo arquivo JSON do n8n, dividindo entre Ingestão (quando a mensagem chega) e Processamento (com o Cron). 

## Proposed Changes

### Banco de Dados (PostgreSQL)

Precisaremos criar a tabela de controle (caso ainda não exista). O comando SQL seria semelhante a este:
```sql
CREATE TABLE IF NOT EXISTS agendamentos (
   id SERIAL PRIMARY KEY,
   url TEXT UNIQUE NOT NULL,
   cupom TEXT,
   desconto TEXT,
   chatId TEXT,
   instance TEXT,
   createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   status VARCHAR(20) DEFAULT 'pending'
);
```

### [N8N Workflow] Atualização de `AdGenerator_EvolutionAPI_v2.json`

Vou refatorar o arquivo `AdGenerator_EvolutionAPI_v2.json` adicionando dois novos ramos e mantendo as lógicas pedidas.

#### 1. Fluxo de Ingestão (Recepção da Mensagem)
- Após mapear os campos da mensagem recém-chegada, adicionarei um nó **If**, validando:
  - **Se a mensagem iniciar com "agendar" (case-insensitive):** 
    - Envia a mensagem a um nó **Code** para extrair as URLs separadas por linha, o cupom e o desconto, criando um Array de links.
    - Conecta cada item num nó do **PostgreSQL** (`Insert` na tabela `agendamentos` com técnica de *Upsert*, caso a URL já exista).
    - Envia uma notificação rápida ao Evolution API: "Links recebidos e agendados para processamento."
  - **Se NÃO iniciar com "agendar":** 
    - Continua rodando o fluxo da mesma forma como faz hoje (avalia URL, roda HTTP Request imediato, formata com AI, envia).

#### 2. Fluxo de Execução Agendada (Disparo via Cron)
Conforme a instrução do PDF:
- Novo nó: **Schedule Trigger**. Configurado para rodar a cada hora aos 0 minutos, mas limitado às horas 8 até 20.
- Consulta **PostgreSQL**: `SELECT * FROM agendamentos WHERE status = 'pending' ORDER BY createdAt ASC LIMIT 5`.
- Nó **If**: Verifica se retornaram resultados.
- Nó **Loop Over Items**: Lote de tamanho 1 (Batch size: 1).
- Dentro do Loop:
  - Nó **HTTP Request (Scraping)** para buscar as informações.
  - Nó **Wait** com atraso de 5 segundos (evitando bloqueio do servidor).
  - Retorno ao **Loop** (porta superior).
- Porta *Done* do Loop:
  - Nó **Aggregate**: Agrupa todos os 5 JSONs coletados em um único array, associados aos dados do DB (chatId, etc.).
  - Nó **Code** (Calcular Desconto para a lista aglomerada).
  - Nó **AI Agent (Processamento Único)**: Envia o Array inteiro com o prompt, instruindo: "Formate cada elemento deste array JSON individualmente e retorne uma lista de dados incluindo os textos prontos e referências das imagens de forma estruturada (JSON array)".
  - Nó **Item Lists (Split Out)**: Separa os retornos do AI Agent em 5 itens separados.
  - Nós **Evolution API** (`Send Image` e `Send Text`): Disparam de forma independente a imagem e a legenda para o `chatId` resgatado do BD.
  - Nó **PostgreSQL** (`Update`): Por último, atualiza o status dos itens disparados no banco de dados para `status = 'sent'`.

## Open Questions

> [!WARNING]
> 1. Para quem o bot deve enviar os anúncios processados no final? Para o mesmo contato que mandou o link (`chatId`), ou existe algum grupo específico para onde os anúncios sempre devem ir?
> 2. Posso recriar inteiramente o arquivo do n8n com as novas credenciais de Postgres, criando nós "vazios" que depois você conecta no seu N8N com a sua credencial real do Postgres?

## Verification Plan

### Teste Manual
- Você importará o arquivo JSON modificado no N8N.
- Configurará a sua Credencial para o Nó do PostgreSQL nas opções do N8N.
- Enviará a palavra "agendar link1 \n link2" no WhatsApp.
- Validaremos se foi salvo no Postgres.
- Testaremos o cron (clicando manualmente em Test) para ver se os nós executam do Scraping até a divisão (Split), aguardando os 5s e retornando o painel de envios.
