import logging
from funzioni import parse_command

# Abilita la registrazione degli errori
logging.basicConfig(level=logging.DEBUG)

def test_parse_command():

    command = parse_command("""
    📈BUY        GBP/USD

    Entry price     1.2659 / 1.2664

    TP1 :      1.2679
    TP2 :      1.2709
    TP3 :      1.2759

    SL        1.2589

    Please respect your lot size ⚠️⚠️Risk
    """)
    print(f"Passato: {command}\n")
    if command:
        order_type = command["order_type"]
        symbol = command["symbol"]
        entry_price = command["entry_price"]
        take_profits = command["take_profits"]
        stop_loss = command["stop_loss"]

        # Imposta il volume del trade (può essere calcolato o definito manualmente)
        volume = 0.01  # Ad esempio, volume fisso per ogni trade. Puoi personalizzarlo

        # Invia un ordine per ogni Take Profitclea
        for tp in take_profits:
             print(f"Invio ordine per TP={tp}")


# Chiamare la funzione di test
test_parse_command()


