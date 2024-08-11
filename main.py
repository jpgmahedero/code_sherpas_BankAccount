# main.py

from fastapi import FastAPI, Query
from contextlib import asynccontextmanager  # used for setup in lifespan

from typing import Dict
from db import log_transaction, initialize_db, get_db, db_deposit, db_withdraw, get_sorted_transactions
from utils import populate_db, check_account_exists, get_account, check_amount_is_positive, \
    check_account_is_IBAN_compliant

from schemas import DepositRequest, DepositResponse
from schemas import WithdrawRequest, WithdrawResponse
from schemas import TransferRequest, TransferResponse
from schemas import Transaction


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('## startup')
    initialize_db()  # Initialize the db structure

    db = get_db()
    populate_db(db)  # Populate the db with data
    print('Database after population:', db)

    yield  # This runs the application

    print('## shutdown')


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return {"message": 'Hello World'}


@app.get("/status_all/", include_in_schema=False)
async def status_all():
    db: Dict = get_db()
    return {"message": db}


@app.get("/status", include_in_schema=False)
async def status():
    db: Dict = get_db()
    return {"message": db}


@app.get("/check_account/{account_number}")
async def check_account(account_number):
    check_account_exists(account_number)
    account = get_account(account_number)
    return {"message": account}


@app.post("/deposit", response_model=DepositResponse)
async def deposit(request: DepositRequest):
    check_account_exists(request.account)
    check_amount_is_positive(request.amount)

    # call the db
    account = db_deposit(request)
    log_transaction(type='deposit', account=request.account, amount=request.amount, balance=account["balance"])

    return DepositResponse(account=request.account, new_balance=account["balance"])


@app.post("/withdraw", response_model=WithdrawResponse)
async def withdraw(request: WithdrawRequest):
    check_account_exists(request.account)
    check_amount_is_positive(request.amount)

    # call the db
    account = db_withdraw(request)
    log_transaction(type='withdraw', account=request.account, amount=request.amount, balance=account["balance"])

    return WithdrawResponse(account=request.account, new_balance=account["balance"])


@app.post("/transfer", response_model=TransferResponse)
async def transfer(request: TransferRequest):
    # will check
    check_account_is_IBAN_compliant(request.dest_account)

    # First, perform the withdrawal from the source account
    withdraw_request = WithdrawRequest(account=request.src_account, amount=request.amount)
    withdraw_response = await withdraw(withdraw_request)

    # Then, perform the deposit into the destination account
    deposit_request = DepositRequest(account=request.dest_account, amount=request.amount)
    deposit_response = await deposit(deposit_request)

    # Return a summary of the transfer
    return TransferResponse(
        src_account=withdraw_response.account,  # Access the attribute directly
        src_new_balance=withdraw_response.new_balance,  # Access the attribute directly
        dest_account=deposit_response.account,  # Access the attribute directly
        dest_new_balance=deposit_response.new_balance  # Access the attribute directly
    )


@app.get("/account_statement/{account_number}")
async def account_statement(account_number: str, sort_order: str = Query("asc", patter="^(asc|desc)$")):
    """
    Get the account statement for a specific account number, sorted by date.

    Parameters:
    - account_number: The account number to fetch transactions for.
    - sort_order: The order to sort the transactions by date. Either 'asc' for ascending or 'desc' for descending.
    """
    print(f'order {sort_order}')
    # Get sorted transactions for the specific account number
    transactions = get_sorted_transactions(account_number, sort_order)


    return {"message": transactions}