API Locadora de Filmes - Backend Python/Flask

Esta API é o coração do sistema, desenvolvida em Python (Flask). Ela gerencia os dados de Clientes (usando SQLite) e se comunica com o TMDB para buscar informações de filmes.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Regras Chave do Sistema:

* O sistema garante a integridade dos dados através destas regras de negócio:
* Idade Mínima: Clientes devem ter mais de 18 anos.
* Identificador Único: O CPF é exclusivo para cada cliente.
* Dados Obrigatórios: Nome, CPF e Data de Nascimento são exigidos.
* Busca: Requer o parâmetro titulo para buscar filmes externos.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Acesso e Documentação

* Documentação (Swagger)	http://127.0.0.1:5000/apidocs	irá ver todos os endpoints.
* Servidor Principal	http://127.0.0.1:5000/	Confirma que a API está no ar.
