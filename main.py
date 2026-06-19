import os
import telebot
import requests

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'ajuda'])
def enviar_boas_vindas(message):
    bot.reply_to(message, "Olá! Envie o CNPJ que deseja buscar.\nExemplo: /buscar 00000000000191")

@bot.message_handler(commands=['buscar'])
def realizar_busca(message):
    # Pega o texto digitado e remove espaços ou pontos
    termo = message.text.replace('/buscar', '').strip().replace('.', '').replace('/', '').replace('-', '')
    
    if not termo:
        bot.reply_to(message, "Por favor, digite o CNPJ após o comando. Ex: /buscar 00000000000191")
        return
        
    bot.reply_to(message, f"🔍 Consultando CNPJ: {termo} na base de dados...")
    
    try:
        # Consulta uma API real e gratuita de CNPJ
        url = f"https://brasilapi.com.br{termo}"
        resposta = requests.get(url)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            
            # Organiza as informações para exibir no Telegram
            resultado = (
                f"📋 **DADOS DA EMPRESA** 📋\n\n"
                f"🏢 **Razão Social:** {dados.get('razao_social')}\n"
                f"🏷️ **Nome Fantasia:** {dados.get('nome_fantasia', 'Não informado')}\n"
                f"📌 **Situação Cadastral:** {dados.get('descricao_situacao_cadastral')}\n"
                f"📞 **Telefone:** {dados.get('ddd_telefone1', 'Não informado')}\n"
                f"📍 **Cidade/UF:** {dados.get('municipio')} - {dados.get('uf')}\n"
                f"📅 **Abertura:** {dados.get('data_inicio_atividade')}"
            )
        else:
            resultado = "❌ CNPJ não encontrado ou inválido. Verifique os números."
            
    except Exception as e:
        resultado = "⚠️ Erro temporário ao consultar a base de dados."

    bot.reply_to(message, resultado)

if __name__ == "__main__":
    bot.infinity_polling()
