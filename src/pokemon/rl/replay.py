"""Numpy ring buffer. Stores each next state's padded option set + mask so the
DQN target can max over options offered at s'."""

from __future__ import annotations

import numpy as np


class ReplayBuffer:
    def __init__(self, capacity: int, state_dim: int, option_dim: int, k_max: int) -> None:
        self.capacity = capacity
        self.k_max = k_max
        self.state = np.zeros((capacity, state_dim), np.float32)
        self.option = np.zeros((capacity, option_dim), np.float32)
        self.reward = np.zeros((capacity,), np.float32)
        self.next_state = np.zeros((capacity, state_dim), np.float32)
        self.next_options = np.zeros((capacity, k_max, option_dim), np.float32)
        self.next_mask = np.zeros((capacity, k_max), bool)
        self.done = np.zeros((capacity,), np.float32)
        self.size = 0
        self.ptr = 0

    def add(self, state, option, reward, next_state, next_options, done) -> None:
        i = self.ptr
        self.state[i] = state
        self.option[i] = option
        self.reward[i] = reward
        self.next_state[i] = next_state
        self.done[i] = float(done)
        self.next_options[i] = 0.0
        self.next_mask[i] = False
        k = min(len(next_options), self.k_max)
        if k:
            self.next_options[i, :k] = next_options[:k]
            self.next_mask[i, :k] = True
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, rng: np.random.Generator) -> dict:
        idx = rng.integers(0, self.size, size=batch_size)
        return {
            "state": self.state[idx],
            "option": self.option[idx],
            "reward": self.reward[idx],
            "next_state": self.next_state[idx],
            "next_options": self.next_options[idx],
            "next_mask": self.next_mask[idx],
            "done": self.done[idx],
        }
