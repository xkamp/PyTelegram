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
import time
import sys

def initialize_mt5():
    if not mt5.initialize():
        logging.error(f"MetaTrader5 non inizializzato, errore: {mt5.last_error()}")
        raise SystemExit("Errore nella connessione a MetaTrader 5")
    logging.info("MetaTrader 5 inizializzato con successo.")


def connessione_db(nome_db):
    return sqlite3.connect(f"{nome_db}.db")


def close_order_market(order_id):
    # Initialize the connection to MetaTrader 5
    if not mt5.initialize():
        print("Initialization failed")
        return
    
    # Get the position by order_id
    positions = mt5.positions_get(ticket=order_id)
    print('open positions', positions)

    # Working with 1st position in the list and closing it
    pos1 = positions[0]

    def reverse_type(type):
        # to close a buy positions, you must perform a sell position and vice versa
        if type == mt5.ORDER_TYPE_BUY:
            return mt5.ORDER_TYPE_SELL
        elif type == mt5.ORDER_TYPE_SELL:
            return mt5.ORDER_TYPE_BUY


    def get_close_price(symbol, type):
        if type == mt5.ORDER_TYPE_BUY:
            return mt5.symbol_info(symbol).bid
        elif type == mt5.ORDER_TYPE_SELL:
            return mt5.symbol_info(symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos1.ticket,
        "symbol": pos1.symbol,
        "volume": pos1.volume,
        "type": reverse_type(pos1.type),
        "price":get_close_price(pos1.symbol, pos1.type),
        "deviation": 20,
        "magic": 0,
        "comment": "python close order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,  # some brokers accept mt5.ORDER_FILLING_FOK only
    }

    res = mt5.order_send(request)
    logging.info(f" {res} --> closed successfully.")

def close_order_pending(order_id):
    if not mt5.initialize():
        logging.error("initialize() failed, error code =", mt5.last_error())
        return

    # Recupera tutti gli ordini attivi
    orders = mt5.orders_get()
    if orders is None:
        logging.error("No orders found, error code =", mt5.last_error())
        return

    # Cerca l'ordine con l'ID specificato
    order = None
    for o in orders:
        if o.ticket == order_id:
            order = o
            break

    if order is None:
        print(f"No order found with ID {order_id}")
        return

    # Chiusura dell'ordine
    close_request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": order.ticket,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "type_time": mt5.ORDER_TIME_GTC
    }

    result = mt5.order_send(close_request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Failed to close order: {result.retcode}, {result.comment}")
    else:
        logging.info(f"Order {order_id} closed successfully.")


def esegui_comando_close_order(order_ticket, message_id, dict_messageid_orderid):
    if order_ticket is None:
        return False
    positions = mt5.orders_get(ticket=order_ticket)
    if positions is None:
        close_order_market(order_ticket)
    else:
        close_order_pending(order_ticket)

    cancella_coppia_dict_messageid_orderid(dict_messageid_orderid, message_id, order_ticket)

def esegui_comando_change_TP(order_id, nuovo_tp):
    """
    Modifica il Take Profit (TP) di un ordine esistente su MetaTrader 5.

    Args:
        order_id (int): ID dell'ordine da modificare.
        original_message_id (int): ID del messaggio associato (per il dizionario).
        conn (oggetto): Connessione al database o altra risorsa (non usata qui).
        dict_messageid_orderid (dict): Dizionario che associa message_id a order_id.
        nuovo_tp (float): Nuovo valore di Take Profit da impostare.

    Returns:
        bool: True se l'operazione è riuscita, False altrimenti.
    """
    if order_id is None or nuovo_tp is None:
        logging.error("Errore: order_id o nuovo_tp non validi.")
        return False

    # Ottieni l'ordine
    ordine = mt5.orders_get(ticket=order_id)
    if ordine is None:
        logging.error(f"Errore: impossibile trovare l'ordine con ticket {order_id}")
        return False
    current_ordine = ordine[0]
    # Prepara la richiesta per modificare il TP
    request = {
        "action": mt5.TRADE_ACTION_SLTP,  # Azione per modificare SL/TP
        "symbol": current_ordine.symbol,
        "sl": current_ordine.sl,  # Mantieni lo stesso Stop Loss
        "tp": nuovo_tp,   # Imposta il nuovo Take Profit
        "magic": current_ordine.magic,
        "ticket": order_id,
    }

    # Invia la richiesta per modificare il TP
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Errore durante la modifica del TP: {result.retcode}")
        return False

    logging.info(f"TP dell'ordine {order_id} modificato correttamente a {nuovo_tp}.")
    return True
    

def esegui_comando_change_SL(order_id, nuovo_sl):
    """
    Modifica lo Stop Loss (SL) di un ordine esistente su MetaTrader 5.

    Args:
        order_id (int): ID dell'ordine da modificare.
        original_message_id (int): ID del messaggio associato (per il dizionario).
        conn (oggetto): Connessione al database o altra risorsa (non usata qui).
        dict_messageid_orderid (dict): Dizionario che associa message_id a order_id.
        nuovo_sl (float): Nuovo valore di Stop Loss da impostare.

    Returns:
        bool: True se l'operazione è riuscita, False altrimenti.
    """
    if order_id is None or nuovo_sl is None:
        logging.error("Errore: order_id o nuovo_sl non validi.")
        return False

    # Ottieni l'ordine
    ordine = mt5.order_get(ticket=order_id)
    if ordine is None:
        logging.error(f"Errore: impossibile trovare l'ordine con ticket {order_id}")
        return False

    # Prepara la richiesta per modificare lo SL
    request = {
        "action": mt5.TRADE_ACTION_SLTP,  # Azione per modificare SL/TP
        "symbol": ordine.symbol,
        "sl": nuovo_sl,   # Imposta il nuovo Stop Loss
        "tp": ordine.tp,  # Mantieni lo stesso Take Profit
        "magic": ordine.magic,
        "ticket": order_id,
    }

    # Invia la richiesta per modificare lo SL
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Errore durante la modifica dello SL: {result.retcode}")
        return False

    logging.info(f"SL dell'ordine {order_id} modificato correttamente a {nuovo_sl}.")
    return True


def send_order(order_type, symbol, volume, sl, tp, entry_price, magic, num_minutes):
    # Inizializza la connessione con MetaTrader 5
    if not mt5.initialize():
        logging.error(f"Impossibile connettersi a MetaTrader 5. Errore: {mt5.last_error()}")
        return None

    # Verifica la disponibilità del simbolo
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logging.error(f"Simbolo {symbol} non trovato.")
        return None
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            logging.error(f"Impossibile attivare il simbolo {symbol}.")
            return None

    # Recupera il prezzo di mercato per l'ordine
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logging.error(f"Errore nel recupero del prezzo per {symbol}.")
        return None

    market_price = tick.ask if order_type == "BUY" else tick.bid

    # Configura il tipo di ordine in base al prezzo di ingresso
    if order_type == "BUY":
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if float(entry_price) <= market_price else mt5.ORDER_TYPE_BUY_STOP
    elif order_type == "SELL":
        order_type = mt5.ORDER_TYPE_SELL_LIMIT if float(entry_price) >= market_price else mt5.ORDER_TYPE_SELL_STOP
    else:
        logging.error(f"Tipo di ordine {order_type} non valido.")
        return None

    
    # Configurazione dei parametri dell'ordine
    action = mt5.TRADE_ACTION_PENDING
    # Aggiungi i minuti alla data e ora attuali
    scadenza = datetime.now() + timedelta(minutes=num_minutes)
    scadenza_senza_secondi = scadenza.replace(second=0, microsecond=0)
    
    # Restituisci il timestamp Unix
    expiration_timestamp = int(scadenza_senza_secondi.timestamp())
    #logging.info(f"Expiration timestamp: {expiration_timestamp}")
    data_ora = datetime.fromtimestamp(expiration_timestamp)
    #logging.info(f"Data e ora di scadenza: {data_ora}")


    # Crea la richiesta per l'ordine
    request = {
        "action": action,
        "symbol": symbol,
        "volume": volume,  # Utilizza il valore di volume
        "type": order_type,
        "price": float(entry_price),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 0,  # Deviation a zero, può essere personalizzato
        "magic": magic,  # Usa il magic number per identificare l'ordine
        "comment": "Trade inviato da Telegram",
        "type_time": mt5.ORDER_TIME_DAY,  # Tipo di scadenza: specificata
        "type_filling": mt5.ORDER_FILLING_IOC,  # Tipo di riempimentcleao
        #"expiration": expiration_timestamp,  # Data di scadenza dell'ordine
    }
    
    # Log dell'ordine creato
    #logging.info(f"Ordine creato: {request}")

    # Invia l'ordine
    result = mt5.order_send(request)
    #logging.error(f"Errore nell'invio dell'ordine: {result}")

    if result == None:
        logging.error(f"Errore nell'invio dell'ordine: {mt5.last_error()}")
        return None
    else:
        #logging.info(f"Ordine inviato con successo. Ticket dell'ordine: {result.order}")
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

    #logging.info(f"il dizionario è: {dict_messageid_orderid}")

def cancella_coppia_dict_messageid_orderid(dict_messageid_orderid, message_id, order_id):
    # Cancella la coppia dal dizionario
    if message_id in dict_messageid_orderid and dict_messageid_orderid[message_id] == order_id:
        del dict_messageid_orderid[message_id]

    # Se la coppia non è più presente nel dizionario, avvia un thread per cancellarla dal DB
    if message_id not in dict_messageid_orderid or dict_messageid_orderid[message_id] != order_id:
        threading.Thread(target=asyncio.run, args=(cancella_MessageIdOrderId_db(message_id, order_id),)).start()



async def cancella_MessageIdOrderId_db(message_id, order_id):
    """
    Cancella una coppia MessageId e OrderId dalla tabella nel database.
    
    Args:
        conn (sqlite3.Connection): Connessione al database SQLite.
        message_id (str): MessageId da cancellare.
        order_id (str): OrderId da cancellare.
    """
    try:
        conn = connessione_db("database")
        c = conn.cursor()
        c.execute("DELETE FROM MessageIdOrderId WHERE MessageId = ? AND OrderId = ?", (message_id, order_id))
        conn.commit()
    except Exception as e:
        logging.error(f"Errore durante la funzione cancella_id_database con errore: {e}")


def chiudi_connessione_db(conn):
    conn.close()



def monitor_order(order_ticket, tp, sl, symbol, order_type, message_id, dict_messageid_orderid):
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
    logging.info(f"Monitoraggio dell'ordine {order_ticket} in corso...")
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
                logging.warning(f"Errore nel recupero dei tick per {symbol}.")
                continue
        

        # Controlla se il tick di mercato ha cambiato
        if tick != last_tick:
            last_tick = tick
            #logging.info(f"Tick di mercato per {symbol}: {tick}")
            # Controlla se il TP o SL sono stati raggiunti
            if order_type == "BUY":
                #logging.info(f"ordine = {order_ticket}, TP: {tp}, SL: {sl}, tick.ask: {tick.ask}, tick.bid: {tick.bid}")
                if float(tick.ask) >= float(tp):
                    logging.info(f"Take Profit hit for order {order_ticket}. Closing order.")
                    esegui_comando_close_order(order_ticket, message_id, dict_messageid_orderid)
                    break
                elif float(tick.ask) <= float(sl):
                    logging.info(f"Stop Loss hit for order {order_ticket}. Closing order.")
                    esegui_comando_close_order(order_ticket, message_id, dict_messageid_orderid)
                    break
            elif order_type == "SELL":
                if float(tick.bid) <= float(tp):
                    logging.info(f"Take Profit hit for order {order_ticket}. Closing order.")
                    esegui_comando_close_order(order_ticket, message_id, dict_messageid_orderid)
                    break
                elif float(tick.bid) >= float(sl):
                    logging.info(f"Stop Loss hit for order {order_ticket}. Closing order.")
                    esegui_comando_close_order(order_ticket, message_id, dict_messageid_orderid)
                    break



def monitor_order_process(array_success, tp, sl, symbol, order_type, message_id, dict_messageid_orderid):
    take_profit = None
    for order_id in array_success:
        orders = mt5.orders_get(ticket=order_id)
        for order in orders:
            take_profit = order.tp 
            #logging.info(f"Take Profit: {take_profit}")
        process = multiprocessing.Process(target=monitor_order, args=(order_id, take_profit, sl, symbol, order_type, message_id, dict_messageid_orderid))
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


def monitor_breakeven_order(order_id, max_attempts=100000, sleep_interval=1):
    """
    Imposta lo stop loss di un ordine sul prezzo di entrata appena il prezzo di mercato lo permette.
    Gestisce ordini di tipo Buy, Sell, Buy Limit, Buy Stop, Sell Limit, e Sell Stop.
    Riprova fino a max_attempts volte se il prezzo di mercato non consente di spostare lo SL.
    
    Args:
        order_id (int): L'ID dell'ordine da modificare.
        max_attempts (int): Numero massimo di tentativi di aggiornamento dello SL.
        sleep_interval (int): Tempo di attesa (in secondi) tra i tentativi.
        
    Returns:
        bool: True se l'operazione è stata completata con successo, False altrimenti.
    """
    # Recupera i dettagli dell'ordine
    order = mt5.positions_get(ticket=order_id)
    if not order:
        logging.info(f"Ordine con ID {order_id} non trovato.")
        return False

    order = order[0]  # Prende il primo elemento della lista (l'ordine specifico)
    entry_price = order.price_open  # Prezzo di apertura
    symbol = order.symbol  # Simbolo dell'ordine
    order_type = order.type  # Tipo dell'ordine

    # Recupera il prezzo di mercato corrente
    market_price = mt5.symbol_info_tick(symbol)
    if not market_price:
        logging.error(f"Impossibile recuperare il prezzo di mercato per il simbolo {symbol}.")
        return False

    # Funzione per verificare se il prezzo di mercato consente di spostare lo SL
    def can_move_sl(order_type, entry_price, market_price):
        if order_type == mt5.ORDER_TYPE_BUY:
            return market_price.bid >= entry_price
        elif order_type == mt5.ORDER_TYPE_SELL:
            return market_price.ask <= entry_price
        elif order_type == mt5.ORDER_TYPE_BUY_LIMIT:
            return market_price.bid >= entry_price
        elif order_type == mt5.ORDER_TYPE_SELL_LIMIT:
            return market_price.ask <= entry_price
        elif order_type == mt5.ORDER_TYPE_BUY_STOP:
            return market_price.bid >= entry_price
        elif order_type == mt5.ORDER_TYPE_SELL_STOP:
            return market_price.ask <= entry_price
        return False

    # Tenta di spostare lo SL finché non ci riesce o raggiunge il numero massimo di tentativi
    attempt = 0
    while attempt < max_attempts:
        # Verifica se il prezzo di mercato consente di spostare lo SL
        if can_move_sl(order_type, entry_price, market_price):
            # Imposta il nuovo SL al prezzo di entrata
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": order_id,
                "sl": entry_price,
                "tp": order.tp  # Mantieni il take profit invariato
            }

            # Esegui la modifica
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"SL spostato al prezzo di entrata per l'ordine {order_id}.")
                return True
            else:
                logging.error(f"Errore nello spostare lo SL per l'ordine {order_id}. Retcode: {result.retcode}")
                return False
        else:
            # Aumento il contatore dei tentativi
            attempt += 1
            logging.info(f"Tentativo {attempt} di {max_attempts}. Il prezzo di mercato non consente ancora di spostare lo SL.")
            time.sleep(sleep_interval)  # Attendere un po' prima di riprovare
            # Recupera nuovamente il prezzo di mercato
            market_price = mt5.symbol_info_tick(symbol)
            if not market_price:
                logging.error(f"Impossibile recuperare il prezzo di mercato per il simbolo {symbol}.")
                return False

    logging.error(f"Non è stato possibile spostare lo SL dopo {max_attempts} tentativi.")
    return False


def esegui_comando_breakeven(dict_messageid_orderid,message_id):
    for order_id in dict_messageid_orderid[message_id]:
        #avvia il processo per il monitoraggio del breakeven e appena può lo esegue
        process = multiprocessing.Process(target=monitor_breakeven_order, args=(order_id))
        process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
        process.start()



def extract_number(text):
    """
    Estrae il numero decimale da una stringa.

    Args:
        text (str): La stringa da cui estrarre il numero.

    Returns:
        float: Il numero estratto, se presente, altrimenti None.
    """
    match = re.search(r"\d+\.\d+", text)  # Cerca un numero decimale
    return float(match.group())

def search_order1_dict_messageid_orderid(dict_messageid_orderid, original_message_id):
    """
    Cerca un `original_message_id` in un dizionario e restituisce il primo valore trovato nell'array associato alla chiave corrispondente.

    Args:
        dict_messageid_orderid (dict): Dizionario in cui cercare. Le chiavi sono di tipo generico e i valori sono array.
        original_message_id (int/str): ID del messaggio da cercare nel dizionario.

    Returns:
        any: Il primo valore trovato nell'array associato alla chiave `original_message_id`.
        None: Se `original_message_id` non è presente o l'array associato è vuoto.
    """
    # Controlla se la chiave esiste nel dizionario
    if original_message_id in dict_messageid_orderid:
        # Accedi all'array associato alla chiave
        array = dict_messageid_orderid[original_message_id]
        # Restituisci il primo valore se l'array non è vuoto
        if array:
            return array[0]
    # Restituisci None se la chiave non esiste o l'array è vuoto
    return None

def search_order2_dict_messageid_orderid(dict_messageid_orderid, original_message_id):
    """
    Cerca un `original_message_id` in un dizionario e restituisce il primo valore trovato nell'array associato alla chiave corrispondente.

    Args:
        dict_messageid_orderid (dict): Dizionario in cui cercare. Le chiavi sono di tipo generico e i valori sono array.
        original_message_id (int/str): ID del messaggio da cercare nel dizionario.

    Returns:
        any: Il primo valore trovato nell'array associato alla chiave `original_message_id`.
        None: Se `original_message_id` non è presente o l'array associato è vuoto.
    """
    # Controlla se la chiave esiste nel dizionario
    if original_message_id in dict_messageid_orderid:
        # Accedi all'array associato alla chiave
        array = dict_messageid_orderid[original_message_id]
        # Restituisci il primo valore se l'array non è vuoto
        if array:
            return array[1]
    # Restituisci None se la chiave non esiste o l'array è vuoto
    return None

def search_order3_dict_messageid_orderid(dict_messageid_orderid, original_message_id):
    """
    Cerca un `original_message_id` in un dizionario e restituisce il primo valore trovato nell'array associato alla chiave corrispondente.

    Args:
        dict_messageid_orderid (dict): Dizionario in cui cercare. Le chiavi sono di tipo generico e i valori sono array.
        original_message_id (int/str): ID del messaggio da cercare nel dizionario.

    Returns:
        any: Il primo valore trovato nell'array associato alla chiave `original_message_id`.
        None: Se `original_message_id` non è presente o l'array associato è vuoto.
    """
    # Controlla se la chiave esiste nel dizionario
    if original_message_id in dict_messageid_orderid:
        # Accedi all'array associato alla chiave
        array = dict_messageid_orderid[original_message_id]
        # Restituisci il primo valore se l'array non è vuoto
        if array:
            return array[2]
    # Restituisci None se la chiave non esiste o l'array è vuoto
    return None

def search_order4_dict_messageid_orderid(dict_messageid_orderid, original_message_id):
    """
    Cerca un `original_message_id` in un dizionario e restituisce il primo valore trovato nell'array associato alla chiave corrispondente.

    Args:
        dict_messageid_orderid (dict): Dizionario in cui cercare. Le chiavi sono di tipo generico e i valori sono array.
        original_message_id (int/str): ID del messaggio da cercare nel dizionario.

    Returns:
        any: Il primo valore trovato nell'array associato alla chiave `original_message_id`.
        None: Se `original_message_id` non è presente o l'array associato è vuoto.
    """
    # Controlla se la chiave esiste nel dizionario
    if original_message_id in dict_messageid_orderid:
        # Accedi all'array associato alla chiave
        array = dict_messageid_orderid[original_message_id]
        # Restituisci il primo valore se l'array non è vuoto
        if array:
            return array[3]
    # Restituisci None se la chiave non esiste o l'array è vuoto
    return None

def search_order5_dict_messageid_orderid(dict_messageid_orderid, original_message_id):
    """
    Cerca un `original_message_id` in un dizionario e restituisce il primo valore trovato nell'array associato alla chiave corrispondente.

    Args:
        dict_messageid_orderid (dict): Dizionario in cui cercare. Le chiavi sono di tipo generico e i valori sono array.
        original_message_id (int/str): ID del messaggio da cercare nel dizionario.

    Returns:
        any: Il primo valore trovato nell'array associato alla chiave `original_message_id`.
        None: Se `original_message_id` non è presente o l'array associato è vuoto.
    """
    # Controlla se la chiave esiste nel dizionario
    if original_message_id in dict_messageid_orderid:
        # Accedi all'array associato alla chiave
        array = dict_messageid_orderid[original_message_id]
        # Restituisci il primo valore se l'array non è vuoto
        if array:
            return array[4]
    # Restituisci None se la chiave non esiste o l'array è vuoto
    return None


def esegui_comandi_process(array_command_da_eseguire, conn, dict_messageid_orderid,original_message_id,message_text):
    for command in array_command_da_eseguire:
        #metto qua il controllo del comando così lo fa' solo una volta per ogni process
        if command == "change_TP1":
            order_id = search_order1_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            new_tp = extract_number(message_text)
            process = multiprocessing.Process(target=esegui_comando_change_TP, args=(order_id, new_tp))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_TP2":
            order_id = search_order2_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            new_tp = extract_number(message_text)
            process = multiprocessing.Process(target=esegui_comando_change_TP, args=(order_id, new_tp))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()  
        if command == "change_TP3":
            order_id = search_order3_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            new_tp = extract_number(message_text)
            process = multiprocessing.Process(target=esegui_comando_change_TP, args=(order_id, new_tp))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_TP4":
            order_id = search_order4_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            new_tp = extract_number(message_text)
            process = multiprocessing.Process(target=esegui_comando_change_TP, args=(order_id, new_tp))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_TP5":
            order_id = search_order5_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            new_tp = extract_number(message_text)
            process = multiprocessing.Process(target=esegui_comando_change_TP, args=(order_id, new_tp))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "change_SL": #cambia lo stop a tutti gli ordini con message_id uguale
            new_sl = extract_number(message_text)
            #ciclo dentro l'array del dizionario con la chiave original_message_id
            for order_id in dict_messageid_orderid[original_message_id]:
                process = multiprocessing.Process(target=esegui_comando_change_SL, args=(order_id, new_sl))
                process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
                process.start()
            process = multiprocessing.Process(target=esegui_comando_change_SL, args=())
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "breakeven":
            process = multiprocessing.Process(target=esegui_comando_breakeven, args=(dict_messageid_orderid,original_message_id))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_full":
            for order_id in dict_messageid_orderid[original_message_id]:
                process = multiprocessing.Process(target=esegui_comando_close_order,args=(order_id, original_message_id, conn, dict_messageid_orderid))
                process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale terminA
                process.start()
        if command == "close_TP1":
            order_id = search_order1_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            process = multiprocessing.Process(target=esegui_comando_close_order,args=(order_id, original_message_id, conn, dict_messageid_orderid))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP2":
            order_id = search_order2_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            process = multiprocessing.Process(target=esegui_comando_close_order,args=(order_id, original_message_id, conn, dict_messageid_orderid))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP3":
            order_id = search_order3_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            process = multiprocessing.Process(target=esegui_comando_close_order,args=(order_id, original_message_id, conn, dict_messageid_orderid))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP4":
            order_id = search_order4_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            process = multiprocessing.Process(target=esegui_comando_close_order,args=(order_id, original_message_id, conn, dict_messageid_orderid))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()
        if command == "close_TP5":
            order_id = search_order5_dict_messageid_orderid(dict_messageid_orderid, original_message_id)
            process = multiprocessing.Process(target=esegui_comando_close_order,args=(order_id, original_message_id, conn, dict_messageid_orderid))
            process.daemon = False  # Non é un processo demon, continuerà anche quando il programma principale termina
            process.start()




    