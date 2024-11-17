from telethon import TelegramClient, events
import MetaTrader5 as mt5
import logging
import re
import json
import multiprocessing
from datetime import datetime, timedelta
import sqlite3
import threading
import asyncio

def initialize_mt5():
    if not mt5.initialize():
        logging.error(f"MetaTrader5 non inizializzato, errore: {mt5.last_error()}")
        raise SystemExit("Errore nella connessione a MetaTrader 5")
    logging.info("MetaTrader 5 inizializzato con successo.")


def connessione_db(nome_db):
    return sqlite3.connect(f"{nome_db}.db")


def close_order(order_ticket, message_id, conn, dict_messageid_orderid):
    if order_ticket is None:
        return False

    # Ottieni l'ordine
    ordine = mt5.order_get(order_ticket)
    if ordine is None:
        return False
    
        # Determina l'azione da eseguire (chiusura dell'ordine)
    if ordine.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT, 
                        mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP]:
        action = mt5.TRADE_ACTION_REMOVE  # Rimuove un ordine pendente
    else:
        action = mt5.TRADE_ACTION_DEAL  # Chiude un ordine aperto

    # Chiudi l'ordine (sia aperto che pendente)
    result = mt5.order_send(
        action=action,
        symbol=ordine.symbol,
        volume=ordine.volume,
        type=ordine.type,
        price=ordine.price,
        sl=ordine.sl,
        tp=ordine.tp,
        magic=ordine.magic,
        ticket=order_ticket
    )
    
    # Restituisce True se l'ordine è stato chiuso con successo
    if result > 0:
        cancella_coppia_dict_messageid_orderid(dict_messageid_orderid, message_id, order_ticket, conn)



def send_order(order_type, symbol, volume, sl, tp, entry_price, magic,num_minutes):

    #configuriamo il tipo d'ordine
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logging.error(f"Errore nel recupero del prezzo per {symbol}.")
        return None

    market_price = tick.ask if order_type == "BUY" else tick.bid

    if order_type == "BUY":
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if float(entry_price) <= market_price else mt5.ORDER_TYPE_BUY_STOP
    elif order_type == "SELL":
        order_type = mt5.ORDER_TYPE_SELL_LIMIT if float(entry_price) >= market_price else mt5.ORDER_TYPE_SELL_STOP
    else:
        logging.error(f"Tipo di ordine {order_type} non valido.")
        return None

    # Ottieni i dati del simbolo e verifica la visibilità
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logging.error(f"Simbolo {symbol} non trovato.")
        return None

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):  # Attiva il simbolo nel terminale
            logging.error(f"Impossibile attivare il simbolo {symbol}.")
            return None
        
    #TO DO: creare una classe con le variabili per l'ordine
    deviation = 0  # Valore standard, puoi personalizzarlo
    action = mt5.TRADE_ACTION_PENDING
    now = datetime.now()
    experation = now + timedelta(minutes=num_minutes)

    # Crea l'ordine
    request = {
        "action": action,
        "symbol": symbol,  
        "volume": volume,  # Utilizza il valore di volume,
        "type": order_type,  
        "price": float(entry_price), 
        "sl": float(sl),  
        "tp": float(tp),  
        "deviation": 0,
        "magic": 0,  
        "comment": "Trade inviato da Telegram",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "expiration_time": experation,
    }
    
    # Invia l'ordine
    result = mt5.order_send(request)

    return result.order



def parse_command(message):
    """Parses a trading command message to extract key trading details.

    The function uses regular expressions to identify and extract:
        - `pair`: A currency pair (e.g., "EUR/USD").
        - `action`: The trading action, either "BUY" or "SELL".
        - `entry_price`: The entry price for the trade.
        - `sl`: The stop loss price.
        - `tp1`, `tp2`, `tp3`: Three take profit prices.

    Args:
        message (str): The message containing the trading command.

    Returns:
        dict: A dictionary with the following keys and extracted values:
            - 'pair' (str): The currency pair.
            - 'action' (str): The trading action ("BUY" or "SELL").
            - 'entry_price' (float): The entry price.
            - 'sl' (float): The stop loss price.
            - 'tp1' (float): The first take profit price.
            - 'tp2' (float): The second take profit price.
            - 'tp3' (float): The third take profit price.
        None: If parsing fails or the message format is invalid.
    """
    try:
        # Compilazione dei pattern per le espressioni regolari
        pair_pattern = re.compile(r"([A-Z]{3})/([A-Z]{3})")  # Modifica per separare le valute
        action_pattern = re.compile(r"(BUY|SELL)")
        entry_pattern = re.compile(r"Entry price\s+(\d+\.\d+)")
        sl_pattern = re.compile(r"SL\s+(\d+\.\d+)")
        tp_pattern = re.compile(r"TP\d\s*:\s*(\d+\.\d+)")

        # Esecuzione delle ricerche con i pattern compilati
        pair_match = pair_pattern.search(message)
        action_match = action_pattern.search(message)
        entry_match = entry_pattern.search(message)
        sl_match = sl_pattern.search(message)
        tp_matches = tp_pattern.findall(message)

        if not (pair_match and action_match and entry_match and sl_match and len(tp_matches) == 3):
            logging.error(f"Errore nel parsing del messaggio")
            return None

        # Estrazione dei valori
        pair = pair_match.group(1) + pair_match.group(2)  # Rimuove la "/"
        action = action_match.group(1)
        entry_price = entry_match.group(1)
        sl = sl_match.group(1)
        tp1, tp2, tp3 = tp_matches[0], tp_matches[1], tp_matches[2]

        return {
            "order_type": action,
            "symbol": pair,
            "entry_price": entry_price,
            "take_profits": [tp1, tp2, tp3],
            "stop_loss": sl,
        }
    except Exception as e:
        logging.error(f"Errore nel parsing del messaggio: {e}")
        return None



def crea_tabelle_database(conn):
    c = conn.cursor()
    c.execute('''  
        CREATE TABLE IF NOT EXISTS MessageIdOrderId (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            MessageId INTEGER,
            OrderId INTEGER
        )
    ''')
    conn.commit()


def inserisci_MessageIdOrderId_database(conn, data_batch):
    """
    Inserisce un batch di coppie MessageId e OrderId nel database.
    
    Args:
        conn (sqlite3.Connection): Connessione al database SQLite.
        data_batch (list): Lista di tuple (MessageId, OrderId).
    """
    try:
        c = conn.cursor()
        c.executemany("INSERT INTO MessageIdOrderId (MessageId, OrderId) VALUES (?,?)", data_batch)
        conn.commit()
    except Exception as e:
        logging.error(f"Errore durante la funzione inserisci_id_database con errore: {e}")


def inserisci_id_database_async(conn, data_batch):
    """
    Inserisce un batch di dati nel database in un thread separato.
    
    Args:
        conn (sqlite3.Connection): Connessione al database SQLite.
        data_batch (list): Lista di tuple (MessageId, OrderId).
    """
    def worker(conn, data_batch):
        try:
            #logging.info(f"Inserimento batch di {len(data_batch)} righe...")
            inserisci_MessageIdOrderId_database(conn, data_batch)
        except Exception as e:
            logging.error(f"Errore durante la funzione inserisci_id_database_async con errore: {e}")

    # Crea un nuovo thread per l'inserimento
    thread = threading.Thread(target=worker, args=(conn, data_batch))
    thread.start()


def manage_dict_messageid_orderid(dict_messageid_orderid, message_id, array_order_id, insert_func, conn):
    # Aggiunge una nuova coppia al dizionario
    dict_messageid_orderid[message_id] = array_order_id
    
    # Controlla se il dizionario ha raggiunto 1000 righe
    if len(dict_messageid_orderid) >= 1000:
        # Estrai le prime 100 coppie
        first_100 = list(dict_messageid_orderid.items())[:100]
        
        # Inserisci i dati nel database (asincrono)
        insert_func(conn, first_100)
        
        # Elimina le prime 100 coppie
        for key, _ in first_100:
            dict_messageid_orderid.pop(key, None)


def cancella_coppia_dict_messageid_orderid(dict_messageid_orderid, message_id, order_id, conn):
    # Cancella la coppia dal dizionario
    if message_id in dict_messageid_orderid and dict_messageid_orderid[message_id] == order_id:
        del dict_messageid_orderid[message_id]

    # Se la coppia non è più presente nel dizionario, avvia un thread per cancellarla dal DB
    if message_id not in dict_messageid_orderid or dict_messageid_orderid[message_id] != order_id:
        threading.Thread(target=asyncio.run, args=(cancella_MessageIdOrderId_db(message_id, order_id, conn),)).start()



async def cancella_MessageIdOrderId_db(message_id, order_id,conn):
    """
    Cancella una coppia MessageId e OrderId dalla tabella nel database.
    
    Args:
        conn (sqlite3.Connection): Connessione al database SQLite.
        message_id (str): MessageId da cancellare.
        order_id (str): OrderId da cancellare.
    """
    try:
        c = conn.cursor()
        c.execute("DELETE FROM MessageIdOrderId WHERE MessageId = ? AND OrderId = ?", (message_id, order_id))
        conn.commit()
    except Exception as e:
        logging.error(f"Errore durante la funzione cancella_id_database con errore: {e}")


def chiudi_connessione_db(conn):
    conn.close()



def monitor_order(order_ticket, tp, sl, symbol, order_type, message_id, conn, dict_messageid_orderid):
    """Monitors a trade order and closes it when the Take Profit or Stop Loss is reached.

    The function continuously checks the current market price for the specified symbol 
    and compares it with the Take Profit (TP) and Stop Loss (SL) levels. If the price 
    reaches either of these levels, the order is closed.

    Args:
        order_ticket (int): The unique ID of the order to monitor.
        tp (float): The Take Profit price.
        sl (float): The Stop Loss price.
        symbol (str): The trading symbol (e.g., "EURUSD").
        order_type (str): The type of order ("BUY" or "SELL").

    Returns:
        None: The function runs indefinitely, continuously monitoring the order.
    
    Notes:
        - The function initializes the MetaTrader 5 platform and checks if the symbol is visible.
        - If the symbol is not active, it attempts to select it using `mt5.symbol_select()`.
        - The market price is retrieved using `mt5.symbol_info_tick()` and compared with TP/SL.
        - If the TP or SL is reached, the order is closed using a helper function `close_order()`.
    """

    last_tick = None
    if not mt5.initialize():
        # Se l'inizializzazione fallisce, logga l'errore
        error_code, error_msg = mt5.last_error()
        logging.error(f"Impossibile inizializzare MetaTrader 5. Codice errore: {error_code}, Messaggio: {error_msg}")
        return False

    # Verifica che il simbolo sia disponibile e visibile
    symbol_info = mt5.symbol_info("EURUSD")
    if not symbol_info or not symbol_info.visible:
        logging.error(f"Simbolo {symbol} non trovato o non visibile.")
        

    # Se il simbolo non è attivo, proviamo a selezionarlo
    if not mt5.symbol_select(symbol, True):
        logging.error(f"Impossibile selezionare il simbolo {symbol}.")


    while True:
        # Ottieni il tick di mercato corrente
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
                #logging.warning(f"Errore nel recupero dei tick per {symbol}.")
                continue

        # Controlla se il tick di mercato ha cambiato
        if tick != last_tick:
            last_tick = tick

            # Controlla se il TP o SL sono stati raggiunti
            if order_type == "BUY":
                if tick.ask >= tp:
                    logging.info(f"Take Profit hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket, message_id, conn, dict_messageid_orderid)
                    break
                elif tick.ask <= sl:
                    logging.info(f"Stop Loss hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket, message_id, conn, dict_messageid_orderid)
                    break
            elif order_type == "SELL":
                if tick.bid <= tp:
                    logging.info(f"Take Profit hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket, message_id, conn, dict_messageid_orderid)
                    break
                elif tick.bid >= sl:
                    logging.info(f"Stop Loss hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket, message_id, conn, dict_messageid_orderid)
                    break



def monitor_order_process(array_success, tp, sl, symbol, order_type, message_id, conn, dict_messageid_orderid):
    for order_id in array_success:
        process = multiprocessing.Process(target=monitor_order, args=(order_id, tp, sl, symbol, order_type, message_id, conn, dict_messageid_orderid))
        process.daemon = False  # Non è un processo demon, continuerà anche quando il programma principale termina
        process.start()


def carica_dizionario_da_json(nome_file):
    """
    Carica un dizionario da un file JSON.
    
    Parametri:
    nome_file (str): Il nome del file JSON da cui caricare il dizionario.
    
    Restituisce:
    dict: Il dizionario caricato dal file JSON.
    """
    try:
        with open(nome_file, 'r') as file:
            dizionario = json.load(file)
        return dizionario
    except FileNotFoundError:
        logging.error(f"Errore: il file {nome_file} non è stato trovato.")
    except json.JSONDecodeError:
        logging.error(f"Errore: il file {nome_file} non è un file JSON valido.")
    except Exception as e:
        logging.error(f"Errore inaspettato: {e}")


def parse_command_reply(message, comandi):
    """
    Analizza un messaggio e, in base alle parole chiave nel dizionario `comandi`, esegue le azioni corrispondenti.
    
    Args:
    message (str): Il messaggio di input da analizzare.
    comandi (dict): Un dizionario che mappa le parole chiave a comandi.
    
    Returns:
    list: Una lista di comandi eseguiti (se trovati nel messaggio).
    """
    executed_commands = []

    # Convertiamo il messaggio in minuscolo per evitare problemi con maiuscole/minuscole
    message = message.lower()

    # Cicliamo su ogni comando nel dizionario
    for key, command in comandi.items():
        # Verifica se il comando (in minuscolo) è una sottostringa nel messaggio
        if command.lower() in message:
            # Aggiungiamo il comando eseguito alla lista
            executed_commands.append(key)

    return executed_commands


def esegui_comandi_process(array_command_da_eseguire):
    for command in array_command_da_eseguire:
        #metto qua il controllo del comando così lo fa' solo una volta per ogni process
        if command == "change_TP1":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_TP2":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()  
        if command == "change_TP3":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_TP4":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_TP5":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_SL":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "breakeven":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_full":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale terminA
            process.start()
        if command == "close_TP1":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP2":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP3":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP4":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP5":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "delete":
            process = multiprocessing.Process(target=esegui_comando, args=(command,))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()



    