import os
import asyncio
import logging
import aiohttp
from typing import Dict, Any, List, Optional
from telebot.async_telebot import AsyncTeleBot

# -------------------------------------------------------------------------
# CONFIGURAÇÃO DE LOGGING E INICIALIZAÇÃO ENCAPSULADA
# -------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN: Optional[str] = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise RuntimeError("CRITICAL CORE ERROR: 'TELEGRAM_TOKEN' não injetado nas variáveis de ambiente.")

# Instanciação do bot usando o Core Assíncrono (Ideal para alta concorrência de usuários)
bot: AsyncTeleBot = AsyncTeleBot(TOKEN, parse_mode='Markdown')

# -------------------------------------------------------------------------
# NÚCLEO MOTOR DE CONSULTAS ASSÍNCRONAS EM PARALELO (Async Engine)
# -------------------------------------------------------------------------
async def requisitar_provedor_dados(session: aiohttp.ClientSession, provedor: Dict[str, str], termo: str) -> Optional[Dict[str, Any]]:
    """
    Efetua a requisição HTTP não-bloqueante de forma isolada.
    Se um site falhar, o erro fica encapsulado nesta função, sem derrubar as outras buscas.
    """
    url_formatada = provedor["url_base"].format(termo=termo)
    try:
        # Define um limite estrito de 4 segundos por requisição paralela
        async with session.get(url_formatada, timeout=aiohttp.ClientTimeout(total=4)) as resposta:
            if resposta.status == 200:
                dados: Dict[str, Any] = await resposta.json()
                
                # Validação de payload nulo ou erro lógico interno da API externa
                if "erro" in dados or dados.get("type") == "service_error":
                    return None
                    
                # Injeta o nome do provedor vencedor dentro do dicionário de dados
                dados["__provedor_emissor__"] = provedor["nome"]
                return dados
    except Exception as erro_rede:
        logging.warning(f"Falha de comunicação com {provedor['nome']}: {str(erro_rede)}")
    return None

async def executar_barramento_concorrente(termo: str) -> Optional[Dict[str, Any]]:
    """
    Gerencia o disparo simultâneo de requisições (Asynchronous Concurrency).
    Usa o conceito de 'Primeira Resposta Válida Vence' (Fastest Response Wins).
    """
    # MATRIZ DE CONFIGURAÇÃO DE GATEWAYS (Modifique os links e tokens aqui)
    matriz_provedores: List[Dict[str, str]] = [
        {
            "nome": "Core-Alfa Premium (CPF/CNPJ)",
            "url_base": "https://brasilapi.com.br/docs#tag/BANKS"
        },
        {
            "nome": "Core-Beta Contingência (Nome/Telefone)",
            "url_base": "https://exemplo-paga2.com{termo}"
        },
        {
            "nome": "Geral-Público (BrasilAPI)",
            "url_base": "https://brasilapi.com.br{termo}"
        }
    ]

    # Cria uma sessão única de conexões assíncronas otimizadas para reuso de memória
    async with aiohttp.ClientSession() as session:
        # Cria uma lista de tarefas concorrentes em background
        tarefas = [requisitar_provedor_dados(session, provedor, termo) for provedor in matriz_provedores]
        
        # Dispara TODAS as requisições para todos os sites no exato mesmo milissegundo
        for tarefa_concluida in asyncio.as_completed(tarefas):
            resultado = await tarefa_concluida
            if resultado is not None:
                return resultado # Interrompe imediatamente e entrega o primeiro dado válido que chegar
                
    return None

# -------------------------------------------------------------------------
# INTERFACES DE EXECUÇÃO DO BOT (Handlers Assíncronos)
# -------------------------------------------------------------------------
@bot.message_handler(commands=['start', 'ajuda'])
async def comando_inicial(message):
    texto = (
        f"🤖 *SISTEMA DE ALTA DISPONIBILIDADE ENGENHARIA PRO*\n\n"
        f"Olá, *{message.from_user.first_name}*.\n"
        f"Barramento de microsserviços ativado com processamento assíncrono paralelo.\n\n"
        f"⚙️ *SINTAXE DE ENGENHARIA:* `/buscar <documento>`"
    )
    await bot.reply_to(message, texto)

@bot.message_handler(commands=['buscar'])
async def rota_busca_avancada(message):
    # Processamento de strings e higienização de inputs
    termo_bruto: str = message.text.replace('/buscar', '').strip()
    termo_limpo: str = termo_bruto.replace('.', '').replace('-', '').replace('/', '')

    if not termo_limpo:
        await bot.reply_to(message, "❌ *EXCEÇÃO SINTÁTICA:* Parâmetro obrigatório ausente na pilha de execução.")
        return

    # Envia o feedback visual de processamento assíncrono
    mensagem_status = await bot.reply_to(message, "⏳ *THROTTLE:* Alocando canais de memória e disparando requisições paralelas...")

    # Invoca o motor de busca concorrente passando o termo limpo
    dados_retornados = await executar_barramento_concorrente(termo_limpo)

    if dados_retornados:
        # Formatação profissional do JSON integrado (Tratamento Polymórfico de Respostas)
        provedor_origem = dados_retornados.get("__provedor_emissor__", "Desconhecido")
        relatorio = (
            f"👑 *RESULTADO DO BARRAMENTO ASSÍNCRONO* 👑\n"
            f"📡 _Gateway Emissor: {provedor_origem}_\n\n"
            f"📊 *DADOS INDEXADOS:*\n"
            f"👤 *Nome / Razão:* `{dados_retornados.get('nome', dados_retornados.get('razao_social', 'N/A'))}`\n"
            f"🆔 *Documento:* `{dados_retornados.get('cpf', dados_retornados.get('cnpj', termo_bruto))}`\n"
            f"📅 *Registro:* `{dados_retornados.get('data_nascimento', dados_retornados.get('data_inicio_atividade', 'N/A'))}`\n"
            f"📞 *Contato:* `{dados_retornados.get('telefone', dados_retornados.get('ddd_telefone1', 'N/A'))}`\n"
            f"📍 *Origem:* `{dados_retornados.get('municipio', 'N/A')} - {dados_retornados.get('uf', '')}`"
        )
        await bot.edit_message_text(text=relatorio, chat_id=message.chat.id, message_id=mensagem_status.message_id)
    else:
        # Tela de tratamento de erro absoluto de IO (Input/Output Exception)
        erro_payload = (
            f"❌ *EXCEÇÃO GERAL DE ENGENHARIA*\n\n"
            f"O termo `{termo_bruto}` causou estouro de pilha ou não foi retornado por nenhum gateway concorrente.\n\n"
            f"🔍 *Causa Raiz:* Nenhuma das APIs em `matriz_provedores` possuía o registro ou os links falharam por estouro de timeout (4000ms)."
        )
        await bot.edit_message_text(text=erro_payload, chat_id=message.chat.id, message_id=mensagem_status.message_id)

# -------------------------------------------------------------------------
# LOOP PRINCIPAL DA APLICAÇÃO (Event Loop Initialization)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    logging.info("Iniciando Event Loop Assíncrono do Robô...")
    asyncio.run(bot.polling(non_stop=True))

URL: https://brasilapi.com.br
License: MIT
Terms of Service
Acesso programático de informações é algo fundamental na comunicação entre sistemas, mas, para nossa surpresa, uma informação tão útil e pública quanto um CEP não consegue ser acessada diretamente por um navegador por conta da API dos Correios não possuir CORS habilitado. Dado a isso, este projeto experimental tem como objetivo centralizar e disponibilizar endpoints modernos com baixíssima latência utilizando tecnologias como Vercel Smart CDN responsável por fazer o cache das informações em atualmente 23 regiões distribuídas ao longo do mundo (incluindo Brasil). Então não importa o quão devagar for a fonte dos dados, nós queremos disponibilizá-la da forma mais rápida e moderna possível.
Recursos disponíveis
Banks
Câmbio
CEP
CEP V2
CNPJ
Corretoras
CPTEC
DDD
Feriados Nacionais
Tabela FIPE
IBGE
ISBN
NCM
PIX
Registros de domínio br
Taxas
Termos de uso
Não deixe de ler os termos de uso para o uso da API seja feito de forma correta e responsável.
ler termos
BANKS
Informações sobre sistema bancário
Retorna informações de todos os bancos do Brasil

Responses

200 Success

GET
/banks/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"ispb": "00000000",
"name": "BCO DO BRASIL S.A.",
"code": 1,
"fullName": "Banco do Brasil S.A."
}
]
Busca as informações de um banco a partir de um código

PATH PARAMETERS

code
required
integer
O código do banco
Pode ser obtido nesse endpoint
Responses

200 Success
404 O código do banco não foi encontrado

GET
/banks/v1/{code}
Response samples
200404
Content type
application/json

Copy
{
"ispb": "00000000",
"name": "BCO DO BRASIL S.A.",
"code": 1,
"fullName": "Banco do Brasil S.A."
}
CAMBIO
Informações referentes ao Cambio
Lista todas as moedas disponíveis para consulta de câmbio.

Retorna a lista completa de moedas que podem ser utilizadas como parâmetros nos endpoints de consulta de câmbio, incluindo informações sobre símbolo, nome e tipo de cada moeda.
Responses

200 Success
500 Erro interno ao buscar moedas.

GET
/cambio/v1/moedas
Response samples
200500
Content type
application/json

Copy
Expand all Collapse all
[
{
"simbolo": "USD",
"nome": "Dólar dos Estados Unidos",
"tipo_moeda": "A"
}
]
Busca pelo câmbio do Real com outra moeda, em uma data específica

Consulta o câmbio da moeda desejada em relação ao Real, em uma data específica. OBS: Para finais de semana e feriados, a data retornada será o último dia útil disponível.
PATH PARAMETERS

moeda
required
string
A moeda alvo desejada (AUD, CAD, CHF, DKK, EUR, GBP, JPY, SEK, USD). Para maiores informações, consulte: /cambio/v1/moedas
data
required
string
A data desejada, o formato deve ser: YYYY-MM-DD. Os dados só estão disponíveis a partir de 28/11/1984.
Responses

200 Success
404 API de Câmbio retorna Erro

GET
/cambio/v1/cotacao/{moeda}/{data}
Response samples
200404
Content type
application/json

Copy
Expand all Collapse all
{
"cotacoes": [
{},
{},
{},
{},
{}
],
"moeda": "USD",
"data": "2025-02-13"
}
CEP
Informações referentes a CEPs
Busca por CEP com múltiplos providers de fallback.

A busca utiliza como fonte principal o OpenCep, caso não encontre o CEP é buscado em diversos outros providers de CEP.
PATH PARAMETERS

cep
required
integer <int64>
O CEP (Código de Endereçamento Postal) é um sistema de códigos que visa racionalizar o processo de encaminhamento e entrega de correspondências através da divisão do país em regiões postais. ... Atualmente, o CEP é composto por oito dígitos, cinco de um lado e três de outro. Cada algarismo do CEP possui um significado.
Responses

200 Success
404 Todos os serviços de CEP retornaram erro.

GET
/cep/v1/{cep}
Response samples
200404
Content type
application/json

Copy
{
"cep": "89010025",
"state": "SC",
"city": "Blumenau",
"neighborhood": "Centro",
"street": "Rua Doutor Luiz de Freitas Melro",
"service": "viacep"
}
CEP V2
A geolocalização dos CEPs estão suscetíveis a erros, pois as coordenadas são provindas do OpenStreetMap. Caso encontre algum erro você poderá corrigir no próprio OpenStreetMap que será refletido no CEP V2.
Busca por CEP com múltiplos providers e geolocalização.

Versão 2 do serviço de busca por CEP que inclui informações de geolocalização (latitude e longitude) além dos dados básicos de endereço. Utiliza múltiplos provedores com sistema de fallback para garantir maior disponibilidade.
PATH PARAMETERS

cep
required
string^[0-9]{8}$|^[0-9]{5}-[0-9]{3}$
Example: 01310930
CEP a ser consultado. Deve conter exatamente 8 dígitos, com ou sem formatação (hífen). Exemplo: 01310-930 ou 01310930.
Responses

200 Success
400 CEP inválido ou mal formatado.
404 CEP não encontrado em nenhum provedor.
500 Erro interno no serviço de CEP.

GET
/cep/v2/{cep}
Response samples
200400404500
Content type
application/json

Copy
Expand all Collapse all
{
"cep": "89010025",
"state": "SC",
"city": "Blumenau",
"neighborhood": "Centro",
"street": "Rua Doutor Luiz de Freitas Melro",
"timezoneName": "America/Sao_Paulo",
"location": {
"type": "Point",
"coordinates": {}
}
}
CNPJ
Consulta de informações empresariais através do CNPJ. Retorna dados cadastrais completos, situação fiscal, sócios, atividades econômicas e outras informações da Receita Federal.
Busca por CNPJ na API Minha Receita.

Retorna informações completas de uma empresa a partir do CNPJ, incluindo dados cadastrais, situação, sócios e atividades econômicas.
PATH PARAMETERS

cnpj
required
string^[0-9]{14}$|^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-...Show pattern
Example: 19131243000197
O Cadastro Nacional da Pessoa Jurídica é um número único que identifica uma pessoa jurídica junto à Receita Federal. Deve conter 14 dígitos, com ou sem formatação (pontos, barras e hífen).
Responses

200 Success
400 CNPJ inválido ou mal formatado.
404 CNPJ não encontrado na API Minha Receita.

GET
/cnpj/v1/{cnpj}
Response samples
200400404
Content type
application/json

Copy
Expand all Collapse all
{
"uf": "SP",
"cep": "01311902",
"qsa": [
{}
],
"cnpj": "19131243000197",
"pais": null,
"email": null,
"porte": "DEMAIS",
"bairro": "BELA VISTA",
"numero": "37",
"ddd_fax": "",
"municipio": "SAO PAULO",
"logradouro": "PAULISTA 37",
"cnae_fiscal": 9430800,
"codigo_pais": null,
"complemento": "ANDAR 4",
"codigo_porte": 5,
"razao_social": "OPEN KNOWLEDGE BRASIL",
"nome_fantasia": "REDE PELO CONHECIMENTO LIVRE",
"capital_social": 0,
"ddd_telefone_1": "1123851939",
"ddd_telefone_2": "",
"opcao_pelo_mei": null,
"descricao_porte": "",
"codigo_municipio": 7107,
"cnaes_secundarios": [
{},
{},
{},
{},
{}
],
"natureza_juridica": "Associação Privada",
"regime_tributario": [
{},
{},
{},
{},
{},
{},
{}
],
"situacao_especial": "",
"opcao_pelo_simples": null,
"situacao_cadastral": 2,
"data_opcao_pelo_mei": null,
"data_exclusao_do_mei": null,
"cnae_fiscal_descricao": "Atividades de associações de defesa de direitos sociais",
"codigo_municipio_ibge": 3550308,
"data_inicio_atividade": "2013-10-03",
"data_situacao_especial": null,
"data_opcao_pelo_simples": null,
"data_situacao_cadastral": "2013-10-03",
"nome_cidade_no_exterior": "",
"codigo_natureza_juridica": 3999,
"data_exclusao_do_simples": null,
"motivo_situacao_cadastral": 0,
"ente_federativo_responsavel": "",
"identificador_matriz_filial": 1,
"qualificacao_do_responsavel": 16,
"descricao_situacao_cadastral": "ATIVA",
"descricao_tipo_de_logradouro": "AVENIDA",
"descricao_motivo_situacao_cadastral": "SEM MOTIVO",
"descricao_identificador_matriz_filial": "MATRIZ"
}
Corretoras
Informações referentes a Corretoras ativas listadas na CVM
Retorna as corretoras nos arquivos da CVM.

Responses

200 Success

GET
/cvm/corretoras/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"bairro": "LEBLON",
"cep": "22440032",
"cnpj": "02332886000104",
"codigo_cvm": "3247",
"complemento": "SALA 201",
"data_inicio_situacao": "1998-02-10",
"data_patrimonio_liquido": "2021-12-31",
"data_registro": "1997-12-05",
"email": "juridico.regulatorio@xpi.com.br",
"logradouro": "AVENIDA ATAULFO DE PAIVA 153",
"municipio": "RIO DE JANEIRO",
"nome_social": "XP INVESTIMENTOS CCTVM S.A.",
"nome_comercial": "XP INVESTIMENTOS",
"pais": "",
"status": "EM FUNCIONAMENTO NORMAL",
"telefone": "30272237",
"type": "CORRETORAS",
"uf": "RJ",
"valor_patrimonio_liquido": "5514593491.29"
}
]
Busca por corretoras nos arquivos da CVM.

PATH PARAMETERS

cnpj
required
string
O Cadastro Nacional da Pessoa Jurídica é um número único que identifica uma pessoa jurídica e outros tipos de arranjo jurídico sem personalidade jurídica junto à Receita Federal.
Responses

200 Success
404 Não foi encontrado este CNPJ na listagem da CVM.

GET
/cvm/corretoras/v1/{cnpj}
Response samples
200404
Content type
application/json

Copy
{
"bairro": "LEBLON",
"cep": "22440032",
"cnpj": "02332886000104",
"codigo_cvm": "3247",
"complemento": "SALA 201",
"data_inicio_situacao": "1998-02-10",
"data_patrimonio_liquido": "2021-12-31",
"data_registro": "1997-12-05",
"email": "juridico.regulatorio@xpi.com.br",
"logradouro": "AVENIDA ATAULFO DE PAIVA 153",
"municipio": "RIO DE JANEIRO",
"nome_social": "XP INVESTIMENTOS CCTVM S.A.",
"nome_comercial": "XP INVESTIMENTOS",
"pais": "",
"status": "EM FUNCIONAMENTO NORMAL",
"telefone": "30272237",
"type": "CORRETORAS",
"uf": "RJ",
"valor_patrimonio_liquido": "5514593491.29"
}
CPTEC
Dados meteorológicos e oceanográficos do Centro de Previsão de Tempo e Estudos Climáticos (CPTEC/INPE). Inclui previsões do tempo, condições atuais, informações sobre cidades e previsões oceânicas.
Listar localidades

Retorna listagem com todas as cidades junto a seus respectivos códigos presentes nos serviços da CPTEC. O Código destas cidades será utilizado para os serviços de meteorologia e a ondas (previsão oceânica) fornecido pelo centro. Leve em consideração que o WebService do CPTEC as vezes é instável, então se não encontrar uma determinada cidade na listagem completa, tente buscando por parte de seu nome no endpoint de busca.
Responses

200

GET
/cptec/v1/cidade
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
[
{
"nome": "São Benedito",
"estado": "CE",
"regiao": "Nordeste",
"id": 4750
}
]
Buscar localidades

Retorna listagem com todas as cidades correspondentes ao termo pesquisado junto a seus respectivos códigos presentes nos serviços da CPTEC. O Código destas cidades será utilizado para os serviços de meteorologia e a ondas (previsão oceânica) fornecido pelo centro.
PATH PARAMETERS

cityName
required
string
Example: Chiforímpola
Nome ou parte do nome da cidade a ser buscada
Responses

200
404 Not Found

GET
/cptec/v1/cidade/{cityName}
Response samples
200404
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
[
{
"nome": "São Benedito",
"estado": "CE",
"regiao": "Nordeste",
"id": 4750
}
]
Condições atuais nas capitais

Retorna condições meteorológicas atuais nas capitais do país, com base nas estações de solo de seu aeroporto.
Responses

200

GET
/cptec/v1/clima/capital
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
[
{
"codigo_icao": "SBAR",
"atualizado_em": "2021-01-27T15:00:00.974Z",
"pressao_atmosferica": "1014",
"visibilidade": "9000",
"vento": 29,
"direcao_vento": 90,
"umidade": 74,
"condicao": "ps",
"condicao_Desc": "Predomínio de Sol",
"temp": 28
}
]
Condições atuais no aeroporto (/cptec/v1/clima/aeroporto/:icaoCode)

Retorna condições meteorológicas atuais no aeroporto solicitado. Este endpoint utiliza o código ICAO (4 dígitos) do aeroporto.
PATH PARAMETERS

icaoCode
required
string
Example: SBGR
Código ICAO (4 dígitos) do aeroporto desejado
Responses

200
404 Not Found

GET
/cptec/v1/clima/aeroporto/{icaoCode}
Response samples
200404
Content type
application/json; charset=utf-8

Copy
{
"codigo_icao": "SBAR",
"atualizado_em": "2021-01-27T15:00:00.974Z",
"pressao_atmosferica": "1014",
"visibilidade": "9000",
"vento": 29,
"direcao_vento": 90,
"umidade": 74,
"condicao": "ps",
"condicao_Desc": "Predomínio de Sol",
"temp": 28
}
Previsão meteorológica para uma cidade

Retorna Pervisão meteorológica para 1 dia na cidade informada.
PATH PARAMETERS

cityCode
required
integer <int32>
Example: 999
Código da cidade fornecido pelo endpoint /cidade
Responses

200
404 Not Found

GET
/cptec/v1/clima/previsao/{cityCode}
Response samples
200404
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
{
"cidade": "Brejo Alegre",
"estado": "SP",
"atualizado_em": "2020-12-27",
"clima": [
{},
{}
]
}
Previsão meteorológica para, até, 6 dias

Retorna a previsão meteorológica para a cidade informada para um período de 1 até 6 dias. Devido a inconsistências encontradas nos retornos da CPTEC nossa API só consegue retornar com precisão o período máximo de 6 dias.
PATH PARAMETERS

cityCode
required
integer <int32>
Example: 999
Código da cidade fornecido pelo endpoint /cidade
days
required
integer <int32>
Example: 5
Quantidade de dias desejado para a previsão
Responses

200

GET
/cptec/v1/clima/previsao/{cityCode}/{days}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
{
"cidade": "Brejo Alegre",
"estado": "SP",
"atualizado_em": "2020-12-27",
"clima": [
{},
{}
]
}
Previsão meteorológica com base na latitude e longitude

Retorna a previsão meteorológica para a cidade com base na latitude e longitude informada para um período de até 7 dias. Devido a inconsistências encontradas nos retornos da CPTEC nossa API só consegue retornar com precisão o período máximo de 6 dias.
PATH PARAMETERS

lat
required
float <float32>
Example: -21.166666
Latitude de uma cidade
long
required
float <float32>
Example: -50.184665928
Longitude de uma cidade
Responses

200

GET
/cptec/v1/clima/previsao/semana/{lat}/{long}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
{
"cidade": "Brejo Alegre",
"estado": "SP",
"atualizado_em": "2020-12-27",
"clima": [
{},
{}
]
}
Previsão oceânica

Retorna a previsão oceânica para a cidade informada para 1 dia
PATH PARAMETERS

cityCode
required
integer <int32>
Example: 241
Código da cidade fornecido pelo endpoint /cidade
Responses

200

GET
/cptec/v1/ondas/{cityCode}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
{
"cidade": "Rio de Janeiro",
"estado": "RJ",
"atualizado_em": "2020-12-27",
"ondas": [
{}
]
}
Previsão oceânica para, até, 6 dias

Retorna a previsão oceânica para a cidade informada para um período de, até, 6 dias.
PATH PARAMETERS

cityCode
required
integer <int32>
Example: 241
Código da cidade fornecido pelo endpoint /cidade
days
required
integer <int32>
Example: 2
Quantidade de dias desejada para a previsão
Responses

200
400 Bad Request
404 Not Found

GET
/cptec/v1/ondas/{cityCode}/{days}
Response samples
200400404
Content type
application/json; charset=utf-8

Copy
Expand all Collapse all
{
"cidade": "Rio de Janeiro",
"estado": "RJ",
"atualizado_em": "2020-12-27",
"ondas": [
{}
]
}
DDD
Consulta de códigos DDD (Discagem Direta à Distância) brasileiros. Permite buscar informações sobre estados e cidades associadas a cada código de área telefônica.
Retorna estado e lista de cidades por DDD

Consulta informações sobre um código DDD específico, retornando o estado correspondente e a lista completa de cidades que utilizam esse código de área.
PATH PARAMETERS

ddd
required
integer <int64> [ 10 .. 99 ]
Example: 11
DDD significa Discagem Direta à Distância. É um código constituído por 2 dígitos que identificam as principais cidades do país. Deve ser informado apenas os 2 dígitos do código de área.
Responses

200 Success
400 Tamanho do DDD inválido
404 DDD não encontrado
500 Todos os serviços de DDD retornaram erro.

GET
/ddd/v1/{ddd}
Response samples
200400404500
Content type
application/json

Copy
Expand all Collapse all
{
"state": "SP",
"cities": [
"EMBU",
"VÁRZEA PAULISTA",
"VARGEM GRANDE PAULISTA",
"VARGEM",
"TUIUTI",
"TABOÃO DA SERRA",
"SUZANO",
"SÃO ROQUE",
"SÃO PAULO"
]
}
Feriados Nacionais
Consulta de feriados nacionais brasileiros. Calcula automaticamente feriados móveis (como Páscoa, Carnaval) e inclui todos os feriados fixos estabelecidos pela legislação federal.
Lista os feriados nacionais de determinado ano.

Retorna a lista completa de feriados nacionais para o ano especificado. Calcula automaticamente os feriados móveis baseados na data da Páscoa e inclui todos os feriados fixos estabelecidos pela legislação brasileira.
PATH PARAMETERS

ano
required
integer <int64> [ 1900 .. 2199 ]
Ano para calcular os feriados. Deve ser um número inteiro entre 1900 e 2199.
Responses

200 Success
400 Ano não informado.
404 Ano fora do intervalo suportado.
500 Erro interno no serviço de feriados.

GET
/feriados/v1/{ano}
Response samples
200400404500
Content type
application/json

Copy
Expand all Collapse all
[
{
"date": "2021-01-01",
"name": "Confraternização mundial",
"type": "national"
}
]
FIPE
Tabela FIPE de preços de veículos. Consulta valores de carros, motos e caminhões usados segundo a Fundação Instituto de Pesquisas Econômicas. Inclui dados históricos e atuais.
Lista as marcas de veículos referente ao tipo de veículo

PATH PARAMETERS

tipoVeiculo
string <string>
Os tipos suportados são caminhoes, carros e motos. Quando o tipo não é específicado são buscada as marcas de todos os tipos de veículos
QUERY PARAMETERS

tabela_referencia
integer <int64>
Código da tabela fipe de referência. Por padrão é utilizado o código da tabela fipe atual.
Responses

200 Success
400 Tabela de referência inválida

GET
/fipe/marcas/v1/{tipoVeiculo}
Response samples
200400
Content type
application/json

Copy
Expand all Collapse all
[
{
"nome": "AGRALE",
"valor": "102"
}
]
Consulta o preço do veículo segundo a tabela FIPE.

Retorna informações detalhadas sobre o preço de um veículo específico de acordo com a tabela FIPE, incluindo valor, marca, modelo e outras informações relevantes.
PATH PARAMETERS

codigoFipe
required
string^[0-9]{6}-[0-9]$
Example: 001004-9
Código FIPE do veículo que identifica unicamente um modelo específico na tabela FIPE. Exemplo: 001004-9 para Fiat Palio EX 1.0.
QUERY PARAMETERS

tabela_referencia
integer <int64>
Example: tabela_referencia=295
Código da tabela FIPE de referência para consulta. Se não especificado, utiliza a tabela mais atual disponível.
Responses

200 Success
400 Requisição inválida

GET
/fipe/preco/v1/{codigoFipe}
Response samples
200400
Content type
application/json

Copy
Expand all Collapse all
[
{
"valor": "R$ 6.022,00",
"marca": "Fiat",
"modelo": "Palio EX 1.0 mpi 2p",
"anoModelo": 1998,
"combustivel": "Álcool",
"codigoFipe": "001004-9",
"mesReferencia": "junho de 2021 ",
"tipoVeiculo": 1,
"siglaCombustivel": "Á",
"dataConsulta": "segunda-feira, 7 de junho de 2021 23:05"
}
]
Lista as tabelas de referência existentes.

Responses

200 Success

GET
/fipe/tabelas/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"codigo": 271,
"mes": "junho/2021 "
}
]
Lista os veículos de acordo com a marca e o tipo de veículo

PATH PARAMETERS

tipoVeiculo
required
string <string>
Os tipos suportados são caminhoes, carros e motos.
codigoMarca
required
integer <int64>
Código da marca do veiculo. Para consultar as marcas acesse a rota /fipe/marcas/v1/
QUERY PARAMETERS

tabela_referencia
integer <int64>
Código da tabela fipe de referência. Por padrão é utilizado o código da tabela fipe atual.
Responses

200 Success
400 Requisição inválida

GET
/fipe/veiculos/v1/{tipoVeiculo}/{codigoMarca}
Response samples
200400
Content type
application/json

Copy
Expand all Collapse all
[
{
"modelo": "Palio EX 1.0 mpi 2p"
}
]
Fundos de investimento
Informações referentes a Fundos de investimentos registrados na CVM
Retorna lista de fundos de investimentos registrados na CVM.

Lista de dados cadastrais de fundos de investimento estruturados e não Estruturados (ICVM 555/ICVM 175). São retornados fundos ativos e cancelados. Devido ao grande volume, utilizamos paginação para acesso dos dados.
QUERY PARAMETERS

page
number
Indica paginação necessária para pesquisa.
size
number
Tamanho de elementos em cada página (1 a 200).
Responses

200 Success

GET
/cvm/fundos/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
{
"data": [
{},
{},
{}
],
"page": 1,
"size": 3
}
Busca por detalhes de um registro de fundo na CVM.

PATH PARAMETERS

cnpj
required
string
O Cadastro Nacional da Pessoa Jurídica é um número único que identifica uma pessoa jurídica e outros tipos de arranjo jurídico sem personalidade jurídica junto à Receita Federal.
Responses

200 Success
404 Não foi encontrado este CNPJ na listagem da CVM.

GET
/cvm/fundos/v1/{cnpj}
Response samples
200404
Content type
application/json

Copy
{
"tipo_fundo": "FACFIF",
"cnpj": "00.000.732/0001-81",
"denominacao_social": "FUNDO APLIC. QUOTAS DE F.I. SANTANDER CURTO PRAZO",
"data_registro": "2003-04-30",
"data_constituicao": "1994-05-24",
"codigo_cvm": "27",
"data_cancelamento": "1999-09-03",
"situacao": "CANCELADA",
"data_inicio_situacao": "1999-09-03",
"data_inicio_atividade": null,
"data_inicio_exercicio": null,
"data_fim_exercicio": null,
"classe": null,
"data_inicio_classe": null,
"rentabilidade": null,
"condominio": null,
"cotas": null,
"fundo_exclusivo": null,
"tributacao_longo_prazo": null,
"publico_alvo": null,
"entidade_investimento": null,
"taxa_performance": null,
"informacao_taxa_performance": null,
"taxa_administracao": null,
"informacao_taxa_administracao": null,
"valor_patrimonio_liquido": null,
"data_patrimonio_liquido": null,
"diretor": null,
"cnpj_administrador": null,
"administrador": null,
"tipo_pessoa_gestor": null,
"cpf_cnpj_gestor": null,
"gestor": null,
"cnpj_auditor": null,
"auditor": null,
"cnpj_custodiante": null,
"custodiante": null,
"cnpj_controlador": null,
"controlador": null,
"investimento_externo": null,
"classe_anbima": null
}
IBGE
Informações sobre estados Provenientes do IBGE
Retorna os municípios da unidade federativa

Retorna uma lista de municípios pertencentes à unidade federativa. Cada município contém o nome e o código IBGE correspondente.
PATH PARAMETERS

siglaUF
required
string <string>
Sigla da unidade federativa, por exemplo SP, RJ, SC, etc.
QUERY PARAMETERS

providers
string <string>
Lista de provedores separados por vírgula.
Provedores disponíveis:
dados-abertos-br
gov
wikipedia
Responses

200 Successo
400 UF ausente ou com formato inválido (deve ser exatamente duas letras A–Z)
404 Sigla com formato válido, mas não corresponde a um estado brasileiro
422 Parâmetro providers vazio ou com valores não suportados
500 Erro interno ao consultar os provedores

GET
/ibge/municipios/v1/{siglaUF}
Response samples
200400404422
Content type
application/json

Copy
Expand all Collapse all
[
{
"nome": "Tubarão",
"codigo_ibge": "421870705"
},
{
"nome": "Tunápolis",
"codigo_ibge": "421875605"
},
{
"nome": "Turvo",
"codigo_ibge": "421880605"
},
{
"nome": "Morro Chato",
"codigo_ibge": "421880620"
},
{
"nome": "União do Oeste",
"codigo_ibge": "421885505"
},
{
"nome": "Urubici",
"codigo_ibge": "421890505"
},
{
"nome": "Águas Brancas",
"codigo_ibge": "421890510"
},
{
"nome": "Santa Teresinha",
"codigo_ibge": "421890520"
},
{
"nome": "Urupema",
"codigo_ibge": "421895405"
},
{
"nome": "Urussanga",
"codigo_ibge": "421900205"
},
{
"nome": "Vargeão",
"codigo_ibge": "421910105"
},
{
"nome": "Vargem",
"codigo_ibge": "421915005"
},
{
"nome": "Vargem Bonita",
"codigo_ibge": "421917605"
},
{
"nome": "Vidal Ramos",
"codigo_ibge": "421920005"
},
{
"nome": "Videira",
"codigo_ibge": "421930905"
},
{
"nome": "Anta Gorda",
"codigo_ibge": "421930910"
},
{
"nome": "Lourdes",
"codigo_ibge": "421930925"
},
{
"nome": "Vitor Meireles",
"codigo_ibge": "421935805"
},
{
"nome": "Barra da Prata",
"codigo_ibge": "421935810"
},
{
"nome": "Witmarsum",
"codigo_ibge": "421940805"
},
{
"nome": "Xanxerê",
"codigo_ibge": "421950705"
},
{
"nome": "Cambuinzal",
"codigo_ibge": "421950715"
},
{
"nome": "Xavantina",
"codigo_ibge": "421960605"
},
{
"nome": "Linha das Palmeiras",
"codigo_ibge": "421960610"
},
{
"nome": "Xaxim",
"codigo_ibge": "421970505"
},
{
"nome": "Anita Garibaldi",
"codigo_ibge": "421970511"
},
{
"nome": "Diadema",
"codigo_ibge": "421970516"
},
{
"nome": "Zortéa",
"codigo_ibge": "421985305"
}
]
Retorna informações de todos estados do Brasil

Responses

200 Success

GET
/ibge/uf/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"id": 35,
"sigla": "SP",
"nome": "São Paulo",
"regiao": {},
"populacao_estimada": 45969144,
"periodo": "2024"
}
]
Busca as informações de um estado a partir da sigla ou código

Responses

200 Success
404 O código / sigla do estado não foi encontrado

GET
/ibge/uf/v1/{code}
Response samples
200404
Content type
application/json

Copy
Expand all Collapse all
{
"id": 35,
"sigla": "SP",
"nome": "São Paulo",
"regiao": {
"id": 3,
"sigla": "SE",
"nome": "Sudeste"
},
"populacao_estimada": 45969144,
"periodo": "2024"
}
ISBN
Informações sobre livros publicados no Brasil (prefixo 65 ou 85) a partir do ISBN, um sistema internacional de identificação de livros que utiliza números para classificá-los por título, autor, país, editora e edição.
Informações sobre o livro a partir do ISBN

Busca informações detalhadas de um livro utilizando seu código ISBN. Suporta múltiplos provedores de dados e formatos ISBN-10 e ISBN-13.
PATH PARAMETERS

isbn
required
string^[0-9]{10}([0-9]{3})?$|^[0-9-]{13,17}$
Example: 9788545702870
O código ISBN do livro. Aceita tanto o formato de 10 dígitos (obsoleto) quanto o de 13 dígitos (atual). Pode conter ou não traços de formatação.
QUERY PARAMETERS

providers
Array of strings
Items Enum: "cbl" "mercado-editorial" "open-library" "google-books"
Example: providers=cbl,google-books
Lista de provedores separados por vírgula para busca do ISBN. Se não especificado, será realizada busca em todos os provedores disponíveis, retornando o resultado mais rápido.
Responses

200 Sucesso
400 ISBN inválido
404 ISBN não encontrado
500 Todos os serviços de ISBN retornaram erro

GET
/isbn/v1/{isbn}
Response samples
200400404500
Content type
application/json

Copy
Expand all Collapse all
{
"isbn": "9788545702870",
"title": "Akira",
"subtitle": null,
"authors": [
"KATSUHIRO OTOMO",
"DRIK SADA",
"CASSIUS MEDAUAR",
"MARCELO DEL GRECO",
"DENIS TAKATA"
],
"publisher": "Japorama Editora e Comunicação",
"synopsis": "Um dos marcos da ficção científica oriental que revolucionou a chegada dos mangás e da cultura pop japonesa no Ocidente retorna em uma nova edição especial. Após atropelar uma criança de aparência estranha, Tetsuo Shima (o melhor amigo de Kaneda), começa a sentir algumas reações anormais. Isso acaba chamando a atenção do governo que está projetando diversas experiências secretas e acabam sequestrando Tetsuo. Nesta aventura cheia de ficção, Kaneda entra em cena para salvar o amigo, enquanto uma terrível e monstruosa entidade ameaça despertar.",
"dimensions": {
"width": 17.5,
"height": 25.7,
"unit": "CENTIMETER"
},
"year": 2017,
"format": "PHYSICAL",
"page_count": 364,
"subjects": [
"Cartoons; caricaturas e quadrinhos",
"mangá",
"motocicleta",
"gangue",
"Delinquência"
],
"location": "SÃO PAULO, SP",
"retail_price": null,
"cover_url": null,
"provider": "cbl"
}
NCM
Nomenclatura Comum do Mercosul (NCM) - Sistema de classificação de produtos para fins de tributação e controle de comércio exterior. Inclui consulta, busca e listagem completa de códigos NCM.
Retorna informações de todos os NCMs

Lista completa de todos os códigos NCM (Nomenclatura Comum do Mercosul) cadastrados. Inclui código, descrição e informações de vigência de cada NCM.
Responses

200 Success

GET
/ncm/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"codigo": "3305.10.00",
"descricao": "- Xampus",
"data_inicio": "2022-04-01",
"data_fim": "9999-12-31",
"tipo_ato": "Res Camex",
"numero_ato": "000272",
"ano_ato": "2021"
}
]
Pesquisa por NCMs a partir de um código ou descrição.

Permite buscar códigos NCM utilizando código parcial ou palavras-chave na descrição. Útil para encontrar NCMs relacionados a um produto específico.
Responses

200 Success

GET
/ncm/v1?search={code}
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"codigo": "3305.10.00",
"descricao": "- Xampus",
"data_inicio": "2022-04-01",
"data_fim": "9999-12-31",
"tipo_ato": "Res Camex",
"numero_ato": "000272",
"ano_ato": "2021"
}
]
Busca as informações de um NCM a partir de um código

Retorna informações detalhadas de um código NCM específico, incluindo descrição, dados de vigência e informações do ato legal que o criou.
PATH PARAMETERS

code
required
string
Example: 33051000
Código NCM a ser consultado. Pode conter ou não pontos de formatação (ex: 3305.10.00 ou 33051000).
Responses

200 Success
404 O código do NCM não foi encontrado

GET
/ncm/v1/{code}
Response samples
200404
Content type
application/json

Copy
{
"codigo": "3305.10.00",
"descricao": "- Xampus",
"data_inicio": "2022-04-01",
"data_fim": "9999-12-31",
"tipo_ato": "Res Camex",
"numero_ato": "000272",
"ano_ato": "2021"
}
PIX
Informações referentes ao PIX
Retorna informações de todos os participantes do PIX no dia atual ou último dia útil.

Os dados são obtidos diretamente do Banco Central do Brasil.
Em novembro de 2025 o banco central deixou de fornecer a data de início de operação dos participantes, por isso este campo pode estar vazio para alguns participantes.
Responses

200 Success
500 Error

GET
/pix/v1/participants
Response samples
200500
Content type
application/json

Copy
Expand all Collapse all
[
{
"ispb": "360305",
"nome": "CAIXA ECONOMICA FEDERAL",
"nome_reduzido": "CAIXA ECONOMICA FEDERAL",
"modalidade_participacao": "PDCT",
"tipo_participacao": "DRCT",
"inicio_operacao": "2020-11-03T09:30:00.000Z"
}
]
REGISTRO BR
Avalia um dominio no registro.br
Avalia o status de um dominio .br

PATH PARAMETERS

domain
required
string
O domínio ou nome a ser avaliado
Responses

200 Success
400 Bad Request

GET
/registrobr/v1/{domain}
Response samples
200400
Content type
application/json

Copy
Expand all Collapse all
{
"status_code": 2,
"status": "REGISTERED",
"fqdn": "brasilapi.com.br",
"fqdnace": "",
"hosts": [
"bob.ns.cloudflare.com",
"lily.ns.cloudflare.com"
],
"publication-status": "published",
"expires-at": "2022-09-23T00:00:00-03:00",
"suggestions": [
"agr.br",
"app.br",
"art.br",
"blog.br",
"dev.br",
"eco.br",
"esp.br",
"etc.br",
"far.br",
"flog.br",
"imb.br",
"ind.br",
"inf.br",
"log.br",
"net.br",
"ong.br",
"rec.br",
"seg.br",
"srv.br",
"tec.br",
"tmp.br",
"tur.br",
"tv.br",
"vlog.br",
"wiki.br"
]
}
TAXAS
Taxas de juros e índices oficiais
Retorna as taxas de juros e alguns índices oficiais do Brasil

Responses

200 Success

GET
/taxas/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"nome": "CDI",
"valor": 7.65
}
]
Busca as informações de uma taxa a partir do seu nome/sigla

Responses

200 Success
404 Taxa ou Índice não foi encontrada

GET
/taxas/v1/{sigla}
Response samples
200404
Content type
application/json

Copy
{
"nome": "CDI",
"valor": 7.65
}
TICKERS
Tickers do Brasil
Retorna a lista de tickers das empresas listadas na B3

Endpoint para obter a lista completa de tickers de empresas listadas na B3 (Brasil, Bolsa, Balcão)
Responses

200 Lista de tickers retornada com sucesso
500 Erro ao obter os dados dos tickers

GET
/tickers/b3/acoes/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"code_CVM": "1023",
"issuing_company": "BBAS",
"company_name": "BCO BRASIL S.A.",
"trading_name": "BRASIL",
"cnpj": "191",
"market_indicator": "18",
"type_BDR": "",
"date_listing": "18/06/1921",
"status": "A",
"segment": "Bancos",
"segment_eng": "Banks",
"type": "1",
"market": "NM"
}
]
Retorna a lista de tickers de fundos de investimento listados na B3

Endpoint para obter a lista completa de tickers de fundos de investimento listados na B3 de acordo com o tipo especificado
PATH PARAMETERS

typeFund
required
string
Enum: "FII" "SETORIAL" "FIAGRO-FII" "FIAGRO-FIDC" "FIAGRO-FIP" "FIP" "FIA"
Tipo de fundo de investimento
Responses

200 Lista de tickers de fundos retornada com sucesso
400 Tipo de fundo inválido ou não especificado
500 Erro ao obter os dados dos tickers

GET
/tickers/b3/fundos/v1/{typeFund}
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"id": 1234,
"type_name": "FII",
"acronym": "HGLG11",
"fund_name": "CSHG LOGÍSTICA FUNDO DE INVESTIMENTO IMOBILIÁRIO",
"trading_name": "CSHG LOGÍSTICA"
}
]
TUSS
Termos e códigos TUSS (Terminologia Unificada da Saúde Suplementar). Permite listagem completa e busca por nome e por código.
Lista termos TUSS (Terminologia Unificada da Saúde Suplementar) com suporte a busca por nome e código

Retorna a lista completa de termos TUSS. Quando parâmetros de busca são fornecidos, retorna somente os itens que correspondem ao filtro. A busca por nome é case-insensitive e acento-insensitive; a busca por código considera apenas dígitos e casa pelo início do código. Suporta paginação via parâmetros limit e offset.
QUERY PARAMETERS

name
string
Example: name=Consulta
Busca parcial por nome do termo TUSS (ignora acentos e caixa).
tuss
string
Example: tuss=1010
Busca por código TUSS (somente dígitos), compara pelo início do código.
limit
integer >= 1
Example: limit=50
Quantidade máxima de itens a retornar (paginação).
offset
integer >= 0
Deslocamento inicial para paginação (número de itens a pular).
Responses

200 Success

GET
/tuss/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
{
"total": 25731,
"limit": 20,
"offset": 0,
"items": [
{},
{}
]
}
Detalhe de um termo TUSS pelo código

PATH PARAMETERS

tuss
required
string
Example: 10101012
Código TUSS (somente dígitos)
Responses

200 Success
404 Código TUSS não encontrado

GET
/tuss/v1/{tuss}
Response samples
200404
Content type
application/json

Copy
{
"tuss": "10101012",
"name": "Consulta em consultório (no horário normal ou preestabelecido)"
}
Busca avançada de termos TUSS

Busca com campo livre q mais filtros opcionais name e tuss. Suporta modos de correspondência via match=prefix|exact, ordenação por sort=tuss|name e order=asc|desc, projeção de campos via fields, além de paginação limit e offset.
QUERY PARAMETERS

q
string
Example: q=consulta 1010
Busca livre; tokens com dígitos aplicam-se ao código TUSS, textos ao nome.
name
string
Example: name=Consulta
Filtro por nome (acento-insensitive).
tuss
string
Example: tuss=10101012
Filtro por código TUSS (somente dígitos).
match
string
Enum: "prefix" "exact"
Example: match=prefix
Modo de correspondência para q, name e tuss.
sort
string
Enum: "tuss" "name"
Example: sort=tuss
Campo de ordenação.
order
string
Enum: "asc" "desc"
Example: order=asc
Direção da ordenação.
fields
string
Example: fields=tuss,name
Projeção de campos (lista separada por vírgula).
limit
integer >= 1
Example: limit=50
Quantidade máxima de itens a retornar (paginação).
offset
integer >= 0
Deslocamento inicial para paginação.
Responses

200 Success

GET
/tuss/v1/search
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
{
"total": 57,
"limit": 20,
"offset": 0,
"items": [
{},
{}
]
}
Autocomplete de termos TUSS

Sugestões leves para digitação com correspondência por prefixo em name e tuss. Limite padrão 10, máximo 20.
QUERY PARAMETERS

q
string
Example: q=consu
Texto livre para sugestão.
name
string
Example: name=Consu
Prefixo do nome.
tuss
string
Example: tuss=1010
Prefixo do código TUSS (somente dígitos).
limit
integer [ 1 .. 20 ]
Example: limit=10
Quantidade máxima de sugestões (padrão 10).
Responses

200 Success

GET
/tuss/v1/autocomplete
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
[
{
"tuss": "1010",
"name": "Consulta"
},
{
"tuss": "10101012",
"name": "Consulta em consultório (no horário normal ou preestabelecido)"
}
]
Fundos
Retorna lista de fundos de investimentos registrados na CVM.

Lista de dados cadastrais de fundos de investimento estruturados e não Estruturados (ICVM 555/ICVM 175). São retornados fundos ativos e cancelados. Devido ao grande volume, utilizamos paginação para acesso dos dados.
QUERY PARAMETERS

page
number
Indica paginação necessária para pesquisa.
size
number
Tamanho de elementos em cada página (1 a 200).
Responses

200 Success

GET
/cvm/fundos/v1
Response samples
200
Content type
application/json

Copy
Expand all Collapse all
{
"data": [
{},
{},
{}
],
"page": 1,
"size": 3
}
Busca por detalhes de um registro de fundo na CVM.

PATH PARAMETERS

cnpj
required
string
O Cadastro Nacional da Pessoa Jurídica é um número único que identifica uma pessoa jurídica e outros tipos de arranjo jurídico sem personalidade jurídica junto à Receita Federal.
Responses

200 Success
404 Não foi encontrado este CNPJ na listagem da CVM.

GET
/cvm/fundos/v1/{cnpj}
Response samples
200404
Content type
application/json

Copy
{
"tipo_fundo": "FACFIF",
"cnpj": "00.000.732/0001-81",
"denominacao_social": "FUNDO APLIC. QUOTAS DE F.I. SANTANDER CURTO PRAZO",
"data_registro": "2003-04-30",
"data_constituicao": "1994-05-24",
"codigo_cvm": "27",
"data_cancelamento": "1999-09-03",
"situacao": "CANCELADA",
"data_inicio_situacao": "1999-09-03",
"data_inicio_atividade": null,
"data_inicio_exercicio": null,
"data_fim_exercicio": null,
"classe": null,
"data_inicio_classe": null,
"rentabilidade": null,
"condominio": null,
"cotas": null,
"fundo_exclusivo": null,
"tributacao_longo_prazo": null,
"publico_alvo": null,
"entidade_investimento": null,
"taxa_performance": null,
"informacao_taxa_performance": null,
"taxa_administracao": null,
"informacao_taxa_administracao": null,
"valor_patrimonio_liquido": null,
"data_patrimonio_liquido": null,
"diretor": null,
"cnpj_administrador": null,
"administrador": null,
"tipo_pessoa_gestor": null,
"cpf_cnpj_gestor": null,
"gestor": null,
"cnpj_auditor": null,
"auditor": null,
"cnpj_custodiante": null,
"custodiante": null,
"cnpj_controlador": null,
"controlador": null,
"investimento_externo": null,
"classe_anbima": null
}
