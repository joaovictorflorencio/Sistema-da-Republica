from decimal import Decimal, ROUND_DOWN

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, Republica, Tarefa

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
    return model_class(**data)


class RepublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Republica
        fields = ['id', 'nome', 'endereco', 'criada_em']
        read_only_fields = ['id', 'criada_em']


class UsuarioSerializer(serializers.ModelSerializer):
    morador_id = serializers.IntegerField(source='morador.id', read_only=True)
    morador_nome = serializers.CharField(source='morador.nome', read_only=True)
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
            'data_entrada',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        instance = _build_instance(self, Morador, attrs)
        instance.full_clean()
        return attrs


class DivisaoDespesaSerializer(serializers.ModelSerializer):
    morador_nome = serializers.CharField(source='morador.nome', read_only=True)

    class Meta:
        model = DivisaoDespesa
        fields = ['id', 'despesa', 'morador', 'morador_nome', 'valor_devido', 'quitado']
        read_only_fields = ['id']

    def validate(self, attrs):
        instance = _build_instance(self, DivisaoDespesa, attrs)
        instance.full_clean()
        return attrs


class DespesaSerializer(serializers.ModelSerializer):
    divisoes = DivisaoDespesaSerializer(many=True, read_only=True)
    paga_por_nome = serializers.CharField(source='paga_por.nome', read_only=True)
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
            'data_despesa',
            'criada_em',
            'morador_ids',
            'divisoes',
        ]
        read_only_fields = ['id', 'criada_em', 'divisoes']

    def validate(self, attrs):
        morador_ids = attrs.pop('morador_ids', None)
        instance = _build_instance(self, Despesa, attrs)
        instance.full_clean()

        republica = instance.republica
        if morador_ids is None:
            participantes = list(republica.moradores.filter(ativo=True).order_by('id'))
        else:
            participantes = list(Morador.objects.filter(id__in=morador_ids).order_by('id'))
            if len(participantes) != len(set(morador_ids)):
                raise serializers.ValidationError(
                    {'morador_ids': 'Um ou mais moradores informados nao existem.'}
                )

        if not participantes:
            raise serializers.ValidationError(
                {'morador_ids': 'Informe pelo menos um morador para dividir a despesa.'}
            )

        ids_invalidos = [morador.id for morador in participantes if morador.republica_id != republica.id]
        if ids_invalidos:
            raise serializers.ValidationError(
                {'morador_ids': 'Todos os moradores da divisao precisam ser da mesma republica.'}
            )

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
            divisoes.append(
                DivisaoDespesa(
                    despesa=despesa,
                    morador=morador,
                    valor_devido=base + acrescimo,
                )
            )

        DivisaoDespesa.objects.bulk_create(divisoes)


class PagamentoSerializer(serializers.ModelSerializer):
    pagador_nome = serializers.CharField(source='pagador.nome', read_only=True)
    recebedor_nome = serializers.CharField(source='recebedor.nome', read_only=True)

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
            'observacao',
            'data_pagamento',
            'criado_em',
        ]
        read_only_fields = ['id', 'criado_em']

    def validate(self, attrs):
        instance = _build_instance(self, Pagamento, attrs)
        instance.full_clean()
        return attrs


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
    total_pago_em_acertos = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_recebido_em_acertos = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=10, decimal_places=2)


class RepublicaResumoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_despesas = serializers.DecimalField(max_digits=10, decimal_places=2)
    moradores = ResumoMoradorSerializer(many=True)


class DashboardOverviewSerializer(serializers.Serializer):
    republica = RepublicaSerializer()
    total_moradores = serializers.IntegerField()
    total_despesas = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_tarefas_pendentes = serializers.IntegerField()
    ultimas_despesas = DespesaSerializer(many=True)
    tarefas_pendentes = TarefaSerializer(many=True)
