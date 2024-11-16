# pyTelegram

**pyTelegram** è un progetto in Python che integra Telegram con MetaTrader 5 (MT5). Riceve segnali da un canale Telegram chiamato **forexpert** e esegue automaticamente le azioni su MT5, come l'apertura di posizioni e la gestione dei trade.

## Tecnologie

- **Python**: Linguaggio di programmazione principale per l'automazione e l'integrazione.
- **Telegram API**: Per ricevere e inviare messaggi dal canale forexpert.
- **MetaTrader 5 (MT5)**: Per eseguire le azioni di trading come apertura posizioni e gestione ordini.

## Funzionalità

- **Ricezione segnali**: Rileva automaticamente i messaggi inviati nel canale Telegram forexpert.
- **Esecuzione automatica su MT5**: Il sistema esegue le azioni di trading come apertura di posizioni e gestione dello stop loss/take profit in base ai segnali ricevuti.
- **Gestione risk/reward**: La strategia include un'analisi del rischio e del reward per ogni trade eseguito.

## Installazione

1. **Clona il repository**:

   ```bash
   git clone https://github.com/tuo-username/pyTelegram.git
   ```

2. **Installa le dipendenze**: Assicurati di avere pip aggiornato e installa le dipendenze necessarie.

   ```bash
   pip install -r requirements.txt
   ```

3. **Configura le credenziali di Telegram**: Crea un bot su Telegram e prendi il tuo `API_TOKEN` e `chat_id` dal canale **forexpert**. Inserisci queste informazioni nel file di configurazione.

4. **Configura MetaTrader 5**: Assicurati di avere MetaTrader 5 installato e configurato per l'accesso tramite API. Inserisci le credenziali di accesso nel file di configurazione.

## Uso

Avvia il programma:

```bash
pythonT main.py
```

Il programma inizierà a ricevere i segnali dal canale Telegram **forexpert** e ad eseguire le azioni su MT5 automaticamente.

## Contribuire

Se vuoi contribuire a pyTelegram, sentiti libero di fare un fork del repository e inviare una pull request con le tue modifiche.

1. Fai un fork del progetto.
2. Crea un branch per la tua feature (`git checkout -b feature-nome`).
3. Commetti le tue modifiche (`git commit -am 'Aggiungi una feature'`).
4. Push su GitHub (`git push origin feature-nome`).
5. Invia una pull request.

## Licenza

Distribuito sotto la licenza **MIT**. Vedi il file [LICENSE](LICENSE) per ulteriori dettagli.
