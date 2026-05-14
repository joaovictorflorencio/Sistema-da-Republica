from decimal import Decimal, ROUND_DOWN

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import (
    Despesa,
    DivisaoDespesa,
    Morador,
    Pagamento,
    PagamentoDivisao,
    Republica,
    Tarefa,
)

User = get_user_model()


def _build_instance(serializer, model_class, attrs):
    if serializer.instance is None:
        return model_class(**attrs)

    data = {}
    for field in model_class._meta.fields:
        if field.name == 'id':
            continue
        data[field.name] = getattr(serializer.instance, field.name)
    data.update(attrs)
    instance = model_class(**data)
    instance.pk = serializer.instance.pk
    instance._state.adding = False
    return instance


class RepublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Republica
        fields = ['id', 'nome', 'endereco', 'criada_em']
        read_only_fields = ['id', 'criada_em']


class UsuarioSerializer(serializers.ModelSerializer):
    morador_id = serializers.IntegerField(source='morador.id', read_only=True)
    morador_nome = serializers.CharField(source='morador.nome', read_only=True)
    morador_eh_admin = serializers.BooleanField(source='morador.eh_admin', read_only=True)
    republica_id = serializers.IntegerField(source='morador.republica.id', read_only=True)
    republica_nome = serializers.CharField(source='morador.republica.nome', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'morador_id',
            'morador_nome',
            'morador_eh_admin',
            'republica_id',
            'republica_nome',
        ]
        read_only_fields = fields


class CadastroUsuarioSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    nome = serializers.CharField(max_length=100)
    republica = serializers.PrimaryKeyRelatedField(
        queryset=Republica.objects.all(),
        required=False,
        allow_null=True,
    )
    nova_republica_nome = serializers.CharField(max_length=100, required=False, allow_blank=True)
    nova_republica_endereco = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Ja existe um usuario com esse username.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ja existe um usuario com esse email.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'As senhas precisam ser iguais.'})

        republica = attrs.get('republica')
        nova_republica_nome = (attrs.get('nova_republica_nome') or '').strip()
        nova_republica_endereco = (attrs.get('nova_republica_endereco') or '').strip()

        if republica and (nova_republica_nome or nova_republica_endereco):
            raise serializers.ValidationError(
                {'detail': 'Escolha entre entrar em uma republica existente ou criar uma nova.'}
            )

        if nova_republica_nome and not nova_republica_endereco:
            raise serializers.ValidationError(
                {'nova_republica_endereco': 'Informe o endereco da nova republica.'}
            )

        if nova_republica_endereco and not nova_republica_nome:
            raise serializers.ValidationError(
                {'nova_republica_nome': 'Informe o nome da nova republica.'}
            )

        user = User(
            username=attrs['username'],
            email=attrs['email'],
            first_name=attrs['nome'],
        )
        password_validation.validate_password(attrs['password'], user=user)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        republica = validated_data.pop('republica', None)
        nova_republica_nome = validated_data.pop('nova_republica_nome', '').strip()
        nova_republica_endereco = validated_data.pop('nova_republica_endereco', '').strip()
        nome = validated_data.pop('nome')
        password = validated_data.pop('password')

        if nova_republica_nome:
            republica = Republica.objects.create(
                nome=nova_republica_nome,
                endereco=nova_republica_endereco,
            )

        user = User.objects.create_user(
            first_name=nome,
            password=password,
            **validated_data,
        )

        morador = None
        if republica is not None:
            morador = Morador.objects.create(
                nome=nome,
                email=user.email,
                usuario=user,
                republica=republica,
                eh_admin=bool(nova_republica_nome),
            )

        token, _ = Token.objects.get_or_create(user=user)
        return {'user': user, 'token': token.key, 'morador': morador}


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('username') or attrs.get('email')
        if not identifier:
            raise serializers.ValidationError({'detail': 'Informe username ou email.'})

        username = attrs.get('username')
        if attrs.get('email'):
            user = User.objects.filter(email__iexact=attrs['email']).first()
            username = user.username if user else None

        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=attrs.get('password'),
        )
        if not user:
            raise serializers.ValidationError({'detail': 'Email/username ou senha invalidos.'})
        attrs['user'] = user
        return attrs


class MoradorSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = Morador
        fields = [
            'id',
            'nome',
            'email',
            'usuario',
            'usuario_username',
            'republica',
            'ativo',
            'eh_admin',
            'data_entrada',
        ]
        read_only_fields = ['id', 'usuario', 'usuario_username']

    def validate(self, attrs):
        if (
            self.instance
            and 'republica' in attrs
            and attrs['republica'].id != self.instance.republica_id
        ):
            raise serializers.ValidationError(
                {'republica': 'Nao e permitido mover um morador para outra republica por edicao.'}
            )
        instance = _build_instance(self, Morador, attrs)
        instance.full_clean()
        return attrs


class DivisaoDespesaSerializer(serializers.ModelSerializer):
    morador_nome = serializers.CharField(source='morador.nome', read_only=True)
    despesa_titulo = serializers.CharField(source='despesa.titulo', read_only=True)
    despesa_categoria = serializers.CharField(source='despesa.categoria', read_only=True)
    despesa_data = serializers.DateField(source='despesa.data_despesa', read_only=True)
    credor_nome = serializers.CharField(source='despesa.paga_por.nome', read_only=True)
    saldo_aberto = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DivisaoDespesa
        fields = [
            'id',
            'despesa',
            'despesa_titulo',
            'despesa_categoria',
            'despesa_data',
            'morador',
            'morador_nome',
            'credor_nome',
            'valor_devido',
            'valor_pago',
            'saldo_aberto',
            'status',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        instance = _build_instance(self, DivisaoDespesa, attrs)
        instance.full_clean()
        return attrs


class DespesaSerializer(serializers.ModelSerializer):
    divisoes = DivisaoDespesaSerializer(many=True, read_only=True)
    paga_por_nome = serializers.CharField(source='paga_por.nome', read_only=True)
    quitada_por_nome = serializers.CharField(source='quitada_por.nome', read_only=True)
    participantes_count = serializers.SerializerMethodField()
    valor_em_aberto = serializers.SerializerMethodField()
    valor_quitado = serializers.SerializerMethodField()
    comprovante_url = serializers.SerializerMethodField()
    morador_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=False,
        help_text='Lista de moradores que participam da divisao. Se omitida, usa todos os moradores ativos.',
    )

    class Meta:
        model = Despesa
        fields = [
            'id',
            'republica',
            'titulo',
            'descricao',
            'categoria',
            'valor_total',
            'paga_por',
            'paga_por_nome',
            'quitada_por',
            'quitada_por_nome',
            'data_vencimento',
            'data_despesa',
            'status_pagamento',
            'data_pagamento',
            'comprovante_pagamento',
            'comprovante_url',
            'criada_em',
            'participantes_count',
            'valor_em_aberto',
            'valor_quitado',
            'morador_ids',
            'divisoes',
        ]
        read_only_fields = ['id', 'criada_em', 'divisoes', 'comprovante_url', 'quitada_por_nome']

    def get_participantes_count(self, obj):
        return obj.divisoes.count()

    def get_valor_em_aberto(self, obj):
        total = sum(
            divisao.saldo_aberto
            for divisao in obj.divisoes.all()
            if divisao.morador_id != obj.paga_por_id
        )
        return total

    def get_valor_quitado(self, obj):
        return obj.valor_total - self.get_valor_em_aberto(obj)

    def get_comprovante_url(self, obj):
        if not obj.comprovante_pagamento:
            return None

        request = self.context.get('request')
        url = obj.comprovante_pagamento.url
        return request.build_absolute_uri(url) if request else url

    def validate(self, attrs):
        morador_ids = attrs.pop('morador_ids', None)

        if (
            'status_pagamento' not in attrs
            and ('data_pagamento' in attrs or 'comprovante_pagamento' in attrs)
        ):
            attrs['status_pagamento'] = Despesa.StatusPagamento.PAGA

        instance = _build_instance(self, Despesa, attrs)
        instance.full_clean()

        status_pagamento = attrs.get(
            'status_pagamento',
            self.instance.status_pagamento if self.instance else Despesa.StatusPagamento.PENDENTE,
        )
        data_pagamento = attrs.get(
            'data_pagamento',
            self.instance.data_pagamento if self.instance else None,
        )
        comprovante_pagamento = attrs.get(
            'comprovante_pagamento',
            self.instance.comprovante_pagamento if self.instance else None,
        )

        if status_pagamento == Despesa.StatusPagamento.PAGA:
            if not data_pagamento:
                raise serializers.ValidationError(
                    {'data_pagamento': 'Informe a data em que a conta foi paga.'}
                )
            if not comprovante_pagamento:
                raise serializers.ValidationError(
                    {'comprovante_pagamento': 'Anexe o comprovante do pagamento.'}
                )
        elif 'status_pagamento' in attrs and status_pagamento == Despesa.StatusPagamento.PENDENTE:
            attrs['data_pagamento'] = None
            attrs['comprovante_pagamento'] = None
            attrs['quitada_por'] = None

        participantes = None
        republica = instance.republica
        if morador_ids is not None:
            participantes = list(Morador.objects.filter(id__in=morador_ids, ativo=True).order_by('id'))
            if len(participantes) != len(set(morador_ids)):
                raise serializers.ValidationError(
                    {'morador_ids': 'Um ou mais moradores informados nao existem ou estao inativos.'}
                )
        elif self.instance is None:
            participantes = list(republica.moradores.filter(ativo=True).order_by('id'))

        if participantes is not None and not participantes:
            raise serializers.ValidationError(
                {'morador_ids': 'Informe pelo menos um morador para dividir a despesa.'}
            )

        if participantes is not None:
            ids_invalidos = [morador.id for morador in participantes if morador.republica_id != republica.id]
            if ids_invalidos:
                raise serializers.ValidationError(
                    {'morador_ids': 'Todos os moradores da divisao precisam ser da mesma republica.'}
                )

        if self.instance and PagamentoDivisao.objects.filter(divisao__despesa=self.instance).exists():
            campos_sensiveis = {'valor_total', 'paga_por', 'republica'}
            if morador_ids is not None or (set(attrs.keys()) & campos_sensiveis):
                raise serializers.ValidationError(
                    {'detail': 'Nao e possivel alterar a estrutura financeira de uma despesa que ja possui pagamentos aplicados.'}
                )

        if participantes is not None:
            attrs['morador_ids'] = [morador.id for morador in participantes]
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        morador_ids = validated_data.pop('morador_ids')
        despesa = Despesa.objects.create(**validated_data)
        self._criar_divisoes(despesa, morador_ids)
        return despesa

    @transaction.atomic
    def update(self, instance, validated_data):
        morador_ids = validated_data.pop('morador_ids', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()

        if morador_ids is not None:
            instance.divisoes.all().delete()
            self._criar_divisoes(instance, morador_ids)

        return instance

    def _criar_divisoes(self, despesa, morador_ids):
        participantes = list(Morador.objects.filter(id__in=morador_ids).order_by('id'))
        quantidade = len(participantes)
        valor_total = despesa.valor_total
        base = (valor_total / quantidade).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        restante = valor_total - (base * quantidade)

        divisoes = []
        for indice, morador in enumerate(participantes):
            acrescimo = Decimal('0.01') if Decimal(indice) < (restante * 100) else Decimal('0.00')
            valor_devido = base + acrescimo
            valor_pago = valor_devido if morador.id == despesa.paga_por_id else Decimal('0.00')
            divisoes.append(
                DivisaoDespesa(
                    despesa=despesa,
                    morador=morador,
                    valor_devido=valor_devido,
                    valor_pago=valor_pago,
                    status=(
                        DivisaoDespesa.Status.QUITADO
                        if valor_pago == valor_devido
                        else DivisaoDespesa.Status.PENDENTE
                    ),
                )
            )

        DivisaoDespesa.objects.bulk_create(divisoes)


class PagamentoDivisaoSerializer(serializers.ModelSerializer):
    despesa_id = serializers.IntegerField(source='divisao.despesa.id', read_only=True)
    despesa_titulo = serializers.CharField(source='divisao.despesa.titulo', read_only=True)
    morador_nome = serializers.CharField(source='divisao.morador.nome', read_only=True)

    class Meta:
        model = PagamentoDivisao
        fields = [
            'id',
            'divisao',
            'despesa_id',
            'despesa_titulo',
            'morador_nome',
            'valor_aplicado',
        ]
        read_only_fields = fields


class PagamentoSerializer(serializers.ModelSerializer):
    pagador_nome = serializers.CharField(source='pagador.nome', read_only=True)
    recebedor_nome = serializers.CharField(source='recebedor.nome', read_only=True)
    referencia_despesa_titulo = serializers.CharField(source='referencia_despesa.titulo', read_only=True)
    itens = PagamentoDivisaoSerializer(many=True, read_only=True)

    class Meta:
        model = Pagamento
        fields = [
            'id',
            'republica',
            'pagador',
            'pagador_nome',
            'recebedor',
            'recebedor_nome',
            'valor',
            'referencia_despesa',
            'referencia_despesa_titulo',
            'observacao',
            'data_pagamento',
            'criado_em',
            'itens',
        ]
        read_only_fields = ['id', 'criado_em', 'referencia_despesa_titulo', 'itens']

    def _mapear_aplicacoes_atuais(self):
        if not self.instance:
            return {}
        return {
            item.divisao_id: item.valor_aplicado
            for item in self.instance.itens.select_related('divisao')
        }

    def _obter_divisoes_alvo(self, instance):
        query = (
            DivisaoDespesa.objects.select_related('despesa', 'morador', 'despesa__paga_por')
            .filter(
                despesa__republica=instance.republica,
                morador=instance.pagador,
                despesa__paga_por=instance.recebedor,
            )
            .order_by('despesa__data_despesa', 'despesa_id', 'id')
        )
        if instance.referencia_despesa_id:
            query = query.filter(despesa=instance.referencia_despesa)
        return list(query)

    def _construir_aplicacoes(self, instance):
        aplicacoes_atuais = self._mapear_aplicacoes_atuais()
        divisoes = self._obter_divisoes_alvo(instance)
        if not divisoes:
            raise serializers.ValidationError(
                {'detail': 'Nao existem divisoes em aberto entre esse pagador e recebedor.'}
            )

        restante = instance.valor
        aplicacoes = []
        total_disponivel = Decimal('0.00')

        for divisao in divisoes:
            disponivel = divisao.saldo_aberto + aplicacoes_atuais.get(divisao.id, Decimal('0.00'))
            if disponivel <= Decimal('0.00'):
                continue
            total_disponivel += disponivel
            valor_aplicado = min(restante, disponivel)
            if valor_aplicado > Decimal('0.00'):
                aplicacoes.append(
                    {
                        'divisao': divisao,
                        'valor_aplicado': valor_aplicado,
                    }
                )
                restante -= valor_aplicado
            if restante <= Decimal('0.00'):
                break

        if not aplicacoes:
            raise serializers.ValidationError(
                {'detail': 'Nao ha saldo pendente para aplicar nesse pagamento.'}
            )

        if restante > Decimal('0.00'):
            raise serializers.ValidationError(
                {
                    'valor': (
                        f'O valor do pagamento nao pode ser maior que R$ {total_disponivel:.2f} '
                        'para esse acerto.'
                    )
                }
            )

        return aplicacoes

    def _aplicar_pagamento(self, pagamento, aplicacoes):
        itens = []
        for aplicacao in aplicacoes:
            divisao = aplicacao['divisao']
            valor_aplicado = aplicacao['valor_aplicado']
            divisao.valor_pago += valor_aplicado
            divisao.save(update_fields=['valor_pago', 'status'])
            itens.append(
                PagamentoDivisao(
                    pagamento=pagamento,
                    divisao=divisao,
                    valor_aplicado=valor_aplicado,
                )
            )
        PagamentoDivisao.objects.bulk_create(itens)

    def _desfazer_pagamento(self, pagamento):
        for item in pagamento.itens.select_related('divisao'):
            divisao = item.divisao
            divisao.valor_pago -= item.valor_aplicado
            if divisao.valor_pago < Decimal('0.00'):
                divisao.valor_pago = Decimal('0.00')
            divisao.save(update_fields=['valor_pago', 'status'])
        pagamento.itens.all().delete()

    def validate(self, attrs):
        instance = _build_instance(self, Pagamento, attrs)
        instance.full_clean()
        attrs['_aplicacoes'] = self._construir_aplicacoes(instance)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        aplicacoes = validated_data.pop('_aplicacoes')
        pagamento = Pagamento.objects.create(**validated_data)
        self._aplicar_pagamento(pagamento, aplicacoes)
        return pagamento

    @transaction.atomic
    def update(self, instance, validated_data):
        aplicacoes = validated_data.pop('_aplicacoes')
        self._desfazer_pagamento(instance)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        self._aplicar_pagamento(instance, aplicacoes)
        return instance


class TarefaSerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source='responsavel.nome', read_only=True)

    class Meta:
        model = Tarefa
        fields = [
            'id',
            'republica',
            'titulo',
            'descricao',
            'responsavel',
            'responsavel_nome',
            'status',
            'prioridade',
            'data_limite',
            'concluida_em',
            'criada_em',
        ]
        read_only_fields = ['id', 'criada_em']

    def validate(self, attrs):
        if (
            self.instance
            and 'republica' in attrs
            and attrs['republica'].id != self.instance.republica_id
        ):
            raise serializers.ValidationError(
                {'republica': 'Nao e permitido mover uma tarefa para outra republica por edicao.'}
            )
        instance = _build_instance(self, Tarefa, attrs)
        instance.full_clean()
        return attrs

    def create(self, validated_data):
        if validated_data.get('status') == Tarefa.Status.CONCLUIDA and not validated_data.get('concluida_em'):
            validated_data['concluida_em'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        novo_status = validated_data.get('status', instance.status)
        if novo_status == Tarefa.Status.CONCLUIDA and not validated_data.get('concluida_em'):
            validated_data['concluida_em'] = instance.concluida_em or timezone.now()
        if novo_status != Tarefa.Status.CONCLUIDA:
            validated_data['concluida_em'] = None
        return super().update(instance, validated_data)


class ResumoMoradorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_pago_em_despesas = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_devido = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_quitado = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_pendente = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_pago_em_acertos = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_recebido_em_acertos = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_credito_aberto = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=10, decimal_places=2)


class RepublicaResumoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_despesas = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_quitado = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_pendente = serializers.DecimalField(max_digits=10, decimal_places=2)
    moradores = ResumoMoradorSerializer(many=True)


class DashboardOverviewSerializer(serializers.Serializer):
    republica = RepublicaSerializer()
    total_moradores = serializers.IntegerField()
    total_despesas = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_tarefas_pendentes = serializers.IntegerField()
    ultimas_despesas = DespesaSerializer(many=True)
    tarefas_pendentes = TarefaSerializer(many=True)
