"""Modo local para aprender e experimentar sem conectar ao WhatsApp."""

from dotenv import load_dotenv

load_dotenv()

import bot
import database


def main():
    database.initialize_database()
    print("Controle financeiro local. Digite 'sair' para encerrar.")
    print("Exemplos: gasto R$32,50 almoço | salario R$3500 | relatorio | ajuda")
    while True:
        try:
            message = input("Você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break
        if message.casefold() in {"sair", "exit", "quit"}:
            print("Até mais!")
            break
        print("Bot>", bot.handle_message("teste-local", message))


if __name__ == "__main__":
    main()
