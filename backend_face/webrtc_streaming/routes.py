"""
WebRTC streaming routes
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from .webrtc_service import get_webrtc_manager, WebRTCStreamManager
from auth.config import ENABLE_LEGACY_WEBRTC_CONNECT
from auth.secret_store import mask_secret_url

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webrtc"])

@router.websocket("/ws/socket.io")
async def socketio_compatibility_endpoint(
    websocket: WebSocket,
    webrtc_manager: WebRTCStreamManager = Depends(get_webrtc_manager)
):
    """Socket.io compatibility endpoint for DirectWebRTCPlayer.js"""
    try:
        # Use a generic camera_id or extract from query if possible
        await webrtc_manager.connect(websocket, "socketio_compat")
    except WebSocketDisconnect:
        logger.info("Socket.io compatibility WebSocket disconnected")
    except Exception as e:
        logger.error(f"Socket.io compatibility WebSocket error: {e}")

@router.websocket("/ws/webrtc/{camera_id}")
async def websocket_webrtc_endpoint(
    websocket: WebSocket,
    camera_id: int,
    webrtc_manager: WebRTCStreamManager = Depends(get_webrtc_manager)
):
    """WebSocket endpoint for WebRTC signaling"""
    try:
        await webrtc_manager.connect(websocket, str(camera_id))
    except WebSocketDisconnect:
        logger.info(f"WebRTC WebSocket disconnected for camera {camera_id}")
    except Exception as e:
        logger.error(f"WebRTC WebSocket error for camera {camera_id}: {e}")

@router.post("/stream")
async def webrtc_stream_offer(
    request: dict,
    http_request: Request,
    webrtc_manager: WebRTCStreamManager = Depends(get_webrtc_manager)
):
    """Legacy WebRTC signaling. Disabled by default because it accepts camera network targets."""
    try:
        if not ENABLE_LEGACY_WEBRTC_CONNECT:
            raise HTTPException(status_code=403, detail="Legacy WebRTC connect is disabled")
        collection_name = request.get("collection_name")
        camera_ip = request.get("camera_ip")
        offer_sdp = request.get("sdp")
        
        logger.info(f"Received WebRTC offer for collection {collection_name}, camera {camera_ip}")
        
        # In a real implementation with aiortc, we would:
        # 1. Create a PeerConnection
        # 2. Set remote description (offer)
        # 3. Add tracks (from RTSP)
        # 4. Create local description (answer)
        # 5. Return answer
        
        # For now, we'll return a mock answer that matches what the frontend expects
        # and use the demo SDP generation from webrtc_manager
        
        camera_id = f"{collection_name}_{camera_ip.replace('.', '_')}"
        
        # Try to get real RTSP URL if possible (mocked for now)
        rtsp_url = f"rtsp://{camera_ip}:554/stream"
        
        answer_sdp = webrtc_manager.create_rtsp_sdp(camera_id, rtsp_url)
        
        return {
            "success": True,
            "data": {
                "type": "answer",
                "sdp": answer_sdp
            }
        }
    except Exception as e:
        logger.error(f"Error handling WebRTC offer: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/connect")
async def webrtc_connect(
    request: dict,
    http_request: Request,
    webrtc_manager: WebRTCStreamManager = Depends(get_webrtc_manager)
):
    """Legacy arbitrary RTSP WebRTC connect. Disabled by default for SSRF/credential safety."""
    try:
        if not ENABLE_LEGACY_WEBRTC_CONNECT:
            raise HTTPException(status_code=403, detail="Legacy WebRTC connect is disabled")
        rtsp_url = request.get("rtspUrl")
        offer = request.get("offer")
        
        logger.info(f"Received WebRTC connect request for RTSP URL: {mask_secret_url(rtsp_url)}")
        
        # Extract camera info from RTSP URL if possible, otherwise use a generic ID
        camera_id = "rtsp_camera_" + str(hash(rtsp_url))
        
        answer_sdp = webrtc_manager.create_rtsp_sdp(camera_id, rtsp_url)
        
        return {
            "success": True,
            "answer": {
                "type": "answer",
                "sdp": answer_sdp
            }
        }
    except Exception as e:
        logger.error(f"Error handling WebRTC connect: {e}")
        return {
            "success": False,
            "error": str(e)
        }
