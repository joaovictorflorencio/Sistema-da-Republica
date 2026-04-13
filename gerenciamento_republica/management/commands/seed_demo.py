from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from gerenciamento_republica.models import Despesa, DivisaoDespesa, Morador, Pagamento, Republica, Tarefa


class Command(BaseCommand):
    help = 'Popula o banco com dados de demonstracao para o MVP.'

    def handle(self, *args, **options):
        user_model = get_user_model()

        republica, _ = Republica.objects.get_or_create(
            nome='Republica Teste',
            defaults={'endereco': 'Rua das Flores, 123'},
        )

        user1, created = user_model.objects.get_or_create(
            username='testeuser',
            defaults={'email': 'testeuser@example.com', 'first_name': 'Usuario Teste'},
        )
        if created:
            user1.set_password('Teste12345')
            user1.save()

        user2, created = user_model.objects.get_or_create(
            username='teuszx',
            defaults={'email': 'shinrateus@gmail.com', 'first_name': 'Mateus'},
        )
        if created:
            user2.set_password('Teste12345')
            user2.save()

        morador1, _ = Morador.objects.get_or_create(
            email='testeuser@example.com',
            defaults={'nome': 'Usuario Teste', 'usuario': user1, 'republica': republica},
        )
        morador1.usuario = user1
        morador1.republica = republica
        morador1.nome = 'Usuario Teste'
        morador1.save()

        morador2, _ = Morador.objects.get_or_create(
            email='shinrateus@gmail.com',
            defaults={'nome': 'Mateus De Miranda Santos Moura', 'usuario': user2, 'republica': republica},
        )
        morador2.usuario = user2
        morador2.republica = republica
        morador2.nome = 'Mateus De Miranda Santos Moura'
        morador2.save()

        morador3, _ = Morador.objects.get_or_create(
            email='bia@example.com',
            defaults={'nome': 'Bia', 'republica': republica},
        )

        despesa, created = Despesa.objects.get_or_create(
            republica=republica,
            titulo='Internet da casa',
            defaults={
                'descricao': 'Plano mensal',
                'categoria': 'INTERNET',
                'valor_total': '120.00',
                'paga_por': morador1,
                'data_despesa': '2026-04-04',
            },
        )
        if created:
            participantes = [morador1, morador2, morador3]
            valor = 40
            for morador in participantes:
                DivisaoDespesa.objects.create(despesa=despesa, morador=morador, valor_devido=valor)

        Pagamento.objects.get_or_create(
            republica=republica,
            pagador=morador2,
            recebedor=morador1,
            valor='40.00',
            data_pagamento='2026-04-05',
            defaults={'observacao': 'Acerto da internet'},
        )

        Tarefa.objects.get_or_create(
            republica=republica,
            titulo='Limpar cozinha',
            defaults={
                'descricao': 'Organizar pia e lixo',
                'responsavel': morador2,
                'status': 'PENDENTE',
                'prioridade': 'MEDIA',
                'data_limite': '2026-04-10',
            },
        )
        Tarefa.objects.get_or_create(
            republica=republica,
            titulo='Comprar produtos de limpeza',
            defaults={
                'descricao': 'Detergente e agua sanitaria',
                'responsavel': morador3,
                'status': 'EM_ANDAMENTO',
                'prioridade': 'ALTA',
                'data_limite': '2026-04-09',
            },
        )

        self.stdout.write(self.style.SUCCESS('Dados de demonstracao criados com sucesso.'))
        self.stdout.write('Usuario: testeuser / Senha: Teste12345')
        self.stdout.write('Usuario: teuszx / Senha: Teste12345')
