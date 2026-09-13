"""Public machine interface for external Buyer Agents."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.errors import AgentProtocolError
from app.agent.gateway import AgentGatewayService
from app.agent.schemas import (
    AgentAcceptRequest,
    AgentActivityResponse,
    AgentCapabilities,
    AgentCounterRequest,
    AgentOfferRequest,
    AgentOfferResponse,
    AgentTransactionResponse,
)
from app.db.dependencies import get_db

router = APIRouter(prefix="/agent", tags=["agent"])


def _gateway(db: AsyncSession = Depends(get_db)) -> AgentGatewayService:
    return AgentGatewayService(db)


def _raise(exc: AgentProtocolError) -> None:
    raise HTTPException(status_code=exc.http_status, detail=exc.as_dict()) from exc


@router.get("/capabilities", response_model=AgentCapabilities)
async def capabilities(
    gateway: AgentGatewayService = Depends(_gateway),
) -> AgentCapabilities:
    return gateway.capabilities()


@router.get("/activity", response_model=AgentActivityResponse)
async def list_activity(
    limit: int = 20,
    gateway: AgentGatewayService = Depends(_gateway),
) -> AgentActivityResponse:
    """Read-only recent negotiation activity for merchant operator views."""
    return await gateway.list_activity(limit=limit)


@router.post("/offers/request", response_model=AgentOfferResponse)
async def request_offer(
    payload: AgentOfferRequest,
    gateway: AgentGatewayService = Depends(_gateway),
) -> AgentOfferResponse:
    try:
        return await gateway.request_offer(payload)
    except AgentProtocolError as exc:
        _raise(exc)
        raise


@router.get("/offers/{proposal_id}", response_model=AgentOfferResponse)
async def inspect_offer(
    proposal_id: UUID,
    gateway: AgentGatewayService = Depends(_gateway),
) -> AgentOfferResponse:
    try:
        return await gateway.inspect_offer(proposal_id)
    except AgentProtocolError as exc:
        _raise(exc)
        raise


@router.post("/offers/counter", response_model=AgentOfferResponse)
async def counter_offer(
    payload: AgentCounterRequest,
    gateway: AgentGatewayService = Depends(_gateway),
) -> AgentOfferResponse:
    try:
        return await gateway.counter_offer(payload)
    except AgentProtocolError as exc:
        _raise(exc)
        raise


@router.post("/offers/accept", response_model=AgentTransactionResponse)
async def accept_offer(
    payload: AgentAcceptRequest,
    gateway: AgentGatewayService = Depends(_gateway),
) -> AgentTransactionResponse:
    try:
        return await gateway.accept_offer(payload)
    except AgentProtocolError as exc:
        _raise(exc)
        raise


@router.get("/orders/{ref}")
async def get_order(
    ref: str,
    gateway: AgentGatewayService = Depends(_gateway),
) -> dict[str, Any]:
    try:
        return await gateway.get_order(ref)
    except AgentProtocolError as exc:
        _raise(exc)
        raise


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: UUID,
    gateway: AgentGatewayService = Depends(_gateway),
) -> dict[str, Any]:
    try:
        return await gateway.get_transaction(transaction_id)
    except AgentProtocolError as exc:
        _raise(exc)
        raise
