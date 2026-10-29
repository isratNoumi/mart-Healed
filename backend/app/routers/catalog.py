from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Brand, Category, Inventory, Product, ProductVariant, RegionalPrice, Store
from ..schemas import (
    AvailabilityResponse,
    BrandResponse,
    CategoryResponse,
    PriceResponse,
    ProductListResponse,
    ProductResponse,
    VariantResponse,
)

router = APIRouter(prefix="/api", tags=["catalog"])


def category_response(category: Category) -> CategoryResponse:
    return CategoryResponse.model_validate(category, from_attributes=True)


def brand_response(brand: Brand) -> BrandResponse:
    return BrandResponse.model_validate(brand, from_attributes=True)


def build_product_response(
    db: Session,
    product: Product,
    region_id: int | None = None,
    store_id: int | None = None,
) -> ProductResponse:
    brand = db.get(Brand, product.brand_id)
    category = db.get(Category, product.category_id)
    variants = db.query(ProductVariant).filter(ProductVariant.product_id == product.id).all()
    price = None
    if region_id is not None:
        regional_price = db.query(RegionalPrice).filter_by(
            product_id=product.id, region_id=region_id
        ).first()
        if regional_price:
            price = PriceResponse(
                price=regional_price.price,
                sale_price=regional_price.sale_price,
                current_price=regional_price.sale_price or regional_price.price,
                currency=regional_price.currency,
                region_id=region_id,
            )

    availability = None
    if store_id is not None:
        inventory = db.query(Inventory).filter_by(product_id=product.id, store_id=store_id).first()
        store = db.get(Store, store_id)
        if inventory and store and store.is_active == 1:
            available = max(inventory.quantity - inventory.reserved_quantity, 0)
            availability = AvailabilityResponse(
                store_id=store.id,
                store_name=store.name,
                available_quantity=available,
                in_stock=available > 0,
                status="In Stock" if available > 10 else f"Only {available} left" if available else "Out of Stock",
            )

    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        slug=product.slug,
        description=product.description,
        short_description=product.short_description,
        model_number=product.model_number,
        rating=product.rating,
        review_count=product.review_count,
        image_url=product.image_url,
        brand=brand_response(brand),
        category=category_response(category),
        price=price,
        availability=availability,
        variants=[VariantResponse.model_validate(variant, from_attributes=True) for variant in variants],
    )


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/categories/{slug}", response_model=CategoryResponse)
def get_category(slug: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/brands", response_model=list[BrandResponse])
def list_brands(db: Session = Depends(get_db)):
    return db.query(Brand).order_by(Brand.name).all()


@router.get("/products", response_model=ProductListResponse)
def list_products(
    category: str | None = None,
    brand: str | None = None,
    search: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool = False,
    region_id: int | None = None,
    store_id: int | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    sort: str = "relevance",
    db: Session = Depends(get_db),
):
    query = db.query(Product).join(Brand).join(Category).filter(Product.is_active == 1)
    if category:
        query = query.filter(or_(Category.slug == category, Category.name.ilike(f"%{category}%")))
    if brand:
        query = query.filter(or_(Brand.slug == brand, Brand.name.ilike(f"%{brand}%")))
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(term), Product.sku.ilike(term), Product.description.ilike(term), Brand.name.ilike(term), Category.name.ilike(term)))
    needs_price_join = region_id is not None and (
        min_price is not None or max_price is not None or sort == "price"
    )
    if needs_price_join:
        query = query.join(RegionalPrice, RegionalPrice.product_id == Product.id).filter(RegionalPrice.region_id == region_id)
    if region_id is not None and (min_price is not None or max_price is not None):
        current_price = func.coalesce(RegionalPrice.sale_price, RegionalPrice.price)
        if min_price is not None:
            query = query.filter(current_price >= min_price)
        if max_price is not None:
            query = query.filter(current_price <= max_price)
    if in_stock and store_id is not None:
        query = query.join(Inventory, Inventory.product_id == Product.id).filter(
            Inventory.store_id == store_id,
            Inventory.quantity > Inventory.reserved_quantity,
        )
    if sort == "price" and region_id is not None:
        query = query.order_by(func.coalesce(RegionalPrice.sale_price, RegionalPrice.price))
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.created_at.desc(), Product.id)

    total = query.count()
    products = query.offset((page - 1) * limit).limit(limit).all()
    return ProductListResponse(
        items=[build_product_response(db, product, region_id, store_id) for product in products],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, region_id: int | None = None, store_id: int | None = None, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == 1).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return build_product_response(db, product, region_id, store_id)


@router.get("/products/{product_id}/availability", response_model=list[AvailabilityResponse])
def get_product_availability(product_id: int, db: Session = Depends(get_db)):
    if not db.query(Product).filter(Product.id == product_id, Product.is_active == 1).first():
        raise HTTPException(status_code=404, detail="Product not found")
    rows = db.query(Inventory, Store).join(Store, Store.id == Inventory.store_id).filter(Inventory.product_id == product_id, Store.is_active == 1).all()
    return [
        AvailabilityResponse(
            store_id=store.id,
            store_name=store.name,
            available_quantity=max(inventory.quantity - inventory.reserved_quantity, 0),
            in_stock=inventory.quantity > inventory.reserved_quantity,
            status="In Stock" if inventory.quantity - inventory.reserved_quantity > 10 else f"Only {max(inventory.quantity - inventory.reserved_quantity, 0)} left" if inventory.quantity > inventory.reserved_quantity else "Out of Stock",
        )
        for inventory, store in rows
    ]