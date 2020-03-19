from typing import TYPE_CHECKING

from saleor.extensions import ConfigurationTypeField
from saleor.extensions.base_plugin import BasePlugin

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
        self._initialize_plugin_configuration()
        if not self.active:
            return previous
        return fn(self, *args, **kwargs)

    return wrapped


class MpesaGatewayPlugin(BasePlugin):
    PLUGIN_NAME = GATEWAY_NAME
    CONFIG_STRUCTURE = {
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
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = None

    def _initialize_plugin_configuration(self):
        super()._initialize_plugin_configuration()

        if self._cached_config and self._cached_config.configuration:
            configuration = self._cached_config.configuration

            configuration = {item["name"]: item["value"] for item in configuration}
            self.config = GatewayConfig(
                gateway_name=GATEWAY_NAME,
                auto_capture=False,
                connection_params={
                    "consumer_key": configuration["Consumer key"],
                    "consumer_secret": configuration["Consumer secret"],
                    "base_url": configuration["Base URL"],
                    "shortcode": configuration["Business shortcode"],
                    "passkey": configuration["Online passkey"],
                    "callback_url": configuration["Callback URL"]
                },
                store_customer=False,
            )

    @classmethod
    def _get_default_configuration(cls):
        defaults = {
            "name": cls.PLUGIN_NAME,
            "description": "",
            "active": False,
            "configuration": [
                {"name": "Consumer key", "value": None},
                {"name": "Consumer secret", "value": None},
                {"name": "Base URL", "value": None},
                {"name": "Business shortcode", "value": None},
                {"name": "Online passkey", "value": None},
                {"name": "Callback URL", "value": None}
            ],
        }
        return defaults

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
