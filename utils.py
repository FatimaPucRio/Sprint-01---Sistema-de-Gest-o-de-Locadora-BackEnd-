import requests
import logging
from sqlite3 import IntegrityError
from typing import Dict, Any, Tuple

# === CONFIGURAÇÕES GLOBAIS ===
logger = logging.getLogger(__name__)
TMDB_API_KEY = "eeaaf226c2fe250bfce3e36d8e50f9d5"
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_DETAILS_URL = "https://api.themoviedb.org/3/movie"

# Importa a conexão do arquivo CORRETO
from db_config import get_conexao_db


# === LÓGICA DE NEGÓCIO 1: REPOSITÓRIO DE CLIENTE ===

def registrar_cliente(nome, cpf, email, telefone, data_nascimento_str) -> Tuple[Dict[str, Any], int]:

    conn = get_conexao_db()
    try:
        cursor = conn.execute(
            "INSERT INTO clientes (nome, cpf, email, telefone, data_nascimento) VALUES (?, ?, ?, ?, ?)",
            (nome, cpf, email, telefone, data_nascimento_str)
        )
        conn.commit()

        cliente_id = cursor.lastrowid
        cliente_salvo = conn.execute(
            "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
        ).fetchone()

        return {"cliente": dict(cliente_salvo)}, 201

    except IntegrityError:
        conn.rollback()
        return {"erro": "CPF já cadastrado."}, 409

    except Exception as e:
        conn.rollback()
        logger.error(f"Erro no DB: {str(e)}")
        return {"erro": f"Falha no banco de dados: {str(e)}"}, 500

    finally:
        conn.close()


# === LÓGICA DE NEGÓCIO 2: BUSCA EXTERNA (TMDb) ===

def busca_filme_tmdb(titulo: str) -> Dict[str, Any]:

    if not TMDB_API_KEY:
        return {"error": "API Key da TMDb não configurada."}

    search_params = {
        'api_key': TMDB_API_KEY,
        'query': titulo,
        'language': 'pt-BR',
    }

    try:
        search_res = requests.get(TMDB_SEARCH_URL, params=search_params)
        search_res.raise_for_status()
        data = search_res.json()

        if not data.get("results"):
            return {"error": f"Filme '{titulo}' não encontrado."}

        filme = data["results"][0]
        tmdb_id = filme["id"]

        details_res = requests.get(
            f"{TMDB_DETAILS_URL}/{tmdb_id}",
            params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'}
        )
        details_res.raise_for_status()
        details = details_res.json()

        generos = ", ".join([g["name"] for g in details.get("genres", [])])
        ano = details.get("release_date", "0000").split("-")[0]

        return {
            "titulo": details.get("title"),
            "genero": generos,
            "ano": int(ano) if ano.isdigit() else None,
            "omdb_id": tmdb_id
        }

    except Exception as e:
        logger.error(f"Erro TMDb: {e}")
        return {"error": "Erro ao buscar detalhes do filme."}
