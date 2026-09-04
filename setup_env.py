import os
import subprocess
import sys
import site

def run_command(cmd):
    print(f"Running: {cmd}")
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {cmd}")
        sys.exit(e.returncode)

def patch_face_recognition_models():
    print("Patching face_recognition_models to fix pkg_resources deprecation...")
    try:
        import face_recognition_models
        init_file = face_recognition_models.__file__
    except ImportError:
        # Fallback to site-packages path if import fails somehow
        site_packages = site.getsitepackages()
        init_file = None
        for sp in site_packages:
            potential_path = os.path.join(sp, 'face_recognition_models', '__init__.py')
            if os.path.exists(potential_path):
                init_file = potential_path
                break
        
        if not init_file:
            print("Could not find face_recognition_models installation.")
            return

    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'from pkg_resources import resource_filename' in content:
        new_content = """# -*- coding: utf-8 -*-
import os

__author__ = \"\"\"Adam Geitgey\"\"\"
__email__ = 'ageitgey@gmail.com'
__version__ = '0.1.0'

def resource_filename(pkg, path):
    return os.path.join(os.path.dirname(__file__), path)

def pose_predictor_model_location():
    return resource_filename(__name__, "models/shape_predictor_68_face_landmarks.dat")

def pose_predictor_five_point_model_location():
    return resource_filename(__name__, "models/shape_predictor_5_face_landmarks.dat")

def face_recognition_model_location():
    return resource_filename(__name__, "models/dlib_face_recognition_resnet_model_v1.dat")

def cnn_face_detector_model_location():
    return resource_filename(__name__, "models/mmod_human_face_detector.dat")
"""
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully patched face_recognition_models!")
    else:
        print("face_recognition_models is already patched or does not use pkg_resources.")

def main():
    print("--- Setting up the environment ---")
    
    # 1. Install dlib from the local wheel
    dlib_wheel = "dlib-19.24.99-cp312-cp312-win_amd64.whl"
    if os.path.exists(dlib_wheel):
        run_command(f"{sys.executable} -m pip install {dlib_wheel}")
    else:
        print(f"Warning: {dlib_wheel} not found. Ensure it is in the same directory.")
        print("dlib installation might fail if building from source.")

    # 2. Install the rest of the requirements
    if os.path.exists("requirements.txt"):
        run_command(f"{sys.executable} -m pip install -r requirements.txt")
    else:
        print("Warning: requirements.txt not found.")

    # 3. Patch the broken library
    patch_face_recognition_models()
    
    print("--- Environment setup complete! ---")

if __name__ == "__main__":
    main()
