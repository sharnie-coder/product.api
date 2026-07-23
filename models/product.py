from datetime import datetime
from typing import Optional, List
import re
from pydantic import field_validator, model_validator, EmailStr
from sqlmodel import SQLModel, Field, Relationship

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    products: List["Product"] = Relationship(back_populates="category_rel")

class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, min_length=2, max_length=100)
    contact_person: str
    email: EmailStr = Field(index=True, unique=True)
    phone: str
    is_active: bool = True
    products: List["Product"] = Relationship(back_populates="supplier_rel")

class Product(SQLModel, table=True):
    id: Optional[int]=Field(default=None,primary_key=True)
    name:str=Field(index=True)
    description:str
    brand:str=Field(index=True)
    category:str=Field(index=True)
    price:float=Field(gt=0)
    stock:int=Field(default=0,ge=0)
    warranty_months:int=Field(default=0,ge=0)
    sku:str=Field(index=True,unique=True)
    created_at:datetime=Field(default_factory=datetime.utcnow)
    updated_at:datetime=Field(default_factory=datetime.utcnow)
    category_id:Optional[int]=Field(default=None,foreign_key="category.id")
    supplier_id:Optional[int]=Field(default=None,foreign_key="supplier.id")
    category_rel:Optional[Category]=Relationship(back_populates="products")
    supplier_rel:Optional[Supplier]=Relationship(back_populates="products")

class ProductCreate(SQLModel):
    name:str=Field(min_length=2,max_length=100)
    description:str=Field(min_length=10,max_length=500)
    brand:str
    category:str
    price:float
    stock:int=Field(default=0,ge=0)
    warranty_months:int=Field(default=0,ge=0)
    sku:str
    category_id:Optional[int]=None
    supplier_id:Optional[int]=None

    @field_validator("name")
    @classmethod
    def v_name(cls,v):
        if not v[0].isupper(): raise ValueError("Name must start with a capital letter")
        if not re.fullmatch(r"[A-Za-z0-9\s\-]+",v): raise ValueError("Invalid characters")
        return v
    @field_validator("brand")
    @classmethod
    def v_brand(cls,v):
        allowed={"HP":"HP","DELL":"Dell","LENOVO":"Lenovo","APPLE":"Apple","SAMSUNG":"Samsung","INTEL":"Intel","AMD":"AMD","CORSAIR":"Corsair","LOGITECH":"Logitech","OTHER":"Other"}
        k=v.strip().upper()
        if k not in allowed: raise ValueError("Invalid brand")
        return allowed[k]
    @field_validator("category")
    @classmethod
    def v_cat(cls,v):
        allowed=["Laptops","Monitors","Storage","Processors","Memory","Keyboards","Mice","Accessories"]
        for c in allowed:
            if c.lower()==v.lower(): return c
        raise ValueError("Invalid category")
    @field_validator("price")
    @classmethod
    def v_price(cls,v):
        if v!=round(v,2): raise ValueError("Max 2 decimal places")
        if v<100 or v>500000: raise ValueError("Price must be between 100 and 500000")
        return round(v,2)
    @field_validator("sku")
    @classmethod
    def v_sku(cls,v):
        if not re.fullmatch(r"^[A-Z]{3,4}-[A-Z]{2,4}-[0-9]{4}$",v): raise ValueError("Invalid SKU")
        return v
    @model_validator(mode="after")
    def v_warranty(self):
        if self.warranty_months>36: raise ValueError("Warranty max 36 months")
        if self.price>50000 and self.warranty_months<12: raise ValueError("Minimum 12-month warranty required")
        return self

class ProductUpdate(ProductCreate):
    name: Optional[str]=None
    description: Optional[str]=None
    brand: Optional[str]=None
    category: Optional[str]=None
    price: Optional[float]=None
    stock: Optional[int]=None
    warranty_months: Optional[int]=None
    sku: Optional[str]=None

class CategoryCreate(SQLModel):
    name:str
    description:Optional[str]=None

class SupplierCreate(SQLModel):
    name:str
    contact_person:str
    email:EmailStr
    phone:str
    is_active:bool=True

    @field_validator("phone")
    @classmethod
    def v_phone(cls,v):
        if not re.fullmatch(r"^\+?[0-9]{10,15}$",v):
            raise ValueError("Invalid phone number")
        return v
