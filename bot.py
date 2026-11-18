"""Interpretação das mensagens e respostas do bot."""

import random
import re
from datetime import datetime

import database


GREETINGS = [
    "Oi! Vamos organizar suas finanças?",
    "Olá! Pronto para registrar seus gastos e recebimentos?",
    "E aí! Seu controle financeiro está pronto.",
]

HELP = (
    "Posso ajudar com seu controle financeiro.\n\n"
    "• `gasto 32,50 almoço` — registra uma despesa\n"
    "• `salario 3500` — registra um recebimento\n"
    "• `relatorio` — mostra o mês atual\n"
    "• `relatorio 2026-11` — escolhe o mês\n"
    "• `ajuda` — mostra esta lista\n\n"
    "Exemplo: gasto 18,90 café"
)

AMOUNT_PATTERN = r"(?P<amount>\d+(?:[.,]\d{1,2})?)"
EXPENSE_PATTERN = re.compile(
    rf"^gasto\s+{AMOUNT_PATTERN}(?=\s|$)(?:\s+(?P<description>.+))?$", re.IGNORECASE
)
INCOME_PATTERN = re.compile(
    rf"^(?:salario|salário)\s+{AMOUNT_PATTERN}(?=\s|$)(?:\s+(?P<description>.+))?$",
    re.IGNORECASE,
)


def parse_amount(text):
    normalized = text.replace(",", ".")
    whole, dot, fraction = normalized.partition(".")
    fraction = (fraction + "00")[:2] if dot else "00"
    cents = int(whole) * 100 + int(fraction)
    if cents <= 0:
        raise ValueError("O valor precisa ser maior que zero.")
    return cents


def money(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    value = f"{cents // 100:,}".replace(",", ".")
    fraction = f"{cents % 100:02d}"
    return f"R$ {sign}{value},{fraction}"


def report_text(sender, month_text=None):
    if month_text:
        try:
            year, month = (int(part) for part in month_text.split("-"))
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            return "Use o formato `relatorio AAAA-MM`, por exemplo `relatorio 2026-11`."
    else:
        today = database.now_local()
        year, month = today.year, today.month

    report = database.monthly_report(sender, year, month)
    lines = [
        f"📊 Relatório de {month:02d}/{year}",
        f"Entradas: {money(report['income'])}",
        f"Gastos: {money(report['expense'])}",
        f"Saldo: {money(report['balance'])}",
        "",
        "Por semana (ISO):",
    ]
    if report["weekly"]:
        for week, totals in sorted(report["weekly"].items()):
            lines.append(
                f"{week}: gastos {money(totals['expense'])} · "
                f"entradas {money(totals['income'])}"
            )
    else:
        lines.append("Sem lançamentos neste mês ainda.")

    lines.extend(["", "Por dia:"])
    if report["daily"]:
        for day, totals in sorted(report["daily"].items()):
            lines.append(
                f"{day}: gastos {money(totals['expense'])} · "
                f"entradas {money(totals['income'])}"
            )

    lines.extend(["", "Lançamentos recentes:"])
    for item in report["transactions"]:
        kind = "Gasto" if item["kind"] == "expense" else "Entrada"
        when = datetime.fromisoformat(item["occurred_at"]).strftime("%d/%m %H:%M")
        lines.append(
            f"{when} · {kind} · {money(item['amount_cents'])} · {item['description']}"
        )
    return "\n".join(lines)


def handle_message(sender, message, message_id=None):
    text = (message or "").strip()
    lowered = text.casefold()

    if lowered in {"oi", "olá", "ola", "menu", "início", "inicio"}:
        return random.choice(GREETINGS) + "\n\n" + HELP
    if lowered in {"ajuda", "help", "comandos"}:
        return HELP
    if lowered in {"relatorio", "relatório"}:
        return report_text(sender)
    report_match = re.fullmatch(r"(?:relatorio|relatório)\s+(\d{4}-\d{2})", lowered)
    if report_match:
        return report_text(sender, report_match.group(1))

    for pattern, kind, label, default_description in (
        (EXPENSE_PATTERN, "expense", "Gasto registrado", "Sem descrição"),
        (INCOME_PATTERN, "income", "Recebimento registrado", "Salário"),
    ):
        match = pattern.fullmatch(text)
        if match:
            try:
                cents = parse_amount(match.group("amount"))
            except ValueError as error:
                return str(error)
            description = (match.group("description") or default_description).strip()
            inserted, timestamp = database.add_transaction(
                sender, kind, cents, description, message_id
            )
            if not inserted:
                return "Este lançamento já foi registrado."
            when = datetime.fromisoformat(timestamp).strftime("%d/%m/%Y às %H:%M")
            return f"✅ {label}: {money(cents)} — {description}\nRegistrado em {when}."

    return "Não entendi essa mensagem.\n\n" + HELP
