from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID
from sqlmodel import Session, select
from fastapi import HTTPException

from ..models import OrderItem, OrderItemKDSStatus, KDSEventLog, User
from ..schemas import KDSSyncBatchPayload, KDSSyncResponse, KDSSyncResultItem

# Helper function for getting monotonic weight of the enum
def get_kds_status_weight(status: OrderItemKDSStatus) -> int:
    return status.value

class KDSService:
    @staticmethod
    def process_sync_batch(db: Session, payload: KDSSyncBatchPayload, user: User) -> KDSSyncResponse:
        """
        Process an offline-first batch of actions from a KDS client.
        Applies monotonic weight checks and logs each transition.
        """
        results: List[KDSSyncResultItem] = []
        server_now = datetime.now(timezone.utc)
        
        # We need a list of unique item IDs from the batch to lock and lookup efficiently
        item_ids = list(set([a.order_item_id for a in payload.actions]))
        
        # Load all requested items in one query
        items_db = db.exec(
            select(OrderItem).where(OrderItem.id.in_(item_ids))
        ).all()
        
        item_map = {item.id: item for item in items_db}
        
        for action in payload.actions:
            result = KDSSyncResultItem(
                client_uuid=action.client_uuid,
                success=False,
                server_timestamp=server_now
            )
            
            # Retrieve from map
            item = item_map.get(action.order_item_id)
            
            if not item:
                result.error_code = "ITEM_NOT_FOUND"
                results.append(result)
                continue
                
            current_weight = get_kds_status_weight(item.kds_status)
            new_weight = get_kds_status_weight(action.new_status)
            
            # --- Anti-Ghosting Check ---
            if item.kds_status == OrderItemKDSStatus.VOIDED:
                # Item is fully voided, reject any kitchen updates (e.g. they cooked it anyway but POS says voided)
                result.error_code = "ALREADY_VOIDED"
                result.applied_status = item.kds_status
                results.append(result)
                continue
                
            if item.kds_status == OrderItemKDSStatus.VOIDED_PENDING_ACK:
                # POS voided it while kitchen was working on it.
                # If the tablet is acknowledging the void, we let it through.
                if action.new_status == OrderItemKDSStatus.VOIDED:
                    # Valid transition
                    pass
                else:
                    # Any other action while pending ack is rejected to force the UI to show the red VOID ghost
                    result.error_code = "PENDING_VOID_ACK"
                    result.applied_status = item.kds_status
                    results.append(result)
                    continue

            # --- Monotonic Weight Check ---
            # If it's a normal forward progression
            if not action.is_undo:
                if new_weight <= current_weight:
                    # Stale update from a tablet that was offline and just came back online
                    # after another tablet already bumped the ticket further.
                    result.error_code = "STALE_UPDATE_IGNORED"
                    result.applied_status = item.kds_status
                    results.append(result)
                    continue
            else:
                # If it IS an undo action, the expected behaviour is to allow moving backwards,
                # BUT only if the current state exactly matches the state they are undoing FROM.
                # In this system, 'new_status' for an undo is the target fallback state.
                # Since an undo can be dangerous if another tablet already acted, we strictly validate.
                if new_weight >= current_weight:
                    result.error_code = "INVALID_UNDO_WEIGHT"
                    result.applied_status = item.kds_status
                    results.append(result)
                    continue

            # --- Apply state transition ---
            old_state_str = item.kds_status.name
            
            item.kds_status = action.new_status
            
            # Update critical timestamps based on new state
            if action.new_status == OrderItemKDSStatus.PREPARING and not item.sent_to_kitchen_at:
                item.sent_to_kitchen_at = action.client_timestamp
            elif action.new_status == OrderItemKDSStatus.READY:
                item.ready_at = action.client_timestamp
                
            # Bump document version
            item.document_version += 1
            
            # --- Audit Trail ---
            audit_event = KDSEventLog(
                order_item_id=item.id,
                action_type="BUMP_STATE" if not action.is_undo else "UNDO_STATE",
                actor_id=user.id,
                old_state=old_state_str,
                new_state=action.new_status.name,
                client_timestamp=action.client_timestamp,
                server_timestamp=server_now,
                is_undo=action.is_undo
            )
            db.add(audit_event)
            
            # Record success
            result.success = True
            result.applied_status = item.kds_status
            results.append(result)

        # Commit all successful changes in this batch transaction
        db.commit()
        
        # After commit, get the fresh state of all active items to send back to the tablet
        # so it can reconcile its local db.
        # Active items logic: things that are not Delivered and not fully Voided.
        active_items = db.exec(
            select(OrderItem).where(
                OrderItem.kds_status.notin_([OrderItemKDSStatus.DELIVERED, OrderItemKDSStatus.VOIDED])
            )
        ).all()
        
        # We need to map them to OrderItemResponse. Currently we just send them back, routers will handle schema conversion.
        # But wait, KDSSyncResponse expects OrderItemResponse. In a service we should ideally return the ORM items
        # and let the router map it.
        
        return {
            "results": results,
            "refreshed_items_orm": active_items,
            "server_time": server_now
        }

    @staticmethod
    def calculate_pacing(order_items: List[OrderItem]) -> dict:
        """
        Calculates pacing metadata for a list of order items (typically an entire order).
        Pacing is course-based. Within each course, the item with the longest
        prep_time_sec is the 'anchor'. All other items in that course should start
        later so that everything finishes at the same time.
        
        Returns a dictionary mapping item ID (string) to pacing metadata dict.
        """
        # Group items by course
        courses = {}
        for item in order_items:
            # Only pace items that are not delivered/voided
            if item.kds_status in (OrderItemKDSStatus.DELIVERED, OrderItemKDSStatus.VOIDED):
                continue
                
            c = item.course
            if c not in courses:
                courses[c] = []
            courses[c].append(item)
            
        pacing_metadata = {}
        
        for c_id, course_items in courses.items():
            if not course_items:
                continue
                
            # Find the maximum prep time in this course (the Anchor)
            # Default to 0 if prep_time_sec is missing somehow
            max_prep_time = max([getattr(item, 'prep_time_sec_snapshot', 0) or 0 for item in course_items])
            
            # The target ready time for this course is purely relative for the KDS UI.
            # We calculate delay_sec for each item: how long they should wait after 
            # the anchor starts before THEY start.
            for item in course_items:
                my_prep = getattr(item, 'prep_time_sec_snapshot', 0) or 0
                delay_sec = max_prep_time - my_prep
                
                is_anchor = (my_prep == max_prep_time) and (my_prep > 0)
                
                pacing_metadata[str(item.id)] = {
                    "is_anchor": is_anchor,
                    "prep_time_sec": my_prep,
                    "target_course_prep_time_sec": max_prep_time,
                    "delay_start_sec": delay_sec
                }
                
        return pacing_metadata

