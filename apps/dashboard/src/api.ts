const API_BASE = '/api';

export interface AdminUser {
  id: number;
  username: string;
  role: string;
  full_name?: string;
  is_active: boolean;
}

export interface OrderItem {
  id: number;
  menu_item_id: number;
  name?: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  notes?: string;
}

export interface Order {
  id: number;
  customer_id: number;
  dining_session_id: number;
  table_id: number;
  status: 'ORDERED' | 'IN_PROGRESS' | 'DONE';
  payment_status: 'UNPAID' | 'PAID';
  total_amount: number;
  is_overdue: boolean;
  payment_due_at?: string;
  completed_at?: string;
  created_at: string;
  items: OrderItem[];
}

export interface MenuItem {
  id: number;
  category_id?: number;
  category_name?: string;
  name: string;
  description?: string;
  price: number;
  is_available: boolean;
  created_at: string;
}

export interface MenuCategory {
  id: number;
  name: string;
  description?: string;
}

export interface CustomerMemoryProfile {
  customer_id: number;
  telegram_id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  created_at: string;
  memories: {
    preference: Array<{ id: number; description: string; created_at?: string }>;
    dislike: Array<{ id: number; description: string; created_at?: string }>;
    dietary: Array<{ id: number; description: string; created_at?: string }>;
    note: Array<{ id: number; description: string; created_at?: string }>;
  };
  favorites: Array<{
    menu_id: number;
    name: string;
    price: number;
    category?: string;
    is_available: boolean;
  }>;
}

export interface PopularMenuItem {
  menu_item_id: number;
  name: string;
  category?: string;
  total_quantity_ordered: number;
  total_revenue: number;
}

export interface TableUsage {
  table_id: number;
  table_number: string;
  capacity: number;
  total_sessions: number;
}

export interface ActiveCustomerInfo {
  customer_id: number;
  telegram_id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
}

export interface ActiveSessionInfo {
  session_id: number;
  started_at: string;
  last_order_completed_at?: string;
  customer?: ActiveCustomerInfo;
}

export interface TableLayout {
  id: number;
  table_number: string;
  status: 'AVAILABLE' | 'OCCUPIED';
  capacity: number;
  position_x: number;
  position_y: number;
  is_active: boolean;
  qr_code_token: string;
  deep_link_url: string;
  created_at: string;
  active_session?: ActiveSessionInfo;
}

export interface TableQRInfo {
  table_id: number;
  table_number: string;
  qr_code_token: string;
  deep_link_url: string;
}

class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('admin_token');
  }

  setToken(token: string) {
    localStorage.setItem('admin_token', token);
  }

  clearToken() {
    localStorage.removeItem('admin_token');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.dispatchEvent(new Event('auth:unauthorized'));
      throw new Error('Session expired or unauthorized');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorData.detail || 'Request failed');
    }

    return response.json();
  }

  // Auth
  async login(username: string, password: string) {
    const data = await this.request<{ access_token: string; username: string; role: string; full_name?: string }>(
      '/admin/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }
    );
    this.setToken(data.access_token);
    return data;
  }

  async getMe() {
    return this.request<AdminUser>('/admin/auth/me');
  }

  // Tables
  async listTables(includeInactive: boolean = true) {
    return this.request<TableLayout[]>(`/admin/tables?include_inactive=${includeInactive}`);
  }

  async createTable(payload: { table_number: string; capacity: number; position_x?: number; position_y?: number }) {
    return this.request<TableLayout>('/admin/tables', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateTable(id: number, payload: { table_number?: string; capacity?: number }) {
    return this.request<TableLayout>(`/admin/tables/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async updateTablePosition(id: number, position_x: number, position_y: number) {
    return this.request<TableLayout>(`/admin/tables/${id}/position`, {
      method: 'PATCH',
      body: JSON.stringify({ position_x, position_y }),
    });
  }

  async deactivateTable(id: number) {
    return this.request<{ id: number; action: string; message: string }>(`/admin/tables/${id}`, {
      method: 'DELETE',
    });
  }

  async getTableQR(id: number) {
    return this.request<TableQRInfo>(`/admin/tables/${id}/qr`);
  }

  // Orders
  async listOrders(status?: string, payment_status?: string) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (payment_status) params.append('payment_status', payment_status);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<Order[]>(`/admin/orders${qs}`);
  }

  async updateOrderStatus(orderId: number, status: 'IN_PROGRESS' | 'DONE') {
    return this.request<Order>(`/admin/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async markOrderPaid(orderId: number) {
    return this.request<Order>(`/admin/orders/${orderId}/pay`, {
      method: 'POST',
    });
  }

  // Menu & Categories
  async listCategories() {
    return this.request<MenuCategory[]>('/admin/categories');
  }

  async createCategory(name: string, description?: string) {
    return this.request<MenuCategory>('/admin/categories', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  }

  async updateCategory(id: number, name: string, description?: string) {
    return this.request<MenuCategory>(`/admin/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description }),
    });
  }

  async deleteCategory(id: number) {
    return this.request<{ id: number; action: string }>(`/admin/categories/${id}`, {
      method: 'DELETE',
    });
  }

  async listMenuItems(categoryId?: number) {
    const qs = categoryId ? `?category_id=${categoryId}` : '';
    return this.request<MenuItem[]>(`/admin/menu/items${qs}`);
  }

  async createMenuItem(item: { name: string; price: number; category_id?: number; description?: string; is_available?: boolean }) {
    return this.request<MenuItem>('/admin/menu/items', {
      method: 'POST',
      body: JSON.stringify(item),
    });
  }

  async updateMenuItem(id: number, item: Partial<{ name: string; price: number; category_id: number; description: string; is_available: boolean }>) {
    return this.request<MenuItem>(`/admin/menu/items/${id}`, {
      method: 'PUT',
      body: JSON.stringify(item),
    });
  }

  async setMenuItemAvailability(id: number, is_available: boolean) {
    return this.request<MenuItem>(`/admin/menu/items/${id}/availability`, {
      method: 'PATCH',
      body: JSON.stringify({ is_available }),
    });
  }

  async deleteMenuItem(id: number) {
    return this.request<{ id: number; action: string }>(`/admin/menu/items/${id}`, {
      method: 'DELETE',
    });
  }

  // Customers & Memory
  async listCustomers() {
    return this.request<Array<{ id: number; telegram_id: number; username?: string; first_name?: string; last_name?: string; created_at: string }>>('/admin/customers');
  }

  async getCustomerMemory(customerId: number) {
    return this.request<CustomerMemoryProfile>(`/admin/customers/${customerId}/memory`);
  }

  // Analytics
  async getPopularMenu() {
    return this.request<PopularMenuItem[]>('/admin/analytics/popular-menu');
  }

  async getTableUsage() {
    return this.request<TableUsage[]>('/admin/analytics/table-usage');
  }
}

export const api = new ApiClient();
