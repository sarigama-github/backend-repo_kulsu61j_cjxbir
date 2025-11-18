import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import re

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="Clothing Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(Product):
    pass


class ProductOut(Product):
    id: Optional[str] = None


class OrderCreate(Order):
    pass


@app.get("/")
def read_root():
    return {"message": "Clothing Shop Backend Running"}


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
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.get("/api/products", response_model=List[ProductOut])
def list_products(
    category: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    try:
        filter_dict = {}
        if category:
            filter_dict["category"] = category
        if size:
            filter_dict["sizes"] = {"$in": [size]}
        if color:
            filter_dict["colors"] = {"$in": [color]}
        if q:
            regex = re.compile(re.escape(q), re.IGNORECASE)
            filter_dict["$or"] = [{"title": regex}, {"description": regex}]

        docs = get_documents("product", filter_dict, limit=100)
        products: List[ProductOut] = []
        for d in docs:
            d_id = str(d.get("_id")) if d.get("_id") else None
            d.pop("_id", None)
            products.append(ProductOut(id=d_id, **d))
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str = Path(...)):
    try:
        if db is None:
            raise Exception("Database not available")
        doc = None
        try:
            oid = ObjectId(product_id)
            doc = db["product"].find_one({"_id": oid})
        except Exception:
            # allow lookup by custom id string if stored
            doc = db["product"].find_one({"id": product_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        d_id = str(doc.get("_id")) if doc.get("_id") else None
        doc.pop("_id", None)
        return ProductOut(id=d_id, **doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", response_model=dict)
def create_product(payload: ProductCreate):
    try:
        new_id = create_document("product", payload)
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orders", response_model=dict)
def create_order(payload: OrderCreate):
    try:
        # Optionally recalc totals server-side for integrity
        subtotal = sum([item.price * item.quantity for item in payload.items])
        shipping = payload.shipping if payload.shipping is not None else 0.0
        total = subtotal + shipping
        order_data = payload.model_dump()
        order_data["subtotal"] = round(subtotal, 2)
        order_data["shipping"] = round(shipping, 2)
        order_data["total"] = round(total, 2)
        new_id = create_document("order", order_data)
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
