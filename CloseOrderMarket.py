import MetaTrader5 as mt5

def close_market_order(order_id):
    # Initialize the connection to MetaTrader 5
    if not mt5.initialize():
        print("Initialization failed")
        return
    
    # Get the position by order_id
    positions = mt5.orders_get(ticket=order_id)
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
    
    # Shutdown the connection
    mt5.shutdown()

# Example usage
close_market_order(51761944)  # Replace with your actual order_id
