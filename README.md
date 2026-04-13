# Gerenciamento de Republicas

Este projeto e um MVP feito em Django para ajudar no dia a dia de moradias compartilhadas. A ideia e simples: reunir, em um lugar so, o que normalmente gera confusao em uma republica, como despesas da casa, organizacao de tarefas e a visao geral de como a rotina esta andando.

Hoje o sistema ja permite:
- cadastro e login pela web
- criacao de uma nova republica durante o cadastro
- acesso a um dashboard com resumo da casa
- lancamento de despesas
- gerenciamento de tarefas
- API REST para republicas, moradores, despesas, pagamentos e tarefas

## Como rodar o projeto

Se voce acabou de baixar o projeto, estes comandos ja deixam tudo pronto:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

Depois disso, e so abrir:

`http://127.0.0.1:8000/`

## Como navegar

As telas principais do sistema sao estas:

- `http://127.0.0.1:8000/login/`
- `http://127.0.0.1:8000/cadastro/`
- `http://127.0.0.1:8000/painel/`
- `http://127.0.0.1:8000/financas/`
- `http://127.0.0.1:8000/tarefas/`

O fluxo mais natural do MVP e:

1. criar uma conta em `/cadastro/`
2. entrar em uma republica existente ou criar uma nova
3. acessar o painel
4. lancar despesas da casa
5. organizar as tarefas da rotina

## Dados de demonstracao

Se voce quiser ver o sistema com dados de exemplo, pode popular o banco com:

```powershell
.\.venv\Scripts\python manage.py seed_demo
```

Usuarios criados:

- `testeuser@example.com` / `Teste12345`
- `shinrateus@gmail.com` / `Teste12345`

## Area administrativa

Se quiser acessar o admin do Django, crie um superusuario:

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

Depois abra:

`http://127.0.0.1:8000/admin/`

## API e autenticacao

O projeto tambem possui API REST. O cadastro fica em:

`POST /api/auth/cadastro/`

Exemplo para entrar em uma republica existente:

```json
{
  "username": "lucas",
  "email": "lucas@example.com",
  "password": "SenhaForte123",
  "password_confirm": "SenhaForte123",
  "nome": "Lucas",
  "republica": 1
}
```

Exemplo para criar uma nova republica no mesmo fluxo:

```json
{
  "username": "lucas",
  "email": "lucas@example.com",
  "password": "SenhaForte123",
  "password_confirm": "SenhaForte123",
  "nome": "Lucas",
  "nova_republica_nome": "Solar 101",
  "nova_republica_endereco": "Rua A, 10"
}
```

O login fica em:

`POST /api/auth/login/`

```json
{
  "email": "lucas@example.com",
  "password": "SenhaForte123"
}
```

Com o token retornado, use:

```text
Authorization: Token SEU_TOKEN
```

Tambem existem:

- `GET /api/auth/me/`
- `POST /api/auth/logout/`

## Endpoints principais

Os endpoints principais da API hoje sao:

- `GET/POST /api/republicas/`
- `GET/POST /api/moradores/`
- `GET/POST /api/despesas/`
- `GET /api/divisoes/`
- `GET/POST /api/pagamentos/`
- `GET/POST /api/tarefas/`
- `GET /api/republicas/<id>/resumo-financeiro/`
- `GET /api/dashboard/overview/`

## O que este MVP ja entrega

O sistema ja tem uma base boa para demonstracao:

- usuarios comuns so enxergam dados da propria republica
- despesas sao divididas automaticamente entre os moradores informados
- o criador de uma republica passa a ser vinculado como primeiro morador
- o dashboard mostra uma visao geral da casa
- os testes cobrem a jornada principal do projeto

## O que ainda pode evoluir

Alguns pontos ficaram como proxima etapa:

- refinar toda a logica de pagamentos
- trocar a entrada em republica por ID por algo mais amigavel, como codigo ou lista
- dar mais polimento visual e de experiencia

## Como rodar os testes

```powershell
.\.venv\Scripts\python manage.py test gerenciamento_republica
```


