import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import (
    AdminUser,
    Customer,
    CustomerFavorite,
    CustomerMemory,
    DiningSession,
    MenuCategory,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    RestaurantTable,
    SessionStatus,
    TableStatus,
)


@pytest.mark.asyncio
async def test_customer_creation(db_session: AsyncSession):
    customer = Customer(
        telegram_id=123456789,
        username="john_doe",
        first_name="John",
        last_name="Doe",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    assert customer.id is not None
    assert customer.telegram_id == 123456789
    assert customer.username == "john_doe"
    assert customer.created_at is not None


@pytest.mark.asyncio
async def test_table_and_dining_session_lifecycle(db_session: AsyncSession):
    customer = Customer(telegram_id=987654321, username="alice")
    table = RestaurantTable(
        table_number="T-01",
        status=TableStatus.OCCUPIED,
        qr_code_token="token_table_01",
        capacity=4,
    )
    db_session.add_all([customer, table])
    await db_session.commit()
    await db_session.refresh(customer)
    await db_session.refresh(table)

    session = DiningSession(
        customer_id=customer.id,
        table_id=table.id,
        status=SessionStatus.ACTIVE,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.status == SessionStatus.ACTIVE
    assert session.customer_id == customer.id
    assert session.table_id == table.id
    assert session.started_at is not None


@pytest.mark.asyncio
async def test_menu_and_order_models(db_session: AsyncSession):
    customer = Customer(telegram_id=111222333, first_name="Bob")
    table = RestaurantTable(table_number="T-02", qr_code_token="token_t02")
    category = MenuCategory(name="Main Course", description="Delicious meals")
    db_session.add_all([customer, table, category])
    await db_session.commit()
    await db_session.refresh(customer)
    await db_session.refresh(table)
    await db_session.refresh(category)

    menu_item = MenuItem(
        category_id=category.id,
        name="Nasi Goreng Spesial",
        description="Indonesian fried rice with chicken and egg",
        price=35000,
        is_available=True,
    )
    db_session.add(menu_item)
    await db_session.commit()
    await db_session.refresh(menu_item)

    session = DiningSession(customer_id=customer.id, table_id=table.id)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    order = Order(
        customer_id=customer.id,
        dining_session_id=session.id,
        table_id=table.id,
        status=OrderStatus.ORDERED,
        payment_status=PaymentStatus.UNPAID,
        total_amount=35000,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    order_item = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        quantity=1,
        unit_price=35000,
        subtotal=35000,
        notes="No spicy please",
    )
    db_session.add(order_item)
    await db_session.commit()
    await db_session.refresh(order_item)

    # Verify query
    result = await db_session.execute(select(Order).where(Order.id == order.id))
    fetched_order = result.scalar_one()
    assert fetched_order.total_amount == 35000
    assert fetched_order.status == OrderStatus.ORDERED
    assert fetched_order.payment_status == PaymentStatus.UNPAID


@pytest.mark.asyncio
async def test_customer_memory_and_favorite(db_session: AsyncSession):
    customer = Customer(telegram_id=444555666, first_name="Charlie")
    menu_item = MenuItem(
        name="Es Teh Manis",
        description="Sweet iced tea",
        price=8000,
        is_available=True,
    )
    db_session.add_all([customer, menu_item])
    await db_session.commit()
    await db_session.refresh(customer)
    await db_session.refresh(menu_item)

    memory = CustomerMemory(
        customer_id=customer.id,
        type="preference",
        description="Customer menyukai minuman manis dan dingin.",
        metadata_json={"sweetness": "high"},
    )
    favorite = CustomerFavorite(
        customer_id=customer.id,
        menu_item_id=menu_item.id,
    )
    db_session.add_all([memory, favorite])
    await db_session.commit()
    await db_session.refresh(memory)
    await db_session.refresh(favorite)

    assert memory.id is not None
    assert memory.type == "preference"
    assert memory.description == "Customer menyukai minuman manis dan dingin."
    assert favorite.id is not None
    assert favorite.menu_item_id == menu_item.id


@pytest.mark.asyncio
async def test_admin_user_model(db_session: AsyncSession):
    admin = AdminUser(
        username="admin",
        hashed_password="hashed_secure_password_test",
        full_name="Restaurant Manager",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    assert admin.id is not None
    assert admin.username == "admin"
    assert admin.is_active is True
