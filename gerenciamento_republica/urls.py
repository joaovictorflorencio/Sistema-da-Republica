from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CadastroUsuarioView,
    DashboardOverviewView,
    DespesaViewSet,
    DivisaoDespesaViewSet,
    LoginView,
    MeView,
    LogoutView,
    MoradorViewSet,
    PagamentoViewSet,
    RepublicaResumoFinanceiroView,
    RepublicaViewSet,
    TarefaViewSet,
    cadastro_page,
    dashboard_page,
    financas_page,
    login_page,
    perfil_page,
    tarefas_page,
)

app_name = 'gerenciamento_republica'

router = DefaultRouter()
router.register('republicas', RepublicaViewSet, basename='republica')
router.register('moradores', MoradorViewSet, basename='morador')
router.register('despesas', DespesaViewSet, basename='despesa')
router.register('divisoes', DivisaoDespesaViewSet, basename='divisao')
router.register('pagamentos', PagamentoViewSet, basename='pagamento')
router.register('tarefas', TarefaViewSet, basename='tarefa')

urlpatterns = [
    path('', dashboard_page, name='home'),
    path('login/', login_page, name='login-page'),
    path('cadastro/', cadastro_page, name='cadastro-page'),
    path('painel/', dashboard_page, name='painel-page'),
    path('financas/', financas_page, name='financas-page'),
    path('tarefas/', tarefas_page, name='tarefas-page'),
    path('perfil/', perfil_page, name='perfil-page'),
    path('api/auth/cadastro/', CadastroUsuarioView.as_view(), name='cadastro'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/me/', MeView.as_view(), name='me'),
    path('api/dashboard/overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('api/republicas/<int:pk>/resumo-financeiro/', RepublicaResumoFinanceiroView.as_view(), name='resumo-financeiro'),
]

urlpatterns += [
    path('api/', include(router.urls)),
]
