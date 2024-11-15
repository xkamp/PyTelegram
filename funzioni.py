from telethon import TelegramClient, events
import MetaTrader5 as mt5
import logging
import re
import time
import multiprocessing
from datetime import datetime, timedelta



# Connessione a MetaTrader 5
def initialize_mt5():
    if not mt5.initialize():
        logging.error(f"MetaTrader5 non inizializzato, errore: {mt5.last_error()}")
        raise SystemExit("Errore nella connessione a MetaTrader 5")
    logging.info("MetaTrader 5 inizializzato con successo.")

def close_order(order_ticket):
    if order_ticket is not None:
        mt5.order_close(order_ticket)
        

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


# Funzione per monitorare e chiudere l'ordine su ogni tick di mercato
def monitor_order(order_ticket, tp, sl, symbol, order_type):
    #logging.info(f"Monitoraggio dell'ordine {order_ticket} in corso...")
    #logging.info(f"TP: {tp}, SL: {sl}, Symbol: {symbol}, Order Type: {order_type}")
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
                    close_order(order_ticket)
                    break
                elif tick.ask <= sl:
                    logging.info(f"Stop Loss hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket)
                    break
            elif order_type == "SELL":
                if tick.bid <= tp:
                    logging.info(f"Take Profit hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket)
                    break
                elif tick.bid >= sl:
                    logging.info(f"Stop Loss hit for order {order_ticket}. Closing order.")
                    close_order(order_ticket)
                    break


# Funzione per avviare un processo separato che monitori ogni tick di mercato
def monitor_order_process(order_ticket, tp, sl, symbol, order_type):
    process = multiprocessing.Process(target=monitor_order, args=(order_ticket, tp, sl, symbol, order_type))
    process.daemon = False  # Non è un processo demon, continuerà anche quando il programma principale termina
    process.start()

