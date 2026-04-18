"""API Routes for Tudor Printing House"""

import uuid
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from lulu_client import LuluAPI
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["orders"])

# Storage
UPLOAD_DIR = Path(__file__).parent.parent / "DATA" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory orders (replace with DB)
orders = {}

# Lulu client
lulu = LuluAPI(
    client_key=os.getenv("LULU_CLIENT_KEY"),
    client_secret=os.getenv("LULU_CLIENT_SECRET"),
    sandbox=os.getenv("LULU_SANDBOX", "false").lower() == "true"
)


@router.post("/orders")
async def create_order(
    title: str,
    author: str,
    cover: UploadFile,
    interior: UploadFile,
    quantity: int,
    product_id: str,
    shipping_name: str,
    shipping_street: str,
    shipping_city: str,
    shipping_state: str,
    shipping_postcode: str,
    shipping_country: str,
    background_tasks: BackgroundTasks
):
    """Create print order"""
    try:
        order_id = str(uuid.uuid4())[:8]

        # Save files
        cover_path = UPLOAD_DIR / f"{order_id}_cover.pdf"
        interior_path = UPLOAD_DIR / f"{order_id}_interior.pdf"

        with open(cover_path, "wb") as f:
            f.write(await cover.read())

        with open(interior_path, "wb") as f:
            f.write(await interior.read())

        logger.info(f"Order {order_id}: Files saved")

        # Upload to Lulu
        cover_file_id = lulu.upload_file(str(cover_path))
        interior_file_id = lulu.upload_file(str(interior_path))

        # Create job
        job_data = {
            "line_items": [{
                "cover_file_id": cover_file_id,
                "interior_file_id": interior_file_id,
                "quantity": quantity,
                "product_id": product_id
            }],
            "shipping_address": {
                "name": shipping_name,
                "street1": shipping_street,
                "city": shipping_city,
                "state": shipping_state,
                "postcode": shipping_postcode,
                "country_code": shipping_country
            }
        }

        job = lulu.create_print_job(job_data)

        # Store order
        orders[order_id] = {
            "order_id": order_id,
            "title": title,
            "author": author,
            "lulu_job_id": job.get("id"),
            "status": job.get("status"),
            "total_cost": job.get("total_cost_exc_tax"),
            "created_at": datetime.now().isoformat(),
            "shipping_address": {
                "name": shipping_name,
                "city": shipping_city,
                "country": shipping_country
            }
        }

        logger.info(f"Order {order_id}: Created (Lulu: {job.get('id')})")

        return {
            "order_id": order_id,
            "lulu_job_id": job.get("id"),
            "status": job.get("status"),
            "total_cost": job.get("total_cost_exc_tax"),
            "message": "Order created"
        }

    except Exception as e:
        logger.error(f"Order failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details"""
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")

    order = orders[order_id]

    try:
        lulu_job = lulu.get_job_status(order["lulu_job_id"])
        order["status"] = lulu_job.get("status")
        order["tracking_url"] = lulu_job.get("tracking_url")
    except Exception as e:
        logger.error(f"Status fetch failed: {str(e)}")

    return order


@router.get("/orders")
async def list_orders(limit: int = 20, offset: int = 0):
    """List all orders"""
    order_list = list(orders.values())
    return {
        "count": len(order_list),
        "limit": limit,
        "offset": offset,
        "results": order_list[offset:offset+limit]
    }


@router.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "lulu_api": "connected",
        "timestamp": datetime.now().isoformat()
    }
