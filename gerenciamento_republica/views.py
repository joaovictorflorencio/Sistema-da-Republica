from decimal import Decimal

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
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
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, PagamentoDivisao, Republica, Tarefa
from .serializers import (
    CadastroUsuarioSerializer,
    DashboardOverviewSerializer,
    DespesaSerializer,
    DivisaoDespesaSerializer,
    LoginSerializer,
    MoradorSerializer,
    PagamentoSerializer,
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


def get_user_republica(user):
    morador = getattr(user, 'morador', None)
    return morador.republica if morador else None


def get_user_morador(user):
    return getattr(user, 'morador', None)


def construir_resumo_financeiro_morador(morador):
    divisoes = list(
        morador.divisoes_despesa.select_related('despesa', 'despesa__paga_por')
    )
    divisoes_creditoras = list(
        DivisaoDespesa.objects.select_related('despesa', 'morador')
        .filter(
            despesa__republica=morador.republica,
            despesa__paga_por=morador,
        )
        .exclude(morador=morador)
    )

    total_pago_em_despesas = morador.despesas_pagas.aggregate(
        total=Coalesce(Sum('valor_total'), Decimal('0.00'))
    )['total']
    total_pago_em_acertos = PagamentoDivisao.objects.filter(
        pagamento__pagador=morador
    ).aggregate(total=Coalesce(Sum('valor_aplicado'), Decimal('0.00')))['total']
    total_recebido_em_acertos = PagamentoDivisao.objects.filter(
        pagamento__recebedor=morador
    ).aggregate(total=Coalesce(Sum('valor_aplicado'), Decimal('0.00')))['total']

    total_devido = sum((divisao.valor_devido for divisao in divisoes), Decimal('0.00'))
    total_quitado = sum(
        (
            (
                divisao.valor_devido
                if divisao.despesa.paga_por_id == morador.id
                else divisao.valor_pago
            )
            for divisao in divisoes
        ),
        start=Decimal('0.00'),
    )
    total_pendente = sum(
        (
            (
                Decimal('0.00')
                if divisao.despesa.paga_por_id == morador.id
                else divisao.saldo_aberto
            )
            for divisao in divisoes
        ),
        start=Decimal('0.00'),
    )
    total_credito_aberto = sum(
        (divisao.saldo_aberto for divisao in divisoes_creditoras),
        Decimal('0.00'),
    )

    return {
        'id': morador.id,
        'nome': morador.nome,
        'total_pago_em_despesas': total_pago_em_despesas,
        'total_devido': total_devido,
        'total_quitado': total_quitado,
        'total_pendente': total_pendente,
        'total_pago_em_acertos': total_pago_em_acertos,
        'total_recebido_em_acertos': total_recebido_em_acertos,
        'total_credito_aberto': total_credito_aberto,
        'saldo': total_credito_aberto - total_pendente,
    }


class RepublicaScopedMixin:
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
        if self.request.user.is_staff:
            return True

        morador = self.get_user_morador()
        if not morador or not morador.eh_admin:
            return False

        if republica is None:
            return True

        return morador.republica_id == republica.id

    def get_scoped_queryset(self, queryset):
        if self.request.user.is_staff:
            return queryset

        try:
            republica = self.get_required_user_republica()
        except ValidationError:
            return queryset.none()

        return queryset.filter(**{self.republica_lookup: republica})

    def validate_user_republica(self, republica):
        if self.request.user.is_staff:
            return

        user_republica = self.get_user_republica()
        if not user_republica:
            raise PermissionDenied('Seu usuario nao esta vinculado a uma republica.')
        if republica.id != user_republica.id:
            raise PermissionDenied('Voce so pode acessar dados da sua propria republica.')

    def ensure_republic_admin(self, republica, message='Voce nao tem permissao para alterar esse recurso.'):
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
        serializer.save(republica=self.get_required_user_republica())

    def perform_update(self, serializer):
        despesa = self.get_object()
        self.validate_user_republica(despesa.republica)
        self.ensure_republic_admin(
            despesa.republica,
            'Somente o administrador da republica pode editar despesas existentes.',
        )
        serializer.save()

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
        divisoes_republica = list(
            DivisaoDespesa.objects.select_related('despesa', 'morador')
            .filter(despesa__republica=republica)
            .exclude(morador=F('despesa__paga_por'))
        )
        total_pendente = sum((divisao.saldo_aberto for divisao in divisoes_republica), Decimal('0.00'))
        total_quitado = total_despesas - total_pendente

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
