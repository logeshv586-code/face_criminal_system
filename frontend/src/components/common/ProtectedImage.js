import React from 'react';
import { getAuthHeaders } from '../../utils/fetchAuthShim';

const ProtectedImage = React.forwardRef(({ src, alt = '', onError, onLoad, ...props }, ref) => {
  const [objectUrl, setObjectUrl] = React.useState('');
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let active = true;
    let createdUrl = '';
    let retryTimer = null;
    setFailed(false);
    setObjectUrl('');
    if (!src) return () => {};

    if (/^(data:|blob:|file:)/i.test(src)) {
      setObjectUrl(src);
      return () => {};
    }

    const load = async (attempt = 0) => {
      try {
        const response = await fetch(src, {
          headers: getAuthHeaders(),
          cache: 'no-store',
        });
        if (!response.ok) throw new Error(`Image request failed (${response.status})`);
        const blob = await response.blob();
        if (!active) return;
        if (!blob || blob.size === 0) throw new Error('Empty image response');
        createdUrl = URL.createObjectURL(blob);
        setObjectUrl(createdUrl);
      } catch (error) {
        if (!active) return;
        if (attempt === 0) {
          retryTimer = setTimeout(() => load(1), 250);
          return;
        }
        setFailed(true);
        if (onError) { try { onError(error); } catch (_) {} }
      }
    };
    load();

    return () => {
      active = false;
      if (retryTimer) clearTimeout(retryTimer);
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [src]); // keep image fetch stable even when parent creates inline handlers

  if (failed || !objectUrl) {
    return <span className={props.className ? `${props.className} protected-image-placeholder` : 'protected-image-placeholder'} title={failed ? `Unable to load ${alt || 'image'}` : 'Loading image'} aria-label={alt} />;
  }
  return <img ref={ref} src={objectUrl} alt={alt} onLoad={onLoad} {...props} />;
});

ProtectedImage.displayName = 'ProtectedImage';
export default ProtectedImage;
