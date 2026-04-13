from django.contrib import admin

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, Republica, Tarefa


@admin.register(Republica)
class RepublicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'endereco', 'criada_em')
    search_fields = ('nome', 'endereco')


@admin.register(Morador)
class MoradorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'email', 'usuario', 'republica', 'ativo')
    list_filter = ('ativo', 'republica')
    search_fields = ('nome', 'email', 'usuario__username')


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'categoria', 'valor_total', 'republica', 'paga_por', 'data_despesa')
    list_filter = ('categoria', 'republica', 'data_despesa')
    search_fields = ('titulo', 'descricao')


@admin.register(DivisaoDespesa)
class DivisaoDespesaAdmin(admin.ModelAdmin):
    list_display = ('id', 'despesa', 'morador', 'valor_devido', 'quitado')
    list_filter = ('quitado', 'despesa__republica')
    search_fields = ('despesa__titulo', 'morador__nome')


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'republica', 'pagador', 'recebedor', 'valor', 'data_pagamento')
    list_filter = ('republica', 'data_pagamento')
    search_fields = ('pagador__nome', 'recebedor__nome', 'observacao')


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'republica', 'responsavel', 'status', 'prioridade', 'data_limite')
    list_filter = ('status', 'prioridade', 'republica')
    search_fields = ('titulo', 'descricao')
