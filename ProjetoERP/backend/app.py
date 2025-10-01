from flask import Flask, jsonify, request
from datetime import datetime
from auth import authenticate_user, generate_token, token_required, role_required
import backup
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui-mude-em-producao'  # Change this in production!

# Configurar logging básico
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("=== Inicializando servidor Flask ===")
logger.info("Aplicação Flask iniciada com sucesso")

# Dados simulados para o módulo Projetos (Ordens de Serviço)
ordens_servico = [
    {
        'id': 1,
        'cliente': 'João Silva',
        'produto': 'Cobertura em Policarbonato Fixa',
        'status': 'Aguardando Medição',
        'data_criacao': '2024-01-15',
        'agendamento': '2024-01-20 10:00'
    },
    {
        'id': 2,
        'cliente': 'Maria Santos',
        'produto': 'Toldo em Lona',
        'status': 'Em Fabricação',
        'data_criacao': '2024-01-10',
        'agendamento': '2024-01-25 14:00'
    }
]

# Dados simulados para o módulo Vendas (Orçamentos)
orcamentos = [
    {
        'id': 1,
        'cliente': 'João Silva',
        'produto': 'Cobertura em Policarbonato Fixa',
        'valor': 2500.00,
        'data_envio': '2024-01-15',
        'status': 'enviado',
        'validade': '2024-02-15'
    },
    {
        'id': 2,
        'cliente': 'Maria Santos',
        'produto': 'Toldo em Lona',
        'valor': 1200.00,
        'data_envio': '2024-01-20',
        'status': 'aprovado',
        'validade': '2024-02-20'
    }
]

# Dados simulados para o módulo Financeiro
lancamentos_financeiros = [
    {
        'id': 1,
        'tipo': 'receber',
        'descricao': 'Pagamento João Silva - Cobertura Policarbonato',
        'valor': 2500.00,
        'data_vencimento': '2024-02-01',
        'data_pagamento': None,
        'status': 'pendente',
        'categoria': 'venda'
    },
    {
        'id': 2,
        'tipo': 'pagar',
        'descricao': 'Compra de policarbonato',
        'valor': 800.00,
        'data_vencimento': '2024-01-25',
        'data_pagamento': '2024-01-20',
        'status': 'pago',
        'categoria': 'fornecedor'
    }
]

@app.route('/')
def home():
    print("Acessando rota raiz '/'")
    logger.info("Requisição para rota home")
    return "Sistema de Gestão Integrada - Toldos Fortaleza"

@app.route('/api/login', methods=['POST'])
def login():
    """Endpoint para autenticação de usuários"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username e password são obrigatórios!'}), 400
    
    user = authenticate_user(username, password)
    if user:
        token = generate_token({
            'username': username,
            'role': user['role'],
            'name': user['name']
        })
        return jsonify({
            'token': token,
            'user': {
                'username': username,
                'role': user['role'],
                'name': user['name']
            }
        }), 200
    
    return jsonify({'message': 'Credenciais inválidas!'}), 401

@app.route('/api/projetos', methods=['GET'])
def projetos_wrapper(*args, **kwargs):
    print("Requisição recebida para /api/projetos")
    logger.info("Tentando acessar /api/projetos")
    return listar_projetos(*args, **kwargs)

@token_required
def listar_projetos(current_user):
    print(f"Autenticação OK para listar_projetos. Usuário: {current_user['username']}")
    logger.info(f"Listando projetos para usuário: {current_user['username']}")
    return jsonify(ordens_servico)

@app.route('/api/projetos', methods=['POST'])
@token_required
@role_required('admin')
def criar_projeto(current_user):
    novo_projeto = request.json
    novo_projeto['id'] = len(ordens_servico) + 1
    novo_projeto['data_criacao'] = datetime.now().strftime('%Y-%m-%d')
    novo_projeto['criado_por'] = current_user['username']
    ordens_servico.append(novo_projeto)
    return jsonify(novo_projeto), 201

@app.route('/api/projetos/<int:id>', methods=['PUT'])
@token_required
def atualizar_projeto(current_user, id):
    projeto = next((p for p in ordens_servico if p['id'] == id), None)
    if projeto:
        # Verificar se o usuário tem permissão para editar
        if current_user['role'] != 'admin' and projeto.get('criado_por') != current_user['username']:
            return jsonify({'erro': 'Permissão negada!'}), 403
        
        dados = request.json
        projeto.update(dados)
        return jsonify(projeto)
    return jsonify({'erro': 'Projeto não encontrado'}), 404

# Endpoints para o módulo Financeiro
@app.route('/api/financeiro/contas-a-pagar', methods=['GET'])
@token_required
@role_required('admin')
def listar_contas_a_pagar(current_user):
    contas_pagar = [l for l in lancamentos_financeiros if l['tipo'] == 'pagar']
    return jsonify(contas_pagar)

@app.route('/api/financeiro/contas-a-receber', methods=['GET'])
@token_required
def listar_contas_a_receber(current_user):
    contas_receber = [l for l in lancamentos_financeiros if l['tipo'] == 'receber']
    return jsonify(contas_receber)

@app.route('/api/financeiro/lancamento', methods=['POST'])
@token_required
@role_required('admin')
def criar_lancamento(current_user):
    novo_lancamento = request.json
    novo_lancamento['id'] = len(lancamentos_financeiros) + 1
    novo_lancamento['criado_por'] = current_user['username']
    lancamentos_financeiros.append(novo_lancamento)
    return jsonify(novo_lancamento), 201

@app.route('/api/financeiro/fluxo-caixa', methods=['GET'])
@token_required
@role_required('admin')
def fluxo_caixa(current_user):
    # Cálculo simples do fluxo de caixa
    total_receber = sum(l['valor'] for l in lancamentos_financeiros if l['tipo'] == 'receber' and l['status'] == 'pendente')
    total_pagar = sum(l['valor'] for l in lancamentos_financeiros if l['tipo'] == 'pagar' and l['status'] == 'pendente')
    saldo = total_receber - total_pagar
    return jsonify({
        'total_a_receber': total_receber,
        'total_a_pagar': total_pagar,
        'saldo': saldo
    })

@app.route('/api/financeiro/relatorios', methods=['GET'])
@token_required
@role_required('admin')
def relatorios_financeiros(current_user):
    # Relatório simples de faturamento
    faturamento = sum(l['valor'] for l in lancamentos_financeiros if l['tipo'] == 'receber' and l['status'] == 'pago')
    despesas = sum(l['valor'] for l in lancamentos_financeiros if l['tipo'] == 'pagar' and l['status'] == 'pago')
    lucro = faturamento - despesas
    return jsonify({
        'faturamento': faturamento,
        'despesas': despesas,
        'lucro': lucro
    })

# Endpoints para o Dashboard
@app.route('/api/dashboard/kpis', methods=['GET'])
def kpis_wrapper(*args, **kwargs):
    print("Requisição recebida para /api/dashboard/kpis")
    logger.info("Tentando acessar /api/dashboard/kpis")
    return dashboard_kpis(*args, **kwargs)

@token_required
def dashboard_kpis(current_user):
    print(f"Autenticação OK para dashboard_kpis. Usuário: {current_user['username']}")
    logger.info(f"Carregando KPIs para usuário: {current_user['username']}")
    from datetime import datetime, timedelta
    
    # 1. Valor total em orçamentos enviados no mês
    mes_atual = datetime.now().month
    orcamentos_mes = [o for o in orcamentos if datetime.strptime(o['data_envio'], '%Y-%m-%d').month == mes_atual and o['status'] == 'enviado']
    total_orcamentos = sum(o['valor'] for o in orcamentos_mes)
    
    # 2. Número de vendas fechadas (orcamentos aprovados)
    vendas_fechadas = len([o for o in orcamentos if o['status'] == 'aprovado'])
    
    # 3. Faturamento do mês (receitas pagas no mês)
    faturamento_mes = sum(l['valor'] for l in lancamentos_financeiros if l['tipo'] == 'receber' and l['status'] == 'pago' and datetime.strptime(l['data_pagamento'], '%Y-%m-%d').month == mes_atual)
    
    # 4. Número de projetos em andamento (ordens de serviço não finalizadas)
    projetos_andamento = len([p for p in ordens_servico if p['status'] not in ['Finalizado']])
    
    # 5. Contas a receber vencendo na semana
    hoje = datetime.now()
    fim_semana = hoje + timedelta(days=7)
    contas_vencendo = [l for l in lancamentos_financeiros if l['tipo'] == 'receber' and l['status'] == 'pendente']
    contas_vencendo_semana = []
    
    for conta in contas_vencendo:
        data_vencimento = datetime.strptime(conta['data_vencimento'], '%Y-%m-%d')
        if hoje <= data_vencimento <= fim_semana:
            contas_vencendo_semana.append(conta)
    
    return jsonify({
        'total_orcamentos_mes': total_orcamentos,
        'vendas_fechadas': vendas_fechadas,
        'faturamento_mes': faturamento_mes,
        'projetos_andamento': projetos_andamento,
        'contas_vencendo_semana': len(contas_vencendo_semana)
    })

# Endpoints para Backup
@app.route('/api/backup/create', methods=['POST'])
@token_required
@role_required('admin')
def criar_backup_manual(current_user):
    """Cria um backup manual dos dados"""
    try:
        backup_path = backup.criar_backup(ordens_servico, orcamentos, lancamentos_financeiros)
        return jsonify({'message': 'Backup criado com sucesso!', 'caminho': backup_path}), 200
    except Exception as e:
        return jsonify({'message': f'Erro ao criar backup: {str(e)}'}), 500

@app.route('/api/backup/list', methods=['GET'])
@token_required
@role_required('admin')
def listar_backups(current_user):
    """Lista todos os backups disponíveis"""
    try:
        backups = backup.listar_backups()
        return jsonify(backups), 200
    except Exception as e:
        return jsonify({'message': f'Erro ao listar backups: {str(e)}'}), 500

@app.route('/api/backup/restore/<backup_name>', methods=['POST'])
@token_required
@role_required('admin')
def restaurar_backup(current_user, backup_name):
    """Restaura dados de um backup específico"""
    try:
        backup_path = os.path.join(backup.BACKUP_DIR, backup_name)
        if not os.path.exists(backup_path):
            return jsonify({'message': 'Backup não encontrado!'}), 404
        
        success = backup.restaurar_backup(backup_path, ordens_servico, orcamentos, lancamentos_financeiros)
        if success:
            return jsonify({'message': 'Backup restaurado com sucesso!'}), 200
        else:
            return jsonify({'message': 'Erro ao restaurar backup!'}), 500
    except Exception as e:
        return jsonify({'message': f'Erro ao restaurar backup: {str(e)}'}), 500

@app.route('/api/backup/clean', methods=['POST'])
@token_required
@role_required('admin')
def limpar_backups_antigos(current_user):
    """Remove backups antigos (mais de 30 dias)"""
    try:
        removidos = backup.limpar_backups_antigos(30)
        return jsonify({'message': f'{removidos} backups antigos removidos!'}), 200
    except Exception as e:
        return jsonify({'message': f'Erro ao limpar backups: {str(e)}'}), 500

if __name__ == '__main__':
    try:
        # Iniciar agendamento automático de backups
        print("Iniciando scheduler de backup...")
        backup_scheduler = backup.iniciar_agendamento_backup(ordens_servico, orcamentos, lancamentos_financeiros)
        print("Scheduler de backup iniciado com sucesso")
        logger.info("Scheduler de backup ativo")
    except Exception as e:
        print(f"Erro ao iniciar scheduler de backup: {e}")
        logger.error(f"Falha no scheduler: {e}")
    
    print("Iniciando servidor Flask na porta 5000...")
    app.run(debug=True, host='0.0.0.0')