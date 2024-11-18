import logging
import MetaTrader5 as mt5


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
    if not mt5.initialize():
        logging.error(f"MetaTrader5 non inizializzato, errore: {mt5.last_error()}")
        raise SystemExit("Errore nella connessione a MetaTrader 5")

    if order_id is None or nuovo_tp is None:
        logging.error("Errore: order_id o nuovo_tp non validi.")
        return False
    ordini = mt5.orders_get()
    
    # Ottieni l'ordine
    ordine = mt5.orders_get(ticket=int(order_id))
    #logging.info(f"Ordini trovati: {ordine}")
    if ordine is None:
        ordine = mt5.positions_get(ticket=order_id)
        logging.info(f"Ordini pendant trovati: {ordine}")
        if ordine is None:
            logging.error(f"Errore: impossibile trovare l'ordine con ticket {order_id}")
            return False
    current_ordine = ordine[0]
    # Prepara la richiesta per modificare il TP
    logging.info(f"current_ordine: {current_ordine}")
    logging.info(f"order_id da modificare: {order_id}, nuovo_tp: {nuovo_tp}")
    request = {
        "action": mt5.TRADE_ACTION_SLTP,  # Azione per modificare SL/TP
        "position": order_id,
        "sl": current_ordine.sl,  # Mantieni lo stesso Stop Loss
        "tp": nuovo_tp,   # Imposta il nuovo Take Profit
        
    }

    # Invia la richiesta per modificare il TP
    result = mt5.order_send(request)

    logging.info(f"result: {result}")

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Errore durante la modifica del TP: {result.retcode}")
        return False

    logging.info(f"TP dell'ordine {order_id} modificato correttamente a {nuovo_tp}.")
    return True


# modify SL/TP

stop_loss = 1.05  # set to 0.0 if you don't want SL
take_profit = 1.15  # set to 0.0 if you don't want TP

positions = mt5.orders_get()
print('open positions', positions)

# Working with 1st position in the list and closing it
pos1 = positions[0]

request = {
    'action': mt5.TRADE_ACTION_SLTP,
    'position': pos1.ticket,
    'sl': stop_loss,
    'tp': take_profit
}

res = mt5.order_send(request)
logging.info(f"res: {res}")
res