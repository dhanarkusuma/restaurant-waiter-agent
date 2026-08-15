from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.database import AsyncSessionLocal
from apps.backend.app.services.menu_service import MenuService

# Global session factory used by ADK tools (can be overridden in tests)
_session_factory = AsyncSessionLocal


def set_tool_session_factory(factory: Any) -> None:
    """Set the session factory for menu tools (useful for isolated tests)."""
    global _session_factory
    _session_factory = factory


def reset_tool_session_factory() -> None:
    """Reset session factory to production AsyncSessionLocal."""
    global _session_factory
    _session_factory = AsyncSessionLocal


@asynccontextmanager
async def get_tool_session() -> AsyncGenerator[AsyncSession, None]:
    """Return async context manager for tool db session with auto-commit on success."""
    session_obj = _session_factory()
    if hasattr(session_obj, "__aenter__"):
        async with session_obj as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    else:
        try:
            yield session_obj
            await session_obj.commit()
        except Exception:
            await session_obj.rollback()
            raise


async def search_available_menu(
    query: str | None = None,
    category: str | None = None,
    max_price: int | None = None,
    min_price: int | None = None,
) -> list[dict[str, Any]]:
    """
    Mencari daftar menu makanan dan minuman yang saat ini TERSEDIA di restoran.
    Gunakan fungsi ini setiap kali pelanggan menanyakan menu, meminta rekomendasi, mencari makanan/minuman tertentu, atau memfilter berdasarkan kategori dan harga.

    Args:
        query: Kata kunci pencarian nama makanan/minuman atau bahan (misal: 'nasi goreng', 'ayam', 'pedas', 'cokelat', 'teh').
        category: Nama kategori menu (misal: 'Makanan Utama', 'Minuman', 'Dessert', 'Camilan').
        max_price: Batas harga maksimum dalam Rupiah (misal: 50000).
        min_price: Batas harga minimum dalam Rupiah (misal: 10000).

    Returns:
        Daftar menu yang tersedia lengkap dengan id, name, category, price (harga dalam Rp), dan description.
    """
    async with get_tool_session() as session:
        service = MenuService(session)
        return await service.search_menu(
            query=query if query else None,
            category_name=category if category else None,
            max_price=max_price,
            min_price=min_price,
            only_available=True,
        )


async def get_menu_details(menu_id: int) -> dict[str, Any]:
    """
    Mendapatkan rincian lengkap suatu menu berdasarkan ID menu.

    Args:
        menu_id: ID numerik dari menu.

    Returns:
        Rincian menu meliputi id, nama, kategori, harga, deskripsi, dan ketersediaan.
    """
    async with get_tool_session() as session:
        service = MenuService(session)
        details = await service.get_menu_details(menu_id)
        if not details:
            return {"error": f"Menu dengan ID {menu_id} tidak ditemukan"}
        return details
