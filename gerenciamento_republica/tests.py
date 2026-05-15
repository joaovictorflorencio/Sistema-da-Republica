import shutil
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, PagamentoDivisao, Republica, Tarefa

User = get_user_model()
TEST_MEDIA_ROOT = Path(__file__).resolve().parent.parent / 'test_media'


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
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
            eh_admin=True,
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_admin_cria_despesa_sem_divisao_automatica(self):
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
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        despesa = Despesa.objects.get(pk=response.data['id'])
        self.assertEqual(despesa.paga_por_id, self.m1.id)
        self.assertEqual(despesa.divisoes.count(), 0)
        self.assertEqual(despesa.status_pagamento, Despesa.StatusPagamento.PENDENTE)

    def test_resumo_financeiro_retorna_saldo(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Energia',
            descricao='Conta de luz',
            categoria='ENERGIA',
            valor_total='90.00',
            paga_por=self.m1,
            quitada_por=self.m1,
            status_pagamento=Despesa.StatusPagamento.PAGA,
            data_pagamento='2026-04-04',
            data_despesa='2026-04-04',
            comprovante_pagamento=SimpleUploadedFile(
                'energia.pdf',
                b'comprovante energia',
                content_type='application/pdf',
            ),
        )
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m1, valor_devido='30.00')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m2, valor_devido='30.00')
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m3, valor_devido='30.00')

        response = self.client.get(f'/api/republicas/{self.republica.id}/resumo-financeiro/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_despesas'], '90.00')
        self.assertEqual(response.data['total_quitado'], '90.00')
        self.assertEqual(response.data['total_pendente'], '0.00')
        saldos = {item['nome']: item['saldo'] for item in response.data['moradores']}
        self.assertEqual(saldos['Ana'], '90.00')
        self.assertEqual(saldos['Bia'], '0.00')
        self.assertEqual(saldos['Caio'], '0.00')

    def test_cria_pagamento_na_mesma_republica(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Internet',
            descricao='Conta principal',
            categoria='INTERNET',
            valor_total='100.00',
            paga_por=self.m1,
            quitada_por=self.m1,
            status_pagamento=Despesa.StatusPagamento.PAGA,
            data_pagamento='2026-04-04',
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
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        despesa_id = response.data['id']
        despesa = Despesa.objects.get(pk=despesa_id)
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m2, valor_devido=Decimal('30.00'))
        Despesa.objects.filter(pk=despesa_id).update(
            status_pagamento=Despesa.StatusPagamento.PAGA,
            quitada_por_id=self.m1.id,
            data_pagamento='2026-04-10',
        )

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
            quitada_por=self.m1,
            status_pagamento=Despesa.StatusPagamento.PAGA,
            data_pagamento='2026-04-04',
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

    def test_responsavel_pela_conta_pode_marcar_despesa_como_paga_com_comprovante(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Conta de agua',
            descricao='Conta mensal',
            categoria='AGUA',
            valor_total='78.50',
            paga_por=self.m1,
            data_vencimento='2026-04-14',
            data_despesa='2026-04-10',
        )
        DivisaoDespesa.objects.create(
            despesa=despesa,
            morador=self.m1,
            valor_devido=Decimal('26.17'),
        )
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m2, valor_devido=Decimal('26.17'))
        DivisaoDespesa.objects.create(despesa=despesa, morador=self.m3, valor_devido=Decimal('26.16'))

        comprovante = SimpleUploadedFile(
            'comprovante.pdf',
            b'conteudo do comprovante',
            content_type='application/pdf',
        )
        response = self.client.patch(
            f'/api/despesas/{despesa.id}/',
            {
                'status_pagamento': Despesa.StatusPagamento.PAGA,
                'data_pagamento': '2026-04-14',
                'comprovante_pagamento': comprovante,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        despesa.refresh_from_db()
        self.assertEqual(despesa.status_pagamento, Despesa.StatusPagamento.PAGA)
        self.assertEqual(str(despesa.data_pagamento), '2026-04-14')
        self.assertTrue(bool(despesa.comprovante_pagamento))
        self.assertEqual(despesa.quitada_por_id, self.m1.id)

        outro_user = User.objects.create_user(
            username='carlos_login',
            email='carlos@example.com',
            password='SenhaForte123',
        )
        outro_morador = Morador.objects.create(
            nome='Carlos',
            email='carlos-morador@example.com',
            usuario=outro_user,
            republica=self.republica,
        )
        despesa_pendente = Despesa.objects.create(
            republica=self.republica,
            titulo='Conta de gas',
            descricao='Reposicao',
            categoria='OUTROS',
            valor_total='95.00',
            paga_por=self.m2,
            data_vencimento='2026-04-20',
            data_despesa='2026-04-13',
        )
        DivisaoDespesa.objects.create(
            despesa=despesa_pendente,
            morador=self.m2,
            valor_devido=Decimal('95.00'),
        )

        self.client.force_authenticate(user=outro_user)
        comprovante_outro = SimpleUploadedFile(
            'comprovante-outro.pdf',
            b'conteudo do comprovante de outro morador',
            content_type='application/pdf',
        )
        response_outro = self.client.patch(
            f'/api/despesas/{despesa_pendente.id}/',
            {
                'status_pagamento': Despesa.StatusPagamento.PAGA,
                'data_pagamento': '2026-04-20',
                'comprovante_pagamento': comprovante_outro,
            },
            format='multipart',
        )

        self.assertEqual(response_outro.status_code, status.HTTP_403_FORBIDDEN)
        despesa_pendente.refresh_from_db()
        self.assertIsNone(despesa_pendente.quitada_por_id)

    def test_morador_atribuido_pode_registrar_pagamento_da_propria_conta(self):
        user_m2 = User.objects.create_user(
            username='bia_login',
            email='bia_login@example.com',
            password='SenhaForte123',
        )
        self.m2.usuario = user_m2
        self.m2.save(update_fields=['usuario'])

        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Internet da casa',
            descricao='Plano mensal',
            categoria='INTERNET',
            valor_total='120.00',
            paga_por=self.m2,
            data_vencimento='2026-04-22',
            data_despesa='2026-04-15',
        )

        self.client.force_authenticate(user=user_m2)
        comprovante = SimpleUploadedFile(
            'internet.pdf',
            b'comprovante internet',
            content_type='application/pdf',
        )
        response = self.client.patch(
            f'/api/despesas/{despesa.id}/',
            {
                'status_pagamento': Despesa.StatusPagamento.PAGA,
                'data_pagamento': '2026-04-22',
                'comprovante_pagamento': comprovante,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        despesa.refresh_from_db()
        self.assertEqual(despesa.status_pagamento, Despesa.StatusPagamento.PAGA)
        self.assertEqual(despesa.quitada_por_id, self.m2.id)

    def test_nao_permite_marcar_despesa_como_paga_sem_comprovante(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Conta de luz',
            descricao='Conta mensal',
            categoria='ENERGIA',
            valor_total='110.00',
            paga_por=self.m1,
            data_vencimento='2026-04-18',
            data_despesa='2026-04-12',
        )

        response = self.client.patch(
            f'/api/despesas/{despesa.id}/',
            {
                'status_pagamento': Despesa.StatusPagamento.PAGA,
                'data_pagamento': '2026-04-18',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprovante_pagamento', response.data)

    def test_nao_permite_comprovante_com_extensao_invalida(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Conta de gas',
            descricao='Mensal',
            categoria='OUTROS',
            valor_total='80.00',
            paga_por=self.m1,
            data_vencimento='2026-04-18',
            data_despesa='2026-04-12',
        )
        comprovante = SimpleUploadedFile(
            'comprovante.exe',
            b'arquivo invalido',
            content_type='application/octet-stream',
        )

        response = self.client.patch(
            f'/api/despesas/{despesa.id}/',
            {
                'status_pagamento': Despesa.StatusPagamento.PAGA,
                'data_pagamento': '2026-04-18',
                'comprovante_pagamento': comprovante,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprovante_pagamento', response.data)

    def test_nao_permite_comprovante_maior_que_5mb(self):
        despesa = Despesa.objects.create(
            republica=self.republica,
            titulo='Conta de agua',
            descricao='Mensal',
            categoria='AGUA',
            valor_total='95.00',
            paga_por=self.m1,
            data_vencimento='2026-04-19',
            data_despesa='2026-04-12',
        )
        comprovante = SimpleUploadedFile(
            'comprovante.pdf',
            b'a' * (5 * 1024 * 1024 + 1),
            content_type='application/pdf',
        )

        response = self.client.patch(
            f'/api/despesas/{despesa.id}/',
            {
                'status_pagamento': Despesa.StatusPagamento.PAGA,
                'data_pagamento': '2026-04-19',
                'comprovante_pagamento': comprovante,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprovante_pagamento', response.data)


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

    def test_patch_me_atualiza_nome_do_usuario_e_do_morador(self):
        user = User.objects.create_user(
            username='perfil_login',
            email='perfil@example.com',
            password='SenhaForte123',
            first_name='Nome Antigo',
        )
        morador = Morador.objects.create(
            nome='Nome Antigo',
            email='perfil.morador@example.com',
            usuario=user,
            republica=self.republica,
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            '/api/auth/me/',
            {'nome': 'Nome Novo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        morador.refresh_from_db()
        self.assertEqual(user.first_name, 'Nome Novo')
        self.assertEqual(morador.nome, 'Nome Novo')

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

    def test_usuario_comum_nao_pode_criar_despesa(self):
        response = self.client.post(
            '/api/despesas/',
            {
                'republica': self.republica_1.id,
                'titulo': 'Nova conta',
                'descricao': 'Teste',
                'categoria': 'OUTROS',
                'valor_total': '50.00',
                'paga_por': self.morador_1.id,
                'data_despesa': '2026-04-15',
            },
            format='json',
        )

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
            },
            format='json',
        )
        self.assertEqual(despesa.status_code, status.HTTP_201_CREATED)

        resumo_apos_despesa = self.client.get(f'/api/republicas/{republica_id}/resumo-financeiro/')
        self.assertEqual(resumo_apos_despesa.status_code, status.HTTP_200_OK)
        saldos_despesa = {item['id']: item['saldo'] for item in resumo_apos_despesa.data['moradores']}
        pendentes_despesa = {item['id']: item['total_pendente'] for item in resumo_apos_despesa.data['moradores']}
        self.assertEqual(pendentes_despesa[morador_principal_id], '120.00')
        self.assertEqual(pendentes_despesa[morador_extra_id], '0.00')

        despesa_model = Despesa.objects.get(pk=despesa.data['id'])
        despesa_model.status_pagamento = Despesa.StatusPagamento.PAGA
        despesa_model.quitada_por_id = morador_principal_id
        despesa_model.data_pagamento = '2026-04-13'
        despesa_model.save()

        resumo_apos_quitacao = self.client.get(f'/api/republicas/{republica_id}/resumo-financeiro/')
        self.assertEqual(resumo_apos_quitacao.status_code, status.HTTP_200_OK)
        quitados_quitacao = {item['id']: item['total_quitado'] for item in resumo_apos_quitacao.data['moradores']}
        pendentes_quitacao = {item['id']: item['total_pendente'] for item in resumo_apos_quitacao.data['moradores']}
        self.assertEqual(quitados_quitacao[morador_principal_id], '120.00')
        self.assertEqual(pendentes_quitacao[morador_principal_id], '0.00')
        self.assertEqual(quitados_quitacao[morador_extra_id], '0.00')

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
        for rota in ['/', '/login/', '/cadastro/', '/painel/', '/financas/', '/tarefas/', '/perfil/']:
            response = self.client.get(rota)
            self.assertEqual(response.status_code, status.HTTP_200_OK, rota)
