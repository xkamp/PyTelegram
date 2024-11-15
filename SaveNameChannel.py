import json
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

# Configura le tue credenziali Telegram
API_ID = 21280755
API_HASH = 'f339f77b7c693302c8d318a91f86c1b0'  
SESSION_NAME = "my_session"    # Nome del file della sessione

async def save_channels_and_conversations(client, output_file="channels_and_conversations.json"):
    """
    Salva tutti i canali e le conversazioni aperte in un file JSON.
    :param client: Istanza del TelegramClient.
    :param output_file: Nome del file JSON di output.
    """
    # Recupera tutte le chat disponibili
    dialogs = await client.get_dialogs()

    # Lista per salvare i dettagli
    data = []

    for dialog in dialogs:
        entity = dialog.entity

        # Distinguere tra canali, chat e utenti
        if isinstance(entity, Channel):  # Canali o supergruppi
            entity_type = "Channel"
        elif isinstance(entity, Chat):  # Gruppi normali
            entity_type = "Chat"
        elif isinstance(entity, User):  # Conversazioni con utenti
            entity_type = "User"
        else:
            entity_type = "Unknown"

        # Salva le informazioni principali
        data.append({
            "id": entity.id,
            "name": getattr(entity, "title", getattr(entity, "username", "N/A")),
            "type": entity_type
        })

    # Scrive i dati su un file JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Canali e conversazioni salvati in '{output_file}'")

# Funzione per avviare il client Telegram e chiamare la funzione
async def main():
    # Inizializza il client Telegram
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        # Chiama la funzione per salvare canali e conversazioni
        await save_channels_and_conversations(client, output_file="channels_and_conversations.json")

# Esegui la funzione principale
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
