from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from sqlalchemy.orm import Session

from models.models import AuditLog, InventoryItem

logger = logging.getLogger(__name__)


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def find_item(self, query: str) -> Optional[InventoryItem]:
        """Find by sku or name (case-insensitive)."""
        q = query.strip().lower()
        return (
            self.db.query(InventoryItem)
            .filter(
                (InventoryItem.sku == q) | (InventoryItem.name.ilike(q))
            )
            .first()
        )

    def get_item(self, sku: str) -> Optional[InventoryItem]:
        return self.db.query(InventoryItem).filter(InventoryItem.sku == sku).first()

    def get_all_items(self) -> List[Dict[str, Any]]:
        items = self.db.query(InventoryItem).order_by(InventoryItem.sku).all()
        return [
            {
                "id": i.id,
                "sku": i.sku,
                "name": i.name,
                "quantity": i.quantity,
                "price": i.price,
                "description": i.description,
            }
            for i in items
        ]

    def update_stock(
        self,
        query: str,
        quantity: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        item = self.find_item(query)
        if not item:
            return {"status": "error", "message": f"Item '{query}' not found"}

        old_qty = item.quantity
        item.quantity = quantity
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)

        self._audit(user_id, "update_stock", item.id, {"sku": item.sku, "old": old_qty, "new": quantity})
        logger.info("update_stock: %s %d → %d", item.sku, old_qty, quantity)

        return {
            "status": "success",
            "sku": item.sku,
            "name": item.name,
            "old_quantity": old_qty,
            "quantity": item.quantity,
        }

    def upsert_item(
        self,
        sku: str,
        name: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        item = self.get_item(sku)
        if item:
            if quantity is not None:
                item.quantity = quantity
            if price is not None:
                item.price = price
            if name is not None:
                item.name = name
            item.updated_at = datetime.utcnow()
            self.db.commit()
            self._audit(user_id, "update_inventory", item.id, {"sku": sku})
            return {"status": "updated", "id": item.id}

        item = InventoryItem(
            sku=sku,
            name=name or sku,
            quantity=quantity or 0,
            price=price,
            description=description,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        self._audit(user_id, "create_inventory", item.id, {"sku": sku})
        return {"status": "created", "id": item.id}

    def _audit(
        self,
        user_id: Optional[int],
        action: str,
        resource_id: Optional[int],
        details: Optional[Dict] = None,
    ) -> None:
        try:
            self.db.add(AuditLog(
                user_id=user_id,
                action=action,
                resource_type="inventory",
                resource_id=resource_id,
                details=details or {},
            ))
            self.db.commit()
        except Exception as e:
            logger.warning("audit write failed: %s", e)
            self.db.rollback()
