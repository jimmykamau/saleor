import base64
import logging

import requests

from ...interface import GatewayConfig

logger = logging.getLogger(__name__)

def generate_auth_string(config: GatewayConfig):
    connection_params = config.connection_params
    return base64.b64encode(
        f"{connection_params['consumer_key']}:{connection_params['consumer_secret']}".encode('utf-8'))


def generate_lipa_password(timestamp, config: GatewayConfig):
    connection_params = config.connection_params
    return base64.b64encode(
        f"{connection_params['shortcode']}{connection_params['passkey']}{timestamp}".encode('utf-8')
    )


def get_access_token(config: GatewayConfig):
    connection_params = config.connection_params
    auth_string = generate_auth_string(config).decode('utf-8')
    try:
        response = requests.get(
            f"{connection_params['base_url']}oauth/v1/generate?grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Error fetching Mpesa auth key")
        return None
    else:
        return response.json()['access_token']
