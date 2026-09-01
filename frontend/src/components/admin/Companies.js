import React from 'react';
import { Building2, Plus, Search, Pencil, Trash2, X } from 'lucide-react';
import { API_BASE_URL } from '../../utils/apiConfig';
import './Companies.css';

const EMPTY = { name: '', company_code: '', description: '', status: 'active' };

const Companies = () => {
  const [items, setItems] = React.useState([]);
  const [query, setQuery] = React.useState('');
  const [editing, setEditing] = React.useState(null);
  const [form, setForm] = React.useState(EMPTY);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');

  const load = React.useCallback(async () => {
    try {
      setError('');
      const res = await fetch(`${API_BASE_URL}/api/companies/`);
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Unable to load companies');
      const data = await res.json();
      setItems(Array.isArray(data) ? data : data.companies || []);
    } catch (e) { setError(e.message); }
  }, []);

  React.useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing('new'); setForm(EMPTY); setError(''); };
  const openEdit = (item) => {
    setEditing(item.id || item.company_id);
    setForm({
      name: item.name || '', company_code: item.company_code || item.code || '',
      description: item.description || '', status: item.status || 'active'
    });
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return setError('Company name is required.');
    setBusy(true); setError('');
    try {
      const isNew = editing === 'new';
      const url = isNew ? `${API_BASE_URL}/api/companies/` : `${API_BASE_URL}/api/companies/${editing}`;
      const res = await fetch(url, { method: isNew ? 'POST' : 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(form) });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Unable to save company');
      setEditing(null); setForm(EMPTY); await load();
    } catch(e) { setError(e.message); } finally { setBusy(false); }
  };

  const remove = async (item) => {
    const id = item.id || item.company_id;
    if (!window.confirm(`Delete ${item.name || id}? This removes tenant data using the backend cleanup policy.`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/companies/${id}`, {method:'DELETE'});
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Delete failed');
      await load();
    } catch(e) { setError(e.message); }
  };

  const filtered = items.filter(i => `${i.name||''} ${i.company_code||i.code||''} ${i.id||i.company_id||''}`.toLowerCase().includes(query.toLowerCase()));

  return <section className="companies-page">
    <div className="premium-page-toolbar">
      <div><h2>Companies</h2><p>Manage tenant organizations and isolated recognition workspaces.</p></div>
      <button className="premium-primary-btn" onClick={openCreate}><Plus size={16}/> Add company</button>
    </div>
    <div className="premium-table-shell">
      <div className="premium-table-tools"><div className="premium-search"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search companies"/></div><span>{filtered.length} companies</span></div>
      {error && <div className="premium-alert error">{error}</div>}
      <div className="premium-table-scroll"><table className="premium-table"><thead><tr><th>Company</th><th>Code</th><th>Tenant ID</th><th>Status</th><th className="actions">Actions</th></tr></thead><tbody>
        {filtered.map(item => { const id=item.id||item.company_id; return <tr key={id}><td><div className="company-name"><span><Building2 size={15}/></span><div><strong>{item.name||'Unnamed company'}</strong><small>{item.description||'Recognition tenant'}</small></div></div></td><td>{item.company_code||item.code||'—'}</td><td><code>{id}</code></td><td><span className={`status-chip ${item.status==='inactive'?'inactive':''}`}>{item.status||'active'}</span></td><td className="actions"><button onClick={()=>openEdit(item)} title="Edit"><Pencil size={15}/></button><button className="danger" onClick={()=>remove(item)} title="Delete"><Trash2 size={15}/></button></td></tr> })}
        {!filtered.length && <tr><td colSpan="5" className="empty-row">No companies match this search.</td></tr>}
      </tbody></table></div>
    </div>
    {editing && <div className="premium-modal-backdrop"><form className="premium-modal" onSubmit={save}><div className="premium-modal-header"><div><h3>{editing==='new'?'Add company':'Edit company'}</h3><p>Company data remains isolated by tenant ID.</p></div><button type="button" onClick={()=>setEditing(null)}><X size={18}/></button></div><div className="premium-form-grid"><label>Company name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required/></label><label>Company code<input value={form.company_code} onChange={e=>setForm({...form,company_code:e.target.value})}/></label><label className="full">Description<textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})} rows="3"/></label><label>Status<select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}><option value="active">Active</option><option value="inactive">Inactive</option></select></label></div>{error&&<div className="premium-alert error">{error}</div>}<div className="premium-modal-actions"><button type="button" className="premium-secondary-btn" onClick={()=>setEditing(null)}>Cancel</button><button className="premium-primary-btn" disabled={busy}>{busy?'Saving…':'Save company'}</button></div></form></div>}
  </section>;
};
export default Companies;
