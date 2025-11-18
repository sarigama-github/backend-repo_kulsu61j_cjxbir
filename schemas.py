"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema for clothing items
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category, e.g., 'Tops', 'Bottoms', 'Outerwear'")
    in_stock: bool = Field(True, description="Whether product is in stock")
    sizes: List[str] = Field(default_factory=lambda: ["S", "M", "L", "XL"], description="Available sizes")
    colors: List[str] = Field(default_factory=lambda: ["black"], description="Available color names")
    image_url: Optional[str] = Field(None, description="Primary image URL")
    rating: Optional[float] = Field(4.5, ge=0, le=5, description="Average rating out of 5")
    badge: Optional[str] = Field(None, description="Optional badge text like 'New' or 'Sale'")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="ID of the product")
    title: str = Field(..., description="Snapshot of product title at purchase time")
    price: float = Field(..., ge=0, description="Unit price at purchase time")
    quantity: int = Field(1, ge=1, description="Quantity of this product")
    size: Optional[str] = Field(None, description="Selected size")
    color: Optional[str] = Field(None, description="Selected color (name or hex)")
    image_url: Optional[str] = Field(None, description="Image preview")

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    email: str = Field(..., description="Customer email")
    items: List[OrderItem] = Field(..., description="Items in the order")
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(0.0, ge=0)
    total: float = Field(..., ge=0)
    note: Optional[str] = Field(None)

class Review(BaseModel):
    """
    Reviews collection schema
    Collection name: "review"
    """
    product_id: str = Field(..., description="ID of the product being reviewed")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, description="Optional review text")
    author: Optional[str] = Field(None, description="Display name of reviewer")
    email: Optional[str] = Field(None, description="Reviewer email (optional)")

class Wishlist(BaseModel):
    """
    Wishlist collection schema (one document per wish pair)
    Collection name: "wishlist"
    """
    email: str = Field(..., description="Customer email owning the wishlist item")
    product_id: str = Field(..., description="Wished product id")
