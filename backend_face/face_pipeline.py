# -*- coding: utf-8 -*-
"""Conservative live FRS: detect far faces, name only strong/confirmed ones."""
import logging, os, threading, time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
import cv2, face_recognition, numpy as np
from insightface.app import FaceAnalysis
from recognition_guard import UNKNOWN, stable_known_evidence_key, update_identity_state
from save_face import save_face_image

log=logging.getLogger(__name__)
TOLERANCE=.46; LONG_RANGE_TOLERANCE=.50; MIN_FACE_PX=20; MIN_IDENTITY_FACE_PX=56
KNOWN_EVIDENCE_FACE_PX=72; UNKNOWN_EVIDENCE_FACE_PX=48; LONG_RANGE_FACE_PX=90
MIN_SAVE_INTERVAL=30.; UNKNOWN_MIN_SAVE_INTERVAL=20.; MAX_TRACK_AGE_SECONDS=.75
face_app=None; face_apps={}; available_gpus=[]; data_directory=""
runtime_profile={"device":"uninitialized","ctx":-1,"det_size":None,"process_every_n":4,"providers":[]}
company_embeddings={}; person_tracking=defaultdict(dict); track_id_counter=defaultdict(int)
best_evidence=defaultdict(dict); unknown_clusters=defaultdict(dict); unknown_cluster_counter=defaultdict(int)
embedding_lock=threading.RLock(); tracking_lock=threading.RLock(); _settings_lock=threading.RLock(); _settings_cache={}

def _f(n,d,lo,hi):
    try:return max(lo,min(hi,float(os.getenv(n,str(d)))))
    except:return d

def _i(n,d,lo,hi):
    try:return max(lo,min(hi,int(os.getenv(n,str(d)))))
    except:return d

def _settings(company):
    now=time.time(); key=str(company or "default")
    with _settings_lock:
        c=_settings_cache.get(key)
        if c and now-c.get("_loaded_at",0)<2:return c
    s={"face_recognition_enabled":True,"show_bounding_boxes":True,"unknown_detection_enabled":True,
       "long_distance_detection_enabled":True,"min_face_size":20,"min_identity_face_size":56,
       "known_evidence_min_face_size":72,"unknown_evidence_min_face_size":48,"detection_confidence_target":.45,
       "recognition_tolerance":.46,"long_range_tolerance":.50,"recognition_margin":.06,
       "long_range_recognition_margin":.08,"known_capture_min_confidence":.58,"unknown_capture_min_confidence":.55,
       "known_capture_interval_seconds":30.,"unknown_capture_interval_seconds":20.,"identity_confirmations":2,
       "identity_switch_confirmations":4,"evidence_min_quality":.30,"evidence_min_observations":2}
    try:
        from auth.storage import get_settings
        s.update({k:v for k,v in (get_settings(None if key=="default" else key) or {}).items() if v is not None})
    except Exception as e:log.debug("settings %s: %s",key,e)
    s["recognition_tolerance"]=min(float(s.get("recognition_tolerance",.46)),_f("FRS_RECOGNITION_MAX_TOLERANCE",.50,.35,.55))
    s["long_range_tolerance"]=min(float(s.get("long_range_tolerance",.50)),_f("FRS_LONG_RANGE_MAX_TOLERANCE",.52,.35,.56))
    s["recognition_margin"]=max(.05,float(s.get("recognition_margin",.06))); s["long_range_recognition_margin"]=max(.07,float(s.get("long_range_recognition_margin",.08)))
    s["min_identity_face_size"]=max(int(s.get("min_identity_face_size",56)),_i("FRS_MIN_IDENTITY_FACE_PX",56,40,160))
    s["known_evidence_min_face_size"]=max(int(s.get("known_evidence_min_face_size",72)),_i("FRS_KNOWN_EVIDENCE_MIN_FACE_PX",72,48,220))
    s["unknown_evidence_min_face_size"]=max(int(s.get("unknown_evidence_min_face_size",48)),_i("FRS_UNKNOWN_EVIDENCE_MIN_FACE_PX",48,36,180))
    s["known_capture_min_confidence"]=max(.55,float(s.get("known_capture_min_confidence",.58))); s["unknown_capture_min_confidence"]=max(.50,float(s.get("unknown_capture_min_confidence",.55)))
    s["known_capture_interval_seconds"]=max(float(s.get("known_capture_interval_seconds",30)),_f("FRS_KNOWN_EVIDENCE_COOLDOWN",30,10,3600))
    s["unknown_capture_interval_seconds"]=max(float(s.get("unknown_capture_interval_seconds",20)),_f("FRS_UNKNOWN_EVIDENCE_COOLDOWN",20,10,3600))
    s["identity_confirmations"]=max(2,int(s.get("identity_confirmations",2))); s["identity_switch_confirmations"]=max(s["identity_confirmations"]+2,int(s.get("identity_switch_confirmations",4)))
    s["evidence_min_quality"]=max(.25,float(s.get("evidence_min_quality",.30))); s["evidence_min_observations"]=max(2,int(s.get("evidence_min_observations",2))); s["_loaded_at"]=now
    with _settings_lock:_settings_cache[key]=s
    return s

def get_runtime_settings(company_id=None):return dict(_settings(str(company_id or "default")))
def clear_runtime_settings_cache(company_id=None):
    with _settings_lock:
        _settings_cache.clear() if company_id is None else _settings_cache.pop(str(company_id or "default"),None)

def _iou(a,b):
    x1,y1,x2,y2=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    if x2<=x1 or y2<=y1:return 0.
    q=(x2-x1)*(y2-y1); aa=(a[2]-a[0])*(a[3]-a[1]); bb=(b[2]-b[0])*(b[3]-b[1]); return q/(aa+bb-q+1e-6)
def _ov(a,b):
    x1,y1,x2,y2=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    if x2<=x1 or y2<=y1:return 0.
    return (x2-x1)*(y2-y1)/(min(max(1,(a[2]-a[0])*(a[3]-a[1])),max(1,(b[2]-b[0])*(b[3]-b[1])))+1e-6)
def _same(a,b):
    i,o=_iou(a,b),_ov(a,b); d=max(a[2]-a[0],a[3]-a[1],b[2]-b[0],b[3]-b[1],1)
    c=np.hypot((a[0]+a[2]-b[0]-b[2])/2,(a[1]+a[3]-b[1]-b[3])/2)/d
    return i>=.42 or o>=.68 or (i>=.20 and c<=.35)
def _dedupe(xs):
    out=[]
    for x in sorted(xs,key=lambda z:float(z.get("det_conf",z.get("conf",0))),reverse=True):
        if not any(x.get("bbox") and y.get("bbox") and _same(x["bbox"],y["bbox"]) for y in out):out.append(x)
    return out

def _quality(c,conf):
    if c is None or not c.size or min(c.shape[:2])<8:return 0.
    g=cv2.cvtColor(c,cv2.COLOR_BGR2GRAY); sh=np.clip(np.log1p(cv2.Laplacian(g,cv2.CV_64F).var())/np.log1p(600),0,1); sz=np.clip(min(c.shape[:2])/160,0,1); m=float(g.mean()); ex=1 if 45<=m<=215 else max(.35,1-abs(m-130)/160)
    return float(np.clip((.5*sh+.3*sz+.2*conf)*ex,0,1))
def _crop(f,b,p=.18):
    h,w=f.shape[:2]; x1,y1,x2,y2=b; pw,ph=int((x2-x1)*p),int((y2-y1)*p); c=f[max(0,y1-ph):min(h,y2+ph),max(0,x1-pw):min(w,x2+pw)].copy(); return c if c.size and min(c.shape[:2])>=10 else None
def _encode(f,b,size):
    c=_crop(f,b);
    if c is None:return None
    if size<LONG_RANGE_FACE_PX and min(c.shape[:2])<160:
        sc=min(3.,160/max(1,min(c.shape[:2]))); c=cv2.resize(c,None,fx=sc,fy=sc,interpolation=cv2.INTER_LANCZOS4)
    r=cv2.cvtColor(c,cv2.COLOR_BGR2RGB); h,w=r.shape[:2]
    try:
        e=face_recognition.face_encodings(r,known_face_locations=[(0,w-1,h-1,0)],num_jitters=1,model="large"); return np.asarray(e[0]) if e else None
    except:return None

def _match(enc,known,names,size,det,s):
    if enc is None or not known or size<int(s["min_identity_face_size"]) or det<max(.50,float(s["detection_confidence_target"])):return UNKNOWN,det,None
    lr=size<LONG_RANGE_FACE_PX; th=min(float(s["long_range_tolerance"] if lr else s["recognition_tolerance"]),.52 if lr else .50); mr=float(s["long_range_recognition_margin"] if lr else s["recognition_margin"]); vr=3 if lr else 2
    by=defaultdict(list)
    for n,d in zip(names,face_recognition.face_distance(known,enc)):by[str(n)].append(float(d))
    r=[]
    for n,v in by.items():v.sort(); r.append((n,v[0],sum(x<=th+.01 for x in v),float(np.mean(v[:min(3,len(v))]))))
    r.sort(key=lambda x:(x[1],x[3]))
    if not r:return UNKNOWN,det,None
    n,b,v,m=r[0]; sec=r[1][1] if len(r)>1 else 1.
    if b>th or v<vr or m>th+.015 or (len(r)>1 and sec-b<mr):return UNKNOWN,det,b
    return n,max(0.,min(1.,1-b)),b

def _track(b,tracks):
    best=None; score=0
    for tid,t in tracks.items():
        old=t.get("bbox")
        if old and _same(b,old):
            q=max(_iou(b,old),.9*_ov(b,old))
            if q>score:best,score=tid,q
    return best
def _cleanup(sid,now):
    for tid in list(person_tracking[sid]):
        if now-float(person_tracking[sid][tid].get("last_seen",0))>MAX_TRACK_AGE_SECONDS:del person_tracking[sid][tid]
    for cid in list(unknown_clusters[sid]):
        if now-float(unknown_clusters[sid][cid].get("last_seen",0))>25:del unknown_clusters[sid][cid]
def _ukey(sid,enc,b,now):
    sid=str(sid or "default"); cs=unknown_clusters[sid]; bid=None; bd=999
    if enc is not None:
        for cid,x in cs.items():
            if x.get("encoding") is not None:
                d=float(np.linalg.norm(np.asarray(x["encoding"])-enc))
                if d<.50 and d<bd:bid,bd=cid,d
    if bid is None:
        for cid,x in cs.items():
            if now-x.get("last_seen",0)<=2 and x.get("bbox") and _same(b,x["bbox"]):bid=cid; break
    if bid is None:unknown_cluster_counter[sid]+=1; bid=unknown_cluster_counter[sid]; cs[bid]={}
    cs[bid].update({"encoding":enc,"bbox":b,"last_seen":now}); return f"unknown:cluster_{bid}"
def _offer(sid,key,c,q,now,cool,n):
    r=best_evidence[sid].setdefault(key,{"q":-1.,"crop":None,"n":0,"saved":0.}); r["n"]+=1
    if q>r["q"]:r["q"],r["crop"]=q,c.copy()
    if r["n"]<n or now-r["saved"]<cool or r["crop"] is None:return None
    out=r["crop"]; r.update({"q":-1.,"crop":None,"n":0,"saved":now}); return out
def _camera(sid,company):
    cam="camera"; comp=str(company or "default")
    if sid:
        try:
            from camera_management.streaming import get_stream_manager
            x=get_stream_manager().get_stream_info(sid) or {}; cam=str(x.get("camera_name") or (f"camera_{x.get('camera_id')}" if x.get("camera_id") is not None else "camera")); comp=str(x.get("company_id") or comp)
        except:pass
    return cam,comp

def check_gpu_availability():
    try:
        import onnxruntime as ort
        if "CUDAExecutionProvider" not in ort.get_available_providers():return []
        return [0]
    except:return []
def init(data_dir,ctx=-1,det_size=(640,640),use_dual_gpu=True):
    del use_dual_gpu
    global data_directory,face_app
    data_directory=data_dir; g=check_gpu_availability(); dev="gpu" if g else "cpu"; c=(ctx if ctx>=0 and ctx in g else g[0]) if dev=="gpu" else -1; ds=det_size if dev=="gpu" else (min(det_size[0],640),min(det_size[1],640))
    try:a=FaceAnalysis(allowed_modules=["detection"],providers=["CUDAExecutionProvider","CPUExecutionProvider"] if dev=="gpu" else ["CPUExecutionProvider"])
    except TypeError:a=FaceAnalysis(allowed_modules=["detection"])
    a.prepare(ctx_id=c,det_size=ds); face_app=a; face_apps.clear(); available_gpus.clear()
    if dev=="gpu":face_apps[c]=a; available_gpus.append(c)
    runtime_profile.update({"device":dev,"ctx":c,"det_size":ds,"process_every_n":_i("FACE_PROCESS_EVERY_N_GPU" if dev=="gpu" else "FACE_PROCESS_EVERY_N_CPU",2 if dev=="gpu" else 5,1,30)})
def get_runtime_profile():return dict(runtime_profile)
def clear_company_embeddings_cache(company_id):
    with embedding_lock:company_embeddings.pop(str(company_id or "default"),None)
def load_company_embeddings(company_id):
    c=str(company_id or "default")
    with embedding_lock:
        x=company_embeddings.get(c)
        if x and time.time()-x.get("last_loaded",0)<300:return x
    try:
        from fr1 import load_known_faces
        e,n=load_known_faces(data_directory,company_id=c)
    except Exception as z:log.error("gallery %s: %s",c,z); e,n=[],[]
    x={"encodings":e,"names":n,"last_loaded":time.time()}
    with embedding_lock:company_embeddings[c]=x
    return x

def process_frame(frame_bgr,force_process=False,stream_id=None,company_id=None):
    del force_process
    if frame_bgr is None:return frame_bgr,[]
    app=face_apps[available_gpus[hash(stream_id or "")%len(available_gpus)]] if face_apps and available_gpus else face_app
    if app is None:raise RuntimeError("Face pipeline not initialised")
    if not company_id and stream_id:
        try:
            from camera_management.streaming import get_stream_manager
            company_id=(get_stream_manager().get_stream_info(stream_id) or {}).get("company_id")
        except:pass
    company=str(company_id or "default"); s=_settings(company)
    if not s["face_recognition_enabled"]:return frame_bgr,[]
    minface=max(12,int(s["min_face_size"])); minface=max(minface,48) if not s["long_distance_detection_enabled"] else minface; target=max(.2,float(s["detection_confidence_target"])); g=load_company_embeddings(company); known,names=g["encodings"],g["names"]
    sid=str(stream_id or "default"); now=time.time(); _cleanup(sid,now)
    h,w=frame_bgr.shape[:2]; raw=[]
    for f in app.get(frame_bgr):
        b=getattr(f,"bbox",None)
        if b is None or len(b)<4:continue
        x1,y1,x2,y2=map(int,b[:4]); conf=float(getattr(f,"det_score",0) or getattr(f,"score",0) or 0); x1,y1,x2,y2=max(0,x1),max(0,y1),min(w,x2),min(h,y2)
        if conf>=target and x2>x1 and y2>y1 and min(x2-x1,y2-y1)>=minface:raw.append({"bbox":(x1,y1,x2,y2),"det_conf":conf})
    tracks=person_tracking[sid] if stream_id else {}; out=[]
    for d in _dedupe(raw):
        b,dc=d["bbox"],d["det_conf"]; x1,y1,x2,y2=b; fw,fh=x2-x1,y2-y1; size=min(fw,fh); c=frame_bgr[y1:y2,x1:x2]; tid=_track(b,tracks) if stream_id else None; t=tracks.get(tid) if tid is not None else None; enc=None
        verify=t is None or now-float(t.get("last_verified_at",0))>=.8 or (t.get("bbox") and _iou(t["bbox"],b)<.12)
        if not verify:name=str(t.get("confirmed_name") or UNKNOWN); conf=float(t.get("conf",dc)); enc=t.get("encoding")
        else:
            enc=_encode(frame_bgr,b,size); cand,conf,dist=_match(enc,known,names,size,dc,s); state=t if t is not None else {}; name=update_identity_state(state,cand,candidate_is_strong=cand!=UNKNOWN and dist is not None,confirm_hits=int(s["identity_confirmations"]),switch_hits=int(s["identity_switch_confirmations"])); state["last_verified_at"]=now; t=state
        if stream_id:
            if tid is None:track_id_counter[sid]+=1; tid=track_id_counter[sid]; tracks[tid]=t or {}; t=tracks[tid]
            t.update({"bbox":b,"last_seen":now,"display_name":name,"conf":conf,"det_conf":dc});
            if enc is not None:t["encoding"]=enc
        q=_quality(c,dc); known_person=name!=UNKNOWN; minev=int(s["known_evidence_min_face_size"] if known_person else s["unknown_evidence_min_face_size"]); minconf=float(s["known_capture_min_confidence"] if known_person else s["unknown_capture_min_confidence"]); eligible=size>=minev and q>=float(s["evidence_min_quality"]) and (conf if known_person else dc)>=minconf and (known_person or s["unknown_detection_enabled"])
        if eligible:
            key=stable_known_evidence_key(name) if known_person else _ukey(stream_id,enc,b,now); cool=float(s["known_capture_interval_seconds"] if known_person else s["unknown_capture_interval_seconds"]); ev=_crop(frame_bgr,b,.35 if size>=90 else .45); chosen=_offer(sid,key,ev,q,now,cool,int(s["evidence_min_observations"])) if ev is not None and stream_id else ev
            if chosen is not None:
                cam,comp=_camera(stream_id,company); crop=chosen.copy(); label=name if known_person else UNKNOWN; cf=conf if known_person else dc
                def _save(crop=crop,label=label,cf=cf,cool=cool,cam=cam,comp=comp,key=key):
                    save_face_image(face_crop_bgr=crop,label=label,confidence=cf,min_interval=cool,source="stream",jpeg_quality=96,target_width=320,max_upscale=3.,camera_name=cam,company_id=comp,identity_key=key,min_known_confidence=float(s["known_capture_min_confidence"]),min_unknown_confidence=float(s["unknown_capture_min_confidence"]))
                threading.Thread(target=_save,daemon=True).start()
        out.append({"name":name,"conf":conf if known_person else dc,"bbox":b,"face_size_px":(fw,fh),"track_id":tid,"quality":round(q,3),"review_required":known_person})
    if stream_id:
        active=[]
        for tid,t in tracks.items():
            if now-float(t.get("last_seen",0))<MAX_TRACK_AGE_SECONDS and t.get("bbox"):
                b=t["bbox"]; n=str(t.get("display_name") or t.get("confirmed_name") or UNKNOWN); active.append({"name":n,"conf":float(t.get("conf",t.get("det_conf",0))),"bbox":b,"track_id":tid,"face_size_px":(b[2]-b[0],b[3]-b[1]),"is_persisted":now-float(t.get("last_seen",0))>.1,"review_required":n!=UNKNOWN})
        return frame_bgr,_dedupe(active)
    return frame_bgr,_dedupe(out)

def render_bounding_boxes(frame,detections,show_bounding_box=True):
    if not show_bounding_box or not detections:return frame
    out=frame.copy(); scale=max(.5,min(1.,out.shape[1]/900)); thick=max(2,int(scale*2))
    for d in _dedupe(detections):
        if not d.get("bbox"):continue
        x1,y1,x2,y2=map(int,d["bbox"]); n=str(d.get("name") or UNKNOWN); color=(0,180,0) if n!=UNKNOWN else (0,0,220); cv2.rectangle(out,(x1,y1),(x2,y2),color,thick); (tw,th),base=cv2.getTextSize(n,cv2.FONT_HERSHEY_SIMPLEX,scale,thick); ly=max(0,y1-th-base-8); cv2.rectangle(out,(x1,ly),(x1+tw+8,ly+th+base+8),color,cv2.FILLED); cv2.putText(out,n,(x1+4,ly+th+4),cv2.FONT_HERSHEY_SIMPLEX,scale,(255,255,255),thick,cv2.LINE_AA)
    return out
