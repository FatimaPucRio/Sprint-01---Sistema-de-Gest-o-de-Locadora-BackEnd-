import sqlite3
import os
import logging

# Configuração de Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Caminho ABSOLUTO do banco — garante que sempre é o mesmo arquivo
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locadora.db')

# --- FUNÇÃO DE CONEXÃO ---
def get_conexao_db():
    """
    Cria e retorna a conexão com o SQLite sempre usando o mesmo arquivo.
    """
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON") 
    conn.row_factory = sqlite3.Row
    return conn

# --- FUNÇÃO PRINCIPAL DE CRIAÇÃO DO ESQUEMA ---
def criar_esquema_db():
    """
    Cria a tabela 'clientes' caso não exista.
    """
    conn = get_conexao_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                email TEXT,
                telefone TEXT,
                data_nascimento TEXT NOT NULL
            );
        """)

        conn.commit()
        logger.info("Esquema do banco de dados criado com sucesso.")

    except sqlite3.Error as e:
        logger.error(f"Erro ao criar tabelas: {e}", exc_info=True)
        conn.rollback()

    finally:
        conn.close()

# --- FUNÇÃO DE INICIALIZAÇÃO ---
def inicializar_db():
    """
    Executa a criação do banco e das tabelas na inicialização do app.
    """
    if not os.path.exists(DATABASE):
        logger.warning(f"Banco de dados '{DATABASE}' não encontrado. Criando novo esquema...")

    criar_esquema_db()
    logger.info("Inicialização do DB concluída.")

# Permite rodar diretamente
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    inicializar_db()
