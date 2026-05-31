"""
RL Engine — Reinforcement Learning Layer (Phase 7).

Stub for future implementation.
Will contain:
  - BerthingRLAgent: PPO/DQN agent for dynamic weight tuning
  - State: berth occupancy + queue + resource availability
  - Action: weight adjustments for optimizer objective
  - Reward: revenue - penalties
  - Training: offline via Digital Twin simulation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.config.settings import settings


@dataclass
class RLState:
    """Environment state for the RL agent."""
    berth_occupancy: List[float] = field(default_factory=list)
    queue_length: int = 0
    resource_availability: List[float] = field(default_factory=list)
    time_of_day: float = 0.0
    day_of_week: int = 0
    congestion_level: float = 0.0

    def to_array(self) -> np.ndarray:
        return np.array(
            self.berth_occupancy +
            [self.queue_length] +
            self.resource_availability +
            [self.time_of_day, self.day_of_week, self.congestion_level]
        )


@dataclass
class RLAction:
    """Action: weight adjustments for the optimizer."""
    weight_adjustments: Dict[str, float] = field(default_factory=dict)


class BerthingRLAgent:
    """
    Reinforcement learning agent for dynamic weight tuning.

    This is a stub — full implementation requires Phase 8 (Digital Twin)
    for training environment.
    """

    def __init__(self, state_dim: int = 20, action_dim: int = 6):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.trained = False
        # Default weights (no RL yet — use static defaults)
        self.default_weights = {
            "w_waiting": 1.0,
            "w_idle": 0.3,
            "w_sla_penalty": 2.0,
            "w_contract_bonus": 0.5,
            "w_throughput": 0.5,
        }

    def select_action(self, state: RLState) -> RLAction:
        """Select weight adjustments given current state."""
        if not self.trained:
            # Return default weights (no RL adjustment)
            return RLAction(weight_adjustments=dict(self.default_weights))

        # Future: policy_net forward pass
        return RLAction(weight_adjustments=dict(self.default_weights))

    def compute_reward(
        self,
        delay_minutes: float,
        idle_minutes: float,
        capacity_mismatch: float,
    ) -> float:
        """Compute reward signal."""
        # FIX (Phase 5): RL is experimental, but reward direction now penalizes delay, idle time, and mismatch.
        return -(
            settings.RL_DELAY_WEIGHT * max(delay_minutes, 0)
            + settings.RL_IDLE_WEIGHT * max(idle_minutes, 0)
            + settings.RL_MISMATCH_WEIGHT * max(capacity_mismatch, 0)
        )

    def train_offline(self, trajectories: list):
        """Train on historical trajectories (Phase 7+8)."""
        raise NotImplementedError("RL training requires Digital Twin (Phase 8)")
