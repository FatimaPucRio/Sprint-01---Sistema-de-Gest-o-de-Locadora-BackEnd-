from datetime import date, datetime
from functools import wraps
from sqlite3 import IntegrityError
import logging
import sqlite3

from flask import Flask, request, jsonify, Blueprint
from flasgger import Swagger
from flask_cors import CORS
from typing import Tuple

from db_config import get_conexao_db, DATABASE
from utils import registrar_cliente, busca_filme_tmdb

# --- Configuração de Logging ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(ch)


# === Decorador de conexão ===
def gerenciar_conexao_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = get_conexao_db()
        try:
            result = func(conn, *args, **kwargs)

            status_check = result[1] if isinstance(result, tuple) else 200

            if status_check in [200, 201, 204]:
                conn.commit()
            return result

        except IntegrityError:
            conn.rollback()
            return jsonify({"erro": "Recurso já existe ou viola restrições."}), 409

        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"erro": f"Erro interno no DB: {str(e)}"}), 500

        except Exception as e:
            conn.rollback()
            return jsonify({"erro": f"Erro inesperado: {str(e)}"}), 500

        finally:
            conn.close()

    return wrapper


# === Função de validação ===
def valida_idade(data_nascimento_str: str) -> Tuple[str, int]:
    try:
        # PONTO DE REVERSÃO: Sem o .strip() para tratamento de espaços
        data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Data inválida. Use YYYY-MM-DD.")

    hoje = date.today()
    idade = hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )

    if idade < 18:
        raise ValueError("Cliente deve ser maior de 18 anos.")

    return data_nascimento_str, idade


# === Inicialização ===
app = Flask(__name__)
CORS(app)

app.config['SWAGGER'] = {
    'title': 'API Sistema de Gestão de Locadora',
    'uiversion': 3,
    'openapi': '3.0.2'
}

swagger = Swagger(app)

clientes_bp = Blueprint('clientes_bp', __name__, url_prefix='/clientes')
filmes_bp = Blueprint('filmes_bp', __name__, url_prefix='/filmes')


# === ROTA INICIAL — OCULTA DO SWAGGER ===
@app.route('/')
def inicio():
    logger.info("Rota raiz acessada.")
    return "API da Locadora está rodando! Acesse /apidocs para a documentação."


# === ROTAS DE CLIENTES ===

@clientes_bp.route('/', methods=['POST'])
def cadastra_cliente():
    """
    Cadastra um novo cliente
    ---
    tags:
      - Clientes
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              nome:
                type: string
              cpf:
                type: string
              data_nascimento:
                type: string
              email:
                type: string
              telefone:
                type: string
    responses:
      201:
        description: Cliente cadastrado
      400:
        description: Dados inválidos
    """
    dados = request.get_json()

    nome = dados.get('nome')
    cpf = dados.get('cpf')
    data_nascimento_str = dados.get('data_nascimento')
    email = dados.get('email', '')
    telefone = dados.get('telefone', '')

    if not all([nome, cpf, data_nascimento_str]):
        return jsonify({"erro": "Campos obrigatórios faltando."}), 400

    try:
        valida_idade(data_nascimento_str)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    resultado = registrar_cliente(nome, cpf, email, telefone, data_nascimento_str)

    if isinstance(resultado, tuple):
        dados_resposta, status_code = resultado
    else:
        return jsonify({"erro": "Erro interno inesperado."}), 500

    if "erro" in dados_resposta:
        return jsonify(dados_resposta), status_code

    logger.info(f"Cliente cadastrado: {dados_resposta['cliente']['id']}")
    return jsonify({"mensagem": "Cliente cadastrado!", "cliente": dados_resposta["cliente"]}), 201


@clientes_bp.route('/', methods=['GET'])
@gerenciar_conexao_db
def lista_clientes(conn: sqlite3.Connection):
    """
    Lista todos os clientes cadastrados
    ---
    tags:
      - Clientes
    responses:
      200:
        description: Lista de clientes
    """
    clientes = conn.execute("SELECT * FROM clientes").fetchall()
    return jsonify([dict(c) for c in clientes]), 200


@clientes_bp.route('/<int:cliente_id>', methods=['PUT'])
@gerenciar_conexao_db
def atualiza_cliente(conn: sqlite3.Connection, cliente_id: int):
    """
    Atualiza um cliente específico
    ---
    tags:
      - Clientes
    parameters:
      - name: cliente_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              nome:
                type: string
              cpf:
                type: string
              data_nascimento:
                type: string
              email:
                type: string
              telefone:
                type: string
    responses:
      200:
        description: Cliente atualizado
      400:
        description: Dados inválidos ou formato JSON incorreto
      415:
        description: Tipo de Mídia Não Suportado (Content-Type não é application/json)
      404:
        description: Cliente não encontrado
    """
    # PONTO DE REVERSÃO: Sem a checagem de Content-Type/Erro 415
    dados = request.get_json()

    set_clauses, params = [], []

    existe = conn.execute("SELECT id FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    if not existe:
        return jsonify({"erro": "Cliente não encontrado."}), 404

    if not dados:
        return jsonify({"erro": "Nenhum campo enviado."}), 400

    for key, value in dados.items():
        if key == 'data_nascimento':
            try:
                # PONTO DE REVERSÃO: Sem a checagem de value.strip()
                valida_idade(value)
                set_clauses.append("data_nascimento = ?")
                params.append(value)
            except ValueError as e:
                return jsonify({"erro": str(e)}), 400
        elif key in ['nome', 'email', 'telefone', 'cpf']:
            set_clauses.append(f"{key} = ?")
            params.append(value)

    if not set_clauses:
        return jsonify({"erro": "Nenhum campo válido enviado."}), 400

    sql = f"UPDATE clientes SET {', '.join(set_clauses)} WHERE id = ?"
    params.append(cliente_id)

    conn.execute(sql, tuple(params))

    return jsonify({"mensagem": "Cliente atualizado!"}), 200


@clientes_bp.route('/<int:cliente_id>', methods=['DELETE'])
@gerenciar_conexao_db
def exclui_cliente(conn: sqlite3.Connection, cliente_id: int):
    """
    Exclui um cliente
    ---
    tags:
      - Clientes
    parameters:
      - name: cliente_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      204:
        description: Cliente removido
      404:
        description: Cliente não encontrado
    """
    cursor = conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    if cursor.rowcount == 0:
        return jsonify({"erro": "Cliente não encontrado."}), 404

    return ('', 204)


# === ROTAS DE FILMES ===

@filmes_bp.route('/busca_externa', methods=['GET'])
def busca_filme_externa():
    """
    Busca filme no TMDB
    ---
    tags:
      - Filmes
    parameters:
      - name: titulo
        in: query
        required: true
        schema:
          type: string
    responses:
      200:
        description: Resultado da busca
      400:
        description: Erro no envio dos dados
    """
    titulo = request.args.get('titulo')

    if not titulo:
        return jsonify({"erro": "Título é obrigatório."}), 400

    resultado = busca_filme_tmdb(titulo)
    if "erro" in resultado:
        return jsonify(resultado), resultado.get("status_code", 503)

    return jsonify(resultado), 200


# === Registrar Blueprints ===
app.register_blueprint(clientes_bp)
app.register_blueprint(filmes_bp)


# === Inicialização ===
if __name__ == '__main__':
    try:
        from db_config import inicializar_db
        inicializar_db()
    except ImportError:
        logger.error("Função inicializar_db não encontrada.")

    logger.info("Iniciando servidor Flask (porta 5000)")
    app.run(debug=True, host='0.0.0.0', port=5000)