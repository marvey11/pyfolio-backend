# core

Shared Pyfolio domain and persistence package. It defines countries, currencies, securities, security quotes, and FX rates; identifier and ISO-code validation; SQLAlchemy database configuration; and persistence services for resources and idempotent quote/rate writes.

The `Currency` entity is a dedicated reference table. Production reference data will be supplied by a future worker; the core package does not seed production currencies. Quotes and FX rates reference currencies through foreign keys. FX rates are quoted as units of foreign currency per EUR 1.00; EUR itself is implicit. Exchange identifiers are trimmed and uppercased.

Test this package from the repository root with `uv run --package core pytest libs/core/tests`.
