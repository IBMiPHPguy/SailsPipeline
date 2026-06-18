import json
import urllib.error
import urllib.parse
import urllib.request

login_body = urllib.parse.urlencode({"username": "admin", "password": "AdminPass1!"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/auth/login",
    data=login_body,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    token = json.load(resp)["access_token"]

headers = {"Authorization": f"Bearer {token}"}
req = urllib.request.Request("http://localhost:8000/api/requests/1", headers=headers)
with urllib.request.urlopen(req) as resp:
    detail = json.load(resp)

cruise = next(c for c in detail["proposed_cruises"] if c["id"] == 1)
cruise_id = cruise["id"]
print("cruise id", cruise_id, "status", cruise["status"])
print("before", [[p["id"] for p in room] for room in cruise.get("room_passengers", [])])
print("cabin_pricing", cruise.get("cabin_pricing"))
print("reservations", detail.get("cabin_hold_reservation_ids"))

payload = {
    "departure_date": cruise["departure_date"],
    "cruise_line": cruise["cruise_line"],
    "ship": cruise["ship"],
    "number_of_nights": cruise["number_of_nights"],
    "itinerary_name": cruise["itinerary_name"],
    "room_category": cruise["room_category"],
    "room_number": cruise["room_number"],
    "passengers_in_room": cruise["passengers_in_room"],
    "deposit_amount": cruise["deposit_amount"],
    "deposit_due_date": cruise["deposit_due_date"],
    "final_payment_due_date": cruise["final_payment_due_date"],
    "cost": cruise["cost"],
    "includes": cruise["includes"],
    "cabin_pricing": cruise["cabin_pricing"],
    "status": cruise["status"],
    "room_passenger_ids": [[1], [2]],
    "passenger_ids": [1, 2],
}
body = json.dumps(payload).encode()
url = f"http://localhost:8000/api/requests/1/proposed-cruises/{cruise_id}"
req = urllib.request.Request(
    url,
    data=body,
    headers={**headers, "Content-Type": "application/json"},
    method="PATCH",
)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.load(resp)
        print("PATCH OK", [[p["id"] for p in room] for room in result.get("room_passengers", [])])
except urllib.error.HTTPError as e:
    print("PATCH FAILED", e.code, e.read().decode())

# also test updateRequest with empty reservation validation
res_payload = {"cabin_hold_reservation_ids": detail.get("cabin_hold_reservation_ids") or [[""], [""]]}
body2 = json.dumps(res_payload).encode()
req2 = urllib.request.Request(
    "http://localhost:8000/api/requests/1",
    data=body2,
    headers={**headers, "Content-Type": "application/json"},
    method="PATCH",
)
try:
    with urllib.request.urlopen(req2) as resp2:
        print("request PATCH OK")
except urllib.error.HTTPError as e:
    print("request PATCH FAILED", e.code, e.read().decode()[:500])
