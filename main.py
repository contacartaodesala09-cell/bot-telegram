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
            "url_base": "https://exemplo-paga1.com{termo}"
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
