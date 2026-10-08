"""Educational, in-memory bank account and ATM CLI simulation.

This program is not real banking software. It uses no database or external
services, and all accounts exist only until the process exits.

Savings accounts must retain at least MINIMUM_SAVINGS_BALANCE after a cash
withdrawal or outgoing transfer. Current accounts may be reduced to zero.
Daily withdrawal and transfer totals are tracked separately per account and
reset logically when a transaction is made on a new calendar date. The CLI
uses the system date; business functions accept an explicit date for
deterministic use.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from getpass import getpass
from typing import TypedDict


# Monetary limits are expressed in rupees.
MAX_OPENING_BALANCE = Decimal("100000")
MAX_DEPOSIT_PER_TRANSACTION = Decimal("50000")
MAX_WITHDRAWAL_PER_TRANSACTION = Decimal("20000")
MAX_TRANSFER_PER_TRANSACTION = Decimal("25000")
MAX_DAILY_WITHDRAWAL = Decimal("30000")
MAX_DAILY_TRANSFER = Decimal("25000")
MINIMUM_SAVINGS_BALANCE = Decimal("1000")
MINIMUM_CURRENT_BALANCE = Decimal("0")
WITHDRAWAL_MULTIPLE = Decimal("100")
MAX_FAILED_LOGIN_ATTEMPTS = 3
MAX_HISTORY_ENTRIES = 10
ACCOUNT_TYPES = ("Savings", "Current")


class Transaction(TypedDict):
    date: date
    type: str
    amount: Decimal
    balance_after: Decimal
    related_account: str | None


class Account(TypedDict):
    account_id: str
    customer_name: str
    pin: str
    account_type: str
    balance: Decimal
    daily_withdrawal_date: date | None
    daily_withdrawal_total: Decimal
    daily_transfer_date: date | None
    daily_transfer_total: Decimal
    transaction_history: list[Transaction]


class BankingError(ValueError):
    """Base class for predictable business-rule failures."""


class ValidationError(BankingError):
    """An input value does not satisfy the required format or range."""


class InvalidAmountError(ValidationError):
    """An amount is malformed, nonpositive, or otherwise invalid."""


class TransactionLimitError(BankingError):
    """An operation exceeds its per-transaction limit."""


class DailyLimitError(BankingError):
    """An operation exceeds the applicable daily limit."""


class InsufficientFundsError(BankingError):
    """An operation would violate available funds or the account minimum."""


class AccountNotFoundError(BankingError):
    """The requested account ID is not present."""


class DuplicateAccountError(BankingError):
    """An account ID is already in use."""


class SameAccountTransferError(BankingError):
    """A transfer cannot have the same source and destination."""


class InvalidPinError(BankingError):
    """The supplied login PIN is incorrect."""

    def __init__(self, failed_attempts: int):
        self.failed_attempts = failed_attempts
        self.attempts_remaining = MAX_FAILED_LOGIN_ATTEMPTS - failed_attempts
        super().__init__(
            f"Incorrect PIN. {self.attempts_remaining} login attempt(s) remaining."
        )


class LoginLockedError(BankingError):
    """The current login session has exhausted its PIN attempts."""

    def __init__(self) -> None:
        super().__init__(
            "Login session locked after three incorrect PIN attempts. "
            "The account itself is not locked."
        )


class InvalidCurrentPinError(BankingError):
    """The current PIN supplied for a PIN change is incorrect."""


def _resolve_date(transaction_date: date | None) -> date:
    """Return a supplied transaction date or the system's current date."""
    if transaction_date is None:
        return date.today()
    if not isinstance(transaction_date, date):
        raise ValidationError("Transaction date must be a date.")
    return transaction_date


def _to_money(value: Decimal | int | str) -> Decimal:
    """Convert supported money inputs without accepting binary floats."""
    if isinstance(value, bool) or isinstance(value, float):
        raise InvalidAmountError("Amount must be a decimal, integer, or numeric string.")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise InvalidAmountError("Amount must be a valid number.") from None
    if not amount.is_finite():
        raise InvalidAmountError("Amount must be a finite number.")
    return amount


def _validate_pin(pin: str) -> None:
    if not isinstance(pin, str) or len(pin) != 4 or not pin.isascii() or not pin.isdigit():
        raise ValidationError("PIN must contain exactly four numeric digits.")


def _minimum_balance(account_type: str) -> Decimal:
    if account_type == "Savings":
        return MINIMUM_SAVINGS_BALANCE
    if account_type == "Current":
        return MINIMUM_CURRENT_BALANCE
    raise ValidationError("Account type must be Savings or Current.")


def _get_account(accounts: dict[str, Account], account_id: str) -> Account:
    if account_id not in accounts:
        raise AccountNotFoundError(f"Account '{account_id}' was not found.")
    return accounts[account_id]


def _current_daily_total(account: Account, kind: str, on_date: date) -> Decimal:
    date_key = f"daily_{kind}_date"
    total_key = f"daily_{kind}_total"
    if account[date_key] != on_date:
        return Decimal("0")
    return account[total_key]


def _record_transaction(
    account: Account,
    transaction_type: str,
    amount: Decimal,
    on_date: date,
    related_account: str | None = None,
) -> None:
    account["transaction_history"].append(
        {
            "date": on_date,
            "type": transaction_type,
            "amount": amount,
            "balance_after": account["balance"],
            "related_account": related_account,
        }
    )
    account["transaction_history"] = account["transaction_history"][-MAX_HISTORY_ENTRIES:]


def create_account(
    accounts: dict[str, Account],
    account_id: str,
    customer_name: str,
    pin: str,
    account_type: str,
    opening_balance: Decimal | int | str = Decimal("0"),
    transaction_date: date | None = None,
) -> Account:
    """Validate and add a new account; account IDs are case-sensitive."""
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValidationError("Account ID must not be blank.")
    account_id = account_id.strip()
    if account_id in accounts:
        raise DuplicateAccountError(f"Account '{account_id}' already exists.")
    if not isinstance(customer_name, str) or not customer_name.strip():
        raise ValidationError("Customer name must not be blank.")
    _validate_pin(pin)
    if account_type not in ACCOUNT_TYPES:
        raise ValidationError("Account type must be Savings or Current.")

    balance = _to_money(opening_balance)
    if balance < 0:
        raise InvalidAmountError("Opening balance must be nonnegative.")
    if balance > MAX_OPENING_BALANCE:
        raise TransactionLimitError("Opening balance must not exceed ₹100,000.")
    on_date = _resolve_date(transaction_date)

    account: Account = {
        "account_id": account_id,
        "customer_name": customer_name.strip(),
        "pin": pin,
        "account_type": account_type,
        "balance": balance,
        "daily_withdrawal_date": None,
        "daily_withdrawal_total": Decimal("0"),
        "daily_transfer_date": None,
        "daily_transfer_total": Decimal("0"),
        "transaction_history": [],
    }
    account["transaction_history"].append(
        {
            "date": on_date,
            "type": "OPENING",
            "amount": balance,
            "balance_after": balance,
            "related_account": None,
        }
    )
    accounts[account_id] = account
    return account


def authenticate_account(
    accounts: dict[str, Account],
    account_id: str,
    pin: str,
    failed_attempts: int = 0,
) -> Account:
    """Authenticate one attempt; callers pass prior failures for this session.

    Invalid PIN formatting does not count as an authentication attempt.
    A wrong PIN on the third attempt raises LoginLockedError; no lock is stored
    on the account, so a later login session starts with zero failed attempts.
    """
    if isinstance(failed_attempts, bool) or not isinstance(failed_attempts, int):
        raise ValidationError("Failed-attempt count must be an integer.")
    if failed_attempts < 0 or failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        raise LoginLockedError()
    _validate_pin(pin)
    account = _get_account(accounts, account_id)
    if pin == account["pin"]:
        return account
    if failed_attempts + 1 >= MAX_FAILED_LOGIN_ATTEMPTS:
        raise LoginLockedError()
    raise InvalidPinError(failed_attempts + 1)


def check_balance(account: Account) -> Decimal:
    """Return the account's current balance."""
    return account["balance"]


def deposit(
    account: Account,
    amount: Decimal | int | str,
    transaction_date: date | None = None,
) -> Decimal:
    """Deposit a positive amount up to the per-transaction deposit limit."""
    value = _to_money(amount)
    if value <= 0:
        raise InvalidAmountError("Deposit amount must be positive.")
    if value > MAX_DEPOSIT_PER_TRANSACTION:
        raise TransactionLimitError("Deposit must not exceed ₹50,000 per transaction.")
    on_date = _resolve_date(transaction_date)

    new_balance = account["balance"] + value
    account["balance"] = new_balance
    _record_transaction(account, "DEPOSIT", value, on_date)
    return new_balance


def withdraw(
    account: Account,
    amount: Decimal | int | str,
    transaction_date: date | None = None,
) -> Decimal:
    """Withdraw cash after validating amount, daily limit, and minimum balance."""
    value = _to_money(amount)
    if value <= 0:
        raise InvalidAmountError("Withdrawal amount must be positive.")
    if value % WITHDRAWAL_MULTIPLE != 0:
        raise InvalidAmountError("Cash withdrawal must be a multiple of ₹100.")
    if value > MAX_WITHDRAWAL_PER_TRANSACTION:
        raise TransactionLimitError("Withdrawal must not exceed ₹20,000 per transaction.")

    on_date = _resolve_date(transaction_date)
    daily_total = _current_daily_total(account, "withdrawal", on_date)
    if value > MAX_DAILY_WITHDRAWAL - daily_total:
        raise DailyLimitError("Withdrawal exceeds the ₹30,000 daily limit.")

    minimum = _minimum_balance(account["account_type"])
    new_balance = account["balance"] - value
    if not (account["balance"] >= value and new_balance >= minimum):
        raise InsufficientFundsError(
            f"Withdrawal must leave at least ₹{minimum:,.2f} in the account."
        )

    account["balance"] = new_balance
    account["daily_withdrawal_date"] = on_date
    account["daily_withdrawal_total"] = daily_total + value
    _record_transaction(account, "WITHDRAWAL", value, on_date)
    return new_balance


def transfer(
    accounts: dict[str, Account],
    source_account_id: str,
    destination_account_id: str,
    amount: Decimal | int | str,
    transaction_date: date | None = None,
) -> tuple[Decimal, Decimal]:
    """Transfer between existing accounts after all validations pass.

    Returns the new (source balance, destination balance). All validation is
    completed before either account is mutated.
    """
    source = _get_account(accounts, source_account_id)
    destination = _get_account(accounts, destination_account_id)
    if source_account_id == destination_account_id:
        raise SameAccountTransferError("Source and destination accounts must differ.")

    value = _to_money(amount)
    if value <= 0:
        raise InvalidAmountError("Transfer amount must be positive.")
    if value > MAX_TRANSFER_PER_TRANSACTION:
        raise TransactionLimitError("Transfer must not exceed ₹25,000 per transaction.")

    on_date = _resolve_date(transaction_date)
    daily_total = _current_daily_total(source, "transfer", on_date)
    if value > MAX_DAILY_TRANSFER - daily_total:
        raise DailyLimitError("Transfer exceeds the ₹25,000 daily outgoing limit.")

    minimum = _minimum_balance(source["account_type"])
    source_balance = source["balance"] - value
    if not (source["balance"] >= value and source_balance >= minimum):
        raise InsufficientFundsError(
            f"Transfer must leave at least ₹{minimum:,.2f} in the source account."
        )
    destination_balance = destination["balance"] + value

    # Commit only after both accounts and all transaction rules are validated.
    source["balance"] = source_balance
    destination["balance"] = destination_balance
    source["daily_transfer_date"] = on_date
    source["daily_transfer_total"] = daily_total + value
    _record_transaction(source, "TRANSFER_OUT", value, on_date, destination_account_id)
    _record_transaction(destination, "TRANSFER_IN", value, on_date, source_account_id)
    return source_balance, destination_balance


def change_pin(account: Account, current_pin: str, new_pin: str) -> None:
    """Change a PIN only when the current PIN and new PIN format are valid."""
    _validate_pin(current_pin)
    if current_pin != account["pin"]:
        raise InvalidCurrentPinError("Current PIN is incorrect.")
    _validate_pin(new_pin)
    account["pin"] = new_pin


def get_transaction_history(
    account: Account, limit: int = MAX_HISTORY_ENTRIES
) -> list[Transaction]:
    """Return a copy of the most recent history entries, newest first."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValidationError("History limit must be a positive integer.")
    return [dict(item) for item in reversed(account["transaction_history"][-limit:])]


def _read_amount(prompt: str) -> Decimal:
    return _to_money(input(prompt).strip())


def _display_amount(amount: Decimal) -> str:
    return f"₹{amount:,.2f}"


def _account_session(accounts: dict[str, Account], account: Account) -> None:
    while True:
        print(
            "\n1. Check balance  2. Deposit  3. Withdraw  4. Transfer\n"
            "5. Change PIN     6. Transaction history  7. Log out"
        )
        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                print(f"Balance: {_display_amount(check_balance(account))}")
            elif choice == "2":
                balance = deposit(account, _read_amount("Deposit amount: "))
                print(f"Deposit successful. Balance: {_display_amount(balance)}")
            elif choice == "3":
                balance = withdraw(account, _read_amount("Withdrawal amount: "))
                print(f"Withdrawal successful. Balance: {_display_amount(balance)}")
            elif choice == "4":
                destination_id = input("Destination account ID: ").strip()
                source_balance, _ = transfer(
                    accounts,
                    account["account_id"],
                    destination_id,
                    _read_amount("Transfer amount: "),
                )
                print(f"Transfer successful. Balance: {_display_amount(source_balance)}")
            elif choice == "5":
                current_pin = getpass("Current PIN: ")
                new_pin = getpass("New four-digit PIN: ")
                change_pin(account, current_pin, new_pin)
                print("PIN changed successfully.")
            elif choice == "6":
                for item in get_transaction_history(account):
                    related = (
                        f" (account {item['related_account']})"
                        if item["related_account"] is not None
                        else ""
                    )
                    print(
                        f"{item['date'].isoformat()} {item['type']}: "
                        f"{_display_amount(item['amount'])}{related}; "
                        f"balance {_display_amount(item['balance_after'])}"
                    )
            elif choice == "7":
                return
            else:
                print("Invalid menu selection. Choose a number from 1 to 7.")
        except BankingError as error:
            print(f"Operation failed: {error}")


def _create_account_from_cli(accounts: dict[str, Account]) -> None:
    account_id = input("Account ID: ").strip()
    customer_name = input("Customer name: ").strip()
    pin = getpass("Choose a four-digit PIN: ")
    account_type = input("Account type (Savings/Current): ").strip().title()
    opening_text = input("Opening balance (press Enter for 0): ").strip()
    account = create_account(
        accounts,
        account_id,
        customer_name,
        pin,
        account_type,
        opening_text or "0",
    )
    print(
        f"Account created for {account['customer_name']} "
        f"(ID: {account['account_id']}, {account['account_type']})."
    )


def _login_from_cli(accounts: dict[str, Account]) -> None:
    account_id = input("Account ID: ").strip()
    failed_attempts = 0
    while True:
        pin = getpass("PIN: ")
        try:
            account = authenticate_account(accounts, account_id, pin, failed_attempts)
            print(f"Welcome, {account['customer_name']}.")
            _account_session(accounts, account)
            return
        except InvalidPinError as error:
            failed_attempts = error.failed_attempts
            print(error)
        except BankingError as error:
            print(f"Login failed: {error}")
            return


def main() -> None:
    """Run the terminal menu using in-memory account state."""
    accounts: dict[str, Account] = {}
    print("Educational Bank Account / ATM Simulation (not real banking software)")
    while True:
        print("\n1. Create account  2. Log in  3. Exit")
        try:
            choice = input("Choose an option: ").strip()
            if choice == "1":
                _create_account_from_cli(accounts)
            elif choice == "2":
                _login_from_cli(accounts)
            elif choice == "3":
                print("Goodbye.")
                return
            else:
                print("Invalid menu selection. Choose 1, 2, or 3.")
        except BankingError as error:
            print(f"Operation failed: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return


if __name__ == "__main__":
    main()
