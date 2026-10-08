from datetime import date
from decimal import Decimal

import pytest

import bank_app


@pytest.fixture
def accounts():
    return {}


@pytest.fixture
def savings_account(accounts):
    return bank_app.create_account(
        accounts,
        "SAV001",
        "Alice",
        "1234",
        "Savings",
        Decimal("5000"),
        date(2025, 1, 15),
    )


@pytest.fixture
def current_account(accounts):
    return bank_app.create_account(
        accounts,
        "CUR001",
        "Bob",
        "5678",
        "Current",
        Decimal("2000"),
        date(2025, 1, 15),
    )


def test_create_account_valid(accounts):
    account = bank_app.create_account(
        accounts,
        "SAV001",
        "Alice",
        "1234",
        "Savings",
        "2500",
        date(2025, 1, 10),
    )

    assert account["account_id"] == "SAV001"
    assert account["customer_name"] == "Alice"
    assert account["pin"] == "1234"
    assert account["account_type"] == "Savings"
    assert account["balance"] == Decimal("2500")
    assert account["daily_withdrawal_date"] is None
    assert account["daily_withdrawal_total"] == Decimal("0")
    assert account["daily_transfer_date"] is None
    assert account["daily_transfer_total"] == Decimal("0")
    assert account["transaction_history"][0]["type"] == "OPENING"
    assert account["transaction_history"][0]["balance_after"] == Decimal("2500")
    assert accounts["SAV001"] is account


@pytest.mark.parametrize(
    ("account_id", "customer_name", "pin", "account_type", "opening_balance", "exception"),
    [
        ("", "Alice", "1234", "Savings", "0", bank_app.ValidationError),
        ("SAV001", "", "1234", "Savings", "0", bank_app.ValidationError),
        ("SAV001", "Alice", "123", "Savings", "0", bank_app.ValidationError),
        ("SAV001", "Alice", "1234", "Credit", "0", bank_app.ValidationError),
        ("SAV001", "Alice", "1234", "Savings", "-1", bank_app.InvalidAmountError),
        ("SAV001", "Alice", "1234", "Savings", "100001", bank_app.TransactionLimitError),
    ],
)
def test_create_account_rejects_invalid_values(
    accounts,
    account_id,
    customer_name,
    pin,
    account_type,
    opening_balance,
    exception,
):
    with pytest.raises(exception):
        bank_app.create_account(
            accounts,
            account_id,
            customer_name,
            pin,
            account_type,
            opening_balance,
        )


def test_create_account_rejects_duplicate_account(accounts, savings_account):
    with pytest.raises(bank_app.DuplicateAccountError):
        bank_app.create_account(
            accounts,
            "SAV001",
            "Alice Clone",
            "4321",
            "Savings",
            Decimal("2000"),
        )


def test_authenticate_account_success_and_wrong_pin(accounts, savings_account):
    assert bank_app.authenticate_account(accounts, "SAV001", "1234") is savings_account

    with pytest.raises(bank_app.InvalidPinError) as exc_info:
        bank_app.authenticate_account(accounts, "SAV001", "9999")

    assert exc_info.value.failed_attempts == 1
    assert exc_info.value.attempts_remaining == 2


def test_authenticate_account_lockout_and_invalid_attempt_count(accounts, savings_account):
    with pytest.raises(bank_app.LoginLockedError):
        bank_app.authenticate_account(accounts, "SAV001", "9999", failed_attempts=2)

    with pytest.raises(bank_app.ValidationError):
        bank_app.authenticate_account(accounts, "SAV001", "1234", failed_attempts=True)


def test_authenticate_account_missing_account_raises_not_found(accounts):
    with pytest.raises(bank_app.AccountNotFoundError):
        bank_app.authenticate_account(accounts, "NOPE", "1234")


def test_check_balance_returns_current_balance(savings_account):
    assert bank_app.check_balance(savings_account) == Decimal("5000")


def test_deposit_updates_balance_and_history(savings_account):
    before_balance = savings_account["balance"]
    before_history_count = len(savings_account["transaction_history"])

    new_balance = bank_app.deposit(savings_account, Decimal("1500"), date(2025, 1, 20))

    assert new_balance == Decimal("6500")
    assert savings_account["balance"] == Decimal("6500")
    assert before_balance != savings_account["balance"]
    assert len(savings_account["transaction_history"]) == before_history_count + 1
    assert savings_account["transaction_history"][-1]["type"] == "DEPOSIT"
    assert savings_account["transaction_history"][-1]["amount"] == Decimal("1500")
    assert savings_account["transaction_history"][-1]["balance_after"] == Decimal("6500")


@pytest.mark.parametrize(
    ("amount", "exception"),
    [
        (Decimal("0"), bank_app.InvalidAmountError),
        (Decimal("-1"), bank_app.InvalidAmountError),
        (Decimal("50001"), bank_app.TransactionLimitError),
    ],
)
def test_deposit_rejects_invalid_amounts(savings_account, amount, exception):
    before_balance = savings_account["balance"]
    before_history = list(savings_account["transaction_history"])

    with pytest.raises(exception):
        bank_app.deposit(savings_account, amount, date(2025, 1, 20))

    assert savings_account["balance"] == before_balance
    assert savings_account["transaction_history"] == before_history


def test_withdraw_valid_and_daily_total_updates(savings_account):
    new_balance = bank_app.withdraw(savings_account, Decimal("1000"), date(2025, 2, 1))

    assert new_balance == Decimal("4000")
    assert savings_account["balance"] == Decimal("4000")
    assert savings_account["daily_withdrawal_date"] == date(2025, 2, 1)
    assert savings_account["daily_withdrawal_total"] == Decimal("1000")
    assert savings_account["transaction_history"][-1]["type"] == "WITHDRAWAL"

    second_balance = bank_app.withdraw(savings_account, Decimal("2000"), date(2025, 2, 2))
    assert second_balance == Decimal("2000")
    assert savings_account["daily_withdrawal_date"] == date(2025, 2, 2)
    assert savings_account["daily_withdrawal_total"] == Decimal("2000")


@pytest.mark.parametrize(
    ("amount", "date_value", "exception"),
    [
        (Decimal("150"), date(2025, 2, 3), bank_app.InvalidAmountError),
        (Decimal("4100"), date(2025, 2, 3), bank_app.InsufficientFundsError),
    ],
)
def test_withdraw_rejects_invalid_values_and_leaves_state_unchanged(
    savings_account, amount, date_value, exception
):
    before_balance = savings_account["balance"]
    before_total = savings_account["daily_withdrawal_total"]
    before_history = list(savings_account["transaction_history"])

    with pytest.raises(exception):
        bank_app.withdraw(savings_account, amount, date_value)

    assert savings_account["balance"] == before_balance
    assert savings_account["daily_withdrawal_total"] == before_total
    assert savings_account["transaction_history"] == before_history


def test_withdraw_rejects_daily_limit_and_keeps_state_unchanged():
    account = bank_app.create_account(
        {},
        "SAV200",
        "Dina",
        "8888",
        "Savings",
        Decimal("100000"),
        date(2025, 2, 1),
    )
    account["daily_withdrawal_date"] = date(2025, 2, 1)
    account["daily_withdrawal_total"] = Decimal("15000")

    with pytest.raises(bank_app.DailyLimitError):
        bank_app.withdraw(account, Decimal("20000"), date(2025, 2, 1))

    assert account["balance"] == Decimal("100000")
    assert account["daily_withdrawal_total"] == Decimal("15000")


def test_transfer_updates_both_accounts_and_daily_total(accounts, savings_account, current_account):
    source_balance, destination_balance = bank_app.transfer(
        accounts,
        "SAV001",
        "CUR001",
        Decimal("1000"),
        date(2025, 3, 1),
    )

    assert source_balance == Decimal("4000")
    assert destination_balance == Decimal("3000")
    assert savings_account["balance"] == Decimal("4000")
    assert current_account["balance"] == Decimal("3000")
    assert savings_account["daily_transfer_total"] == Decimal("1000")
    assert savings_account["transaction_history"][-1]["type"] == "TRANSFER_OUT"
    assert current_account["transaction_history"][-1]["type"] == "TRANSFER_IN"


def test_transfer_rejects_same_account_and_invalid_amounts(accounts, savings_account, current_account):
    with pytest.raises(bank_app.SameAccountTransferError):
        bank_app.transfer(accounts, "SAV001", "SAV001", Decimal("100"), date(2025, 3, 2))

    before_balance = savings_account["balance"]
    before_history = list(savings_account["transaction_history"])
    with pytest.raises(bank_app.InvalidAmountError):
        bank_app.transfer(accounts, "SAV001", "CUR001", Decimal("0"), date(2025, 3, 2))

    assert savings_account["balance"] == before_balance
    assert savings_account["transaction_history"] == before_history


def test_transfer_rejects_daily_limit_and_insufficient_funds(accounts):
    source = bank_app.create_account(
        accounts,
        "SAV100",
        "Dana",
        "1111",
        "Savings",
        Decimal("25000"),
        date(2025, 4, 1),
    )
    destination = bank_app.create_account(
        accounts,
        "CUR100",
        "Eve",
        "2222",
        "Current",
        Decimal("1000"),
        date(2025, 4, 1),
    )
    source["daily_transfer_date"] = date(2025, 4, 1)
    source["daily_transfer_total"] = Decimal("20000")

    with pytest.raises(bank_app.DailyLimitError):
        bank_app.transfer(accounts, "SAV100", "CUR100", Decimal("10000"), date(2025, 4, 1))

    source["balance"] = Decimal("11000")
    source["daily_transfer_date"] = date(2025, 4, 2)
    source["daily_transfer_total"] = Decimal("0")
    with pytest.raises(bank_app.InsufficientFundsError):
        bank_app.transfer(accounts, "SAV100", "CUR100", Decimal("10001"), date(2025, 4, 2))

    assert source["balance"] == Decimal("11000")
    assert destination["balance"] == Decimal("1000")
    assert source["daily_transfer_total"] == Decimal("0")


def test_change_pin_updates_pin_and_rejects_wrong_current_pin(savings_account):
    bank_app.change_pin(savings_account, "1234", "4321")
    assert savings_account["pin"] == "4321"

    with pytest.raises(bank_app.InvalidCurrentPinError):
        bank_app.change_pin(savings_account, "1234", "9999")

    with pytest.raises(bank_app.ValidationError):
        bank_app.change_pin(savings_account, "4321", "12A4")


def test_get_transaction_history_returns_newest_first_and_validates_limit(savings_account):
    bank_app.deposit(savings_account, Decimal("250"), date(2025, 5, 1))
    bank_app.withdraw(savings_account, Decimal("100"), date(2025, 5, 2))

    history = bank_app.get_transaction_history(savings_account, 2)

    assert [entry["type"] for entry in history] == ["WITHDRAWAL", "DEPOSIT"]
    assert history[0]["balance_after"] == Decimal("5150")
    assert history[1]["balance_after"] == Decimal("5250")
    assert history is not savings_account["transaction_history"]
    assert history[0] is not savings_account["transaction_history"][-1]

    with pytest.raises(bank_app.ValidationError):
        bank_app.get_transaction_history(savings_account, 0)


def test_main_handles_invalid_menu_selection(capsys, monkeypatch):
    inputs = iter(["9", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    bank_app.main()

    captured = capsys.readouterr()
    assert "Invalid menu selection. Choose 1, 2, or 3." in captured.out
    assert "Goodbye." in captured.out


def test_money_validation_helpers_and_daily_total_logic():
    assert bank_app._resolve_date(None) == date.today()
    with pytest.raises(bank_app.ValidationError):
        bank_app._resolve_date("2025-01-01")

    account = {"daily_withdrawal_date": date(2025, 1, 1), "daily_withdrawal_total": Decimal("1500")}
    assert bank_app._current_daily_total(account, "withdrawal", date(2025, 1, 1)) == Decimal("1500")
    assert bank_app._current_daily_total(account, "withdrawal", date(2025, 1, 2)) == Decimal("0")

    for value in (True, False, float("nan"), "abc"):
        with pytest.raises(bank_app.InvalidAmountError):
            bank_app._to_money(value)

    account = {"daily_transfer_date": date(2025, 1, 3), "daily_transfer_total": Decimal("2000")}
    assert bank_app._current_daily_total(account, "transfer", date(2025, 1, 3)) == Decimal("2000")

    with pytest.raises(bank_app.AccountNotFoundError):
        bank_app._get_account({}, "MISSING")


def test_cli_create_account_and_account_session(monkeypatch, capsys, accounts):
    create_inputs = iter(["A100", "Alice", "Savings", "5000"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(create_inputs))
    monkeypatch.setattr("bank_app.getpass", lambda prompt="": "1234")

    bank_app._create_account_from_cli(accounts)

    account = accounts["A100"]
    assert account["balance"] == Decimal("5000")

    session_inputs = iter([
        "1",
        "2",
        "100",
        "3",
        "100",
        "4",
        "B200",
        "50",
        "5",
        "6",
        "7",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(session_inputs))
    monkeypatch.setattr("bank_app.getpass", lambda prompt="": "1234" if prompt == "Current PIN: " else "4321")

    destination = bank_app.create_account(
        accounts,
        "B200",
        "Bob",
        "5678",
        "Current",
        Decimal("4000"),
        date(2025, 1, 1),
    )
    bank_app._account_session(accounts, account)

    assert account["pin"] == "4321"
    assert account["balance"] == Decimal("4950")
    assert destination["balance"] == Decimal("4050")
    output = capsys.readouterr().out
    assert "Balance:" in output
    assert "Deposit successful." in output
    assert "Withdrawal successful." in output
    assert "Transfer successful." in output
    assert "PIN changed successfully." in output
    assert "WITHDRAWAL" in output


def test_login_cli_handles_failed_and_successful_pin(monkeypatch, capsys, accounts):
    account = bank_app.create_account(
        accounts,
        "LOGIN001",
        "Charlie",
        "1234",
        "Savings",
        Decimal("2000"),
    )

    inputs = iter(["LOGIN001", "7"])
    pins = iter(["9999", "1234"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr("bank_app.getpass", lambda prompt="": next(pins))

    bank_app._login_from_cli(accounts)

    captured = capsys.readouterr()
    assert "Incorrect PIN" in captured.out
    assert f"Welcome, {account['customer_name']}." in captured.out
    assert "1. Check balance" in captured.out
