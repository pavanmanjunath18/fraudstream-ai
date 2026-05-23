from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Index
from ..database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    merchant_id = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(String, nullable=False)
    device_id = Column(String, nullable=False, index=True)
    ip_address = Column(String)
    geo_lat = Column(Float)
    geo_lon = Column(Float)
    merchant_category = Column(String)
    transaction_channel = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_transactions_account_timestamp", "account_id", "timestamp"),
    )
