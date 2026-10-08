# Software Testing Report for Bank Account / ATM Simulation

## 1. Project title and purpose

Project title: Bank Account / ATM Simulation (Python)

Purpose: This laboratory exercise validates the correctness of the in-memory banking business logic in `bank_app.py` using pytest. The testing effort focuses on business rules, transaction safety, validation behavior, account authentication, and state mutation checks rather than on UI interaction alone.

## 2. Application functionality

The application implements the following core behaviors:

- Account creation with validation for account ID, customer name, PIN, account type, and opening balance.
- Authentication using account ID and PIN with attempt tracking.
- Balance checks.
- Deposits with positive-amount and transaction-limit validation.
- Withdrawals with amount validation, daily-limit checks, and minimum-balance enforcement.
- Transfers between accounts with same-account prevention, daily outgoing limits, and minimum-balance checks.
- PIN changes using current PIN verification.
- Transaction history retrieval with newest-first ordering and a size limit.
- Terminal-style CLI flows for account creation, login, and menu navigation.

## 3. Testing scope and assumptions

Scope:

- Direct unit testing of business logic functions in `bank_app.py`.
- State-change verification for accept/reject outcomes.
- Validation of deterministic month/day business rules through explicit `date` inputs.
- Focused CLI validation for invalid menu input and startup safety.

Assumptions:

- The application is intentionally in-memory and does not persist data across runs.
- Business rules are defined by the actual implementation, not by assumptions from unrelated specifications.
- We do not modify the application behavior unless a genuine defect prevents a required rule from being meaningfully tested and the change is justified.

## 4. Testing framework and execution instructions

Framework:

- pytest
- pytest-cov

Commands to run:

```bash
cd /Users/jenilbuha/Desktop/sem7/stqa/p9
python3 -m pip install -r requirements.txt
python3 -m pytest -v
python3 -m pytest --cov=bank_app --cov-branch --cov-report=term-missing --cov-report=html
```

Note: The project uses a local virtual environment (`.venv`) and the above commands may be run inside that environment if preferred.

## 5. List of business logic functions tested

Planned test coverage targets the following functions and behaviors:

- `create_account()`
- `authenticate_account()`
- `check_balance()`
- `deposit()`
- `withdraw()`
- `transfer()`
- `change_pin()`
- `get_transaction_history()`
- CLI entry points: `main()`, `_login_from_cli()`, and invalid menu handling

## 6. Test case table

| Test ID | Feature/function | Input/preconditions | Technique | Expected result | Actual result | Status |
|---|---|---|---|---|---|---|
| TC-ACC-001 | Account creation | Valid account details | Boundary/domain | Account created with expected values | Measured pass via `test_create_account_valid` | Passed |
| TC-ACC-002 | Account creation invalid PIN | Invalid numeric PIN | Validation | `ValidationError` raised | Measured pass via parameterized validation tests | Passed |
| TC-AUTH-001 | Authentication success | Correct account ID and PIN | Normal path | Returns account | Measured pass via `test_authenticate_account_success_and_wrong_pin` | Passed |
| TC-AUTH-002 | Authentication failure | Wrong PIN | Error path | `InvalidPinError` with attempt count | Measured pass via `test_authenticate_account_success_and_wrong_pin` | Passed |
| TC-AUTH-003 | Authentication lockout | Three failed attempts | Boundary | `LoginLockedError` raised | Measured pass via `test_authenticate_account_lockout_and_invalid_attempt_count` | Passed |
| TC-DEP-001 | Deposit success | Positive amount under limit | Normal path | Balance increases and history updated | Measured pass via `test_deposit_updates_balance_and_history` | Passed |
| TC-DEP-002 | Deposit invalid amount | Zero / negative / oversize | Domain/boundary | `InvalidAmountError` or `TransactionLimitError` | Measured pass via `test_deposit_rejects_invalid_amounts` | Passed |
| TC-WD-001 | Withdrawal success | Valid savings withdrawal | Normal path | Balance decreases; daily total updated | Measured pass via `test_withdraw_valid_and_daily_total_updates` | Passed |
| TC-WD-002 | Withdrawal minimum balance | Leaves account below required minimum | Validation | `InsufficientFundsError` | Measured pass via `test_withdraw_rejects_invalid_values_and_leaves_state_unchanged` | Passed |
| TC-WD-003 | Daily withdrawal limit | Amount exceeding current daily limit | Boundary | `DailyLimitError` | Measured pass via `test_withdraw_rejects_daily_limit_and_keeps_state_unchanged` | Passed |
| TC-TR-001 | Transfer success | Valid source/destination transfer | Normal path | Both balances updated | Measured pass via `test_transfer_updates_both_accounts_and_daily_total` | Passed |
| TC-TR-002 | Transfer same account | Same source and destination | Validation | `SameAccountTransferError` | Measured pass via `test_transfer_rejects_same_account_and_invalid_amounts` | Passed |
| TC-TR-003 | Transfer daily limit | Exceeds source daily outgoing transfer limit | Boundary | `DailyLimitError` | Measured pass via `test_transfer_rejects_daily_limit_and_insufficient_funds` | Passed |
| TC-PIN-001 | PIN change | Correct current PIN and valid new PIN | Normal path | PIN updated | Measured pass via `test_change_pin_updates_pin_and_rejects_wrong_current_pin` | Passed |
| TC-PIN-002 | PIN change invalid current PIN | Wrong current PIN | Validation | `InvalidCurrentPinError` | Measured pass via `test_change_pin_updates_pin_and_rejects_wrong_current_pin` | Passed |
| TC-HIS-001 | History retrieval | Recent transactions | Normal path | Newest-first order | Measured pass via `test_get_transaction_history_returns_newest_first_and_validates_limit` | Passed |
| TC-CLI-001 | Invalid CLI menu input | Invalid menu selection | CLI validation | No crash; message displayed | Measured pass via `test_main_handles_invalid_menu_selection` | Passed |

## 7. Statement coverage analysis

Statement coverage targets the executable business logic in the module. The test suite exercises:

- Validation branches in `create_account()`, `authenticate_account()`, `deposit()`, `withdraw()`, `transfer()`, `change_pin()`, and `get_transaction_history()`.
- Success paths for each accepted transaction.
- Error paths for invalid amounts, invalid PINs, insufficient funds, daily limits, duplicate accounts, and missing accounts.
- State mutation checks for both the success and failure paths.
- CLI flows for account creation, login, invalid menu handling, and session operations.

Measured coverage after execution:

- Statements: 91% (251/274 executable statements covered)
- Branches: 89% (80/90 branches covered)
- Result: 29 tests passed

This is a strong result for the laboratory context, but it is not complete exploratory path coverage of every possible user path or every impossible branch combination.

## 8. Branch/decision coverage matrix

| Decision | Possible outcomes | Planned test cases |
|---|---|---|
| `if account_id in accounts` | True / False | Duplicate vs new account |
| `if balance < 0` | True / False | Negative and valid opening balances |
| `if balance > MAX_OPENING_BALANCE` | True / False | Below/above opening limit |
| `if pin == account["pin"]` | True / False | Correct vs incorrect PIN |
| `if failed_attempts + 1 >= MAX_FAILED_LOGIN_ATTEMPTS` | True / False | Final wrong attempt vs earlier wrong attempt |
| `if value <= 0` | True / False | Zero/negative vs valid positive deposit |
| `if value > MAX_DEPOSIT_PER_TRANSACTION` | True / False | Within/above deposit limit |
| `if value % WITHDRAWAL_MULTIPLE != 0` | True / False | Multiple-of-100 vs non-multiple |
| `if value > MAX_WITHDRAWAL_PER_TRANSACTION` | True / False | Within/above withdrawal limit |
| `if value > MAX_DAILY_WITHDRAWAL - daily_total` | True / False | Inside/outside daily limit |
| `if not (account["balance"] >= value and new_balance >= minimum)` | True / False | Sufficient vs insufficient funds |
| `if source_account_id == destination_account_id` | True / False | Same vs different account |
| `if value > MAX_TRANSFER_PER_TRANSACTION` | True / False | Within/above transfer limit |
| `if current_pin != account["pin"]` | True / False | Correct vs incorrect current PIN |
| `if isinstance(limit, bool) or ...` | True / False | Invalid vs valid history limit |

## 9. Condition coverage matrix

Atomic conditions identified for compound decisions include, for example:

- `account["balance"] >= value`
- `new_balance >= minimum`
- `source["balance"] >= value`
- `source_balance >= minimum`
- `pin == account["pin"]`
- `failed_attempts + 1 >= MAX_FAILED_LOGIN_ATTEMPTS`
- `value > MAX_DAILY_WITHDRAWAL - daily_total`

Each atomic condition will be evaluated to both TRUE and FALSE through representative valid and invalid test cases. The aim is not merely to trigger the outer branch but to exercise each atomic condition independently where feasible.

## 10. Predicate coverage matrix

For each relevant Boolean decision, the test suite will document the complete predicate result as well as the values of its constituent conditions. Examples include:

- `not (account["balance"] >= value and new_balance >= minimum)`
- `value > MAX_DAILY_WITHDRAWAL - daily_total`
- `source_account_id == destination_account_id`
- `failed_attempts + 1 >= MAX_FAILED_LOGIN_ATTEMPTS`
- `isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0`

Predicate coverage is distinct from condition coverage because both the combined predicate and its internal pieces are analyzed separately.

## 11. Selected control-flow/path analysis

Functions selected for path analysis:

- `withdraw()`
- `transfer()`
- `authenticate_account()`
- `change_pin()`
- `get_transaction_history()`

Method used:

- Decision-based path analysis and basis-path-style reasoning using decision points in the code. This yields independent business paths rather than exhaustive enumeration of all possible numeric inputs.

Important paths:

- Acceptable withdrawal path.
- Invalid amount path.
- Daily-limit violation path.
- Minimum-balance violation path.
- Transfer success path.
- Same-account transfer path.
- Insufficient-funds transfer path.
- Incorrect PIN path.
- Final PIN-attempt lockout path.
- History limit validation path.

Not every numeric combination can be enumerated exhaustively; some paths are infeasible or redundant because they are equivalent under the same business rule.

## 12. Cyclomatic complexity calculations

Selected functions and rough complexity estimates:

- `withdraw()` - decision points include amount validation, withdrawal multiple, per-transaction limit, daily limit, funds/minimum checks. Estimated V(G) = D + 1, where D is approximately 6 to 7 depending on how the compound conditions are counted. This is a medium-complexity function.
- `transfer()` - decision points include source/destination check, amount positivity, per-transaction limit, daily limit, minimum-balance validation, and commit path. Complexity is similarly medium-to-high.
- `authenticate_account()` - decision points include format validation, account lookup, correct PIN check, and lockout condition. This is a small-to-medium complexity function.
- `change_pin()` - several validation checks with a straightforward linear path. Complexity is low-to-medium.

The precise count depends on whether one counts compound predicates as a single decision or multiple atomic decisions; thus the report will use the usual decision-count approximation for practical interpretation.

## 13. Domain partitions and representative tests

### Amount values

- Positive values inside transaction limits.
- Zero and negative values.
- Values exactly equal to the maximum legal amount.
- Values just above the maximum legal amount.
- Multiples of ₹100 versus non-multiples for cash withdrawals.

### Account IDs

- Valid non-empty IDs.
- Blank or whitespace-only IDs.
- Duplicate IDs in existing account dictionary.
- Nonexistent IDs on lookup.

### PINs

- Four numeric digits.
- Too short, too long, non-numeric, and non-string values.
- Correct vs incorrect current PIN during change and authentication.

### Account types

- Savings.
- Current.
- Invalid values.

### Balances

- Nonnegative opening balances.
- Balances exactly at required minimum.
- Balances just below required minimum.
- Daily totals below, equal to, and above the transaction limit.

### Date handling

- Explicit transaction dates.
- The default system date behavior via `_resolve_date(None)`.
- Same-day processing versus new-day processing to ensure daily totals reset correctly.

## 14. Boundary Value Analysis tables

### Opening balance boundaries

| Boundary | Representative values | Purpose |
|---|---|---|
| Below minimum | `Decimal("-1")` | Reject negative opening balance |
| Zero | `Decimal("0")` | Allowed opening balance |
| Upper limit | `Decimal("100000")` | Highest allowed opening balance |
| Above limit | `Decimal("100001")` | Must reject |

### Deposit boundaries

| Boundary | Representative values | Purpose |
|---|---|---|
| Just below positive | `Decimal("0")` | Reject nonpositive deposit |
| Smallest positive | `Decimal("1")` | Accepted |
| Maximum allowed | `Decimal("50000")` | Accepted |
| Above maximum | `Decimal("50001")` | Reject |

### Withdrawal boundaries

| Boundary | Representative values | Purpose |
|---|---|---|
| Smallest positive | `Decimal("100")` | Accepted if funds allow |
| Near limit | `Decimal("19900")`, `Decimal("20000")`, `Decimal("20100")` | Validate per-transaction cap |
| Daily total boundary | `Decimal("30000")` and `Decimal("30001")` around daily cap | Validate daily limit |
| Minimum balance boundary | Account balance exactly at minimum and one rupee below | Validate minimum-savings-balance rule |

### Transfer boundaries

| Boundary | Representative values | Purpose |
|---|---|---|
| Maximum per-transfer | `Decimal("25000")` | Accepted if other rules allow |
| Above max | `Decimal("25001")` | Reject |
| Daily outgoing total | `Decimal("25000")` and `Decimal("25001")` | Validate current-day transfer limit |

### PIN boundaries

| Boundary | Representative values | Purpose |
|---|---|---|
| Too short | `"123"` | Invalid |
| Exact valid length | `"1234"` | Valid |
| Too long | `"12345"` | Invalid |
| Non-digit | `"12A4"` | Invalid |

## 15. Equivalence Class Partitioning tables

### Account creation

| Class | Representative inputs | Expected outcome |
|---|---|---|
| Valid account ID | `"A100"` | Accepted |
| Blank/whitespace account ID | `""`, `"   "` | Rejected |
| Duplicate account ID | Existing ID in dictionary | Rejected |
| Valid customer name | `"Asha"` | Accepted |
| Blank customer name | `""` | Rejected |
| Valid PIN | `"1234"` | Accepted |
| Invalid PIN | `"12A4"`, `"123"` | Rejected |
| Valid account type | `"Savings"`, `"Current"` | Accepted |
| Invalid account type | `"Credit"` | Rejected |

### Amount operations

| Class | Representative inputs | Expected outcome |
|---|---|---|
| Positive valid amount | `Decimal("500")` | Accepted |
| Zero and negative | `0`, `-100` | Rejected |
| Too large | `Decimal("50001")` for deposit | Rejected |
| Withdrawal multiple | `Decimal("100")`, `Decimal("200")` | Accepted |
| Non-multiple | `Decimal("150")` | Rejected |

### Authentication

| Class | Representative inputs | Expected outcome |
|---|---|---|
| Correct PIN | Correct known account PIN | Success |
| Wrong PIN | Other value | `InvalidPinError` |
| Final wrong attempt | Third consecutive failure | `LoginLockedError` |
| Invalid formatting PIN | `"12A4"` | `ValidationError` |

## 16. Uncovered branches, conditions, or statements and reasons

Measured coverage after execution:

- 91% statement coverage (251/274 executable statements)
- 89% branch coverage (80/90 branches)

The remaining uncovered lines are concentrated in uncommon validation and CLI error-handling paths, specifically:

- `Decimal("NaN")` / non-finite number rejection inside `_to_money()`.
- Rare account lookup failure paths in `_get_account()`.
- CLI exception paths that are intentionally guarded but were not triggered in normal test execution.
- `EOFError` / `KeyboardInterrupt` exits from `main()`.
- Some `BankingError` branches in the terminal menu that require forced error injection or interrupted CLI interaction.

These are legitimate untested edge cases, but they are not business-rule regressions in the implemented application. More exhaustive CLI fault injection could exercise them, but the direct business-logic tests already cover the dominant customer workflow and validation rules.

## 17. Known limitations and conclusion

- The application is an in-memory simulation and therefore does not expose a persistent database layer.
- The terminal CLI is intentionally small and text-based; testing focuses on business logic and direct input validation instead of true end-to-end whole-UI testing.
- Pytest-cov measures executable lines and branch coverage; it does not automatically prove condition, predicate, domain, or path coverage. Those are evaluated explicitly in the accompanying test design.

Measured conclusion: The implemented test suite exercises the primary business logic and CLI flows successfully and demonstrates solid coverage across validation, deposits, withdrawals, transfers, PIN changes, authentication, and transaction history. The measured result is 29 passing tests with 91% statement coverage and 89% branch coverage.

The exact commands used for reproduction are:

```bash
cd /Users/jenilbuha/Desktop/sem7/stqa/p9
. .venv/bin/activate
python -m pytest -q
python -m pytest --cov=bank_app --cov-branch --cov-report=term-missing --cov-report=html
```

This is a valid laboratory result for the current application version and is not claimed to be exhaustive path coverage of every impossible or contrived scenario.
