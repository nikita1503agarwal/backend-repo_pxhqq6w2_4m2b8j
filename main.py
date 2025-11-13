import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

# Local imports
from schemas import User, Customer, Product, Order, Sale
from database import db, create_document, get_documents

app = FastAPI(title="Business Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return str(v)
        except Exception:
            raise ValueError("Invalid ObjectId")

def serialize_doc(doc: dict):
    if not doc:
        return doc
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert datetimes to isoformat for JSON
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d

@app.get("/")
def read_root():
    return {"message": "Business Dashboard API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", None) or "Unknown"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Auth models for responses
class AuthRequest(BaseModel):
    name: Optional[str] = None
    email: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user: dict

@app.post("/auth/signup", response_model=AuthResponse)
def signup(payload: AuthRequest):
    # Very simple demo-only signup: store user document (password in plain text for demo)
    user = User(name=payload.name or payload.email.split("@")[0], email=payload.email, password=payload.password)
    try:
        user_id = create_document("user", user)
        return {"token": user_id, "user": {"id": user_id, "name": user.name, "email": user.email}}
    except Exception:
        # Fallback without DB
        return {"token": "demo-token", "user": {"id": "demo-user", "name": user.name, "email": user.email}}

@app.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest):
    # Demo login always succeeds and returns dummy token
    try:
        # Try to find user
        if db is not None:
            doc = db["user"].find_one({"email": payload.email})
            if doc:
                uid = str(doc["_id"])
                name = doc.get("name", payload.email)
                return {"token": uid, "user": {"id": uid, "name": name, "email": payload.email}}
    except Exception:
        pass
    return {"token": "demo-token", "user": {"id": "demo-user", "name": payload.email.split("@")[0], "email": payload.email}}

# CRUD Endpoints: Customers
@app.get("/customers")
def list_customers(q: Optional[str] = None):
    try:
        filt = {"name": {"$regex": q, "$options": "i"}} if q else {}
        docs = get_documents("customer", filt)
        return [serialize_doc(d) for d in docs]
    except Exception:
        # Dummy data fallback
        return [{"id": "c1", "name": "Alice", "email": "alice@example.com", "status": "active"}]

@app.post("/customers")
def create_customer(customer: Customer):
    try:
        cid = create_document("customer", customer)
        return {"id": cid}
    except Exception:
        return {"id": "demo"}

@app.put("/customers/{customer_id}")
def update_customer(customer_id: str, payload: Customer):
    try:
        if db is None:
            return {"updated": False}
        db["customer"].update_one({"_id": ObjectId(customer_id)}, {"$set": payload.model_dump()})
        return {"updated": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: str):
    try:
        if db is None:
            return {"deleted": False}
        db["customer"].delete_one({"_id": ObjectId(customer_id)})
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# CRUD Endpoints: Products
@app.get("/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    try:
        filt = {}
        if category:
            filt["category"] = category
        if q:
            filt["title"] = {"$regex": q, "$options": "i"}
        docs = get_documents("product", filt)
        return [serialize_doc(d) for d in docs]
    except Exception:
        return [
            {"id": "p1", "title": "Premium Plan", "price": 99, "category": "subscriptions", "in_stock": True}
        ]

@app.post("/products")
def create_product(product: Product):
    try:
        pid = create_document("product", product)
        return {"id": pid}
    except Exception:
        return {"id": "demo"}

@app.put("/products/{product_id}")
def update_product(product_id: str, payload: Product):
    try:
        if db is None:
            return {"updated": False}
        db["product"].update_one({"_id": ObjectId(product_id)}, {"$set": payload.model_dump()})
        return {"updated": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    try:
        if db is None:
            return {"deleted": False}
        db["product"].delete_one({"_id": ObjectId(product_id)})
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# CRUD Endpoints: Orders
@app.get("/orders")
def list_orders(status: Optional[str] = None):
    try:
        filt = {"status": status} if status else {}
        docs = get_documents("order", filt)
        # Join basic customer name
        results = []
        for d in docs:
            d = serialize_doc(d)
            if db is not None:
                cust = db["customer"].find_one({"_id": ObjectId(d["customer_id"])}) if d.get("customer_id") else None
                d["customer_name"] = cust.get("name") if cust else "—"
            results.append(d)
        return results
    except Exception:
        return [{"id": "o1", "status": "paid", "customer_name": "Alice", "items": [], "order_date": datetime.utcnow().isoformat()}]

@app.post("/orders")
def create_order(order: Order):
    try:
        oid = create_document("order", order)
        return {"id": oid}
    except Exception:
        return {"id": "demo"}

@app.put("/orders/{order_id}")
def update_order(order_id: str, payload: Order):
    try:
        if db is None:
            return {"updated": False}
        db["order"].update_one({"_id": ObjectId(order_id)}, {"$set": payload.model_dump()})
        return {"updated": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/orders/{order_id}")
def delete_order(order_id: str):
    try:
        if db is None:
            return {"deleted": False}
        db["order"].delete_one({"_id": ObjectId(order_id)})
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Analytics endpoint
class AnalyticsResponse(BaseModel):
    total_sales: float
    orders_count: int
    avg_order_value: float
    top_categories: List[dict]
    trend: List[dict]

@app.get("/analytics/overview", response_model=AnalyticsResponse)
def analytics_overview(
    start_date: Optional[str] = Query(None, description="ISO date"),
    end_date: Optional[str] = Query(None, description="ISO date"),
    category: Optional[str] = None,
):
    # Build filter for orders/sales
    try:
        filt = {}
        if start_date or end_date:
            rng = {}
            if start_date:
                rng["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                rng["$lte"] = datetime.fromisoformat(end_date)
            filt["order_date"] = rng
        if category:
            filt["items.category"] = category  # if items were expanded with category

        # Aggregate from orders collection
        if db is not None:
            pipeline = [
                {"$match": filt},
                {"$unwind": "$items"},
                {"$addFields": {"line_total": {"$multiply": ["$items.quantity", "$items.price"]}}},
                {"$group": {
                    "_id": {
                        "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}},
                        "category": "$items.category"
                    },
                    "sales": {"$sum": "$line_total"},
                    "orders": {"$addToSet": "$_id"}
                }},
            ]
            rows = list(db["order"].aggregate(pipeline))
            total_sales = float(sum(r.get("sales", 0) for r in rows))
            orders_count = len({str(oid) for r in rows for oid in r.get("orders", [])})
            avg_order_value = round(total_sales / orders_count, 2) if orders_count else 0.0
            # Top categories
            cat_map = {}
            trend_map = {}
            for r in rows:
                cat = r["_id"].get("category") or "Unknown"
                day = r["_id"].get("day")
                cat_map[cat] = cat_map.get(cat, 0) + float(r.get("sales", 0))
                trend_map[day] = trend_map.get(day, 0) + float(r.get("sales", 0))
            top_categories = sorted([
                {"category": k, "sales": round(v, 2)} for k, v in cat_map.items()
            ], key=lambda x: x["sales"], reverse=True)[:5]
            trend = [
                {"date": d, "sales": round(s, 2)} for d, s in sorted(trend_map.items())
            ]
            return AnalyticsResponse(
                total_sales=round(total_sales, 2),
                orders_count=orders_count,
                avg_order_value=avg_order_value,
                top_categories=top_categories,
                trend=trend,
            )
    except Exception:
        pass

    # Fallback dummy analytics
    dummy_trend = [
        {"date": "2025-11-01", "sales": 1200},
        {"date": "2025-11-02", "sales": 1800},
        {"date": "2025-11-03", "sales": 900},
        {"date": "2025-11-04", "sales": 1500},
        {"date": "2025-11-05", "sales": 2100},
    ]
    total = sum(p["sales"] for p in dummy_trend)
    return AnalyticsResponse(
        total_sales=float(total),
        orders_count=42,
        avg_order_value=round(total / 42, 2),
        top_categories=[{"category": "subscriptions", "sales": 3200}, {"category": "hardware", "sales": 2300}],
        trend=dummy_trend,
    )

# Optional schemas endpoint for viewers
@app.get("/schema")
def get_schema():
    return {
        "collections": [
            "user", "customer", "product", "order", "sale"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
