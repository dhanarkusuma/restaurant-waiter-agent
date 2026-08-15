from typing import Any
from google.adk.tools import ToolContext

from agent.tools.menu_tool import get_tool_session
from apps.backend.app.services.order_service import OrderService


def _resolve_context(tool_context: Any = None, customer_id: int | None = None, session_id: int | None = None) -> tuple[int | None, int | None]:
    cid = customer_id
    sid = session_id

    if tool_context is not None and hasattr(tool_context, "state"):
        if cid is None:
            cid = tool_context.state.get("customer_id")
        if sid is None:
            sid = tool_context.state.get("dining_session_id")

    return cid, sid


async def add_item_to_order_draft(
    menu_item: str,
    quantity: int = 1,
    notes: str = "",
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """
    Menambahkan menu makanan atau minuman ke dalam draft pesanan sementara pelanggan.
    Harga dihitung secara aman dari database restoran.

    Args:
        menu_item: Nama menu (misal: 'Nasi Goreng Spesial') atau ID numerik menu.
        quantity: Jumlah porsi (minimal 1).
        notes: Catatan khusus pemesanan jika ada (misal: 'pedas sedang', 'tanpa es', 'telur matang').

    Returns:
        Ringkasan penambahan item dan isi draft pesanan terkini.
    """
    cid, sid = _resolve_context(tool_context, customer_id, session_id)
    if not cid or not sid:
        return {"error": "Konteks pelanggan atau sesi makan tidak ditemukan"}

    async with get_tool_session() as session:
        service = OrderService(session)
        return await service.add_item_to_draft(
            customer_id=cid,
            session_id=sid,
            menu_name_or_id=menu_item,
            quantity=quantity,
            notes=notes if notes else None,
        )


async def update_draft_item_quantity(
    menu_item: str,
    quantity: int,
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """
    Mengubah jumlah porsi suatu menu di dalam draft pesanan. Jika quantity <= 0, menu akan dihapus dari draft.

    Args:
        menu_item: Nama menu atau ID numerik menu yang ingin diubah jumlahnya.
        quantity: Jumlah porsi baru.

    Returns:
        Status pembaruan dan ringkasan draft pesanan terkini.
    """
    cid, sid = _resolve_context(tool_context, customer_id, session_id)
    if not cid or not sid:
        return {"error": "Konteks pelanggan atau sesi makan tidak ditemukan"}

    async with get_tool_session() as session:
        service = OrderService(session)
        return await service.update_item_quantity(
            customer_id=cid,
            session_id=sid,
            menu_name_or_id=menu_item,
            quantity=quantity,
        )


async def remove_item_from_order_draft(
    menu_item: str,
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """
    Menghapus suatu menu dari draft pesanan sementara pelanggan.

    Args:
        menu_item: Nama menu atau ID numerik menu yang ingin dihapus.

    Returns:
        Status penghapusan dan ringkasan draft pesanan terkini.
    """
    cid, sid = _resolve_context(tool_context, customer_id, session_id)
    if not cid or not sid:
        return {"error": "Konteks pelanggan atau sesi makan tidak ditemukan"}

    async with get_tool_session() as session:
        service = OrderService(session)
        return await service.remove_item_from_draft(
            customer_id=cid,
            session_id=sid,
            menu_name_or_id=menu_item,
        )


async def view_order_draft(
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """
    Melihat rincian lengkap draft pesanan saat ini (daftar menu, jumlah porsi, catatan, harga satuan, subtotal, dan total harga).
    Gunakan tool ini untuk mereview dan merangkum pesanan sebelum meminta konfirmasi dari pelanggan.

    Returns:
        Rincian item draft, subtotal, total harga, dan jumlah item.
    """
    cid, sid = _resolve_context(tool_context, customer_id, session_id)
    if not cid or not sid:
        return {"error": "Konteks pelanggan atau sesi makan tidak ditemukan"}

    async with get_tool_session() as session:
        service = OrderService(session)
        return await service.get_draft_summary(customer_id=cid, session_id=sid)


async def confirm_and_place_order(
    tool_context: ToolContext | None = None,
    customer_id: int | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """
    Mengonfirmasi dan secara resmi menyimpan pesanan ke database restoran (status ORDERED, UNPAID).
    PENTING: Gunakan tool ini HANYA setelah pelanggan secara eksplisit menyetujui/mengonfirmasi ringkasan pesanannya (misal: "Ya, saya pesan", "Sudah benar, tolong proses", "Kirim pesanan").

    Returns:
        Status pembuatan pesanan, order_id, daftar item, total_amount, dan status pesanan.
    """
    cid, sid = _resolve_context(tool_context, customer_id, session_id)
    if not cid or not sid:
        return {"error": "Konteks pelanggan atau sesi makan tidak ditemukan"}

    async with get_tool_session() as session:
        service = OrderService(session)
        return await service.confirm_and_create_order(customer_id=cid, session_id=sid)
