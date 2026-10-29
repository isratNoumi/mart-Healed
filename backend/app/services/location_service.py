from sqlalchemy.orm import Session

from ..models import Region, Store
from .errors import ServiceError


def resolve_store_context(
    db: Session,
    region_id: int | None,
    store_id: int | None,
    zip_code: str | None = None,
) -> tuple[int, int]:
    if zip_code and (region_id is None or store_id is None):
        store = db.query(Store).filter(Store.zip_code == zip_code.strip(), Store.is_active == 1).first()
        if store:
            region_id = region_id or store.region_id
            store_id = store_id or store.id
    region_id = region_id or 1
    store_id = store_id or 1
    store = db.query(Store).filter(Store.id == store_id, Store.region_id == region_id, Store.is_active == 1).first()
    if not store:
        raise ServiceError(400, "STORE_REGION_MISMATCH", "Selected store does not belong to the selected region")
    return region_id, store_id


def get_active_store(db: Session, store_id: int) -> Store:
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == 1).first()
    if store is None:
        raise ServiceError(404, "STORE_NOT_FOUND", "We couldn't find that store.")
    return store


def get_region(db: Session, region_id: int) -> Region:
    return db.get(Region, region_id)


def zip_in_region(zip_code: str, region: Region) -> bool:
    zip5 = zip_code[:5]
    return region.zip_start <= zip5 <= region.zip_end
