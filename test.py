import logging
import MetaTrader5 as mt5

mt5.initialize()


def esegui_comando_change_TP_pending_order(order_id, nuovo_tp):
    if not mt5.initialize():
        logging.error(f"MetaTrader5 non inizializzato, errore: {mt5.last_error()}")
        raise SystemExit("Errore nella connessione a MetaTrader 5")

    if order_id is None or nuovo_tp is None:
        logging.error("Errore: order_id o nuovo_tp non validi.")
        return False
    
    # Ottieni l'ordine
    ordine = mt5.orders_get(ticket=int(order_id))
    #logging.info(f"Ordini trovati: {ordine}")
    if ordine is None:
        logging.error(f"Errore: impossibile trovare l'ordine con ticket {order_id}")
        return False

    current_ordine = ordine[0]
    #rimuoviamo prima l'ordine e poi lo riaggiungiamo con il nuovo tp
    request = {
        'action': mt5.TRADE_ACTION_REMOVE,
        'order': current_ordine.ticket
    }

    mt5.order_send(request)

    # Prepara la richiesta per modificare il TP
    logging.info(f"current_ordine: {current_ordine}")
    logging.info(f"order_id da modificare: {order_id}, nuovo_tp: {nuovo_tp}")
    request = {
        "action": current_ordine.action,
        "symbol": current_ordine.symbol,
        "volume": current_ordine.volume,  # float
        "type": current_ordine.order_type,
        "price": current_ordine.stop_price,
        "sl": current_ordine.stop_loss,  # float
        "tp": nuovo_tp,  # float
        "deviation": 0,
        "magic": current_ordine.magic,  # Usa il magic number per identificare l'ordine
        "comment": "Trade inviato da Telegram",
        "type_time": mt5.ORDER_TIME_GTC,  # Tipo di scadenza: specificata
        "type_filling": mt5.ORDER_FILLING_IOC,  # Tipo di riempimentcleao
    }
 
    # Invia la richiesta per modificare il TP
    result = mt5.order_send(request)
    logging.info(f"result: {result}")

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Errore durante la modifica del TP: {result.retcode}")
        return False

    logging.info(f"TP dell'ordine {order_id} modificato correttamente a {nuovo_tp}.")
    return True

esegui_comando_change_TP_pending_order(51855490, 1.5)