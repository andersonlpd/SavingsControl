# Especificação — Controle financeiro e de investimentos

**Status:** proposta escolhida para implementação  
**Data:** 2026-10-08  
**Público:** um usuário, acesso web pessoal  
**Origem de requisitos:** entrevista; o arquivo `asset/Controle de investimentos - AGORAVAI.xlsx` foi inspecionado somente quanto à estrutura, sem ler nem transcrever valores financeiros.

## 1. Visão geral

Aplicação web responsiva para controlar gastos e uma carteira buy-and-hold. O usuário registra manualmente operações de investimento (inclusive retroativas) e proventos. A aplicação calcula posições, rentabilidade estimada, evolução da renda fixa e resumos de despesas. Pluggy pode sincronizar gastos Bradesco e fornecer posições da Ágora para conferência, se os dados forem disponibilizados pelo consentimento. As ordens da Ágora e Vest não entram automaticamente no ledger.

Não é sistema de negociação, consultoria financeira, declaração fiscal ou produto multiusuário. Não há recomendações de investimento nem chat/LLM. “Assistente” significa regras locais de categorização, resumos e limites de gastos.

### Uso e volume

- Um usuário; leitura predominante, com lançamentos manuais e uma sincronização diária.
- Ativos cobertos: ações, FIIs, Tesouro Direto, CDB, LCI e LCA no Brasil; ações e REITs nos EUA.
- Renda fixa internacional está fora de escopo.
- Não há prazo fixo para a primeira versão. O projeto é greenfield; a planilha existente serve como referência e fonte para entrada manual de snapshots históricos, sem migração automática.
- A pasta também contém `.mvn/wrapper`, mas não foi encontrado `pom.xml` nem fonte de aplicação; a stack Django não usa Maven. Não remover o wrapper sem confirmar que é dispensável.

## 2. Requisitos funcionais

Origem **Declarado** significa que o usuário solicitou ou confirmou; **Suposto** marca uma escolha mínima de implementação a validar.

### RF-01 — Login individual

**Origem:** Declarado.  
**Aceite:**
- Um único usuário autorizado; sem cadastro público.
- Login exige senha e TOTP de aplicativo autenticador.
- Recursos de recuperação de TOTP são gerados no provisionamento, exibidos uma vez e armazenados em formato seguro.
- Toda página e endpoint de dados exige sessão autenticada e verificação TOTP.

### RF-02 — Cadastro de ativos e operações

**Origem:** Declarado.  
**Aceite:**
- Permitir cadastrar ativo brasileiro ou norte-americano, tipo/classe, ticker quando aplicável e moeda.
- Permitir lançar compra e venda retroativas para ações, FIIs e REITs com data, quantidade, preço unitário, taxas, moeda e câmbio opcional.
- Para renda fixa, lançar um lote com principal, aplicação, indexador, taxa e vencimento; registrar resgate com valor bruto, principal resgatado, retenção e data.
- Validar campos obrigatórios, valores positivos e venda/resgate não superior à posição disponível. Não suportar venda descoberta, alavancagem ou execução de ordens.
- Atualizar posições a partir do ledger; não migrar operações da planilha automaticamente.

### RF-03 — Posições e gráficos da carteira

**Origem:** Declarado + Suposto.  
**Aceite:**
- Mostrar quantidade, custo registrado, valor de mercado estimado e fonte/data do preço.
- Mostrar visão consolidada em BRL e a parcela internacional em USD.
- Mostrar gráficos de patrimônio total e composição; a série de renda fixa/variável por classe começa na data de início da aplicação.
- Incluir proventos nos relatórios de renda; mostrar separadamente valor de mercado e proventos acumulados para não confundir retorno de preço com retorno total.
- Mostrar resultado acumulado (não anualizado), sem benchmark; exibir capital aplicado, valor atual, ganhos realizados/não realizados e proventos separadamente. Para ativos variáveis, usar custo médio ponderado e explicitar a metodologia na interface.
- Valores com cotação antiga ou manual devem ser identificados visualmente.

### RF-04 — Renda fixa e estimativa líquida

**Origem:** Declarado.  
**Aceite:**
- Cadastrar Tesouro Direto, CDB, LCI e LCA com principal, data de aplicação, vencimento, indexador e taxa.
- Indexadores: percentual do CDI, IPCA+, Selic e prefixado.
- Mostrar principal, saldo bruto estimado, impostos estimados e saldo líquido estimado na data de avaliação. Identificar a hipótese de resgate como estimativa; não substituir cotação oficial de resgate.
- Para Tesouro Direto, usar preços diários oficiais quando houver correspondência inequívoca do título; se não houver, usar o cálculo estimado e marcar a origem.
- Permitir corrigir o saldo por lançamento manual de valor quando a cotação efetiva da instituição divergir.

### RF-05 — Proventos

**Origem:** Declarado.  
**Aceite:**
- Lançar manualmente dividendos, JCP e rendimentos de renda fixa com ativo, data de pagamento, moeda, valor bruto, imposto retido e valor líquido.
- Aceitar datas retroativas para proventos.
- Validar que valor líquido não seja maior que o bruto, salvo correção explícita documentada.
- Proventos podem ser consultados por ativo, tipo, período e moeda.

### RF-06 — Cotações e câmbio

**Origem:** Declarado.  
**Aceite:**
- Atualizar preços pelo menos uma vez ao dia, quando a fonte gratuita cobrir o ticker e sua quota permitir.
- Registrar fonte, horário/data do preço, moeda e se o valor foi informado manualmente.
- Permitir cotação manual quando não houver fonte, ticker ou chamadas disponíveis; mostrar data e aviso de preço manual/desatualizado.
- Usar PTAX diária de venda do Banco Central como referência de conversão USD/BRL, armazenando a data e taxa usada. Operações guardam moeda original e taxa efetiva informada; PTAX da data da operação é fallback.
- Se não houver PTAX na data (fim de semana/feriado), usar a última observação anterior e exibir sua data.

### RF-07 — Histórico patrimonial

**Origem:** Declarado.  
**Aceite:**
- Permitir cadastrar um snapshot mensal do patrimônio total em BRL, com mês de referência e origem “manual/planilha”.
- Usar os snapshots inseridos para desenhar o histórico total anterior ao uso do app.
- Não reconstruir retroativamente histórico por ativo ou por classe. A série por classe começa quando as posições do app tiverem cotações e snapshots.
- A estrutura observada na planilha contém série mensal total, mas não evidência de série mensal separada por renda fixa/variável. Não importar valores automaticamente.

### RF-08 — Gastos, categorias e resumos

**Origem:** Declarado.  
**Aceite:**
- Importar transações Bradesco via Pluggy quando disponíveis e consentidas; aceitar lançamentos manuais para despesas ausentes, dinheiro e categorias corrigidas.
- Normalizar transações e impedir duplicatas usando identificador do provedor e conta.
- Categorizar localmente por regras configuráveis sobre descrição/estabelecimento. Uma transação sem regra fica como “Revisar”. Corrigir uma categoria deve permitir criar/alterar a regra correspondente.
- Mostrar total mensal, distribuição por categoria e maiores categorias/despesas.
- Permitir editar categoria e descrição sem modificar o valor original da transação importada.

### RF-09 — Limites e alertas

**Origem:** Declarado.  
**Aceite:**
- Definir valor máximo por categoria e mês-calendário.
- Exibir alerta dentro do site ao atingir 80% e 100% do limite.
- Gerar no máximo um alerta de cada limiar por categoria e mês; atualizações repetidas/importações não duplicam o alerta.
- Ao corrigir ou remover uma transação, recalcular o mês e o estado do alerta.
- Não enviar WhatsApp, SMS ou e-mail na primeira versão.

### RF-10 — Integrações e conferência

**Origem:** Declarado + Suposto.  
**Aceite:**
- Pluggy é usado para transações de gastos Bradesco e, se suportado no conector pessoal, posições atuais da Ágora somente para conferência.
- O ledger manual é a fonte de verdade da carteira e da rentabilidade; posições da Ágora não criam compras/vendas automaticamente.
- Vest não tem conector Pluggy confirmado nas listas públicas consultadas; operações e proventos ficam manuais.
- Mostrar estado e horário da última sincronização e erro sanitizado, sem revelar token ou dados bancários nos logs.

## 3. Requisitos não funcionais

### RNF-01 — Segurança e privacidade

**Origem:** Declarado + Suposto. A aplicação será exposta à internet e armazenará dados financeiros pessoais.

- HTTPS obrigatório; cookies `Secure`, `HttpOnly` e `SameSite`; proteção CSRF nas alterações.
- Senha + TOTP obrigatórios. Cadastro público desligado. Limitar tentativas de login e proteger sessão.
- Usar `django-axes` para limitar falhas de senha (5 falhas em 15 minutos, bloqueio por 15 minutos) e throttling exponencial do `django-otp` para códigos TOTP inválidos. Reter registros de tentativas por no máximo 30 dias e permitir desbloqueio administrativo pelo host.
- Credenciais Pluggy e chaves de cotações apenas no servidor, fora do repositório e da resposta HTML. Usar arquivo de ambiente com permissões restritas ou mecanismo equivalente do provedor.
- Não enviar gastos/operações a LLM ou serviço de categorização. Não guardar payload bruto da Pluggy além do necessário para normalizar lançamentos.
- Logs não devem conter valores, descrição de transação, CPF, tokens, segredos ou números completos de conta/cartão.
- Banco e backups em armazenamento criptografado pelo provedor; backup em contêiner privado e acesso mínimo.
- Região fora do Brasil é aceitável; selecionar a região pela calculadora e disponibilidade.

### RNF-02 — Desempenho e atualidade

**Origem:** Declarado.

- Meta: p95 ≤ 2 s para telas comuns em uso normal, sem incluir chamadas externas feitas durante a requisição. Sincronização ocorre em tarefa de fundo/agendada.
- Sem atualização intradiária obrigatória nem cotações em tempo real.
- Dados importados e cotações devem exibir a data da última atualização.

### RNF-03 — Confiabilidade e recuperação

**Origem:** Declarado + Suposto.

- Uma única VM é aceitável; não há SLO de alta disponibilidade.
- RPO alvo ≤ 24 horas via backup diário.
- RTO de restauração manual ≤ 24 horas.
- Retenção de 30 backups diários é premissa inicial, a confirmar pelo custo; testar a restauração antes do uso real e periodicamente.

### RNF-04 — Escalabilidade

**Origem:** Declarado. Um usuário e um operador.

- Dimensionar uma única instância Linux; sem escala horizontal, cache distribuído, fila ou múltiplas réplicas na primeira versão.
- Reavaliar SQLite se houver múltiplos usuários, escrita concorrente frequente, disponibilidade contínua ou necessidade de múltiplas instâncias.

### RNF-05 — Observabilidade

**Origem:** Suposto.

- Log de aplicação, falhas de sincronização e health check local; registrar `last_success_at` por fonte.
- Uma tela de status mostra origem, última sincronização e resultado.
- Sem produto externo pago de métricas/tracing; logs estruturados com redação de campos sensíveis.

### RNF-06 — Custo

**Origem:** Declarado.

- Evitar banco gerenciado, Redis, fila, SMS/WhatsApp, LLM e fontes pagas enquanto a alternativa gratuita atender.
- Referência consultada: VM Linux Azure B2s de 2 vCPU/4 GB em Brazil South aparece por cerca de US$ 49,06/mês apenas para computação; disco, backup, tráfego, câmbio e tributos não incluídos. Validar preço real na [calculadora oficial Azure](https://azure.microsoft.com/pricing/calculator/) antes do provisionamento.

## 4. Arquitetura e stack escolhidas

### Arquitetura

**Opção A — monólito modular em uma VM Linux (escolhida).** Django, SQLite local, tarefa diária `systemd`, Caddy e Gunicorn; backup privado fora da VM. Adequada a um usuário e baixa concorrência. Menor quantidade de serviços e custo, mas a VM é ponto único de falha e o crescimento é vertical. Não serve para alta disponibilidade nem múltiplas instâncias sem migração do banco.

**Opção B — monólito em serviços gerenciados (não escolhida).** Aplicação web gerenciada, banco relacional gerenciado e agendador separado. Adequada quando a prioridade é reduzir manutenção do SO/banco, ou quando há vários usuários e necessidade de disponibilidade/escala. Tem mais serviços, configuração e custo; não se justifica para o uso atual. O teto de escala e disponibilidade é maior, condicionado ao plano contratado.

**Por que A:** volume de um usuário, meta de latência modesta, tolerância a restauração em até um dia e preferência por custo baixo. Migrar para PostgreSQL/serviços gerenciados quando aparecer escrita concorrente frequente, vários usuários, necessidade de réplicas ou indisponibilidade intolerável.

### Stack

- **Linguagem:** Python; cálculos em `Decimal`, nunca `float` para dinheiro.
- **Web:** Django, páginas renderizadas no servidor, HTML semântico, CSS responsivo próprio e JavaScript mínimo.
- **Gráficos:** Chart.js, instalado por npm e empacotado como asset local servido pelo Django. Nenhum CDN nem serviço Node em produção; não adicionar uma SPA.
- **Banco:** SQLite em disco persistente na VM. Modelo relacional para ledger, ativos, proventos, transações, orçamentos e snapshots. Migrações Django.
- **API:** REST JSON apenas para dados dos gráficos e ações internas necessárias; páginas são server-rendered. Sem GraphQL.
- **Autenticação:** sessões Django e `django-two-factor-auth` para senha + TOTP, com cadastro desligado e códigos de recuperação. `django-axes` para limitar tentativas de login. Verificar versões compatíveis e suportadas no início da implementação; não fixar versões neste documento.
- **Servidor:** Gunicorn atrás de Caddy (TLS e proxy reverso); serviços administrados pelo `systemd`.
- **Sincronização:** management commands Django agendados por `systemd timer`; sem fila/cache.
- **Fontes externas:** Pluggy personal API; BCB PTAX/SGS; Tesouro Transparente; provedor gratuito de preços brasileiros e norte-americanos a validar por ticker.
- **Observabilidade:** logging Django/systemd sanitizado, health check e estado de sincronização na UI.
- **CI/CD:** repositório privado GitHub como premissa; GitHub Actions executa testes Django, lint, build dos assets locais e checagem de migrações. Implantação automatizada via ambiente protegido e acesso restrito à VM. Se o código for hospedado em outro lugar, manter os mesmos checks.

### Alternativa de stack não escolhida

**TypeScript + Next.js + React + SQLite/PostgreSQL.** Compartilha linguagem entre servidor e browser e facilita SPA altamente interativa. Foi preterida porque o objetivo não exige SPA; autenticação TOTP, tarefas de fundo e precisão monetária exigiriam mais componentes. Não há benchmark comparativo assumido; ambas suportariam a carga de um usuário.

**Ecossistema e contratação:** Python/Django e TypeScript/Next.js têm ecossistemas web maduros. Não foi feita pesquisa de contratação local; como a aplicação será mantida por uma pessoa e não há equipe a contratar, disponibilidade regional não decide a escolha. Nenhum benchmark de desempenho entre stacks foi presumido.

## 5. Componentes, responsabilidades e interfaces

Todos os componentes residem no mesmo projeto Django; não são serviços independentes.

| Módulo | Responsabilidade | Interface |
|---|---|---|
| `accounts` | Login, sessão, TOTP, códigos de recuperação | Páginas de autenticação; sem cadastro público |
| `portfolio` | Ativos, operações retroativas, contratos de renda fixa, proventos e snapshots | Formulários protegidos por sessão/CSRF |
| `valuation` | Posição, preços, câmbio, indexadores, estimativas bruta/líquida | Serviço Python interno; JSON de gráficos |
| `expenses` | Gastos importados/manuais, categorias, regras locais, orçamento e alertas | Formulários + resumos JSON internos |
| `integrations` | Cliente Pluggy e clientes de cotações/índices; deduplicação e estado de sync | Management commands diários; configurações do servidor |
| `reports` | Dashboard, tabelas e gráficos | HTML server-rendered e `/api/reports/*` autenticado |
| `systemd` | Agendamento diário e inicialização de serviços | Commands: `sync_pluggy`, `refresh_market_data`, `create_daily_snapshot`, `backup_sqlite` |

### Rotas do app

Todos os endpoints de dados exigem usuário autenticado e TOTP verificado. POSTs usam CSRF; valores monetários são strings decimais na API JSON.

O navegador não calcula rentabilidade/impostos: recebe resultados do servidor. Para desenhar Chart.js, pode converter um valor para `Number` apenas como coordenada visual; tooltip e rótulo exibem o valor decimal exato fornecido pelo servidor.

| Método e rota | Contrato/responsabilidade |
|---|---|
| `GET /dashboard/` | Patrimônio, composição, limites e avisos de atualização |
| `GET /portfolio/` | Posições e filtro por classe/mercado |
| `GET, POST /portfolio/assets/` | Consultar/criar ativo; ticker opcional para renda fixa |
| `GET, POST /portfolio/operations/` | Consultar/criar compra ou venda de ativo variável; data, ativo, quantidade, preço, taxas, moeda e câmbio opcional |
| `GET, POST /portfolio/fixed-income/` | Criar/editar lote de renda fixa com principal, indexador, taxa, aplicação e vencimento |
| `POST /portfolio/fixed-income/{id}/redemptions/` | Registrar resgate: data, valor bruto, principal resgatado, retenção, taxas e líquido |
| `GET, POST /portfolio/income/` | Lançar dividendos, JCP ou rendimentos; bruto, retenção, líquido, moeda e data |
| `GET, POST /portfolio/snapshots/` | Inserir snapshot mensal do total histórico em BRL |
| `GET /api/reports/portfolio?from=YYYY-MM&to=YYYY-MM` | Série total, renda fixa, variável e composição; valores em BRL, com USD separado |
| `GET /expenses/` | Transações, filtros, categorias e resumo mensal |
| `GET, POST /expenses/manual/` | Registrar gasto manual |
| `GET, POST /expenses/categories/` | Administrar categorias e regras de descrição/estabelecimento |
| `GET, POST /expenses/budgets/` | Definir limite por categoria e mês-calendário |
| `GET /settings/integrations/` | Mostrar estado e horário de sync; nunca exibir segredo |

Não há endpoint público de ingestão de webhook na primeira versão. Sync é pull agendado do servidor; não executar chamadas de provedor na thread de renderização de página.

### Pluggy

- Uso pessoal via Meu Pluggy, com consentimento concedido pelo usuário no fluxo do provedor. O app não coleta senha bancária.
- Segredos `clientId`, `clientSecret` e `apiKey`, e `itemId` configurado, ficam somente no servidor em configuração protegida (placeholders no repositório: `TROCAR_POR_PLUGGY_CLIENT_ID`, `TROCAR_POR_PLUGGY_CLIENT_SECRET`, `TROCAR_POR_PLUGGY_ITEM_IDS`).
- Autenticação conforme documentação Pluggy: `POST /auth`; obter contas por `GET /accounts?itemId=...`; transações via endpoint atual `GET /v2/transactions?accountId=...`, percorrendo cursor `next`. Não usar `GET /transactions` paginado por página: a documentação marca esse endpoint como depreciado.
- Para conferência da Ágora, consultar `GET /investments?itemId=...` e guardar apenas o retrato recebido para comparação; não converter esses registros em operações do ledger.
- Manter apenas campos necessários (ID externo, conta referenciada, data, descrição necessária para categorização, tipo, valor, moeda e status). Não guardar payload bruto completo.
- Unicidade por provedor + ID externo + conta. Reprocessar a mesma página não duplica nem altera lançamento manual.
- Categorias da Pluggy não são usadas: o recurso é trial/premium. Categorizar localmente.
- A atualização pessoal da Pluggy é diária e a documentação indica limite de cinco conexões e até 12 meses de transações; conferir condições atuais antes de ativar. Disponibilidade exata dos cartões Bradesco deve ser testada por consentimento/produto.
- Posições da Ágora são leitura somente para conferência; divergências são exibidas, não convertidas em operações automaticamente. Confirmar produtos e campos retornados para o consentimento específico.

### Cotações, índices e estimativas

- **BR ações/FIIs:** brapi é candidato para cotação básica; plano gratuito tem limites de uso/histórico e atraso. Verificar licença/limites vigentes antes de ativar.
- **Ações/REITs EUA:** Alpha Vantage é candidato a dados diários; plano gratuito publicado limita chamadas e histórico. Validar ticker e quota antes de depender dele. Se indisponível, armazenar último preço e aceitar atualização manual.
- **Tesouro Direto:** usar arquivo/dataset diário oficial do Tesouro Transparente quando o título puder ser identificado sem ambiguidade.
- **USD/BRL:** PTAX diária do BCB (cotação de venda para avaliação); não representa taxa de execução da Vest.
- **CDI, Selic e IPCA:** API pública BCB SGS, séries 12 (CDI diário, percentual ao dia), 11 (Selic efetiva diária) e 433 (IPCA mensal, percentual). Persistir série, data e valor retornado.
- Não supor cotação/reconstrução diária histórica gratuita de todos os ativos. As séries históricas antigas totais são snapshots digitados da planilha; cotações do app passam a compor histórico a partir da implantação.

### Interface/UX

- Dashboard inicial: total do patrimônio, variação no período, divisão RF/RV, últimos proventos, maiores categorias de gasto, limites e datas das cotações/sync.
- Ações rápidas: “Lançar operação”, “Lançar provento”, “Lançar gasto” e “Adicionar snapshot histórico”.
- Formulários suportam data retroativa, autocomplete de ativo, validação junto ao campo e preservação do rascunho em erro.
- Tabelas filtráveis por período, classe, ativo, categoria e moeda; layout responsivo para celular sem exigir app nativo.
- Categorias e orçamento no calendário mensal. Alertas são discretos no site, sem WhatsApp.

## 6. Modelo de dados

Armazenamento SQL SQLite. Para não depender da aritmética `REAL` do SQLite, persistir valores monetários como inteiros em centavos (`amount_minor`), quantidade em milionésimos (`*_u6`) e preço/taxa/câmbio em escala decimal fixa de 8 casas (`*_e8`). Converter para `Decimal` no domínio; arredondar dinheiro apenas na fronteira apropriada, com regra explícita. JSON serializa valores decimais como strings. Não usar `float` para cálculos de dinheiro.

### `Asset`

- `id`; `name`; `market` (`BR`, `US`); `ticker` nullable; `asset_class` (`FIXED_INCOME`, `VARIABLE_INCOME`); `subtype` (`STOCK`, `FII`, `REIT`, `TREASURY`, `CDB`, `LCI`, `LCA`); `currency` (`BRL`, `USD`); `active`; `quote_source` nullable.
- Unicidade de ticker por mercado quando ticker existe. Título de renda fixa sem ticker tem nome/identificador manual.

### `InvestmentOperation`

- `id`; `asset_id` FK; `side` (`BUY`, `SELL`); `trade_date`; `quantity_u6`; `unit_price_e8`; `fees_minor`; `taxes_minor`; `currency`; `fx_to_brl_e8` nullable; `created_at`; `updated_at`; `note` opcional. Usado para ativos variáveis.
- Quantidade positiva; venda validada contra saldo cronológico. Operações retroativas recalculam saldo e snapshots posteriores.

### `FixedIncomeContract`

- `asset_id` FK; `principal_minor`; `application_date`; `maturity_date`; `indexer` (`CDI_PERCENT`, `IPCA_PLUS`, `SELIC`, `FIXED`); `contract_rate_e8` como razão decimal (ex.: 105% CDI = `1.05`; 12% a.a. = `0.12`); `rate_unit`; `liquidity_date` opcional; `tax_regime` configurável.
- Um ativo pode ter vários lotes/contratos para datas, taxas e vencimentos diferentes.

### `FixedIncomeRedemption`

- `id`; `contract_id` FK; `date`; `gross_amount_minor`; `principal_redeemed_minor`; `withheld_tax_minor`; `fees_minor`; `net_amount_minor`; `currency`.
- Resgates parciais exigem o principal resgatado informado; resgate total fecha o lote. Amortizações automáticas não são inferidas.

### `FixedIncomeValuationOverride`

- `id`; `contract_id` FK; `observed_at`; `gross_amount_minor`; `source` (`BROKER_MANUAL`).
- A última correção substitui o valor bruto calculado para aquele lote na data indicada; o app mantém a estimativa tributária e exibe que o saldo bruto foi informado manualmente.

### `IncomeEvent`

- `id`; `asset_id` FK; `kind` (`DIVIDEND`, `JCP`, `FIXED_INCOME`); `payment_date`; `gross_amount_minor`; `withheld_tax_minor`; `net_amount_minor`; `currency`; `fx_to_brl_e8` opcional; `note`.

### `ExternalPositionSnapshot`

- `provider`; `external_asset_id`; `asset_id` nullable; `observed_at`; `quantity_u6` nullable; `reported_value_minor`; `currency`; `match_status` (`MATCHED`, `UNMATCHED`).
- Guardar apenas a posição mais recente por provedor/ativo externo para conferência da Ágora. Nunca gerar uma operação manual a partir desse snapshot.

### `MarketQuote` e `ExchangeRate`

- `MarketQuote`: `asset_id`; `observed_at`; `price_e8`; `currency`; `source`; `manual`; unicidade por ativo/data/fonte apropriada.
- `ExchangeRate`: `date`; `base` (`USD`); `quote` (`BRL`); `rate_e8`; `source` (`BCB_PTAX`); `observed_at`.
- Cotação manual substitui a avaliação corrente para a data informada, sem apagar a cotação original da fonte; guardar trilha mínima de alteração.

### `PortfolioSnapshot`

- `snapshot_date`; `scope` (`TOTAL`, `FIXED_INCOME`, `VARIABLE_INCOME`); `value_minor_brl`; `source` (`MANUAL_SHEET`, `APP`); `created_at`.
- Restrição única por `snapshot_date` + `scope`. Snapshots antigos manuais usam `scope=TOTAL` e data de fim de mês; snapshots do app podem registrar total e classe por dia.
- `MANUAL_SHEET` para os totais mensais antigos. Snapshot de classe/ativo não pode ser fabricado no passado; períodos anteriores ao app mostram apenas total geral.
- Após implantação, guardar ao menos snapshots diários para que os gráficos futuros continuem corretos mesmo quando a fonte gratuita não tiver histórico antigo.

### `ExpenseTransaction`, `Category`, `CategoryRule`, `Budget`, `BudgetAlert`

- `ExpenseTransaction`: `id`; `source` (`PLUGGY`, `MANUAL`); `external_id` nullable; `account_ref` mascarado/local; `transaction_date`; `description`; `amount_minor`; `currency`; `direction`; `status` (`POSTED`, `PENDING`, `UNKNOWN`); `category_id`; `category_source`; `created_at`.
- Transação pendente fica visível como provisória; somente `POSTED` entra nos totais e limites. A mudança de status do mesmo ID externo atualiza o registro existente.
- `direction` normaliza `DEBIT` como gasto e `CREDIT`/estorno como crédito; relatórios mensais usam a data da transação e somam créditos/estornos como redução do gasto da categoria quando aplicável.
- Restrição única `(source, account_ref, external_id)` para transação externa; `external_id` é nulo para manual.
- `Category`: nome, estado ativo e grupo opcional.
- `CategoryRule`: padrão normalizado/estabelecimento e categoria. Regras explicitamente criadas/editadas pelo usuário; precedência determinística e teste de correspondência exata normalizada.
- `Budget`: categoria, mês `YYYY-MM`, `limit_minor_brl`.
- `BudgetAlert`: orçamento, limiar `80` ou `100`, criado em; chave única orçamento+mês+limiar.

### `SyncRun`

- `source`; `started_at`; `finished_at`; `status`; `records_seen`; `records_created`; `safe_error_code`; `last_success_at`.
- Não incluir token, descrição de transação, CPF ou valor financeiro no erro/log.

## 7. Fluxos principais

### Lançar operação retroativa

1. Usuário autenticado abre “Lançar operação”.
2. Para ativo variável, escolhe compra/venda, data, quantidade, preço, taxas/impostos, moeda e câmbio se souber. Para renda fixa, cria lote ou resgate com principal, taxa/indexador, data e vencimento.
3. Django valida data, ativo, valores e saldo disponível para venda.
4. Salva operação no ledger; recalcula a posição em ordem cronológica e invalida/regera snapshots posteriores.
5. Dashboard atualiza posição e gráfico; preço usado exibe fonte/data. Nenhuma ordem é enviada à corretora.

### Avaliar carteira

1. Job diário salva cotações disponíveis, PTAX e índices, cada registro com fonte e observação.
2. Avaliador calcula quantidade × preço para ativos variáveis; converte USD por PTAX da data de avaliação.
3. Para renda fixa, aplica o indexador/taxa ao lote desde a aplicação; usa preço oficial para Tesouro Direto quando há correspondência inequívoca.
4. Calcula bruto e estimativa líquida de resgate na data de avaliação; mostra base, data e premissa tributária.
5. Grava snapshot diário; se a fonte falhar, mantém o último preço e marca “desatualizado”, sem fingir atualização.

Para ativos variáveis, custo médio ponderado atualiza com cada compra; uma venda realiza resultado igual ao valor líquido recebido menos a parcela correspondente do custo médio. Resultado não realizado é valor de mercado menos custo da posição aberta. Proventos líquidos aparecem à parte e entram no resultado acumulado do ativo, não no preço. A porcentagem é não anualizada; quando a base de custo for zero, exibir valor em moeda sem percentual.

### Estimativa de imposto de renda fixa

- Base: rendimento bruto positivo por lote na data de avaliação.
- Para CDB/Tesouro sujeitos à tabela regressiva, iniciar com a regra publicada pela Receita Federal para 2026: 22,5% até 180 dias; 20% de 181–360; 17,5% de 361–720; 15% acima de 720. Usar tabela versionada/configurável por vigência, revisar fonte oficial antes de release e não codificar o valor em vários lugares.
- Aplicar IOF regressivo somente quando aplicável a resgate antes de 30 dias, segundo tabela oficial vigente; limitar ao rendimento conforme regra legal.
- LCI/LCA devem usar regime isento de IR de pessoa física conforme a regra vigente validada na data de implantação. A classificação fiscal deve ser campo explícito/configurável; não inferir para todo produto futuro.
- Líquido estimado = saldo bruto − IR estimado − IOF estimado − taxas informadas. Não incluir taxas desconhecidas.
- Indicar “estimativa; confirme na instituição” e não gerar apuração fiscal ou DARF.

### Convenções de cálculo de renda fixa

- CDI (%): para cada observação diária SGS 12, aplicar `1 + (CDI_diário_percentual / 100) × multiplicador_contratual`; multiplicar os fatores desde a aplicação. Exemplo de entrada de 105% do CDI: multiplicador `1.05`.
- Selic: usar observações efetivas diárias SGS 11 e o multiplicador contratual, convertendo percentuais publicados em decimais antes da multiplicação.
- `dias_úteis` é a quantidade de observações da série diária CDI (SGS 12) entre as datas; não estimar feriados ou dias faltantes.
- Prefixado: fator acumulado `((1 + taxa_anual) ** (dias_úteis/252))`; taxa anual é armazenada como razão decimal (ex.: 12% = `0.12`).
- IPCA+: fator estimado `produto(1 + IPCA_mensal/100) × ((1 + spread_anual) ** (dias_úteis/252))`, usando somente IPCA publicado e spread anual como razão decimal. Avançar o spread até a data de avaliação e exibir o mês mais recente do IPCA; é aproximação, não preço de resgate/mercado.
- Para Tesouro Direto, preferir PU oficial diário. Se não houver correspondência, usar a estimativa contratual e identificá-la.
- Se uma série diária estiver indisponível, não inventar fator para o dia: avaliar até a última observação válida e indicar defasagem. IPCA é mensal e sua data de divulgação deve ser exibida separadamente da data de avaliação.

### Importar gastos e alertar orçamento

1. `systemd timer` executa `sync_pluggy` uma vez ao dia.
2. O comando autentica no backend Pluggy, percorre contas configuradas e busca transações usando cursor `GET /v2/transactions`. Para a Ágora, pode buscar posições por `GET /investments?itemId=...` para conferência.
3. Cada transação é normalizada e inserida/upsert por ID externo; duplicata não cria novo gasto nem sobrescreve categoria manual.
4. Regra local seleciona categoria; sem correspondência, fica “Revisar”. Correção manual pode criar regra para futuras transações.
5. Calcula total do mês-calendário por categoria. Ao cruzar 80%/100%, cria um alerta único.
6. Dashboard mostra data da atualização e eventuais falhas. Usuário pode cadastrar manualmente gastos que não foram fornecidos pelo provedor.

### Histórico patrimonial

1. Usuário digita mês e total mensal em BRL copiado da planilha, um registro por mês.
2. O app valida unicidade de mês e apresenta a série histórica geral.
3. Desde a implantação, snapshots e operações sustentam gráficos de total e classe. Não tentar reconstruir classes passadas com dados de preço que não foram guardados.

## 8. Deploy e ambiente

- Alvo inicial: uma VM Linux no Azure, escolhendo região elegível de menor custo após consulta à calculadora; usuário não exige residência no Brasil. Manter portabilidade para uma VPS equivalente sem alterar o monólito.
- DNS do domínio `.br` aponta para IP público; Caddy termina TLS e encaminha para Gunicorn/Django. Forçar HTTPS.
- Manter relógio do host sincronizado por NTP/systemd-timesyncd; TOTP depende de relógio correto.
- Entrada pública somente 80/443. SSH com chave, acesso administrativo restrito por IP quando possível; nenhuma porta SQLite/DB exposta.
- `systemd` mantém Gunicorn e agenda sincronizações/backups. Persistir SQLite em diretório de dados, não no diretório descartável de release. Backup usa a API de backup do SQLite para criar snapshot consistente antes do upload; não copiar o arquivo ativo enquanto há escrita.
- Backup diário consistente do SQLite para contêiner Blob privado, separado da VM; retenção inicial 30 dias. Testar procedimento de restauração, incluindo migrações compatíveis.
- Segredos são configurados fora do repositório com permissões restritas. Placeholders de documentação: `TROCAR_POR_PLUGGY_CLIENT_ID`, `TROCAR_POR_PLUGGY_CLIENT_SECRET`, `TROCAR_POR_QUOTE_API_KEY`; não incluir valores reais.
- CI: Django tests, verificação de estilo e checagem de migrações em GitHub Actions. Implantação só após checks; processo de rollback é voltar ao release anterior e restaurar backup se uma migração afetar dados.
- Primeiro acesso: comando de provisionamento cria o único usuário e códigos TOTP de recuperação; não criar endpoint de cadastro público.

## 9. Fontes e limitações

- Pluggy personal use: https://docs.pluggy.ai/pt/docs/guides/meu-pluggy-personal-use
- Pluggy coverage Open Finance: https://docs.pluggy.ai/pt/docs/open-finance/institutions-coverage
- Pluggy pagination cursor (usar `/v2/transactions`): https://docs.pluggy.ai/pt/reference/transaction/transactions-list-by-cursor
- Pluggy investments list (positions by item): https://docs.pluggy.ai/pt/reference/investment/investments-list
- Pluggy categorization (trial/premium): https://docs.pluggy.ai/en/docs/products/transaction-categorization
- PTAX BCB: https://dadosabertos.bcb.gov.br/dataset/dolar-americano-usd-todos-os-boletins-diarios
- BCB SGS API: https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic ; CDI série 12: https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json ; IPCA série 433: https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json
- Tesouro Transparente: https://www.tesourotransparente.gov.br/temas/divida-publica-federal/tesouro-direto
- Receita Federal — tributação de 2026: https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026 ; rendimentos isentos: https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/preenchimento/manual-mir/rendimentos/rendimentos-do-capital
- Decreto nº 6.306/2007 (IOF, texto vigente): https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2007/decreto/d6306.htm
- brapi: https://brapi.dev/docs/acoes/cotacao.mdx ; Alpha Vantage: https://www.alphavantage.co/documentation/ . Revalidar limite, licença, atraso e cobertura ticker por ticker.
- Azure price estimate (third-party, nonbinding): https://www.azurespeed.com/AzureVmPricing/Regions/brazilsouth ; official calculator: https://azure.microsoft.com/pricing/calculator/
- Django TOTP integration: https://django-two-factor-auth.readthedocs.io/en/stable/ ; Django security deployment checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- Django login-attempt limits: https://django-axes.readthedocs.io/en/stable/
- Django OTP TOTP throttling: https://django-otp-official.readthedocs.io/en/stable/overview.html

## 10. Fora de escopo

- Compra/venda automática, conexão para execução de ordens, recomendações de ativos ou estratégia.
- Chatbot, LLM, treinamento de modelo financeiro ou envio de transações para categorização remota.
- Importar a planilha inteira, importar histórico de compras automaticamente ou reconstruir histórico por ativo anterior à implantação.
- Renda fixa internacional, ativos além das classes listadas, cripto, opções, margem, short selling, imóveis físicos ou contas de múltiplos usuários.
- Integração da Vest, e-mail/WhatsApp/SMS, app nativo e notificações fora do site.
- Apuração fiscal oficial, declaração de IR, DARF, lucro tributável de renda variável no exterior ou substituição do informe da corretora.
- Garantia de cotação em tempo real, disponibilidade de provedor público ou preço de liquidação efetivo para CDB/LCI/LCA.

## 11. Premissas e validações pendentes

1. Testar consentimento Pluggy para Bradesco e confirmar que os lançamentos dos cartões são expostos no conector pessoal. Se não forem, gastos continuam manuais.
2. Testar se a conexão pessoal gratuita expõe posições da Ágora no produto/tipo de conta real. Se não, Ágora também será manual; não importar operações sem confirmação.
3. Confirmar cobertura e limites de cada ticker brasileiro e norte-americano com o plano gratuito do provedor; aplicar fallback manual quando faltar.
4. Revalidar regras de impostos/indexadores oficiais na implementação e manter sua data de vigência. Cálculos são demonstrativos, não aconselhamento tributário.
5. Confirmar preço total por região, disco e backup na calculadora Azure antes da criação da VM. A cifra de US$ 49,06 não inclui esses itens e refere-se à computação B2s em Brazil South.
6. Confirmar retenção de backup de 30 dias; o requisito declarado é backup diário e recuperação em até um dia.
7. A pasta não possui metadados Git; GitHub Actions pressupõe criar um repositório privado, ou trocar pelo CI disponível quando o repositório for escolhido.

## 12. Validação da implementação

- Testes unitários de soma de compras/vendas retroativas, validação de saldo, custos e conversão USD/BRL usando `Decimal`.
- Casos de renda fixa para cada indexador, mudança de faixa de IR, IOF antes/depois do prazo, LCI/LCA isenta conforme regra vigente e arredondamento explícito.
- Reprocessar a mesma resposta Pluggy duas vezes e provar que há uma única transação; corrigir categoria manual e provar que o sync não a sobrescreve.
- Testar alertas em 80% e 100%, uma vez por categoria/mês/limiar, após inclusão e correção de gasto.
- Testar preços manuais/desatualizados, cotações faltantes e série total histórica manual; gráficos por classe não devem inventar dados antes da implantação.
- Teste de acesso: usuário anônimo não lê dados; usuário precisa completar TOTP; rate limit funciona; valores sensíveis não aparecem nos logs.
- Smoke test em celular e desktop, formulários com teclado, foco visível, rótulos de gráfico e mensagens de erro junto aos campos.
- Executar restore de um backup diário em ambiente isolado e conferir acesso à carteira e aos gastos restaurados.
