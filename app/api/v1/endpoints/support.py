from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from ...models.user import User
from ...models.support import SupportTicket, TicketMessage, TicketStatus
from ...services.support import support_service
from ...core.security import get_current_user, get_current_staff_user

router = APIRouter()

class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: str = "medium"

class TicketMessageCreate(BaseModel):
    message: str

class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    assigned_to_id: Optional[int] = None

class AnalyticsRequest(BaseModel):
    start_date: datetime
    end_date: datetime

@router.post("/tickets", response_model=SupportTicket)
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: User = Depends(get_current_user)
):
    return await support_service.create_ticket(
        user=current_user,
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority
    )

@router.get("/tickets", response_model=List[SupportTicket])
async def get_tickets(
    status: Optional[TicketStatus] = None,
    current_user: User = Depends(get_current_user)
):
    return await support_service.get_user_tickets(current_user, status)

@router.get("/tickets/{ticket_id}", response_model=SupportTicket)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user)
):
    ticket = await SupportTicket.get_or_none(id=ticket_id)
    if not ticket or (not current_user.is_staff and ticket.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessage)
async def add_ticket_message(
    ticket_id: int,
    message_data: TicketMessageCreate,
    current_user: User = Depends(get_current_user)
):
    ticket = await SupportTicket.get_or_none(id=ticket_id)
    if not ticket or (not current_user.is_staff and ticket.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return await support_service.add_ticket_message(
        ticket=ticket,
        user=current_user,
        message=message_data.message
    )

@router.get("/tickets/{ticket_id}/messages", response_model=List[TicketMessage])
async def get_ticket_messages(
    ticket_id: int,
    current_user: User = Depends(get_current_user)
):
    ticket = await SupportTicket.get_or_none(id=ticket_id)
    if not ticket or (not current_user.is_staff and ticket.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return await support_service.get_ticket_messages(ticket)

@router.patch("/tickets/{ticket_id}", response_model=SupportTicket)
async def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    current_user: User = Depends(get_current_staff_user)
):
    ticket = await SupportTicket.get_or_none(id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return await support_service.update_ticket_status(
        ticket=ticket,
        status=ticket_data.status,
        assigned_to=current_user if ticket_data.assigned_to_id else None
    )

@router.get("/faq/categories")
async def get_faq_categories():
    return await support_service.get_faq_categories()

@router.get("/faq/items")
async def get_faq_items(category_id: Optional[int] = None):
    return await support_service.get_faq_items(category_id)

@router.get("/analytics/user")
async def get_user_analytics(
    request: AnalyticsRequest,
    current_user: User = Depends(get_current_user)
):
    return await support_service.get_user_analytics(
        user=current_user,
        start_date=request.start_date,
        end_date=request.end_date
    )

@router.get("/analytics/support")
async def get_support_metrics(
    request: AnalyticsRequest,
    current_user: User = Depends(get_current_staff_user)
):
    return await support_service.get_support_metrics(
        start_date=request.start_date,
        end_date=request.end_date
    )

@router.post("/reports/financial")
async def generate_financial_report(
    request: AnalyticsRequest,
    current_user: User = Depends(get_current_staff_user)
):
    return await support_service.generate_financial_report(
        report_type="monthly",
        start_date=request.start_date,
        end_date=request.end_date
    ) 