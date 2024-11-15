# Signal.py
import re
import datetime
import json

#Funzione per caricare il file json
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

#Funzione per trasformare i messaggi di segnale in una Stringa predefinita da mandare all'EA
def transform_telegram_signal_optimize(message, account_id):
    # Compilazione dei pattern per le espressioni regolari
    pair_pattern = re.compile(r"([A-Z]{3}/[A-Z]{3})")
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
        return "Messaggio non valido"

    # Estrazione dei valori
    pair = pair_match.group(1)
    action = action_match.group(1)
    entry_price = entry_match.group(1)
    sl = sl_match.group(1)
    tp1, tp2, tp3 = tp_matches[0], tp_matches[1], tp_matches[2]

    # Chiamata unica per il timestamp
    current_time = datetime.datetime.now()
    received_time = current_time.strftime("%Y.%m.%d %H:%M:%S.%f")

        #Trasformo tutti gli ordini in ordini limit
    all_limit_orders = True

    if all_limit_orders == True:
        if action == "BUY":
            action = "BUY LIMIT"
        elif action == "SELL":
            action = "SELL LIMIT"


    # Creazione del risultato
    result = f"/open {pair},{action},{entry_price},{sl},{tp1},{tp2},{tp3}| for account {account_id} (Received: {received_time})"

    return result


# Funzione per cercare ,tramite un dizionario in json, delle parole chiave all'interno di messaggi che non siano segnali e restituisce una stringa sempre presente nel dizioario
def find_keywords_in_message_from_json(message, file_path):
    # Carica il file JSON solo una volta
    json_data = load_json(file_path)

    # Convertiamo il messaggio in minuscolo per la ricerca insensibile al caso
    message_lower = message.lower()

    # Creiamo un dizionario per le parole chiave con la risposta corrispondente
    keyword_to_response = {keyword.lower(): response for keyword, response in json_data["responses"].items()}

    # Controlla prima le parole chiave speciali
    special_keywords = ['change tp1', 'change tp2', 'change tp3', 'change sl']
    for special_keyword in special_keywords:
        if special_keyword in message_lower:
            numbers = re.findall(r'\d+', message)  # Trova tutti i numeri nel messaggio
            if numbers:
                return json_data["responses"].get(special_keyword, "No response found") + ' ' + ' '.join(numbers)

    # Eseguiamo la ricerca delle parole chiave nel messaggio
    for keyword, response in keyword_to_response.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower):  # Cerca la parola chiave come parola intera
            return response  # Restituisce la risposta corrispondente alla parola chiave trovata

    # Se nessuna parola chiave è trovata
    return "No relevant keywords found."