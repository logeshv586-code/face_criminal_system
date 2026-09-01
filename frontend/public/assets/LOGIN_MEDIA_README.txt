LOGIN BACKGROUND MEDIA
======================
The existing animated login supports video OR image/GIF media.

Default:
  public/assets/login-bg.mov

To replace the background without editing React code:
1. Put your file in frontend/public/assets/, e.g. login-bg.gif
2. Create frontend/.env (do not commit it) with:
   REACT_APP_LOGIN_MEDIA=/assets/login-bg.gif
3. Rebuild: npm run build

Supported image modes: .gif, .png, .jpg, .jpeg, .webp, .avif
Other file extensions are rendered as looping muted video.

Keep media local in the package; do not load remote login assets in production.
