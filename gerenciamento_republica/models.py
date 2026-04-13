from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Republica(models.Model):
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=200)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Republica'
        verbose_name_plural = 'Republicas'

    def __str__(self):
        return self.nome


class Morador(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='morador',
    )
    republica = models.ForeignKey(
        Republica,
        on_delete=models.CASCADE,
        related_name='moradores',
    )
    ativo = models.BooleanField(default=True)
    data_entrada = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Morador'
        verbose_name_plural = 'Moradores'

    def __str__(self):
        return f'{self.nome} - {self.republica.nome}'


class Despesa(models.Model):
    class Categoria(models.TextChoices):
        ALUGUEL = 'ALUGUEL', 'Aluguel'
        AGUA = 'AGUA', 'Agua'
        ENERGIA = 'ENERGIA', 'Energia'
        INTERNET = 'INTERNET', 'Internet'
        MERCADO = 'MERCADO', 'Mercado'
        LIMPEZA = 'LIMPEZA', 'Limpeza'
        OUTROS = 'OUTROS', 'Outros'

    republica = models.ForeignKey(
        Republica,
        on_delete=models.CASCADE,
        related_name='despesas',
    )
    titulo = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.OUTROS,
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    paga_por = models.ForeignKey(
        Morador,
        on_delete=models.PROTECT,
        related_name='despesas_pagas',
    )
    data_despesa = models.DateField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_despesa', '-id']
        verbose_name = 'Despesa'
        verbose_name_plural = 'Despesas'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_total__gt=0),
                name='despesa_valor_total_gt_zero',
            ),
        ]

    def clean(self):
        if self.paga_por_id and self.republica_id:
            if self.paga_por.republica_id != self.republica_id:
                raise ValidationError(
                    {'paga_por': 'O morador pagante precisa pertencer a mesma republica da despesa.'}
                )

    def __str__(self):
        return f'{self.titulo} - R$ {self.valor_total}'


class DivisaoDespesa(models.Model):
    despesa = models.ForeignKey(
        Despesa,
        on_delete=models.CASCADE,
        related_name='divisoes',
    )
    morador = models.ForeignKey(
        Morador,
        on_delete=models.CASCADE,
        related_name='divisoes_despesa',
    )
    valor_devido = models.DecimalField(max_digits=10, decimal_places=2)
    quitado = models.BooleanField(default=False)

    class Meta:
        ordering = ['morador__nome']
        verbose_name = 'Divisao de despesa'
        verbose_name_plural = 'Divisoes de despesa'
        constraints = [
            models.UniqueConstraint(
                fields=['despesa', 'morador'],
                name='unique_divisao_por_morador',
            ),
            models.CheckConstraint(
                condition=models.Q(valor_devido__gte=0),
                name='divisao_valor_devido_gte_zero',
            ),
        ]

    def clean(self):
        if self.despesa_id and self.morador_id:
            if self.despesa.republica_id != self.morador.republica_id:
                raise ValidationError(
                    {'morador': 'O morador precisa pertencer a mesma republica da despesa.'}
                )

    def __str__(self):
        return f'{self.morador.nome} deve R$ {self.valor_devido} em {self.despesa.titulo}'


class Pagamento(models.Model):
    republica = models.ForeignKey(
        Republica,
        on_delete=models.CASCADE,
        related_name='pagamentos',
    )
    pagador = models.ForeignKey(
        Morador,
        on_delete=models.PROTECT,
        related_name='pagamentos_realizados',
    )
    recebedor = models.ForeignKey(
        Morador,
        on_delete=models.PROTECT,
        related_name='pagamentos_recebidos',
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    referencia_despesa = models.ForeignKey(
        Despesa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos',
    )
    observacao = models.CharField(max_length=200, blank=True)
    data_pagamento = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_pagamento', '-id']
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gt=0),
                name='pagamento_valor_gt_zero',
            ),
        ]

    def _saldo_atual_morador(self, morador):
        total_pago_em_despesas = (
            morador.despesas_pagas.aggregate(total=models.Sum('valor_total'))['total']
            or Decimal('0.00')
        )
        total_devido = (
            morador.divisoes_despesa.aggregate(total=models.Sum('valor_devido'))['total']
            or Decimal('0.00')
        )

        pagamentos_realizados = morador.pagamentos_realizados.all()
        pagamentos_recebidos = morador.pagamentos_recebidos.all()
        if self.pk:
            pagamentos_realizados = pagamentos_realizados.exclude(pk=self.pk)
            pagamentos_recebidos = pagamentos_recebidos.exclude(pk=self.pk)

        total_pago_em_acertos = (
            pagamentos_realizados.aggregate(total=models.Sum('valor'))['total']
            or Decimal('0.00')
        )
        total_recebido_em_acertos = (
            pagamentos_recebidos.aggregate(total=models.Sum('valor'))['total']
            or Decimal('0.00')
        )

        return (
            total_pago_em_despesas
            - total_devido
            - total_recebido_em_acertos
            + total_pago_em_acertos
        )

    def clean(self):
        errors = {}

        if self.pagador_id and self.republica_id and self.pagador.republica_id != self.republica_id:
            errors['pagador'] = 'O pagador precisa pertencer a mesma republica.'

        if self.recebedor_id and self.republica_id and self.recebedor.republica_id != self.republica_id:
            errors['recebedor'] = 'O recebedor precisa pertencer a mesma republica.'

        if self.pagador_id and self.recebedor_id and self.pagador_id == self.recebedor_id:
            errors['recebedor'] = 'Pagador e recebedor nao podem ser a mesma pessoa.'

        if (
            self.referencia_despesa_id
            and self.republica_id
            and self.referencia_despesa.republica_id != self.republica_id
        ):
            errors['referencia_despesa'] = 'A despesa de referencia precisa ser da mesma republica.'

        if not errors and self.pagador_id and self.recebedor_id and self.valor:
            saldo_pagador = self._saldo_atual_morador(self.pagador)
            saldo_recebedor = self._saldo_atual_morador(self.recebedor)

            if saldo_pagador >= Decimal('0.00'):
                errors['pagador'] = 'O pagador precisa ter saldo negativo para registrar um acerto.'

            if saldo_recebedor <= Decimal('0.00'):
                errors['recebedor'] = 'O recebedor precisa ter saldo positivo para receber um acerto.'

            if not errors:
                limite = min(abs(saldo_pagador), saldo_recebedor)
                if self.valor > limite:
                    errors['valor'] = (
                        f'O valor do pagamento nao pode ser maior que R$ {limite:.2f} '
                        'para esse acerto.'
                    )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.pagador.nome} pagou R$ {self.valor} para {self.recebedor.nome}'


class Tarefa(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
        CONCLUIDA = 'CONCLUIDA', 'Concluida'

    class Prioridade(models.TextChoices):
        BAIXA = 'BAIXA', 'Baixa'
        MEDIA = 'MEDIA', 'Media'
        ALTA = 'ALTA', 'Alta'

    republica = models.ForeignKey(
        Republica,
        on_delete=models.CASCADE,
        related_name='tarefas',
    )
    titulo = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        Morador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarefas',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    prioridade = models.CharField(
        max_length=10,
        choices=Prioridade.choices,
        default=Prioridade.MEDIA,
    )
    data_limite = models.DateField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['status', 'data_limite', 'titulo']
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def clean(self):
        if self.responsavel_id and self.republica_id:
            if self.responsavel.republica_id != self.republica_id:
                raise ValidationError(
                    {'responsavel': 'O responsavel precisa pertencer a mesma republica da tarefa.'}
                )

    def __str__(self):
        return self.titulo
