import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Furniture

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Furniture Management API"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
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

# Furniture API models
class FurnitureIn(BaseModel):
    name: str
    category: str
    material: Optional[str] = None
    price: float
    stock: int = 0
    width_cm: Optional[float] = None
    depth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    image_url: Optional[str] = None

class FurnitureOut(FurnitureIn):
    id: str

# CRUD endpoints for furniture
@app.post("/api/furniture", response_model=dict)
async def create_furniture(item: FurnitureIn):
    try:
        furniture = Furniture(**item.model_dump())
        inserted_id = create_document("furniture", furniture)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/furniture", response_model=List[FurnitureOut])
async def list_furniture(category: Optional[str] = None, q: Optional[str] = None):
    try:
        filter_q = {}
        if category:
            filter_q["category"] = category
        # Simple name search
        if q:
            filter_q["name"] = {"$regex": q, "$options": "i"}
        docs = get_documents("furniture", filter_q)
        results = []
        for d in docs:
            results.append(FurnitureOut(
                id=str(d.get("_id")),
                name=d.get("name"),
                category=d.get("category"),
                material=d.get("material"),
                price=d.get("price"),
                stock=d.get("stock", 0),
                width_cm=d.get("width_cm"),
                depth_cm=d.get("depth_cm"),
                height_cm=d.get("height_cm"),
                image_url=d.get("image_url"),
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/furniture/{item_id}", response_model=FurnitureOut)
async def get_furniture(item_id: str):
    try:
        docs = get_documents("furniture", {"_id": ObjectId(item_id)}, limit=1)
        if not docs:
            raise HTTPException(status_code=404, detail="Item not found")
        d = docs[0]
        return FurnitureOut(
            id=str(d.get("_id")),
            name=d.get("name"),
            category=d.get("category"),
            material=d.get("material"),
            price=d.get("price"),
            stock=d.get("stock", 0),
            width_cm=d.get("width_cm"),
            depth_cm=d.get("depth_cm"),
            height_cm=d.get("height_cm"),
            image_url=d.get("image_url"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/furniture/{item_id}")
async def update_furniture(item_id: str, item: FurnitureIn):
    try:
        if db is None:
            raise Exception("Database not available")
        update_data = item.model_dump()
        update_data["updated_at"] = __import__("datetime").datetime.utcnow()
        result = db["furniture"].find_one_and_update(
            {"_id": ObjectId(item_id)},
            {"$set": update_data},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/furniture/{item_id}")
async def delete_furniture(item_id: str):
    try:
        if db is None:
            raise Exception("Database not available")
        result = db["furniture"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
