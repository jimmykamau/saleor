from typing import TYPE_CHECKING

from saleor.plugins.base_plugin import BasePlugin, ConfigurationTypeField

from . import (
    GatewayConfig,
    capture,
    confirm,
    get_client_token,
    process_payment,
    refund,
    void,
)

GATEWAY_NAME = "Mpesa"

if TYPE_CHECKING:
    from ...interface import GatewayResponse, PaymentData, TokenConfig


def require_active_plugin(fn):
    def wrapped(self, *args, **kwargs):
        previous = kwargs.get("previous_value", None)
        if not self.active:
            return previous
        return fn(self, *args, **kwargs)

    return wrapped


class MpesaGatewayPlugin(BasePlugin):
    PLUGIN_ID = "olduka.payments.mpesa"
    PLUGIN_NAME = GATEWAY_NAME
    DEFAULT_CONFIGURATION = [
        {"name": "Consumer key", "value": None},
        {"name": "Consumer secret", "value": None},
        {"name": "Base URL", "value": "https://sandbox.safaricom.co.ke/"},
        {"name": "Business shortcode", "value": "174379"},
        {"name": "Online passkey", "value": None},
        {"name": "Callback URL", "value": None},
        {"name": "Initiator security credential", "value": None},
        {"name": "Initiator name", "value": "apitest425"}
    ]

    CONFIG_STRUCTURE = {
        "Initiator name": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Provide username used to authenticate the transaction",
            "label": "Initiator name"
        },
        "Consumer key": {
            "type": ConfigurationTypeField.SECRET,
            "help_text": "Provide Mpesa Consumer Key",
            "label": "Consumer key"
        },
        "Consumer secret": {
            "type": ConfigurationTypeField.SECRET,
            "help_text": "Provide Mpesa Consumer Secret",
            "label": "Consumer secret"
        },
        "Base URL": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Provide the base URL for the Mpesa API",
            "label": "Mpesa API URL"
        },
        "Business shortcode": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Provide Mpesa Business Shortcode",
            "label": "Business shortcode"
        },
        "Online passkey": {
            "type": ConfigurationTypeField.SECRET,
            "help_text": "Provide Mpesa online passkey",
            "label": "Online passkey"
        },
        "Callback URL": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Provide the URL that Safaricom"
            " will call with transaction details",
            "label": "Callback URL"
        },
        "Initiator security credential": {
            "type": ConfigurationTypeField.SECRET,
            "help_text": "Provide the security credential "
            "generated on the Safaricom Portal",
            "label": "Initiator security credential"
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configuration = {item["name"]: item["value"] for item in self.configuration}
        self.config = GatewayConfig(
            gateway_name=GATEWAY_NAME,
            auto_capture=False,
            connection_params={
                "consumer_key": configuration["Consumer key"],
                "consumer_secret": configuration["Consumer secret"],
                "base_url": configuration["Base URL"],
                "shortcode": configuration["Business shortcode"],
                "passkey": configuration["Online passkey"],
                "callback_url": configuration["Callback URL"],
                "initiator_security_credential": configuration["Initiator security credential"],
                "initiator_name": configuration["Initiator name"]
            },
            store_customer=False,
        )   

    def _get_gateway_config(self):
        return self.config

    @require_active_plugin
    def capture_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return capture(payment_information, self._get_gateway_config())

    @require_active_plugin
    def confirm_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return confirm(payment_information, self._get_gateway_config())

    @require_active_plugin
    def refund_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return refund(payment_information, self._get_gateway_config())

    @require_active_plugin
    def void_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return void(payment_information, self._get_gateway_config())

    @require_active_plugin
    def process_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return process_payment(payment_information, self._get_gateway_config())

    @require_active_plugin
    def get_client_token(self, token_config: "TokenConfig", previous_value):
        return get_client_token()

    @require_active_plugin
    def get_payment_config(self, previous_value):
        config = self._get_gateway_config()
        return [
            {"field": "shortcode", "value": config.connection_params['shortcode']},
            {"field": "callback_url", "value": config.connection_params['callback_url']}
        ]
