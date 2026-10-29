from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Region, Store
from ..schemas import LocationResponse, RegionResponse, StoreResponse

router = APIRouter(prefix="/api", tags=["location"])


def store_response(store: Store) -> StoreResponse:
    return StoreResponse.model_validate(store, from_attributes=True)


@router.get("/regions", response_model=list[RegionResponse])
def list_regions(db: Session = Depends(get_db)):
    return db.query(Region).order_by(Region.name).all()


@router.get("/regions/zip/{zip_code}", response_model=LocationResponse)
def region_for_zip(zip_code: str, db: Session = Depends(get_db)):
    normalized_zip = zip_code.strip()
    if not normalized_zip.isdigit() or len(normalized_zip) != 5:
        raise HTTPException(status_code=400, detail="ZIP code must contain five digits")
    region = db.query(Region).filter(Region.zip_start <= normalized_zip, Region.zip_end >= normalized_zip).first()
    if not region:
        raise HTTPException(status_code=404, detail="We couldn't find a store for this ZIP code")
    store = db.query(Store).filter(Store.region_id == region.id, Store.is_active == 1).order_by(Store.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="No active store is available for this region")
    return LocationResponse(
        zip_code=normalized_zip,
        region=RegionResponse.model_validate(region, from_attributes=True),
        store=store_response(store),
    )


@router.get("/stores", response_model=list[StoreResponse])
def list_stores(region_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Store).filter(Store.is_active == 1)
    if region_id is not None:
        query = query.filter(Store.region_id == region_id)
    return query.order_by(Store.name).all()


@router.get("/stores/{store_id}", response_model=StoreResponse)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == 1).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store