from __future__ import annotations

from typing import List, Optional
from aiohttp import ClientSession
from pydantic import BaseModel


class Input(BaseModel):
    prev_hash: Optional[str] = None
    output_index: Optional[int] = None
    script: Optional[str] = None
    output_value: Optional[int] = None
    sequence: Optional[int] = None
    addresses: Optional[List[str]] = None
    script_type: Optional[str] = None
    age: Optional[int] = None


class Output(BaseModel):
    value: Optional[int] = None
    script: Optional[str] = None
    spent_by: Optional[str] = None
    addresses: Optional[List[str]] = None
    script_type: Optional[str] = None


class TransactionResponse(BaseModel):
    block_hash: Optional[str] = None
    block_height: Optional[int] = None
    block_index: Optional[int] = None
    hash: Optional[str] = None
    hex: Optional[str] = None
    addresses: Optional[List[str]] = None
    total: Optional[int] = None
    fees: Optional[int] = None
    size: Optional[int] = None
    vsize: Optional[int] = None
    preference: Optional[str] = None
    confirmed: Optional[str] = None
    received: Optional[str] = None
    ver: Optional[int] = None
    double_spend: Optional[bool] = None
    vin_sz: Optional[int] = None
    vout_sz: Optional[int] = None
    confirmations: Optional[int] = None
    confidence: Optional[int] = None
    inputs: Optional[List[Input]] = None
    outputs: Optional[List[Output]] = None

    @classmethod
    async def from_response(cls, coin: str, txid: str):
        async with ClientSession() as session:
            async with session.get(f"https://api.blockcypher.com/v1/{coin.lower()}/main/txs/{txid}") as response:
                data = await response.read()
        return cls.parse_raw(data)
