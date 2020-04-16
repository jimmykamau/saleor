import json
import logging
import time
import uuid

import requests
from django.core.cache import cache
from django.utils import timezone

from ... import TransactionError, TransactionKind
from ...interface import GatewayConfig, GatewayResponse, PaymentData
from .utils import generate_lipa_password, get_access_token

logger = logging.getLogger(__name__)

def _access_token(config: GatewayConfig):
    CACHE_TTL = 45 * 10
    return cache.get_or_set(
        'mpesa_auth_key', get_access_token(config),
        CACHE_TTL
    )

def get_client_token(**_):
    return str(uuid.uuid4())


def get_billing_data(payment_information: PaymentData, config: GatewayConfig):
    shortcode = config.connection_params['shortcode']
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    password = generate_lipa_password(timestamp, config)
    callback_url = config.connection_params['callback_url']
    phone_number = payment_information.billing.phone[1:]
    token = payment_information.order_id if payment_information.order_id else payment_information.token

    return dict(
        BusinessShortCode=shortcode,
        Password=password.decode('utf-8'),
        Timestamp=timestamp,
        TransactionType="CustomerPayBillOnline",
        Amount=int(payment_information.amount),
        PartyA=phone_number,
        PartyB=shortcode,
        PhoneNumber=phone_number,
        CallBackURL=callback_url,
        AccountReference=token,
        TransactionDesc="M-PESA payment"
    )


def void(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    error = None
    success = dummy_success()
    if not success:
        error = "Unable to void the transaction."
    return GatewayResponse(
        is_success=success,
        action_required=False,
        kind=TransactionKind.VOID,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token,
        error=error,
    )


def capture(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    """Perform capture transaction."""
    error = None
    success = False
    action_required = False
    response_data = None
    billing_data = get_billing_data(payment_information, config)
    access_token = _access_token(config)
    try:
        response = requests.post(
            f"{config.connection_params['base_url']}mpesa/stkpush/v1/processrequest",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            data=json.dumps(billing_data)
        )
        response_data = response.json()
        response.raise_for_status()
    except Exception:
        if response_data:
            if response_data.get('errorMessage') == "Invalid Access Token":
                get_access_token(config)
                capture(payment_information, config)
            else:
                error = TransactionError.PROCESSING_ERROR
                logger.warning(f"Error initiating Mpesa payment: {response_data}", exc_info=True)
        else:
            logger.warning(f"Error initiating MPESA payment", exc_info=True)
            error = TransactionError.PROCESSING_ERROR
            action_required = True
    else:
        response_data['Timestamp'] = billing_data['Timestamp']
        success = True

    return GatewayResponse(
        is_success=success,
        action_required=action_required,
        kind=TransactionKind.CAPTURE,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=response_data.get('CheckoutRequestID', payment_information.token),
        error=error,
        raw_response=response_data
    )


def confirm(payment_information: PaymentData, config: GatewayConfig, capture_response: GatewayResponse) -> GatewayResponse:
    """Perform confirm transaction."""
    error = None
    response_data = None
    action_required = False
    success = False
    access_token = _access_token(config)
    timestamp = capture_response.raw_response['Timestamp']
    password = generate_lipa_password(timestamp, config)
    transaction_data = dict(
        BusinessShortCode=config.connection_params['shortcode'],
        Password=password.decode('utf-8'),
        Timestamp=timestamp,
        CheckoutRequestID=capture_response.raw_response['CheckoutRequestID']
    )

    try:
        response = requests.post(
            f"{config.connection_params['base_url']}mpesa/stkpushquery/v1/query",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            data=json.dumps(transaction_data)
        )
        response_data = response.json()
        response.raise_for_status()
    except Exception:
        if response_data:
            if response_data.get('errorMessage') == "The transaction is being processed":
                time.sleep(3)
                confirm(payment_information, config, capture_response)
            else:
                error = TransactionError.PROCESSING_ERROR
                logger.warning(f"Error confirming MPESA payment: {response_data}", exc_info=True)
                action_required = True
        else:
            logger.warning(f"Error confirming MPESA payment", exc_info=True)
            error = TransactionError.PROCESSING_ERROR
            action_required = True
    else:
        if response_data['ResultDesc'] == "The service request is processed successfully.":
            success = True
        else:
            error = TransactionError.DECLINED
            action_required = True

    return GatewayResponse(
        is_success=success,
        action_required=action_required,
        kind=TransactionKind.CONFIRM,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=response_data.get('CheckoutRequestID', payment_information.token),
        error=error,
        raw_response=response_data
    )


def refund(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    error = None
    success = dummy_success()
    if not success:
        error = "Unable to process refund"
    return GatewayResponse(
        is_success=success,
        action_required=False,
        kind=TransactionKind.REFUND,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token,
        error=error,
    )


def process_payment(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Process the payment."""
    capture_request = capture(payment_information=payment_information, config=config)
    if capture_request.error:
        return capture_request
    time.sleep(10)
    confirmation = confirm(payment_information, config, capture_request)
    return confirmation
