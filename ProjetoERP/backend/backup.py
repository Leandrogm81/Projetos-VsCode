import json
import os
import shutil
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Diretório para armazenar backups
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def criar_backup(ordens_servico, orcamentos, lancamentos_financeiros):
    """Cria um backup dos dados atuais em arquivos JSON"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'backup_{timestamp}')
    os.makedirs(backup_path, exist_ok=True)
    
    # Salvar cada conjunto de dados em arquivos separados
    with open(os.path.join(backup_path, 'ordens_servico.json'), 'w', encoding='utf-8') as f:
        json.dump(ordens_servico, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(backup_path, 'orcamentos.json'), 'w', encoding='utf-8') as f:
        json.dump(orcamentos, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(backup_path, 'lancamentos_financeiros.json'), 'w', encoding='utf-8') as f:
        json.dump(lancamentos_financeiros, f, ensure_ascii=False, indent=2)
    
    # Criar um arquivo de metadados do backup
    metadata = {
        'timestamp': timestamp,
        'data_criacao': datetime.now().isoformat(),
        'total_ordens': len(ordens_servico),
        'total_orcamentos': len(orcamentos),
        'total_lancamentos': len(lancamentos_financeiros)
    }
    
    with open(os.path.join(backup_path, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"Backup criado em: {backup_path}")
    return backup_path

def listar_backups():
    """Lista todos os backups disponíveis"""
    backups = []
    if os.path.exists(BACKUP_DIR):
        for item in os.listdir(BACKUP_DIR):
            item_path = os.path.join(BACKUP_DIR, item)
            if os.path.isdir(item_path) and item.startswith('backup_'):
                metadata_path = os.path.join(item_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    backups.append({
                        'nome': item,
                        'caminho': item_path,
                        'metadata': metadata
                    })
    return sorted(backups, key=lambda x: x['metadata']['timestamp'], reverse=True)

def restaurar_backup(backup_path, ordens_servico, orcamentos, lancamentos_financeiros):
    """Restaura dados de um backup"""
    try:
        # Carregar ordens de serviço
        with open(os.path.join(backup_path, 'ordens_servico.json'), 'r', encoding='utf-8') as f:
            ordens_servico.clear()
            ordens_servico.extend(json.load(f))
        
        # Carregar orçamentos
        with open(os.path.join(backup_path, 'orcamentos.json'), 'r', encoding='utf-8') as f:
            orcamentos.clear()
            orcamentos.extend(json.load(f))
        
        # Carregar lançamentos financeiros
        with open(os.path.join(backup_path, 'lancamentos_financeiros.json'), 'r', encoding='utf-8') as f:
            lancamentos_financeiros.clear()
            lancamentos_financeiros.extend(json.load(f))
        
        print(f"Dados restaurados do backup: {backup_path}")
        return True
    except Exception as e:
        print(f"Erro ao restaurar backup: {e}")
        return False

def limpar_backups_antigos(dias_retencao=30):
    """Remove backups mais antigos que o número especificado de dias"""
    agora = datetime.now()
    backups = listar_backups()
    removidos = 0
    
    for backup in backups:
        data_criacao = datetime.fromisoformat(backup['metadata']['data_criacao'])
        diferenca_dias = (agora - data_criacao).days
        
        if diferenca_dias > dias_retencao:
            try:
                shutil.rmtree(backup['caminho'])
                print(f"Backup removido: {backup['nome']}")
                removidos += 1
            except Exception as e:
                print(f"Erro ao remover backup {backup['nome']}: {e}")
    
    return removidos

def iniciar_agendamento_backup(ordens_servico, orcamentos, lancamentos_financeiros):
    """Inicia o agendamento automático de backups"""
    scheduler = BackgroundScheduler()
    
    # Agendar backup diário às 2h da manhã
    scheduler.add_job(
        lambda: criar_backup(ordens_servico, orcamentos, lancamentos_financeiros),
        trigger=CronTrigger(hour=2, minute=0),
        id='backup_diario'
    )
    
    # Agendar limpeza de backups antigos todo domingo às 3h
    scheduler.add_job(
        lambda: limpar_backups_antigos(30),
        trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='limpeza_backups'
    )
    
    scheduler.start()
    print("Agendamento de backups iniciado")
    return scheduler