Release Notes
=============

___

v1.1.0 (2025-10-14)
-------------------

New Features (v1.1.0)
---------------------
- Added end-to-end payload encryption for secure telemetry transmission using AES-256-GCM.
- Implemented `PayloadEncryptor` class with project-specific encryption keys.
- Added encrypted endpoint support for events and metrics (`/api/v1/events/encrypted`).
- Integrated automatic datetime serialization in encrypted payloads via custom JSON handler.
- Added encryption key verification during transport initialization.

Technical Details (v1.1.0)
--------------------------
- Encryption uses AES-256-GCM with 96-bit nonces and 128-bit authentication tags.
- Pydantic models are serialized using `.model_dump(mode="json")` before encryption.
- Custom `_default_json_handler` ensures datetime objects are properly ISO-formatted.

___

v1.0.2 (2025-09-12)
-------------------

Enhancements (v1.0.2)
---------------------
- Added dynamic rule updated event type.

___

v1.0.1 (2025-08-07)
-------------------

Enhancements (v1.0.1)
------------
- Added path_excluded event type.

___

v1.0.0 (2025-07-24)
-------------------

**Official Release**

___

v0.1.1 (2025-07-09)
-------------------

Enhancements (v0.1.1)
------------
- Standardized Redis Protocl/Manager methods across libraries.

___

v0.1.0 (2025-07-08)
-------------------

Enhancements (v0.1.0)
------------
- Switched from aiohttp to httpx for HTTP client.
- Completed implementation.
- 100% test coverage.

___

v0.0.1 (2025-06-22)
-------------------

New Features (v0.0.1)
------------
- Initial release FastAPI Guard Agent.
