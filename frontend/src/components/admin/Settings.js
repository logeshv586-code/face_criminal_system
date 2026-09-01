import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Settings as SettingsIcon, Save, ShieldCheck, Mail, Shield, Building2,
  CheckCircle2, AlertCircle, Gauge, Camera, Send, Activity, RefreshCw,
  Eye, EyeOff, Crosshair, TimerReset
} from 'lucide-react';
import useAuthStore from '../../store/authStore';
import { API_BASE_URL } from '../../utils/apiConfig';
import './Settings.css';

const DEFAULTS = {
  max_cameras_per_admin: 10,
  max_cameras_per_supervisor: 5,
  face_recognition_enabled: true,
  show_bounding_boxes: true,
  unknown_detection_enabled: true,
  long_distance_detection_enabled: true,
  min_face_size: 20,
  detection_confidence_target: 0.35,
  recognition_tolerance: 0.55,
  long_range_tolerance: 0.60,
  known_capture_min_confidence: 0.35,
  unknown_capture_min_confidence: 0.45,
  known_capture_interval_seconds: 5,
  unknown_capture_interval_seconds: 12,
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  smtp_password_configured: false,
  smtp_use_tls: true,
  email_from: '',
};

const clamp = (value, min, max) => Math.max(min, Math.min(max, Number(value)));
const pct = value => `${Math.round(Number(value || 0) * 100)}%`;

const ToggleRow = ({ name, checked, onChange, title, description }) => (
  <div className="setting-toggle-row">
    <div className="setting-toggle-copy">
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
    <label className="switch" aria-label={title}>
      <input type="checkbox" name={name} checked={Boolean(checked)} onChange={onChange} />
      <span className="slider round" />
    </label>
  </div>
);

const SliderField = ({ label, name, value, min, max, step, onChange, help, format = pct }) => (
  <div className="slider-field">
    <div className="slider-field-head">
      <label htmlFor={name}>{label}</label>
      <output htmlFor={name}>{format(value)}</output>
    </div>
    <input id={name} name={name} type="range" min={min} max={max} step={step} value={value} onChange={onChange} />
    <small>{help}</small>
  </div>
);

const NumberField = ({ label, name, value, min, max, step = 1, onChange, help, suffix }) => (
  <div className="field-block">
    <label htmlFor={name}>{label}</label>
    <div className="number-input-wrap">
      <input id={name} type="number" name={name} min={min} max={max} step={step} value={value} onChange={onChange} />
      {suffix && <span>{suffix}</span>}
    </div>
    {help && <small>{help}</small>}
  </div>
);

const Settings = () => {
  const { user, token } = useAuthStore();
  const [settings, setSettings] = useState(DEFAULTS);
  const [companies, setCompanies] = useState([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [showSmtpPassword, setShowSmtpPassword] = useState(false);
  const [testRecipient, setTestRecipient] = useState('');
  const [testingEmail, setTestingEmail] = useState(false);

  const authHeaders = useMemo(() => ({
    Authorization: `Bearer ${token || sessionStorage.getItem('auth_token') || ''}`,
  }), [token]);

  const query = user?.role === 'SuperAdmin' && selectedCompanyId
    ? `?cid=${encodeURIComponent(selectedCompanyId)}` : '';

  const loadSettings = useCallback(async () => {
    if (!user || !['SuperAdmin', 'Admin'].includes(user.role)) return;
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/settings/system${query}`, { headers: authHeaders });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Failed to load settings');
      const next = { ...DEFAULTS, ...(data.settings || {}) };
      next.smtp_password = '';
      setSettings(next);
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Unable to connect to the settings service.' });
    } finally {
      setLoading(false);
    }
  }, [user, query, authHeaders]);

  useEffect(() => {
    if (user?.role !== 'SuperAdmin') return;
    (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/companies/`, { headers: authHeaders });
        if (!response.ok) return;
        const data = await response.json();
        setCompanies(data.companies || []);
      } catch (err) {
        console.error('Unable to load companies', err);
      }
    })();
  }, [user?.role, authHeaders]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const update = (e) => {
    const { name, type, checked, value } = e.target;
    let next = type === 'checkbox' ? checked : value;
    if (type === 'number' || type === 'range') next = Number(value);
    setSettings(prev => ({ ...prev, [name]: next }));
  };

  const validate = () => {
    if (settings.long_range_tolerance < settings.recognition_tolerance) {
      return 'Long-distance tolerance should be equal to or higher than the normal recognition tolerance.';
    }
    if (settings.unknown_capture_min_confidence < settings.detection_confidence_target) {
      return 'Unknown capture confidence cannot be lower than the detection confidence target.';
    }
    return null;
  };

  const submit = async (e) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setMessage({ type: 'error', text: validationError });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      const payload = { ...settings };
      delete payload.smtp_password_configured;
      if (!payload.smtp_password) delete payload.smtp_password;
      const response = await fetch(`${API_BASE_URL}/api/users/settings/system${query}`, {
        method: 'PUT',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map(x => x.msg).join(', ') : data.detail;
        throw new Error(detail || 'Failed to save settings');
      }
      setSettings(prev => ({ ...prev, ...(data.settings || {}), smtp_password: '' }));
      setMessage({ type: 'success', text: 'Saved. Live recognition will pick up these values within a few seconds.' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Unable to save settings.' });
    } finally {
      setSaving(false);
    }
  };

  const testEmail = async () => {
    if (!testRecipient || !testRecipient.includes('@')) {
      setMessage({ type: 'error', text: 'Enter a valid test recipient email address.' });
      return;
    }
    setTestingEmail(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/settings/test-email${query}`, {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient: testRecipient,
          smtp_host: settings.smtp_host,
          smtp_port: settings.smtp_port,
          smtp_user: settings.smtp_user,
          smtp_password: settings.smtp_password,
          smtp_use_tls: settings.smtp_use_tls,
          email_from: settings.email_from,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'SMTP test failed');
      setMessage({ type: 'success', text: data.message || 'SMTP test succeeded.' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'SMTP test failed.' });
    } finally {
      setTestingEmail(false);
    }
  };

  if (!user || !['SuperAdmin', 'Admin'].includes(user.role)) {
    return <div className="settings-access-denied"><Shield size={28} /><strong>Access restricted</strong><span>Administrator permission is required.</span></div>;
  }

  return (
    <div className="settings-page-shell">
      <div className="settings-container">
        <div className="settings-header">
          <div>
            <h2><SettingsIcon size={20} /> System Settings</h2>
            <p>Live recognition, capture, camera limits and notification configuration. No unused options are shown.</p>
          </div>
          <div className="settings-header-actions">
            <button type="button" className="settings-refresh" onClick={loadSettings} disabled={loading}><RefreshCw size={14} /> Refresh</button>
            <div className="settings-scope-badge"><Activity size={14} /> {selectedCompanyId || (user.role === 'SuperAdmin' ? 'System Default' : user.company_id || 'Company')}</div>
          </div>
        </div>

        {message && <div className={`settings-message ${message.type}`}>{message.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}<span>{message.text}</span></div>}

        <form onSubmit={submit} className="settings-form">
          {user.role === 'SuperAdmin' && (
            <section className="settings-section scope-section">
              <div className="section-title"><Building2 size={17} /><div><h3>Configuration Target</h3><p>Edit the system default or tune one customer/company separately.</p></div></div>
              <div className="field-block scope-select">
                <label htmlFor="settings-company">Apply settings to</label>
                <select id="settings-company" value={selectedCompanyId} onChange={e => setSelectedCompanyId(e.target.value)}>
                  <option value="">System Default (Global)</option>
                  {companies.map(c => <option key={c.id} value={c.id}>{c.name} ({c.id})</option>)}
                </select>
              </div>
            </section>
          )}

          <div className="settings-main-grid">
            <section className="settings-section recognition-section">
              <div className="section-title"><Crosshair size={17} /><div><h3>Recognition Engine</h3><p>These values are connected directly to live detection and matching.</p></div></div>
              <div className="toggle-list compact-toggle-list">
                <ToggleRow name="face_recognition_enabled" checked={settings.face_recognition_enabled} onChange={update} title="Live recognition" description="Enable detection and identity matching on active streams." />
                <ToggleRow name="long_distance_detection_enabled" checked={settings.long_distance_detection_enabled} onChange={update} title="Long-distance mode" description="Allow small/distant faces and the long-range tolerance." />
              </div>
              <div className="slider-stack">
                <SliderField label="Detection confidence target" name="detection_confidence_target" value={settings.detection_confidence_target} min="0.15" max="0.85" step="0.01" onChange={update} help="Lower detects more candidates; higher rejects weak detector boxes." />
                <SliderField label="Recognition tolerance" name="recognition_tolerance" value={settings.recognition_tolerance} min="0.35" max="0.70" step="0.01" onChange={update} help="Higher is easier to match against augmented gallery references; lower is stricter." />
                <SliderField label="Long-distance tolerance" name="long_range_tolerance" value={settings.long_range_tolerance} min="0.40" max="0.75" step="0.01" onChange={update} help="Used only for smaller/farther faces when long-distance mode is enabled." />
              </div>
              <NumberField label="Minimum face size" name="min_face_size" value={settings.min_face_size} min="12" max="240" onChange={update} suffix="px" help="20 px is a balanced long-distance starting point." />
            </section>

            <section className="settings-section capture-section">
              <div className="section-title"><ShieldCheck size={17} /><div><h3>Capture & Display</h3><p>Control boxes and when known/unknown evidence is stored.</p></div></div>
              <div className="toggle-list compact-toggle-list">
                <ToggleRow name="show_bounding_boxes" checked={settings.show_bounding_boxes} onChange={update} title="Bounding boxes" description="Master switch for visible boxes. Camera BOXES toggle still applies per stream." />
                <ToggleRow name="unknown_detection_enabled" checked={settings.unknown_detection_enabled} onChange={update} title="Save unknown faces" description="Capture unknown evidence only when it passes the confidence target." />
              </div>
              <div className="capture-grid">
                <SliderField label="Known save confidence" name="known_capture_min_confidence" value={settings.known_capture_min_confidence} min="0.20" max="0.90" step="0.01" onChange={update} help="Minimum match confidence before saving a known-person event." />
                <SliderField label="Unknown save confidence" name="unknown_capture_min_confidence" value={settings.unknown_capture_min_confidence} min="0.20" max="0.90" step="0.01" onChange={update} help="Minimum detector confidence before saving unknown evidence." />
                <NumberField label="Known capture cooldown" name="known_capture_interval_seconds" value={settings.known_capture_interval_seconds} min="1" max="300" step="1" onChange={update} suffix="sec" />
                <NumberField label="Unknown capture cooldown" name="unknown_capture_interval_seconds" value={settings.unknown_capture_interval_seconds} min="1" max="600" step="1" onChange={update} suffix="sec" />
              </div>
            </section>
          </div>

          {user.role === 'SuperAdmin' && (
            <div className="settings-main-grid lower-grid">
              <section className="settings-section limits-section">
                <div className="section-title"><Camera size={17} /><div><h3>General Camera Limits</h3><p>Commercial/license allocation limits used when creating cameras.</p></div></div>
                <div className="settings-grid">
                  <NumberField label="Maximum cameras per Admin" name="max_cameras_per_admin" value={settings.max_cameras_per_admin} min="1" max="500" onChange={update} />
                  <NumberField label="Maximum cameras per Supervisor" name="max_cameras_per_supervisor" value={settings.max_cameras_per_supervisor} min="1" max="500" onChange={update} />
                </div>
              </section>

              <section className="settings-section health-section">
                <div className="section-title"><Gauge size={17} /><div><h3>Recommended Starting Point</h3><p>Balanced values for augmented-photo to live-camera matching.</p></div></div>
                <div className="health-list">
                  <div><span>Detection</span><strong>35%</strong></div>
                  <div><span>Recognition tolerance</span><strong>55%</strong></div>
                  <div><span>Long-distance tolerance</span><strong>60%</strong></div>
                  <div><span>Minimum face</span><strong>20 px</strong></div>
                </div>
                <small className="health-note">Tune using your own RTSP camera and lighting. Avoid increasing tolerance until the registered person is incorrectly rejected under normal angles.</small>
              </section>
            </div>
          )}

          {user.role === 'SuperAdmin' && (
            <section className="settings-section smtp-section">
              <div className="section-title"><Mail size={17} /><div><h3>Email / SMTP Notifications</h3><p>Used for password reset, license and operational notifications. The saved password is never displayed back in the UI.</p></div></div>
              <div className="smtp-grid">
                <div className="field-block"><label>SMTP host</label><input name="smtp_host" value={settings.smtp_host || ''} onChange={update} placeholder="smtp.office365.com" /></div>
                <NumberField label="Port" name="smtp_port" value={settings.smtp_port} min="1" max="65535" onChange={update} />
                <div className="field-block"><label>Username</label><input name="smtp_user" value={settings.smtp_user || ''} onChange={update} autoComplete="off" placeholder="alerts@company.com" /></div>
                <div className="field-block password-field"><label>Password / app password</label><div className="password-wrap"><input type={showSmtpPassword ? 'text' : 'password'} name="smtp_password" value={settings.smtp_password || ''} onChange={update} placeholder={settings.smtp_password_configured ? 'Configured securely — enter only to replace' : 'Enter SMTP password'} autoComplete="new-password" /><button type="button" onClick={() => setShowSmtpPassword(v => !v)} aria-label="Toggle SMTP password visibility">{showSmtpPassword ? <EyeOff size={14}/> : <Eye size={14}/>}</button></div></div>
                <div className="field-block"><label>From address</label><input type="email" name="email_from" value={settings.email_from || ''} onChange={update} placeholder="alerts@company.com" /></div>
                <label className="inline-check"><input type="checkbox" name="smtp_use_tls" checked={Boolean(settings.smtp_use_tls)} onChange={update} /><span>Use TLS</span></label>
              </div>
              <div className="smtp-test-row">
                <div className="field-block"><label>Test recipient</label><input type="email" value={testRecipient} onChange={e => setTestRecipient(e.target.value)} placeholder="your.email@company.com" /></div>
                <button type="button" className="test-email-btn" onClick={testEmail} disabled={testingEmail}><Send size={14} /> {testingEmail ? 'Testing…' : 'Send Test Email'}</button>
                {settings.smtp_password_configured && <span className="configured-chip"><CheckCircle2 size={13}/> SMTP password stored securely</span>}
              </div>
            </section>
          )}

          <div className="settings-savebar">
            <span><TimerReset size={14} /> {loading ? 'Loading configuration…' : 'Save applies the recognition values to live processing within about 2 seconds.'}</span>
            <button className="save-btn" type="submit" disabled={saving || loading}><Save size={15} />{saving ? 'Saving…' : 'Save Settings'}</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Settings;
