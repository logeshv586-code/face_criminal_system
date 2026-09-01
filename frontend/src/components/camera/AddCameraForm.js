import React, { useEffect, useMemo, useState } from 'react';
import { Camera, MapPin, Link2, Folder, CheckCircle2, AlertCircle, Loader2, Trash2 } from 'lucide-react';
import { useCameras } from './CameraManager';
import { extractIPFromStreamURL, validatePrivateIP } from '../../utils/ipValidation';
import { API_BASE_URL } from '../../utils/apiConfig';
import useAuthStore from '../../store/authStore';
import './AddCameraForm.css';

const AddCameraForm = ({ collectionId, onClose, editingCamera = null }) => {
  const { token } = useAuthStore();
  const { addCamera, updateCamera, removeCamera, collections = [], activeCollection } = useCameras();
  const [cameraName, setCameraName] = useState('');
  const [location, setLocation] = useState('');
  const [streamUrl, setStreamUrl] = useState('');
  const [selectedCollection, setSelectedCollection] = useState(collectionId || activeCollection || 'default');
  const [error, setError] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);

  useEffect(() => {
    if (editingCamera) {
      setCameraName(editingCamera.name || '');
      setLocation(editingCamera.location || '');
      setStreamUrl(editingCamera.streamUrl || editingCamera.rtsp_url || editingCamera.stream_url || '');
      setSelectedCollection(editingCamera.collection_id || editingCamera.collectionId || collectionId || activeCollection || 'default');
    } else {
      setCameraName(''); setLocation(''); setStreamUrl('');
      setSelectedCollection(collectionId || activeCollection || collections[0]?.id || 'default');
    }
    setError(''); setValidationResult(null);
  }, [editingCamera, collectionId, activeCollection]);

  const effectiveCollection = useMemo(() => selectedCollection || collectionId || activeCollection || collections[0]?.id || 'default', [selectedCollection, collectionId, activeCollection, collections]);

  const validateCameraData = async (ip, url, collectionName = null, excludeIp = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/collections/validate-camera`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ip, streamUrl: url, collection_name: collectionName, exclude_ip: excludeIp }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) return { valid: false, error: result.detail || `Camera validation failed (${response.status})`, type: 'server_error' };
      return result;
    } catch (err) {
      return { valid: false, error: `Unable to reach the camera validation service: ${err.message}`, type: 'network_error' };
    }
  };

  const validateForm = async () => {
    const name = cameraName.trim(); const url = streamUrl.trim();
    if (!name) { setError('Camera name is required.'); return false; }
    if (!effectiveCollection) { setError('Select a collection for this camera.'); return false; }
    if (!url) { setError('RTSP/HTTP stream URL or local camera index is required.'); return false; }

    const isCameraIndex = /^\d+$/.test(url);
    if (!isCameraIndex && !/^https?:\/\//i.test(url) && !/^rtsp:\/\//i.test(url)) {
      setError('Use rtsp://, http://, https://, or a local camera index such as 0.'); return false;
    }

    let extractedIP = url;
    if (!isCameraIndex) {
      extractedIP = extractIPFromStreamURL(url);
      if (!extractedIP) { setError('The stream URL must contain a valid camera IP address.'); return false; }
      const ipValidation = validatePrivateIP(extractedIP);
      if (!ipValidation.isValid) {
        setError(`Camera IP ${extractedIP} must be inside a private network range (192.168.x.x, 10.x.x.x, or 172.16–31.x.x).`); return false;
      }
    }

    setIsValidating(true); setValidationResult(null);
    const target = collections.find(c => c.id === effectiveCollection);
    const excludeIp = editingCamera ? extractIPFromStreamURL(editingCamera.streamUrl || editingCamera.rtsp_url || '') : null;
    const validation = await validateCameraData(extractedIP, url, target?.name, excludeIp);
    setIsValidating(false); setValidationResult(validation);
    if (!validation?.valid) { setError(validation?.error || 'Camera validation failed.'); return false; }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setError('');
    if (!(await validateForm())) return;
    try {
      if (editingCamera) {
        await updateCamera(editingCamera.id, { name: cameraName.trim(), location: location.trim(), streamUrl: streamUrl.trim(), collectionId: effectiveCollection });
      } else {
        await addCamera(cameraName.trim(), streamUrl.trim(), effectiveCollection, location.trim());
      }
      setValidationResult(null);
      onClose?.();
    } catch (err) {
      setError(err?.message || `Failed to ${editingCamera ? 'update' : 'add'} camera.`);
    }
  };

  const handleDelete = async () => {
    if (!editingCamera) return;
    try { await removeCamera(editingCamera.id); setShowDeleteConfirm(false); onClose?.(); }
    catch (err) { setError(err?.message || 'Failed to delete camera.'); setShowDeleteConfirm(false); }
  };

  return (
    <div className="add-camera-form">
      <div className="camera-form-intro">
        <span className="camera-form-icon"><Camera size={18} /></span>
        <div><h3>{editingCamera ? 'Edit camera connection' : 'Add camera connection'}</h3><p>Enter the camera details exactly as provided by the CCTV/NVR. Credentials in the URL are encrypted before storage.</p></div>
      </div>
      <form onSubmit={handleSubmit} autoComplete="off">
        {error && <div className="camera-form-message error"><AlertCircle size={16} /><span>{error}</span></div>}
        {validationResult?.valid && <div className="camera-form-message success"><CheckCircle2 size={16} /><span>Camera details validated successfully.</span></div>}

        <div className="camera-form-grid">
          <div className="camera-field"><label htmlFor="camera-name"><Camera size={13} />Camera name <b>*</b></label><input id="camera-name" value={cameraName} onChange={e => { setCameraName(e.target.value); setValidationResult(null); }} placeholder="Example: Main Gate Camera" required autoFocus={!editingCamera} /></div>
          <div className="camera-field"><label htmlFor="camera-location"><MapPin size={13} />Location</label><input id="camera-location" value={location} onChange={e => setLocation(e.target.value)} placeholder="Example: Main Gate / Floor 1" /></div>
          <div className="camera-field"><label htmlFor="camera-collection"><Folder size={13} />Collection <b>*</b></label><select id="camera-collection" value={effectiveCollection} onChange={e => setSelectedCollection(e.target.value)}>{collections.map(c => <option value={c.id} key={c.id}>{c.name}</option>)}</select></div>
          <div className="camera-field camera-field-wide"><label htmlFor="stream-url"><Link2 size={13} />Stream URL / camera index <b>*</b></label><input id="stream-url" value={streamUrl} onChange={e => { setStreamUrl(e.target.value); setValidationResult(null); }} placeholder="rtsp://user:password@192.168.1.100:554/stream or 0" required spellCheck="false" /><small>Supported: RTSP, HTTP/HTTPS and local webcam index. The application validates private-network IP addresses before saving.</small></div>
        </div>

        <div className="camera-form-actions">
          <div>{editingCamera && <button type="button" className="camera-danger-btn" onClick={() => setShowDeleteConfirm(true)} disabled={isValidating}><Trash2 size={14} />Delete</button>}</div>
          <div className="camera-form-actions-right"><button type="button" className="camera-secondary-btn" onClick={() => onClose?.()} disabled={isValidating}>Cancel</button><button type="submit" className="camera-primary-btn" disabled={isValidating}>{isValidating ? <><Loader2 size={14} className="camera-spin" />Validating…</> : editingCamera ? 'Save Camera' : 'Add Camera'}</button></div>
        </div>
      </form>

      {showDeleteConfirm && <div className="camera-modal-overlay" onMouseDown={e => e.target === e.currentTarget && setShowDeleteConfirm(false)}><div className="camera-confirm-modal"><h3>Delete camera?</h3><p>This removes the camera configuration and stops its active stream.</p><div><button type="button" className="camera-secondary-btn" onClick={() => setShowDeleteConfirm(false)}>Cancel</button><button type="button" className="camera-danger-btn" onClick={handleDelete}>Delete Camera</button></div></div></div>}
    </div>
  );
};

export default AddCameraForm;
