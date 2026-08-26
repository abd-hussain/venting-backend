"""OpenAPI requestBody helpers for registration endpoints that parse Request.form()."""

from __future__ import annotations

VENTOR_REGISTER_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": [
                        "nickname",
                        "gender",
                        "language_ids",
                        "interest_ids",
                        "notifications_enabled",
                    ],
                    "properties": {
                        "nickname": {"type": "string", "minLength": 1, "maxLength": 20},
                        "gender": {
                            "type": "string",
                            "enum": ["male", "female", "prefer_not_to_say"],
                        },
                        "language_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "interest_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "other_interest_text": {
                            "type": "string",
                            "nullable": True,
                        },
                        "avatar_preset_index": {
                            "type": "integer",
                            "nullable": True,
                        },
                        "notifications_enabled": {"type": "boolean"},
                        "fcm_token": {"type": "string", "nullable": True},
                    },
                }
            },
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": [
                        "nickname",
                        "gender",
                        "language_ids",
                        "interest_ids",
                        "notifications_enabled",
                    ],
                    "properties": {
                        "nickname": {"type": "string"},
                        "gender": {
                            "type": "string",
                            "enum": ["male", "female", "prefer_not_to_say"],
                        },
                        "language_ids": {
                            "type": "string",
                            "description": 'JSON array string, e.g. ["en","ar"]',
                        },
                        "interest_ids": {
                            "type": "string",
                            "description": 'JSON array string, e.g. ["relationships"]',
                        },
                        "other_interest_text": {"type": "string"},
                        "avatar_preset_index": {"type": "integer"},
                        "notifications_enabled": {
                            "type": "string",
                            "description": '"true" or "false"',
                        },
                        "fcm_token": {"type": "string"},
                        "avatar": {
                            "type": "string",
                            "format": "binary",
                            "description": "Optional gallery photo",
                        },
                    },
                }
            },
        },
    }
}


LISTENER_REGISTER_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": [
                        "full_name",
                        "agreed_to_terms",
                        "language_ids",
                        "comfort_area_ids",
                        "identity_document",
                        "selfie",
                    ],
                    "properties": {
                        "full_name": {"type": "string"},
                        "phone": {"type": "string"},
                        "phone_country": {"type": "string"},
                        "agreed_to_terms": {
                            "type": "string",
                            "description": '"true" or "false"',
                        },
                        "date_of_birth": {
                            "type": "string",
                            "description": "YYYY-MM-DD",
                        },
                        "country_iso": {"type": "string"},
                        "city": {"type": "string"},
                        "language_ids": {
                            "type": "string",
                            "description": 'JSON array string, e.g. ["en","ar"]',
                        },
                        "life_experience_ids": {
                            "type": "string",
                            "description": 'JSON array string',
                        },
                        "custom_experiences": {
                            "type": "string",
                            "description": 'JSON array string',
                        },
                        "comfort_area_ids": {
                            "type": "string",
                            "description": 'JSON array string',
                        },
                        "custom_comfort_area_text": {"type": "string"},
                        "boundary_ids": {
                            "type": "string",
                            "description": 'JSON array string',
                        },
                        "custom_boundary_text": {"type": "string"},
                        "availability": {
                            "type": "string",
                            "description": "JSON object (#37 shape)",
                        },
                        "accept_instant_calls": {
                            "type": "string",
                            "description": '"true" or "false"',
                        },
                        "session_minutes": {
                            "type": "integer",
                            "description": "Preferred session length (e.g. 30)",
                        },
                        "notifications_enabled": {
                            "type": "string",
                            "description": '"true" or "false"',
                        },
                        "fcm_token": {"type": "string"},
                        "voice_intro_seconds": {"type": "integer"},
                        "avatar": {"type": "string", "format": "binary"},
                        "identity_document": {
                            "type": "string",
                            "format": "binary",
                            "description": "Single government-ID photo (required)",
                        },
                        "selfie": {"type": "string", "format": "binary"},
                        "voice_intro": {"type": "string", "format": "binary"},
                        "document_front": {
                            "type": "string",
                            "format": "binary",
                            "description": "Legacy alias for identity_document",
                        },
                    },
                }
            }
        },
    }
}
