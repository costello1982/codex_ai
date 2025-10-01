from __future__ import annotations

from datetime import datetime
from ipaddress import ip_address, ip_network
from typing import Iterable, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    subnets: Mapped[list[Subnet]] = relationship("Subnet", back_populates="owner", cascade="all, delete-orphan")


class Subnet(Base):
    __tablename__ = "subnets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cidr: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    owner: Mapped[User] = relationship("User", back_populates="subnets")
    ip_addresses: Mapped[list[IPAddress]] = relationship(
        "IPAddress", back_populates="subnet", cascade="all, delete-orphan"
    )

    @property
    def network(self):
        return ip_network(self.cidr, strict=False)

    @property
    def capacity(self) -> int:
        network = self.network
        if network.prefixlen >= 31:
            return network.num_addresses
        return max(network.num_addresses - 2, 0)

    @property
    def hosts(self) -> Iterable[str]:
        network = self.network
        if network.prefixlen >= 31:
            for ip in network:
                yield str(ip)
        else:
            for host in network.hosts():
                yield str(host)

    def is_valid_host(self, ip_str: str) -> bool:
        try:
            ip_obj = ip_address(ip_str)
        except ValueError:
            return False

        network = self.network
        if ip_obj not in network:
            return False

        if network.prefixlen >= 31:
            return True

        return ip_obj != network.network_address and ip_obj != network.broadcast_address


class IPAddress(Base):
    __tablename__ = "ip_addresses"
    __table_args__ = (UniqueConstraint("subnet_id", "address", name="uq_subnet_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String(64), nullable=False)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="allocated", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allocated_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"), nullable=False)

    subnet: Mapped[Subnet] = relationship("Subnet", back_populates="ip_addresses")


__all__ = ["User", "Subnet", "IPAddress"]
