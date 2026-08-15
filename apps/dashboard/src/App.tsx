import React, { useState, useEffect } from 'react';
import {
  api,
  Order,
  MenuItem,
  MenuCategory,
  CustomerMemoryProfile,
  PopularMenuItem,
  TableUsage,
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
} from 'lucide-react';

type Tab = 'overview' | 'orders' | 'menu' | 'customers' | 'analytics';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(api.isAuthenticated());
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Auth State
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // Data State
  const [orders, setOrders] = useState<Order[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [popularMenu, setPopularMenu] = useState<PopularMenuItem[]>([]);
  const [tableUsage, setTableUsage] = useState<TableUsage[]>([]);
  const [selectedCustomerMemory, setSelectedCustomerMemory] = useState<CustomerMemoryProfile | null>(null);

  // Filters & Modal
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
        const [pop, tables] = await Promise.all([api.getPopularMenu(), api.getTableUsage()]);
        setPopularMenu(pop);
        setTableUsage(tables);
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
              <h1 className="text-2xl font-bold tracking-tight text-slate-100 capitalize">
                {activeTab === 'overview' && 'Ringkasan Restoran'}
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
                  <div className="text-xs font-semibold uppercase text-slate-400">Total Pesanan</div>
                  <div className="text-2xl font-bold mt-2 text-slate-100">{orders.length}</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-amber-400">Pesanan ORDERED</div>
                  <div className="text-2xl font-bold mt-2 text-amber-400">
                    {orders.filter((o) => o.status === 'ORDERED').length}
                  </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-blue-400">Sedang Diproses (IN_PROGRESS)</div>
                  <div className="text-2xl font-bold mt-2 text-blue-400">
                    {orders.filter((o) => o.status === 'IN_PROGRESS').length}
                  </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs font-semibold uppercase text-emerald-400">Selesai (DONE)</div>
                  <div className="text-2xl font-bold mt-2 text-emerald-400">
                    {orders.filter((o) => o.status === 'DONE').length}
                  </div>
                </div>
              </div>

              {/* Recent Orders Preview */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h3 className="font-semibold text-base mb-4 text-slate-200">Pesanan Terbaru</h3>
                {orders.length === 0 ? (
                  <p className="text-slate-500 text-sm">Belum ada pesanan.</p>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {orders.slice(0, 5).map((ord) => (
                      <div key={ord.id} className="py-3 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-slate-200">
                            Order #{ord.id} • Meja {ord.table_id}
                          </div>
                          <div className="text-xs text-slate-400">
                            Total: Rp {ord.total_amount.toLocaleString('id-ID')} • {ord.items.length} item
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span
                            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                              ord.status === 'ORDERED'
                                ? 'bg-amber-500/10 text-amber-400'
                                : ord.status === 'IN_PROGRESS'
                                ? 'bg-blue-500/10 text-blue-400'
                                : 'bg-emerald-500/10 text-emerald-400'
                            }`}
                          >
                            {ord.status}
                          </span>
                          <span
                            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                              ord.payment_status === 'PAID'
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : 'bg-red-500/10 text-red-400'
                            }`}
                          >
                            {ord.payment_status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ORDERS TAB */}
          {activeTab === 'orders' && (
            <div className="space-y-4">
              {/* Filters */}
              <div className="flex flex-wrap gap-3 bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Status Dapur</label>
                  <select
                    value={orderStatusFilter}
                    onChange={(e) => setOrderStatusFilter(e.target.value)}
                    className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                  >
                    <option value="">Semua Status</option>
                    <option value="ORDERED">ORDERED</option>
                    <option value="IN_PROGRESS">IN_PROGRESS</option>
                    <option value="DONE">DONE</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Status Pembayaran</label>
                  <select
                    value={orderPaymentFilter}
                    onChange={(e) => setOrderPaymentFilter(e.target.value)}
                    className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                  >
                    <option value="">Semua Pembayaran</option>
                    <option value="UNPAID">UNPAID</option>
                    <option value="PAID">PAID</option>
                  </select>
                </div>
              </div>

              {/* Orders Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-slate-800/60 text-slate-400 uppercase text-xs">
                    <tr>
                      <th className="px-4 py-3">Order ID</th>
                      <th className="px-4 py-3">Meja</th>
                      <th className="px-4 py-3">Pelanggan</th>
                      <th className="px-4 py-3">Total</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Pembayaran</th>
                      <th className="px-4 py-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {orders.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                          Tidak ada pesanan yang sesuai filter.
                        </td>
                      </tr>
                    ) : (
                      orders.map((ord) => (
                        <tr key={ord.id} className="hover:bg-slate-800/30">
                          <td className="px-4 py-3 font-semibold text-slate-200">#{ord.id}</td>
                          <td className="px-4 py-3">Meja {ord.table_id}</td>
                          <td className="px-4 py-3">Cust #{ord.customer_id}</td>
                          <td className="px-4 py-3 font-medium">Rp {ord.total_amount.toLocaleString('id-ID')}</td>
                          <td className="px-4 py-3">
                            <span
                              className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                                ord.status === 'ORDERED'
                                  ? 'bg-amber-500/10 text-amber-400'
                                  : ord.status === 'IN_PROGRESS'
                                  ? 'bg-blue-500/10 text-blue-400'
                                  : 'bg-emerald-500/10 text-emerald-400'
                              }`}
                            >
                              {ord.status}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center space-x-2">
                              <span
                                className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                                  ord.payment_status === 'PAID'
                                    ? 'bg-emerald-500/10 text-emerald-400'
                                    : 'bg-red-500/10 text-red-400'
                                }`}
                              >
                                {ord.payment_status}
                              </span>
                              {ord.is_overdue && (
                                <span className="text-xs px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20">
                                  Overdue
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right space-x-2">
                            {ord.status === 'ORDERED' && (
                              <button
                                onClick={() => handleAdvanceOrderStatus(ord.id, 'IN_PROGRESS')}
                                className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-2.5 py-1 rounded font-medium transition"
                              >
                                Proses
                              </button>
                            )}
                            {ord.status === 'IN_PROGRESS' && (
                              <button
                                onClick={() => handleAdvanceOrderStatus(ord.id, 'DONE')}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-2.5 py-1 rounded font-medium transition"
                              >
                                Selesai (DONE)
                              </button>
                            )}
                            {ord.payment_status === 'UNPAID' && (
                              <button
                                onClick={() => handleMarkPaid(ord.id)}
                                className="bg-amber-500 hover:bg-amber-600 text-slate-950 text-xs px-2.5 py-1 rounded font-semibold transition"
                              >
                                Bayar (PAID)
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* MENU TAB */}
          {activeTab === 'menu' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <p className="text-sm text-slate-400">Daftar item menu terdaftar di PostgreSQL.</p>
                <button
                  onClick={() => setShowAddMenuModal(true)}
                  className="flex items-center space-x-2 bg-amber-500 hover:bg-amber-600 text-slate-950 px-3.5 py-2 rounded-lg text-sm font-semibold transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Tambah Menu</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {menuItems.map((item) => (
                  <div
                    key={item.id}
                    className={`bg-slate-900 border rounded-xl p-4 flex flex-col justify-between ${
                      item.is_available ? 'border-slate-800' : 'border-red-900/40 opacity-75'
                    }`}
                  >
                    <div>
                      <div className="flex justify-between items-start">
                        <h4 className="font-semibold text-slate-200 text-base">{item.name}</h4>
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            item.is_available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                          }`}
                        >
                          {item.is_available ? 'Tersedia' : 'Habis'}
                        </span>
                      </div>
                      <div className="text-xs text-amber-400 font-medium mt-1">
                        Rp {item.price.toLocaleString('id-ID')}
                      </div>
                      <p className="text-xs text-slate-400 mt-2 line-clamp-2">
                        {item.description || 'Tidak ada deskripsi.'}
                      </p>
                    </div>

                    <div className="pt-4 mt-4 border-t border-slate-800 flex justify-between items-center">
                      <button
                        onClick={() => handleToggleMenuAvailability(item.id, item.is_available)}
                        className="text-xs text-slate-300 hover:text-white underline"
                      >
                        Ubah status: {item.is_available ? 'Tandai Habis' : 'Tandai Tersedia'}
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
              <p className="text-sm text-slate-400">
                Data personalisasi, alergi/pantangan, dan preferensi pelanggan (Read-Only).
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {customers.map((c) => (
                  <div key={c.id} className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex justify-between items-center">
                    <div>
                      <div className="font-semibold text-slate-200">
                        {c.first_name || 'Customer'} {c.last_name || ''}
                      </div>
                      <div className="text-xs text-slate-400">
                        Telegram ID: {c.telegram_id} • @{c.username || 'unknown'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleViewCustomerMemory(c.id)}
                      className="bg-slate-800 hover:bg-slate-700 text-amber-400 text-xs px-3 py-1.5 rounded-lg font-medium transition"
                    >
                      Lihat Memori
                    </button>
                  </div>
                ))}
              </div>

              {/* Memory Modal */}
              {selectedCustomerMemory && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full max-h-[85vh] overflow-y-auto space-y-4">
                    <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                      <h3 className="font-bold text-slate-100">
                        Memori Pelanggan #{selectedCustomerMemory.customer_id}
                      </h3>
                      <button
                        onClick={() => setSelectedCustomerMemory(null)}
                        className="text-slate-400 hover:text-white"
                      >
                        ✕
                      </button>
                    </div>

                    <div>
                      <h4 className="text-xs font-semibold uppercase text-amber-400 mb-1">Preferensi (Likes)</h4>
                      {selectedCustomerMemory.memories.preference.length === 0 ? (
                        <p className="text-xs text-slate-500">Tidak ada catatan preferensi.</p>
                      ) : (
                        <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                          {selectedCustomerMemory.memories.preference.map((m) => (
                            <li key={m.id}>{m.description}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div>
                      <h4 className="text-xs font-semibold uppercase text-red-400 mb-1">Tidak Disukai (Dislikes)</h4>
                      {selectedCustomerMemory.memories.dislike.length === 0 ? (
                        <p className="text-xs text-slate-500">Tidak ada catatan dislikes.</p>
                      ) : (
                        <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                          {selectedCustomerMemory.memories.dislike.map((m) => (
                            <li key={m.id}>{m.description}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div>
                      <h4 className="text-xs font-semibold uppercase text-orange-400 mb-1">Pantangan / Alergi (Dietary)</h4>
                      {selectedCustomerMemory.memories.dietary.length === 0 ? (
                        <p className="text-xs text-slate-500">Tidak ada pantangan makanan.</p>
                      ) : (
                        <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                          {selectedCustomerMemory.memories.dietary.map((m) => (
                            <li key={m.id}>{m.description}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div>
                      <h4 className="text-xs font-semibold uppercase text-emerald-400 mb-1">Menu Favorit</h4>
                      {selectedCustomerMemory.favorites.length === 0 ? (
                        <p className="text-xs text-slate-500">Belum ada menu favorit.</p>
                      ) : (
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {selectedCustomerMemory.favorites.map((f) => (
                            <span key={f.menu_id} className="text-xs bg-slate-800 text-slate-200 px-2 py-1 rounded">
                              ★ {f.name}
                            </span>
                          ))}
                        </div>
                      )}
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
