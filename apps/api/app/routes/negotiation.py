"""B2A negotiation HTTP routes, including proposal acceptance."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.negotiation import (
    BuyerTurnRequest,
    CreateNegotiationRequest,
    NegotiationResponse,
    SimulateBuyerRequest,
)
from app.schemas.transaction import AcceptProposalRequest, AcceptProposalResponse
from app.services.negotiation import NegotiationError, NegotiationService
from app.services.transaction import TransactionError, TransactionService

router = APIRouter(prefix="/negotiations", tags=["negotiation"])


def _service(db: AsyncSession = Depends(get_db)) -> NegotiationService:
    return NegotiationService(db)


@router.post("", response_model=NegotiationResponse)
async def create_session(
    payload: CreateNegotiationRequest,
    service: NegotiationService = Depends(_service),
) -> NegotiationResponse:
    return await service.create(payload)


@router.get("/{session_id}", response_model=NegotiationResponse)
async def get_session(
    session_id: uuid.UUID,
    service: NegotiationService = Depends(_service),
) -> NegotiationResponse:
    detail = await service.get(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return detail


@router.post("/{session_id}/turns", response_model=NegotiationResponse)
async def post_turn(
    session_id: uuid.UUID,
    payload: BuyerTurnRequest,
    service: NegotiationService = Depends(_service),
) -> NegotiationResponse:
    try:
        return await service.turn(session_id, payload)
    except NegotiationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{session_id}/simulate-buyer", response_model=NegotiationResponse)
async def simulate_buyer_turn(
    session_id: uuid.UUID,
    payload: SimulateBuyerRequest,
    service: NegotiationService = Depends(_service),
) -> NegotiationResponse:
    try:
        return await service.simulate(session_id, payload)
    except NegotiationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _transactions(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


@router.post("/{session_id}/accept", response_model=AcceptProposalResponse)
async def accept_proposal(
    session_id: uuid.UUID,
    payload: AcceptProposalRequest,
    service: TransactionService = Depends(_transactions),
) -> AcceptProposalResponse:
    try:
        return await service.accept(session_id, payload)
    except TransactionError as exc:
        status = 404 if exc.code.value.endswith("NOT_FOUND") else 409
        raise HTTPException(status_code=status, detail=exc.code.value) from exc
