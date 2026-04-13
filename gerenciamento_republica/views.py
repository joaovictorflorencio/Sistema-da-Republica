from decimal import Decimal

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.db.models import Count
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

from .models import Despesa, DivisaoDespesa, Morador, Pagamento, Republica, Tarefa
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


class RepublicaScopedMixin:
    republica_lookup = 'republica'

    def get_user_republica(self):
        return get_user_republica(self.request.user)

    def get_scoped_queryset(self, queryset):
        if self.request.user.is_staff:
            return queryset

        republica = self.get_user_republica()
        if not republica:
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
        )

    def perform_update(self, serializer):
        self.validate_user_republica(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.validate_user_republica(instance)
        instance.delete()


class MoradorViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MoradorSerializer

    def get_queryset(self):
        queryset = Morador.objects.select_related('republica', 'usuario').all()
        return self.get_scoped_queryset(queryset)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())

    def perform_update(self, serializer):
        morador = self.get_object()
        self.validate_user_republica(morador.republica)
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())


class DespesaViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DespesaSerializer

    def get_queryset(self):
        queryset = Despesa.objects.select_related('republica', 'paga_por').prefetch_related('divisoes').all()
        return self.get_scoped_queryset(queryset)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())

    def perform_update(self, serializer):
        despesa = self.get_object()
        self.validate_user_republica(despesa.republica)
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())


class DivisaoDespesaViewSet(RepublicaScopedMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DivisaoDespesaSerializer
    republica_lookup = 'despesa__republica'

    def get_queryset(self):
        queryset = DivisaoDespesa.objects.select_related('despesa', 'morador').all()
        return self.get_scoped_queryset(queryset)


class PagamentoViewSet(RepublicaScopedMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PagamentoSerializer

    def get_queryset(self):
        queryset = Pagamento.objects.select_related(
            'republica',
            'pagador',
            'recebedor',
            'referencia_despesa',
        ).all()
        return self.get_scoped_queryset(queryset)

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())

    def perform_update(self, serializer):
        pagamento = self.get_object()
        self.validate_user_republica(pagamento.republica)
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())


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
        serializer.save(republica=self.get_user_republica())

    def perform_update(self, serializer):
        tarefa = self.get_object()
        self.validate_user_republica(tarefa.republica)
        if self.request.user.is_staff:
            serializer.save()
            return
        serializer.save(republica=self.get_user_republica())


class RepublicaResumoFinanceiroView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        republica = get_object_or_404(Republica, pk=pk)
        if not request.user.is_staff:
            user_republica = get_user_republica(request.user)
            if not user_republica or user_republica.id != republica.id:
                raise PermissionDenied('Voce so pode acessar o resumo da sua propria republica.')
        moradores = republica.moradores.order_by('nome')

        resumo_moradores = []
        total_despesas = republica.despesas.aggregate(
            total=Coalesce(Sum('valor_total'), Decimal('0.00'))
        )['total']

        for morador in moradores:
            total_pago_em_despesas = morador.despesas_pagas.aggregate(
                total=Coalesce(Sum('valor_total'), Decimal('0.00'))
            )['total']
            total_devido = morador.divisoes_despesa.aggregate(
                total=Coalesce(Sum('valor_devido'), Decimal('0.00'))
            )['total']
            total_pago_em_acertos = morador.pagamentos_realizados.aggregate(
                total=Coalesce(Sum('valor'), Decimal('0.00'))
            )['total']
            total_recebido_em_acertos = morador.pagamentos_recebidos.aggregate(
                total=Coalesce(Sum('valor'), Decimal('0.00'))
            )['total']

            saldo = (
                total_pago_em_despesas
                - total_devido
                - total_recebido_em_acertos
                + total_pago_em_acertos
            )

            resumo_moradores.append(
                {
                    'id': morador.id,
                    'nome': morador.nome,
                    'total_pago_em_despesas': total_pago_em_despesas,
                    'total_devido': total_devido,
                    'total_pago_em_acertos': total_pago_em_acertos,
                    'total_recebido_em_acertos': total_recebido_em_acertos,
                    'saldo': saldo,
                }
            )

        serializer = RepublicaResumoSerializer(
            {
                'id': republica.id,
                'nome': republica.nome,
                'total_despesas': total_despesas,
                'moradores': resumo_moradores,
            }
        )
        return Response(serializer.data)


class DashboardOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        republica = get_user_republica(request.user)
        if request.user.is_staff and not republica:
            republica = Republica.objects.order_by('nome').first()
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
        total_moradores = republica.moradores.aggregate(total=Count('id'))['total']
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
