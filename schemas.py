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

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Auth/User schema
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=4, description="Plain text for demo only")
    role: str = Field("user", description="User role")
    is_active: bool = Field(True, description="Whether user is active")

# Customer schema
class Customer(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    status: str = Field("active", description="active|inactive")

# Product schema
class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    in_stock: bool = True

# Order item schema
class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)
    price: float = Field(..., ge=0)

# Order schema
class Order(BaseModel):
    customer_id: str
    items: List[OrderItem]
    status: str = Field("paid", description="paid|pending|refunded|shipped")
    order_date: datetime = Field(default_factory=datetime.utcnow)

# Sales record (optional standalone analytics docs if needed)
class Sale(BaseModel):
    order_id: str
    amount: float
    category: str
    date: datetime = Field(default_factory=datetime.utcnow)
