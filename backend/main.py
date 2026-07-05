"""
Astrology Web App — FastAPI Backend
Classical/Medieval astrology calculation engine.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.ephemeris import init_ephemeris, close_ephemeris
from api.routes import health, natal, returns, progressions, solar_arc, transits, transit_timing, ingresses, profections_route, decennials_route, circumambulations_route, synastry_route, composite_route, horary_route, horary_perfection_route, horary_dignities_route, horary_turned_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_ephemeris()
    yield
    # Shutdown
    close_ephemeris()


app = FastAPI(
    title="Astrology Web App",
    description="Classical/Medieval astrology calculation engine (Zoller/Bonatti tradition)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["system"])
app.include_router(natal.router, tags=["chart"])
app.include_router(returns.router, tags=["returns"])
app.include_router(progressions.router, tags=["progressions"])
app.include_router(solar_arc.router, tags=["progressions"])
app.include_router(transits.router, tags=["transits"])
app.include_router(transit_timing.router, tags=["transits"])
app.include_router(ingresses.router, tags=["transits"])
app.include_router(profections_route.router, tags=["chart"])
app.include_router(decennials_route.router, tags=["chart"])
app.include_router(circumambulations_route.router, tags=["chart"])
app.include_router(synastry_route.router, tags=["synastry"])
app.include_router(composite_route.router, tags=["synastry"])
app.include_router(horary_route.router, tags=["horary"])
app.include_router(horary_perfection_route.router, tags=["horary"])
app.include_router(horary_dignities_route.router, tags=["horary"])
app.include_router(horary_turned_route.router, tags=["horary"])
