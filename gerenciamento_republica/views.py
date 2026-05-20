from decimal import Decimal

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.db.models import F
from django.db.models import Q
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, PagamentoDivisao, Republica, Tarefa
from .serializers import (
    CadastroUsuarioSerializer,
    DashboardOverviewSerializer,
    DespesaSerializer,
    DivisaoDespesaSerializer,
    EntrarRepublicaSerializer,
    LoginSerializer,
    MoradorSerializer,
    PagamentoSerializer,
    PerfilUpdateSerializer,
    RepublicaResumoSerializer,
    RepublicaSerializer,
    TarefaSerializer,
    UsuarioSerializer,
)


def login_page(request):
    return render(request, 'gerenciamento_republica/login.html')


def cadastro_page(request):
    return render(request, 'gerenciamento_republica/cadastro.html')


def dashboard_page(request):
    return render(request, 'gerenciamento_republica/dashboard.html', {'page_key': 'dashboard'})


def financas_page(request):
    return render(request, 'gerenciamento_republica/financas.html', {'page_key': 'financas'})


def tarefas_page(request):
    return render(request, 'gerenciamento_republica/tarefas.html', {'page_key': 'tarefas'})


def perfil_page(request):
    return render(request, 'gerenciamento_republica/perfil.html', {'page_key': 'perfil'})


def get_user_republica(user):
    morador = get_user_morador(user)
    return morador.republica if morador else None


def get_user_morador(user):
    # O sistema considera apenas moradores ativos. Registros antigos ficam no
    # banco para preservar historico, mas nao representam vinculo atual.
    morador = getattr(user, 'morador', None)
    if not morador or not morador.ativo:
        return None
    return morador


def serializar_usuario_atualizado(user):
    user = user.__class__.objects.get(pk=user.pk)
    return UsuarioSerializer(user).data


def promover_novo_admin_se_necessario(republica):
    # Ao sair um admin, o sistema promove apenas moradores ativos com conta de
    # usuario. Isso evita criar um "admin fantasma" sem login.
    if republica.moradores.filter(ativo=True, eh_admin=True).exists():
        return None

    novo_admin = republica.moradores.filter(
        ativo=True,
        usuario__isnull=False,
    ).order_by('data_entrada', 'id').first()
    if not novo_admin:
        return None

    novo_admin.eh_admin = True
    novo_admin.save(update_fields=['eh_admin'])
    return novo_admin


def construir_resumo_financeiro_morador(morador):
    # O resumo separa responsabilidade pela conta de quem realmente anexou o
    # comprovante. Essa diferenca evita leituras incorretas no quadro financeiro.
    despesas_responsaveis = morador.despesas_pagas.filter(
        republica=morador.republica
    )
    total_assumido = despesas_responsaveis.aggregate(
        total=Coalesce(Sum('valor_total'), Decimal('0.00'))
    )['total']
    total_quitado = despesas_responsaveis.filter(
        status_pagamento=Despesa.StatusPagamento.PAGA
    ).aggregate(
        total=Coalesce(Sum('valor_total'), Decimal('0.00'))
    )['total']
    total_pendente = total_assumido - total_quitado
    total_pago_real = morador.despesas_quitadas.filter(
        republica=morador.republica,
        status_pagamento=Despesa.StatusPagamento.PAGA,
    ).aggregate(
        total=Coalesce(Sum('valor_total'), Decimal('0.00'))
    )['total']

    return {
        'id': morador.id,
        'nome': morador.nome,
        'total_pago_em_despesas': total_pago_real,
        'total_devido': total_assumido,
        'total_quitado': total_quitado,
        'total_pendente': total_pendente,
        'total_pago_em_acertos': Decimal('0.00'),
        'total_recebido_em_acertos': Decimal('0.00'),
        'total_credito_aberto': Decimal('0.00'),
        'saldo': total_quitado,
    }


class RepublicaScopedMixin:
    """Centraliza as regras de isolamento por republica nas APIs."""

    republica_lookup = 'republica'

    def get_user_republica(self):
        return get_user_republica(self.request.user)

    def get_user_morador(self):
        return get_user_morador(self.request.user)

    def get_required_user_republica(self):
        republica = self.get_user_republica()
        if not republica:
            raise ValidationError({'detail': 'Seu usuario precisa estar vinculado a uma republica.'})
        return republica

    def user_is_republic_admin(self, republica=None):
        # Staff e o poder tecnico global; admin da republica e o papel de negocio.
        if self.request.user.is_staff:
            return True

        morador = self.get_user_morador()
        if not morador or not morador.eh_admin:
            return False

        if republica is None:
            return True

        return morador.republica_id == republica.id

    def get_scoped_queryset(self, queryset):
        # Usuarios comuns enxergam apenas dados da propria republica.
        if self.request.user.is_staff:
            return queryset

        try:
            republica = self.get_required_user_republica()
        except ValidationError:
            return queryset.none()

        return queryset.filter(**{self.republica_lookup: republica})

    def validate_user_republica(self, republica):
        # Protecao contra acesso direto a IDs de outra republica pela API.
        if self.request.user.is_staff:
            return

        user_republica = self.get_user_republica()
        if not user_republica:
            raise PermissionDenied('Seu usuario nao esta vinculado a uma republica.')
        if republica.id != user_republica.id:
            raise PermissionDenied('Voce so pode acessar dados da sua propria republica.')

    def ensure_republic_admin(self, republica, message='Voce nao tem permissao para alterar esse recurso.'):
        # Usado antes de operacoes sensiveis, como alterar despesas ou moradores.
        if not self.user_is_republic_admin(republica):
            raise PermissionDenied(message)


class RepublicaViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RepublicaSerializer

    def get_queryset(self):
        queryset = Republica.objects.all()
        if self.request.user.is_staff:
            return queryset

        republica = self.get_user_republica()
        if not republica:
            return queryset.none()
        return queryset.filter(id=republica.id)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return

        # Quem cria uma republica pelo fluxo comum passa a ser o primeiro admin.
        if self.get_user_republica():
            raise ValidationError({'detail': 'Voce ja esta vinculado a uma republica.'})

        email = (self.request.user.email or '').strip()
        if not email:
            raise ValidationError({'detail': 'Seu usuario precisa ter um email para criar uma republica.'})

        republica = serializer.save()
        nome_morador = (
            self.request.user.get_full_name().strip()
            or self.request.user.first_name.strip()
            or self.request.user.username
        )
        Morador.objects.create(
            nome=nome_morador,
            email=email,
            usuario=self.request.user,
            republica=republica,
            eh_admin=True,
        )

    def perform_update(self, serializer):
        self.validate_user_republica(serializer.instance)
        self.ensure_republic_admin(
            serializer.instance,
            'A republica so pode ser alterada pelo administrador da republica.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        self.validate_user_republica(instance)
        self.ensure_republic_admin(
            instance,
            'A republica so pode ser removida pelo administrador da republica.',
        )
        instance.delete()


class MoradorViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MoradorSerializer

    def get_queryset(self):
        queryset = Morador.objects.select_related('republica', 'usuario').all()
        return self.get_scoped_queryset(queryset)

    def update(self, request, *args, **kwargs):
        morador = self.get_object()
        if not self.user_is_republic_admin(morador.republica):
            raise PermissionDenied('Somente o administrador da republica pode alterar moradores pela API.')
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        morador = self.get_object()
        if not self.user_is_republic_admin(morador.republica):
            raise PermissionDenied('Somente o administrador da republica pode alterar moradores pela API.')
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        republica = self.get_required_user_republica()
        serializer.save(republica=republica, eh_admin=False)

    def perform_update(self, serializer):
        morador = self.get_object()
        self.validate_user_republica(morador.republica)
        self.ensure_republic_admin(
            morador.republica,
            'Somente o administrador da republica pode alterar moradores pela API.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        self.validate_user_republica(instance.republica)
        self.ensure_republic_admin(
            instance.republica,
            'Somente o administrador da republica pode remover moradores pela API.',
        )
        instance.delete()


class DespesaViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DespesaSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        queryset = (
            Despesa.objects.select_related('republica', 'paga_por')
            .prefetch_related('divisoes', 'divisoes__morador')
            .all()
        )
        return self.get_scoped_queryset(queryset)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        republica = self.get_required_user_republica()
        # No fluxo atual, apenas o admin da republica cadastra novas contas.
        self.ensure_republic_admin(
            republica,
            'Somente o administrador da republica pode cadastrar despesas.',
        )
        serializer.save(republica=republica)

    def _usuario_pode_quitar_despesa(self, despesa, campos_alterados):
        # Morador comum nao edita a despesa inteira; ele so registra pagamento
        # da conta que esta atribuida a ele.
        morador = self.get_user_morador()
        if (
            not morador
            or morador.republica_id != despesa.republica_id
            or morador.id != despesa.paga_por_id
        ):
            return False

        campos_permitidos = {
            'status_pagamento',
            'data_pagamento',
            'comprovante_pagamento',
            'quitada_por',
        }
        return not (campos_alterados - campos_permitidos)

    def perform_update(self, serializer):
        despesa = self.get_object()
        self.validate_user_republica(despesa.republica)
        campos_alterados = set(serializer.validated_data.keys())
        morador_atual = self.get_user_morador()
        # Se o pagamento vem do morador logado, registramos quem quitou sem
        # depender de campo enviado pelo frontend.
        marcando_como_paga = (
            serializer.validated_data.get('status_pagamento') == Despesa.StatusPagamento.PAGA
        )
        quitada_por_informado = 'quitada_por' in serializer.validated_data

        save_kwargs = {}
        if marcando_como_paga and not quitada_por_informado and morador_atual:
            save_kwargs['quitada_por'] = morador_atual

        if self.user_is_republic_admin(despesa.republica):
            serializer.save(**save_kwargs)
            return

        if not self._usuario_pode_quitar_despesa(despesa, campos_alterados):
            raise PermissionDenied(
                'Somente o administrador da republica pode editar despesas. O morador responsavel pela conta pode apenas registrar o pagamento e anexar o comprovante.'
            )

        serializer.save(republica=despesa.republica, **save_kwargs)

    def perform_destroy(self, instance):
        self.validate_user_republica(instance.republica)
        self.ensure_republic_admin(
            instance.republica,
            'Somente o administrador da republica pode remover despesas.',
        )
        instance.delete()


class DivisaoDespesaViewSet(RepublicaScopedMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DivisaoDespesaSerializer
    republica_lookup = 'despesa__republica'

    def get_queryset(self):
        queryset = DivisaoDespesa.objects.select_related('despesa', 'despesa__paga_por', 'morador').all()
        return self.get_scoped_queryset(queryset)


class PagamentoViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PagamentoSerializer

    def get_queryset(self):
        queryset = (
            Pagamento.objects.select_related(
                'republica',
                'pagador',
                'recebedor',
                'referencia_despesa',
            )
            .prefetch_related('itens', 'itens__divisao', 'itens__divisao__despesa')
            .all()
        )
        return self.get_scoped_queryset(queryset)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_required_user_republica())

    def perform_update(self, serializer):
        pagamento = self.get_object()
        self.validate_user_republica(pagamento.republica)
        self.ensure_republic_admin(
            pagamento.republica,
            'Somente o administrador da republica pode editar pagamentos.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        self.validate_user_republica(instance.republica)
        self.ensure_republic_admin(
            instance.republica,
            'Somente o administrador da republica pode remover pagamentos.',
        )
        instance.delete()


class TarefaViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TarefaSerializer

    def get_queryset(self):
        queryset = Tarefa.objects.select_related('republica', 'responsavel').all()
        return self.get_scoped_queryset(queryset)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_required_user_republica())

    def perform_update(self, serializer):
        tarefa = self.get_object()
        self.validate_user_republica(tarefa.republica)
        if self.user_is_republic_admin(tarefa.republica):
            serializer.save()
            return

        # Para simplificar o MVP, morador comum pode organizar o andamento, mas
        # nao altera titulo, responsavel ou prazo de uma tarefa.
        campos_alterados = set(serializer.validated_data.keys())
        if campos_alterados - {'status'}:
            raise PermissionDenied(
                'Usuarios comuns so podem atualizar o status das tarefas.'
            )
        serializer.save(republica=self.get_required_user_republica())

    def perform_destroy(self, instance):
        self.validate_user_republica(instance.republica)
        self.ensure_republic_admin(
            instance.republica,
            'Somente o administrador da republica pode remover tarefas.',
        )
        instance.delete()


class RepublicaResumoFinanceiroView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        republica = get_object_or_404(Republica, pk=pk)
        if not request.user.is_staff:
            user_republica = get_user_republica(request.user)
            if not user_republica or user_republica.id != republica.id:
                raise PermissionDenied('Voce so pode acessar o resumo da sua propria republica.')
        moradores = republica.moradores.filter(ativo=True).order_by('nome')

        total_despesas = republica.despesas.aggregate(
            total=Coalesce(Sum('valor_total'), Decimal('0.00'))
        )['total']
        total_quitado = republica.despesas.filter(
            status_pagamento=Despesa.StatusPagamento.PAGA
        ).aggregate(
            total=Coalesce(Sum('valor_total'), Decimal('0.00'))
        )['total']
        total_pendente = total_despesas - total_quitado

        resumo_moradores = [
            construir_resumo_financeiro_morador(morador)
            for morador in moradores
        ]

        serializer = RepublicaResumoSerializer(
            {
                'id': republica.id,
                'nome': republica.nome,
                'total_despesas': total_despesas,
                'total_quitado': total_quitado,
                'total_pendente': total_pendente,
                'moradores': resumo_moradores,
            }
        )
        return Response(serializer.data)


class DashboardOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        republica = get_user_republica(request.user)
        if not republica:
            return Response(
                {
                    'detail': 'Seu usuario ainda nao esta vinculado a uma republica.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        ultimas_despesas = list(
            republica.despesas.select_related('paga_por').prefetch_related('divisoes')[:5]
        )
        tarefas_pendentes = list(
            republica.tarefas.select_related('responsavel')
            .filter(~Q(status=Tarefa.Status.CONCLUIDA))[:5]
        )
        total_despesas = republica.despesas.aggregate(
            total=Coalesce(Sum('valor_total'), Decimal('0.00'))
        )['total']
        total_moradores = republica.moradores.filter(ativo=True).aggregate(total=Count('id'))['total']
        total_tarefas_pendentes = republica.tarefas.filter(~Q(status=Tarefa.Status.CONCLUIDA)).count()

        serializer = DashboardOverviewSerializer(
            {
                'republica': republica,
                'total_moradores': total_moradores,
                'total_despesas': total_despesas,
                'total_tarefas_pendentes': total_tarefas_pendentes,
                'ultimas_despesas': ultimas_despesas,
                'tarefas_pendentes': tarefas_pendentes,
            }
        )
        return Response(serializer.data)


class CadastroUsuarioView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CadastroUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resultado = serializer.save()

        return Response(
            {
                'token': resultado['token'],
                'user': UsuarioSerializer(resultado['user']).data,
                'morador_id': resultado['morador'].id if resultado['morador'] else None,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                'token': token.key,
                'user': UsuarioSerializer(user).data,
            }
        )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        serializer = PerfilUpdateSerializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UsuarioSerializer(user).data)

    @transaction.atomic
    def delete(self, request):
        # Excluir a conta remove o login, mas nao apaga o morador antigo. Isso
        # preserva historico de despesas, tarefas e comprovantes da republica.
        user = request.user
        morador = get_user_morador(user)

        if morador:
            republica = morador.republica
            era_admin = morador.eh_admin
            # Um admin so pode excluir a conta se houver outro morador ativo,
            # com usuario vinculado, capaz de assumir a administracao.
            tem_substituto_admin = republica.moradores.filter(
                ativo=True,
                usuario__isnull=False,
            ).exclude(pk=morador.pk).exists()

            if era_admin and not tem_substituto_admin:
                raise ValidationError(
                    {
                        'detail': (
                            'Antes de excluir sua conta, vincule outro morador com conta de usuario '
                            'para assumir como administrador.'
                        )
                    }
                )

            morador.usuario = None
            morador.ativo = False
            morador.eh_admin = False
            morador.save(update_fields=['usuario', 'ativo', 'eh_admin'])

            if era_admin:
                # A promocao automatica e uma protecao extra caso a tela nao
                # tenha transferido o papel antes da exclusao.
                promover_novo_admin_se_necessario(republica)

        # Depois da exclusao, tokens antigos deixam de ser validos.
        Token.objects.filter(user=user).delete()
        logout(request)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SairRepublicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        morador = get_user_morador(request.user)
        if not morador:
            raise ValidationError({'detail': 'Seu usuario nao esta vinculado a uma republica.'})

        republica = morador.republica
        era_admin = morador.eh_admin
        tem_substituto_admin = republica.moradores.filter(
            ativo=True,
            usuario__isnull=False,
        ).exclude(pk=morador.pk).exists()

        if era_admin and not tem_substituto_admin:
            # A saida do ultimo admin com login e bloqueada para nao deixar a
            # republica sem responsavel operacional.
            raise ValidationError(
                {
                    'detail': (
                        'Antes de sair da republica, vincule outro morador com conta de usuario '
                        'para assumir como administrador.'
                    )
                }
            )

        morador.usuario = None
        morador.ativo = False
        morador.eh_admin = False
        morador.save(update_fields=['usuario', 'ativo', 'eh_admin'])

        if era_admin:
            promover_novo_admin_se_necessario(republica)

        return Response(serializar_usuario_atualizado(request.user))


class TransferirAdminView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # Transferencia de admin e uma regra sensivel: apenas o admin atual da
        # propria republica pode escolher o substituto.
        morador_atual = get_user_morador(request.user)
        if not morador_atual or not morador_atual.eh_admin:
            raise PermissionDenied('Somente o administrador atual pode transferir a administracao.')

        novo_admin_id = request.data.get('morador_id')
        if not novo_admin_id:
            raise ValidationError({'morador_id': 'Escolha o morador que vai assumir como administrador.'})

        novo_admin = get_object_or_404(
            Morador.objects.select_related('republica', 'usuario'),
            pk=novo_admin_id,
            republica=morador_atual.republica,
            ativo=True,
        )

        # O novo admin precisa ser outra pessoa e precisa conseguir acessar o
        # sistema com uma conta propria.
        if novo_admin.pk == morador_atual.pk:
            raise ValidationError({'morador_id': 'Escolha outro morador para assumir a administracao.'})

        if not novo_admin.usuario_id:
            raise ValidationError({'morador_id': 'O novo administrador precisa ter uma conta de usuario vinculada.'})

        # Mantemos apenas um administrador de negocio por republica para evitar
        # conflito na demonstracao e nas regras de permissao.
        Morador.objects.filter(republica=morador_atual.republica, eh_admin=True).update(eh_admin=False)
        novo_admin.eh_admin = True
        novo_admin.save(update_fields=['eh_admin'])

        return Response(
            {
                'detail': 'Administracao transferida com sucesso.',
                'novo_admin': MoradorSerializer(novo_admin).data,
                'user': serializar_usuario_atualizado(request.user),
            }
        )


class EntrarRepublicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # O usuario so pode entrar em uma nova republica depois de sair da atual.
        if get_user_morador(request.user):
            raise ValidationError(
                {'detail': 'Saia da republica atual antes de entrar em outra.'}
            )

        serializer = EntrarRepublicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        republica = serializer.validated_data['republica']
        email = (request.user.email or '').strip()
        if not email:
            raise ValidationError({'detail': 'Seu usuario precisa ter um email para entrar em uma republica.'})

        nome_morador = (
            request.user.get_full_name().strip()
            or request.user.first_name.strip()
            or request.user.username
        )
        Morador.objects.create(
            nome=nome_morador,
            email=email,
            usuario=request.user,
            republica=republica,
            eh_admin=False,
        )

        return Response(serializar_usuario_atualizado(request.user), status=status.HTTP_201_CREATED)
