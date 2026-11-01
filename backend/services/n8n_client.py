import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


class N8nIntegrationError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def submit_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.n8n_webhook_url or not settings.n8n_webhook_token:
        raise N8nIntegrationError('L’intégration n8n n’est pas configurée.', status_code=503)

    try:
        response = httpx.post(
            settings.n8n_webhook_url,
            json=payload,
            headers={'X-EASEIT-N8N-TOKEN': settings.n8n_webhook_token},
            timeout=settings.n8n_timeout_seconds,
        )
    except httpx.TimeoutException as error:
        logger.warning('n8n workflow request timed out')
        raise N8nIntegrationError('Le workflow n8n n’a pas répondu dans le délai prévu.', status_code=504) from error
    except httpx.RequestError as error:
        logger.warning('n8n workflow request failed: %s', type(error).__name__)
        raise N8nIntegrationError('Le service n8n est momentanément inaccessible.', status_code=503) from error

    if response.is_error:
        logger.warning('n8n workflow returned HTTP %s', response.status_code)
        raise N8nIntegrationError('n8n a refusé ou échoué à traiter la demande.')

    try:
        result = response.json()
    except ValueError as error:
        logger.warning('n8n workflow returned invalid JSON')
        raise N8nIntegrationError('La réponse du workflow n8n est invalide.') from error

    if not isinstance(result, dict):
        raise N8nIntegrationError('La réponse du workflow n8n est invalide.')
    return result
