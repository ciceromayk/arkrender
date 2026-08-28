"""Contrato comum dos motores de render do ARKITEKT."""
from dataclasses import dataclass, field, asdict
from typing import Optional
import time


@dataclass
class RenderResult:
    engine: str
    config_id: str
    ok: bool
    image_path: Optional[str] = None
    control_map_path: Optional[str] = None
    seconds: float = 0.0
    cost_usd: Optional[float] = None
    params: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class Engine:
    """Um motor = uma rota de render. Todos recebem o mesmo screenshot e o mesmo
    prompt, para que a comparação seja honesta."""

    name = "base"

    def available(self) -> tuple[bool, str]:
        """(disponível?, motivo se não)"""
        raise NotImplementedError

    def render(self, image_path: str, prompt: str, negative: str,
               strength: float, control_weight: float,
               seed: int, config_id: str, out_dir: str) -> RenderResult:
        raise NotImplementedError

    # helper
    @staticmethod
    def timed():
        return time.time()
