import asyncio
from telethon import TelegramClient, events
import MetaTrader5 as mt5
import logging
from funzioni import *  # Assicurati che le funzioni necessarie siano nel modulo funzioni

# Imposta i dati di accesso per il client Telegram
api_id = 21280755
api_hash = "f339f77b7c693302c8d318a91f86c1b0"
telegram_client_name = "my_session"
nome_db = "database"
dict_messageid_orderid = {}
comandi = carica_dizionario_da_json("comandi.json")

# Configura il logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

#configurazione database
conn = connessione_db(nome_db)
#creazione delle tabele se non esistono
crea_tabelle_database(conn)

# Configura il client Telegram
client = TelegramClient(telegram_client_name, api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    # Log iniziale del messaggio
    # logging.info(f"messaggio ricevuto: {event}.")
    allowed_chats = [621182607]  # Chat consentite, aggiungi gli ID delle chat
    
    if event.chat_id not in allowed_chats:
        logging.info(f"Chat non consentita: {event.chat_id}.")
        return
    
    if event.is_reply:
        # Se il messaggio è una risposta, esegui azioni specifiche
        logging.info("Il messaggio è una risposta, ma non sono state specificate azioni.")




    else:
        # Se non è una risposta, prosegui con il processo del comando
        message = event.raw_text
        # logging.info(f"messaggio ricevuto: {message}")
        
        command = parse_command(message)
        # logging.info(f"Comando ricevuto: {command}")
        
        if command:
            order_type = command["order_type"]
            symbol = command["symbol"]
            entry_price = command["entry_price"]
            take_profits = command["take_profits"]
            stop_loss = command["stop_loss"]

            if not symbol or not order_type:
                logging.warning("Messaggio non valido.")
                return

            # Imposta il volume del trade
            volume = 0.01  # Volume fisso per ogni trade. Puoi personalizzarlo
            num_minutes = 3  # Sostituire con il numero di minuti
            messagge_id = event.message.id  # Associa l'ordine al messaggio
            max_retries = 3  # Numero massimo di tentativi per inviare l'ordine

            # Invia un ordine per ogni Take Profit
            for tp in take_profits:
                for retries in range(max_retries):
                    success = send_order(order_type, symbol, volume, stop_loss, tp, entry_price, messagge_id, num_minutes)
                    if success is not None:
                        manage_dict_messageid_orderid(dict_messageid_orderid, messagge_id, success, inserisci_id_database_async, conn)  # Inserisce coppia nel dizionario e salva nel db
                        monitor_order_process(success, tp, stop_loss, symbol, order_type, messagge_id, conn, dict_messageid_orderid)  # Avvia il processo di monitoraggio dell'ordine
                        break
                    else:
                        logging.info(f"Impossibile inviare l'ordine dopo {max_retries} tentativi.")
        else:
            # Messaggio di segnale non valido
            logging.warning("Messaggio non valido.")



# Avvia il client Telegram
async def main():


    logging.info("Avvio del client Telegram...")
    await client.start()
    logging.info("Client Telegram avviato.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        initialize_mt5()
        asyncio.run(main())  # Utilizza asyncio.run per avviare il client
    finally:
        mt5.shutdown()
