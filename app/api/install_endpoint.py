from time import sleep
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from app.config import server
from elasticsearch import ElasticsearchException

from tracardi.domain.credentials import Credentials
from tracardi.service.setup.setup_indices import create_indices
from tracardi.service.setup.setup_plugins import add_plugins
from tracardi.service.storage.driver import storage
from tracardi.service.storage.indices_manager import get_missing_indices, remove_index


router = APIRouter()


@router.get("/install", tags=["installation"], include_in_schema=server.expose_gui_api, response_model=dict)
async def check_if_installation_complete():
    """
    Returns list of missing indices
    """
    sleep(2)
    try:
        missing_indices = [item async for item in get_missing_indices()]
        admins = await storage.driver.user.search_by_role('admin')

        return {
            "missing": [idx[1] for idx in missing_indices if idx[0] == 'missing'],
            "exists": [idx[1] for idx in missing_indices if idx[0] == 'exists'],
            "admins": admins.dict()
        }
    except ElasticsearchException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install", tags=["installation"], include_in_schema=server.expose_gui_api, response_model=dict)
async def install(credentials: Optional[Credentials]):
    try:
        if server.reset_plugins is True:
            await remove_index('action')

        created_indices = [idx async for idx in create_indices()]
        result = {
            "created": {
                "templates": [item[1] for item in created_indices if item[0] == 'template'],
                "indices": [item[1] for item in created_indices if item[0] == 'index'],
            }
        }

        if server.update_plugins_on_start_up is not False:
            result['plugins'] = await add_plugins()

        return result
    except ElasticsearchException as e:
        raise HTTPException(status_code=500, detail=str(e))
