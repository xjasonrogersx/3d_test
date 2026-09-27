# 3d_test

Setup

```bash

# On the host
xhost +local:
docker run -it --name god \
  -v /home/jason/work:/workspace \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --device /dev/dri \
  ubuntu:24.04

# Inside the container
apt-get update && apt-get install -y \
  python3 python3-pip \
  libgl1 libglx0 libegl1 libgl1-mesa-dri \
  libglu1-mesa \
  libx11-6 libxext6 libxi6 libxfixes3 libxrandr2 libxxf86vm1
pip config set global.break-system-packages true
cd /workspace/3d_test
pip install -r requirements.txt
# pyrender 0.1.45 pins the incompatible PyOpenGL 3.1.0 release.
pip install --upgrade --force-reinstall \
 'PyOpenGL>=3.1.10' 'PyOpenGL_accelerate>=3.1.10'
python3 test1.py

```