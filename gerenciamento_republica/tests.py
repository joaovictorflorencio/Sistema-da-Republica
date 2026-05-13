from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, PagamentoDivisao, Republica, Tarefa

User = get_user_model()


class DespesaApiTests(APITestCase):
    def setUp(self):
        self.republica = Republica.objects.create(nome='Solar 101', endereco='Rua A, 10')
        self.user = User.objects.create_user(
            username='ana_login',
            email='ana_login@example.com',
            password='SenhaForte123',
        )
        self.m1 = Morador.objects.create(
            nome='Ana',
            email='ana@example.com',
            usuario=self.user,
            republica=self.republica,
        )
        self.m2 = Morador.objects.create(
            nome='Bia',
            email='bia@example.com',
            republica=self.republica,
        )
        self.m3 = Morador.objects.create(
            nome='Caio',
            email='caio@example.com',
            republica=self.republica,
        )
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'username': 'ana_login',
                'password': 'SenhaForte123',
            },
            format='json',
        )
        self.token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')

    def test_cria_despesa_com_divisao_automatica(self):
        response = self.client.post(
            '/api/despesas/',
            {
                'republica': self.republica.id,
                'titulo': 'Internet',
                'descricao': 'Fatura do mes',
                'categoria': 'INTERNET',
                'valor_total': '100.00',
                'paga_por': self.m1.id,
                'data_despesa': '2026-04-04',
                'morador_ids': [self.m1.id, self.m2.id, self.m3.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        despesa = Despesa.objects.get(pk=response.data['id'])
        divisoes = DivisaoDespesa.objects.filter(despesa=despesa).order_by('morador_id')
        divisao_pagante = divisoes.get(morador=self.m1)

        self.assertEqual(divisoes.count(), 3)
        self.assertEqual(sum(divisao.valor_devido for divisao in divisoes), Decimal('100.00'))
        self.assertEqual(divisao_pagante.valor_pago, divisao_pagante.valor_devido)
        self.assertEqual(divisao_pagante.status, DivisaoDespesa.Status.QUITADO)

    def test_resumo_financeiro_retorna_saldo(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Energia',
            descricao='Conta de luz',
            categoria='ENERGIA',
            valor_total='90.00',
            paga_por=self.m1,
            data_despesa='2026-04-04',
        )
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m1, valor_devido='30.00')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m2, valor_devido='30.00')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m3, valor_devido='30.00')

        response = self.client.get(f'/api/republicas/{self.republica.id}/resumo-financeiro/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_despesas'], '90.00')
        self.assertEqual(response.data['total_quitado'], '30.00')
        self.assertEqual(response.data['total_pendente'], '60.00')
        saldos = {item['nome']: item['saldo'] for item in response.data['moradores']}
        self.assertEqual(saldos['Ana'], '60.00')
        self.assertEqual(saldos['Bia'], '-30.00')
        self.assertEqual(saldos['Caio'], '-30.00')

    def test_cria_pagamento_na_mesma_republica(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Internet',
            descricao='Conta principal',
            categoria='INTERNET',
            valor_total='100.00',
            paga_por=self.m1,
            data_despesa='2026-04-04',
        )
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m1, valor_devido='33.34')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m2, valor_devido='33.33')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m3, valor_devido='33.33')

        response = self.client.post(
            '/api/pagamentos/',
            {
                'republica': self.republica.id,
                'pagador': self.m2.id,
                'recebedor': self.m1.id,
                'valor': '33.33',
                'observacao': 'Acerto da internet',
                'data_pagamento': '2026-04-05',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['pagador_nome'], 'Bia')
        self.assertEqual(response.data['recebedor_nome'], 'Ana')
        self.assertEqual(len(response.data['itens']), 1)
        divisao_bia = DivisaoDespesa.objects.get(despesa=despesa, morador=self.m2)
        self.assertEqual(divisao_bia.valor_pago, Decimal('33.33'))
        self.assertEqual(divisao_bia.status, DivisaoDespesa.Status.QUITADO)

    def test_pagamento_parcial_atualiza_divisao_e_cria_item_de_aplicacao(self):
        response = self.client.post(
            '/api/despesas/',
            {
                'republica': self.republica.id,
                'titulo': 'Mercado do mes',
                'descricao': 'Compras compartilhadas',
                'categoria': 'MERCADO',
                'valor_total': '90.00',
                'paga_por': self.m1.id,
                'data_despesa': '2026-04-10',
                'morador_ids': [self.m1.id, self.m2.id, self.m3.id],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        despesa_id = response.data['id']

        pagamento = self.client.post(
            '/api/pagamentos/',
            {
                'republica': self.republica.id,
                'pagador': self.m2.id,
                'recebedor': self.m1.id,
                'valor': '15.00',
                'referencia_despesa': despesa_id,
                'observacao': 'Primeira parcela',
                'data_pagamento': '2026-04-11',
            },
            format='json',
        )

        self.assertEqual(pagamento.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PagamentoDivisao.objects.count(), 1)
        divisao_bia = DivisaoDespesa.objects.get(despesa_id=despesa_id, morador=self.m2)
        self.assertEqual(divisao_bia.valor_devido, Decimal('30.00'))
        self.assertEqual(divisao_bia.valor_pago, Decimal('15.00'))
        self.assertEqual(divisao_bia.saldo_aberto, Decimal('15.00'))
        self.assertEqual(divisao_bia.status, DivisaoDespesa.Status.PARCIAL)

    def test_nao_permite_pagamento_acima_do_saldo_devido(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Mercado',
            descricao='Compras da semana',
            categoria='MERCADO',
            valor_total='90.00',
            paga_por=self.m1,
            data_despesa='2026-04-04',
        )
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m1, valor_devido='30.00')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m2, valor_devido='30.00')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m3, valor_devido='30.00')

        response = self.client.post(
            '/api/pagamentos/',
            {
                'republica': self.republica.id,
                'pagador': self.m2.id,
                'recebedor': self.m1.id,
                'valor': '45.00',
                'observacao': 'Tentativa acima do devido',
                'data_pagamento': '2026-04-05',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('valor', response.data)


class AutenticacaoApiTests(APITestCase):
    def setUp(self):
        self.republica = Republica.objects.create(nome='Vila 22', endereco='Rua B, 22')

    def test_cadastro_retorna_token_e_cria_morador(self):
        response = self.client.post(
            '/api/auth/cadastro/',
            {
                'username': 'lucas',
                'email': 'lucas@example.com',
                'password': 'SenhaForte123',
                'password_confirm': 'SenhaForte123',
                'nome': 'Lucas',
                'republica': self.republica.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'lucas')
        self.assertIsNotNone(response.data['morador_id'])

    def test_me_exige_autenticacao_e_retorna_usuario_logado(self):
        user = User.objects.create_user(
            username='bia_login',
            email='bia_login@example.com',
            password='SenhaForte123',
        )
        self.client.force_authenticate(user=user)

        response = self.client.get('/api/auth/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'bia_login')

    def test_login_por_email_retorna_token(self):
        user = User.objects.create_user(
            username='mateus_login',
            email='mateus@example.com',
            password='SenhaForte123',
        )

        response = self.client.post(
            '/api/auth/login/',
            {
                'email': user.email,
                'password': 'SenhaForte123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_invalido_retorna_erro(self):
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'naoexiste@example.com',
                'password': 'errada',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_cadastro_pode_criar_nova_republica(self):
        response = self.client.post(
            '/api/auth/cadastro/',
            {
                'username': 'nova_moradora',
                'email': 'nova@example.com',
                'password': 'SenhaForte123',
                'password_confirm': 'SenhaForte123',
                'nome': 'Nova Moradora',
                'nova_republica_nome': 'Casa Aurora',
                'nova_republica_endereco': 'Rua das Flores, 200',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        morador = Morador.objects.get(usuario__username='nova_moradora')
        self.assertEqual(morador.republica.nome, 'Casa Aurora')
        self.assertTrue(morador.eh_admin)


class EscopoRepublicaTests(APITestCase):
    def setUp(self):
        self.republica_1 = Republica.objects.create(nome='Casa 1', endereco='Rua 1')
        self.republica_2 = Republica.objects.create(nome='Casa 2', endereco='Rua 2')
        self.user = User.objects.create_user(
            username='escopo_user',
            email='escopo@example.com',
            password='SenhaForte123',
        )
        self.morador_1 = Morador.objects.create(
            nome='Escopo 1',
            email='escopo1@example.com',
            usuario=self.user,
            republica=self.republica_1,
        )
        self.morador_2 = Morador.objects.create(
            nome='Outro Morador',
            email='outro@example.com',
            republica=self.republica_2,
        )
        self.despesa_1 = Despesa.objects.create(
            republica=self.republica_1,
            titulo='Internet Casa 1',
            descricao='Conta',
            categoria='INTERNET',
            valor_total='80.00',
            paga_por=self.morador_1,
            data_despesa='2026-04-04',
        )
        self.despesa_2 = Despesa.objects.create(
            republica=self.republica_2,
            titulo='Internet Casa 2',
            descricao='Conta',
            categoria='INTERNET',
            valor_total='70.00',
            paga_por=self.morador_2,
            data_despesa='2026-04-04',
        )
        self.tarefa_1 = Tarefa.objects.create(
            republica=self.republica_1,
            titulo='Limpar cozinha',
            responsavel=self.morador_1,
            status='PENDENTE',
            prioridade='MEDIA',
        )
        self.tarefa_2 = Tarefa.objects.create(
            republica=self.republica_2,
            titulo='Comprar gas',
            responsavel=self.morador_2,
            status='PENDENTE',
            prioridade='ALTA',
        )
        self.client.force_authenticate(user=self.user)

    def test_lista_despesas_retorna_apenas_dados_da_propria_republica(self):
        response = self.client.get('/api/despesas/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['titulo'], 'Internet Casa 1')

    def test_nao_permite_resumo_de_outra_republica(self):
        response = self.client.get(f'/api/republicas/{self.republica_2.id}/resumo-financeiro/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_overview_retorna_somente_dados_da_republica_do_usuario(self):
        response = self.client.get('/api/dashboard/overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['republica']['id'], self.republica_1.id)
        self.assertEqual(response.data['total_moradores'], 1)
        self.assertEqual(len(response.data['ultimas_despesas']), 1)
        self.assertEqual(len(response.data['tarefas_pendentes']), 1)

    def test_dashboard_considera_apenas_moradores_ativos(self):
        Morador.objects.create(
            nome='Morador Inativo',
            email='inativo@example.com',
            republica=self.republica_1,
            ativo=False,
        )

        response = self.client.get('/api/dashboard/overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_moradores'], 1)

    def test_usuario_comum_nao_pode_editar_morador(self):
        response = self.client.patch(
            f'/api/moradores/{self.morador_1.id}/',
            {'nome': 'Nome alterado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_da_republica_pode_editar_morador(self):
        self.morador_1.eh_admin = True
        self.morador_1.save(update_fields=['eh_admin'])

        response = self.client.patch(
            f'/api/moradores/{self.morador_1.id}/',
            {'nome': 'Nome admin alterado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.morador_1.refresh_from_db()
        self.assertEqual(self.morador_1.nome, 'Nome admin alterado')

    def test_admin_da_republica_nao_pode_mover_morador_para_outra_republica(self):
        self.morador_1.eh_admin = True
        self.morador_1.save(update_fields=['eh_admin'])

        response = self.client.patch(
            f'/api/moradores/{self.morador_1.id}/',
            {'republica': self.republica_2.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.morador_1.refresh_from_db()
        self.assertEqual(self.morador_1.republica_id, self.republica_1.id)

    def test_usuario_comum_nao_pode_excluir_despesa(self):
        response = self.client.delete(f'/api/despesas/{self.despesa_1.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_da_republica_pode_editar_despesa_existente(self):
        self.morador_1.eh_admin = True
        self.morador_1.save(update_fields=['eh_admin'])

        response = self.client.patch(
            f'/api/despesas/{self.despesa_1.id}/',
            {'titulo': 'Internet atualizada'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.despesa_1.refresh_from_db()
        self.assertEqual(self.despesa_1.titulo, 'Internet atualizada')

    def test_editar_titulo_da_despesa_nao_recria_divisoes(self):
        self.morador_1.eh_admin = True
        self.morador_1.save(update_fields=['eh_admin'])
        DivisaoDespesa.objects.create(
            despesa=self.despesa_1,
            morador=self.morador_1,
            valor_devido=Decimal('40.00'),
            valor_pago=Decimal('40.00'),
        )
        DivisaoDespesa.objects.create(
            despesa=self.despesa_1,
            morador=self.morador_2,
            valor_devido=Decimal('40.00'),
            valor_pago=Decimal('0.00'),
        )

        ids_antes = list(self.despesa_1.divisoes.values_list('id', flat=True).order_by('id'))
        response = self.client.patch(
            f'/api/despesas/{self.despesa_1.id}/',
            {'titulo': 'Internet casa 1 ajustada'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids_depois = list(self.despesa_1.divisoes.values_list('id', flat=True).order_by('id'))
        self.assertEqual(ids_antes, ids_depois)

    def test_usuario_comum_nao_pode_editar_despesa_existente(self):
        response = self.client.patch(
            f'/api/despesas/{self.despesa_1.id}/',
            {'titulo': 'Titulo alterado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_comum_so_pode_alterar_status_da_tarefa(self):
        response = self.client.patch(
            f'/api/tarefas/{self.tarefa_1.id}/',
            {'status': 'CONCLUIDA'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'CONCLUIDA')

    def test_usuario_comum_nao_pode_editar_outros_campos_da_tarefa(self):
        response = self.client.patch(
            f'/api/tarefas/{self.tarefa_1.id}/',
            {'titulo': 'Novo titulo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_da_republica_nao_pode_mover_tarefa_para_outra_republica(self):
        self.morador_1.eh_admin = True
        self.morador_1.save(update_fields=['eh_admin'])

        response = self.client.patch(
            f'/api/tarefas/{self.tarefa_1.id}/',
            {'republica': self.republica_2.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.tarefa_1.refresh_from_db()
        self.assertEqual(self.tarefa_1.republica_id, self.republica_1.id)

    def test_campo_usuario_de_morador_nao_e_editavel_pela_api(self):
        outro_user = User.objects.create_user(
            username='outro_login',
            email='outrologin@example.com',
            password='SenhaForte123',
        )

        response = self.client.post(
            '/api/moradores/',
            {
                'nome': 'Novo Morador',
                'email': 'novo@example.com',
                'usuario': outro_user.id,
                'republica': self.republica_1.id,
                'ativo': True,
                'data_entrada': '2026-04-13',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        morador = Morador.objects.get(id=response.data['id'])
        self.assertIsNone(morador.usuario)

    def test_usuario_comum_nao_pode_criar_morador_como_admin(self):
        response = self.client.post(
            '/api/moradores/',
            {
                'nome': 'Novo Admin Indevido',
                'email': 'novo-admin@example.com',
                'republica': self.republica_1.id,
                'ativo': True,
                'eh_admin': True,
                'data_entrada': '2026-04-13',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        morador = Morador.objects.get(id=response.data['id'])
        self.assertFalse(morador.eh_admin)


class RepublicaFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='criador_rep',
            email='criador@example.com',
            password='SenhaForte123',
            first_name='Criador',
        )
        self.client.force_authenticate(user=self.user)

    def test_criar_republica_vincula_usuario_como_morador(self):
        response = self.client.post(
            '/api/republicas/',
            {
                'nome': 'Nova Casa',
                'endereco': 'Rua Nova, 123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        morador = Morador.objects.get(usuario=self.user)
        self.assertEqual(morador.republica_id, response.data['id'])
        self.assertEqual(morador.nome, 'Criador')
        self.assertTrue(morador.eh_admin)

    def test_nao_permite_criar_outra_republica_quando_usuario_ja_tem_vinculo(self):
        republica = Republica.objects.create(nome='Casa Atual', endereco='Rua A')
        Morador.objects.create(
            nome='Criador',
            email=self.user.email,
            usuario=self.user,
            republica=republica,
        )

        response = self.client.post(
            '/api/republicas/',
            {
                'nome': 'Outra Casa',
                'endereco': 'Rua B',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)


class JornadaMvpTests(APITestCase):
    def test_jornada_principal_do_mvp(self):
        cadastro = self.client.post(
            '/api/auth/cadastro/',
            {
                'username': 'jornada_user',
                'email': 'jornada@example.com',
                'password': 'SenhaForte123',
                'password_confirm': 'SenhaForte123',
                'nome': 'Jornada User',
                'nova_republica_nome': 'Casa Jornada',
                'nova_republica_endereco': 'Rua Principal, 10',
            },
            format='json',
        )
        self.assertEqual(cadastro.status_code, status.HTTP_201_CREATED)

        token = cadastro.data['token']
        republica_id = cadastro.data['user']['republica_id']
        morador_principal_id = cadastro.data['user']['morador_id']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        morador_extra = self.client.post(
            '/api/moradores/',
            {
                'nome': 'Colega de Casa',
                'email': 'colega@example.com',
                'republica': republica_id,
                'ativo': True,
                'data_entrada': '2026-04-13',
            },
            format='json',
        )
        self.assertEqual(morador_extra.status_code, status.HTTP_201_CREATED)
        morador_extra_id = morador_extra.data['id']

        overview_inicial = self.client.get('/api/dashboard/overview/')
        self.assertEqual(overview_inicial.status_code, status.HTTP_200_OK)
        self.assertEqual(overview_inicial.data['republica']['id'], republica_id)

        despesa = self.client.post(
            '/api/despesas/',
            {
                'republica': republica_id,
                'titulo': 'Internet da casa',
                'descricao': 'Plano mensal',
                'categoria': 'INTERNET',
                'valor_total': '120.00',
                'paga_por': morador_principal_id,
                'data_despesa': '2026-04-13',
                'morador_ids': [morador_principal_id, morador_extra_id],
            },
            format='json',
        )
        self.assertEqual(despesa.status_code, status.HTTP_201_CREATED)

        resumo_apos_despesa = self.client.get(f'/api/republicas/{republica_id}/resumo-financeiro/')
        self.assertEqual(resumo_apos_despesa.status_code, status.HTTP_200_OK)
        saldos_despesa = {item['id']: item['saldo'] for item in resumo_apos_despesa.data['moradores']}
        self.assertEqual(saldos_despesa[morador_principal_id], '60.00')
        self.assertEqual(saldos_despesa[morador_extra_id], '-60.00')

        pagamento = self.client.post(
            '/api/pagamentos/',
            {
                'republica': republica_id,
                'pagador': morador_extra_id,
                'recebedor': morador_principal_id,
                'valor': '60.00',
                'observacao': 'Acerto da internet',
                'data_pagamento': '2026-04-14',
            },
            format='json',
        )
        self.assertEqual(pagamento.status_code, status.HTTP_201_CREATED)

        resumo_apos_pagamento = self.client.get(f'/api/republicas/{republica_id}/resumo-financeiro/')
        self.assertEqual(resumo_apos_pagamento.status_code, status.HTTP_200_OK)
        saldos_pagamento = {item['id']: item['saldo'] for item in resumo_apos_pagamento.data['moradores']}
        self.assertEqual(saldos_pagamento[morador_principal_id], '0.00')
        self.assertEqual(saldos_pagamento[morador_extra_id], '0.00')

        tarefa = self.client.post(
            '/api/tarefas/',
            {
                'republica': republica_id,
                'titulo': 'Limpar a cozinha',
                'descricao': 'Organizar a pia e o fogao',
                'responsavel': morador_extra_id,
                'prioridade': 'MEDIA',
                'status': 'PENDENTE',
                'data_limite': '2026-04-15',
            },
            format='json',
        )
        self.assertEqual(tarefa.status_code, status.HTTP_201_CREATED)

        concluir_tarefa = self.client.patch(
            f"/api/tarefas/{tarefa.data['id']}/",
            {'status': 'CONCLUIDA'},
            format='json',
        )
        self.assertEqual(concluir_tarefa.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(concluir_tarefa.data['concluida_em'])


class FrontendRoutesTests(TestCase):
    def test_rotas_html_principais_renderizam(self):
        for rota in ['/', '/login/', '/cadastro/', '/painel/', '/financas/', '/tarefas/']:
            response = self.client.get(rota)
            self.assertEqual(response.status_code, status.HTTP_200_OK, rota)
