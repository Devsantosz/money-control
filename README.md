# Controle financeiro pelo WhatsApp

Um primeiro bot em Python para registrar despesas e salário pelo WhatsApp Business Platform (Cloud API), guardar cada lançamento em SQLite e consultar relatórios por mês, semana e dia.

## Como funciona

1. Você inicia a conversa com o número configurado e manda `oi`.
2. O bot responde com uma saudação escolhida aleatoriamente e mostra os comandos.
3. Você envia `gasto 32,50 almoço` ou `salario 3500`.
4. Os valores ficam no arquivo `financeiro.db`, com data e hora local.
5. `relatorio` mostra o mês atual; `relatorio 2026-11` escolhe outro mês.

O exemplo aceita mensagens de texto. A integração usa a API oficial da Meta. Para um teste local, o servidor precisa estar acessível pela internet através de HTTPS (por exemplo, um túnel de desenvolvimento); para uso contínuo, hospede-o num serviço com HTTPS. Não publique este bot antes de configurar quem pode usá-lo.

## Comandos

| Mensagem | O que faz |
|---|---|
| `oi`, `olá`, `menu` | Mostra a ajuda e uma saudação aleatória |
| `gasto 32,50 almoço` | Registra uma despesa de R$ 32,50 com descrição “almoço” |
| `salario 3500` | Registra uma entrada de R$ 3.500,00 |
| `relatorio` | Resume o mês atual e lista os lançamentos recentes |
| `relatorio 2026-11` | Resume o mês indicado |
| `ajuda` | Mostra os comandos |

Valores podem ser digitados como `32,50`, `32.50` ou `3500`. Para evitar ambiguidades, use sempre duas casas decimais quando houver centavos. Na primeira versão, lançamentos são registrados na data/hora em que a mensagem chega.

## Passo 1 — preparar o ambiente

Instale Python 3.11 ou mais recente. No terminal, dentro desta pasta:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

O `venv` cria um ambiente isolado para este projeto. As bibliotecas instaladas estão em `requirements.txt`.

## Passo 2 — aprender no terminal

Antes de configurar o WhatsApp, execute:

```powershell
python cli.py
```

Experimente `oi`, `gasto 32,50 almoço`, `salario 3500`, `relatorio` e `sair`. O terminal usa o mesmo banco e a mesma lógica que o bot. Os lançamentos de teste ficam separados pelo identificador `teste-local`.

## Passo 3 — configurar a Meta

1. Crie um app no Meta for Developers e adicione o produto WhatsApp.
2. Use o número de teste e os destinatários de teste fornecidos pelo painel.
3. Copie para `.env` o token de acesso, o ID do número de telefone e o ID de verificação do webhook.
4. O exemplo usa `GRAPH_API_VERSION=v27.0`; confirme no painel/documentação da Meta qual versão está disponível para o seu app. A versão fica configurável porque as versões da Graph API mudam.
5. Configure `META_APP_SECRET` com o segredo do app. Ele valida a assinatura dos webhooks.
6. Defina `ALLOWED_PHONE_NUMBERS` com o número de WhatsApp autorizado, no formato internacional só com dígitos, por exemplo `5511999999999`. Não inclua `+`.
7. Exponha seu servidor local em HTTPS por um túnel de desenvolvimento. No painel de Webhooks, informe a URL pública terminada em `/webhook`, use o mesmo `VERIFY_TOKEN` e assine o campo `messages`.
8. Inicie o servidor conforme o Passo 3 e envie `oi` do telefone de teste autorizado.

O token e os segredos são privados: não os envie em mensagens, não os publique e não faça commit do `.env`. A plataforma oficial pode exigir modelos aprovados para conversas iniciadas pelo negócio fora da janela de atendimento. Para este protótipo, comece sempre enviando uma mensagem ao bot.

## Passo 4 — iniciar o servidor

```powershell
python app.py
```

O servidor local abre na porta `8000`. Deixe o terminal ativo enquanto testa. A URL local `/webhook` não é acessível à Meta diretamente; use uma URL HTTPS pública do túnel configurado no passo anterior.

## Entendendo os arquivos

- `app.py`: recebe a confirmação inicial e os eventos enviados pela Meta. Valida a assinatura e encaminha mensagens recebidas.
- `bot.py`: interpreta comandos, escolhe a saudação e monta as respostas.
- `database.py`: cria o SQLite, grava valores em centavos e calcula o relatório mensal.
- `.env.example`: lista as configurações necessárias sem conter credenciais reais.

### O que você está aprendendo

1. **Variáveis de ambiente:** `python-dotenv` carrega credenciais sem colocá-las no código.
2. **HTTP e webhooks:** Flask recebe as mensagens que a Meta envia ao seu endereço HTTPS.
3. **JSON:** o webhook lê os dados da mensagem e a API envia as respostas.
4. **SQLite:** o módulo `sqlite3` já vem com Python; não precisa instalar um servidor de banco.
5. **Datas:** cada lançamento guarda data/hora com fuso `America/Sao_Paulo`; o relatório agrupa por mês, semana ISO e dia.
6. **Centavos inteiros:** R$ 12,34 vira `1234` no banco, evitando pequenos erros de arredondamento de ponto flutuante.

## Próximos passos de aprendizagem

Depois de confirmar que a primeira versão funciona, evolua uma coisa por vez:

1. Adicione categorias explícitas, como `gasto 32,50 alimentação almoço`.
2. Crie `desfazer` para remover o último lançamento do remetente, pedindo confirmação.
3. Exporte um mês para CSV.
4. Adicione metas e limites por categoria.
5. Mova o SQLite para PostgreSQL se houver vários usuários ou hospedagem com armazenamento efêmero.
6. Só então avalie botões interativos, lembretes e modelos de mensagem aprovados.

## Limites desta versão

- O relatório lista até 20 lançamentos mais recentes do mês, além dos resumos por semana e dia.
- O banco é local: em hospedagem, configure armazenamento persistente e backups.
- O campo `ALLOWED_PHONE_NUMBERS` é uma barreira simples de acesso, não um sistema completo de contas.
- A versão não interpreta áudio, imagens, comprovantes ou mensagens em linguagem livre.

## Estrutura dos dados

Cada lançamento tem tipo (`expense` ou `income`), valor em centavos, descrição, instante ISO com fuso e número do remetente. Os registros não são apagados por relatórios e cada mês permanece no mesmo banco.
