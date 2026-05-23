"""
tools/clinical_trials_api.py
─────────────────────────────
Python tool wrapping the ClinicalTrials.gov REST API v2.

This module does two things:
  1. Provides a plain Python function `search_trials()` that the Searcher
     agent calls directly (after the PreToolUse hook has cleared it).
  2. Provides the Anthropic-compatible tool schema dict so the SDK can
     describe the tool to Claude in a messages.create() call.

ClinicalTrials.gov API v2 reference:
  https://clinicaltrials.gov/data-api/api

Key v2 behaviour:
  - Base URL: https://clinicaltrials.gov/api/v2/studies
  - No API key required (public dataset)
  - query.cond      → condition / disease name
  - filter.overallStatus → RECRUITING  (comma-separated, uppercase)
  - fields          → pipe-separated list of field paths to return
  - pageSize        → max 1000, we cap at MAX_TRIALS (default 20)
  - format          → json

Response shape (simplified):
  {
    "studies": [
      {
        "protocolSection": {
          "identificationModule":     { "nctId", "officialTitle" },
          "eligibilityModule":        { "eligibilityCriteria" },
          "contactsLocationsModule":  { "locations": [...], "centralContacts": [...] },
          "designModule":             { "phases": [...] }
        }
      }
    ]
  }
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from utils.logger import get_logger
from utils.state import RawTrial

logger = get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_BASE_URL: str = os.environ.get(
    "CLINICAL_TRIALS_API_BASE_URL",
    "https://clinicaltrials.gov/api/v2"
)
_MAX_TRIALS: int = int(os.environ.get("MAX_TRIALS", "20"))
_TIMEOUT_SECONDS: float = 30.0

# Fields we request — v2 uses dot-path syntax
_REQUESTED_FIELDS: str = "|".join([
    "NCTId",
    "OfficialTitle",
    "EligibilityCriteria",
    "LocationFacility",
    "LocationCity",
    "LocationCountry",
    "Phase",
    "CentralContactName",
    "CentralContactEMail",
    "CentralContactPhone",
])


# ── Core search function ──────────────────────────────────────────────────────

def search_trials(condition: str, max_results: int = _MAX_TRIALS) -> list[dict[str, Any]]:
    """
    Query ClinicalTrials.gov API v2 for actively recruiting trials.

    Args:
        condition:   Primary condition / disease (maps to query.cond).
        max_results: Cap on returned trials (default from MAX_TRIALS env var).

    Returns:
        List of RawTrial dicts (serialized via .model_dump()) with keys:
          nct_id, official_title, eligibility_criteria, locations,
          phase, contact_name, contact_email, contact_phone

    Raises:
        httpx.HTTPStatusError: If the API returns a non-2xx status.
        httpx.TimeoutException: If the API call exceeds _TIMEOUT_SECONDS.
        RuntimeError:          On unexpected response shape.
    """
    logger.info(f"Searching ClinicalTrials.gov for condition='{condition}', max={max_results}")

    params: dict[str, Any] = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "fields": _REQUESTED_FIELDS,
        "pageSize": min(max_results, _MAX_TRIALS),
        "format": "json",
    }

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            response = client.get(f"{_BASE_URL}/studies", params=params)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise httpx.TimeoutException(
            f"ClinicalTrials.gov API timed out after {_TIMEOUT_SECONDS}s"
        ) from exc
    except httpx.ProxyError as exc:
        raise RuntimeError(
            f"Network proxy blocked the ClinicalTrials.gov request. "
            f"Ensure you have outbound HTTPS access on port 443. Detail: {exc}"
        ) from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Could not connect to ClinicalTrials.gov. Check network connectivity. Detail: {exc}"
        ) from exc

    raw_data: dict = response.json()
    studies: list[dict] = raw_data.get("studies", [])

    logger.info(f"API returned {len(studies)} studies")

    trials: list[dict[str, Any]] = []
    for study in studies:
        parsed = _parse_study(study)
        if parsed:
            trials.append(parsed.model_dump())

    logger.info(f"Successfully parsed {len(trials)} trials")
    return trials


def _parse_study(study: dict) -> RawTrial | None:
    """
    Extract the fields we care about from a v2 study object.

    Returns None if the study is missing critical fields (nctId or title).
    """
    try:
        protocol = study.get("protocolSection", {})

        # ── Identification ──
        id_module = protocol.get("identificationModule", {})
        nct_id: str = id_module.get("nctId", "")
        official_title: str = (
            id_module.get("officialTitle")
            or id_module.get("briefTitle", "")
        )

        if not nct_id or not official_title:
            logger.warning(f"Skipping study with missing nctId or title: {study}")
            return None

        # ── Eligibility ──
        eligibility_module = protocol.get("eligibilityModule", {})
        eligibility_criteria: str = eligibility_module.get("eligibilityCriteria", "Not provided")

        # ── Locations ──
        contacts_module = protocol.get("contactsLocationsModule", {})
        raw_locations: list[dict] = contacts_module.get("locations", [])
        locations: list[str] = []
        for loc in raw_locations[:5]:  # Cap at 5 locations to stay concise
            city = loc.get("city", "")
            country = loc.get("country", "")
            facility = loc.get("facility", "")
            loc_str = ", ".join(filter(None, [facility, city, country]))
            if loc_str:
                locations.append(loc_str)

        # ── Phase ──
        design_module = protocol.get("designModule", {})
        phases: list[str] = design_module.get("phases", [])
        phase: str = "/".join(phases) if phases else "N/A"

        # ── Central contacts ──
        central_contacts: list[dict] = contacts_module.get("centralContacts", [])
        contact_name = contact_email = contact_phone = ""
        if central_contacts:
            first_contact = central_contacts[0]
            contact_name = first_contact.get("name", "")
            contact_email = first_contact.get("email", "")
            contact_phone = first_contact.get("phone", "")

        return RawTrial(
            nct_id=nct_id,
            official_title=official_title,
            eligibility_criteria=eligibility_criteria,
            locations=locations,
            phase=phase,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

    except Exception as exc:
        logger.error(f"Failed to parse study object: {exc} — study keys: {list(study.keys())}")
        return None


# ── Anthropic tool schema ─────────────────────────────────────────────────────

CLINICAL_TRIALS_TOOL_SCHEMA: dict[str, Any] = {
    "name": "search_clinical_trials",
    "description": (
        "Search ClinicalTrials.gov API v2 for actively recruiting clinical trials "
        "matching a given medical condition. Returns up to 20 trial objects with "
        "NCT ID, official title, eligibility criteria, locations, phase, and "
        "contact information."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "condition": {
                "type": "string",
                "description": (
                    "The primary medical condition to search for. "
                    "Use standard medical terminology (e.g., 'Type 2 Diabetes', "
                    "'Non-small cell lung cancer', 'Atrial fibrillation'). "
                    "Do NOT include patient names or personal identifiers."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": f"Maximum number of trials to return (default: {_MAX_TRIALS}, max: {_MAX_TRIALS}).",
                "default": _MAX_TRIALS,
            },
        },
        "required": ["condition"],
    },
}
