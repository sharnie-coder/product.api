from datetime import datetime
from typing import List, Optional
import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database.session import create_db_and_tables, get_session
from models.product import (
    Category, CategoryCreate,
    Supplier, SupplierCreate,
    Product, ProductCreate, ProductUpdate,
)

app = FastAPI(title="Product Catalog API", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def startup():
    create_db_and_tables()

def error_response(status_code:int,message:str,path:str,errors=None):
    body={
        "success":False,
        "status_code":status_code,
        "message":message,
        "timestamp":datetime.utcnow().isoformat(),
        "path":path
    }
    if errors is not None:
        body["errors"]=errors
    return JSONResponse(status_code=status_code,content=body)

@app.exception_handler(HTTPException)
async def http_handler(request:Request,exc:HTTPException):
    logger.warning(exc.detail)
    return error_response(exc.status_code,exc.detail,request.url.path)

@app.exception_handler(RequestValidationError)
async def validation_handler(request:Request,exc:RequestValidationError):
    errs=[{
        "field":".".join(map(str,e["loc"])),
        "message":e["msg"],
        "type":e["type"]
    } for e in exc.errors()]
    return error_response(422,"Validation error",request.url.path,errs)

@app.exception_handler(IntegrityError)
async def integrity_handler(request:Request,exc:IntegrityError):
    logger.error(str(exc))
    return error_response(409,"Duplicate SKU or database constraint violation",request.url.path)

@app.exception_handler(Exception)
async def general_handler(request:Request,exc:Exception):
    logger.exception(exc)
    return error_response(500,"Internal server error",request.url.path)

# Category CRUD
@app.post("/categories",response_model=Category,status_code=201)
def create_category(category:CategoryCreate,session:Session=Depends(get_session)):
    if session.exec(select(Category).where(Category.name==category.name)).first():
        raise HTTPException(400,"Category already exists")
    db=Category(**category.model_dump())
    session.add(db);session.commit();session.refresh(db)
    return db

@app.get("/categories",response_model=List[Category])
def list_categories(session:Session=Depends(get_session)):
    return session.exec(select(Category)).all()

# Supplier CRUD
@app.post("/suppliers",response_model=Supplier,status_code=201)
def create_supplier(supplier:SupplierCreate,session:Session=Depends(get_session)):
    db=Supplier(**supplier.model_dump())
    session.add(db);session.commit();session.refresh(db)
    return db

@app.get("/suppliers",response_model=List[Supplier])
def list_suppliers(session:Session=Depends(get_session)):
    return session.exec(select(Supplier)).all()

# Product CRUD
#list products
@app.get("/products",response_model=List[Product])
def list_products(session:Session=Depends(get_session)):
    return session.exec(select(Product)).all()


#create product
@app.post("/products",response_model=Product,status_code=201)
def create_product(product:ProductCreate,session:Session=Depends(get_session)):
    db=Product(**product.model_dump())
    session.add(db);session.commit();session.refresh(db)
    return db



#search products
@app.get("/products/search",response_model=List[Product])
def search_products(q:str,session:Session=Depends(get_session)):
    return session.exec(select(Product).where((Product.name.contains(q))|(Product.description.contains(q)))).all()


@app.patch("/products/bulk-update")
def bulk_update(category:str,discount_percent:float,session:Session=Depends(get_session)):
    if not 0<discount_percent<=100:
        raise HTTPException(400,"Discount must be between 0 and 100")
    products=session.exec(select(Product).where(Product.category==category)).all()
    updated=0
    for p in products:
        new_price=round(p.price*(1-discount_percent/100),2)
        if new_price<100:
            continue
        p.price=new_price
        updated+=1
    session.commit()
    logger.info(f"Updated {updated} products")
    return {"updated_products":updated}

# Stock adjustment
from pydantic import BaseModel
class StockAdjustment(BaseModel):
    product_id:int
    quantity_to_add:int

#adjust stock
@app.patch("/products/adjust-stock")
def adjust_stock(adjustments:list[StockAdjustment],session:Session=Depends(get_session)):
    success=[];failed=[]
    for a in adjustments:
        p=session.get(Product,a.product_id)
        if not p:
            failed.append({"product_id":a.product_id,"reason":"Not found"});continue
        if p.stock+a.quantity_to_add>5000:
            failed.append({"product_id":a.product_id,"reason":"Exceeds max stock"});continue
        p.stock+=a.quantity_to_add
        success.append(a.product_id)
    session.commit()
    return {"successful_updates":success,"failed_updates":failed}

#delete products
@app.delete("/products/{product_id}",status_code=204)
def delete_product(product_id:int,session:Session=Depends(get_session)):
    p=session.get(Product,product_id)
    if not p: raise HTTPException(404,"Product not found")
    session.delete(p);session.commit()
#get product by id
@app.get("/products/{product_id}",response_model=Product)
def get_product(product_id:int,session:Session=Depends(get_session)):
    p=session.get(Product,product_id)
    if not p: raise HTTPException(404,"Product not found")
    return p

#update product by id
@app.patch("/products/{product_id}",response_model=Product)
def update_product(product_id:int,data:ProductUpdate,session:Session=Depends(get_session)):
    p=session.get(Product,product_id)
    if not p: raise HTTPException(404,"Product not found")
    for k,v in data.model_dump(exclude_unset=True).items():
        setattr(p,k,v)
    p.updated_at=datetime.utcnow()
    session.add(p);session.commit();session.refresh(p)
    return p