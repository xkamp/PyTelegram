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

# Esempio di utilizzo:
comandi = {
    "change_TP1": "CHANGE TP1 TO",
    "change_TP2": "CHANGE TP2 TO",
    "change_TP3": "CHANGE TP3 TO",
    "change_TP4": "CHANGE TP4 TO",
    "change_TP5": "CHANGE TP5 TO",
    "change_SL" : "CHANGE SL TO",
    "breakeven": "SECURE THIS TRADE",
    "close full" : "MANUALLY CLOSE, CANCEL THIS TRADE, REMOVE IT",
    "close_TP1" : "MANUALLY CLOSE TP1",
    "close_TP2" : "MANUALLY CLOSE TP2",
    "close_TP3" : "MANUALLY CLOSE TP3",
    "close_TP4" : "MANUALLY CLOSE TP4",
    "close_TP5" : "MANUALLY CLOSE TP5",
    "delete" : "DELETE"
}

# Esempio di messaggio
message = "I want to secure this trade now"
result = parse_command_reply(message, comandi)
print(result)  # Uscita: ['breakeven']