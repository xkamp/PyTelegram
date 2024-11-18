import MetaTrader5 as mt5

def close_order(order_id):
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return

    # Recupera tutti gli ordini attivi
    orders = mt5.orders_get()
    if orders is None:
        print("No orders found, error code =", mt5.last_error())
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
        print(f"Failed to close order: {result.retcode}, {result.comment}")
    else:
        print(f"Order {order_id} closed successfully.")

# Test della funzione con un order_id specifico
close_order(51751415)
