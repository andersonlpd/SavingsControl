# SavingControl

Aplicação Django privada para registrar carteira de investimentos, proventos, despesas e snapshots patrimoniais. Implementada conforme `architecture/spec.md`; a planilha em `asset/` não é lida nem importada pelo app.

## Desenvolvimento

Requer Python 3.12+, Node.js e npm.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
npm ci
npm run build
cp .env.example .env
chmod 600 .env
```

Edite `.env` com uma `DJANGO_SECRET_KEY` aleatória (por exemplo, `python -c 'import secrets; print(secrets.token_urlsafe(64))'`). Carregue-a no shell antes dos comandos Django:

```sh
set -a
. ./.env
set +a
python manage.py migrate
python manage.py provision_user investidor
python manage.py runserver
```

O comando de provisionamento pergunta a senha sem exibi-la, cria a única conta e imprime códigos de recuperação uma vez, somente em terminal interativo. Guarde-os fora do computador; no banco, ficam somente hashes. Entre em `/account/login/`, cadastre o TOTP em `/account/two_factor/setup/` e use sempre senha + TOTP ou um código de recuperação.

## Verificações

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
ruff check .
npm run build
```

CI executa testes, lint, checagem de migrações e build dos assets locais. Chart.js é empacotado em `static/vendor/`; a aplicação não carrega bibliotecas de CDN.

## Segurança e operação

- Não há cadastro público. Proteção CSRF, cookies de sessão seguros em produção, redirecionamento HTTPS, TOTP e bloqueio Axes (5 falhas em 15 minutos, bloqueio por 15 minutos) são habilitados.
- Configure segredos fora do repositório, com arquivo de ambiente acessível somente ao usuário do serviço. Use Gunicorn atrás de Caddy/TLS e restrinja o acesso SSH. `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` devem corresponder ao domínio real.
- HSTS vale para o host atual; subdomínios e preload ficam desligados até confirmar HTTPS em todos os hosts envolvidos.
- SQLite fica em `data/db.sqlite3` por padrão. Restrinja permissões do diretório e providencie backup consistente fora da VM antes de inserir dados reais.
- `python manage.py cleanup_login_attempts` apaga registros do Axes com mais de 30 dias; ainda não há timer systemd para agendá-lo.
- `/health/` é um health check local sem dados pessoais.

## Escopo implementado e pendências

O ledger manual de ativos/operações retroativas, custo médio ponderado, proventos, renda fixa cadastral/resgates, cotações manuais, snapshots totais mensais, gastos manuais, categorização local e limites com alertas 80%/100% funcionam localmente. Valores monetários são inteiros em centavos no banco e `Decimal` no domínio.

**Não usar ainda como fonte para decisão financeira ou recuperação de dados:** sincronizações Pluggy/BCB/Tesouro/provedores de preços não estão implementadas; cálculos automáticos de renda fixa, IOF/IR e conversão USD/BRL de despesas também não. Saldos de renda fixa só podem ser informados manualmente e são identificados como tal. Não há jobs systemd, backup remoto, configuração de VM/Caddy nem teste de restauração. A página de integrações deixa esse estado explícito; a aplicação não finge que houve sincronização ou avaliação.

Antes de uso real, concluir essas integrações com credenciais e consentimento válidos, revalidar regras fiscais/fontes oficiais, automatizar e testar backup/restore, configurar HTTPS no host e executar `python manage.py check --deploy` com a chave e domínio de produção.
