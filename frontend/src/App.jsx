import { useState, useEffect, useRef } from 'react';
import './App.css';

// Base API URL configuration, defaults to local Django port
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/';

function App() {
  // Authentication & Session States
  const [token, setToken] = useState(localStorage.getItem('spritai_token') || '');
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('spritai_refresh_token') || '');
  const [user, setUser] = useState(null);
  
  // Data States
  const [groups, setGroups] = useState([]);
  const [users, setUsers] = useState([]);
  const [activeGroup, setActiveGroup] = useState(null);
  const [activeGroupBalances, setActiveGroupBalances] = useState({ balances: [], transactions: [] });
  const [expenses, setExpenses] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [activeExpense, setActiveExpense] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);

  // Form & UI States
  const [isLoginView, setIsLoginView] = useState(true);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authName, setAuthName] = useState('');
  const [authError, setAuthError] = useState('');

  // Modals Toggle States
  const [showAddGroup, setShowAddGroup] = useState(false);
  const [showAddExpense, setShowAddExpense] = useState(false);
  const [showAddSettlement, setShowAddSettlement] = useState(false);

  // Group Create Form States
  const [newGroupName, setNewGroupName] = useState('');
  const [selectedGroupMembers, setSelectedGroupMembers] = useState([]);

  // Settlement Form States
  const [settlementFrom, setSettlementFrom] = useState('');
  const [settlementTo, setSettlementTo] = useState('');
  const [settlementAmount, setSettlementAmount] = useState('');
  const [settlementDate, setSettlementDate] = useState(new Date().toISOString().split('T')[0]);
  const [settlementError, setSettlementError] = useState('');

  // Expense Form States
  const [expenseDesc, setExpenseDesc] = useState('');
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().split('T')[0]);
  const [expensePayer, setExpensePayer] = useState('');
  const [expenseSplitType, setExpenseSplitType] = useState('equal');
  // State mapping participant user.id -> input value (raw_input_value)
  const [participantShares, setParticipantShares] = useState({});
  // Checklist for equal split (user.id -> boolean)
  const [participantSelection, setParticipantSelection] = useState({});
  const [expenseError, setExpenseError] = useState('');

  // Chat/Timeline posting state
  const [newCommentText, setNewCommentText] = useState('');
  const chatEndRef = useRef(null);

  // Fetch helper with JWT inclusion and automatic 401 handling
  const fetchWithAuth = async (endpoint, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    let res = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && refreshToken) {
      // Try token refresh under deadline
      try {
        const refreshRes = await fetch(`${API_URL}auth/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh: refreshToken }),
        });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          localStorage.setItem('spritai_token', refreshData.access);
          setToken(refreshData.access);
          
          // Retry the request
          headers['Authorization'] = `Bearer ${refreshData.access}`;
          res = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers,
          });
        } else {
          handleLogout();
        }
      } catch (err) {
        handleLogout();
      }
    }
    return res;
  };

  // Perform startup auth state check
  useEffect(() => {
    if (token) {
      fetchWithAuth('auth/me/')
        .then(async (res) => {
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
          } else {
            handleLogout();
          }
        })
        .catch(() => handleLogout());
    }
  }, [token]);

  // Load baseline app lists when authenticated
  useEffect(() => {
    if (user) {
      loadGroups();
      loadUsers();
    }
  }, [user]);

  // Polling loop for active group stats (expenses, settlements, balances)
  useEffect(() => {
    if (user && activeGroup) {
      loadGroupStats();
      const interval = setInterval(() => {
        loadGroupStats();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [user, activeGroup]);

  // Polling loop for comments of active expense
  useEffect(() => {
    if (user && activeExpense) {
      loadComments();
      const interval = setInterval(() => {
        loadComments();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [user, activeExpense]);

  // Scroll chat window to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const loadGroups = async () => {
    const res = await fetchWithAuth('groups/');
    if (res.ok) {
      const data = await res.json();
      setGroups(data);
    }
  };

  const loadUsers = async () => {
    const res = await fetchWithAuth('users/');
    if (res.ok) {
      const data = await res.json();
      setUsers(data);
    }
  };

  const loadGroupStats = async () => {
    if (!activeGroup) return;
    
    // Fetch group details, balances, expenses, and settlements in parallel
    const [balRes, expRes, setRes] = await Promise.all([
      fetchWithAuth(`groups/${activeGroup.id}/balances/`),
      fetchWithAuth(`expenses/?group=${activeGroup.id}`),
      fetchWithAuth(`settlements/?group=${activeGroup.id}`)
    ]);

    if (balRes.ok) {
      const data = await balRes.json();
      setActiveGroupBalances(data);
    }
    if (expRes.ok) {
      const data = await expRes.json();
      // Filter expenses client side to belong strictly to activeGroup
      const groupExpenses = data.filter(e => e.group === activeGroup.id);
      setExpenses(groupExpenses);
    }
    if (setRes.ok) {
      const data = await setRes.json();
      // Filter settlements client side to belong strictly to activeGroup
      const groupSettlements = data.filter(s => s.group === activeGroup.id);
      setSettlements(groupSettlements);
    }
  };

  const loadComments = async () => {
    if (!activeExpense) return;
    const res = await fetchWithAuth(`chat-messages/?expense=${activeExpense.id}`);
    if (res.ok) {
      const data = await res.json();
      setChatMessages(data);
    }
  };

  // Auth form submissions
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');

    if (isLoginView) {
      // Login flow
      try {
        const res = await fetch(`${API_URL}auth/login/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPassword }),
        });
        const data = await res.json();
        if (res.ok) {
          localStorage.setItem('spritai_token', data.access);
          localStorage.setItem('spritai_refresh_token', data.refresh);
          setToken(data.access);
          setRefreshToken(data.refresh);
        } else {
          setAuthError(data.detail || 'Invalid email or password.');
        }
      } catch (err) {
        setAuthError('Server is currently unreachable.');
      }
    } else {
      // Signup flow
      try {
        const res = await fetch(`${API_URL}auth/register/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPassword, name: authName }),
        });
        const data = await res.json();
        if (res.ok) {
          localStorage.setItem('spritai_token', data.access);
          localStorage.setItem('spritai_refresh_token', data.refresh);
          setToken(data.access);
          setRefreshToken(data.refresh);
        } else {
          setAuthError(Object.values(data).join(' '));
        }
      } catch (err) {
        setAuthError('Server is currently unreachable.');
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('spritai_token');
    localStorage.removeItem('spritai_refresh_token');
    setToken('');
    setRefreshToken('');
    setUser(null);
    setGroups([]);
    setActiveGroup(null);
    setActiveExpense(null);
  };

  // Group creation action
  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;

    const res = await fetchWithAuth('groups/', {
      method: 'POST',
      body: JSON.stringify({
        name: newGroupName,
        members: selectedGroupMembers
      })
    });

    if (res.ok) {
      const data = await res.json();
      setNewGroupName('');
      setSelectedGroupMembers([]);
      setShowAddGroup(false);
      loadGroups();
      setActiveGroup(data);
    }
  };

  // Settlement creation action
  const handleCreateSettlement = async (e) => {
    e.preventDefault();
    setSettlementError('');

    if (!settlementFrom || !settlementTo || !settlementAmount) {
      setSettlementError('All fields are required.');
      return;
    }

    const res = await fetchWithAuth('settlements/', {
      method: 'POST',
      body: JSON.stringify({
        group: activeGroup.id,
        from_user: parseInt(settlementFrom),
        to_user: parseInt(settlementTo),
        amount: settlementAmount,
        date: settlementDate
      })
    });

    if (res.ok) {
      setSettlementAmount('');
      setShowAddSettlement(false);
      loadGroupStats();
    } else {
      const errData = await res.json();
      setSettlementError(Object.values(errData).flat().join(' '));
    }
  };

  // Initialize Split configuration values when Expense modal is loaded
  useEffect(() => {
    if (showAddExpense && activeGroup) {
      // Default payer is the current user if they are in the group, otherwise first member
      const isUserInGroup = activeGroup.members_detail.some(m => m.id === user?.id);
      setExpensePayer(isUserInGroup ? user.id : activeGroup.members_detail[0]?.id);
      
      // Initialize participant selection (true for all members)
      const select = {};
      activeGroup.members_detail.forEach(m => {
        select[m.id] = true;
      });
      setParticipantSelection(select);

      // Reset values
      setParticipantShares({});
      setExpenseAmount('');
      setExpenseDesc('');
      setExpenseError('');
    }
  }, [showAddExpense, activeGroup]);

  // Expense creation action
  const handleCreateExpense = async (e) => {
    e.preventDefault();
    setExpenseError('');

    if (!expenseDesc || !expenseAmount || !expensePayer) {
      setExpenseError('Description, Amount, and Payer are required.');
      return;
    }

    // Build the shares array payload
    let shares = [];

    if (expenseSplitType === 'equal') {
      const activeMemberIds = Object.keys(participantSelection).filter(id => participantSelection[id]);
      if (activeMemberIds.length === 0) {
        setExpenseError('Please select at least one participant.');
        return;
      }
      shares = activeMemberIds.map(id => ({ user: parseInt(id) }));
    } else {
      // For unequal, percentage, share
      const list = activeGroup.members_detail.map(m => {
        const val = participantShares[m.id];
        return {
          user: m.id,
          raw_input_value: val ? parseFloat(val) : 0
        };
      });

      // Validations
      if (expenseSplitType === 'unequal') {
        const sum = list.reduce((a, b) => a + b.raw_input_value, 0);
        if (Math.abs(sum - parseFloat(expenseAmount)) > 0.01) {
          setExpenseError(`Unequal amounts sum to ${sum.toFixed(2)}, but must equal the total of ${expenseAmount}`);
          return;
        }
      }
      if (expenseSplitType === 'percentage') {
        const sum = list.reduce((a, b) => a + b.raw_input_value, 0);
        if (sum === 0) {
          setExpenseError('Total percentage cannot be zero.');
          return;
        }
      }
      if (expenseSplitType === 'share') {
        const sum = list.reduce((a, b) => a + b.raw_input_value, 0);
        if (sum === 0) {
          setExpenseError('Total shares cannot be zero.');
          return;
        }
      }
      shares = list;
    }

    const res = await fetchWithAuth('expenses/', {
      method: 'POST',
      body: JSON.stringify({
        group: activeGroup.id,
        payer: parseInt(expensePayer),
        amount: expenseAmount,
        description: expenseDesc,
        date: expenseDate,
        split_type: expenseSplitType,
        shares
      })
    });

    if (res.ok) {
      setShowAddExpense(false);
      loadGroupStats();
    } else {
      const errData = await res.json();
      setExpenseError(Object.values(errData).flat().join(' '));
    }
  };

  // Delete Expense action
  const handleDeleteExpense = async (id) => {
    if (!window.confirm("Are you sure you want to delete this expense?")) return;
    const res = await fetchWithAuth(`expenses/${id}/`, {
      method: 'DELETE'
    });
    if (res.ok) {
      if (activeExpense?.id === id) {
        setActiveExpense(null);
      }
      loadGroupStats();
    }
  };

  // Chat timelines post comment action
  const handlePostComment = async (e) => {
    e.preventDefault();
    if (!newCommentText.trim() || !activeExpense) return;

    const res = await fetchWithAuth('chat-messages/', {
      method: 'POST',
      body: JSON.stringify({
        expense: activeExpense.id,
        text: newCommentText
      })
    });

    if (res.ok) {
      setNewCommentText('');
      loadComments();
    }
  };

  // Auth form components
  if (!user) {
    return (
      <div className="auth-container">
        <div className="auth-card glass">
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <h1 style={{ fontSize: '28px', color: '#ffffff', letterSpacing: '-0.5px' }}>Spritai</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
              {isLoginView ? 'Login to continue splits' : 'Create a split account'}
            </p>
          </div>

          <form onSubmit={handleAuthSubmit}>
            {!isLoginView && (
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  placeholder="Your name"
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  required
                />
              </div>
            )}
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                placeholder="name@example.com"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                required
              />
            </div>

            {authError && (
              <p style={{ color: 'var(--color-danger)', fontSize: '13px', marginBottom: '16px' }}>
                {authError}
              </p>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }}>
              {isLoginView ? 'Log In' : 'Sign Up'}
            </button>
          </form>

          <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            {isLoginView ? "Don't have an account? " : "Already have an account? "}
            <span
              style={{ color: 'var(--color-primary)', cursor: 'pointer', fontWeight: 500 }}
              onClick={() => {
                setIsLoginView(!isLoginView);
                setAuthError('');
              }}
            >
              {isLoginView ? 'Sign up' : 'Log in'}
            </span>
          </p>
        </div>
      </div>
    );
  }

  // Dashboard interface
  return (
    <div className="app-layout">
      {/* Top Navbar */}
      <nav className="navbar">
        <span className="navbar-brand">Spritai</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Logged in as <strong>{user.name || user.email}</strong>
          </span>
          <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '12px' }}>
            Log Out
          </button>
        </div>
      </nav>

      {/* Main Grid content */}
      <main className="main-content">
        <div className="dashboard-container">
          
          {/* Sidebar Area */}
          <aside className="sidebar">
            {/* Groups Card */}
            <div className="card glass">
              <div className="card-title">
                <span>Groups</span>
                <button
                  onClick={() => {
                    setSelectedGroupMembers([user.id]); // Default creator is selected
                    setShowAddGroup(true);
                  }}
                  className="btn btn-primary"
                  style={{ padding: '4px 10px', fontSize: '11px' }}
                >
                  + New
                </button>
              </div>

              {groups.length === 0 ? (
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                  No groups yet.
                </p>
              ) : (
                groups.map(g => (
                  <div
                    key={g.id}
                    className={`list-item ${activeGroup?.id === g.id ? 'active' : ''}`}
                    onClick={() => {
                      setActiveGroup(g);
                      setActiveExpense(null);
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <div>
                      <div style={{ fontWeight: 500, fontSize: '14px' }}>{g.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {g.members_detail.length} members
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Users / Roommates list card */}
            <div className="card glass">
              <div className="card-title">Roommates</div>
              {users.map(u => (
                <div key={u.id} className="list-item" style={{ padding: '10px 14px' }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '13px', color: '#ffffff' }}>{u.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{u.email}</div>
                  </div>
                </div>
              ))}
            </div>
          </aside>

          {/* Central Workspace */}
          <section>
            {!activeGroup ? (
              <div className="card glass landing-hero">
                <h1>Welcome to Spritai</h1>
                <p>
                  Settle balances, track flat expenses, and split shares easily. Select a group from the sidebar to view transactions or create one to begin.
                </p>
                <button
                  onClick={() => {
                    setSelectedGroupMembers([user.id]);
                    setShowAddGroup(true);
                  }}
                  className="btn btn-primary"
                >
                  Create new group
                </button>
              </div>
            ) : (
              <div className="grid">
                {/* Active Group Banner Info */}
                <div className="card glass" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h2 style={{ fontSize: '22px' }}>{activeGroup.name}</h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '4px' }}>
                      Members: {activeGroup.members_detail.map(m => m.name || m.email).join(', ')}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => setShowAddSettlement(true)} className="btn btn-secondary">
                      Settle Debt
                    </button>
                    <button onClick={() => setShowAddExpense(true)} className="btn btn-accent">
                      + Add Expense
                    </button>
                  </div>
                </div>

                {/* Subgrid layout: Left column balances, Right column expenses */}
                <div className="grid grid-cols-2">
                  
                  {/* Left Column: balances and simplified who owes whom */}
                  <div className="sidebar">
                    <div className="card glass">
                      <div className="card-title">Net Balances</div>
                      {activeGroupBalances.balances.map(b => (
                        <div key={b.user.id} className="list-item">
                          <span style={{ fontSize: '13px' }}>{b.user.name}</span>
                          <span className={b.net_balance > 0.01 ? 'bal-positive' : b.net_balance < -0.01 ? 'bal-negative' : 'bal-zero'}>
                            {b.net_balance > 0.01 ? `+₹${b.net_balance.toFixed(2)}` : b.net_balance < -0.01 ? `-₹${Math.abs(b.net_balance).toFixed(2)}` : '₹0.00'}
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className="card glass">
                      <div className="card-title">Who Owes Whom (Simplified)</div>
                      {activeGroupBalances.transactions.length === 0 ? (
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
                          Everything is fully settled!
                        </p>
                      ) : (
                        activeGroupBalances.transactions.map((tx, idx) => (
                          <div key={idx} className="list-item" style={{ background: 'rgba(245, 158, 11, 0.05)', borderColor: 'rgba(245, 158, 11, 0.2)' }}>
                            <span style={{ fontSize: '13px' }}>
                              <strong>{tx.from_user.name}</strong> owes <strong>{tx.to_user.name}</strong>
                            </span>
                            <span style={{ color: 'var(--color-warning)', fontWeight: 600 }}>
                              ₹{tx.amount.toFixed(2)}
                            </span>
                          </div>
                        ))
                      )}
                    </div>

                    <div className="card glass">
                      <div className="card-title">Recent Settlements</div>
                      {settlements.length === 0 ? (
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
                          No settlements recorded.
                        </p>
                      ) : (
                        settlements.map(s => (
                          <div key={s.id} className="settlement-card">
                            <div style={{ fontSize: '12px' }}>
                              <strong>{s.from_user_detail.name}</strong> paid <strong>{s.to_user_detail.name}</strong>
                              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{s.date}</div>
                            </div>
                            <span style={{ fontWeight: 600, color: 'var(--color-accent)' }}>₹{parseFloat(s.amount).toFixed(2)}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Right Column: Expense Timeline list */}
                  <div>
                    <div className="card glass" style={{ minHeight: '400px' }}>
                      <div className="card-title">Expenses Timeline</div>
                      {expenses.length === 0 ? (
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
                          No expenses in this group yet. Click '+ Add Expense' to log one.
                        </p>
                      ) : (
                        expenses.map(e => {
                          const isExpanded = activeExpense?.id === e.id;
                          return (
                            <div key={e.id} className="list-item glass expense-card" style={{ display: 'block', padding: '0px' }}>
                              <div className="expense-main" style={{ padding: '16px' }} onClick={() => {
                                if (isExpanded) {
                                  setActiveExpense(null);
                                } else {
                                  setActiveExpense(e);
                                  setChatMessages([]);
                                }
                              }}>
                                <div className="expense-details">
                                  <div className="expense-date-badge">
                                    <div style={{ fontWeight: 700 }}>{e.date.split('-')[2]}</div>
                                    <div style={{ fontSize: '9px', textTransform: 'uppercase' }}>
                                      {new Date(e.date).toLocaleString('default', { month: 'short' })}
                                    </div>
                                  </div>
                                  <div className="expense-info">
                                    <h3>{e.description}</h3>
                                    <div className="expense-meta">
                                      Paid by <strong>{e.payer_detail.name}</strong> • split <span style={{ textTransform: 'capitalize' }}>{e.split_type}</span>
                                    </div>
                                  </div>
                                </div>
                                <div className="expense-amount-side">
                                  <div className="expense-total-amount">₹{parseFloat(e.amount).toFixed(2)}</div>
                                  <button
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      handleDeleteExpense(e.id);
                                    }}
                                    className="btn btn-danger"
                                    style={{ padding: '2px 8px', fontSize: '10px', marginTop: '6px', borderRadius: '4px' }}
                                  >
                                    Delete
                                  </button>
                                </div>
                              </div>

                              {/* Expanded Panel showing detail splits and polling comments timeline */}
                              {isExpanded && (
                                <div style={{ padding: '16px', background: 'rgba(15, 23, 42, 0.3)', borderTop: '1px solid var(--bg-border)' }}>
                                  <h4 style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Split Details</h4>
                                  <div className="expense-shares-summary">
                                    {e.shares.map(sh => (
                                      <div key={sh.id} className="share-pill">
                                        <span>{sh.user_detail.name}</span>
                                        <strong>
                                          ₹{parseFloat(sh.owed_amount).toFixed(2)}
                                          {sh.raw_input_value !== null && e.split_type !== 'equal' && (
                                            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 'normal', marginLeft: '4px' }}>
                                              ({parseFloat(sh.raw_input_value)}{e.split_type === 'percentage' ? '%' : e.split_type === 'share' ? 'sh' : ''})
                                            </span>
                                          )}
                                        </strong>
                                      </div>
                                    ))}
                                  </div>

                                  {/* Comments system timeline inside expanded view */}
                                  <div className="chat-container">
                                    <h4 style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', borderTop: '1px solid var(--bg-border)', paddingTop: '12px' }}>
                                      Timeline Chat
                                    </h4>
                                    <div className="chat-messages">
                                      {chatMessages.length === 0 ? (
                                        <p style={{ color: 'var(--text-muted)', fontSize: '11px', textAlign: 'center', margin: 'auto' }}>
                                          No chat comments yet. Start the discussion!
                                        </p>
                                      ) : (
                                        chatMessages.map(msg => (
                                          <div
                                            key={msg.id}
                                            className={`chat-bubble ${msg.sender === user.id ? 'own' : 'other'}`}
                                          >
                                            <div className="chat-bubble-sender">{msg.sender_detail.name}</div>
                                            <div>{msg.text}</div>
                                            <div className="chat-bubble-time">
                                              {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </div>
                                          </div>
                                        ))
                                      )}
                                      <div ref={chatEndRef} />
                                    </div>
                                    <form onSubmit={handlePostComment} className="chat-input-row">
                                      <input
                                        type="text"
                                        placeholder="Add comment..."
                                        value={newCommentText}
                                        onChange={(e) => setNewCommentText(e.target.value)}
                                        required
                                      />
                                      <button type="submit" className="btn btn-primary" style={{ padding: '8px 16px', fontSize: '13px' }}>
                                        Post
                                      </button>
                                    </form>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>

                </div>
              </div>
            )}
          </section>

        </div>
      </main>

      {/* MODAL: CREATE GROUP */}
      {showAddGroup && (
        <div className="modal-overlay">
          <div className="modal-content glass">
            <h2 style={{ marginBottom: '20px' }}>Create New Group</h2>
            <form onSubmit={handleCreateGroup}>
              <div className="form-group">
                <label>Group Name</label>
                <input
                  type="text"
                  placeholder="e.g. The Flat"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Select Group Members</label>
                <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid var(--bg-border)', padding: '12px', borderRadius: '8px', background: 'rgba(0,0,0,0.2)' }}>
                  {users.map(u => (
                    <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <input
                        type="checkbox"
                        id={`mg-${u.id}`}
                        style={{ width: 'auto' }}
                        checked={selectedGroupMembers.includes(u.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedGroupMembers([...selectedGroupMembers, u.id]);
                          } else {
                            // Creator cannot be removed to keep things clean
                            if (u.id === user.id) return;
                            setSelectedGroupMembers(selectedGroupMembers.filter(id => id !== u.id));
                          }
                        }}
                      />
                      <label htmlFor={`mg-${u.id}`} style={{ margin: 0, color: '#ffffff', cursor: 'pointer' }}>
                        {u.name} ({u.email}) {u.id === user.id ? ' (You)' : ''}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" onClick={() => setShowAddGroup(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RECORD SETTLEMENT */}
      {showAddSettlement && (
        <div className="modal-overlay">
          <div className="modal-content glass">
            <h2 style={{ marginBottom: '20px' }}>Record a Settlement</h2>
            <form onSubmit={handleCreateSettlement}>
              <div className="form-group">
                <label>Payer (Who Paid)</label>
                <select
                  value={settlementFrom}
                  onChange={(e) => setSettlementFrom(e.target.value)}
                  required
                >
                  <option value="">Choose roommate...</option>
                  {activeGroup.members_detail.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Recipient (Who Received)</label>
                <select
                  value={settlementTo}
                  onChange={(e) => setSettlementTo(e.target.value)}
                  required
                >
                  <option value="">Choose roommate...</option>
                  {activeGroup.members_detail.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={settlementAmount}
                  onChange={(e) => setSettlementAmount(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Settlement Date</label>
                <input
                  type="date"
                  value={settlementDate}
                  onChange={(e) => setSettlementDate(e.target.value)}
                  required
                />
              </div>

              {settlementError && (
                <p style={{ color: 'var(--color-danger)', fontSize: '13px', marginBottom: '16px' }}>
                  {settlementError}
                </p>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" onClick={() => setShowAddSettlement(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-accent">
                  Record Settlement
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD EXPENSE */}
      {showAddExpense && (
        <div className="modal-overlay">
          <div className="modal-content glass">
            <h2 style={{ marginBottom: '20px' }}>Add Expense</h2>
            <form onSubmit={handleCreateExpense}>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  placeholder="e.g. Pizza, Rent, Wifi"
                  value={expenseDesc}
                  onChange={(e) => setExpenseDesc(e.target.value)}
                  required
                />
              </div>

              <div className="grid grid-cols-2">
                <div className="form-group">
                  <label>Total Amount (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={expenseAmount}
                    onChange={(e) => setExpenseAmount(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Date</label>
                  <input
                    type="date"
                    value={expenseDate}
                    onChange={(e) => setExpenseDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Paid By</label>
                <select
                  value={expensePayer}
                  onChange={(e) => setExpensePayer(e.target.value)}
                  required
                >
                  {activeGroup.members_detail.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Split Type</label>
                <div className="split-type-selector">
                  {['equal', 'unequal', 'percentage', 'share'].map(type => (
                    <div
                      key={type}
                      className={`split-tab ${expenseSplitType === type ? 'active' : ''}`}
                      onClick={() => setExpenseSplitType(type)}
                    >
                      {type === 'equal' ? 'Equally' : type === 'unequal' ? 'Unequally' : type === 'percentage' ? 'Percent' : 'Shares'}
                    </div>
                  ))}
                </div>
              </div>

              {/* Dynamic split input sections */}
              <div className="split-members-list">
                <h4 style={{ fontSize: '13px', marginBottom: '12px', color: 'var(--text-primary)' }}>Split Details</h4>
                
                {activeGroup.members_detail.map(m => {
                  if (expenseSplitType === 'equal') {
                    // Equally split selection checklist
                    return (
                      <div key={m.id} className="split-member-row">
                        <label htmlFor={`eq-${m.id}`} style={{ cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            id={`eq-${m.id}`}
                            style={{ width: 'auto' }}
                            checked={!!participantSelection[m.id]}
                            onChange={(e) => {
                              setParticipantSelection({
                                ...participantSelection,
                                [m.id]: e.target.checked
                              });
                            }}
                          />
                          {m.name}
                        </label>
                      </div>
                    );
                  } else {
                    // Custom split value inputs
                    return (
                      <div key={m.id} className="split-member-row">
                        <span>{m.name}</span>
                        <div className="split-input-wrapper">
                          <input
                            type="number"
                            step="0.01"
                            placeholder="0"
                            value={participantShares[m.id] || ''}
                            onChange={(e) => {
                              setParticipantShares({
                                ...participantShares,
                                [m.id]: e.target.value
                              });
                            }}
                          />
                          <span className="split-input-suffix">
                            {expenseSplitType === 'percentage' ? '%' : expenseSplitType === 'share' ? 'sh' : '₹'}
                          </span>
                        </div>
                      </div>
                    );
                  }
                })}
              </div>

              {expenseError && (
                <p style={{ color: 'var(--color-danger)', fontSize: '13px', marginBottom: '16px' }}>
                  {expenseError}
                </p>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" onClick={() => setShowAddExpense(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-accent">
                  Add Expense
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
