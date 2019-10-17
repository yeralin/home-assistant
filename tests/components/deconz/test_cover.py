"""deCONZ cover platform tests."""
from copy import deepcopy

from asynctest import patch

from homeassistant.components import deconz
from homeassistant.setup import async_setup_component

import homeassistant.components.cover as cover

from .test_gateway import ENTRY_CONFIG, DECONZ_WEB_REQUEST, setup_deconz_integration

COVERS = {
    "1": {
        "id": "Level controllable cover id",
        "name": "Level controllable cover",
        "type": "Level controllable output",
        "state": {"bri": 255, "on": False, "reachable": True},
        "modelid": "Not zigbee spec",
        "uniqueid": "00:00:00:00:00:00:00:00-00",
    },
    "2": {
        "id": "Window covering device id",
        "name": "Window covering device",
        "type": "Window covering device",
        "state": {"bri": 255, "on": True, "reachable": True},
        "modelid": "lumi.curtain",
        "uniqueid": "00:00:00:00:00:00:00:01-00",
    },
    "3": {
        "id": "Unsupported cover id",
        "name": "Unsupported cover",
        "type": "Not a cover",
        "state": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:02-00",
    },
}


async def test_platform_manually_configured(hass):
    """Test that we do not discover anything or try to set up a gateway."""
    assert (
        await async_setup_component(
            hass, cover.DOMAIN, {"cover": {"platform": deconz.DOMAIN}}
        )
        is True
    )
    assert deconz.DOMAIN not in hass.data


async def test_no_covers(hass):
    """Test that no cover entities are created."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    gateway = await setup_deconz_integration(
        hass, ENTRY_CONFIG, options={}, get_state_response=data
    )
    assert len(gateway.deconz_ids) == 0
    assert len(hass.states.async_all()) == 0


async def test_cover(hass):
    """Test that all supported cover entities are created."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["lights"] = deepcopy(COVERS)
    gateway = await setup_deconz_integration(
        hass, ENTRY_CONFIG, options={}, get_state_response=data
    )
    assert "cover.level_controllable_cover" in gateway.deconz_ids
    assert "cover.window_covering_device" in gateway.deconz_ids
    assert "cover.unsupported_cover" not in gateway.deconz_ids
    assert len(hass.states.async_all()) == 5

    level_controllable_cover = hass.states.get("cover.level_controllable_cover")
    assert level_controllable_cover.state == "open"

    level_controllable_cover_device = gateway.api.lights["1"]

    level_controllable_cover_device.async_update({"state": {"on": True}})
    await hass.async_block_till_done()

    level_controllable_cover = hass.states.get("cover.level_controllable_cover")
    assert level_controllable_cover.state == "closed"

    with patch.object(
        level_controllable_cover_device, "_async_set_callback", return_value=True
    ) as set_callback:
        await hass.services.async_call(
            cover.DOMAIN,
            cover.SERVICE_OPEN_COVER,
            {"entity_id": "cover.level_controllable_cover"},
            blocking=True,
        )
        await hass.async_block_till_done()
        set_callback.assert_called_with("/lights/1/state", {"on": False})

    with patch.object(
        level_controllable_cover_device, "_async_set_callback", return_value=True
    ) as set_callback:
        await hass.services.async_call(
            cover.DOMAIN,
            cover.SERVICE_CLOSE_COVER,
            {"entity_id": "cover.level_controllable_cover"},
            blocking=True,
        )
        await hass.async_block_till_done()
        set_callback.assert_called_with("/lights/1/state", {"on": True, "bri": 255})

    with patch.object(
        level_controllable_cover_device, "_async_set_callback", return_value=True
    ) as set_callback:
        await hass.services.async_call(
            cover.DOMAIN,
            cover.SERVICE_STOP_COVER,
            {"entity_id": "cover.level_controllable_cover"},
            blocking=True,
        )
        await hass.async_block_till_done()
        set_callback.assert_called_with("/lights/1/state", {"bri_inc": 0})

    await gateway.async_reset()

    assert len(hass.states.async_all()) == 2
