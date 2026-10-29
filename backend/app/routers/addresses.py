from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas import AddressRequest, AddressResponse
from ..services.address_service import address_response, create_address, delete_address, list_addresses, update_address

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressResponse])
def get_addresses(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return [address_response(address) for address in list_addresses(db, user)]


@router.post("", response_model=AddressResponse, status_code=201)
def add_address(payload: AddressRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    address = create_address(db, user, payload)
    db.commit()
    return address_response(address)


@router.put("/{address_id}", response_model=AddressResponse)
def edit_address(address_id: int, payload: AddressRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    address = update_address(db, user, address_id, payload)
    db.commit()
    return address_response(address)


@router.delete("/{address_id}", status_code=204)
def remove_address(address_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    delete_address(db, user, address_id)
    db.commit()
    return Response(status_code=204)
