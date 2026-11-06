from fastapi import APIRouter

from .market_contracts import MarketOverviewContract
from .market_service import V2MarketService


def create_v2_market_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v2/markets",
        tags=["v2-markets"],
    )

    service = V2MarketService()

    @router.get(
        "/overview",
        response_model=MarketOverviewContract,
    )
    def market_overview() -> MarketOverviewContract:
        return service.overview()

    return router
