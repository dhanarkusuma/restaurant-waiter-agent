from typing import Any
from google.adk.tools import ToolContext

from agent.tools.menu_tool import get_tool_session
from apps.backend.app.services.customer_memory_service import CustomerMemoryService


def _resolve_customer_id(tool_context: Any = None, customer_id: int | None = None) -> int | None:
    """Helper to extract customer_id from tool context state or explicit param."""
    if customer_id is not None:
        return customer_id
    if tool_context is not None and hasattr(tool_context, "state"):
        return tool_context.state.get("customer_id")
    return None


async def get_customer_memory(
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """
    Melihat riwayat preferensi, ketidaksukaan (dislike), pantangan/alergi (dietary), catatan, serta daftar menu favorit yang tersimpan untuk pelanggan saat ini.
    Gunakan informasi ini untuk mempersonalisasi rekomendasi menu tanpa menyebutkan informasi yang tidak relevan.

    Returns:
        Data profil pelanggan berisi preferensi, dislikes, dietary, notes, dan favorites.
    """
    cid = _resolve_customer_id(tool_context, customer_id)
    if not cid:
        return {"error": "Konteks pelanggan (customer_id) tidak ditemukan"}

    async with get_tool_session() as session:
        service = CustomerMemoryService(session)
        return await service.get_customer_profile(cid)


async def save_customer_preference(
    memory_type: str,
    description: str,
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """
    Menyimpan preferensi permanen pelanggan ke dalam memori jangka panjang.
    PENTING: Gunakan HANYA jika pelanggan menyatakan preferensi/kebiasaan permanen secara eksplisit (contoh: "Saya memang tidak suka pedas", "Saya vegetarian", "Tolong ingat saya alergi udang").
    JANGAN simpan pernyataan konteks sementara sesi hari ini (contoh: "Hari ini saya tidak mau minum manis").

    Args:
        memory_type: Tipe memori, pilih salah satu dari: 'preference' (kesukaan), 'dislike' (makanan/bahan yang tidak disukai), 'dietary' (alergi/pantangan diet), 'note' (catatan relevan).
        description: Deskripsi kalimat lengkap dan jelas mengenai preferensi pelanggan.

    Returns:
        Konfirmasi penyimpanan memori (created/updated).
    """
    cid = _resolve_customer_id(tool_context, customer_id)
    if not cid:
        return {"error": "Konteks pelanggan (customer_id) tidak ditemukan"}

    async with get_tool_session() as session:
        service = CustomerMemoryService(session)
        return await service.save_memory(
            customer_id=cid,
            memory_type=memory_type,
            description=description,
        )


async def forget_customer_preference(
    keyword: str,
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """
    Menghapus preferensi atau catatan yang pernah disimpan sebelumnya ketika pelanggan secara eksplisit meminta untuk melupakannya.

    Args:
        keyword: Kata kunci atau topik yang ingin dilupakan (misal: 'pedas', 'kacang', 'seafood').

    Returns:
        Status penghapusan memori dan daftar item yang dihapus.
    """
    cid = _resolve_customer_id(tool_context, customer_id)
    if not cid:
        return {"error": "Konteks pelanggan (customer_id) tidak ditemukan"}

    async with get_tool_session() as session:
        service = CustomerMemoryService(session)
        return await service.forget_memory(
            customer_id=cid,
            keyword=keyword,
        )


async def add_customer_favorite(
    menu_name_or_id: str,
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """
    Menambahkan suatu menu ke dalam daftar menu favorit pelanggan ketika pelanggan memintanya.

    Args:
        menu_name_or_id: Nama menu (misal: 'Nasi Goreng Spesial') atau ID numerik menu.

    Returns:
        Status penambahan menu favorit.
    """
    cid = _resolve_customer_id(tool_context, customer_id)
    if not cid:
        return {"error": "Konteks pelanggan (customer_id) tidak ditemukan"}

    async with get_tool_session() as session:
        service = CustomerMemoryService(session)
        menu_id = int(menu_name_or_id) if menu_name_or_id.isdigit() else None
        menu_name = menu_name_or_id if not menu_name_or_id.isdigit() else None
        return await service.add_favorite(
            customer_id=cid,
            menu_id=menu_id,
            menu_name=menu_name,
        )


async def remove_customer_favorite(
    menu_name_or_id: str,
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """
    Menghapus suatu menu dari daftar menu favorit pelanggan ketika pelanggan memintanya.

    Args:
        menu_name_or_id: Nama menu (misal: 'Nasi Goreng Spesial') atau ID numerik menu.

    Returns:
        Status penghapusan menu favorit.
    """
    cid = _resolve_customer_id(tool_context, customer_id)
    if not cid:
        return {"error": "Konteks pelanggan (customer_id) tidak ditemukan"}

    async with get_tool_session() as session:
        service = CustomerMemoryService(session)
        menu_id = int(menu_name_or_id) if menu_name_or_id.isdigit() else None
        menu_name = menu_name_or_id if not menu_name_or_id.isdigit() else None
        return await service.remove_favorite(
            customer_id=cid,
            menu_id=menu_id,
            menu_name=menu_name,
        )
