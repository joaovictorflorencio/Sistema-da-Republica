# Contexto do Projeto para usar no ChatGPT

Use este arquivo como base quando quiser pedir ajuda ao ChatGPT para criar documentacao, apresentacao, relatorio, trabalho academico ou texto tecnico sobre o sistema.

Se quiser, voce pode copiar este arquivo inteiro e colar na conversa antes de fazer o pedido.

---

## 1. Nome do projeto

**RABBU - Sistema de Gestao de Republicas**

---

## 2. Objetivo do sistema

O sistema foi criado para ajudar no dia a dia de moradias compartilhadas, como republicas estudantis.

O foco principal e:
- organizar despesas da casa
- acompanhar quem pagou cada conta
- dividir gastos entre moradores
- organizar tarefas domesticas
- mostrar uma visao geral da rotina da republica

---

## 3. Contexto academico

Este projeto foi feito para faculdade.

Por isso:
- ele precisa ser funcional, claro e explicavel
- nao precisa escalar como produto real de mercado
- a solucao deve ser coerente com o nivel esperado da disciplina
- simplicidade e clareza sao mais importantes do que complexidade excessiva

---

## 4. Tecnologias usadas

- Python
- Django
- Django REST Framework
- SQLite
- HTML
- CSS
- JavaScript

---

## 5. Estrutura geral do sistema

O projeto possui:
- backend em Django
- API REST com Django REST Framework
- frontend web simples servido pelo Django
- autenticacao por token
- banco SQLite

---

## 6. Funcionalidades principais

As funcionalidades principais atualmente sao:

### Autenticacao
- cadastro de usuario
- login
- logout
- leitura do usuario autenticado

### Republica
- criar nova republica
- entrar em republica existente
- o primeiro usuario que cria a republica vira admin da republica

### Moradores
- cadastrar moradores
- vincular moradores a uma republica
- diferenciar admin da republica de morador comum

### Dashboard
- mostrar resumo da casa
- mostrar numero de moradores
- mostrar despesas recentes
- mostrar tarefas pendentes

### Financas
- cadastrar despesas da casa
- definir quem pagou a conta
- dividir automaticamente o valor entre moradores selecionados
- controlar despesas pendentes e pagas
- anexar comprovante quando a conta for paga

### Tarefas
- criar tarefas
- alterar status
- concluir tarefas
- mostrar historico de tarefas concluidas

---

## 7. Como a parte financeira deve ser entendida

### Visao conceitual usada para apresentar o sistema

Hoje a area de financas deve ser explicada mais como um **controle de gastos da republica** do que como um sistema bancario.

Ou seja:
- uma conta e cadastrada
- o sistema registra quem pagou
- o valor e dividido entre moradores
- a conta fica marcada como pendente ou paga
- quando paga, pode receber um comprovante

### O que nao deve ser prometido

Evitar dizer que o sistema:
- gera boleto real
- faz integracao bancaria
- processa pagamento real
- faz PIX real

O correto e dizer:
- controle de gastos
- controle de despesas
- anexo de comprovante
- acompanhamento de status da conta

### Resumo da logica financeira

- `Despesa`: representa uma conta da casa
- `DivisaoDespesa`: representa quanto cada morador participa daquela conta
- a divisao e automatica
- a tela mostra contas pendentes e pagas
- quando a conta e paga, pode ser anexado um comprovante

### Importante

Mesmo que o backend ainda tenha estruturas mais robustas de pagamento e divisao, a **apresentacao funcional principal** deve focar na ideia de **quadro de controle de gastos com comprovante**, porque foi essa a direcao alinhada com o professor.

---

## 8. Como a parte de tarefas deve ser entendida

A area de tarefas funciona como organizacao da rotina da casa.

Ela serve para:
- criar tarefas
- acompanhar o andamento
- marcar conclusao
- guardar historico do que ja foi feito

Ela **nao** tenta ser sistema de auditoria ou fiscalizacao pesada.

---

## 9. Modelos principais do banco

Os modelos principais do sistema sao:

- `Republica`
- `Morador`
- `Despesa`
- `DivisaoDespesa`
- `Pagamento`
- `PagamentoDivisao`
- `Tarefa`

### Relacoes importantes

- uma `Republica` tem varios `Moradores`
- uma `Republica` tem varias `Despesas`
- uma `Despesa` pode gerar varias `DivisaoDespesa`
- uma `Republica` tem varias `Tarefas`

### Observacao importante para documentacao

Se o texto for mais academico e conceitual, a parte financeira pode ser descrita dando destaque a:
- `Despesa`
- `DivisaoDespesa`

e tratando `Pagamento` e `PagamentoDivisao` como parte de apoio/evolucao tecnica, se necessario.

---

## 10. Regras de negocio principais

### Regras de autenticacao e acesso
- o usuario precisa estar autenticado para acessar a area interna
- usuarios comuns so podem acessar dados da propria republica
- usuarios `staff` do Django tem poder tecnico global
- o admin da republica tem poder administrativo dentro da propria republica

### Regras da republica
- quem cria uma nova republica vira admin dela
- um usuario nao deve criar multiplas republicas para si no fluxo normal

### Regras de despesas
- a despesa pertence a uma republica
- o morador que pagou precisa pertencer a mesma republica
- a divisao deve acontecer apenas entre moradores validos da mesma republica

### Regras de tarefas
- a tarefa pertence a uma republica
- o responsavel precisa ser da mesma republica
- usuarios comuns tem menos permissao de edicao que o admin da republica

---

## 11. Rotas web principais

- `/`
- `/login/`
- `/cadastro/`
- `/painel/`
- `/financas/`
- `/tarefas/`

---

## 12. Endpoints principais da API

### Autenticacao
- `POST /api/auth/cadastro/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`

### Recursos principais
- `GET/POST /api/republicas/`
- `GET/POST /api/moradores/`
- `GET/POST /api/despesas/`
- `GET /api/divisoes/`
- `GET/POST /api/pagamentos/`
- `GET/POST /api/tarefas/`
- `GET /api/republicas/<id>/resumo-financeiro/`
- `GET /api/dashboard/overview/`

---

## 13. Estado atual da interface

### Dashboard
- resumo da casa
- indicadores principais
- visao geral de despesas e tarefas

### Financas
- quadro de gastos
- despesas pendentes
- despesas pagas
- comprovante da conta paga
- participacao dos moradores

### Tarefas
- quadro com organizacao do fluxo
- historico de tarefas concluidas

---

## 14. Dados de demonstracao

Existe um comando de carga de dados:

`python manage.py seed_demo`

Ele serve para deixar o sistema pronto para teste e apresentacao com exemplos.

Usuarios demo:
- `testeuser@example.com` / `Teste12345`
- `shinrateus@gmail.com` / `Teste12345`

---

## 15. Como rodar o sistema

### Forma mais simples no Windows

Executar:

`iniciar_rabbu.bat`

Esse arquivo:
- cria o ambiente virtual
- instala dependencias
- roda migracoes
- carrega dados demo
- abre o navegador
- sobe o servidor

### Forma manual

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo
.\.venv\Scripts\python manage.py runserver
```

---

## 16. Estado de qualidade do projeto

O projeto ja possui testes automatizados.

Pontos importantes:
- autenticacao
- escopo por republica
- criacao de republica
- despesas
- validacoes
- tarefas
- fluxo principal do sistema

Quando este contexto foi criado, a suite estava passando com sucesso.

---

## 17. Como o ChatGPT deve me ajudar melhor

Quando eu pedir ajuda, o ChatGPT deve:
- escrever de forma clara e academica
- evitar inventar funcionalidades nao implementadas
- explicar o sistema com base no contexto acima
- priorizar coerencia com o que esta funcionando no projeto
- usar linguagem simples quando o objetivo for apresentacao
- usar linguagem tecnica quando o objetivo for documentacao formal

---

## 18. O que o ChatGPT deve evitar

Evitar afirmar que o sistema:
- faz pagamento real
- gera boleto bancario oficial
- integra com banco
- faz conciliacao financeira real
- possui arquitetura enterprise

Tambem evitar:
- exagerar o nivel de complexidade
- descrever o projeto como produto final de mercado

---

## 19. Exemplos de pedidos que posso fazer ao ChatGPT

### Para documentacao tecnica
"Com base neste contexto, escreva uma documentacao tecnica do sistema em tom academico."

### Para apresentacao
"Com base neste contexto, crie um roteiro de apresentacao de 8 minutos sobre o sistema."

### Para trabalho de testes
"Com base neste contexto, monte um plano de testes e casos de teste para o sistema."

### Para manual do usuario
"Com base neste contexto, crie um manual de uso simples para o professor conseguir rodar e testar o sistema."

### Para documentacao da API
"Com base neste contexto, documente os principais endpoints da API com exemplos de uso."

---

## 20. Arquivos principais do projeto

Se o ChatGPT precisar saber onde olhar primeiro, os arquivos centrais sao:

- `README.md`
- `gerenciamento_republica/models.py`
- `gerenciamento_republica/serializers.py`
- `gerenciamento_republica/views.py`
- `gerenciamento_republica/urls.py`
- `templates/gerenciamento_republica/financas.html`
- `templates/gerenciamento_republica/tarefas.html`
- `templates/gerenciamento_republica/dashboard.html`
- `static/gerenciamento_republica/js/core.js`
- `static/gerenciamento_republica/js/financas.js`
- `static/gerenciamento_republica/js/tarefas.js`
- `gerenciamento_republica/tests.py`

---

## 21. Resumo curto para colar no ChatGPT

Se eu quiser mandar uma versao curta, posso usar isto:

> Tenho um projeto de faculdade chamado RABBU, feito em Django, para gestao de republicas. O sistema possui cadastro/login, criacao e ingresso em republicas, dashboard, controle de gastos da casa e quadro de tarefas. A area de financas deve ser entendida como controle de despesas: cadastra-se uma conta, define-se quem pagou, o sistema divide entre moradores, a conta fica pendente ou paga, e quando paga pode receber comprovante. A area de tarefas serve para organizacao da rotina da casa, com historico de tarefas concluidas. Quero ajuda para criar documentacao, apresentacao ou textos tecnicos, sem inventar integracao bancaria ou funcionalidades nao implementadas.

