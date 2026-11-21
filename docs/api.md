# API reference

All request and response bodies are JSON. Endpoints marked **Auth** need the header `Authorization: Bearer <token>`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | no | Liveness check, returns `{"status":"ok"}` |
| GET | `/api/db-check` | no | Confirms the database connection works |
| POST | `/api/signup` | no | Create an account |
| POST | `/api/login` | no | Returns a JWT valid for 8 hours |
| GET | `/api/me` | yes | Returns the logged-in user's ID |
| POST | `/api/customers` | yes | Add a customer |
| GET | `/api/customers` | yes | List the user's customers |
| POST | `/api/customers/<id>/entries` | yes | Add a credit or payment entry |
| GET | `/api/customers/<id>/entries` | yes | Entries (newest first) plus the balance |
| GET | `/api/summary` | yes | All customers with balances, highest first |

## Examples

**Sign up / log in** (`POST /api/signup`, `POST /api/login`)
```json
{ "email": "shop@example.com", "password": "at-least-8-characters" }
```
Login response: `{ "token": "<jwt>" }`

**Add customer** (`POST /api/customers`)
```json
{ "name": "Ramesh", "phone": "9999999999" }
```

**Add entry** (`POST /api/customers/<id>/entries`)
```json
{ "type": "credit", "amount": "250.50", "note": "groceries", "entry_date": "2026-11-22" }
```
- `type` is `credit` (customer took goods on credit) or `payment` (customer paid).
- `amount` must be above 0 with at most 2 decimals.
- `entry_date` is optional and defaults to today.

**Entries response** (`GET /api/customers/<id>/entries`)
```json
{
  "balance": "300.00",
  "entries": [
    { "id": 2, "amount": "200.00", "type": "payment", "note": null, "entry_date": "2026-11-22" }
  ]
}
```
A positive balance means the customer owes the shopkeeper.

## Error format

`{ "error": "human readable message" }` with status `400` (bad input), `401` (not logged in or wrong credentials), `404` (not found, or not yours), or `409` (email already registered).
