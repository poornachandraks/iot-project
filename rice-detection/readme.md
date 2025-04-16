# Grain Classification System (FastAPI + OpenCV)

### Installation

First, navigate into the project directory:

```bash
cd rice-detection
```
Setup a virtual environment:

```bash
python -m venv venv --system-site-packages
. venv/bin/activate
```
Install requirements:

```bash
pip install -r requirements.txt
```
### Set up Firebase:
1.Download key.json from Firebase
    ->Go to the Firebase Console.
    ->Select your project.
    ->Navigate to Project settings (in the left vertical bar)> Firebase Admin SDK.
    ->Click on "Generate new private key" and save the file as key.json to your project directory.

2.Create a realtime database
    ->Go to build, then Realtime Database.
    ->Create the database in the southeast region and in test mode.
    ->Copy the reference url.

3.Rename the config.template.py file to config.py
    -> Update the dbUrl variable to the previous copied reference url.

### Run the application

Start the FastAPI server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open the browser from another device on the same network (Don't use RVCE network):
```bash
http://<raspberrypi-ip>:8000
```

Get the raspberrypi's ip using,
```bash
ifconfig
```
Copy the IPv4 address.


Example:

```bash
http://192.168.1.42:8000
```


Upload Guidelines
Upload a top-view image of grains (e.g., rice).

The app processes the image using Watershed Segmentation.

Output:

✅ Green contours = Whole grains

❌ Red contours = Broken grains

Counts displayed directly on the webpage.

