import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import re

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem, Review, Wishlist

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


@app.get("/api/categories", response_model=List[str])
def list_categories():
    try:
        if db is None:
            raise Exception("Database not available")
        cats = db["product"].distinct("category")
        cats = [c for c in cats if isinstance(c, str)]
        cats.sort()
        return cats
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


# Reviews Endpoints
class ReviewCreate(Review):
    pass


@app.post("/api/reviews", response_model=dict)
def create_review(payload: ReviewCreate):
    try:
        # ensure product exists
        try:
            _ = get_product(payload.product_id)  # will raise 404 if not
        except HTTPException as he:
            if he.status_code == 404:
                raise
        new_id = create_document("review", payload)
        return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}/reviews", response_model=List[Review])
def list_reviews_for_product(product_id: str = Path(...)):
    try:
        docs = get_documents("review", {"product_id": product_id}, limit=200)
        # No _id in schema, so pop it
        for d in docs:
            d.pop("_id", None)
        return [Review(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}/rating", response_model=dict)
def get_product_rating(product_id: str = Path(...)):
    try:
        docs = get_documents("review", {"product_id": product_id}, limit=1000)
        ratings = [int(d.get("rating", 0)) for d in docs if d.get("rating") is not None]
        count = len(ratings)
        avg = round(sum(ratings) / count, 2) if count else 0
        return {"product_id": product_id, "average": avg, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Wishlist Endpoints
class WishlistCreate(Wishlist):
    pass


@app.get("/api/wishlist", response_model=List[dict])
def get_wishlist(email: str = Query(...)):
    try:
        if db is None:
            raise Exception("Database not available")
        docs = list(db["wishlist"].find({"email": email}))
        # Optionally join with product details
        results = []
        for w in docs:
            w_id = str(w.get("_id")) if w.get("_id") else None
            pid = w.get("product_id")
            prod = None
            try:
                prod = db["product"].find_one({"_id": ObjectId(pid)})
            except Exception:
                prod = db["product"].find_one({"id": pid})
            if prod:
                prod_id = str(prod.get("_id")) if prod.get("_id") else None
                prod.pop("_id", None)
            else:
                prod_id = None
                prod = None
            results.append({
                "id": w_id,
                "product_id": pid,
                "product": ({"id": prod_id, **prod} if prod else None)
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wishlist", response_model=dict)
def add_to_wishlist(payload: WishlistCreate):
    try:
        # ensure product exists
        try:
            _ = get_product(payload.product_id)
        except HTTPException as he:
            if he.status_code == 404:
                raise
        # prevent duplicates for same email+product
        existing = db["wishlist"].find_one({"email": payload.email, "product_id": payload.product_id})
        if existing:
            return {"id": str(existing["_id"])}
        new_id = create_document("wishlist", payload)
        return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/wishlist", response_model=dict)
def remove_from_wishlist(email: str = Query(...), product_id: str = Query(...)):
    try:
        if db is None:
            raise Exception("Database not available")
        res = db["wishlist"].delete_one({"email": email, "product_id": product_id})
        return {"deleted": res.deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
