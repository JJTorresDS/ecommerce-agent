from fastapi import APIRouter, File, HTTPException, UploadFile

from ecommerce_agent.ingest.products import parse_products_csv, upsert_products_batch

router = APIRouter()


@router.post("/products/upload")
async def upload_products(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8") from None

    try:
        products = parse_products_csv(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upsert_products_batch(products)
    return {"upserted": len(products)}
