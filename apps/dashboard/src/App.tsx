import React, { useState, useEffect, useRef } from 'react';
import {
  api,
  Order,
  MenuItem,
  MenuCategory,
  CustomerMemoryProfile,
  PopularMenuItem,
  TableUsage,
  TableLayout,
  TableQRInfo,
} from './api';
import {
  UtensilsCrossed,
  ClipboardList,
  UserCheck,
  BarChart3,
  LogOut,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Plus,
  RefreshCw,
  Search,
  LayoutGrid,
  QrCode,
  Edit3,
  Trash2,
  Users,
  Move,
  Copy,
  Check,
  X,
  ExternalLink,
} from 'lucide-react';

type Tab = 'overview' | 'tables' | 'orders' | 'menu' | 'customers' | 'analytics';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(api.isAuthenticated());
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Auth State
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // Data State
  const [tables, setTables] = useState<TableLayout[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [popularMenu, setPopularMenu] = useState<PopularMenuItem[]>([]);
  const [tableUsage, setTableUsage] = useState<TableUsage[]>([]);
  const [selectedCustomerMemory, setSelectedCustomerMemory] = useState<CustomerMemoryProfile | null>(null);

  // Table State & Modals
  const [selectedTable, setSelectedTable] = useState<TableLayout | null>(null);
  const [showAddTableModal, setShowAddTableModal] = useState<boolean>(false);
  const [newTableNumber, setNewTableNumber] = useState('');
  const [newTableCapacity, setNewTableCapacity] = useState<number>(4);
  const [showEditTableModal, setShowEditTableModal] = useState<boolean>(false);
  const [editTableNumber, setEditTableNumber] = useState('');
  const [editTableCapacity, setEditTableCapacity] = useState<number>(4);
  const [tableQrModal, setTableQrModal] = useState<TableQRInfo | null>(null);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);

  // Dragging State for Visual Floor Layout
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{
    tableId: number;
    startX: number;
    startY: number;
    initialPosX: number;
    initialPosY: number;
    hasMoved: boolean;
  } | null>(null);

  // Filters & Loading
  const [orderStatusFilter, setOrderStatusFilter] = useState<string>('');
  const [orderPaymentFilter, setOrderPaymentFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  // New Menu Item Form
  const [showAddMenuModal, setShowAddMenuModal] = useState<boolean>(false);
  const [newMenuName, setNewMenuName] = useState('');
  const [newMenuPrice, setNewMenuPrice] = useState<number>(25000);
  const [newMenuCategory, setNewMenuCategory] = useState<number | undefined>(undefined);
  const [newMenuDesc, setNewMenuDesc] = useState('');

  useEffect(() => {
    const handleUnauthorized = () => setIsAuthenticated(false);
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated, activeTab, orderStatusFilter, orderPaymentFilter]);

  const loadDashboardData = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      if (activeTab === 'overview' || activeTab === 'tables') {
        const tableList = await api.listTables(true);
        setTables(tableList);
        if (selectedTable) {
          const updated = tableList.find((t) => t.id === selectedTable.id);
          if (updated) setSelectedTable(updated);
        }
      }
      if (activeTab === 'overview' || activeTab === 'orders') {
        const orderData = await api.listOrders(orderStatusFilter || undefined, orderPaymentFilter || undefined);
        setOrders(orderData);
      }
      if (activeTab === 'overview' || activeTab === 'menu') {
        const [items, cats] = await Promise.all([api.listMenuItems(), api.listCategories()]);
        setMenuItems(items);
        setCategories(cats);
        if (cats.length > 0 && !newMenuCategory) {
          setNewMenuCategory(cats[0].id);
        }
      }
      if (activeTab === 'customers') {
        const custList = await api.listCustomers();
        setCustomers(custList);
      }
      if (activeTab === 'overview' || activeTab === 'analytics') {
        const [pop, tUsage] = await Promise.all([api.getPopularMenu(), api.getTableUsage()]);
        setPopularMenu(pop);
        setTableUsage(tUsage);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Gagal memuat data.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setAuthLoading(true);
    try {
      await api.login(username, password);
      setIsAuthenticated(true);
      setActiveTab('overview');
    } catch (err: any) {
      setLoginError(err.message || 'Login gagal. Periksa username dan password.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    api.clearToken();
    setIsAuthenticated(false);
  };

  // --- Table Actions ---
  const handleCreateTable = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Calculate initial position staggered on canvas
      const count = tables.length;
      const initialX = 30 + (count % 4) * 160;
      const initialY = 30 + Math.floor(count / 4) * 130;
      await api.createTable({
        table_number: newTableNumber.trim(),
        capacity: Number(newTableCapacity),
        position_x: initialX,
        position_y: initialY,
      });
      setShowAddTableModal(false);
      setNewTableNumber('');
      setNewTableCapacity(4);
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal menambah meja: ${err.message}`);
    }
  };

  const handleOpenEditTable = (table: TableLayout) => {
    setEditTableNumber(table.table_number);
    setEditTableCapacity(table.capacity);
    setShowEditTableModal(true);
  };

  const handleUpdateTableMetadata = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTable) return;
    try {
      const updated = await api.updateTable(selectedTable.id, {
        table_number: editTableNumber.trim(),
        capacity: Number(editTableCapacity),
      });
      setShowEditTableModal(false);
      setSelectedTable(updated);
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal mengubah data meja: ${err.message}`);
    }
  };

  const handleDeactivateTable = async (table: TableLayout) => {
    if (!window.confirm(`Yakin ingin menonaktifkan/menghapus Meja ${table.table_number}?`)) {
      return;
    }
    try {
      const res = await api.deactivateTable(table.id);
      alert(res.message);
      setSelectedTable(null);
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal: ${err.message}`);
    }
  };

  const handleViewTableQR = async (tableId: number) => {
    try {
      const qrInfo = await api.getTableQR(tableId);
      setTableQrModal(qrInfo);
      setCopiedLink(false);
    } catch (err: any) {
      alert(`Gagal memuat info QR: ${err.message}`);
    }
  };

  // --- Pointer Drag & Drop for Floor Layout ---
  const handlePointerDown = (e: React.PointerEvent, table: TableLayout) => {
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    dragRef.current = {
      tableId: table.id,
      startX: e.clientX,
      startY: e.clientY,
      initialPosX: table.position_x,
      initialPosY: table.position_y,
      hasMoved: false,
    };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const { tableId, startX, startY, initialPosX, initialPosY } = dragRef.current;
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;

    if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
      dragRef.current.hasMoved = true;
    }

    const canvas = canvasRef.current;
    const canvasWidth = canvas ? canvas.clientWidth : 800;
    const canvasHeight = canvas ? canvas.clientHeight : 600;

    const newX = Math.max(10, Math.min(canvasWidth - 150, initialPosX + deltaX));
    const newY = Math.max(10, Math.min(canvasHeight - 120, initialPosY + deltaY));

    setTables((prev) =>
      prev.map((t) => (t.id === tableId ? { ...t, position_x: Math.round(newX), position_y: Math.round(newY) } : t))
    );
  };

  const handlePointerUp = async (e: React.PointerEvent, table: TableLayout) => {
    if (!dragRef.current) return;
    const { tableId, hasMoved } = dragRef.current;
    dragRef.current = null;

    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch (_) {}

    if (hasMoved) {
      // Persist new position to PostgreSQL
      const currentTable = tables.find((t) => t.id === tableId);
      if (currentTable) {
        try {
          await api.updateTablePosition(tableId, currentTable.position_x, currentTable.position_y);
        } catch (err: any) {
          console.error('Failed to persist table position:', err);
        }
      }
    } else {
      // Clicked without dragging -> open details
      setSelectedTable(table);
    }
  };

  // --- Order & Menu Handlers ---
  const handleAdvanceOrderStatus = async (orderId: number, nextStatus: 'IN_PROGRESS' | 'DONE') => {
    try {
      await api.updateOrderStatus(orderId, nextStatus);
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal mengubah status: ${err.message}`);
    }
  };

  const handleMarkPaid = async (orderId: number) => {
    try {
      await api.markOrderPaid(orderId);
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal memproses pembayaran: ${err.message}`);
    }
  };

  const handleToggleMenuAvailability = async (itemId: number, currentAvailable: boolean) => {
    try {
      await api.setMenuItemAvailability(itemId, !currentAvailable);
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal mengubah ketersediaan: ${err.message}`);
    }
  };

  const handleCreateMenuItem = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createMenuItem({
        name: newMenuName,
        price: Number(newMenuPrice),
        category_id: newMenuCategory,
        description: newMenuDesc,
        is_available: true,
      });
      setShowAddMenuModal(false);
      setNewMenuName('');
      setNewMenuDesc('');
      loadDashboardData();
    } catch (err: any) {
      alert(`Gagal menambahkan menu: ${err.message}`);
    }
  };

  const handleViewCustomerMemory = async (customerId: number) => {
    try {
      const memoryProfile = await api.getCustomerMemory(customerId);
      setSelectedCustomerMemory(memoryProfile);
    } catch (err: any) {
      alert(`Gagal mengambil data memori pelanggan: ${err.message}`);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 max-w-md w-full shadow-2xl">
          <div className="flex items-center space-x-3 mb-6">
            <div className="bg-amber-500/10 p-3 rounded-lg text-amber-400">
              <UtensilsCrossed className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100">Restaurant Waiter</h1>
              <p className="text-sm text-slate-400">Admin Staff Dashboard</p>
            </div>
          </div>

          {loginError && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-sm mb-4">
              {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-amber-500 hover:bg-amber-600 font-semibold text-slate-950 py-2.5 rounded-lg transition disabled:opacity-50"
            >
              {authLoading ? 'Memproses...' : 'Masuk ke Dashboard'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between p-4">
        <div>
          <div className="flex items-center space-x-3 px-2 py-4 mb-6">
            <UtensilsCrossed className="w-7 h-7 text-amber-400" />
            <div>
              <h2 className="font-bold text-base leading-tight">Admin Portal</h2>
              <span className="text-xs text-amber-400/90 font-medium">Restaurant Waiter</span>
            </div>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'overview' ? 'bg-amber-500/10 text-amber-400 font-semibold' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Ringkasan</span>
            </button>

            <button
              onClick={() => setActiveTab('tables')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'tables' ? 'bg-amber-500/10 text-amber-400 font-semibold' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
              <span>Denah Meja (Layout)</span>
            </button>

            <button
              onClick={() => setActiveTab('orders')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'orders' ? 'bg-amber-500/10 text-amber-400 font-semibold' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <ClipboardList className="w-4 h-4" />
              <span>Manajemen Pesanan</span>
            </button>

            <button
              onClick={() => setActiveTab('menu')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'menu' ? 'bg-amber-500/10 text-amber-400 font-semibold' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <UtensilsCrossed className="w-4 h-4" />
              <span>Kelola Menu</span>
            </button>

            <button
              onClick={() => setActiveTab('customers')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'customers' ? 'bg-amber-500/10 text-amber-400 font-semibold' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <UserCheck className="w-4 h-4" />
              <span>Memori Pelanggan</span>
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'analytics' ? 'bg-amber-500/10 text-amber-400 font-semibold' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Statistik & Analitik</span>
            </button>
          </nav>
        </div>

        <div className="pt-4 border-t border-slate-800">
          <button
            onClick={handleLogout}
            className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition"
          >
            <LogOut className="w-4 h-4" />
            <span>Keluar (Logout)</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header Bar */}
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                {activeTab === 'overview' && 'Ringkasan Restoran'}
                {activeTab === 'tables' && 'Denah & Manajemen Meja'}
                {activeTab === 'orders' && 'Daftar & Status Pesanan'}
                {activeTab === 'menu' && 'Katalog Menu Restoran'}
                {activeTab === 'customers' && 'Profil & Memori Pelanggan'}
                {activeTab === 'analytics' && 'Laporan & Statistik'}
              </h1>
              <p className="text-sm text-slate-400">PostgreSQL source of truth • Admin Control Panel</p>
            </div>
            <button
              onClick={loadDashboardData}
              disabled={loading}
              className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-lg text-sm font-medium transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Segarkan</span>
            </button>
          </div>

          {errorMsg && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm">
              {errorMsg}
            </div>
          )}

          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-slate-400">Total Meja Aktif</div>
                  <div className="text-2xl font-bold mt-2 text-slate-100">
                    {tables.filter((t) => t.is_active).length}
                  </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-emerald-400">Meja Tersedia</div>
                  <div className="text-2xl font-bold mt-2 text-emerald-400">
                    {tables.filter((t) => t.is_active && t.status === 'AVAILABLE').length}
                  </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-rose-400">Meja Terisi (Occupied)</div>
                  <div className="text-2xl font-bold mt-2 text-rose-400">
                    {tables.filter((t) => t.is_active && t.status === 'OCCUPIED').length}
                  </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-amber-400">Pesanan Aktif</div>
                  <div className="text-2xl font-bold mt-2 text-amber-400">
                    {orders.filter((o) => o.status !== 'DONE').length}
                  </div>
                </div>
              </div>

              {/* Floor Quick View */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-base text-slate-200">Denah Meja Restoran</h3>
                  <button
                    onClick={() => setActiveTab('tables')}
                    className="text-xs text-amber-400 hover:underline font-medium"
                  >
                    Buka Editor Denah &rarr;
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
                  {tables
                    .filter((t) => t.is_active)
                    .map((table) => (
                      <div
                        key={table.id}
                        onClick={() => {
                          setSelectedTable(table);
                          setActiveTab('tables');
                        }}
                        className={`p-3 rounded-lg border cursor-pointer transition ${
                          table.status === 'OCCUPIED'
                            ? 'bg-rose-950/20 border-rose-500/40 text-rose-300 hover:border-rose-400'
                            : 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300 hover:border-emerald-400'
                        }`}
                      >
                        <div className="font-bold text-sm">Meja {table.table_number}</div>
                        <div className="text-xs text-slate-400 mt-1">{table.capacity} Kursi</div>
                        <div className="mt-2 text-[10px] font-semibold uppercase">
                          {table.status === 'OCCUPIED' ? '● Terisi' : '○ Tersedia'}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Recent Orders Preview */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h3 className="font-semibold text-base mb-4 text-slate-200">Pesanan Terbaru</h3>
                {orders.length === 0 ? (
                  <p className="text-slate-500 text-sm">Belum ada pesanan.</p>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {orders.slice(0, 5).map((order) => (
                      <div key={order.id} className="py-3 flex justify-between items-center text-sm">
                        <div>
                          <span className="font-semibold text-slate-200">Order #{order.id}</span>
                          <span className="text-xs text-slate-400 ml-2">Meja #{order.table_id}</span>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {order.items.map((i) => `${i.quantity}x ${i.name}`).join(', ')}
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span
                            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                              order.status === 'DONE'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : order.status === 'IN_PROGRESS'
                                ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            }`}
                          >
                            {order.status}
                          </span>
                          <span className="font-semibold text-slate-300">
                            Rp {order.total_amount.toLocaleString('id-ID')}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TABLES TAB (VISUAL FLOOR LAYOUT) */}
          {activeTab === 'tables' && (
            <div className="space-y-4">
              {/* Floor Layout Controls Bar */}
              <div className="flex flex-wrap justify-between items-center bg-slate-900 border border-slate-800 p-4 rounded-xl gap-4">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
                    <span className="text-slate-300">Tersedia (AVAILABLE)</span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="w-3 h-3 rounded-full bg-rose-500 inline-block"></span>
                    <span className="text-slate-300">Terisi (OCCUPIED)</span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="w-3 h-3 rounded-full bg-slate-600 inline-block"></span>
                    <span className="text-slate-400">Nonaktif</span>
                  </div>
                  <span className="text-xs text-slate-500 border-l border-slate-800 pl-4">
                    💡 Drag meja untuk mengubah denah. Posisi otomatis tersimpan.
                  </span>
                </div>
                <button
                  onClick={() => setShowAddTableModal(true)}
                  className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold px-3.5 py-2 rounded-lg text-sm flex items-center space-x-2 transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Tambah Meja</span>
                </button>
              </div>

              {/* Main Floor Area + Detail Sidebar Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Visual Canvas Area (3 cols) */}
                <div
                  ref={canvasRef}
                  onPointerMove={handlePointerMove}
                  className="lg:col-span-3 h-[620px] bg-slate-950/90 border border-slate-800 rounded-xl relative overflow-hidden shadow-inner select-none"
                  style={{
                    backgroundImage:
                      'radial-gradient(circle, rgba(51, 65, 85, 0.4) 1px, transparent 1px)',
                    backgroundSize: '24px 24px',
                  }}
                >
                  {tables.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">
                      Belum ada meja. Klik "Tambah Meja" untuk menambahkan meja ke denah.
                    </div>
                  ) : (
                    tables.map((table) => {
                      const isOccupied = table.status === 'OCCUPIED';
                      const isSelected = selectedTable?.id === table.id;
                      const isActive = table.is_active;

                      return (
                        <div
                          key={table.id}
                          onPointerDown={(e) => handlePointerDown(e, table)}
                          onPointerUp={(e) => handlePointerUp(e, table)}
                          style={{
                            transform: `translate(${table.position_x}px, ${table.position_y}px)`,
                            touchAction: 'none',
                          }}
                          className={`absolute top-0 left-0 w-36 h-28 rounded-xl p-3 shadow-lg flex flex-col justify-between cursor-grab active:cursor-grabbing transition-shadow transition-colors ${
                            !isActive
                              ? 'bg-slate-900/40 border border-slate-700/60 opacity-60 text-slate-500'
                              : isOccupied
                              ? 'bg-slate-900/90 border-2 border-rose-500/70 text-rose-300 hover:border-rose-400 hover:shadow-rose-950/50'
                              : 'bg-slate-900/90 border-2 border-emerald-500/60 text-emerald-300 hover:border-emerald-400 hover:shadow-emerald-950/50'
                          } ${isSelected ? 'ring-2 ring-amber-400 ring-offset-2 ring-offset-slate-950' : ''}`}
                        >
                          {/* Card Header */}
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="font-bold text-sm tracking-wide text-slate-100">
                                Meja {table.table_number}
                              </span>
                            </div>
                            <Move className="w-3.5 h-3.5 text-slate-500 opacity-60" />
                          </div>

                          {/* Card Body */}
                          <div>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                                !isActive
                                  ? 'bg-slate-800 text-slate-400'
                                  : isOccupied
                                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                  : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              }`}
                            >
                              {!isActive ? 'Nonaktif' : isOccupied ? '● Terisi' : '○ Tersedia'}
                            </span>
                          </div>

                          {/* Card Footer */}
                          <div className="flex justify-between items-center text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                            <span className="flex items-center">
                              <Users className="w-3 h-3 mr-1 text-slate-400" />
                              {table.capacity} Kursi
                            </span>
                            {isOccupied && table.active_session?.customer && (
                              <span className="text-[10px] text-rose-400 truncate max-w-[60px]" title={table.active_session.customer.username || table.active_session.customer.first_name || 'Pelanggan'}>
                                {table.active_session.customer.username || table.active_session.customer.first_name || 'Sesi'}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Table Detail & Actions Panel (1 col) */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
                  {selectedTable ? (
                    <div className="space-y-4">
                      <div className="flex justify-between items-start pb-3 border-b border-slate-800">
                        <div>
                          <h3 className="font-bold text-lg text-slate-100">
                            Meja {selectedTable.table_number}
                          </h3>
                          <span
                            className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase mt-1 inline-block ${
                              !selectedTable.is_active
                                ? 'bg-slate-800 text-slate-400'
                                : selectedTable.status === 'OCCUPIED'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            }`}
                          >
                            {!selectedTable.is_active
                              ? 'Nonaktif'
                              : selectedTable.status === 'OCCUPIED'
                              ? 'Terisi (OCCUPIED)'
                              : 'Tersedia (AVAILABLE)'}
                          </span>
                        </div>
                        <button
                          onClick={() => setSelectedTable(null)}
                          className="text-slate-500 hover:text-slate-300"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="space-y-2.5 text-xs">
                        <div className="flex justify-between py-1 border-b border-slate-800/60">
                          <span className="text-slate-400">Kapasitas:</span>
                          <span className="font-semibold text-slate-200">
                            {selectedTable.capacity} Orang
                          </span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-800/60">
                          <span className="text-slate-400">Status Meja:</span>
                          <span className="font-semibold text-slate-200">
                            {selectedTable.is_active ? 'Aktif Operasional' : 'Nonaktif'}
                          </span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-800/60">
                          <span className="text-slate-400">Koordinat Posisi:</span>
                          <span className="font-mono text-slate-300">
                            X: {selectedTable.position_x}, Y: {selectedTable.position_y}
                          </span>
                        </div>
                      </div>

                      {/* Active Session Info Box */}
                      {selectedTable.active_session ? (
                        <div className="bg-rose-950/20 border border-rose-500/30 rounded-lg p-3 space-y-2 text-xs">
                          <div className="font-bold text-rose-400 flex items-center space-x-1.5">
                            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
                            <span>Sesi Makan Aktif</span>
                          </div>
                          <div>
                            <span className="text-slate-400">Pelanggan:</span>{' '}
                            <span className="font-semibold text-slate-200">
                              {selectedTable.active_session.customer?.first_name || ''}{' '}
                              {selectedTable.active_session.customer?.last_name || ''}
                              {selectedTable.active_session.customer?.username
                                ? ` (@${selectedTable.active_session.customer.username})`
                                : ''}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400">Sesi Dimulai:</span>{' '}
                            <span className="text-slate-300">
                              {new Date(selectedTable.active_session.started_at).toLocaleTimeString('id-ID')}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400">Order Terakhir Selesai:</span>{' '}
                            <span className="text-slate-300">
                              {selectedTable.active_session.last_order_completed_at
                                ? new Date(
                                    selectedTable.active_session.last_order_completed_at
                                  ).toLocaleTimeString('id-ID')
                                : 'Belum ada pesanan selesai'}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="bg-slate-800/40 rounded-lg p-3 text-xs text-slate-400">
                          Tidak ada sesi makan aktif saat ini. Meja siap digunakan oleh pelanggan.
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="space-y-2 pt-2">
                        <button
                          onClick={() => handleViewTableQR(selectedTable.id)}
                          className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition"
                        >
                          <QrCode className="w-3.5 h-3.5 text-amber-400" />
                          <span>Lihat QR & Deep Link</span>
                        </button>
                        <button
                          onClick={() => handleOpenEditTable(selectedTable)}
                          className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition"
                        >
                          <Edit3 className="w-3.5 h-3.5 text-blue-400" />
                          <span>Ubah Nomor / Kapasitas</span>
                        </button>
                        <button
                          onClick={() => handleDeactivateTable(selectedTable)}
                          className="w-full bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 py-2 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Nonaktifkan Meja</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
                      <LayoutGrid className="w-10 h-10 mb-2 opacity-30" />
                      <p className="text-sm font-medium">Pilih Meja</p>
                      <p className="text-xs text-slate-600 mt-1">
                        Klik salah satu meja pada denah untuk melihat informasi sesi, QR code, atau mengubah data.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ORDERS TAB */}
          {activeTab === 'orders' && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3 bg-slate-900 p-4 rounded-xl border border-slate-800 items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-xs text-slate-400 uppercase font-semibold">Filter Status:</span>
                  <select
                    value={orderStatusFilter}
                    onChange={(e) => setOrderStatusFilter(e.target.value)}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-xs px-3 py-1.5 text-slate-200 focus:outline-none"
                  >
                    <option value="">Semua Status Order</option>
                    <option value="ORDERED">ORDERED</option>
                    <option value="IN_PROGRESS">IN_PROGRESS</option>
                    <option value="DONE">DONE</option>
                  </select>

                  <select
                    value={orderPaymentFilter}
                    onChange={(e) => setOrderPaymentFilter(e.target.value)}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-xs px-3 py-1.5 text-slate-200 focus:outline-none"
                  >
                    <option value="">Semua Status Bayar</option>
                    <option value="UNPAID">UNPAID (Belum Bayar)</option>
                    <option value="PAID">PAID (Lunas)</option>
                  </select>
                </div>
                <div className="text-xs text-slate-400 font-medium">
                  Menampilkan {orders.length} pesanan
                </div>
              </div>

              {/* Order Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {orders.length === 0 ? (
                  <div className="col-span-full py-12 text-center text-slate-500 bg-slate-900 border border-slate-800 rounded-xl">
                    Tidak ada pesanan yang sesuai filter.
                  </div>
                ) : (
                  orders.map((order) => (
                    <div
                      key={order.id}
                      className={`bg-slate-900 border rounded-xl p-5 flex flex-col justify-between space-y-4 ${
                        order.is_overdue
                          ? 'border-red-500/50 bg-red-950/10'
                          : 'border-slate-800'
                      }`}
                    >
                      <div className="space-y-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="font-bold text-base text-slate-100">Order #{order.id}</span>
                            <span className="text-xs text-amber-400 font-semibold ml-2">Meja #{order.table_id}</span>
                          </div>
                          <div className="flex flex-col items-end space-y-1">
                            <span
                              className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                                order.status === 'DONE'
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : order.status === 'IN_PROGRESS'
                                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              }`}
                            >
                              {order.status}
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                                order.payment_status === 'PAID'
                                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                                  : 'bg-rose-950 text-rose-400 border border-rose-500/30'
                              }`}
                            >
                              {order.payment_status}
                            </span>
                          </div>
                        </div>

                        {order.is_overdue && (
                          <div className="bg-red-500/20 text-red-400 text-xs px-2.5 py-1 rounded-lg flex items-center space-x-1.5 font-medium border border-red-500/30">
                            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                            <span>Pembayaran Melebihi Batas Waktu (Overdue)</span>
                          </div>
                        )}

                        <div className="bg-slate-950/60 p-3 rounded-lg space-y-1.5 text-xs">
                          {order.items.map((item) => (
                            <div key={item.id} className="flex justify-between items-center text-slate-300">
                              <span>
                                {item.quantity}x {item.name || `Menu #${item.menu_item_id}`}
                                {item.notes && <span className="text-slate-500 italic block text-[10px]">Catatan: {item.notes}</span>}
                              </span>
                              <span className="font-semibold text-slate-400">Rp {item.subtotal.toLocaleString('id-ID')}</span>
                            </div>
                          ))}
                          <div className="pt-2 mt-2 border-t border-slate-800 flex justify-between font-bold text-slate-100 text-sm">
                            <span>Total Pesanan:</span>
                            <span className="text-amber-400">Rp {order.total_amount.toLocaleString('id-ID')}</span>
                          </div>
                        </div>
                      </div>

                      {/* Status Action Buttons */}
                      <div className="pt-2 border-t border-slate-800 space-y-2">
                        <div className="flex space-x-2">
                          {order.status === 'ORDERED' && (
                            <button
                              onClick={() => handleAdvanceOrderStatus(order.id, 'IN_PROGRESS')}
                              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-1.5 rounded-lg text-xs transition"
                            >
                              Proses Pesanan &rarr;
                            </button>
                          )}
                          {order.status === 'IN_PROGRESS' && (
                            <button
                              onClick={() => handleAdvanceOrderStatus(order.id, 'DONE')}
                              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-1.5 rounded-lg text-xs transition"
                            >
                              Selesaikan Pesanan &check;
                            </button>
                          )}
                        </div>

                        {order.payment_status === 'UNPAID' && (
                          <button
                            onClick={() => handleMarkPaid(order.id)}
                            className="w-full bg-slate-800 hover:bg-emerald-600 hover:text-white text-emerald-400 border border-emerald-500/30 font-semibold py-1.5 rounded-lg text-xs transition"
                          >
                            Tandai Sudah Dibayar (Manual PAID)
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* MENU TAB */}
          {activeTab === 'menu' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center bg-slate-900 p-4 rounded-xl border border-slate-800">
                <span className="text-sm text-slate-300 font-semibold">Daftar Menu & Ketersediaan</span>
                <button
                  onClick={() => setShowAddMenuModal(true)}
                  className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Tambah Menu</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {menuItems.map((item) => (
                  <div key={item.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className="font-bold text-sm text-slate-100">{item.name}</span>
                        <span className="text-xs font-semibold text-amber-400">Rp {item.price.toLocaleString('id-ID')}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 uppercase font-semibold">{item.category_name || 'Umum'}</span>
                      {item.description && <p className="text-xs text-slate-400 mt-1">{item.description}</p>}
                    </div>

                    <div className="pt-2 border-t border-slate-800 flex justify-between items-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${item.is_available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                        {item.is_available ? 'Tersedia' : 'Habis (Unavailable)'}
                      </span>
                      <button
                        onClick={() => handleToggleMenuAvailability(item.id, item.is_available)}
                        className="text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1 rounded transition"
                      >
                        {item.is_available ? 'Set Habis' : 'Set Tersedia'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CUSTOMERS TAB */}
          {activeTab === 'customers' && (
            <div className="space-y-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 text-xs uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">ID</th>
                      <th className="p-3">Telegram ID</th>
                      <th className="p-3">Username</th>
                      <th className="p-3">Nama</th>
                      <th className="p-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {customers.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-semibold">{c.id}</td>
                        <td className="p-3 font-mono text-xs text-slate-400">{c.telegram_id}</td>
                        <td className="p-3 font-medium text-amber-400">{c.username ? `@${c.username}` : '-'}</td>
                        <td className="p-3">{`${c.first_name || ''} ${c.last_name || ''}`}</td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => handleViewCustomerMemory(c.id)}
                            className="bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                          >
                            Lihat Profil Memori
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Customer Memory Modal */}
              {selectedCustomerMemory && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-4 max-h-[90vh] overflow-y-auto">
                    <div className="flex justify-between items-start pb-3 border-b border-slate-800">
                      <div>
                        <h3 className="font-bold text-lg text-slate-100">
                          Memori Pelanggan: {selectedCustomerMemory.first_name || selectedCustomerMemory.username || `#${selectedCustomerMemory.customer_id}`}
                        </h3>
                        <span className="text-xs text-slate-400">Telegram ID: {selectedCustomerMemory.telegram_id}</span>
                      </div>
                      <button onClick={() => setSelectedCustomerMemory(null)} className="text-slate-400 hover:text-white">
                        <X className="w-5 h-5" />
                      </button>
                    </div>

                    <div className="space-y-3 text-xs">
                      <div>
                        <h4 className="font-bold text-amber-400 mb-1">Preferensi Makanan</h4>
                        {selectedCustomerMemory.memories.preference.length === 0 ? (
                          <p className="text-slate-500">Tidak ada catatan preferensi.</p>
                        ) : (
                          <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                            {selectedCustomerMemory.memories.preference.map((m) => (
                              <li key={m.id}>{m.description}</li>
                            ))}
                          </ul>
                        )}
                      </div>

                      <div>
                        <h4 className="font-bold text-rose-400 mb-1">Ketidaksukaan (Dislike)</h4>
                        {selectedCustomerMemory.memories.dislike.length === 0 ? (
                          <p className="text-slate-500">Tidak ada catatan.</p>
                        ) : (
                          <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                            {selectedCustomerMemory.memories.dislike.map((m) => (
                              <li key={m.id}>{m.description}</li>
                            ))}
                          </ul>
                        )}
                      </div>

                      <div>
                        <h4 className="font-bold text-blue-400 mb-1">Pantangan / Diet (Dietary)</h4>
                        {selectedCustomerMemory.memories.dietary.length === 0 ? (
                          <p className="text-slate-500">Tidak ada catatan pantangan.</p>
                        ) : (
                          <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                            {selectedCustomerMemory.memories.dietary.map((m) => (
                              <li key={m.id}>{m.description}</li>
                            ))}
                          </ul>
                        )}
                      </div>

                      <div>
                        <h4 className="font-bold text-emerald-400 mb-1">Menu Favorit</h4>
                        {selectedCustomerMemory.favorites.length === 0 ? (
                          <p className="text-slate-500">Belum ada menu favorit tersimpan.</p>
                        ) : (
                          <div className="grid grid-cols-2 gap-2 mt-1">
                            {selectedCustomerMemory.favorites.map((f) => (
                              <div key={f.menu_id} className="bg-slate-800 p-2 rounded border border-slate-700">
                                <span className="font-semibold text-slate-200 block">{f.name}</span>
                                <span className="text-[10px] text-amber-400">Rp {f.price.toLocaleString('id-ID')}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ANALYTICS TAB */}
          {activeTab === 'analytics' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Popular Menu */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h3 className="font-semibold text-base mb-4 text-slate-200">Menu Terpopuler (Paling Sering Dipesan)</h3>
                {popularMenu.length === 0 ? (
                  <p className="text-xs text-slate-500">Belum ada data pesanan.</p>
                ) : (
                  <div className="divide-y divide-slate-800 text-sm">
                    {popularMenu.map((m, idx) => (
                      <div key={m.menu_item_id} className="py-2.5 flex justify-between items-center">
                        <div>
                          <span className="font-bold text-amber-400 mr-2">#{idx + 1}</span>
                          <span className="text-slate-200 font-medium">{m.name}</span>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold text-slate-300">{m.total_quantity_ordered} porsi</div>
                          <div className="text-xs text-slate-500">Rp {m.total_revenue.toLocaleString('id-ID')}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Table Usage */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h3 className="font-semibold text-base mb-4 text-slate-200">Tingkat Penggunaan Meja (Sessions)</h3>
                {tableUsage.length === 0 ? (
                  <p className="text-xs text-slate-500">Belum ada data sesi.</p>
                ) : (
                  <div className="divide-y divide-slate-800 text-sm">
                    {tableUsage.map((t) => (
                      <div key={t.table_id} className="py-2.5 flex justify-between items-center">
                        <div className="font-medium text-slate-200">Meja {t.table_number}</div>
                        <div className="text-slate-400 font-medium">{t.total_sessions} sesi makan</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* MODALS */}

          {/* Add Table Modal */}
          {showAddTableModal && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                  <h3 className="font-bold text-slate-100">Tambah Meja Restoran Baru</h3>
                  <button onClick={() => setShowAddTableModal(false)} className="text-slate-500 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <form onSubmit={handleCreateTable} className="space-y-3 text-sm">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Nomor Meja (Contoh: T-01, VIP-1)</label>
                    <input
                      type="text"
                      value={newTableNumber}
                      onChange={(e) => setNewTableNumber(e.target.value)}
                      required
                      placeholder="T-01"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Kapasitas Kursi</label>
                    <input
                      type="number"
                      value={newTableCapacity}
                      onChange={(e) => setNewTableCapacity(Number(e.target.value))}
                      min={1}
                      max={50}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div className="flex justify-end space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowAddTableModal(false)}
                      className="px-3 py-2 text-slate-400 hover:text-white"
                    >
                      Batal
                    </button>
                    <button
                      type="submit"
                      className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold px-4 py-2 rounded-lg"
                    >
                      Simpan & Pasang di Denah
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Edit Table Modal */}
          {showEditTableModal && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                  <h3 className="font-bold text-slate-100">Ubah Data Meja</h3>
                  <button onClick={() => setShowEditTableModal(false)} className="text-slate-500 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <form onSubmit={handleUpdateTableMetadata} className="space-y-3 text-sm">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Nomor Meja</label>
                    <input
                      type="text"
                      value={editTableNumber}
                      onChange={(e) => setEditTableNumber(e.target.value)}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Kapasitas Kursi</label>
                    <input
                      type="number"
                      value={editTableCapacity}
                      onChange={(e) => setEditTableCapacity(Number(e.target.value))}
                      min={1}
                      max={50}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div className="flex justify-end space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowEditTableModal(false)}
                      className="px-3 py-2 text-slate-400 hover:text-white"
                    >
                      Batal
                    </button>
                    <button
                      type="submit"
                      className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold px-4 py-2 rounded-lg"
                    >
                      Simpan Perubahan
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* QR Code & Deep Link Modal */}
          {tableQrModal && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                  <div>
                    <h3 className="font-bold text-slate-100">QR Code & Deep Link Telegram</h3>
                    <p className="text-xs text-slate-400">Meja {tableQrModal.table_number}</p>
                  </div>
                  <button onClick={() => setTableQrModal(null)} className="text-slate-500 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">QR Code Token (Stabil)</label>
                    <div className="bg-slate-950 p-2.5 rounded-lg font-mono text-amber-400 border border-slate-800 select-all">
                      {tableQrModal.qr_code_token}
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">Telegram Deep Link URL</label>
                    <div className="bg-slate-950 p-2.5 rounded-lg font-mono text-slate-300 border border-slate-800 break-all select-all">
                      {tableQrModal.deep_link_url}
                    </div>
                  </div>

                  <div className="pt-2 flex justify-between items-center">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(tableQrModal.deep_link_url);
                        setCopiedLink(true);
                        setTimeout(() => setCopiedLink(false), 2000);
                      }}
                      className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold px-3 py-2 rounded-lg text-xs flex items-center space-x-1.5 transition"
                    >
                      {copiedLink ? <Check className="w-4 h-4 text-slate-950" /> : <Copy className="w-4 h-4" />}
                      <span>{copiedLink ? 'Tersalin ke Clipboard!' : 'Salin Deep Link'}</span>
                    </button>
                    <a
                      href={tableQrModal.deep_link_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-slate-400 hover:text-amber-400 flex items-center space-x-1"
                    >
                      <span>Buka di Telegram</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Add Menu Modal */}
          {showAddMenuModal && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4">
                <h3 className="font-bold text-slate-100">Tambah Menu Makanan/Minuman Baru</h3>
                <form onSubmit={handleCreateMenuItem} className="space-y-3 text-sm">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Nama Menu</label>
                    <input
                      type="text"
                      value={newMenuName}
                      onChange={(e) => setNewMenuName(e.target.value)}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Harga (Rp)</label>
                    <input
                      type="number"
                      value={newMenuPrice}
                      onChange={(e) => setNewMenuPrice(Number(e.target.value))}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Kategori</label>
                    <select
                      value={newMenuCategory || ''}
                      onChange={(e) => setNewMenuCategory(Number(e.target.value))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
                    >
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Deskripsi</label>
                    <textarea
                      value={newMenuDesc}
                      onChange={(e) => setNewMenuDesc(e.target.value)}
                      rows={2}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowAddMenuModal(false)}
                      className="px-3 py-2 text-slate-400 hover:text-white"
                    >
                      Batal
                    </button>
                    <button
                      type="submit"
                      className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold px-4 py-2 rounded-lg"
                    >
                      Simpan
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
