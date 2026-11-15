from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Category:
    id: str
    name: str


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    category_id: str
    price_kopeks: int
    description: str
    meme: str
    emoji: str
    featured: bool


@dataclass(frozen=True)
class CartLine:
    product_id: str
    product_name: str
    unit_price_kopeks: int
    quantity: int
    line_total_kopeks: int


@dataclass(frozen=True)
class ValidatedCart:
    lines: tuple[CartLine, ...]
    item_count: int
    total_kopeks: int


@dataclass(frozen=True)
class TrackingStage:
    id: str
    title: str
    description: str
    start_after_seconds: int
    emoji: str


@dataclass(frozen=True)
class TrackingState:
    current_stage_index: int
    current_stage: TrackingStage
    stages: tuple[TrackingStage, ...]
    elapsed_seconds: int
    next_stage_at: datetime | None
    is_final: bool
