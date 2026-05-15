# RABBU - Sistema de Gestao de Republicas

O RABBU e um projeto em Django feito para organizar a rotina de uma republica de forma simples e clara. A ideia central do sistema e juntar, em um unico lugar, o que mais costuma gerar atrito no dia a dia: contas da casa, tarefas e visao geral da rotina.

Hoje o sistema esta focado em um MVP funcional, com fluxo web completo e uma API REST para apoiar autenticacao, moradores, despesas e tarefas.

## O que o sistema faz hoje

- cadastro e login pela web
- criacao de uma nova republica no proprio cadastro
- entrada em uma republica existente por ID
- dashboard com resumo da casa
- controle de gastos em formato de quadro
- cadastro de despesas apenas pelo admin da republica
- atribuicao de cada despesa a um morador responsavel pelo pagamento
- registro do pagamento com comprovante
- destaque visual para contas vencidas e ainda pendentes
- quadro de tarefas com historico de concluidas
- isolamento de dados por republica

## Como funciona a tela de financas

No fluxo atual, a area de financas funciona como um controle de gastos da casa.

Regra principal:

1. o admin da republica cadastra a despesa
2. o admin escolhe qual morador fica responsavel por pagar aquela conta
3. a despesa aparece em `Contas pendentes`
4. quando o morador responsavel quita a conta, ele registra o pagamento e anexa o comprovante
5. a conta sai de `Pendentes` e vai para `Pagas`

Ou seja: a versao atual nao tenta fazer rateio complexo entre moradores no fluxo web principal. Ela foi simplificada para ficar mais coerente com o escopo academico do projeto.

## Cadastro de republica com CEP

Ao criar uma nova republica pela tela de cadastro, o usuario pode:

- informar o CEP
- preencher o endereco automaticamente
- ajustar numero e complemento
- abrir o local no Google Maps para conferencia

O endereco final continua sendo salvo em um unico campo de texto no backend.

## Como rodar o projeto

### Jeito mais simples no Windows

Abra a pasta do projeto e execute:

`iniciar_rabbu.bat`

Esse arquivo:

- cria a `.venv`, se precisar
- instala as dependencias
- aplica as migracoes
- roda o `seed_demo`
- abre o navegador
- inicia o servidor

Depois disso, o sistema abre em:

`http://127.0.0.1:8000/login/`

### Jeito manual

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo
.\.venv\Scripts\python manage.py runserver
```

## Rotas principais da interface

- `http://127.0.0.1:8000/login/`
- `http://127.0.0.1:8000/cadastro/`
- `http://127.0.0.1:8000/painel/`
- `http://127.0.0.1:8000/financas/`
- `http://127.0.0.1:8000/tarefas/`

## Fluxo recomendado para demonstracao

1. criar uma conta em `/cadastro/`
2. criar uma nova republica
3. entrar no painel
4. ir para `Financas`
5. cadastrar uma despesa como admin
6. registrar o pagamento da conta com comprovante
7. conferir a conta em `Pagas`
8. criar e concluir uma tarefa

## Dados de demonstracao

O comando `seed_demo` cria uma republica pronta para testes:

- republica: `Republica Teste`
- id da republica: `1`

Usuarios de exemplo:

- username: `testeuser`
  email: `testeuser@example.com`
  senha: `Teste12345`
  papel: admin da republica

- username: `teuszx`
  email: `shinrateus@gmail.com`
  senha: `Teste12345`
  papel: morador comum

## API principal

Autenticacao:

- `POST /api/auth/cadastro/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`

Recursos:

- `GET/POST /api/republicas/`
- `GET/POST /api/moradores/`
- `GET/POST /api/despesas/`
- `GET/POST /api/tarefas/`
- `GET /api/dashboard/overview/`
- `GET /api/republicas/<id>/resumo-financeiro/`

Observacao:

- a interface principal do sistema hoje usa o fluxo de `despesas` e `comprovantes`
- algumas rotas antigas de financas continuam no backend para suporte interno e testes
- no uso normal pela interface web, voce nao precisa se preocupar com elas

## Area administrativa do Django

Se quiser acessar o admin:

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

Depois abra:

`http://127.0.0.1:8000/admin/`

## Como rodar os testes

```powershell
.\.venv\Scripts\python manage.py test gerenciamento_republica
```



## Equipe

- Joao Victor Florencio - 01605737
- Mateus De Miranda Santos Moura - 01592191
- Miqueias Ferreira Barros - 01595460
- Gabriel Marques Barbosa de Santana - 01612589
- Erick Alves de Souza - 01613377
- Patrick Jose Viana Costa - 01594218
- Lucas Enthony Gomes Ferreira - 01576401
